#!/usr/bin/env python3
"""Validate one ephemeral runtime model-route receipt without writing state."""

from __future__ import annotations

import argparse
import json
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
    agent_role: str | None = None
    parent_thread_id: str | None = None
    multi_agent_version: str | None = None


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
        if receipt.agent_role != "luna_worker":
            raise ValueError("Luna route requires agent_role=luna_worker")
        if receipt.multi_agent_version != "v1":
            raise ValueError("Luna route requires multi_agent_version=v1")
        if not expected_parent_thread_id:
            raise ValueError("Luna route requires an independently expected parent thread")
        if receipt.parent_thread_id != expected_parent_thread_id:
            raise ValueError(
                "Luna parent binding mismatch: "
                f"expected={expected_parent_thread_id} actual={receipt.parent_thread_id}"
            )
    return expected


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    return value


def load_rollout_receipt(
    rollout_path: Path,
    *,
    action_class: str,
    context_eligible: bool,
    protected_exposed: bool,
    decision_ambiguity: bool,
) -> RouteReceipt:
    """Read only durable routing fields; never trust worker prose."""

    session_meta: dict[str, Any] | None = None
    turn_context: dict[str, Any] | None = None
    with rollout_path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if '"session_meta"' not in raw and '"turn_context"' not in raw:
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
    if session_meta is None or turn_context is None:
        raise ValueError("rollout is missing session_meta or turn_context routing metadata")

    model = turn_context.get("model")
    effort = turn_context.get("effort")
    if not isinstance(model, str) or not model:
        raise ValueError("turn_context.model is missing")
    if not isinstance(effort, str) or not effort:
        raise ValueError("turn_context.effort is missing")
    return RouteReceipt(
        action_class=action_class,
        model=model,
        effort=effort,
        context_eligible=context_eligible,
        protected_exposed=protected_exposed,
        decision_ambiguity=decision_ambiguity,
        receipt_source="durable_rollout",
        agent_role=session_meta.get("agent_role"),
        parent_thread_id=session_meta.get("parent_thread_id"),
        multi_agent_version=session_meta.get("multi_agent_version"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action-class", required=True, choices=tuple(ROUTES))
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--rollout-path")
    parser.add_argument("--expected-parent-thread-id")
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
            )
        model, effort = validate_receipt(
            receipt,
            expected_parent_thread_id=args.expected_parent_thread_id,
        )
    except (OSError, ValueError) as exc:
        print(f"FAIL_MODEL_ROUTE: {exc}")
        return 1
    suffix = ""
    if receipt.agent_role is not None:
        suffix = (
            f" agent_role={receipt.agent_role}"
            f" parent_thread_id={receipt.parent_thread_id}"
            f" multi_agent_version={receipt.multi_agent_version}"
        )
    print(f"PASS_MODEL_ROUTE: {model}/{effort}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
