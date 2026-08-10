#!/usr/bin/env python3
"""Validate one ephemeral runtime model-route receipt without writing state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROUTES = {
    "frozen_deterministic": ("gpt-5.6-luna", "max"),
    "bounded_engineering": ("gpt-5.6-sol", "high"),
    "real_carrier": ("gpt-5.6-sol", "xhigh"),
    "scientific_decision": ("gpt-5.6-sol", "max"),
}

SAME_THREAD_ACTION_CLASSES = frozenset(
    {"bounded_engineering", "real_carrier", "scientific_decision"}
)


ROUTE_DISPATCH_MARKER = "MODEL_ROUTE_DISPATCH_ID="
LEGACY_ROUTE_DISPATCH_MARKER = "LUNA_ROUTE_DISPATCH_ID="
_ROUTE_DISPATCH_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*\Z")


def _route_prompt_preamble(route_mode: str, action_class: str) -> str:
    try:
        model, effort = ROUTES[action_class]
    except KeyError as exc:
        raise ValueError(f"unknown action class: {action_class}") from exc
    if route_mode == "same_thread":
        if action_class not in SAME_THREAD_ACTION_CLASSES:
            raise ValueError(
                "same-thread prompt requires explicit bounded_engineering, "
                "real_carrier, or scientific_decision action_class"
            )
        continuation = "await-successor-activation"
    elif route_mode == "named_child":
        if action_class != "frozen_deterministic":
            raise ValueError(
                "named-child prompt requires frozen_deterministic action_class"
            )
        continuation = "return-diff-and-validation-to-parent"
    else:
        raise ValueError(f"unknown route mode: {route_mode}")
    return f"PASS_MODEL_ROUTE: {model}/{effort}\n{continuation}\n"


@dataclass(frozen=True)
class RouteReceipt:
    action_class: str
    model: str
    effort: str
    context_eligible: bool = False
    protected_exposed: bool = False
    decision_ambiguity: bool = False
    receipt_source: str = "direct"
    route_mode: str = "named_child"
    agent_role: str | None = None
    parent_thread_id: str | None = None
    multi_agent_version: str | None = None
    thread_id: str | None = None
    turn_id: str | None = None
    first_turn_id: str | None = None
    capsule_bytes: int | None = None
    capsule_sha256: str | None = None
    route_dispatch_id: str | None = None


def expected_route(receipt: RouteReceipt) -> tuple[str, str]:
    if receipt.action_class not in ROUTES:
        raise ValueError(f"unknown action class: {receipt.action_class}")
    if receipt.action_class == "frozen_deterministic":
        if receipt.protected_exposed:
            raise ValueError("protected-exposed work cannot be routed to Luna")
        if receipt.decision_ambiguity:
            raise ValueError("decision-ambiguous work cannot be routed to Luna")
        if not receipt.context_eligible:
            raise ValueError("Luna requires a frozen oracle and eligible visible context")
    return ROUTES[receipt.action_class]


def validate_receipt(
    receipt: RouteReceipt,
    *,
    expected_parent_thread_id: str | None = None,
    expected_thread_id: str | None = None,
    expected_turn_id: str | None = None,
    expected_first_turn_id: str | None = None,
    expected_route_dispatch_id: str | None = None,
) -> tuple[str, str]:
    if receipt.route_mode not in {"named_child", "same_thread"}:
        raise ValueError(f"unknown route mode: {receipt.route_mode}")
    if (
        receipt.route_mode == "same_thread"
        and receipt.action_class == "frozen_deterministic"
    ):
        raise ValueError(
            "same-thread frozen_deterministic route must fail before effects"
        )
    if receipt.route_mode == "same_thread" and receipt.action_class not in SAME_THREAD_ACTION_CLASSES:
        raise ValueError(
            "same-thread route requires explicit bounded_engineering, real_carrier, or scientific_decision action_class"
        )
    if receipt.route_mode == "named_child" and receipt.action_class != "frozen_deterministic":
        raise ValueError("named-child route is reserved for frozen_deterministic")
    expected = expected_route(receipt)
    actual = (receipt.model, receipt.effort)
    if actual != expected:
        raise ValueError(
            "runtime route mismatch: "
            f"expected={expected[0]}/{expected[1]} actual={actual[0]}/{actual[1]}"
        )
    if receipt.route_mode == "same_thread":
        if receipt.receipt_source != "durable_rollout":
            raise ValueError("same-thread route requires durable rollout metadata")
        if not expected_thread_id:
            raise ValueError("same-thread route requires an expected thread")
        if receipt.thread_id != expected_thread_id:
            raise ValueError(
                "same-thread thread binding mismatch: "
                f"expected={expected_thread_id} actual={receipt.thread_id}"
            )
        if not receipt.turn_id:
            raise ValueError("same-thread route is missing durable turn identity")
        if expected_turn_id is not None and receipt.turn_id != expected_turn_id:
            raise ValueError(
                "same-thread turn binding mismatch: "
                f"expected={expected_turn_id} actual={receipt.turn_id}"
            )
        if not expected_route_dispatch_id:
            raise ValueError("same-thread route requires an expected route dispatch")
        validate_route_dispatch_id(expected_route_dispatch_id)
        if receipt.route_dispatch_id != expected_route_dispatch_id:
            raise ValueError(
                "same-thread route dispatch mismatch: "
                f"expected={expected_route_dispatch_id} actual={receipt.route_dispatch_id}"
            )
    elif receipt.action_class == "frozen_deterministic":
        if receipt.receipt_source != "durable_rollout":
            raise ValueError("Luna route requires durable rollout metadata")
        if receipt.route_mode == "named_child":
            if receipt.agent_role != "luna_worker":
                raise ValueError("Luna named-child route requires agent_role=luna_worker")
            if receipt.multi_agent_version not in {"v1", "v2"}:
                raise ValueError(
                    "Luna named-child route requires multi_agent_version=v1 or v2"
                )
            if not expected_parent_thread_id:
                raise ValueError(
                    "Luna named-child route requires an independently expected parent thread"
                )
            if receipt.parent_thread_id != expected_parent_thread_id:
                raise ValueError(
                    "Luna parent binding mismatch: "
                    f"expected={expected_parent_thread_id} actual={receipt.parent_thread_id}"
                )
            if not expected_thread_id:
                raise ValueError("Luna named-child route requires an independently expected child thread")
            if receipt.thread_id != expected_thread_id:
                raise ValueError(
                    "Luna child binding mismatch: "
                    f"expected={expected_thread_id} actual={receipt.thread_id}"
                )
            if not receipt.turn_id or not receipt.first_turn_id:
                raise ValueError("Luna named-child route requires current and first turn identity")
            if receipt.turn_id != receipt.first_turn_id:
                raise ValueError("Luna named-child route requires a no-history first task turn")
            if not expected_turn_id:
                raise ValueError("Luna named-child route requires an expected current turn")
            if receipt.turn_id != expected_turn_id:
                raise ValueError(
                    "Luna child turn binding mismatch: "
                    f"expected={expected_turn_id} actual={receipt.turn_id}"
                )
            if not expected_first_turn_id:
                raise ValueError("Luna named-child route requires an expected first turn")
            if receipt.first_turn_id != expected_first_turn_id:
                raise ValueError(
                    "Luna first-turn binding mismatch: "
                    f"expected={expected_first_turn_id} actual={receipt.first_turn_id}"
                )
            if not receipt.route_dispatch_id:
                raise ValueError("Luna named-child route requires an exact route dispatch")
            if not expected_route_dispatch_id:
                raise ValueError("Luna named-child route requires an expected route dispatch")
            validate_route_dispatch_id(expected_route_dispatch_id)
            if receipt.route_dispatch_id != expected_route_dispatch_id:
                raise ValueError(
                    "Luna route dispatch mismatch: "
                    f"expected={expected_route_dispatch_id} actual={receipt.route_dispatch_id}"
                )
            if receipt.capsule_bytes is None or receipt.capsule_sha256 is None:
                raise ValueError("Luna named-child route requires exact capsule bytes")
        else:
            raise ValueError(f"unknown Luna route mode: {receipt.route_mode}")
    return expected


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    return value


def _user_message_bytes(event: dict[str, Any]) -> bytes | None:
    """Return one user message's one text body without joining content items."""

    if event.get("type") != "response_item":
        return None
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return None
    if payload.get("type") != "message" or payload.get("role") != "user":
        return None
    content = payload.get("content")
    if not isinstance(content, list) or len(content) != 1:
        return None
    item = content[0]
    if (
        not isinstance(item, dict)
        or item.get("type") not in {"input_text", "text"}
        or not isinstance(item.get("text"), str)
    ):
        return None
    return item["text"].encode("utf-8")


