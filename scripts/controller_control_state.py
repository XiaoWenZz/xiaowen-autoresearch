#!/usr/bin/env python3
"""Validate and atomically update the rebuildable Controller control snapshot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = 2
LIFECYCLES = {"DELEGATED", "BLOCKED", "DONE"}
CANDIDATE_STATES = {"OPEN", "BLOCKED", "CLOSED"}
CLOSURE_BASES = {"VALID_SCIENTIFIC_NEGATIVE", "EXTERNAL_IMPOSSIBILITY"}
EXTERNAL_IMPOSSIBILITY_REASONS = {
    "DATA_UNAVAILABLE",
    "HARDWARE_UNAVAILABLE",
    "IRRETRIEVABLE_REQUIRED_EVIDENCE",
    "LEGAL_OR_LICENSE_PROHIBITION",
    "REQUIRED_AUTHORITY_UNAVAILABLE",
    "SERVICE_OR_API_UNAVAILABLE",
}
ROLE_STATES = {"ACTIVE", "WAITING_EXTERNAL", "HOLD", "BLOCKED"}
WAKE_STATES = {"NONE", "CLAIMED", "SENT"}
TITLE_RE = re.compile(r"^(Controller|Explorer|Audit|Executor) · .+ · (ACTIVE|WAITING_EXTERNAL|HOLD|BLOCKED)$")
UNIT_RE = re.compile(r"^[A-Za-z0-9_.@:-]+\.service$")
REMOTE_HOSTS = {"dual5090", "ecnuhpc"}
REMOTE_OUTPUT_ROOTS = (PurePosixPath("/home/xiaowen/runs"), PurePosixPath("/home/xiaowen/projects"))


class StateError(ValueError):
    pass


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require(mapping: dict[str, Any], keys: tuple[str, ...], where: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise StateError(f"{where} missing keys: {', '.join(missing)}")


def validate_state(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise StateError("state must be a JSON object")
    _require(
        state,
        (
            "schema_version",
            "revision",
            "updated_at",
            "controller",
            "objectives",
            "managed_roles",
            "remote_jobs",
            "absorbed_terminal_event_ids",
        ),
        "state",
    )
    if state["schema_version"] != SCHEMA_VERSION:
        raise StateError(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(state["revision"], int) or state["revision"] < 0:
        raise StateError("revision must be a non-negative integer")
    if not _nonempty(state["updated_at"]):
        raise StateError("updated_at must be non-empty")

    controller = state["controller"]
    if not isinstance(controller, dict):
        raise StateError("controller must be an object")
    _require(controller, ("thread_id", "project_id", "cwd", "title", "pin_required"), "controller")
    for key in ("thread_id", "project_id", "cwd", "title"):
        if not _nonempty(controller[key]):
            raise StateError(f"controller.{key} must be non-empty")
    if controller["pin_required"] is not True:
        raise StateError("controller.pin_required must be true")
    if not TITLE_RE.fullmatch(controller["title"]):
        raise StateError("controller.title is not canonical")

    objectives = state["objectives"]
    if not isinstance(objectives, list):
        raise StateError("objectives must be a list")
    objective_ids: set[str] = set()
    for index, objective in enumerate(objectives):
        where = f"objectives[{index}]"
        if not isinstance(objective, dict):
            raise StateError(f"{where} must be an object")
        _require(
            objective,
            (
                "objective_id",
                "candidate_id",
                "candidate_state",
                "stage",
                "scientific_outcome",
                "lifecycle",
                "next_action",
            ),
            where,
        )
        for key in (
            "objective_id",
            "candidate_id",
            "candidate_state",
            "stage",
            "scientific_outcome",
            "next_action",
        ):
            if not _nonempty(objective[key]):
                raise StateError(f"{where}.{key} must be non-empty")
        if objective["objective_id"] in objective_ids:
            raise StateError(f"duplicate objective_id {objective['objective_id']}")
        objective_ids.add(objective["objective_id"])
        lifecycle = objective["lifecycle"]
        if lifecycle not in LIFECYCLES:
            raise StateError(f"{where}.lifecycle must be one of {sorted(LIFECYCLES)}")
        candidate_state = objective["candidate_state"]
        if candidate_state not in CANDIDATE_STATES:
            raise StateError(f"{where}.candidate_state must be one of {sorted(CANDIDATE_STATES)}")
        if lifecycle == "DELEGATED":
            _require(objective, ("owner_thread_id", "owner_role", "owner_state"), where)
            if not all(_nonempty(objective[key]) for key in ("owner_thread_id", "owner_role", "owner_state")):
                raise StateError(f"{where} delegated owner fields must be non-empty")
            if objective["owner_state"] not in ROLE_STATES:
                raise StateError(f"{where}.owner_state must be canonical")
        else:
            blocker = objective.get("blocker")
            if lifecycle == "BLOCKED":
                if not isinstance(blocker, dict):
                    raise StateError(f"{where}.blocker must be an object")
                _require(blocker, ("reopening_fact", "observer", "trigger"), f"{where}.blocker")
                if not all(_nonempty(blocker[key]) for key in ("reopening_fact", "observer", "trigger")):
                    raise StateError(f"{where}.blocker fields must be non-empty")
            if lifecycle == "DONE" and not _nonempty(objective.get("reopening_fact")):
                raise StateError(f"{where}.reopening_fact is required for DONE")

        if candidate_state == "BLOCKED":
            blocker = objective.get("blocker")
            if not isinstance(blocker, dict):
                raise StateError(f"{where}.blocker must be an object for blocked candidate")
            _require(blocker, ("reopening_fact", "observer", "trigger"), f"{where}.blocker")
            if not all(_nonempty(blocker[key]) for key in ("reopening_fact", "observer", "trigger")):
                raise StateError(f"{where}.blocker fields must be non-empty")

        closure = objective.get("idea_closure")
        if candidate_state != "CLOSED":
            if closure is not None:
                raise StateError(f"{where}.idea_closure is only valid for closed candidates")
            continue
        if lifecycle != "DONE":
            raise StateError(f"{where} closed candidate must have lifecycle DONE")
        if not isinstance(closure, dict):
            raise StateError(f"{where}.idea_closure must be an object for closed candidate")
        _require(
            closure,
            ("basis", "scope", "evidence_ref", "reopening_fact"),
            f"{where}.idea_closure",
        )
        if closure["basis"] not in CLOSURE_BASES:
            raise StateError(f"{where}.idea_closure.basis must be one of {sorted(CLOSURE_BASES)}")
        if not all(_nonempty(closure[key]) for key in ("scope", "evidence_ref", "reopening_fact")):
            raise StateError(f"{where}.idea_closure required fields must be non-empty")
        if closure["basis"] == "VALID_SCIENTIFIC_NEGATIVE":
            _require(
                closure,
                (
                    "independent_audit_terminal_id",
                    "evidence_eligible",
                    "prospective_action_table_pass",
                    "power_or_futility_pass",
                ),
                f"{where}.idea_closure",
            )
            if not _nonempty(closure["independent_audit_terminal_id"]):
                raise StateError(f"{where}.idea_closure independent Audit must be bound")
            for key in ("evidence_eligible", "prospective_action_table_pass", "power_or_futility_pass"):
                if closure[key] is not True:
                    raise StateError(f"{where}.idea_closure.{key} must be true")
        else:
            _require(
                closure,
                ("reason_code", "observer", "trigger", "unavoidable"),
                f"{where}.idea_closure",
            )
            if closure["reason_code"] not in EXTERNAL_IMPOSSIBILITY_REASONS:
                raise StateError(f"{where}.idea_closure.reason_code is not an allowed external impossibility")
            if not _nonempty(closure["observer"]) or not _nonempty(closure["trigger"]):
                raise StateError(f"{where}.idea_closure external observer/trigger must be non-empty")
            if closure["unavoidable"] is not True:
                raise StateError(f"{where}.idea_closure.unavoidable must be true")

    roles = state["managed_roles"]
    if not isinstance(roles, list):
        raise StateError("managed_roles must be a list")
    role_threads: set[str] = set()
    for index, role in enumerate(roles):
        where = f"managed_roles[{index}]"
        if not isinstance(role, dict):
            raise StateError(f"{where} must be an object")
        _require(role, ("thread_id", "role", "title", "state", "pin_required", "cursor"), where)
        if role["thread_id"] in role_threads:
            raise StateError(f"duplicate managed role thread_id {role['thread_id']}")
        role_threads.add(role["thread_id"])
        if not all(_nonempty(role[key]) for key in ("thread_id", "role", "title", "state")):
            raise StateError(f"{where} identity fields must be non-empty")
        if role["state"] not in ROLE_STATES:
            raise StateError(f"{where}.state must be canonical")
        if role["pin_required"] is not True:
            raise StateError(f"{where}.pin_required must be true")
        if not TITLE_RE.fullmatch(role["title"]):
            raise StateError(f"{where}.title is not canonical")
        if role["cursor"] is not None and not _nonempty(role["cursor"]):
            raise StateError(f"{where}.cursor must be null or non-empty")

    role_by_thread = {role["thread_id"]: role for role in roles}
    for index, objective in enumerate(objectives):
        if objective["lifecycle"] != "DELEGATED":
            continue
        where = f"objectives[{index}]"
        role = role_by_thread.get(objective["owner_thread_id"])
        if role is None:
            raise StateError(f"{where}.owner_thread_id is not an active managed role")
        if role["role"] != objective["owner_role"] or role["state"] != objective["owner_state"]:
            raise StateError(f"{where} owner identity/state does not match managed role")

    jobs = state["remote_jobs"]
    if not isinstance(jobs, list):
        raise StateError("remote_jobs must be a list")
    job_ids: set[str] = set()
    for index, job in enumerate(jobs):
        where = f"remote_jobs[{index}]"
        if not isinstance(job, dict):
            raise StateError(f"{where} must be an object")
        _require(
            job,
            (
                "job_id",
                "objective_id",
                "owner_thread_id",
                "host",
                "unit",
                "output_path",
                "expected_files",
                "eta",
                "late_threshold",
                "monitor_state",
                "wake_delivery",
            ),
            where,
        )
        for key in ("job_id", "objective_id", "owner_thread_id", "host", "unit", "output_path", "eta", "late_threshold", "monitor_state"):
            if not _nonempty(job[key]):
                raise StateError(f"{where}.{key} must be non-empty")
        if job["job_id"] in job_ids:
            raise StateError(f"duplicate job_id {job['job_id']}")
        job_ids.add(job["job_id"])
        if job["objective_id"] not in objective_ids:
            raise StateError(f"{where}.objective_id is unknown")
        if job["owner_thread_id"] not in role_threads:
            raise StateError(f"{where}.owner_thread_id is not an active managed role")
        if job["host"] not in REMOTE_HOSTS:
            raise StateError(f"{where}.host is not allowlisted")
        if not UNIT_RE.fullmatch(job["unit"]):
            raise StateError(f"{where}.unit is unsafe")
        output_path = PurePosixPath(job["output_path"])
        if not output_path.is_absolute() or not any(output_path.is_relative_to(root) for root in REMOTE_OUTPUT_ROOTS):
            raise StateError(f"{where}.output_path is outside allowlisted roots")
        if not isinstance(job["expected_files"], list) or not all(_nonempty(item) for item in job["expected_files"]):
            raise StateError(f"{where}.expected_files must contain non-empty names")
        if any(PurePosixPath(item).name != item or item in {".", ".."} for item in job["expected_files"]):
            raise StateError(f"{where}.expected_files must be basenames")
        if job["monitor_state"] not in {"ACTIVE", "TERMINAL_OBSERVED"}:
            raise StateError(f"{where}.monitor_state is invalid")
        wake = job["wake_delivery"]
        if not isinstance(wake, dict):
            raise StateError(f"{where}.wake_delivery must be an object")
        _require(wake, ("state", "claim_token", "observation_id"), f"{where}.wake_delivery")
        if wake["state"] not in WAKE_STATES:
            raise StateError(f"{where}.wake_delivery.state is invalid")
        if wake["state"] == "NONE":
            if wake["claim_token"] is not None or wake["observation_id"] is not None:
                raise StateError(f"{where}.wake_delivery NONE must have null identifiers")
        elif not _nonempty(wake["claim_token"]) or not _nonempty(wake["observation_id"]):
            raise StateError(f"{where}.wake_delivery claimed identifiers must be non-empty")

    events = state["absorbed_terminal_event_ids"]
    if not isinstance(events, list) or not all(_nonempty(item) for item in events):
        raise StateError("absorbed_terminal_event_ids must be a list of non-empty strings")
    if len(events) != len(set(events)):
        raise StateError("absorbed_terminal_event_ids contains duplicates")
    return state


def canonical_bytes(state: dict[str, Any]) -> bytes:
    return (json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def checksum_path(state_path: Path) -> Path:
    return state_path.with_name(state_path.name + ".sha256")


def read_state(path: Path, *, verify_checksum: bool = True) -> dict[str, Any]:
    data = path.read_bytes()
    state = validate_state(json.loads(data))
    if verify_checksum:
        sidecar = checksum_path(path)
        if not sidecar.is_file():
            raise StateError(f"missing checksum sidecar {sidecar}")
        expected = sidecar.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(data).hexdigest()
        if expected != actual:
            raise StateError("state checksum mismatch")
    return state


def _atomic_write(path: Path, data: bytes, mode: int = 0o640) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def write_state(path: Path, state: dict[str, Any], expected_revision: int) -> dict[str, Any]:
    current_revision = -1
    if path.exists():
        current_revision = read_state(path)["revision"]
    if current_revision != expected_revision:
        raise StateError(f"revision conflict: expected {expected_revision}, found {current_revision}")
    updated = copy.deepcopy(state)
    updated["schema_version"] = SCHEMA_VERSION
    updated["revision"] = expected_revision + 1
    updated["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    validate_state(updated)
    data = canonical_bytes(updated)
    digest = hashlib.sha256(data).hexdigest()
    _atomic_write(path, data)
    _atomic_write(checksum_path(path), f"{digest}  {path.name}\n".encode("utf-8"))
    return updated


def find_job(state: dict[str, Any], job_id: str) -> dict[str, Any]:
    for job in state["remote_jobs"]:
        if job["job_id"] == job_id:
            return job
    raise StateError(f"unknown job_id {job_id}")


def cmd_replace(args: argparse.Namespace) -> None:
    candidate = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = write_state(Path(args.state), candidate, args.expected_revision)
    print(json.dumps({"status": "PASS", "revision": result["revision"]}, sort_keys=True))


def cmd_validate(args: argparse.Namespace) -> None:
    state = read_state(Path(args.state))
    print(json.dumps({"status": "PASS", "revision": state["revision"]}, sort_keys=True))


def cmd_show(args: argparse.Namespace) -> None:
    state = read_state(Path(args.state))
    print(canonical_bytes(state).decode("utf-8"), end="")


def cmd_claim(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = read_state(path)
    job = find_job(state, args.job_id)
    wake = job["wake_delivery"]
    if wake["state"] != "NONE":
        raise StateError(f"job wake already {wake['state']}")
    job["monitor_state"] = "TERMINAL_OBSERVED"
    job["wake_delivery"] = {
        "state": "CLAIMED",
        "claim_token": args.claim_token,
        "observation_id": args.observation_id,
    }
    result = write_state(path, state, args.expected_revision)
    print(json.dumps({"status": "PASS", "revision": result["revision"], "delivery": "CLAIMED"}, sort_keys=True))


def cmd_complete(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = read_state(path)
    job = find_job(state, args.job_id)
    wake = job["wake_delivery"]
    if wake["state"] != "CLAIMED" or wake["claim_token"] != args.claim_token:
        raise StateError("job wake claim does not match")
    wake["state"] = "SENT"
    result = write_state(path, state, args.expected_revision)
    print(json.dumps({"status": "PASS", "revision": result["revision"], "delivery": "SENT"}, sort_keys=True))


def cmd_advance_cursors(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = read_state(path)
    updates = json.loads(args.updates_json)
    if not isinstance(updates, list) or not updates:
        raise StateError("cursor updates must be a non-empty list")
    roles = {role["thread_id"]: role for role in state["managed_roles"]}
    seen: set[str] = set()
    for index, update in enumerate(updates):
        where = f"cursor_updates[{index}]"
        if not isinstance(update, dict):
            raise StateError(f"{where} must be an object")
        _require(update, ("thread_id", "expected_cursor", "new_cursor"), where)
        thread_id = update["thread_id"]
        if not _nonempty(thread_id) or thread_id in seen:
            raise StateError(f"{where}.thread_id is invalid or duplicate")
        seen.add(thread_id)
        role = roles.get(thread_id)
        if role is None:
            raise StateError(f"{where}.thread_id is not an active managed role")
        if update["expected_cursor"] != role["cursor"]:
            raise StateError(f"{where}.expected_cursor does not match")
        if not _nonempty(update["new_cursor"]):
            raise StateError(f"{where}.new_cursor must be non-empty")
        role["cursor"] = update["new_cursor"]
    result = write_state(path, state, args.expected_revision)
    print(json.dumps({"status": "PASS", "revision": result["revision"], "advanced": len(updates)}, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("validate", cmd_validate), ("show", cmd_show)):
        sub = subparsers.add_parser(name)
        sub.add_argument("--state", required=True)
        sub.set_defaults(handler=handler)
    replace = subparsers.add_parser("replace")
    replace.add_argument("--state", required=True)
    replace.add_argument("--input", required=True)
    replace.add_argument("--expected-revision", type=int, required=True)
    replace.set_defaults(handler=cmd_replace)
    claim = subparsers.add_parser("claim-job-wake")
    claim.add_argument("--state", required=True)
    claim.add_argument("--job-id", required=True)
    claim.add_argument("--expected-revision", type=int, required=True)
    claim.add_argument("--claim-token", required=True)
    claim.add_argument("--observation-id", required=True)
    claim.set_defaults(handler=cmd_claim)
    complete = subparsers.add_parser("complete-job-wake")
    complete.add_argument("--state", required=True)
    complete.add_argument("--job-id", required=True)
    complete.add_argument("--expected-revision", type=int, required=True)
    complete.add_argument("--claim-token", required=True)
    complete.set_defaults(handler=cmd_complete)
    advance = subparsers.add_parser("advance-cursors")
    advance.add_argument("--state", required=True)
    advance.add_argument("--expected-revision", type=int, required=True)
    advance.add_argument("--updates-json", required=True)
    advance.set_defaults(handler=cmd_advance_cursors)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except (OSError, json.JSONDecodeError, StateError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
