from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
INIT = SKILL_ROOT / "scripts" / "init_task.py"
VALIDATE = SKILL_ROOT / "scripts" / "validate_task.py"
UPDATE = SKILL_ROOT / "scripts" / "update_state.py"


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
    )


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class StateHelpersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "task"
        result = run(
            INIT,
            self.root,
            "--title",
            "Callback test",
            "--objective",
            "Retire one uncertainty",
            "--task-type",
            "mixed",
            "--program-id",
            "P1",
            "--epoch-id",
            "P1-E1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_ready(self) -> None:
        charter_path = self.root / "state" / "charter.json"
        charter = json.loads(charter_path.read_text(encoding="utf-8"))
        charter.update(
            {
                "governance_admission_proof": "persistent worker callback and recovery",
                "research_question": "Does the frozen witness change the decision?",
                "hypotheses": ["H1"],
                "success_criteria": ["primary gate passes"],
                "failure_criteria": ["primary gate fails"],
                "primary_metrics": ["utility"],
                "strongest_baseline": "matched static baseline",
                "claim_boundary": "Scout signal only",
            }
        )
        charter["governance"]["promotion_trigger"] = "material attributed signal"
        charter["protocol"].update(
            {
                "frozen": True,
                "frozen_at": "2026-07-22T00:00:00Z",
                "code_version": "abc123",
                "data_version": "data-v1",
                "data_split": "frozen-split",
                "data_boundary": "no public test",
                "seed_policy": "fixed seeds",
                "analysis_plan": "predeclared gate",
            }
        )
        write_json(charter_path, charter)
        progress_path = self.root / "state" / "progress.json"
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        progress["status"] = "ready"
        write_json(progress_path, progress)

    def append(self, stream: str, record: dict[str, object]) -> subprocess.CompletedProcess[str]:
        return run(UPDATE, "append", self.root, stream, "--record-json", json.dumps(record))

    def write_completed_run(
        self,
        *,
        config: dict[str, object],
        artifacts: object,
    ) -> Path:
        task_id = json.loads(
            (self.root / "state" / "charter.json").read_text(encoding="utf-8")
        )["task_id"]
        run_path = self.root / "runs" / "RUN-D05.json"
        write_json(
            run_path,
            {
                "schema_version": "1.0",
                "run_id": "RUN-D05",
                "task_id": task_id,
                "status": "completed",
                "question": "Does local integrity remain bound?",
                "started_at": "2026-07-22T00:00:00Z",
                "ended_at": "2026-07-22T00:01:00Z",
                "code_version": {"git_commit": "abc123"},
                "config": config,
                "dataset": {"name": "synthetic", "version": "v1", "split": "test"},
                "environment": {"host": "local"},
                "seeds": [1],
                "primary_metrics": ["integrity"],
                "artifacts": artifacts,
                "validation": [{"command": "local-check", "status": "pass"}],
                "result_summary": "outcome unobserved",
                "anomalies": [],
                "protocol_deviations": [],
            },
        )
        return run_path

    def test_init_uses_explicit_track_and_weight(self) -> None:
        charter = json.loads((self.root / "state" / "charter.json").read_text(encoding="utf-8"))
        self.assertEqual(charter["schema_version"], "1.2")
        self.assertEqual(charter["governance_track"], "scout")
        self.assertEqual(charter["operating_weight"], "managed")
        self.assertEqual(charter["program_id"], "P1")
        self.assertEqual(charter["epoch_id"], "P1-E1")
        self.assertTrue((self.root / "state" / "workers.jsonl").is_file())

    def test_confirmatory_init_uses_full_weight(self) -> None:
        confirmatory_root = Path(self.temp.name) / "confirmatory"
        result = run(
            INIT,
            confirmatory_root,
            "--title",
            "Confirmatory test",
            "--objective",
            "Confirm one claim",
            "--governance-track",
            "confirmatory",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        charter = json.loads(
            (confirmatory_root / "state" / "charter.json").read_text(encoding="utf-8")
        )
        self.assertEqual(charter["governance_track"], "confirmatory")
        self.assertEqual(charter["operating_weight"], "full")

    def test_ready_managed_scout_passes(self) -> None:
        self.make_ready()
        result = run(VALIDATE, self.root, "--ready")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("operating_weight=managed", result.stdout)

    def test_d05_declared_config_digest_is_recomputed(self) -> None:
        config_path = self.root / "configs" / "frozen.json"
        config_path.parent.mkdir()
        config_path.write_bytes(b'{"frozen":true}\n')
        artifact_path = self.root / "artifacts" / "legacy.txt"
        artifact_path.write_text("legacy\n", encoding="utf-8")
        digest = hashlib.sha256(config_path.read_bytes()).hexdigest()
        run_path = self.write_completed_run(
            config={"path": "configs/frozen.json", "sha256": digest},
            artifacts=["artifacts/legacy.txt"],
        )
        healthy = run(VALIDATE, self.root)
        self.assertEqual(healthy.returncode, 0, healthy.stdout + healthy.stderr)

        config_path.write_bytes(b'{"frozen":false}\n')
        mismatch = run(VALIDATE, self.root)
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("config sha256 mismatch", mismatch.stdout)

        config_path.write_bytes(b'{"frozen":true}\n')
        manifest = json.loads(run_path.read_text(encoding="utf-8"))
        manifest["config"]["sha256"] = "malformed"
        write_json(run_path, manifest)
        malformed = run(VALIDATE, self.root)
        self.assertNotEqual(malformed.returncode, 0)
        self.assertIn("canonical 64-hex sha256", malformed.stdout)

        manifest["config"] = {
            "path": config_path.as_uri(),
            "sha256": digest,
        }
        write_json(run_path, manifest)
        file_uri_healthy = run(VALIDATE, self.root)
        self.assertEqual(
            file_uri_healthy.returncode,
            0,
            file_uri_healthy.stdout + file_uri_healthy.stderr,
        )
        manifest["config"]["sha256"] = "0" * 64
        write_json(run_path, manifest)
        file_uri_mismatch = run(VALIDATE, self.root)
        self.assertNotEqual(file_uri_mismatch.returncode, 0)
        self.assertIn("config sha256 mismatch", file_uri_mismatch.stdout)

        manifest["status"] = "running"
        manifest["config"] = {
            "path": "configs/frozen.json",
            "sha256": "0" * 64,
        }
        manifest["artifacts"] = [
            {"path": "configs/frozen.json", "sha256": "0" * 64}
        ]
        write_json(run_path, manifest)
        running_mismatch = run(VALIDATE, self.root)
        self.assertNotEqual(running_mismatch.returncode, 0)
        self.assertIn("config sha256 mismatch", running_mismatch.stdout)
        self.assertIn("artifact sha256 mismatch", running_mismatch.stdout)

    def test_d05_declared_local_artifact_digest_is_recomputed(self) -> None:
        config_path = self.root / "configs" / "frozen.json"
        config_path.parent.mkdir()
        config_path.write_bytes(b'{"frozen":true}\n')
        artifact_path = self.root / "artifacts" / "bound.bin"
        artifact_path.write_bytes(b"frozen-artifact")
        run_path = self.write_completed_run(
            config={
                "path": "configs/frozen.json",
                "sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            },
            artifacts=[
                {
                    "path": "artifacts/bound.bin",
                    "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                },
                "https://example.invalid/remote-artifact",
            ],
        )
        healthy = run(VALIDATE, self.root)
        self.assertEqual(healthy.returncode, 0, healthy.stdout + healthy.stderr)

        artifact_path.write_bytes(b"mutated-artifact")
        mismatch = run(VALIDATE, self.root)
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("artifact sha256 mismatch", mismatch.stdout)

        artifact_path.write_bytes(b"frozen-artifact")
        manifest = json.loads(run_path.read_text(encoding="utf-8"))
        manifest["artifacts"] = [
            {
                "path": artifact_path.as_uri(),
                "sha256": "0" * 64,
            }
        ]
        write_json(run_path, manifest)
        file_uri_mismatch = run(VALIDATE, self.root)
        self.assertNotEqual(file_uri_mismatch.returncode, 0)
        self.assertIn("artifact sha256 mismatch", file_uri_mismatch.stdout)

        (self.root / "path").write_text("decoy\n", encoding="utf-8")
        (self.root / "sha256").write_text("decoy\n", encoding="utf-8")
        manifest["artifacts"] = {
            "path": "artifacts/missing.bin",
            "sha256": "0" * 64,
        }
        write_json(run_path, manifest)
        malformed_container = run(VALIDATE, self.root)
        self.assertNotEqual(malformed_container.returncode, 0)
        self.assertIn("artifacts must be a non-empty list", malformed_container.stdout)

    def test_invalid_track_weight_pair_fails(self) -> None:
        charter_path = self.root / "state" / "charter.json"
        charter = json.loads(charter_path.read_text(encoding="utf-8"))
        charter["operating_weight"] = "full"
        write_json(charter_path, charter)
        progress_path = self.root / "state" / "progress.json"
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        progress["operating_weight"] = "full"
        write_json(progress_path, progress)
        result = run(VALIDATE, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid durable governance_track/operating_weight pair", result.stdout)

    def test_duplicate_direction_fingerprint_fails(self) -> None:
        base = {
            "iteration": 1,
            "hypothesis": "H",
            "mechanism": "M",
            "changed_variables": ["x"],
            "expected_observation": "O",
            "structural_delta": "D",
            "fingerprint": "same-fingerprint",
            "is_replication": False,
            "status": "planned",
        }
        self.assertEqual(self.append("directions", {"direction_id": "D1", **base}).returncode, 0)
        self.assertEqual(self.append("directions", {"direction_id": "D2", **base}).returncode, 0)
        result = run(VALIDATE, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicates fingerprint", result.stdout)

    def test_scout_cannot_accept_claim(self) -> None:
        evidence = {
            "evidence_id": "E1",
            "kind": "source",
            "summary": "checked",
            "provenance": {"source": "paper", "captured_at": "2026-07-22T00:00:00Z"},
            "verification": {"status": "verified"},
            "supports_claims": ["C1"],
            "limitations": [],
        }
        claim = {
            "claim_id": "C1",
            "claim_type": "fact",
            "text": "accepted too early",
            "status": "accepted",
            "evidence_ids": ["E1"],
            "scope": "test",
            "limitations": [],
            "adjudication": {
                "decision": "accepted",
                "reviewer_role": "adjudicator",
                "independent": True,
                "rationale": "test",
                "decided_at": "2026-07-22T00:10:00Z",
            },
        }
        self.assertEqual(self.append("evidence", evidence).returncode, 0)
        self.assertEqual(self.append("claims", claim).returncode, 0)
        result = run(VALIDATE, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot be accepted", result.stdout)

    def test_callback_delivery_and_acknowledgement_are_idempotent(self) -> None:
        delivered = {
            "worker_record_id": "WR1",
            "worker_id": "B1",
            "thread_id": "T1",
            "program_id": "P1",
            "epoch_id": "P1-E1",
            "contract_revision": "v0",
            "role": "evidence-worker",
            "status": "completed",
            "callback_state": "delivered",
            "terminal_event_id": "TERM1",
            "reclaim_deadline": None,
            "watchdog_id": "WD1",
            "watchdog_state": "active",
            "artifact_paths": ["artifacts/result.json"],
            "recorded_at": "2026-07-22T00:00:00Z",
        }
        acknowledged = {
            **delivered,
            "worker_record_id": "WR2",
            "callback_state": "acknowledged",
            "watchdog_state": "paused",
            "controller_action": {
                "transaction_id": "CTX1",
                "disposition": "hold after bounded result",
                "next_action": "explicit_hold",
                "worker_notified": True,
                "decided_at": "2026-07-22T00:01:00Z",
            },
            "recorded_at": "2026-07-22T00:01:00Z",
            "supersedes_id": "WR1",
        }
        self.assertEqual(self.append("workers", delivered).returncode, 0)
        self.assertEqual(self.append("workers", acknowledged).returncode, 0)
        result = run(VALIDATE, self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        collision = {
            **acknowledged,
            "worker_record_id": "WR3",
            "worker_id": "B2",
            "thread_id": "T2",
            "supersedes_id": None,
        }
        self.assertEqual(self.append("workers", collision).returncode, 0)
        result = run(VALIDATE, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("shared by multiple workers", result.stdout)

    def test_atomic_terminal_acknowledgement_passes(self) -> None:
        acknowledgement = {
            "worker_record_id": "WR-ATOMIC",
            "worker_id": "B1",
            "thread_id": "T1",
            "program_id": "P1",
            "epoch_id": "P1-E1",
            "contract_revision": "v0",
            "role": "evidence-worker",
            "status": "completed",
            "callback_state": "acknowledged",
            "terminal_event_id": "TERM-ATOMIC",
            "reclaim_deadline": None,
            "watchdog_id": None,
            "watchdog_state": "not_required",
            "controller_action": {
                "transaction_id": "CTX-ATOMIC",
                "disposition": "scoped close",
                "next_action": "scoped_close",
                "worker_notified": True,
                "decided_at": "2026-07-22T00:00:00Z",
            },
            "artifact_paths": ["artifacts/result.json"],
            "recorded_at": "2026-07-22T00:00:00Z",
        }
        self.assertEqual(self.append("workers", acknowledgement).returncode, 0)
        result = run(VALIDATE, self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_latest_delivered_terminal_requires_acknowledgement(self) -> None:
        delivered = {
            "worker_record_id": "WR-DELIVERED",
            "worker_id": "B1",
            "thread_id": "T1",
            "program_id": "P1",
            "epoch_id": "P1-E1",
            "contract_revision": "v0",
            "role": "evidence-worker",
            "status": "completed",
            "callback_state": "delivered",
            "terminal_event_id": "TERM-DELIVERED",
            "reclaim_deadline": None,
            "watchdog_id": "WD1",
            "watchdog_state": "active",
            "artifact_paths": ["artifacts/result.json"],
            "recorded_at": "2026-07-22T00:00:00Z",
        }
        self.assertEqual(self.append("workers", delivered).returncode, 0)
        result = run(VALIDATE, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unacknowledged terminal callback", result.stdout)

    def test_dispatch_next_requires_registered_active_transition(self) -> None:
        acknowledgement = {
            "worker_record_id": "WR-ACK",
            "worker_id": "B1",
            "thread_id": "T1",
            "program_id": "P1",
            "epoch_id": "P1-E1",
            "contract_revision": "v0",
            "role": "evidence-worker",
            "status": "completed",
            "callback_state": "acknowledged",
            "terminal_event_id": "TERM-NEXT",
            "reclaim_deadline": None,
            "watchdog_id": "WD1",
            "watchdog_state": "paused",
            "artifact_paths": ["artifacts/result.json"],
            "recorded_at": "2026-07-22T00:00:00Z",
            "controller_action": {
                "transaction_id": "CTX-NEXT",
                "disposition": "continue bounded preflight",
                "next_action": "dispatch_next",
                "worker_notified": True,
                "decided_at": "2026-07-22T00:00:00Z",
                "next_worker_record_id": "WR-NEXT",
                "next_contract_revision": "cycle0b-v0",
            },
        }
        self.assertEqual(self.append("workers", acknowledgement).returncode, 0)
        result = run(VALIDATE, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dispatch_next target does not exist", result.stdout)

        next_record = {
            **acknowledgement,
            "worker_record_id": "WR-NEXT",
            "contract_revision": "cycle0b-v0",
            "status": "running",
            "callback_state": "pending",
            "terminal_event_id": None,
            "watchdog_state": "active",
            "recorded_at": "2026-07-22T00:01:00Z",
            "controller_action": None,
            "supersedes_id": "WR-ACK",
        }
        self.assertEqual(self.append("workers", next_record).returncode, 0)
        result = run(VALIDATE, self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_adopt_existing_preserves_rules_and_artifacts(self) -> None:
        adopted = Path(self.temp.name) / "adopted"
        adopted.mkdir()
        (adopted / "AGENTS.md").write_text("# Existing rules\n", encoding="utf-8")
        (adopted / "artifacts").mkdir()
        (adopted / "artifacts" / "existing.txt").write_text("keep\n", encoding="utf-8")
        result = run(
            INIT,
            adopted,
            "--title",
            "Adopted Scout",
            "--objective",
            "Add durable callback recovery",
            "--program-id",
            "P2",
            "--epoch-id",
            "P2-E1",
            "--adopt-existing",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((adopted / "AGENTS.md").read_text(encoding="utf-8"), "# Existing rules\n")
        self.assertEqual(
            (adopted / "artifacts" / "existing.txt").read_text(encoding="utf-8"), "keep\n"
        )
        self.assertTrue((adopted / "state" / "workers.jsonl").is_file())

    def test_stale_heartbeat_fails(self) -> None:
        progress_path = self.root / "state" / "progress.json"
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        progress["status"] = "running"
        write_json(progress_path, progress)
        heartbeat_path = self.root / "state" / "heartbeat.json"
        heartbeat = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        heartbeat.update(
            {
                "runner_id": "worker",
                "status": "alive",
                "last_seen_at": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
                "lease_expires_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
            }
        )
        write_json(heartbeat_path, heartbeat)
        result = run(VALIDATE, self.root, "--max-heartbeat-age-minutes", "60")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("heartbeat is stale", result.stdout)


if __name__ == "__main__":
    unittest.main()