def _skip_envelope_whitespace(text: str, cursor: int) -> int:
    while cursor < len(text) and text[cursor] in " \t\r\n":
        cursor += 1
    return cursor


def _matches_supported_envelope(
    text: str,
    canonical_prompt: bytes,
    *,
    expected_source_thread_id: str | None,
) -> bool:
    """Match one exact source-thread/input delegation envelope.

    The envelope intentionally has no extensibility surface: only the two
    fields below, in this order, are accepted.  This prevents an instruction,
    metadata element, second input, or arbitrary prefix/suffix from becoming
    part of a route receipt.
    """

    if expected_source_thread_id is None or not isinstance(expected_source_thread_id, str):
        return False
    outer = text.strip(" \t\r\n")
    root_open = "<codex_delegation>"
    root_close = "</codex_delegation>"
    source_open = "<source_thread_id>"
    source_close = "</source_thread_id>"
    input_open = "<input>"
    input_close = "</input>"
    if not outer.startswith(root_open) or not outer.endswith(root_close):
        return False
    interior = outer[len(root_open) : -len(root_close)]
    cursor = _skip_envelope_whitespace(interior, 0)
    if not interior.startswith(source_open, cursor):
        return False
    source_start = cursor + len(source_open)
    source_end = interior.find(source_close, source_start)
    if source_end < 0:
        return False
    source = interior[source_start:source_end]
    if source != expected_source_thread_id:
        return False
    cursor = _skip_envelope_whitespace(interior, source_end + len(source_close))
    if not interior.startswith(input_open, cursor):
        return False
    body_start = cursor + len(input_open)
    body_end = interior.rfind(input_close)
    if body_end < body_start:
        return False
    if interior[body_end + len(input_close) :].strip(" \t\r\n"):
        return False
    body = interior[body_start:body_end]
    try:
        return body.encode("utf-8") == canonical_prompt
    except UnicodeEncodeError:
        return False


