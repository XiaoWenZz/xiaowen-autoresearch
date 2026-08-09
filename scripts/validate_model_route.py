#!/usr/bin/env python3
"""Validate one ephemeral runtime model-route receipt without writing state."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROUTES = {
    "frozen_deterministic": ("gpt-5.6-luna", "max"),
    "bounded_engineering": ("gpt-5.6-sol", "high"),
    "real_carrier": ("gpt-5.6-sol", "xhigh"),
    "scientific_decision": ("gpt-5.6-sol", "max"),
}


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
    if receipt.action_class == "frozen_deterministic":
        if receipt.receipt_source != "durable_rollout":
            raise ValueError("Luna route requires durable rollout metadata")
        if receipt.route_mode == "named_child":
            if receipt.agent_role != "luna_worker":
                raise ValueError("Luna named-child route requires agent_role=luna_worker")
            if receipt.multi_agent_version != "v1":
                raise ValueError("Luna named-child route requires multi_agent_version=v1")
            if not expected_parent_thread_id:
                raise ValueError(
                    "Luna named-child route requires an independently expected parent thread"
                )
            if receipt.parent_thread_id != expected_parent_thread_id:
                raise ValueError(
                    "Luna parent binding mismatch: "
                    f"expected={expected_parent_thread_id} actual={receipt.parent_thread_id}"
                )
        elif receipt.route_mode == "same_thread":
            if not expected_thread_id:
                raise ValueError("Luna same-thread route requires an expected thread")
            if receipt.thread_id != expected_thread_id:
                raise ValueError(
                    "Luna thread binding mismatch: "
                    f"expected={expected_thread_id} actual={receipt.thread_id}"
                )
            if not receipt.turn_id:
                raise ValueError("Luna same-thread route is missing durable turn identity")
            if not expected_route_dispatch_id:
                raise ValueError("Luna same-thread route requires an expected route dispatch")
            if receipt.route_dispatch_id != expected_route_dispatch_id:
                raise ValueError(
                    "Luna route dispatch mismatch: "
                    f"expected={expected_route_dispatch_id} actual={receipt.route_dispatch_id}"
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


def _has_exact_route_dispatch(text: str, route_dispatch_id: str) -> bool:
    marker = rf"LUNA_ROUTE_DISPATCH_ID={re.escape(route_dispatch_id)}"
    return re.search(
        rf"(?m)^(?:{marker}|[ \t]*<input>{marker})$", text
    ) is not None


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
            and _has_exact_route_dispatch(text, expected_route_dispatch_id)
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
    parser.add_argument("--action-class", required=True, choices=tuple(ROUTES))
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--rollout-path")
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
