#!/usr/bin/env python3
"""Validate one compact global research-lane snapshot.

This helper is deliberately small. It does not schedule work, inspect remote
state, or decide science. It only rejects the controller states that previously
allowed a route-local terminal to strand the global zero-GPU or Pro lanes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IDLE_PROOF_CATEGORIES = {
    "current_route",
    "gpu_queue_prerequisites",
    "partial_audits",
    "new_problem_opportunity_search",
}
BACKLOG_STATES = {"admitted", "blocked", "not_decision_changing"}
OPPORTUNITY_STATES = {"active", "admitted", "blocked", "budget_exhausted"}
NEXT_ACTIONS = {"dispatch_next", "validated_idle", "queued", "explicit_hold"}
QUEUE_AUTHORITY_KINDS = {
    "validated_experiment_record",
    "durable_terminal_packet",
    "frozen_prospective_contract",
}
PRO_LIVE_STATES = {"submitted", "generating", "cooldown_held"}
PRO_DUE_HANDLING = {"in_progress", "dispatcher_busy", "cooldown_held"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("top-level value must be an object")
    return value


def require_list(record: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = record.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be a list")
        return []
    return value


def task_id(value: Any) -> str | None:
    if isinstance(value, dict):
        candidate = value.get("task_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def parse_utc(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty UTC timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be an ISO-8601 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed.astimezone(timezone.utc)


def validate_gpu_queue_authority(
    item: Any, index: int, errors: list[str]
) -> None:
    prefix = f"gpu_queue[{index}]"
    if not isinstance(item, dict):
        errors.append(f"{prefix} must be an object")
        return
    for key in ("task_id", "owner_thread_id", "launch_prerequisite"):
        if not isinstance(item.get(key), str) or not item[key].strip():
            errors.append(f"{prefix} requires non-empty {key}")

    authority = item.get("latest_authority")
    if not isinstance(authority, dict):
        errors.append(f"{prefix} requires latest_authority")
        return
    if authority.get("checked_against_latest_terminal") is not True:
        errors.append(
            f"{prefix}.latest_authority must be checked against the latest terminal"
        )
    if authority.get("source_kind") not in QUEUE_AUTHORITY_KINDS:
        errors.append(
            f"{prefix}.latest_authority.source_kind must be one of "
            f"{sorted(QUEUE_AUTHORITY_KINDS)}"
        )
    for key in ("authority_id", "evidence_path"):
        if not isinstance(authority.get(key), str) or not authority[key].strip():
            errors.append(f"{prefix}.latest_authority requires non-empty {key}")
    if authority.get("queue_disposition") != "queue_gpu":
        errors.append(
            f"{prefix}.latest_authority.queue_disposition must be queue_gpu"
        )


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not isinstance(record.get("controller_thread_id"), str):
        errors.append("controller_thread_id must be a string")

    gpu_queue = require_list(record, "gpu_queue", errors)
    zero_backlog = require_list(record, "zero_gpu_backlog", errors)
    result_queue = require_list(record, "result_analysis_queue", errors)

    for index, item in enumerate(gpu_queue):
        validate_gpu_queue_authority(item, index, errors)

    for index, item in enumerate(zero_backlog):
        if not isinstance(item, dict):
            errors.append(f"zero_gpu_backlog[{index}] must be an object")
            continue
        if task_id(item) is None:
            errors.append(f"zero_gpu_backlog[{index}] requires task_id")
        state = item.get("status")
        if state not in BACKLOG_STATES:
            errors.append(
                f"zero_gpu_backlog[{index}].status must be one of "
                f"{sorted(BACKLOG_STATES)}"
            )
        if state == "blocked" and not item.get("reopening_fact"):
            errors.append(
                f"zero_gpu_backlog[{index}] blocked item requires reopening_fact"
            )
        if state == "admitted" and item.get(
            "useful_under_all_pending_gpu_outcomes"
        ) is not True:
            errors.append(
                f"zero_gpu_backlog[{index}] admitted item must be useful under "
                "all pending GPU outcomes"
            )

    opportunity = record.get("opportunity_search")
    if not isinstance(opportunity, dict):
        errors.append("opportunity_search must be an object")
        opportunity = {}
    opportunity_state = opportunity.get("status")
    if opportunity_state not in OPPORTUNITY_STATES:
        errors.append(
            f"opportunity_search.status must be one of {sorted(OPPORTUNITY_STATES)}"
        )
    if opportunity_state == "blocked" and not opportunity.get("reopening_fact"):
        errors.append("blocked opportunity_search requires reopening_fact")
    if opportunity_state in {"active", "admitted"} and not opportunity.get("task_id"):
        errors.append(f"{opportunity_state} opportunity_search requires task_id")

    zero_running = record.get("zero_gpu_running")
    zero_is_idle = zero_running == "explicit_idle"
    if not zero_is_idle:
        if not isinstance(zero_running, dict):
            errors.append(
                "zero_gpu_running must be an active task object or explicit_idle"
            )
        elif task_id(zero_running) is None:
            errors.append("active zero_gpu_running requires task_id")

    admitted_backlog = [
        item
        for item in zero_backlog
        if isinstance(item, dict) and item.get("status") == "admitted"
    ]

    if zero_is_idle:
        if admitted_backlog:
            errors.append("explicit_idle is invalid while admitted zero-GPU work exists")
        if opportunity_state not in {"blocked", "budget_exhausted"}:
            errors.append(
                "explicit_idle requires Opportunity Search to be blocked with one "
                "reopening fact or budget_exhausted"
            )
        idle_proof = record.get("idle_proof")
        if not isinstance(idle_proof, dict):
            errors.append("explicit_idle requires idle_proof")
        else:
            categories = idle_proof.get("evaluated_categories")
            if not isinstance(categories, list) or set(categories) != IDLE_PROOF_CATEGORIES:
                errors.append(
                    "idle_proof.evaluated_categories must exactly cover "
                    f"{sorted(IDLE_PROOF_CATEGORIES)}"
                )
            if not idle_proof.get("reason"):
                errors.append("idle_proof requires reason")
            if not idle_proof.get("reopening_fact"):
                errors.append("idle_proof requires reopening_fact")
    elif record.get("idle_proof") not in (None, {}):
        errors.append("idle_proof must be absent when zero-GPU work is running")

    ready_analysis = [
        item
        for item in result_queue
        if isinstance(item, dict) and item.get("status") == "ready"
    ]
    if ready_analysis:
        for index, item in enumerate(result_queue):
            if not isinstance(item, dict) or item.get("status") != "ready":
                continue
            authority = item.get("terminal_authority")
            if not isinstance(authority, dict):
                errors.append(
                    f"result_analysis_queue[{index}] ready item requires "
                    "terminal_authority"
                )
                continue
            for key in ("terminal_id", "evidence_path"):
                if not isinstance(authority.get(key), str) or not authority[key].strip():
                    errors.append(
                        f"result_analysis_queue[{index}].terminal_authority "
                        f"requires non-empty {key}"
                    )
        expected = task_id(ready_analysis[0])
        if expected is None:
            errors.append("ready result-analysis item requires task_id")
        elif task_id(zero_running) != expected:
            errors.append(
                "ready GPU result analysis must preempt ordinary zero-GPU work"
            )

    if (record.get("gpu_running") is not None or gpu_queue) and zero_is_idle:
        if opportunity_state not in {"blocked", "budget_exhausted"}:
            errors.append(
                "GPU running/queued never justifies zero-GPU idle; Opportunity Search "
                "must run, be admitted, or carry a precise block/exhaustion proof"
            )

    terminal = record.get("terminal_transaction")
    if not isinstance(terminal, dict):
        errors.append("terminal_transaction must be an object")
        terminal = {}
    callback_state = terminal.get("callback_state")
    if callback_state == "acknowledged":
        if terminal.get("portfolio_reconciled") is not True:
            errors.append(
                "acknowledged terminal requires portfolio_reconciled=true"
            )
        next_action = terminal.get("next_action")
        if not isinstance(next_action, dict):
            errors.append("acknowledged terminal requires next_action object")
        else:
            kind = next_action.get("kind")
            if kind not in NEXT_ACTIONS:
                errors.append(
                    f"next_action.kind must be one of {sorted(NEXT_ACTIONS)}"
                )
            if kind == "dispatch_next" and not next_action.get("task_id"):
                errors.append("dispatch_next requires task_id")
            if kind == "validated_idle" and not zero_is_idle:
                errors.append("validated_idle requires zero_gpu_running=explicit_idle")
        if terminal.get("watchdog_state") == "active":
            errors.append("acknowledged terminal cannot retain an active old watchdog")
        reconciled_at = parse_utc(
            terminal.get("portfolio_reconciled_at_utc"),
            "terminal_transaction.portfolio_reconciled_at_utc",
            errors,
        )
        acknowledged_at = parse_utc(
            terminal.get("acknowledged_at_utc"),
            "terminal_transaction.acknowledged_at_utc",
            errors,
        )
        if (
            reconciled_at is not None
            and acknowledged_at is not None
            and acknowledged_at < reconciled_at
        ):
            errors.append(
                "final terminal ACK must follow durable portfolio reconciliation"
            )
        if terminal.get("delivery_intent_durable") is not True:
            errors.append(
                "acknowledged terminal requires delivery_intent_durable=true"
            )

    pro = record.get("pro_advisory_lane")
    if not isinstance(pro, dict):
        errors.append("pro_advisory_lane must be an object")
        pro = {}
    live_jobs = pro.get("live_jobs")
    queued_reviews = pro.get("queue")
    response_ready = pro.get("response_ready")
    if not isinstance(live_jobs, list):
        errors.append("pro_advisory_lane.live_jobs must be a list")
        live_jobs = []
    if not isinstance(queued_reviews, list):
        errors.append("pro_advisory_lane.queue must be a list")
        queued_reviews = []
    if not isinstance(response_ready, list):
        errors.append("pro_advisory_lane.response_ready must be a list")
        response_ready = []
    observed_at = parse_utc(
        record.get("observed_at_utc"),
        "observed_at_utc",
        errors,
    )
    for index, item in enumerate(live_jobs):
        prefix = f"pro_advisory_lane.live_jobs[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in (
            "job_id",
            "decision",
            "polling_owner",
            "completion_callback_thread_id",
        ):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"{prefix} requires non-empty {key}")
        if item.get("completion_callback_configured") is not True:
            errors.append(
                f"{prefix} requires completion_callback_configured=true"
            )
        status = item.get("status")
        if status not in PRO_LIVE_STATES:
            errors.append(
                f"{prefix}.status must be one of {sorted(PRO_LIVE_STATES)}"
            )
        parse_utc(item.get("submitted_at_utc"), f"{prefix}.submitted_at_utc", errors)
        due_at = parse_utc(
            item.get("next_check_due_at_utc"),
            f"{prefix}.next_check_due_at_utc",
            errors,
        )
        if (
            status in {"submitted", "generating"}
            and observed_at is not None
            and due_at is not None
            and observed_at >= due_at
            and item.get("due_handling") not in PRO_DUE_HANDLING
        ):
            errors.append(
                f"{prefix} is due; set due_handling to one of "
                f"{sorted(PRO_DUE_HANDLING)} without resetting its due time"
            )
    if response_ready:
        first = response_ready[0]
        if not isinstance(first, dict) or not isinstance(first.get("job_id"), str):
            errors.append(
                "pro_advisory_lane.response_ready[0] requires job_id"
            )
        elif pro.get("adjudicating_job_id") != first["job_id"]:
            errors.append(
                "oldest response_ready Pro job must be claimed for adjudication"
            )
        for index, item in enumerate(response_ready):
            prefix = f"pro_advisory_lane.response_ready[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for key in ("job_id", "decision", "owner_thread_id", "response_artifact"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append(f"{prefix} requires non-empty {key}")
            parse_utc(
                item.get("completed_at_utc"),
                f"{prefix}.completed_at_utc",
                errors,
            )
    ready_reviews = [
        item
        for item in queued_reviews
        if isinstance(item, dict) and item.get("status") == "decision_ready"
    ]
    blocked = pro.get("dispatcher_blocked") is True or pro.get("cooldown_held") is True
    if ready_reviews and len(live_jobs) < 3 and not blocked:
        errors.append(
            "decision-ready Pro review must be submitted while a Pro slot is free"
        )
    if (
        not live_jobs
        and not queued_reviews
        and not response_ready
        and not pro.get("explicit_idle_reason")
    ):
        errors.append(
            "empty Pro lane requires explicit_idle_reason; do not silently leave it idle"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate global GPU, zero-GPU, result-analysis and Pro lanes."
    )
    parser.add_argument("record", type=Path)
    args = parser.parse_args()

    try:
        record = load_json(args.record)
    except ValueError as exc:
        print(f"FAIL_RESEARCH_LANES: {exc}")
        return 2

    errors = validate(record)
    if errors:
        print("FAIL_RESEARCH_LANES")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS_RESEARCH_LANES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