def _matches_canonical_user_message(
    event: dict[str, Any],
    canonical_prompt: bytes,
    *,
    expected_source_thread_id: str | None = None,
) -> bool:
    """Accept raw canonical bytes or one exact supported delegation envelope."""

    body = _user_message_bytes(event)
    if body is None:
        return False
    if body == canonical_prompt:
        return True
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return _matches_supported_envelope(
        text,
        canonical_prompt,
        expected_source_thread_id=expected_source_thread_id,
    )


def _has_exact_route_dispatch(
    text: str,
    route_dispatch_id: str,
    *,
    action_class: str,
    allow_legacy_luna: bool = False,
) -> bool:
    """Accept one exact marker, with read-only compatibility for old Luna receipts."""

    if not isinstance(text, str):
        return False
    try:
        validate_route_dispatch_id(route_dispatch_id)
    except ValueError:
        return False
    generic_count = text.count(ROUTE_DISPATCH_MARKER)
    legacy_count = text.count(LEGACY_ROUTE_DISPATCH_MARKER)
    if generic_count:
        if generic_count != 1 or legacy_count:
            return False
        marker = rf"{re.escape(ROUTE_DISPATCH_MARKER)}{re.escape(route_dispatch_id)}"
    elif allow_legacy_luna and action_class == "frozen_deterministic" and legacy_count == 1:
        marker = rf"{re.escape(LEGACY_ROUTE_DISPATCH_MARKER)}{re.escape(route_dispatch_id)}"
    else:
        return False
    return re.search(rf"(?m)^(?:{marker}|[ \t]*<input>{marker})$", text) is not None


def validate_route_dispatch_id(route_dispatch_id: str) -> str:
    """Validate the opaque ASCII token used to bind a same-thread dispatch."""

    if not isinstance(route_dispatch_id, str) or not _ROUTE_DISPATCH_ID_PATTERN.fullmatch(
        route_dispatch_id
    ):
        raise ValueError(
            "route dispatch id must be a non-empty ASCII token "
            "([A-Za-z0-9][A-Za-z0-9._:-]*)"
        )
    return route_dispatch_id


