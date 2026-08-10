#!/usr/bin/env python3
"""Validate one ephemeral runtime model-route receipt without writing state."""

from __future__ import annotations

import argparse
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


ROUTE_DISPATCH_MARKER = "MODEL_ROUTE_DISPATCH_ID="
LEGACY_ROUTE_DISPATCH_MARKER = "LUNA_ROUTE_DISPATCH_ID="
_ROUTE_DISPATCH_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*\Z")


def _same_thread_prompt_preamble(action_class: str) -> str:
    try:
        model, effort = ROUTES[action_class]
    except KeyError as exc:
        raise ValueError(f"unknown action class: {action_class}") from exc
    return f"PASS_MODEL_ROUTE: {model}/{effort}\nawait-successor-activation\n"


SAME_THREAD_PROMPT_PREAMBLE = _same_thread_prompt_preamble(
    "frozen_deterministic"
)


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
    route_dispatch_id: str | None = None


def expected_route(receipt: RouteReceipt) -> tuple[str, str]:
    if receipt.action_class not in ROUTES:
        raise ValueError(f"unknown action class: {receipt.action_class}")
    if receipt.protected_exposed and receipt.action_class == "frozen_deterministic":
        raise ValueError("protected-exposed work cannot be routed to Luna")
    if receipt.decision_ambiguity:
        return ROUTES["scientific_decision"]
    if receipt.action_class == "frozen_deterministic" and not receipt.context_eligible:
        raise ValueError("Luna requires a frozen oracle and eligible visible context")
    return ROUTES[receipt.action_class]


def validate_receipt(
    receipt: RouteReceipt,
    *,
    expected_parent_thread_id: str | None = None,
    expected_thread_id: str | None = None,
    expected_route_dispatch_id: str | None = None,
) -> tuple[str, str]:
    expected = expected_route(receipt)
    actual = (receipt.model, receipt.effort)
    if actual != expected:
        raise ValueError(
            "runtime route mismatch: "
            f"expected={expected[0]}/{expected[1]} actual={actual[0]}/{actual[1]}"
        )
    if receipt.route_mode not in {"named_child", "same_thread"}:
        raise ValueError(f"unknown route mode: {receipt.route_mode}")
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
        if not expected_route_dispatch_id:
            raise ValueError("same-thread route requires an expected route dispatch")
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
        else:
            raise ValueError(f"unknown Luna route mode: {receipt.route_mode}")
    return expected


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    return value


def _user_message_text(event: dict[str, Any]) -> str:
    if event.get("type") != "response_item":
        return ""
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return ""
    if payload.get("type") != "message" or payload.get("role") != "user":
        return ""
    content = payload.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        item["text"]
        for item in content
        if isinstance(item, dict)
        and item.get("type") in {"input_text", "text"}
        and isinstance(item.get("text"), str)
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


