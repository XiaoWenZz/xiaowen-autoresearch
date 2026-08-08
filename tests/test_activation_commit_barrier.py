from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.controller_control_state import (
    canonical_bytes,
    completion_binding_sha256,
    validate_state,
)


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "controller_control_state.py"
OLD_EVENT = "TERM-RACE-PREDECESSOR"
NEW_BINDING = {
    "task_id": "task-successor",
    "dispatch_id": "dispatch-successor",
    "lease_epoch": 2,
    "contract_revision": "contract-successor",
    "terminal_event_id": "TERM-RACE-SUCCESSOR",
    "terminal_path": "/private/tmp/TERM-RACE-SUCCESSOR.json",
}


def state_at_revision(revision: int, *, activated: bool) -> dict:
    if activated:
        objective = {
            "objective_id": "successor-objective",
            "candidate_id": "candidate-race",
            "candidate_state": "OPEN",
            "stage": "R1_IMPLEMENTATION",
            "scientific_outcome": "UNOBSERVED",
            "lifecycle": "DELEGATED",
            "next_action": "CONTINUE_AFTER_DURABLE_ACTIVATION",
            "owner_thread_id": "worker-successor",
            "owner_role": "Executor",
            "owner_state": "ACTIVE",
            "completion_binding": NEW_BINDING,
        }
        managed_role = {
            "thread_id": "worker-successor",
            "role": "Executor",
            "title": "Executor · Race Successor · ACTIVE",
            "state": "ACTIVE",
            "pin_required": True,
            "cursor": None,
        }
        absorbed = [OLD_EVENT]
    else:
        old_binding = {
            "task_id": "task-predecessor",
            "dispatch_id": "dispatch-predecessor",
            "lease_epoch": 1,
            "contract_revision": "contract-predecessor",
            "terminal_event_id": OLD_EVENT,
            "terminal_path": f"/private/tmp/{OLD_EVENT}.json",
        }
        objective = {
            "objective_id": "predecessor-objective",
            "candidate_id": "candidate-race",
            "candidate_state": "OPEN",
            "stage": "R1_AUDIT",
            "scientific_outcome": "UNOBSERVED",
            "lifecycle": "DELEGATED",
            "next_action": "CONTROLLER_ACTIVATE_SUCCESSOR",
            "owner_thread_id": "worker-predecessor",
            "owner_role": "Audit",
            "owner_state": "TERMINAL_PENDING_ABSORPTION",
            "completion_binding": old_binding,
        }
        managed_role = {
            "thread_id": "worker-predecessor",
            "role": "Audit",
            "title": "Audit · Race Predecessor · TERMINAL_PENDING_ABSORPTION",
            "state": "TERMINAL_PENDING_ABSORPTION",
            "pin_required": True,
            "cursor": None,
        }
        absorbed = []
        pending = [
            {
                "terminal_event_id": OLD_EVENT,
                "objective_id": "predecessor-objective",
                "owner_thread_id": "worker-predecessor",
                "owner_role": "Audit",
                "completion_binding_sha256": completion_binding_sha256(old_binding),
                "terminal_path": old_binding["terminal_path"],
                "terminal_bytes": 1,
                "terminal_sha256": "a" * 64,
                "terminal_cursor": "terminal-cursor",
                "source_final_turn_id": "source-final-turn",
                "observation_id": "observation-1",
                "observed_at": "2026-08-09T00:00:00Z",
                "verification_state": "CONTROLLER_VERIFIED",
                "controller_verification_ref": "controller-turn-1",
            }
        ]
    if activated:
        pending = []
    state = {
        "schema_version": 5,
        "revision": revision,
        "updated_at": "2026-08-09T00:00:00Z",
        "controller": {
            "thread_id": "controller-1",
            "project_id": "project-1",
            "cwd": "/workspace",
            "title": "Controller · Research · ACTIVE",
            "pin_required": True,
        },
        "objectives": [objective],
        "managed_roles": [managed_role],
        "remote_jobs": [],
        "advisory_reads": [],
        "absorbed_advisory_scopes": [],
        "pending_absorptions": pending,
        "absorbed_terminal_event_ids": absorbed,
    }
    return validate_state(state)