def _validate_route_prompt_any(
    prompt: str | bytes,
    route_dispatch_id: str,
    *,
    route_mode: str,
    action_class: str,
) -> None:
    """Fail closed unless *prompt* is one canonical route prompt.

    This is intentionally a pure check.  It does not read or write files and
    does not accept a marker buried in prose or in a capsule body.
    """

    route_dispatch_id = validate_route_dispatch_id(route_dispatch_id)
    if isinstance(prompt, bytes):
        try:
            prompt = prompt.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("same-thread prompt is not valid UTF-8") from exc
    if not isinstance(prompt, str):
        raise ValueError("same-thread prompt must be text or UTF-8 bytes")

    canonical_prefix = _route_prompt_preamble(route_mode, action_class)
    if LEGACY_ROUTE_DISPATCH_MARKER in prompt:
        raise ValueError("legacy Luna route dispatch marker is not accepted")
    marker = f"{ROUTE_DISPATCH_MARKER}{route_dispatch_id}"
    marker_count = prompt.count(ROUTE_DISPATCH_MARKER)
    if marker_count == 0:
        raise ValueError("same-thread prompt marker is absent")
    if marker_count > 1:
        raise ValueError("same-thread prompt marker is duplicated")
    if marker not in prompt:
        raise ValueError("same-thread prompt marker has the wrong route dispatch id")
    if not prompt.startswith(marker + "\n"):
        raise ValueError(
            "same-thread prompt marker must be the first standalone line"
        )
    canonical_prefix = marker + "\n" + canonical_prefix
    if not prompt.startswith(canonical_prefix):
        raise ValueError(
            "same-thread prompt observability preamble is missing or non-canonical"
        )


def validate_same_thread_prompt(
    prompt: str | bytes,
    route_dispatch_id: str,
    *,
    action_class: str,
) -> None:
    """Validate a public same-thread Sol prompt with an explicit action class."""

    if action_class not in SAME_THREAD_ACTION_CLASSES:
        raise ValueError(
            "same-thread prompt requires explicit bounded_engineering, real_carrier, or scientific_decision action_class"
        )
    _validate_route_prompt_any(
        prompt,
        route_dispatch_id,
        route_mode="same_thread",
        action_class=action_class,
    )


def _read_capsule(capsule_path: str | Path) -> tuple[bytes, str]:
    """Read one existing, real regular UTF-8 capsule without transforming it."""

    try:
        path = Path(capsule_path)
    except TypeError as exc:
        raise ValueError("capsule path must identify a regular file") from exc
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ValueError(f"capsule path cannot be inspected: {path}") from exc
    if not stat.S_ISREG(mode):
        raise ValueError("capsule path must be a regular, non-symlink file")
    if mode & 0o444 == 0 or not os.access(path, os.R_OK):
        raise ValueError("capsule file is not readable")
    try:
        capsule_bytes = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"capsule file is not readable: {path}") from exc
    try:
        capsule_text = capsule_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("capsule file is not valid UTF-8") from exc
    return capsule_bytes, capsule_text


def _build_route_prompt_bytes(
    route_dispatch_id: str,
    capsule_path: str | Path,
    *,
    route_mode: str,
    action_class: str,
) -> bytes:
    """Build the canonical stdout payload for one explicit route turn."""

    route_dispatch_id = validate_route_dispatch_id(route_dispatch_id)
    preamble = _route_prompt_preamble(route_mode, action_class)
    capsule_bytes, capsule_text = _read_capsule(capsule_path)
    if ROUTE_DISPATCH_MARKER in capsule_text or LEGACY_ROUTE_DISPATCH_MARKER in capsule_text:
        raise ValueError("capsule already contains a route dispatch marker")

    marker = f"{ROUTE_DISPATCH_MARKER}{route_dispatch_id}\n".encode("utf-8")
    prompt_bytes = marker + preamble.encode("utf-8") + capsule_bytes
    _validate_route_prompt_any(
        prompt_bytes,
        route_dispatch_id,
        route_mode=route_mode,
        action_class=action_class,
    )
    return prompt_bytes