def validate_same_thread_prompt(
    prompt: str | bytes,
    route_dispatch_id: str,
    *,
    action_class: str = "frozen_deterministic",
) -> None:
    """Fail closed unless *prompt* has one canonical first-line dispatch marker.

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

    canonical_prefix = _same_thread_prompt_preamble(action_class)
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


def build_same_thread_prompt_bytes(
    route_dispatch_id: str,
    capsule_path: str | Path,
    *,
    action_class: str = "frozen_deterministic",
) -> bytes:
    """Build the canonical stdout payload for one same-thread route turn."""

    route_dispatch_id = validate_route_dispatch_id(route_dispatch_id)
    preamble = _same_thread_prompt_preamble(action_class)
    capsule_bytes, capsule_text = _read_capsule(capsule_path)
    if ROUTE_DISPATCH_MARKER in capsule_text or LEGACY_ROUTE_DISPATCH_MARKER in capsule_text:
        raise ValueError("capsule already contains a route dispatch marker")

    marker = f"{ROUTE_DISPATCH_MARKER}{route_dispatch_id}\n".encode("utf-8")
    prompt_bytes = marker + preamble.encode("utf-8") + capsule_bytes
    validate_same_thread_prompt(
        prompt_bytes, route_dispatch_id, action_class=action_class
    )
    return prompt_bytes


def build_same_thread_prompt(
    route_dispatch_id: str,
    capsule_path: str | Path,
    *,
    action_class: str = "frozen_deterministic",
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
    expected_route_dispatch_id: str | None = None,
) -> RouteReceipt:
    """Read only durable routing fields; never trust worker prose."""

    session_meta: dict[str, Any] | None = None
    turn_context: dict[str, Any] | None = None
    user_messages: list[tuple[int, str, str | None]] = []
    with rollout_path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not any(
                marker in raw
                for marker in ('"session_meta"', '"turn_context"', '"response_item"')
            ):
                continue
            if '"response_item"' in raw and (
                route_mode != "same_thread"
                or not expected_route_dispatch_id
                or expected_route_dispatch_id not in raw
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
                turn_context = payload
            elif event.get("type") == "response_item":
                text = _user_message_text(event)
                if text:
                    metadata = payload.get("internal_chat_message_metadata_passthrough")
                    message_turn_id = (
                        metadata.get("turn_id") if isinstance(metadata, dict) else None
                    )
                    user_messages.append((line_number, text, message_turn_id))
    if session_meta is None or turn_context is None:
        raise ValueError("rollout is missing session_meta or turn_context routing metadata")

    model = turn_context.get("model")
    effort = turn_context.get("effort")
    turn_id = turn_context.get("turn_id")
    if not isinstance(model, str) or not model:
        raise ValueError("turn_context.model is missing")
    if not isinstance(effort, str) or not effort:
        raise ValueError("turn_context.effort is missing")
    route_dispatch_id: str | None = None
    if route_mode == "same_thread":
        if not expected_route_dispatch_id:
            raise ValueError("same-thread rollout load requires an expected route dispatch")
        if not isinstance(turn_id, str) or not turn_id:
            raise ValueError("same-thread turn_context.turn_id is missing")
        matches = [
            line_number
            for line_number, text, message_turn_id in user_messages
            if message_turn_id == turn_id
            and _has_exact_route_dispatch(
                text,
                expected_route_dispatch_id,
                action_class=action_class,
                allow_legacy_luna=(
                    action_class == "frozen_deterministic"
                    and not decision_ambiguity
                    and not protected_exposed
                ),
            )
        ]
        if len(matches) != 1:
            raise ValueError("same-thread route dispatch marker is missing or ambiguous")
        route_dispatch_id = expected_route_dispatch_id
    return RouteReceipt(
        action_class=action_class,
        model=model,
        effort=effort,
        context_eligible=context_eligible,
        protected_exposed=protected_exposed,
        decision_ambiguity=decision_ambiguity,
        receipt_source="durable_rollout",
        route_mode=route_mode,
        agent_role=session_meta.get("agent_role"),
        parent_thread_id=session_meta.get("parent_thread_id"),
        multi_agent_version=session_meta.get("multi_agent_version"),
        thread_id=session_meta.get("id"),
        turn_id=turn_id if isinstance(turn_id, str) else None,
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
        "--route-dispatch-id",
        dest="route_dispatch_id",
        help="opaque ID for --build-same-thread-prompt",
    )
    parser.add_argument(
        "--capsule-path",
        dest="capsule_path",
        help="existing UTF-8 capsule file for --build-same-thread-prompt",
    )
    parser.add_argument(
        "--route-mode", choices=("named_child", "same_thread"), default="named_child"
    )
    parser.add_argument("--expected-parent-thread-id")
    parser.add_argument("--expected-thread-id")
    parser.add_argument("--expected-route-dispatch-id")
    parser.add_argument("--context-eligible", action="store_true")
    parser.add_argument("--protected-exposed", action="store_true")
    parser.add_argument("--decision-ambiguity", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.build_same_thread_prompt:
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
            prompt_bytes = build_same_thread_prompt_bytes(
                args.route_dispatch_id,
                args.capsule_path,
                action_class=args.action_class or "frozen_deterministic",
            )
            sys.stdout.buffer.write(prompt_bytes)
            return 0
        if args.action_class is None:
            raise ValueError("--action-class is required for receipt validation")
        if args.route_dispatch_id is not None or args.capsule_path is not None:
            raise ValueError(
                "--route-dispatch-id and --capsule-path require same-thread prompt mode"
            )
        if args.rollout_path:
            if args.model is not None or args.effort is not None:
                raise ValueError("rollout metadata and direct model/effort are mutually exclusive")
            receipt = load_rollout_receipt(
                Path(args.rollout_path),
                action_class=args.action_class,
                context_eligible=args.context_eligible,
                protected_exposed=args.protected_exposed,
                decision_ambiguity=args.decision_ambiguity,
                route_mode=args.route_mode,
                expected_route_dispatch_id=args.expected_route_dispatch_id,
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
                route_mode=args.route_mode,
            )
        model, effort = validate_receipt(
            receipt,
            expected_parent_thread_id=args.expected_parent_thread_id,
            expected_thread_id=args.expected_thread_id,
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
