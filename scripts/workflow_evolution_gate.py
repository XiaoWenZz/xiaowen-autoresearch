#!/usr/bin/env python3
"""Read-only shadow detectors for workflow cost, trace defects, and conformance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import statistics
from pathlib import Path
from typing import Any, Iterable


WORKSPACE_ROOT = Path("/Users/xiaowen/Documents/Obsidian Vault/003_科研")
STATE_DB = Path("/Users/xiaowen/.codex/state_5.sqlite")
ARIS_THREAD_ID = "019fdaac-ce48-74d1-8fa0-94bab9ee2f3e"
SOFT_TOKEN_THRESHOLD = 25_000_000
HARD_TOKEN_THRESHOLD = 75_000_000
MIN_SOFT_TOKEN_TURNS = 2
MIN_RELATIVE_WINDOWS = 8
ISSUE_FIELDS = (
    "source_type",
    "detector",
    "observed_fact",
    "affected_stage",
    "impact",
    "recurrence_clue",
    "evidence_pointer",
    "protected_boundary_flag",
    "suggested_next_check",
    "fingerprint",
    "rule_ref",
    "mode",
)


class GateError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(*parts: Any) -> str:
    return hashlib.sha256(_canonical(list(parts))).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _thread_record(db_path: Path, thread_id: str) -> tuple[Path, Path]:
    if thread_id == ARIS_THREAD_ID:
        raise GateError("ARIS thread is outside xiaowen-autoresearch workflow auditing")
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT rollout_path, cwd FROM threads WHERE id = ?", (thread_id,)
        ).fetchall()
    finally:
        connection.close()
    if len(rows) != 1:
        raise GateError("thread identity is missing or ambiguous")
    return Path(rows[0][0]), Path(rows[0][1])


def _contains_dispatch(value: Any, dispatch_id: str) -> bool:
    if isinstance(value, dict):
        if value.get("dispatch_id") == dispatch_id:
            return True
        return any(_contains_dispatch(item, dispatch_id) for item in value.values())
    if isinstance(value, list):
        return any(_contains_dispatch(item, dispatch_id) for item in value)
    if isinstance(value, str):
        boundary = r"[A-Za-z0-9_.:-]"
        return re.search(
            rf"(?<!{boundary}){re.escape(dispatch_id)}(?!{boundary})", value
        ) is not None
    return False


def _token_usage(event: dict[str, Any]) -> int | None:
    if event.get("type") != "event_msg":
        return None
    payload = event.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "token_count":
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    last = info.get("last_token_usage")
    if not isinstance(last, dict):
        return None
    total = last.get("total_tokens")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise GateError("token_count last_token_usage.total_tokens is invalid")
    return total


def scan_token_window(rollout_path: Path, dispatch_id: str) -> tuple[int, int, int]:
    activation_lines: list[int] = []
    token_events: list[tuple[int, int]] = []
    with rollout_path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if dispatch_id not in raw and '"token_count"' not in raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise GateError(f"invalid rollout JSON at line {line_number}") from exc
            if dispatch_id in raw and _contains_dispatch(event, dispatch_id):
                activation_lines.append(line_number)
            token_usage = _token_usage(event)
            if token_usage is not None:
                token_events.append((line_number, token_usage))
    if len(activation_lines) != 1:
        raise GateError("dispatch activation point is missing or ambiguous")
    activation_line = activation_lines[0]
    usages = [usage for line, usage in token_events if line > activation_line and usage > 0]
    return sum(usages), len(usages), activation_line


def relative_soft_threshold(healthy_windows: Iterable[int]) -> int | None:
    windows = list(healthy_windows)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in windows):
        raise GateError("healthy comparable windows must be non-negative integers")
    if len(windows) < MIN_RELATIVE_WINDOWS:
        return None
    median = statistics.median(windows)
    mad = statistics.median(abs(value - median) for value in windows)
    return int(max(2 * median, median + 3 * mad))


def token_decision(
    *,
    thread_id: str,
    dispatch_id: str,
    token_total: int,
    token_turns: int,
    decision_output_count: int,
    healthy_windows: Iterable[int],
) -> dict[str, Any]:
    if decision_output_count < 0:
        raise GateError("decision_output_count must be non-negative")
    relative = relative_soft_threshold(healthy_windows)
    effective_soft = SOFT_TOKEN_THRESHOLD
    if relative is not None:
        effective_soft = min(HARD_TOKEN_THRESHOLD, max(effective_soft, relative))
    band = "NONE"
    if decision_output_count == 0:
        if token_total >= HARD_TOKEN_THRESHOLD:
            band = "HARD"
        elif token_turns >= MIN_SOFT_TOKEN_TURNS and token_total >= effective_soft:
            band = "SOFT"
    return {
        "status": "PASS",
        "mode": "SHADOW",
        "detector": "BACKWARD_OUTCOME_COST",
        "thread_id": thread_id,
        "dispatch_id": dispatch_id,
        "token_total": token_total,
        "token_turns": token_turns,
        "decision_output_count": decision_output_count,
        "soft_threshold": effective_soft,
        "hard_threshold": HARD_TOKEN_THRESHOLD,
        "relative_threshold": relative,
        "trigger": band,
        "fingerprint": None
        if band == "NONE"
        else _fingerprint("BACKWARD_OUTCOME_COST", thread_id, dispatch_id, band),
    }


def classify_conformance(event: dict[str, Any]) -> str:
    if event.get("authority_conflict") is True:
        return "AUTHORITY_CONFLICT"
    applicable = event.get("rule_applicable")
    feasible = event.get("rule_feasible")
    if applicable is not True or feasible is not True:
        return "NOT_ESTIMABLE"
    if event.get("shared_tooling_drift") is True:
        return "RULE_TOOLING_DRIFT"
    recurrence = event.get("independent_recurrence_count", 0)
    if isinstance(recurrence, bool) or not isinstance(recurrence, int) or recurrence < 0:
        raise GateError("independent_recurrence_count must be a non-negative integer")
    if event.get("compliant_zero_output") is True or recurrence >= 2:
        return "RULE_DESIGN_DEFECT"
    if event.get("isolated_deviation") is True:
        return "EXECUTION_NONCONFORMANCE"
    return "NOT_ESTIMABLE"


def _route_sample_int(event: dict[str, Any], field: str) -> int:
    value = event.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GateError(f"MODEL_ROUTE_SAMPLE.{field} must be a non-negative integer")
    return value


def _route_sample_bool(event: dict[str, Any], field: str) -> bool:
    value = event.get(field)
    if not isinstance(value, bool):
        raise GateError(f"MODEL_ROUTE_SAMPLE.{field} must be boolean")
    return value


def _route_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    def rate(field: str) -> float:
        return sum(_route_sample_bool(sample, field) for sample in samples) / len(samples)

    return {
        "sample_count": len(samples),
        "total_tokens_median": statistics.median(
            _route_sample_int(sample, "total_tokens") for sample in samples
        ),
        "wall_time_ms_median": statistics.median(
            _route_sample_int(sample, "wall_time_ms") for sample in samples
        ),
        "first_pass_acceptance_rate": rate("first_pass_acceptance"),
        "retry_count_median": statistics.median(
            _route_sample_int(sample, "retry_count") for sample in samples
        ),
        "decision_complete_output_rate": rate("decision_complete_output"),
        "reliability_pass_rate": rate("reliability_pass"),
    }


def model_route_scorecard(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare supplied existing process facts; never launch a benchmark task."""

    groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for event in events:
        if event.get("kind") != "MODEL_ROUTE_SAMPLE":
            continue
        comparison_key = event.get("comparison_key")
        route = event.get("route")
        if not isinstance(comparison_key, str) or not comparison_key:
            raise GateError("MODEL_ROUTE_SAMPLE.comparison_key must be a non-empty string")
        if route not in {"LUNA", "SOL"}:
            raise GateError("MODEL_ROUTE_SAMPLE.route must be LUNA or SOL")
        groups.setdefault(comparison_key, {"LUNA": [], "SOL": []})[route].append(event)

    scorecards: list[dict[str, Any]] = []
    for comparison_key in sorted(groups):
        routes = groups[comparison_key]
        if not routes["LUNA"] or not routes["SOL"]:
            scorecards.append(
                {
                    "comparison_key": comparison_key,
                    "mode": "SHADOW",
                    "disposition": "NOT_ESTIMABLE",
                    "reason": "both comparable Luna and Sol samples are required",
                    "sample_count": {
                        "LUNA": len(routes["LUNA"]),
                        "SOL": len(routes["SOL"]),
                    },
                }
            )
            continue

        luna = _route_summary(routes["LUNA"])
        sol = _route_summary(routes["SOL"])
        reliability_noninferior = (
            luna["reliability_pass_rate"] == 1.0
            and luna["reliability_pass_rate"] >= sol["reliability_pass_rate"]
        )
        quality_noninferior = (
            luna["first_pass_acceptance_rate"] >= sol["first_pass_acceptance_rate"]
            and luna["decision_complete_output_rate"]
            >= sol["decision_complete_output_rate"]
            and luna["retry_count_median"] <= sol["retry_count_median"]
        )
        cost_improved = (
            luna["total_tokens_median"] < sol["total_tokens_median"]
            and luna["wall_time_ms_median"] < sol["wall_time_ms_median"]
        )
        if not reliability_noninferior or not quality_noninferior:
            disposition = "ROLLBACK_REQUIRED"
        elif cost_improved:
            disposition = "RETAIN_ELIGIBLE"
        else:
            disposition = "NO_CHANGE"
        scorecards.append(
            {
                "comparison_key": comparison_key,
                "mode": "SHADOW",
                "disposition": disposition,
                "reliability_noninferior": reliability_noninferior,
                "quality_noninferior": quality_noninferior,
                "cost_improved": cost_improved,
                "LUNA": luna,
                "SOL": sol,
            }
        )
    return scorecards


