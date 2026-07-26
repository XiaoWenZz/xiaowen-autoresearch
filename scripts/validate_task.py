#!/usr/bin/env python3
"""Validate xiaowen-autoresearch task structure and cross-record invariants."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_STATUSES = {"draft", "ready", "running", "waiting_external", "needs_approval", "completed", "blocked"}
CLAIM_TYPES = {"fact", "inference", "hypothesis"}
CLAIM_STATUSES = {
    "proposed",
    "supported",
    "challenged",
    "rebuttal-ready",
    "pending-rebuttal",
    "accepted",
    "rejected",
    "withdrawn",
}
EVIDENCE_KINDS = {"source", "experiment", "observation", "negative_result", "diagnostic"}
VERIFICATION_STATUSES = {"unverified", "partial", "verified"}
ITERATION_OUTCOMES = {"progress", "negative_result", "replication", "diagnostic", "stale", "blocked"}
RUN_STATUSES = {"planned", "submitted", "running", "completed", "failed", "cancelled"}
GOVERNANCE_TRACKS = {"scout", "confirmatory"}
OPERATING_WEIGHTS = {"lite", "managed", "full"}
VALID_DURABLE_GOVERNANCE_PAIRS = {("scout", "managed"), ("confirmatory", "full")}
WORKER_STATUSES = {"dispatched", "running", "needs_attention", "completed", "failed", "cancelled", "reclaimed"}
TERMINAL_WORKER_STATUSES = {"completed", "failed", "cancelled", "reclaimed"}
CALLBACK_STATES = {"pending", "delivered", "acknowledged", "not_available"}
WATCHDOG_STATES = {"active", "paused", "not_required"}
CONTROLLER_NEXT_ACTIONS = {
    "dispatch_next",
    "explicit_hold",
    "owner_approval_required",
    "scoped_close",
}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def schema_at_least(value: Any, major: int, minor: int) -> bool:
    if not isinstance(value, str):
        return False
    try:
        current_major, current_minor = (int(part) for part in value.split(".", 1))
    except (ValueError, TypeError):
        return False
    return (current_major, current_minor) >= (major, minor)


def load_json(path: Path, report: Report) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.error(f"cannot read JSON {path}: {exc}")
        return {}
    if not isinstance(value, dict):
        report.error(f"expected JSON object: {path}")
        return {}
    return value


def load_jsonl(path: Path, report: Report) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        report.error(f"cannot read JSONL {path}: {exc}")
        return records
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            report.error(f"invalid JSONL {path}:{line_number}: {exc}")
            continue
        if not isinstance(value, dict):
            report.error(f"expected object at {path}:{line_number}")
            continue
        records.append(value)
    return records


def require_keys(record: dict[str, Any], keys: tuple[str, ...], context: str, report: Report) -> None:
    for key in keys:
        if key not in record:
            report.error(f"{context} missing key: {key}")


def check_unique(records: list[dict[str, Any]], id_field: str, context: str, report: Report) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for position, record in enumerate(records, start=1):
        value = record.get(id_field)
        if not isinstance(value, str) or not value:
            report.error(f"{context} record {position} requires non-empty {id_field}")
            continue
        if value in index:
            report.error(f"duplicate {id_field} in {context}: {value}")
        index[value] = record
    return index


def resolve_governance_track(charter: dict[str, Any], report: Report) -> tuple[str, bool]:
    """Return track and whether the task explicitly uses the two-track schema."""
    if "governance_track" not in charter:
        report.warn("legacy charter has no governance_track; treating it as confirmatory")
        return "confirmatory", False
    track = charter.get("governance_track")
    if track not in GOVERNANCE_TRACKS:
        report.error(f"charter has invalid governance_track: {track}")
        return "confirmatory", True
    return str(track), True


def resolve_operating_weight(
    charter: dict[str, Any], track: str, report: Report
) -> tuple[str, bool]:
    if "operating_weight" not in charter:
        inferred = "managed" if track == "scout" else "full"
        report.warn(f"legacy charter has no operating_weight; inferring {inferred}")
        return inferred, False
    weight = charter.get("operating_weight")
    if weight not in OPERATING_WEIGHTS:
        report.error(f"charter has invalid operating_weight: {weight}")
        return "full", True
    if (track, str(weight)) not in VALID_DURABLE_GOVERNANCE_PAIRS:
        report.error(f"invalid durable governance_track/operating_weight pair: {track}/{weight}")
    return str(weight), True


def validate_charter(
    charter: dict[str, Any], ready: bool, report: Report
) -> tuple[str, bool, str, bool]:
    require_keys(
        charter,
        (
            "schema_version",
            "task_id",
            "task_type",
            "title",
            "objective",
            "research_question",
            "hypotheses",
            "scope",
            "success_criteria",
            "failure_criteria",
            "primary_metrics",
            "protocol",
            "budget",
            "authorization",
            "stop_conditions",
        ),
        "charter",
        report,
    )
    track, explicit_track = resolve_governance_track(charter, report)
    weight, explicit_weight = resolve_operating_weight(charter, track, report)
    if schema_at_least(charter.get("schema_version"), 1, 1):
        require_keys(
            charter,
            ("program_id", "epoch_id", "operating_weight", "governance_admission_proof"),
            "charter schema 1.1",
            report,
        )
        for key in ("program_id", "epoch_id"):
            if not isinstance(charter.get(key), str) or not charter.get(key):
                report.error(f"charter schema 1.1 requires non-empty {key}")
    budget = charter.get("budget", {})
    if not isinstance(budget, dict) or not isinstance(budget.get("max_iterations"), int) or budget.get("max_iterations", 0) < 1:
        report.error("charter budget.max_iterations must be a positive integer")
    authorization = charter.get("authorization", {})
    if not isinstance(authorization, dict) or not authorization.get("approval_required"):
        report.error("charter authorization.approval_required must be non-empty")
    if ready:
        for key in ("research_question", "success_criteria", "failure_criteria", "primary_metrics", "stop_conditions"):
            if not charter.get(key):
                report.error(f"ready charter requires non-empty {key}")
        if explicit_track:
            for key in ("strongest_baseline", "claim_boundary"):
                if not charter.get(key):
                    report.error(f"ready charter requires non-empty {key}")
            governance = charter.get("governance", {})
            if not isinstance(governance, dict):
                report.error("ready charter requires governance object")
            elif track == "scout":
                pre_evidence_budget = governance.get("pre_evidence_iteration_budget")
                if not isinstance(pre_evidence_budget, int) or pre_evidence_budget < 1:
                    report.error("ready Scout charter requires positive governance.pre_evidence_iteration_budget")
                if not governance.get("promotion_trigger"):
                    report.error("ready Scout charter requires governance.promotion_trigger")
        if explicit_weight and not charter.get("governance_admission_proof"):
            report.error("ready charter requires governance_admission_proof")
        protocol = charter.get("protocol", {})
        if not isinstance(protocol, dict) or protocol.get("frozen") is not True or not parse_time(protocol.get("frozen_at")):
            report.error("ready charter requires protocol.frozen=true and a valid frozen_at")
        if charter.get("task_type") in {"experiment", "mixed"}:
            for key in ("code_version", "data_version", "data_split", "seed_policy", "analysis_plan"):
                if not protocol.get(key):
                    report.error(f"ready experimental charter requires protocol.{key}")
        if explicit_track and not protocol.get("data_boundary"):
            report.error("ready charter requires protocol.data_boundary")
    return track, explicit_track, weight, explicit_weight


def validate_run(root: Path, path: Path, run: dict[str, Any], task_id: str, report: Report) -> None:
    context = f"run {path.name}"
    require_keys(run, ("schema_version", "run_id", "task_id", "status", "question", "started_at"), context, report)
    if run.get("task_id") != task_id:
        report.error(f"{context} task_id does not match charter")
    if run.get("status") not in RUN_STATUSES:
        report.error(f"{context} has invalid status: {run.get('status')}")
    if not parse_time(run.get("started_at")):
        report.error(f"{context} requires valid started_at")
    if run.get("status") != "completed":
        return
    required_completed = (
        "ended_at",
        "code_version",
        "config",
        "dataset",
        "environment",
        "seeds",
        "primary_metrics",
        "artifacts",
        "validation",
        "result_summary",
        "anomalies",
        "protocol_deviations",
    )
    require_keys(run, required_completed, context, report)
    started_at = parse_time(run.get("started_at"))
    ended_at = parse_time(run.get("ended_at"))
    if not ended_at:
        report.error(f"{context} requires valid ended_at")
    elif started_at and ended_at < started_at:
        report.error(f"{context} ended_at precedes started_at")
    code_version = run.get("code_version", {})
    if not isinstance(code_version, dict) or not code_version.get("git_commit"):
        report.error(f"{context} requires code_version.git_commit")
    config = run.get("config", {})
    if not isinstance(config, dict) or not config.get("path") or not config.get("sha256"):
        report.error(f"{context} requires config.path and config.sha256")
    dataset = run.get("dataset", {})
    if not isinstance(dataset, dict) or not dataset.get("name") or not dataset.get("version") or not dataset.get("split"):
        report.error(f"{context} requires dataset name, version, and split")
    for key in ("environment", "seeds", "primary_metrics", "artifacts", "validation", "result_summary"):
        if not run.get(key):
            report.error(f"{context} requires non-empty {key}")
    validation = run.get("validation", [])
    if isinstance(validation, list):
        for item in validation:
            if not isinstance(item, dict) or not item.get("command") or item.get("status") not in {"pass", "fail"}:
                report.error(f"{context} validation entries require command and pass/fail status")
    for artifact in run.get("artifacts", []):
        if not isinstance(artifact, str) or not artifact:
            report.error(f"{context} artifact entries must be non-empty strings")
            continue
        if "://" in artifact:
            continue
        artifact_path = Path(artifact)
        if not artifact_path.is_absolute():
            artifact_path = root / artifact_path
        if not artifact_path.is_file():
            report.error(f"{context} references missing artifact: {artifact}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--ready", action="store_true", help="enforce ready-to-run charter gates")
    parser.add_argument("--max-heartbeat-age-minutes", type=int, default=180)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.task_dir.expanduser().resolve()
    report = Report()
    required_files = (
        "AGENTS.md",
        "state/charter.json",
        "state/progress.json",
        "state/heartbeat.json",
        "state/directions.jsonl",
        "state/evidence.jsonl",
        "state/claims.jsonl",
        "state/iterations.jsonl",
        "state/approvals.jsonl",
        "logs/events.jsonl",
    )
    for relative in required_files:
        if not (root / relative).is_file():
            report.error(f"missing required file: {relative}")
    for relative in ("runs", "artifacts", "logs", "reports"):
        if not (root / relative).is_dir():
            report.error(f"missing required directory: {relative}")
    if report.errors:
        for message in report.errors:
            print(f"ERROR: {message}")
        print(f"FAIL: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        return 1

    charter = load_json(root / "state/charter.json", report)
    progress = load_json(root / "state/progress.json", report)
    heartbeat = load_json(root / "state/heartbeat.json", report)
    governance_track, explicit_track, operating_weight, explicit_weight = validate_charter(
        charter, args.ready, report
    )
    task_id = charter.get("task_id", "")
    workers_path = root / "state" / "workers.jsonl"
    if schema_at_least(charter.get("schema_version"), 1, 1) and not workers_path.is_file():
        report.error("schema 1.1 task requires state/workers.jsonl")
    elif not workers_path.is_file():
        report.warn("legacy task has no state/workers.jsonl")

    require_keys(progress, ("task_id", "status", "phase", "iteration", "stale_count", "next_action"), "progress", report)
    if progress.get("task_id") != task_id:
        report.error("progress task_id does not match charter")
    if explicit_track and progress.get("governance_track") != governance_track:
        report.error("progress governance_track does not match charter")
    if explicit_weight and progress.get("operating_weight") != operating_weight:
        report.error("progress operating_weight does not match charter")
    if progress.get("status") not in TASK_STATUSES:
        report.error(f"invalid progress status: {progress.get('status')}")
    if args.ready and progress.get("status") == "draft":
        report.error("ready validation requires progress status to leave draft")
    if not isinstance(progress.get("iteration"), int) or progress.get("iteration", -1) < 0:
        report.error("progress iteration must be a non-negative integer")
    max_iterations = charter.get("budget", {}).get("max_iterations", 0)
    if isinstance(progress.get("iteration"), int) and isinstance(max_iterations, int) and progress["iteration"] > max_iterations:
        report.error("progress iteration exceeds charter budget.max_iterations")

    streams = {
        name: load_jsonl(root / "state" / f"{name}.jsonl", report)
        for name in ("directions", "evidence", "claims", "iterations", "approvals")
    }
    streams["workers"] = load_jsonl(workers_path, report) if workers_path.is_file() else []
    direction_index = check_unique(streams["directions"], "direction_id", "directions", report)
    evidence_index = check_unique(streams["evidence"], "evidence_id", "evidence", report)
    claim_index = check_unique(streams["claims"], "claim_id", "claims", report)
    check_unique(streams["iterations"], "iteration_id", "iterations", report)
    check_unique(streams["approvals"], "approval_id", "approvals", report)
    worker_record_index = check_unique(streams["workers"], "worker_record_id", "workers", report)

    terminal_event_workers: dict[str, str] = {}
    terminal_event_transactions: dict[str, str] = {}
    prior_worker_records: dict[str, dict[str, Any]] = {}
    latest_worker_records: dict[str, tuple[str, dict[str, Any]]] = {}
    pending_dispatch_links: list[tuple[str, str, str, str]] = []
    for worker_record_id, record in worker_record_index.items():
        require_keys(
            record,
            (
                "worker_id",
                "thread_id",
                "program_id",
                "epoch_id",
                "contract_revision",
                "role",
                "status",
                "callback_state",
                "terminal_event_id",
                "reclaim_deadline",
                "watchdog_id",
                "watchdog_state",
                "artifact_paths",
                "recorded_at",
            ),
            f"worker record {worker_record_id}",
            report,
        )
        worker_id = record.get("worker_id")
        if not isinstance(worker_id, str) or not worker_id:
            report.error(f"worker record {worker_record_id} requires non-empty worker_id")
            continue
        if not isinstance(record.get("thread_id"), str) or not record.get("thread_id"):
            report.error(f"worker record {worker_record_id} requires non-empty thread_id")
        if charter.get("program_id") and record.get("program_id") != charter.get("program_id"):
            report.error(f"worker record {worker_record_id} program_id does not match charter")
        if charter.get("epoch_id") and record.get("epoch_id") != charter.get("epoch_id"):
            report.error(f"worker record {worker_record_id} epoch_id does not match charter")
        if record.get("status") not in WORKER_STATUSES:
            report.error(f"worker record {worker_record_id} has invalid status: {record.get('status')}")
        callback_state = record.get("callback_state")
        if callback_state not in CALLBACK_STATES:
            report.error(f"worker record {worker_record_id} has invalid callback_state: {callback_state}")
        watchdog_state = record.get("watchdog_state")
        if watchdog_state not in WATCHDOG_STATES:
            report.error(f"worker record {worker_record_id} has invalid watchdog_state: {watchdog_state}")
        if not parse_time(record.get("recorded_at")):
            report.error(f"worker record {worker_record_id} requires valid recorded_at")
        if not isinstance(record.get("artifact_paths"), list):
            report.error(f"worker record {worker_record_id} artifact_paths must be a list")
        terminal_event_id = record.get("terminal_event_id")
        if callback_state in {"delivered", "acknowledged"}:
            if not isinstance(terminal_event_id, str) or not terminal_event_id:
                report.error(
                    f"worker record {worker_record_id} callback_state {callback_state} requires terminal_event_id"
                )
            elif terminal_event_id in terminal_event_workers and terminal_event_workers[terminal_event_id] != worker_id:
                report.error(f"terminal_event_id {terminal_event_id} is shared by multiple workers")
            else:
                terminal_event_workers[terminal_event_id] = worker_id
        if callback_state == "not_available" and not parse_time(record.get("reclaim_deadline")):
            report.error(f"worker record {worker_record_id} callback_state not_available requires reclaim_deadline")
        if record.get("status") in TERMINAL_WORKER_STATUSES and callback_state == "pending":
            report.error(f"terminal worker record {worker_record_id} cannot leave callback_state pending")
        if (
            record.get("status") in TERMINAL_WORKER_STATUSES
            and callback_state == "acknowledged"
            and watchdog_state not in {"paused", "not_required"}
        ):
            report.error(f"acknowledged terminal worker record {worker_record_id} must pause or omit its watchdog")
        if (
            schema_at_least(charter.get("schema_version"), 1, 2)
            and record.get("status") in TERMINAL_WORKER_STATUSES
            and callback_state == "acknowledged"
        ):
            action = record.get("controller_action")
            if not isinstance(action, dict):
                report.error(
                    f"acknowledged terminal worker record {worker_record_id} requires controller_action"
                )
            else:
                require_keys(
                    action,
                    (
                        "transaction_id",
                        "disposition",
                        "next_action",
                        "worker_notified",
                        "decided_at",
                    ),
                    f"worker record {worker_record_id} controller_action",
                    report,
                )
                transaction_id = action.get("transaction_id")
                if not isinstance(transaction_id, str) or not transaction_id:
                    report.error(
                        f"worker record {worker_record_id} controller_action requires transaction_id"
                    )
                elif isinstance(terminal_event_id, str) and terminal_event_id:
                    prior_transaction = terminal_event_transactions.get(terminal_event_id)
                    if prior_transaction is not None and prior_transaction != transaction_id:
                        report.error(
                            f"terminal_event_id {terminal_event_id} has multiple controller transactions"
                        )
                    terminal_event_transactions[terminal_event_id] = transaction_id
                if not isinstance(action.get("disposition"), str) or not action.get("disposition"):
                    report.error(
                        f"worker record {worker_record_id} controller_action requires disposition"
                    )
                next_action = action.get("next_action")
                if next_action not in CONTROLLER_NEXT_ACTIONS:
                    report.error(
                        f"worker record {worker_record_id} has invalid controller next_action: {next_action}"
                    )
                if action.get("worker_notified") is not True:
                    report.error(
                        f"worker record {worker_record_id} must notify the worker before acknowledgement closes"
                    )
                if not parse_time(action.get("decided_at")):
                    report.error(
                        f"worker record {worker_record_id} controller_action requires valid decided_at"
                    )
                if next_action == "dispatch_next":
                    next_worker_record_id = action.get("next_worker_record_id")
                    next_contract_revision = action.get("next_contract_revision")
                    if not isinstance(next_worker_record_id, str) or not next_worker_record_id:
                        report.error(
                            f"worker record {worker_record_id} dispatch_next requires next_worker_record_id"
                        )
                    if not isinstance(next_contract_revision, str) or not next_contract_revision:
                        report.error(
                            f"worker record {worker_record_id} dispatch_next requires next_contract_revision"
                        )
                    if (
                        isinstance(next_worker_record_id, str)
                        and next_worker_record_id
                        and isinstance(next_contract_revision, str)
                        and next_contract_revision
                    ):
                        pending_dispatch_links.append(
                            (
                                worker_record_id,
                                next_worker_record_id,
                                next_contract_revision,
                                str(action.get("decided_at", "")),
                            )
                        )
        supersedes_id = record.get("supersedes_id")
        if supersedes_id is not None:
            superseded = prior_worker_records.get(supersedes_id)
            if superseded is None:
                report.error(f"worker record {worker_record_id} supersedes missing or later record {supersedes_id}")
            elif superseded.get("worker_id") != worker_id:
                report.error(f"worker record {worker_record_id} supersedes a different worker")
        prior_worker_records[worker_record_id] = record
        latest_worker_records[worker_id] = (worker_record_id, record)

    if schema_at_least(charter.get("schema_version"), 1, 2):
        for worker_id, (worker_record_id, record) in latest_worker_records.items():
            if (
                record.get("status") in TERMINAL_WORKER_STATUSES
                and record.get("callback_state") == "delivered"
            ):
                report.error(
                    f"worker {worker_id} has an unacknowledged terminal callback at {worker_record_id}"
                )
        for source_id, target_id, next_revision, decided_at in pending_dispatch_links:
            target = worker_record_index.get(target_id)
            if target is None:
                report.error(
                    f"worker record {source_id} dispatch_next target does not exist: {target_id}"
                )
                continue
            if target.get("contract_revision") != next_revision:
                report.error(
                    f"worker record {source_id} dispatch_next revision does not match {target_id}"
                )
            if target.get("status") not in {"dispatched", "running", "needs_attention"}:
                report.error(
                    f"worker record {source_id} dispatch_next target {target_id} is not an active transition"
                )
            target_time = parse_time(target.get("recorded_at"))
            decision_time = parse_time(decided_at)
            if target_time is not None and decision_time is not None and target_time < decision_time:
                report.error(
                    f"worker record {source_id} dispatch_next target predates its controller decision"
                )

    fingerprints: dict[str, str] = {}
    for direction_id, record in direction_index.items():
        require_keys(record, ("iteration", "hypothesis", "mechanism", "changed_variables", "expected_observation", "structural_delta", "fingerprint", "is_replication", "status"), f"direction {direction_id}", report)
        fingerprint = record.get("fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            if fingerprint in fingerprints and not record.get("is_replication"):
                report.error(f"direction {direction_id} duplicates fingerprint {fingerprint} without replication flag")
            fingerprints.setdefault(fingerprint, direction_id)
        if record.get("is_replication") and not record.get("replicates_direction_id"):
            report.error(f"direction {direction_id} replication requires replicates_direction_id")

    run_index: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "runs").glob("*.json")):
        run = load_json(path, report)
        validate_run(root, path, run, task_id, report)
        run_id = run.get("run_id")
        if isinstance(run_id, str) and run_id:
            if run_id in run_index:
                report.error(f"duplicate run_id: {run_id}")
            run_index[run_id] = run

    for evidence_id, record in evidence_index.items():
        require_keys(record, ("kind", "summary", "provenance", "verification", "supports_claims", "limitations"), f"evidence {evidence_id}", report)
        if record.get("kind") not in EVIDENCE_KINDS:
            report.error(f"evidence {evidence_id} has invalid kind: {record.get('kind')}")
        provenance = record.get("provenance", {})
        if not isinstance(provenance, dict) or not provenance.get("source") or not parse_time(provenance.get("captured_at")):
            report.error(f"evidence {evidence_id} requires provenance source and captured_at")
        verification = record.get("verification", {})
        if not isinstance(verification, dict) or verification.get("status") not in VERIFICATION_STATUSES:
            report.error(f"evidence {evidence_id} has invalid verification status")
        if record.get("kind") in {"experiment", "negative_result"}:
            run_id = record.get("run_id")
            if not run_id:
                report.error(f"evidence {evidence_id} requires run_id")
            elif run_id not in run_index:
                report.error(f"evidence {evidence_id} references missing run {run_id}")

    for claim in streams["claims"]:
        claim_id = claim.get("claim_id", "<unknown>")
        require_keys(claim, ("claim_type", "text", "status", "evidence_ids", "scope", "limitations", "adjudication"), f"claim {claim_id}", report)
        if claim.get("claim_type") not in CLAIM_TYPES:
            report.error(f"claim {claim_id} has invalid claim_type")
        if claim.get("status") not in CLAIM_STATUSES:
            report.error(f"claim {claim_id} has invalid status")
        if governance_track == "scout" and claim.get("status") == "accepted":
            report.error(f"Scout claim {claim_id} cannot be accepted; promote the task to confirmatory")
        evidence_ids = claim.get("evidence_ids", [])
        if claim.get("status") in {"supported", "accepted"} and not evidence_ids:
            report.error(f"claim {claim_id} status {claim.get('status')} requires evidence_ids")
        if not isinstance(evidence_ids, list):
            report.error(f"claim {claim_id} evidence_ids must be a list")
            evidence_ids = []
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_index:
                report.error(f"claim {claim_id} references missing evidence {evidence_id}")
        if claim.get("status") == "accepted":
            adjudication = claim.get("adjudication")
            if not isinstance(adjudication, dict):
                report.error(f"accepted claim {claim_id} requires adjudication")
            else:
                require_keys(adjudication, ("decision", "reviewer_role", "independent", "rationale", "decided_at"), f"claim {claim_id} adjudication", report)
                if adjudication.get("decision") != "accepted" or not parse_time(adjudication.get("decided_at")):
                    report.error(f"accepted claim {claim_id} has invalid adjudication decision/time")
                if adjudication.get("independent") is not True:
                    report.error(f"accepted claim {claim_id} requires independent adjudication")
            for evidence_id in evidence_ids:
                status = evidence_index.get(evidence_id, {}).get("verification", {}).get("status")
                if status != "verified":
                    report.error(f"accepted claim {claim_id} uses non-verified evidence {evidence_id}")

    for evidence_id, record in evidence_index.items():
        supports_claims = record.get("supports_claims", [])
        if not isinstance(supports_claims, list):
            report.error(f"evidence {evidence_id} supports_claims must be a list")
            continue
        for claim_id in supports_claims:
            if claim_id not in claim_index:
                report.error(f"evidence {evidence_id} references missing claim {claim_id}")
            elif evidence_id not in claim_index[claim_id].get("evidence_ids", []):
                report.error(f"evidence {evidence_id} and claim {claim_id} are not linked bidirectionally")

    stale_count = 0
    for record in sorted(streams["iterations"], key=lambda item: item.get("iteration", -1)):
        iteration_id = record.get("iteration_id", "<unknown>")
        require_keys(record, ("iteration", "direction_id", "started_at", "ended_at", "outcome", "evidence_ids", "validation", "next_action"), f"iteration {iteration_id}", report)
        if record.get("outcome") not in ITERATION_OUTCOMES:
            report.error(f"iteration {iteration_id} has invalid outcome")
        if not parse_time(record.get("started_at")) or not parse_time(record.get("ended_at")):
            report.error(f"iteration {iteration_id} requires valid started_at and ended_at")
        if record.get("direction_id") not in direction_index:
            report.error(f"iteration {iteration_id} references missing direction {record.get('direction_id')}")
        for evidence_id in record.get("evidence_ids", []):
            if evidence_id not in evidence_index:
                report.error(f"iteration {iteration_id} references missing evidence {evidence_id}")
        stale_count = stale_count + 1 if record.get("outcome") == "stale" else 0
    if progress.get("stale_count") != stale_count:
        report.error(f"progress stale_count={progress.get('stale_count')} but iteration history implies {stale_count}")

    if governance_track == "scout" and explicit_track:
        governance = charter.get("governance", {})
        pre_evidence_budget = governance.get("pre_evidence_iteration_budget") if isinstance(governance, dict) else None
        if isinstance(pre_evidence_budget, int) and len(streams["iterations"]) > pre_evidence_budget and not run_index:
            report.warn(
                "Scout exceeded its pre-evidence iteration budget without a run manifest; "
                "simplify the witness or record the hard blocker"
            )

    if heartbeat.get("task_id") != task_id:
        report.error("heartbeat task_id does not match charter")
    if progress.get("status") == "running":
        last_seen = parse_time(heartbeat.get("last_seen_at"))
        if last_seen is None:
            report.error("running task requires a valid heartbeat last_seen_at")
        else:
            age_minutes = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60
            if age_minutes > args.max_heartbeat_age_minutes:
                report.error(f"running task heartbeat is stale ({age_minutes:.1f} minutes)")

    for approval in streams["approvals"]:
        approval_id = approval.get("approval_id", "<unknown>")
        require_keys(approval, ("action", "scope", "status", "requested_at"), f"approval {approval_id}", report)
        if approval.get("status") not in {"requested", "approved", "denied", "expired"}:
            report.error(f"approval {approval_id} has invalid status")
        if not parse_time(approval.get("requested_at")):
            report.error(f"approval {approval_id} requires valid requested_at")
        if approval.get("status") in {"approved", "denied"} and not parse_time(approval.get("decided_at")):
            report.error(f"approval {approval_id} status {approval.get('status')} requires decided_at")

    for message in report.errors:
        print(f"ERROR: {message}")
    for message in report.warnings:
        print(f"WARN: {message}")
    if report.errors:
        print(f"FAIL: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        return 1
    print(
        f"PASS: governance_track={governance_track}, operating_weight={operating_weight}, "
        f"0 errors, {len(report.warnings)} warning(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