def _build_same_thread_prompt_bytes(
    route_dispatch_id: str,
    capsule_path: str | Path,
    *,
    action_class: str,
) -> bytes:
    """Build one canonical same-thread Sol prompt."""

    return _build_route_prompt_bytes(
        route_dispatch_id,
        capsule_path,
        route_mode="same_thread",
        action_class=action_class,
    )


def build_named_child_prompt_bytes(
    route_dispatch_id: str,
    capsule_path: str | Path,
) -> bytes:
    """Build one canonical frozen deterministic Luna child prompt."""

    return _build_route_prompt_bytes(
        route_dispatch_id,
        capsule_path,
        route_mode="named_child",
        action_class="frozen_deterministic",
    )


def build_same_thread_prompt_bytes(
    route_dispatch_id: str,
    capsule_path: str | Path,
    *,
    action_class: str,
) -> bytes:
    """Build a public same-thread prompt for an explicit Sol action class."""

    if action_class not in SAME_THREAD_ACTION_CLASSES:
        raise ValueError(
            "same-thread prompt requires explicit bounded_engineering, real_carrier, or scientific_decision action_class"
        )
    return _build_same_thread_prompt_bytes(
        route_dispatch_id, capsule_path, action_class=action_class
    )


def build_same_thread_prompt(
    route_dispatch_id: str,
    capsule_path: str | Path,
    *,
    action_class: str,
) -> str:
    """Build the canonical same-thread route prompt while preserving capsule text."""

    return build_same_thread_prompt_bytes(
        route_dispatch_id, capsule_path, action_class=action_class
    ).decode("utf-8")


