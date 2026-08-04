from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "reconcile_research_lanes.py"
LANE_REFERENCE = SKILL_ROOT / "references" / "portfolio-lanes.md"
CONTROLLER = "controller"


def lease(task: str, owner: str, dispatch: str, epoch: int = 1) -> dict[str, object]:
    return {
        "task_id": task,
        "owner_thread_id": owner,
        "dispatch_id": dispatch,
        "lease_epoch": epoch,
    }


def registry_entry(
    task: str, owner: str, dispatch: str, epoch: int = 1
) -> dict[str, object]:
    return {
        "owner_thread_id": owner,
        "max_lease_epoch": epoch,
        "current_lease": lease(task, owner, dispatch, epoch),
    }


def delivered_callback() -> dict[str, object]:
    return {
        **lease("SOURCE-1", "source-owner", "DISPATCH-SOURCE-1"),
        "terminal_event_id": "TERM-SOURCE-1",
        "callback_receipt": "receipt-term-source-1",
    }


def base_record() -> dict[str, object]:
    return {
        "schema_version": 2,
        "controller_thread_id": CONTROLLER,
        "observed_at_utc": "2026-07-27T00:10:00Z",
        "worker_registry": [
            registry_entry("GPU-1", "gpu-owner", "DISPATCH-GPU-1"),
            {
                "owner_thread_id": "source-owner",
                "max_lease_epoch": 1,
                "current_lease": None,
            },
        ],
        "lease_transitions": [],
        "terminal_idempotency_history": [
            {
                **delivered_callback(),
                "callback_delivery_state": "delivered",
                "delivered_at_utc": "2026-07-27T00:02:00Z",
                "terminal_sha256": "a" * 64,
            }
        ],
        "gpu_running": {
            "task_id": "GPU-1",
            "owner_thread_id": "gpu-owner",
            "execution_id": "JOB-1",
            "observed_state": "running",
            "terminal_event_id": "TERM-GPU-1",
            "lease": lease("GPU-1", "gpu-owner", "DISPATCH-GPU-1"),
            "watchdog": {
                "automation_id": "gpu-1-watchdog",
                "state": "active",
                "next_check_due_at_utc": "2026-07-27T00:20:00Z",
                "task_id": "GPU-1",
                "execution_id": "JOB-1",
                "target_thread_id": "gpu-owner",
                "terminal_event_id": "TERM-GPU-1",
                "wake_owner_thread_id": "gpu-owner",
                "controller_thread_id": CONTROLLER,
            },
        },
        "gpu_queue": [
            {
                "task_id": "GPU-2",
                "owner_thread_id": "gpu-owner-2",
                "queue_state": "blocked",
                "blocking_fact": "GPU-1 terminal not yet adjudicated",
                "latest_authority": {
                    "checked_against_latest_terminal": True,
                    "source_kind": "frozen_prospective_contract",
                    "authority_id": "CONTRACT-GPU-2",
                    "evidence_path": "/evidence/contract-gpu-2.json",
                    "queue_disposition": "queue_gpu",
                },
            }
        ],
        "gpu_launch_in_progress": None,
        "result_analysis_queue": [],
        "terminal_transaction": {
            "callback_state": "delivered",
            "delivered_callback": delivered_callback(),
            "watchdog_state": "paused",
        },
    }


class ResearchSharedResourcesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "watermark.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_record(
        self,
        record: dict[str, object],
        *,
        check_only: bool = False,
        state: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        path = self.root / "snapshot.json"
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        command = [
            sys.executable,
            str(VALIDATOR),
            str(path),
            "--state",
            str(state or self.state),
        ]
        if check_only:
            command.append("--check-only")
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def assert_passes(self, record: dict[str, object], **kwargs: object) -> None:
        result = self.run_record(record, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS_RESEARCH_LANES", result.stdout)

    def test_minimal_managed_shared_resource_snapshot_passes(self) -> None:
        record = base_record()
        for removed in (
            "zero_gpu_running",
            "zero_gpu_backlog",
            "opportunity_search",
            "idle_proof",
            "pro_advisory_lane",
        ):
            self.assertNotIn(removed, record)
        self.assert_passes(record)

    def test_legacy_capacity_fields_are_inert_and_never_enter_watermark(self) -> None:
        record = base_record()
        record.update(
            {
                "zero_gpu_running": "explicit_idle",
                "zero_gpu_backlog": [{"task_id": "OLD", "status": "admitted"}],
                "opportunity_search": {"status": "blocked"},
                "idle_proof": {"reason": "obsolete"},
                "pro_advisory_lane": {
                    "live_jobs": [{"job_id": "PRO-PENDING", "status": "submitted"}]
                },
            }
        )
        result = self.run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("IGNORED_LEGACY_NONAUTHORITY=", result.stdout)
        watermark = json.loads(self.state.read_text(encoding="utf-8"))
        for removed in (
            "zero_gpu_running",
            "zero_gpu_backlog",
            "opportunity_search",
            "idle_proof",
            "pro_advisory_lane",
        ):
            self.assertNotIn(removed, watermark)

    def test_legacy_pro_pending_and_negative_labels_cannot_block_or_route(self) -> None:
        record = base_record()
        record["pro_advisory_lane"] = {
            "live_jobs": [{"job_id": "PRO-PENDING", "status": "generating"}]
        }
        record["zero_gpu_backlog"] = [
            {"task_id": "NEG", "status": "verified_negative"},
            {"task_id": "CARRIER", "status": "carrier_stop"},
        ]
        self.assert_passes(record, check_only=True)

    def test_gpu_queue_rejects_non_authoritative_operational_source(self) -> None:
        record = base_record()
        record["gpu_queue"][0]["latest_authority"]["source_kind"] = "wiki_summary"
        result = self.run_record(record, check_only=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("non-authoritative queue source", result.stdout)

    def test_live_gpu_requires_exact_registry_lease_and_watchdog_binding(self) -> None:
        record = base_record()
        record["gpu_running"]["lease"]["dispatch_id"] = "STALE-DISPATCH"
        record["gpu_running"]["watchdog"]["execution_id"] = "WRONG-JOB"
        result = self.run_record(record, check_only=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must exactly match worker_registry.current_lease", result.stdout)
        self.assertIn("watchdog.execution_id must match the live job", result.stdout)

    def test_overdue_gpu_watchdog_requires_exact_bounded_recovery(self) -> None:
        record = base_record()
        record["observed_at_utc"] = "2026-07-27T00:21:00Z"
        missing = self.run_record(record, check_only=True)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("overdue gpu watchdog requires task-bound due_handling", missing.stdout)

        record["gpu_running"]["watchdog"]["due_handling"] = {
            "state": "check_in_progress",
            "task_id": "GPU-1",
            "execution_id": "JOB-1",
            "terminal_event_id": "TERM-GPU-1",
            "recovery_receipt": "check-gpu-1",
        }
        self.assert_passes(record, check_only=True)

    def test_launch_ready_gpu_requires_one_activated_launch_owner(self) -> None:
        record = base_record()
        record["gpu_running"] = None
        item = record["gpu_queue"][0]
        item["queue_state"] = "launch_ready"
        item.pop("blocking_fact")
        missing = self.run_record(record, check_only=True)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("requires gpu_launch_in_progress", missing.stdout)

        record["worker_registry"].append(
            registry_entry("GPU-2", "gpu-owner-2", "DISPATCH-GPU-2")
        )
        record["gpu_launch_in_progress"] = {
            **lease("GPU-2", "gpu-owner-2", "DISPATCH-GPU-2"),
            "dispatch_receipt": "receipt-gpu-2",
        }
        self.assert_passes(record, check_only=True)

    def test_result_analysis_is_validated_without_global_preemption_lane(self) -> None:
        record = base_record()
        record["result_analysis_queue"] = [
            {
                "task_id": "ANALYZE-GPU-0",
                "status": "ready",
                "terminal_authority": {
                    "terminal_id": "TERM-GPU-0",
                    "evidence_path": "/evidence/term-gpu-0.json",
                },
            }
        ]
        self.assert_passes(record, check_only=True)

    def test_delivered_terminal_releases_worker_without_ack(self) -> None:
        record = base_record()
        self.assertEqual(record["terminal_transaction"]["callback_state"], "delivered")
        self.assertNotIn("controller_action", record["terminal_transaction"])
        self.assert_passes(record, check_only=True)

    def test_optional_acknowledged_shared_commit_requires_controller_action(self) -> None:
        record = base_record()
        record["terminal_transaction"]["callback_state"] = "acknowledged"
        missing = self.run_record(record, check_only=True)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("requires controller_action", missing.stdout)

        record["terminal_transaction"]["controller_action"] = {
            "transaction_id": "CTX-SOURCE-1",
            "disposition": "hold one unresolved source fact",
            "next_action": "explicit_hold",
            "decided_at": "2026-07-27T00:04:00Z",
            "blocking_fact": "primary source unavailable",
            "reopening_fact": "primary source becomes available",
            "observer_thread_id": CONTROLLER,
            "reopen_trigger_ref": "source-release-event",
            "next_evidence_action": "repeat bounded source audit",
        }
        self.assert_passes(record, check_only=True)

    def test_dispatch_next_must_match_registered_current_lease(self) -> None:
        record = base_record()
        record["terminal_transaction"].update(
            {
                "callback_state": "acknowledged",
                "controller_action": {
                    "transaction_id": "CTX-SOURCE-1",
                    "disposition": "dispatch exact successor",
                    "next_action": "dispatch_next",
                    "decided_at": "2026-07-27T00:04:00Z",
                    "next_lease": lease(
                        "GPU-1", "gpu-owner", "STALE-DISPATCH"
                    ),
                    "dispatch_receipt": "receipt-successor",
                },
            }
        )
        stale = self.run_record(record, check_only=True)
        self.assertEqual(stale.returncode, 1)
        self.assertIn("must exactly match worker_registry.current_lease", stale.stdout)
        record["terminal_transaction"]["controller_action"]["next_lease"] = lease(
            "GPU-1", "gpu-owner", "DISPATCH-GPU-1"
        )
        self.assert_passes(record, check_only=True)

    def test_conflicting_duplicate_terminal_event_fails(self) -> None:
        record = base_record()
        duplicate = copy.deepcopy(record["terminal_idempotency_history"][0])
        duplicate["callback_receipt"] = "different-receipt"
        record["terminal_idempotency_history"].append(duplicate)
        result = self.run_record(record, check_only=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("conflicting duplicate delivery", result.stdout)

    def test_durable_watermark_rejects_epoch_downgrade(self) -> None:
        record = base_record()
        self.assert_passes(record)
        stale = base_record()
        stale["worker_registry"][0]["max_lease_epoch"] = 0
        stale["worker_registry"][0]["current_lease"]["lease_epoch"] = 0
        result = self.run_record(stale)
        self.assertEqual(result.returncode, 1)
        self.assertIn("regresses durable max_lease_epoch", result.stdout)

    def test_epoch_advance_requires_durable_transition_receipt(self) -> None:
        self.assert_passes(base_record())
        advanced = base_record()
        advanced["worker_registry"][0] = registry_entry(
            "GPU-1", "gpu-owner", "DISPATCH-GPU-1-B", 2
        )
        advanced["gpu_running"]["lease"] = lease(
            "GPU-1", "gpu-owner", "DISPATCH-GPU-1-B", 2
        )
        advanced["terminal_idempotency_history"] = []
        advanced["terminal_transaction"] = {"callback_state": "none"}
        missing = self.run_record(advanced)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("advances epoch without a durable transition receipt", missing.stdout)

        advanced["lease_transitions"] = [
            {
                "transition_id": "LT-GPU-1-E2",
                "owner_thread_id": "gpu-owner",
                "kind": "transfer",
                "from_epoch": 1,
                "to_epoch": 2,
                "transition_receipt": "activation-gpu-1-e2",
                "transitioned_at_utc": "2026-07-27T00:11:00Z",
            }
        ]
        self.assert_passes(advanced)

    def test_durable_terminal_history_rejects_rebound_event(self) -> None:
        self.assert_passes(base_record())
        rebound = base_record()
        rebound["terminal_idempotency_history"][0]["callback_receipt"] = "rebound"
        rebound["terminal_transaction"]["delivered_callback"][
            "callback_receipt"
        ] = "rebound"
        result = self.run_record(rebound)
        self.assertEqual(result.returncode, 1)
        self.assertIn("conflicts with durable history", result.stdout)

    def test_exact_replay_has_no_second_durable_effect(self) -> None:
        record = base_record()
        self.assert_passes(record)
        before = self.state.read_bytes()
        generation = json.loads(before)["generation"]
        self.assert_passes(record)
        after = self.state.read_bytes()
        self.assertEqual(before, after)
        self.assertEqual(json.loads(after)["generation"], generation)

    def test_check_only_does_not_create_watermark(self) -> None:
        self.assert_passes(base_record(), check_only=True)
        self.assertFalse(self.state.exists())

    def test_removed_global_scheduler_symbols_do_not_return(self) -> None:
        source = VALIDATOR.read_text(encoding="utf-8")
        for symbol in (
            "IDLE_PROOF_CATEGORIES",
            "PRO_LIVE_STATES",
            "PRO_CALLBACK_EVENT_STATES",
            "validate_final_ack_terminal_artifact",
            "pro_generation_maps",
        ):
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        reference = LANE_REFERENCE.read_text(encoding="utf-8")
        for obsolete in (
            "Maintain these portfolio fields independently",
            "GPU result analysis preempts ordinary Opportunity Search",
            "True saturation and continuous search",
            "Pro lifecycle and completion delivery",
            "ACK the idempotent terminal event",
        ):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(obsolete, reference)
        self.assertIn("This is not a global portfolio scheduler", reference)
        self.assertIn("Delivery needs no `RECEIPT_ONLY`, `FINAL_ACK`", reference)


if __name__ == "__main__":
    unittest.main()
