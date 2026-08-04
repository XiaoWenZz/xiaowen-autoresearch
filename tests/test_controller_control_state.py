import json
import tempfile
import unittest
from pathlib import Path

from scripts.controller_control_state import StateError, read_state, validate_state, write_state


def base_state() -> dict:
    return {
        "schema_version": 1,
        "revision": 0,
        "updated_at": "2026-08-05T00:00:00Z",
        "controller": {
            "thread_id": "controller-1",
            "project_id": "project-1",
            "cwd": "/workspace",
            "title": "Controller · FedFT ICLR 2027 Research · ACTIVE",
            "pin_required": True,
        },
        "objectives": [
            {
                "objective_id": "objective-1",
                "candidate_id": "candidate-1",
                "stage": "R2_SCOUT",
                "scientific_outcome": "UNOBSERVED",
                "lifecycle": "DELEGATED",
                "next_action": "WAIT_TERMINAL",
                "owner_thread_id": "worker-1",
                "owner_role": "Executor",
                "owner_state": "WAITING_EXTERNAL",
            }
        ],
        "managed_roles": [
            {
                "thread_id": "worker-1",
                "role": "Executor",
                "title": "Executor · Candidate One · WAITING_EXTERNAL",
                "state": "WAITING_EXTERNAL",
                "pin_required": True,
                "cursor": None,
            }
        ],
        "remote_jobs": [
            {
                "job_id": "job-1",
                "objective_id": "objective-1",
                "owner_thread_id": "worker-1",
                "host": "dual5090",
                "unit": "job-1.service",
                "output_path": "/home/xiaowen/runs/job-1",
                "expected_files": ["terminal.json"],
                "eta": "2026-08-05T01:00:00Z",
                "late_threshold": "2026-08-05T02:00:00Z",
                "monitor_state": "ACTIVE",
                "wake_delivery": {"state": "NONE", "claim_token": None, "observation_id": None},
            }
        ],
        "absorbed_terminal_event_ids": [],
    }


class ControllerControlStateTest(unittest.TestCase):
    def test_valid_state_round_trips_with_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "controller-state.json"
            written = write_state(path, base_state(), -1)
            self.assertEqual(written["revision"], 0)
            self.assertEqual(read_state(path), written)
            self.assertTrue(path.with_name(path.name + ".sha256").is_file())

    def test_compare_and_swap_rejects_stale_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            with self.assertRaisesRegex(StateError, "revision conflict"):
                write_state(path, base_state(), -1)

    def test_delegated_objective_requires_owner(self) -> None:
        state = base_state()
        del state["objectives"][0]["owner_thread_id"]
        with self.assertRaisesRegex(StateError, "missing keys"):
            validate_state(state)

    def test_delegated_owner_must_match_active_role(self) -> None:
        state = base_state()
        state["objectives"][0]["owner_state"] = "ACTIVE"
        with self.assertRaisesRegex(StateError, "does not match managed role"):
            validate_state(state)

    def test_blocked_objective_requires_reopening_observer_trigger(self) -> None:
        state = base_state()
        objective = state["objectives"][0]
        objective["lifecycle"] = "BLOCKED"
        for key in ("owner_thread_id", "owner_role", "owner_state"):
            objective.pop(key)
        objective["blocker"] = {"reopening_fact": "FACT", "observer": "OWNER"}
        with self.assertRaisesRegex(StateError, "missing keys"):
            validate_state(state)

    def test_checksum_tampering_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            state = json.loads(path.read_text(encoding="utf-8"))
            state["controller"]["title"] = "Controller · Changed · ACTIVE"
            path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "checksum mismatch"):
                read_state(path)

    def test_job_wake_state_is_fail_closed(self) -> None:
        state = base_state()
        state["remote_jobs"][0]["wake_delivery"] = {
            "state": "CLAIMED",
            "claim_token": None,
            "observation_id": "obs-1",
        }
        with self.assertRaisesRegex(StateError, "claimed identifiers"):
            validate_state(state)

    def test_remote_monitor_fields_are_allowlisted(self) -> None:
        state = base_state()
        state["remote_jobs"][0]["host"] = "unknown-host"
        with self.assertRaisesRegex(StateError, "host is not allowlisted"):
            validate_state(state)

        state = base_state()
        state["remote_jobs"][0]["output_path"] = "/tmp/untrusted"
        with self.assertRaisesRegex(StateError, "outside allowlisted roots"):
            validate_state(state)

        state = base_state()
        state["remote_jobs"][0]["expected_files"] = ["../terminal.json"]
        with self.assertRaisesRegex(StateError, "must be basenames"):
            validate_state(state)


if __name__ == "__main__":
    unittest.main()