def load_rollout_receipt(
    rollout_path: Path,
    *,
    action_class: str,
    context_eligible: bool,
    protected_exposed: bool,
    decision_ambiguity: bool,
    route_mode: str = "named_child",
    expected_parent_thread_id: str | None = None,
    expected_thread_id: str | None = None,
    expected_turn_id: str | None = None,
    expected_first_turn_id: str | None = None,
    expected_route_dispatch_id: str | None = None,
    expected_source_thread_id: str | None = None,
    capsule_path: str | Path | None = None,
) -> RouteReceipt:
    """Read only durable routing fields; never trust worker prose."""

    if action_class not in ROUTES:
        raise ValueError(f"unknown action class: {action_class}")
    if route_mode not in {"named_child", "same_thread"}:
        raise ValueError(f"unknown route mode: {route_mode}")
    if route_mode == "same_thread":
        if action_class == "frozen_deterministic":
            raise ValueError(
                "same-thread frozen_deterministic route must fail before effects"
            )
        if action_class not in SAME_THREAD_ACTION_CLASSES:
            raise ValueError(
                "same-thread route requires explicit bounded_engineering, real_carrier, or scientific_decision action_class"
            )
        if expected_route_dispatch_id is None:
            raise ValueError("same-thread rollout load requires an expected route dispatch")
        if capsule_path is None:
            raise ValueError("same-thread rollout load requires --capsule-path")
        canonical_prompt = _build_same_thread_prompt_bytes(
            expected_route_dispatch_id,
            capsule_path,
            action_class=action_class,
        )
    else:
        if action_class != "frozen_deterministic":
            raise ValueError("named-child route is reserved for frozen_deterministic")
        if expected_route_dispatch_id is None:
            raise ValueError("Luna named-child route requires an expected route dispatch")
        if capsule_path is None:
            raise ValueError("Luna named-child route requires --capsule-path")
        canonical_prompt = build_named_child_prompt_bytes(
            expected_route_dispatch_id,
            capsule_path,
        )
    capsule_bytes: int | None = None
    capsule_sha256: str | None = None
    if capsule_path is not None:
        capsule_data, _ = _read_capsule(capsule_path)
        capsule_bytes = len(capsule_data)
        capsule_sha256 = hashlib.sha256(capsule_data).hexdigest()

    session_meta: dict[str, Any] | None = None
    turn_contexts: list[dict[str, Any]] = []
    user_messages: list[tuple[int, dict[str, Any], str | None]] = []
    with rollout_path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not any(
                marker in raw
                for marker in ('"session_meta"', '"turn_context"', '"response_item"')
            ):
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid routing metadata JSON at line {line_number}"
                ) from exc
            event = _object(event, f"event at line {line_number}")
            payload = _object(event.get("payload"), f"payload at line {line_number}")
            if event.get("type") == "session_meta":
                if session_meta is not None:
                    raise ValueError("rollout contains multiple session_meta records")
                session_meta = payload
            elif event.get("type") == "turn_context":
                turn_contexts.append(payload)
            elif event.get("type") == "response_item":
                if payload.get("type") != "message" or payload.get("role") != "user":
                    continue
                metadata = payload.get("internal_chat_message_metadata_passthrough")
                message_turn_id = (
                    metadata.get("turn_id") if isinstance(metadata, dict) else None
                )
                user_messages.append((line_number, event, message_turn_id))
    if session_meta is None or not turn_contexts:
        raise ValueError("rollout is missing session_meta or turn_context routing metadata")

    turn_context = turn_contexts[-1]
    model = turn_context.get("model")
    effort = turn_context.get("effort")
    turn_id = turn_context.get("turn_id")
    if not isinstance(model, str) or not model:
        raise ValueError("turn_context.model is missing")
    if not isinstance(effort, str) or not effort:
        raise ValueError("turn_context.effort is missing")
    if "context_eligible" in turn_context:
        if type(turn_context["context_eligible"]) is not bool:
            raise ValueError("turn_context.context_eligible is invalid")
        if turn_context["context_eligible"] != context_eligible:
            raise ValueError("turn_context.context_eligible does not match receipt")
    route_dispatch_id: str | None = None
    first_turn_id: str | None = None
    if route_mode == "same_thread":
        if not isinstance(turn_id, str) or not turn_id:
            raise ValueError("same-thread turn_context.turn_id is missing")
        matches = [
            line_number
            for line_number, event, message_turn_id in user_messages
            if message_turn_id == turn_id
            and _matches_canonical_user_message(
                event,
                canonical_prompt,
                expected_source_thread_id=expected_source_thread_id,
            )
        ]
        current_turn_messages = [
            line_number
            for line_number, _event, message_turn_id in user_messages
            if message_turn_id == turn_id
        ]
        if len(current_turn_messages) != 1 or len(matches) != 1:
            raise ValueError("same-thread route dispatch marker is missing or ambiguous")
        route_dispatch_id = expected_route_dispatch_id
    else:
        if len(turn_contexts) != 1 or len(user_messages) != 1:
            raise ValueError(
                "Luna named-child route requires a no-history first task turn"
            )
        if not expected_turn_id or not expected_first_turn_id:
            raise ValueError(
                "Luna named-child route requires expected current and first turns"
            )
        if not isinstance(turn_id, str) or not turn_id:
            raise ValueError("Luna named-child turn_context.turn_id is missing")
        first_turn_id = turn_context.get("first_turn_id", turn_id)
        if not isinstance(first_turn_id, str) or not first_turn_id:
            raise ValueError("Luna named-child first turn identity is missing")
        if first_turn_id != turn_id:
            raise ValueError("Luna named-child route requires current and first turn to match")
        if turn_id != expected_turn_id:
            raise ValueError("Luna named-child turn binding mismatch")
        if first_turn_id != expected_first_turn_id:
            raise ValueError("Luna named-child first-turn binding mismatch")
        if "is_first_turn" in turn_context and turn_context["is_first_turn"] is not True:
            raise ValueError("Luna named-child turn is not marked as first")
        if "history_count" in turn_context:
            history_count = turn_context["history_count"]
            if type(history_count) is not int or history_count != 0:
                raise ValueError("Luna named-child route requires zero history")
        if "previous_turn_id" in turn_context and turn_context["previous_turn_id"] is not None:
            raise ValueError("Luna named-child route has a previous turn")
        if type(turn_context.get("context_eligible")) is not bool:
            raise ValueError("Luna named-child route requires durable context eligibility")
        if capsule_bytes is None or capsule_sha256 is None:
            raise ValueError("Luna named-child route requires exact capsule bytes")
        if (
            "capsule_bytes" in turn_context
            and turn_context.get("capsule_bytes") != capsule_bytes
        ):
            raise ValueError("Luna named-child capsule byte count mismatch")
        if (
            "capsule_sha256" in turn_context
            and turn_context.get("capsule_sha256") != capsule_sha256
        ):
            raise ValueError("Luna named-child capsule digest mismatch")
        metadata_dispatch_id = turn_context.get("route_dispatch_id")
        if (
            metadata_dispatch_id is not None
            and metadata_dispatch_id != expected_route_dispatch_id
        ):
            raise ValueError("Luna named-child route dispatch metadata mismatch")
        matches = [
            line_number
            for line_number, event, message_turn_id in user_messages
            if message_turn_id == turn_id
            and _matches_canonical_user_message(
                event,
                canonical_prompt,
                expected_source_thread_id=(
                    expected_source_thread_id or expected_parent_thread_id
                ),
            )
        ]
        if len(matches) != 1:
            raise ValueError("Luna named-child canonical capsule message is missing or ambiguous")
        route_dispatch_id = expected_route_dispatch_id
    agent_role = session_meta.get("agent_role")
    parent_thread_id = session_meta.get("parent_thread_id")
    thread_id = session_meta.get("id")
    if route_mode == "named_child":
        if agent_role != "luna_worker":
            raise ValueError("Luna named-child route requires agent_role=luna_worker")
        if expected_parent_thread_id is None:
            raise ValueError("Luna named-child route requires an expected parent thread")
        if parent_thread_id != expected_parent_thread_id:
            raise ValueError("Luna parent binding mismatch")
        if expected_thread_id is None:
            raise ValueError("Luna named-child route requires an expected child thread")
        if thread_id != expected_thread_id:
            raise ValueError("Luna child binding mismatch")
    elif expected_source_thread_id is not None and not isinstance(expected_source_thread_id, str):
        raise ValueError("expected source thread identity is invalid")
    return RouteReceipt(
        action_class=action_class,
        model=model,
        effort=effort,
        context_eligible=context_eligible,
        protected_exposed=protected_exposed,
        decision_ambiguity=decision_ambiguity,
        receipt_source="durable_rollout",
        route_mode=route_mode,
        agent_role=agent_role,
        parent_thread_id=parent_thread_id,
        multi_agent_version=session_meta.get("multi_agent_version"),
        thread_id=thread_id,
        turn_id=turn_id if isinstance(turn_id, str) else None,
        first_turn_id=first_turn_id,
        capsule_bytes=capsule_bytes,
        capsule_sha256=capsule_sha256,
        route_dispatch_id=route_dispatch_id,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action-class", choices=tuple(ROUTES))
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--rollout-path")
    parser.add_argument(
        "--build-same-thread-prompt",
        dest="build_same_thread_prompt",
        action="store_true",
        help="write the canonical same-thread prompt to stdout",
    )
    parser.add_argument(
        "--build-route-prompt",
        dest="build_route_prompt",
        action="store_true",
        help="write one canonical route prompt to stdout",
    )
    parser.add_argument(
        "--route-dispatch-id",
        dest="route_dispatch_id",
        help="opaque ID for --build-same-thread-prompt",
    )
    parser.add_argument(
        "--capsule-path",
        dest="capsule_path",
        help="existing UTF-8 capsule file for --build-same-thread-prompt",
    )
    parser.add_argument("--route-mode", choices=("named_child", "same_thread"))
    parser.add_argument("--expected-parent-thread-id")
    parser.add_argument("--expected-thread-id")
    parser.add_argument("--expected-turn-id")
    parser.add_argument("--expected-first-turn-id")
    parser.add_argument("--expected-route-dispatch-id")
    parser.add_argument("--expected-source-thread-id")
    parser.add_argument("--context-eligible", action="store_true")
    parser.add_argument("--protected-exposed", action="store_true")
    parser.add_argument("--decision-ambiguity", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.action_class is None:
            raise ValueError("--action-class is required for every route operation")
        if args.build_same_thread_prompt and args.build_route_prompt:
            raise ValueError(
                "--build-same-thread-prompt and --build-route-prompt are mutually exclusive"
            )
        if args.build_same_thread_prompt or args.build_route_prompt:
            if args.model is not None or args.effort is not None:
                raise ValueError(
                    "same-thread prompt mode cannot be combined with receipt arguments"
                )
            if args.rollout_path is not None:
                raise ValueError(
                    "same-thread prompt mode cannot be combined with --rollout-path"
                )
            if args.route_dispatch_id is None:
                raise ValueError(
                    "same-thread prompt mode requires --route-dispatch-id"
                )
            if args.capsule_path is None:
                raise ValueError("same-thread prompt mode requires --capsule-path")
            if args.build_same_thread_prompt and args.route_mode not in {
                None,
                "same_thread",
            }:
                raise ValueError(
                    "--build-same-thread-prompt is a same_thread compatibility alias"
                )
            if args.build_route_prompt and args.route_mode is None:
                raise ValueError("--build-route-prompt requires --route-mode")
            build_route_mode = (
                args.route_mode if args.build_route_prompt else "same_thread"
            )
            if build_route_mode == "same_thread":
                if args.action_class not in SAME_THREAD_ACTION_CLASSES:
                    raise ValueError(
                        "same-thread prompt requires explicit bounded_engineering, real_carrier, or scientific_decision action_class"
                    )
            elif args.action_class != "frozen_deterministic":
                raise ValueError(
                    "named-child prompt requires frozen_deterministic action_class"
                )
            if build_route_mode == "same_thread":
                prompt_bytes = _build_same_thread_prompt_bytes(
                    args.route_dispatch_id,
                    args.capsule_path,
                    action_class=args.action_class,
                )
            else:
                prompt_bytes = build_named_child_prompt_bytes(
                    args.route_dispatch_id,
                    args.capsule_path,
                )
            sys.stdout.buffer.write(prompt_bytes)
            return 0
        if args.route_dispatch_id is not None:
            raise ValueError("--route-dispatch-id requires same-thread prompt mode")
        route_mode = args.route_mode or "named_child"
        if args.rollout_path:
            if args.model is not None or args.effort is not None:
                raise ValueError("rollout metadata and direct model/effort are mutually exclusive")
            receipt = load_rollout_receipt(
                Path(args.rollout_path),
                action_class=args.action_class,
                context_eligible=args.context_eligible,
                protected_exposed=args.protected_exposed,
                decision_ambiguity=args.decision_ambiguity,
                route_mode=route_mode,
                expected_parent_thread_id=args.expected_parent_thread_id,
                expected_thread_id=args.expected_thread_id,
                expected_turn_id=args.expected_turn_id,
                expected_first_turn_id=args.expected_first_turn_id,
                expected_route_dispatch_id=args.expected_route_dispatch_id,
                expected_source_thread_id=args.expected_source_thread_id,
                capsule_path=args.capsule_path,
            )
        else:
            if not args.model or not args.effort:
                raise ValueError("direct receipt requires both model and effort")
            receipt = RouteReceipt(
                action_class=args.action_class,
                model=args.model,
                effort=args.effort,
                context_eligible=args.context_eligible,
                protected_exposed=args.protected_exposed,
                decision_ambiguity=args.decision_ambiguity,
                route_mode=route_mode,
            )
        model, effort = validate_receipt(
            receipt,
            expected_parent_thread_id=args.expected_parent_thread_id,
            expected_thread_id=args.expected_thread_id,
            expected_turn_id=args.expected_turn_id,
            expected_first_turn_id=args.expected_first_turn_id,
            expected_route_dispatch_id=args.expected_route_dispatch_id,
        )
    except (OSError, ValueError) as exc:
        print(f"FAIL_MODEL_ROUTE: {exc}")
        return 1
    suffix = ""
    if receipt.route_mode == "same_thread":
        suffix = (
            " route_mode=same_thread"
            f" thread_id={receipt.thread_id}"
            f" turn_id={receipt.turn_id}"
            f" route_dispatch_id={receipt.route_dispatch_id}"
        )
    elif receipt.agent_role is not None:
        suffix = (
            " route_mode=named_child"
            f" agent_role={receipt.agent_role}"
            f" parent_thread_id={receipt.parent_thread_id}"
            f" multi_agent_version={receipt.multi_agent_version}"
        )
    print(f"PASS_MODEL_ROUTE: {model}/{effort}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