def _issue(detector: str, event: dict[str, Any], observed_fact: str) -> dict[str, Any]:
    fingerprint = _fingerprint(
        detector,
        event.get("failure_fingerprint"),
        event.get("affected_stage"),
        observed_fact,
    )
    issue = {
        "source_type": event.get("source_type", "AUDITOR_DISCOVERY"),
        "detector": detector,
        "observed_fact": observed_fact,
        "affected_stage": event.get("affected_stage", "UNVERIFIED"),
        "impact": event.get("impact", "UNVERIFIED"),
        "recurrence_clue": event.get("recurrence_clue", "UNVERIFIED"),
        "evidence_pointer": event.get("evidence_pointer", "UNVERIFIED"),
        "protected_boundary_flag": bool(event.get("protected_boundary_flag", False)),
        "suggested_next_check": event.get("suggested_next_check", "VERIFY_TRACE"),
        "fingerprint": fingerprint,
        "rule_ref": event.get("rule_ref"),
        "mode": "SHADOW",
    }
    if set(issue) != set(ISSUE_FIELDS):
        raise AssertionError("issue envelope drift")
    return issue


def evaluate_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
        raise GateError("events input must be a list of objects")
    issues: list[dict[str, Any]] = []
    conformance: list[dict[str, Any]] = []
    fingerprint_counts: dict[str, int] = {}
    controller_wakes: dict[str, int] = {}
    forward_kinds = {
        "ACCESS_SELF_LOCK",
        "WHOLE_CHAIN_GAP",
        "USER_RESCUE",
        "MODEL_ROUTE_MISMATCH",
        "CREATE_NEW_ESCALATION",
        "ACTIVATION_READ_BEFORE_CAS",
    }
    for event in events:
        if event.get("detector") == "RULE_CONFORMANCE":
            conformance.append(
                {
                    "evidence_pointer": event.get("evidence_pointer", "UNVERIFIED"),
                    "classification": classify_conformance(event),
                }
            )
        kind = event.get("kind")
        fingerprint = event.get("failure_fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            fingerprint_counts[fingerprint] = fingerprint_counts.get(fingerprint, 0) + 1
        if kind == "CONTROLLER_WAKE":
            key = str(event.get("objective_id", "UNVERIFIED"))
            controller_wakes[key] = controller_wakes.get(key, 0) + 1
        elif kind in forward_kinds:
            issues.append(_issue("FORWARD_TRACE", event, str(kind)))

    for fingerprint, count in sorted(fingerprint_counts.items()):
        if count >= 2:
            event = next(item for item in events if item.get("failure_fingerprint") == fingerprint)
            issues.append(
                _issue(
                    "FORWARD_TRACE",
                    event,
                    f"REPEATED_FAILURE_FINGERPRINT:{fingerprint}:count={count}",
                )
            )
    for objective_id, count in sorted(controller_wakes.items()):
        if count > 1:
            event = next(
                item
                for item in events
                if item.get("kind") == "CONTROLLER_WAKE"
                and str(item.get("objective_id", "UNVERIFIED")) == objective_id
            )
            issues.append(
                _issue(
                    "FORWARD_TRACE",
                    event,
                    f"REPEATED_CONTROLLER_WAKE:{objective_id}:count={count}",
                )
            )

    deduped = {issue["fingerprint"]: issue for issue in issues}
    return {
        "status": "PASS",
        "mode": "SHADOW",
        "issues": [deduped[key] for key in sorted(deduped)],
        "rule_conformance": conformance,
        "model_route_scorecard": model_route_scorecard(events),
    }


def _load_json_value(raw: str, where: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GateError(f"{where} is not valid JSON") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    token = subparsers.add_parser("token-window")
    token.add_argument("--state-db", default=str(STATE_DB))
    token.add_argument("--workspace-root", default=str(WORKSPACE_ROOT))
    token.add_argument("--thread-id", required=True)
    token.add_argument("--dispatch-id", required=True)
    token.add_argument("--decision-output-count", type=int, required=True)
    token.add_argument("--healthy-windows-json", default="[]")
    events = subparsers.add_parser("evaluate-events")
    events.add_argument("--events-json", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "token-window":
            rollout_path, cwd = _thread_record(Path(args.state_db), args.thread_id)
            workspace_root = Path(args.workspace_root)
            if not _is_within(cwd, workspace_root):
                raise GateError("thread cwd is outside the configured workspace")
            if not rollout_path.is_file():
                raise GateError("thread rollout_path is unavailable")
            healthy = _load_json_value(args.healthy_windows_json, "healthy_windows_json")
            if not isinstance(healthy, list):
                raise GateError("healthy_windows_json must be a list")
            token_total, token_turns, activation_line = scan_token_window(
                rollout_path, args.dispatch_id
            )
            result = token_decision(
                thread_id=args.thread_id,
                dispatch_id=args.dispatch_id,
                token_total=token_total,
                token_turns=token_turns,
                decision_output_count=args.decision_output_count,
                healthy_windows=healthy,
            )
            result["activation_line"] = activation_line
        else:
            events = _load_json_value(args.events_json, "events_json")
            result = evaluate_events(events)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (GateError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
