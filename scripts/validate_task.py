#!/usr/bin/env python3
"""Validate xiaowen-autoresearch task structure and cross-record invariants."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


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
OPERATING_WEIGHTS = {"lite", "managed"}
VALID_DURABLE_GOVERNANCE_PAIRS = {("scout", "managed"), ("confirmatory", "managed")}
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
SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}")


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_declared_local_sha256(
    root: Path,
    path_value: Any,
    digest_value: Any,
    context: str,
    report: Report,
) -> None:
    if not isinstance(path_value, str) or not path_value:
        report.error(f"{context} requires a non-empty path")
        return
    if not isinstance(digest_value, str) or SHA256_PATTERN.fullmatch(digest_value) is None:
        report.error(f"{context} requires a canonical 64-hex sha256")
        return
    try:
        parsed = urlsplit(path_value)
    except ValueError as exc:
        report.error(f"{context} has an invalid path or URI: {exc}")
        return
    if parsed.scheme and parsed.scheme.lower() != "file":
        report.warn(f"{context} is remote; sha256 was declared but not locally recomputed")
        return
    if parsed.scheme.lower() == "file":
        if parsed.netloc not in {"", "localhost"}:
            report.error(f"{context} file URI must not name a remote host")
            return
        if parsed.query or parsed.fragment:
            report.error(f"{context} file URI must not contain a query or fragment")
            return
        try:
            local_path = Path(unquote(parsed.path, errors="strict"))
        except (UnicodeDecodeError, ValueError) as exc:
            report.error(f"{context} has an invalid file URI: {exc}")
            return
        if not local_path.is_absolute():
            report.error(f"{context} file URI must resolve to an absolute local path")
            return
    else:
        local_path = Path(path_value)
        if not local_path.is_absolute():
            local_path = root / local_path
    try:
        is_file = local_path.is_file()
    except (OSError, ValueError) as exc:
        report.error(f"{context} cannot inspect local file {path_value}: {exc}")
        return
    if not is_file:
        report.error(f"{context} references missing local file: {path_value}")
        return
    try:
        actual = sha256_file(local_path)
    except OSError as exc:
        report.error(f"{context} cannot hash local file {path_value}: {exc}")
        return
    if actual.lower() != digest_value.lower():
        report.error(
            f"{context} sha256 mismatch for {path_value}: "
            f"declared={digest_value.lower()} actual={actual}"
        )


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
        inferred = "managed"
        report.warn(f"legacy charter has no operating_weight; inferring {inferred}")
        return inferred, False
    weight = charter.get("operating_weight")
    if weight not in OPERATING_WEIGHTS:
        report.error(f"charter has invalid operating_weight: {weight}")
        return "managed", True
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
    schema_13 = schema_at_least(charter.get("schema_version"), 1, 3)
    if schema_at_least(charter.get("schema_version"), 1, 1):
        require_keys(
            charter,
            ("program_id", "epoch_id", "operating_weight", "governance_admission_proof"),
            "charter schema 1.1",
            report,
        )
        program_id = charter.get("program_id")
        epoch_id = charter.get("epoch_id")
        if schema_13:
            if (program_id is None) != (epoch_id is None):
                report.error("charter schema 1.3 requires program_id and epoch_id together or both null")
            for key, value in (("program_id", program_id), ("epoch_id", epoch_id)):
                if value is not None and (not isinstance(value, str) or not value):
                    report.error(f"charter schema 1.3 {key} must be null or a non-empty string")
        else:
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
        for key in ("research_question", "success_criteria", "failure_criteria", "stop_conditions"):
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
        if explicit_track and not protocol.get("data_boundary"):
            report.error("ready charter requires protocol.data_boundary")
        task_type = charter.get("task_type")
        if schema_13 and task_type == "engineering":
            for key in ("code_version", "real_carrier_path", "profile_metrics", "analysis_plan"):
                if not protocol.get(key):
                    report.error(f"ready engineering profile requires protocol.{key}")
            if protocol.get("utility_blind") is not True:
                report.error("ready engineering profile requires protocol.utility_blind=true")
        elif task_type in {"experiment", "mixed"}:
            if not charter.get("primary_metrics"):
                report.error("ready experimental charter requires non-empty primary_metrics")
            required = [
                "code_version",
                "data_version",
                "data_split",
                "seed_policy",
                "analysis_plan",
            ]
            if schema_13:
                required.extend(("dataset_name", "run_bindings"))
            for key in required:
                value = protocol.get(key)
                if key == "run_bindings":
                    if not isinstance(value, dict):
                        report.error("ready experimental charter requires protocol.run_bindings object")
                elif not value:
                    report.error(f"ready experimental charter requires protocol.{key}")
            if schema_13 and track == "scout":
                design = protocol.get("scout_design")
                if not isinstance(design, dict):
                    report.error("ready Scout experiment requires protocol.scout_design")
                else:
                    arms = design.get("arms")
                    if not isinstance(arms, list) or not 2 <= len(arms) <= 3:
                        report.error("ready first Scout requires 2 or 3 protocol.scout_design.arms")
                    if design.get("paired_bundles") != 6:
                        report.error("ready first Scout requires protocol.scout_design.paired_bundles=6")
                    for key in (
                        "mpe",
                        "guard_comparator",
                        "outcome_action_table",
                        "compute_cap",
                    ):
                        if not design.get(key):
                            report.error(f"ready first Scout requires protocol.scout_design.{key}")
            if schema_13 and track == "confirmatory":
                for key in (
                    "power_plan",
                    "multiplicity_plan",
                    "full_baseline_scope",
                    "external_validity_scope",
                ):
                    if not protocol.get(key):
                        report.error(f"ready Confirmatory charter requires protocol.{key}")
    return track, explicit_track, weight, explicit_weight


def validate_run(
    root: Path,
    path: Path,
    run: dict[str, Any],
    charter: dict[str, Any],
    task_id: str,
    report: Report,
) -> tuple[bool, list[str]]:
    context = f"run {path.name}"
    ineligible: list[str] = []

    def mark_ineligible(reason: str) -> None:
        if reason not in ineligible:
            ineligible.append(reason)

    require_keys(run, ("schema_version", "run_id", "task_id", "status", "question", "started_at"), context, report)
    if run.get("task_id") != task_id:
        report.error(f"{context} task_id does not match charter")
        mark_ineligible("task_id differs from the frozen charter")
    if run.get("status") not in RUN_STATUSES:
        report.error(f"{context} has invalid status: {run.get('status')}")
        mark_ineligible("run status is invalid")
    if not parse_time(run.get("started_at")):
        report.error(f"{context} requires valid started_at")
        mark_ineligible("started_at is invalid")
    completed = run.get("status") == "completed"

    # Digest declarations bind bytes at every lifecycle state. A running run
    # may omit these fields, but it cannot declare a digest and defer checking
    # it until completion.
    config = run.get("config")
    if config is not None:
        if not isinstance(config, dict):
            report.error(f"{context} config must be an object")
        elif config.get("path") or config.get("sha256") or completed:
            if not config.get("path") or not config.get("sha256"):
                report.error(f"{context} requires config.path and config.sha256")
            else:
                validate_declared_local_sha256(
                    root,
                    config.get("path"),
                    config.get("sha256"),
                    f"{context} config",
                    report,
                )
    elif completed:
        report.error(f"{context} requires config.path and config.sha256")

    artifacts = run.get("artifacts")
    if artifacts is not None and not isinstance(artifacts, list):
        report.error(f"{context} artifacts must be a non-empty list")
        artifacts = []
    for artifact in artifacts or []:
        if isinstance(artifact, dict):
            validate_declared_local_sha256(
                root,
                artifact.get("path"),
                artifact.get("sha256"),
                f"{context} artifact",
                report,
            )
            continue
        if not isinstance(artifact, str) or not artifact:
            report.error(
                f"{context} artifact entries must be non-empty strings or path/sha256 objects"
            )
            continue
        if not completed:
            continue
        try:
            parsed = urlsplit(artifact)
        except ValueError as exc:
            report.error(f"{context} legacy artifact has an invalid path or URI: {exc}")
            continue
        if parsed.scheme and parsed.scheme.lower() != "file":
            continue
        if parsed.scheme.lower() == "file":
            if parsed.netloc not in {"", "localhost"} or parsed.query or parsed.fragment:
                report.error(f"{context} legacy artifact has an invalid local file URI")
                continue
            artifact_path = Path(unquote(parsed.path))
        else:
            artifact_path = Path(artifact)
            if not artifact_path.is_absolute():
                artifact_path = root / artifact_path
        try:
            exists = artifact_path.is_file()
        except (OSError, ValueError):
            exists = False
        if not exists:
            report.error(f"{context} references missing artifact: {artifact}")

    if not completed:
        mark_ineligible(f"run status is {run.get('status')}, not completed")
        report.warn(f"{context} is evidence-ineligible: {'; '.join(ineligible)}")
        return False, ineligible
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
                mark_ineligible("validation record is malformed")
            elif item.get("status") == "fail":
                mark_ineligible("at least one recorded validation command failed")
    else:
        mark_ineligible("validation is not a list")

    deviations = run.get("protocol_deviations")
    if not isinstance(deviations, list):
        report.error(f"{context} protocol_deviations must be a list")
        mark_ineligible("protocol_deviations is malformed")
    elif deviations:
        mark_ineligible("protocol_deviations is non-empty")

    if schema_at_least(charter.get("schema_version"), 1, 3):
        protocol = charter.get("protocol")
        bindings = protocol.get("run_bindings") if isinstance(protocol, dict) else None
        run_id = run.get("run_id")
        binding = bindings.get(run_id) if isinstance(bindings, dict) and isinstance(run_id, str) else None
        if not isinstance(binding, dict):
            mark_ineligible("run_id has no prospectively frozen protocol.run_bindings entry")
        else:
            required_binding_keys = (
                "question",
                "code_version",
                "config_sha256",
                "dataset",
                "seeds",
                "primary_metrics",
            )
            missing = [key for key in required_binding_keys if key not in binding]
            if missing:
                mark_ineligible(
                    "frozen run binding is incomplete: " + ", ".join(sorted(missing))
                )
            if binding.get("question") != run.get("question"):
                mark_ineligible("question differs from the frozen run binding")
            expected_code = binding.get("code_version")
            actual_code = run.get("code_version")
            if expected_code != actual_code:
                mark_ineligible("code_version differs from the frozen run binding")
            expected_config_sha = binding.get("config_sha256")
            actual_config_sha = (
                run.get("config", {}).get("sha256")
                if isinstance(run.get("config"), dict)
                else None
            )
            if not isinstance(expected_config_sha, str) or not SHA256_PATTERN.fullmatch(
                expected_config_sha
            ):
                mark_ineligible("frozen config_sha256 is not canonical 64-hex")
            elif not isinstance(actual_config_sha, str) or (
                expected_config_sha.lower() != actual_config_sha.lower()
            ):
                mark_ineligible("config sha256 differs from the frozen run binding")
            for key in ("dataset", "seeds", "primary_metrics"):
                if binding.get(key) != run.get(key):
                    mark_ineligible(f"{key} differs from the frozen run binding")

        frozen_at = (
            parse_time(protocol.get("frozen_at")) if isinstance(protocol, dict) else None
        )
        started_at = parse_time(run.get("started_at"))
        if frozen_at is None or started_at is None or frozen_at > started_at:
            mark_ineligible("protocol was not frozen before the run started")

    if ineligible:
        report.warn(f"{context} is evidence-ineligible: {'; '.join(ineligible)}")
    return not ineligible, ineligible


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--ready", action="store_true", help="enforce ready-to-run charter gates")
    parser.add_argument(
        "--legacy-read",
        action="store_true",
        help="inspect a pre-1.3 task without granting readiness, evidence, or claim authority",
    )
    parser.add_argument("--max-heartbeat-age-minutes", type=int, default=180)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.ready and args.legacy_read:
        print("ERROR: --legacy-read cannot be combined with --ready")
        print("FAIL: legacy state cannot grant readiness or evidence authority")
        return 2
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
    legacy_schema = not schema_at_least(charter.get("schema_version"), 1, 3)
    if legacy_schema:
        if args.legacy_read:
            report.warn(
                "legacy task is being inspected read-only; this result grants no readiness, "
                "evidence-eligibility, or claim authority"
            )
        else:
            report.error(
                "task schema is older than 1.3; use --legacy-read for non-authoritative "
                "inspection or migrate prospectively before new evidence"
            )
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
            and callback_state in {"delivered", "acknowledged"}
            and watchdog_state not in {"paused", "not_required"}
        ):
            report.error(
                f"delivered terminal worker record {worker_record_id} must pause or omit its watchdog"
            )
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
    run_eligibility: dict[str, tuple[bool, list[str]]] = {}
    for path in sorted((root / "runs").glob("*.json")):
        run = load_json(path, report)
        eligible, reasons = validate_run(root, path, run, charter, task_id, report)
        run_id = run.get("run_id")
        if isinstance(run_id, str) and run_id:
            if run_id in run_index:
                report.error(f"duplicate run_id: {run_id}")
            run_index[run_id] = run
            run_eligibility[run_id] = (eligible, reasons)

    schema_13 = schema_at_least(charter.get("schema_version"), 1, 3)
    evidence_identities: dict[str, dict[str, Any]] = {}

    def resolve_worker(worker_id: Any, context: str) -> dict[str, Any] | None:
        if not isinstance(worker_id, str) or not worker_id:
            report.error(f"{context} requires a non-empty registered worker_id")
            return None
        latest = latest_worker_records.get(worker_id)
        if latest is None:
            report.error(f"{context} references unknown worker_id {worker_id}")
            return None
        return latest[1]

    for evidence_id, record in evidence_index.items():
        require_keys(record, ("kind", "summary", "provenance", "verification", "supports_claims", "limitations"), f"evidence {evidence_id}", report)
        if record.get("kind") not in EVIDENCE_KINDS:
            report.error(f"evidence {evidence_id} has invalid kind: {record.get('kind')}")
        provenance = record.get("provenance", {})
        captured_at = (
            parse_time(provenance.get("captured_at")) if isinstance(provenance, dict) else None
        )
        if not isinstance(provenance, dict) or not provenance.get("source") or captured_at is None:
            report.error(f"evidence {evidence_id} requires provenance source and captured_at")
        elif provenance.get("artifact_sha256") is not None:
            validate_declared_local_sha256(
                root,
                provenance.get("source"),
                provenance.get("artifact_sha256"),
                f"evidence {evidence_id} provenance",
                report,
            )
        verification = record.get("verification", {})
        verification_status = (
            verification.get("status") if isinstance(verification, dict) else None
        )
        if verification_status not in VERIFICATION_STATUSES:
            report.error(f"evidence {evidence_id} has invalid verification status")

        run_id = record.get("run_id")
        if record.get("kind") in {"experiment", "negative_result"}:
            if not run_id:
                report.error(f"evidence {evidence_id} requires run_id")
            elif run_id not in run_index:
                report.error(f"evidence {evidence_id} references missing run {run_id}")
            elif verification_status == "verified":
                eligible, reasons = run_eligibility.get(str(run_id), (False, ["eligibility unknown"]))
                if not eligible:
                    report.error(
                        f"verified evidence {evidence_id} references evidence-ineligible run "
                        f"{run_id}: {'; '.join(reasons)}"
                    )

        if schema_13 and verification_status == "verified":
            producer_worker_id = record.get("producer_worker_id")
            verifier_worker_id = (
                verification.get("verifier_worker_id")
                if isinstance(verification, dict)
                else None
            )
            producer = resolve_worker(
                producer_worker_id, f"verified evidence {evidence_id} producer"
            )
            verifier = resolve_worker(
                verifier_worker_id, f"verified evidence {evidence_id} verifier"
            )
            verified_at = (
                parse_time(verification.get("verified_at"))
                if isinstance(verification, dict)
                else None
            )
            if verified_at is None:
                report.error(f"verified evidence {evidence_id} requires verification.verified_at")
            elif captured_at is not None and verified_at < captured_at:
                report.error(f"verified evidence {evidence_id} was verified before capture")
            if verifier is not None and str(verifier.get("role", "")).casefold() != "audit":
                report.error(
                    f"verified evidence {evidence_id} verifier must have canonical Audit role"
                )
            if (
                producer is not None
                and verifier is not None
                and (
                    producer_worker_id == verifier_worker_id
                    or producer.get("thread_id") == verifier.get("thread_id")
                )
            ):
                report.error(
                    f"verified evidence {evidence_id} producer and Audit verifier must use "
                    "distinct registered workers and threads"
                )
            evidence_identities[evidence_id] = {
                "producer_worker_id": producer_worker_id,
                "producer_thread_id": producer.get("thread_id") if producer else None,
                "verifier_worker_id": verifier_worker_id,
                "verifier_thread_id": verifier.get("thread_id") if verifier else None,
                "verified_at": verified_at,
            }

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
            elif claim_id not in evidence_index[evidence_id].get("supports_claims", []):
                report.error(f"claim {claim_id} and evidence {evidence_id} are not linked bidirectionally")
        if claim.get("status") in {"supported", "accepted"}:
            for evidence_id in evidence_ids:
                status = evidence_index.get(evidence_id, {}).get("verification", {}).get("status")
                if status != "verified":
                    report.error(
                        f"claim {claim_id} status {claim.get('status')} uses non-verified evidence "
                        f"{evidence_id}"
                    )
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
                if schema_13:
                    reviewer_worker_id = adjudication.get("reviewer_worker_id")
                    reviewer = resolve_worker(
                        reviewer_worker_id, f"accepted claim {claim_id} reviewer"
                    )
                    decided_at = parse_time(adjudication.get("decided_at"))
                    if str(adjudication.get("reviewer_role", "")).casefold() != "audit":
                        report.error(
                            f"accepted claim {claim_id} reviewer_role must be canonical Audit"
                        )
                    if reviewer is not None and str(reviewer.get("role", "")).casefold() != "audit":
                        report.error(
                            f"accepted claim {claim_id} reviewer must have canonical Audit role"
                        )
                    for evidence_id in evidence_ids:
                        identities = evidence_identities.get(evidence_id, {})
                        other_workers = {
                            identities.get("producer_worker_id"),
                            identities.get("verifier_worker_id"),
                        }
                        other_threads = {
                            identities.get("producer_thread_id"),
                            identities.get("verifier_thread_id"),
                        }
                        if reviewer_worker_id in other_workers or (
                            reviewer is not None and reviewer.get("thread_id") in other_threads
                        ):
                            report.error(
                                f"accepted claim {claim_id} reviewer must be distinct from "
                                f"evidence {evidence_id} producer and verifier workers/threads"
                            )
                        verified_at = identities.get("verified_at")
                        if (
                            isinstance(verified_at, datetime)
                            and decided_at is not None
                            and decided_at < verified_at
                        ):
                            report.error(
                                f"accepted claim {claim_id} was adjudicated before evidence "
                                f"{evidence_id} verification"
                            )

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
    if args.legacy_read:
        print(
            "LEGACY_READ_ONLY: structural inspection completed; no readiness, "
            "evidence-eligibility, or claim authority was granted"
        )
        return 2
    print(
        f"PASS: governance_track={governance_track}, operating_weight={operating_weight}, "
        f"0 errors, {len(report.warnings)} warning(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