def write_state_fixture(path: Path, state: dict) -> bytes:
    data = canonical_bytes(state)
    path.write_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
        encoding="utf-8",
    )
    return data


def barrier_command(state_path: Path, **overrides: str) -> list[str]:
    values = {
        "minimum_revision": "655",
        "objective_id": "successor-objective",
        "owner_thread_id": "worker-successor",
        "owner_role": "Executor",
        "completion_binding_json": json.dumps(NEW_BINDING, sort_keys=True),
        "absorbed_terminal_event_id": OLD_EVENT,
        "timeout_ms": "0",
        "poll_ms": "1",
    }
    values.update(overrides)
    return [
        sys.executable,
        str(TOOL),
        "await-successor-activation",
        "--state",
        str(state_path),
        "--minimum-revision",
        values["minimum_revision"],
        "--objective-id",
        values["objective_id"],
        "--owner-thread-id",
        values["owner_thread_id"],
        "--owner-role",
        values["owner_role"],
        "--completion-binding-json",
        values["completion_binding_json"],
        "--absorbed-terminal-event-id",
        values["absorbed_terminal_event_id"],
        "--timeout-ms",
        values["timeout_ms"],
        "--poll-ms",
        values["poll_ms"],
    ]


class ActivationCommitBarrierTest(unittest.TestCase):
    def test_missing_state_path_creates_no_lock_directory(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            state_path = Path(raw) / "absent" / "controller-state.json"
            result = subprocess.run(
                barrier_command(state_path), capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(state_path.parent.exists())

    def test_revision_654_pre_cas_snapshot_waits_without_state_or_terminal_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            state_path = Path(raw) / "controller-state.json"
            before = write_state_fixture(state_path, state_at_revision(654, activated=False))
            checksum_before = state_path.with_name(state_path.name + ".sha256").read_bytes()

            result = subprocess.run(
                barrier_command(state_path), capture_output=True, text=True, check=False
            )

            self.assertEqual(result.returncode, 75, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "WAIT_ACTIVATION_COMMIT")
            self.assertEqual(state_path.read_bytes(), before)
            self.assertEqual(
                state_path.with_name(state_path.name + ".sha256").read_bytes(),
                checksum_before,
            )
            self.assertFalse(Path(NEW_BINDING["terminal_path"]).exists())

    def test_revision_655_exact_successor_binding_passes(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            state_path = Path(raw) / "controller-state.json"
            write_state_fixture(state_path, state_at_revision(655, activated=True))

            result = subprocess.run(
                barrier_command(state_path), capture_output=True, text=True, check=False
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["revision"], 655)
            self.assertEqual(payload["objective_id"], "successor-objective")

    def test_committed_revision_with_binding_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            state_path = Path(raw) / "controller-state.json"
            write_state_fixture(state_path, state_at_revision(655, activated=True))
            wrong = dict(NEW_BINDING, dispatch_id="wrong-dispatch")

            result = subprocess.run(
                barrier_command(
                    state_path,
                    completion_binding_json=json.dumps(wrong, sort_keys=True),
                ),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("completion_binding mismatch", json.loads(result.stdout)["error"])

    def test_committed_revision_without_absorbed_predecessor_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            state_path = Path(raw) / "controller-state.json"
            state = state_at_revision(655, activated=True)
            state["absorbed_terminal_event_ids"] = []
            write_state_fixture(state_path, state)

            result = subprocess.run(
                barrier_command(state_path), capture_output=True, text=True, check=False
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("not absorbed", json.loads(result.stdout)["error"])


if __name__ == "__main__":
    unittest.main()
