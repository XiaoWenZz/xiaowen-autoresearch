from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "reconcile_research_lanes.py"
CONTROLLER = "controller"


def task_lease_fields(
    task: str,
    owner: str,
    dispatch: str,
    epoch: int,
    terminal: str,
    *,
    activated_at: str = "2026-07-27T00:05:00Z",
) -> dict[str, object]:
    return {
        "task_id": task,
        "owner_thread_id": owner,
        "dispatch_id": dispatch,
        "lease_epoch": epoch,
        "terminal_event_id": terminal,
        "activation_evidence": {
            "task_id": task,
            "owner_thread_id": owner,
            "dispatch_id": dispatch,
            "lease_epoch": epoch,
            "observed_thread_status": "active",
            "activation_receipt": f"activation-{dispatch}",
            "observed_at_utc": activated_at,
        },
        "callback_binding": {
            "task_id": task,
            "owner_thread_id": owner,
            "dispatch_id": dispatch,
            "lease_epoch": epoch,
            "terminal_event_id": terminal,
            "controller_thread_id": CONTROLLER,
        },
    }


def delivered_callback_fields(
    task: str = "SOURCE-1",
    owner: str = "source-owner",
    dispatch: str = "DISPATCH-SOURCE-1",
    epoch: int = 1,
    terminal: str = "TERM-SOURCE-1",
) -> dict[str, object]:
    return {
        "task_id": task,
        "owner_thread_id": owner,
        "dispatch_id": dispatch,
        "lease_epoch": epoch,
        "terminal_event_id": terminal,
        "callback_receipt": f"callback-{terminal}",
    }


def run_record(
    record: dict[str, object], state_path: Path | None = None
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "lanes.json"
        effective_state = state_path or Path(temp) / "watermark.json"
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                str(path),
                "--state",
                str(effective_state),
            ],
            text=True,
            capture_output=True,
            check=False,
        )


def base_record() -> dict[str, object]:
    return {
        "controller_thread_id": CONTROLLER,
        "observed_at_utc": "2026-07-27T00:10:00Z",
        "worker_registry": [
            {
                "owner_thread_id": "zero-owner",
                "max_lease_epoch": 1,
                "current_lease": {
                    "task_id": "ZERO-1",
                    "owner_thread_id": "zero-owner",
                    "dispatch_id": "DISPATCH-ZERO-1",
                    "lease_epoch": 1,
                },
            },
            {
                "owner_thread_id": "source-owner",
                "max_lease_epoch": 1,
                "current_lease": None,
            },
        ],
        "terminal_idempotency_history": [
            {
                **delivered_callback_fields(),
                "callback_delivery_state": "delivered",
                "delivered_at_utc": "2026-07-27T00:02:00Z",
            }
        ],
        "lease_transitions": [],
        "gpu_running": {
            "task_id": "GPU-1",
            "owner_thread_id": "gpu-owner",
            "execution_id": "JOB-1",
            "observed_state": "running",
            "terminal_event_id": "TERM-GPU-1",
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
                "launch_prerequisite": "GPU-1 terminal",
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
        "zero_gpu_running": {
            **task_lease_fields(
                "ZERO-1",
                "zero-owner",
                "DISPATCH-ZERO-1",
                1,
                "TERM-ZERO-1",
            ),
            "owner_thread_status": "active",
            "kind": "opportunity_search",
            "expected_reasoning_effort": "max",
            "callback_registered": True,
            "dispatch_receipt": "receipt-zero-1",
            "progress_due_at_utc": "2026-07-27T00:20:00Z",
        },
        "zero_gpu_backlog": [],
        "result_analysis_queue": [],
        "opportunity_search": {"status": "active", "task_id": "ZERO-1"},
        "idle_proof": None,
        "terminal_transaction": {
            "callback_state": "none",
            "portfolio_reconciled": False,
            "watchdog_state": "active",
            "next_action": {"kind": "queued"},
        },
        "pro_advisory_lane": {
            "live_jobs": [
                {
                    "job_id": "PRO-1",
                    "decision": "independent idea-stage neighbor map",
                    "polling_owner": "controller",
                    "completion_callback_thread_id": "controller",
                    "completion_callback_configured": True,
                    "submitted_at_utc": "2026-07-27T00:00:00Z",
                    "next_check_due_at_utc": "2026-07-27T00:15:00Z",
                    "status": "submitted",
                }
            ],
            "queue": [],
            "response_ready": [],
            "explicit_idle_reason": None,
        },
    }


class ResearchLanesTest(unittest.TestCase):
    def test_gpu_queue_with_active_opportunity_search_passes(self) -> None:
        result = run_record(base_record())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS_RESEARCH_LANES", result.stdout)

    def test_gpu_queue_cannot_justify_unproved_zero_gpu_idle(self) -> None:
        record = base_record()
        record["zero_gpu_running"] = "explicit_idle"
        record["opportunity_search"] = {
            "status": "admitted",
            "task_id": "ZERO-NEXT",
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit_idle", result.stdout)

    def test_wiki_only_or_stale_hold_cannot_enter_gpu_queue(self) -> None:
        record = base_record()
        authority = record["gpu_queue"][0]["latest_authority"]
        authority["source_kind"] = "llm_wiki"
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_kind", result.stdout)

        authority["source_kind"] = "durable_terminal_packet"
        authority["queue_disposition"] = "hold_qualification_carrier"
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("queue_disposition must be queue_gpu", result.stdout)

    def test_gpu_queue_requires_latest_terminal_reconciliation(self) -> None:
        record = base_record()
        record["gpu_queue"][0]["latest_authority"][
            "checked_against_latest_terminal"
        ] = False
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checked against the latest terminal", result.stdout)

    def test_validated_global_idle_requires_complete_proof(self) -> None:
        record = base_record()
        record["gpu_running"] = None
        record["gpu_queue"] = []
        record["zero_gpu_running"] = "explicit_idle"
        record["opportunity_search"] = {"status": "budget_exhausted"}
        record["idle_proof"] = {
            "evaluated_categories": [
                "current_route",
                "gpu_queue_prerequisites",
                "partial_audits",
                "new_problem_opportunity_search",
            ],
            "reason": "bounded global search budget is exhausted",
            "reopening_fact": "new owner budget or a terminal result",
        }
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_admitted_backlog_rejects_idle(self) -> None:
        record = base_record()
        record["zero_gpu_running"] = "explicit_idle"
        record["opportunity_search"] = {
            "status": "blocked",
            "reopening_fact": "source release",
        }
        record["idle_proof"] = {
            "evaluated_categories": [
                "current_route",
                "gpu_queue_prerequisites",
                "partial_audits",
                "new_problem_opportunity_search",
            ],
            "reason": "claimed idle",
            "reopening_fact": "source release",
        }
        record["zero_gpu_backlog"] = [
            {
                "task_id": "ZERO-READY",
                "status": "admitted",
                "useful_under_all_pending_gpu_outcomes": True,
            }
        ]
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("admitted zero-GPU work exists", result.stdout)

    def test_ready_result_analysis_preempts_opportunity_search(self) -> None:
        record = base_record()
        record["result_analysis_queue"] = [
            {
                "task_id": "ANALYZE-GPU-1",
                "status": "ready",
                "terminal_authority": {
                    "terminal_id": "TERM-GPU-1",
                    "evidence_path": "/evidence/term-gpu-1.json",
                },
            }
        ]
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must preempt", result.stdout)

        record["zero_gpu_running"] = {
            **task_lease_fields(
                "ANALYZE-GPU-1",
                "analysis-owner",
                "DISPATCH-ANALYZE-GPU-1",
                1,
                "TERM-ANALYZE-GPU-1",
            ),
            "owner_thread_status": "active",
            "kind": "result_analysis",
            "expected_reasoning_effort": "max",
            "callback_registered": True,
            "dispatch_receipt": "receipt-analysis-1",
            "progress_due_at_utc": "2026-07-27T00:20:00Z",
        }
        record["worker_registry"][0] = {
            "owner_thread_id": "analysis-owner",
            "max_lease_epoch": 1,
            "current_lease": {
                "task_id": "ANALYZE-GPU-1",
                "owner_thread_id": "analysis-owner",
                "dispatch_id": "DISPATCH-ANALYZE-GPU-1",
                "lease_epoch": 1,
            },
        }
        record["opportunity_search"] = {
            "status": "admitted",
            "task_id": "ZERO-1",
        }
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_acknowledgement_requires_atomic_portfolio_reconciliation(self) -> None:
        record = base_record()
        record["terminal_transaction"] = {
            "callback_state": "acknowledged",
            "delivered_callback": delivered_callback_fields(),
            "portfolio_reconciled": False,
            "portfolio_reconciled_at_utc": "2026-07-27T00:01:00Z",
            "acknowledged_at_utc": "2026-07-27T00:02:00Z",
            "delivery_intent_durable": True,
            "watchdog_state": "paused",
            "next_action": {
                **task_lease_fields(
                    "ZERO-1",
                    "zero-owner",
                    "DISPATCH-ZERO-1",
                    1,
                    "TERM-ZERO-1",
                ),
                "kind": "dispatch_next",
                "owner_thread_status": "active",
                "dispatch_receipt": "receipt-zero-1",
            },
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("portfolio_reconciled=true", result.stdout)

        record["terminal_transaction"]["portfolio_reconciled"] = True
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_decision_ready_pro_review_cannot_sit_unsent(self) -> None:
        record = base_record()
        record["pro_advisory_lane"] = {
            "live_jobs": [],
            "queue": [{"task_id": "PRO-READY", "status": "decision_ready"}],
            "response_ready": [],
            "explicit_idle_reason": None,
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be submitted", result.stdout)

        record["pro_advisory_lane"]["cooldown_held"] = True
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_live_pro_job_requires_explicit_callback_owner(self) -> None:
        record = base_record()
        job = record["pro_advisory_lane"]["live_jobs"][0]
        job["completion_callback_configured"] = False
        job["completion_callback_thread_id"] = ""
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("completion_callback_configured=true", result.stdout)
        self.assertIn("completion_callback_thread_id", result.stdout)

    def test_due_pro_check_cannot_be_postponed_by_retargeting(self) -> None:
        record = base_record()
        record["observed_at_utc"] = "2026-07-27T00:16:00Z"
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is due", result.stdout)

        job = record["pro_advisory_lane"]["live_jobs"][0]
        job["due_handling"] = "in_progress"
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_completed_pro_response_must_enter_adjudication(self) -> None:
        record = base_record()
        record["pro_advisory_lane"] = {
            "live_jobs": [],
            "queue": [],
            "response_ready": [
                {
                    "job_id": "PRO-DONE",
                    "decision": "theory bottleneck",
                    "owner_thread_id": "controller",
                    "response_artifact": "/evidence/pro-done.json",
                    "completed_at_utc": "2026-07-27T00:05:00Z",
                }
            ],
            "explicit_idle_reason": None,
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be claimed for adjudication", result.stdout)

        record["pro_advisory_lane"]["adjudicating_job_id"] = "PRO-DONE"
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_final_ack_must_follow_reconciliation(self) -> None:
        record = base_record()
        record["terminal_transaction"] = {
            "callback_state": "acknowledged",
            "delivered_callback": delivered_callback_fields(),
            "portfolio_reconciled": True,
            "portfolio_reconciled_at_utc": "2026-07-27T00:03:00Z",
            "acknowledged_at_utc": "2026-07-27T00:02:00Z",
            "delivery_intent_durable": True,
            "watchdog_state": "paused",
            "next_action": {
                **task_lease_fields(
                    "ZERO-1",
                    "zero-owner",
                    "DISPATCH-ZERO-1",
                    1,
                    "TERM-ZERO-1",
                ),
                "kind": "dispatch_next",
                "owner_thread_status": "active",
                "dispatch_receipt": "receipt-zero-1",
            },
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("final terminal ACK must follow", result.stdout)

        record["terminal_transaction"]["acknowledged_at_utc"] = (
            "2026-07-27T00:04:00Z"
        )
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_claimed_running_zero_gpu_worker_must_be_actually_active(self) -> None:
        record = base_record()
        record["zero_gpu_running"]["owner_thread_status"] = "idle"
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owner_thread_status=active", result.stdout)

    def test_zero_gpu_worker_requires_reasoning_route_and_progress_deadline(self) -> None:
        record = base_record()
        record["zero_gpu_running"]["expected_reasoning_effort"] = "high"
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires max reasoning", result.stdout)

        record["zero_gpu_running"]["expected_reasoning_effort"] = "max"
        record["observed_at_utc"] = "2026-07-27T00:21:00Z"
        record["pro_advisory_lane"]["live_jobs"][0][
            "next_check_due_at_utc"
        ] = "2026-07-27T01:00:00Z"
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires task-bound recovery evidence", result.stdout)

        record["zero_gpu_running"]["progress_due_handling"] = {
            "state": "continuity_check_in_progress",
            "task_id": "ZERO-1",
            "owner_thread_id": "zero-owner",
            "dispatch_id": "DISPATCH-ZERO-1",
            "lease_epoch": 1,
            "recovery_receipt": "recover-zero-1",
        }
        record["gpu_running"]["watchdog"]["due_handling"] = {
            "state": "check_in_progress",
            "task_id": "GPU-1",
            "execution_id": "JOB-1",
            "automation_id": "gpu-1-watchdog",
            "terminal_event_id": "TERM-GPU-1",
            "recovery_receipt": "check-gpu-1",
        }
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_live_gpu_requires_active_job_specific_watchdog(self) -> None:
        record = base_record()
        del record["gpu_running"]["watchdog"]
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gpu_running requires watchdog object", result.stdout)

    def test_launch_ready_gpu_requires_active_launch_owner(self) -> None:
        record = base_record()
        record["gpu_running"] = None
        queue_item = record["gpu_queue"][0]
        queue_item["queue_state"] = "launch_ready"
        queue_item.pop("blocking_fact")
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires gpu_launch_in_progress", result.stdout)

        record["gpu_launch_in_progress"] = {
            **task_lease_fields(
                "GPU-2",
                "gpu-owner-2",
                "DISPATCH-GPU-2",
                1,
                "TERM-GPU-2-LAUNCH",
            ),
            "owner_thread_status": "active",
            "dispatch_receipt": "receipt-gpu-2-launch",
        }
        record["worker_registry"].append(
            {
                "owner_thread_id": "gpu-owner-2",
                "max_lease_epoch": 1,
                "current_lease": {
                    "task_id": "GPU-2",
                    "owner_thread_id": "gpu-owner-2",
                    "dispatch_id": "DISPATCH-GPU-2",
                    "lease_epoch": 1,
                },
            }
        )
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_acknowledged_dispatch_requires_receipt_and_active_owner(self) -> None:
        record = base_record()
        record["terminal_transaction"] = {
            "callback_state": "acknowledged",
            "delivered_callback": delivered_callback_fields(),
            "portfolio_reconciled": True,
            "portfolio_reconciled_at_utc": "2026-07-27T00:03:00Z",
            "acknowledged_at_utc": "2026-07-27T00:04:00Z",
            "delivery_intent_durable": True,
            "watchdog_state": "paused",
            "next_action": {
                **task_lease_fields(
                    "ZERO-1",
                    "zero-owner",
                    "DISPATCH-ZERO-1",
                    1,
                    "TERM-ZERO-1",
                ),
                "kind": "dispatch_next",
                "owner_thread_status": "idle",
            },
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dispatch_next requires non-empty dispatch_receipt", result.stdout)
        self.assertIn("owner_thread_status=active", result.stdout)

        action = record["terminal_transaction"]["next_action"]
        action["dispatch_receipt"] = "receipt-zero-1"
        action["owner_thread_status"] = "active"
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_hold_cannot_be_orphaned(self) -> None:
        record = base_record()
        record["terminal_transaction"] = {
            "callback_state": "acknowledged",
            "delivered_callback": delivered_callback_fields(),
            "portfolio_reconciled": True,
            "portfolio_reconciled_at_utc": "2026-07-27T00:03:00Z",
            "acknowledged_at_utc": "2026-07-27T00:04:00Z",
            "delivery_intent_durable": True,
            "watchdog_state": "paused",
            "next_action": {
                "kind": "explicit_hold",
                "task_id": "ZERO-HOLD",
                "owner_thread_id": "zero-owner",
                "reopening_fact": "new source release",
                "reopening_predicate": "source_release_available == true",
                "observer_thread_id": "zero-owner",
                "reopen_trigger_ref": "source-release-event",
                "next_evidence_action": "rerun bounded source audit",
            },
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must match one blocked backlog item", result.stdout)

        record["zero_gpu_backlog"] = [
            {
                "task_id": "ZERO-HOLD",
                "status": "blocked",
                "reopening_fact": "new source release",
                "reopening_predicate": "source_release_available == true",
                "observer_thread_id": "zero-owner",
                "reopen_trigger_ref": "source-release-event",
                "next_evidence_action": "rerun bounded source audit",
            }
        ]
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_active_thread_cannot_impersonate_another_task_lease(self) -> None:
        record = base_record()
        record["zero_gpu_running"]["activation_evidence"]["task_id"] = "OTHER"
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("activation_evidence.task_id must match", result.stdout)

    def test_stale_dispatch_callback_lease_is_rejected(self) -> None:
        record = base_record()
        record["zero_gpu_running"]["callback_binding"]["lease_epoch"] = 2
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("callback_binding.lease_epoch must match", result.stdout)

        record = base_record()
        record["terminal_transaction"] = {
            "callback_state": "acknowledged",
            "delivered_callback": delivered_callback_fields(),
            "portfolio_reconciled": True,
            "portfolio_reconciled_at_utc": "2026-07-27T00:03:00Z",
            "acknowledged_at_utc": "2026-07-27T00:04:00Z",
            "delivery_intent_durable": True,
            "watchdog_state": "paused",
            "next_action": {
                **task_lease_fields(
                    "ZERO-1",
                    "zero-owner",
                    "OLD-DISPATCH-ZERO-1",
                    2,
                    "TERM-ZERO-1",
                ),
                "kind": "dispatch_next",
                "owner_thread_status": "active",
                "dispatch_receipt": "old-receipt",
            },
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dispatch_next lease must exactly match", result.stdout)

    def test_overdue_recovery_evidence_must_match_current_lease(self) -> None:
        record = base_record()
        record["observed_at_utc"] = "2026-07-27T00:21:00Z"
        record["pro_advisory_lane"]["live_jobs"][0][
            "next_check_due_at_utc"
        ] = "2026-07-27T01:00:00Z"
        record["gpu_running"]["watchdog"]["due_handling"] = {
            "state": "check_in_progress",
            "task_id": "GPU-1",
            "execution_id": "JOB-1",
            "automation_id": "gpu-1-watchdog",
            "terminal_event_id": "TERM-GPU-1",
            "recovery_receipt": "check-gpu-1",
        }
        record["zero_gpu_running"]["progress_due_handling"] = {
            "state": "recovery_dispatched",
            "task_id": "OTHER",
            "owner_thread_id": "zero-owner",
            "dispatch_id": "OLD-DISPATCH",
            "lease_epoch": 0,
            "recovery_receipt": "wrong-recovery",
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("progress_due_handling.task_id must match", result.stdout)
        self.assertIn("progress_due_handling.dispatch_id must match", result.stdout)

    def test_blocked_hold_requires_observer_and_concrete_trigger(self) -> None:
        record = base_record()
        record["zero_gpu_backlog"] = [
            {
                "task_id": "TEXT-ONLY-HOLD",
                "status": "blocked",
                "reopening_fact": "more evidence someday",
                "next_evidence_action": "look again",
            }
        ]
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires non-empty reopening_predicate", result.stdout)
        self.assertIn("requires non-empty observer_thread_id", result.stdout)
        self.assertIn("requires reopen_trigger_ref or next_check_at_utc", result.stdout)

    def test_watchdog_must_bind_the_exact_live_job_and_wake_owner(self) -> None:
        record = base_record()
        watchdog = record["gpu_running"]["watchdog"]
        watchdog["execution_id"] = "WRONG-JOB"
        watchdog["target_thread_id"] = "wrong-thread"
        watchdog["wake_owner_thread_id"] = "wrong-owner"
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("watchdog.execution_id must match", result.stdout)
        self.assertIn("watchdog.target_thread_id must match", result.stdout)
        self.assertIn("watchdog.wake_owner_thread_id must match", result.stdout)

    def test_one_owner_cannot_hold_two_current_task_leases(self) -> None:
        record = base_record()
        record["gpu_running"] = None
        queue_item = record["gpu_queue"][0]
        queue_item["queue_state"] = "launch_ready"
        queue_item.pop("blocking_fact")
        record["gpu_launch_in_progress"] = {
            **task_lease_fields(
                "GPU-2",
                "zero-owner",
                "DISPATCH-GPU-2",
                1,
                "TERM-GPU-2-LAUNCH",
            ),
            "owner_thread_status": "active",
            "dispatch_receipt": "receipt-gpu-2-launch",
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("holds multiple current task leases", result.stdout)

    def test_current_lease_cannot_regress_below_durable_owner_epoch(self) -> None:
        record = base_record()
        record["worker_registry"][0]["max_lease_epoch"] = 2
        record["worker_registry"][0]["current_lease"]["lease_epoch"] = 2
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("below durable max_lease_epoch", result.stdout)
        self.assertIn("must exactly match worker_registry.current_lease", result.stdout)

    def test_acknowledged_terminal_requires_exact_callback_lease_provenance(self) -> None:
        record = base_record()
        record["terminal_transaction"] = {
            "callback_state": "acknowledged",
            "delivered_callback": delivered_callback_fields(dispatch="OLD-DISPATCH"),
            "portfolio_reconciled": True,
            "portfolio_reconciled_at_utc": "2026-07-27T00:03:00Z",
            "acknowledged_at_utc": "2026-07-27T00:04:00Z",
            "delivery_intent_durable": True,
            "watchdog_state": "paused",
            "next_action": {"kind": "queued", "task_id": "GPU-2", "owner_thread_id": "gpu-owner-2", "start_prerequisite": "GPU-1 terminal"},
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must match exactly one durable terminal idempotency record", result.stdout)

    def test_recovery_dispatch_cannot_leave_old_lease_current(self) -> None:
        record = base_record()
        record["observed_at_utc"] = "2026-07-27T00:21:00Z"
        record["pro_advisory_lane"]["live_jobs"][0]["next_check_due_at_utc"] = (
            "2026-07-27T01:00:00Z"
        )
        record["gpu_running"]["watchdog"]["due_handling"] = {
            "state": "check_in_progress",
            "task_id": "GPU-1",
            "execution_id": "JOB-1",
            "automation_id": "gpu-1-watchdog",
            "terminal_event_id": "TERM-GPU-1",
            "recovery_receipt": "check-gpu-1",
        }
        record["zero_gpu_running"]["progress_due_handling"] = {
            "state": "recovery_dispatched",
            "task_id": "ZERO-1",
            "owner_thread_id": "zero-owner",
            "dispatch_id": "DISPATCH-ZERO-1",
            "lease_epoch": 1,
            "recovery_receipt": "recover-zero-1",
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must revoke the old lease", result.stdout)

    def test_durable_watermark_rejects_later_epoch_downgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "watermark.json"
            high = base_record()
            high["zero_gpu_running"] = {
                **task_lease_fields(
                    "ZERO-1", "zero-owner", "DISPATCH-ZERO-2", 2, "TERM-ZERO-2"
                ),
                "owner_thread_status": "active",
                "kind": "opportunity_search",
                "expected_reasoning_effort": "max",
                "callback_registered": True,
                "dispatch_receipt": "receipt-zero-2",
                "progress_due_at_utc": "2026-07-27T00:20:00Z",
            }
            high["worker_registry"][0]["max_lease_epoch"] = 2
            high["worker_registry"][0]["current_lease"] = {
                "task_id": "ZERO-1",
                "owner_thread_id": "zero-owner",
                "dispatch_id": "DISPATCH-ZERO-2",
                "lease_epoch": 2,
            }
            first = run_record(high, state)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            downgraded = base_record()
            second = run_record(downgraded, state)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("below durable watermark", second.stdout)

    def test_durable_watermark_rejects_old_callback_after_newer_epoch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "watermark.json"
            anchored = base_record()
            anchored["worker_registry"][1]["max_lease_epoch"] = 2
            first = run_record(anchored, state)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            stale = base_record()
            stale["worker_registry"][1]["max_lease_epoch"] = 2
            stale["terminal_transaction"] = {
                "callback_state": "acknowledged",
                "delivered_callback": delivered_callback_fields(),
                "portfolio_reconciled": True,
                "portfolio_reconciled_at_utc": "2026-07-27T00:03:00Z",
                "acknowledged_at_utc": "2026-07-27T00:04:00Z",
                "delivery_intent_durable": True,
                "watchdog_state": "paused",
                "next_action": {
                    "kind": "queued",
                    "task_id": "GPU-2",
                    "owner_thread_id": "gpu-owner-2",
                    "start_prerequisite": "GPU-1 terminal",
                },
            }
            second = run_record(stale, state)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("pre-transaction durable watermark", second.stdout)

    def test_new_current_lease_requires_durable_transition_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "watermark.json"
            first = run_record(base_record(), state)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            replacement = base_record()
            replacement["zero_gpu_running"] = {
                **task_lease_fields(
                    "ZERO-2", "zero-owner", "DISPATCH-ZERO-2", 2, "TERM-ZERO-2"
                ),
                "owner_thread_status": "active",
                "kind": "opportunity_search",
                "expected_reasoning_effort": "max",
                "callback_registered": True,
                "dispatch_receipt": "receipt-zero-2",
                "progress_due_at_utc": "2026-07-27T00:20:00Z",
            }
            replacement["worker_registry"][0]["max_lease_epoch"] = 2
            replacement["worker_registry"][0]["current_lease"] = {
                "task_id": "ZERO-2",
                "owner_thread_id": "zero-owner",
                "dispatch_id": "DISPATCH-ZERO-2",
                "lease_epoch": 2,
            }
            missing = run_record(replacement, state)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("requires exactly one durable transition", missing.stdout)

            replacement["lease_transitions"] = [
                {
                    "owner_thread_id": "zero-owner",
                    "prior_max_lease_epoch": 1,
                    "from_lease": {
                        "task_id": "ZERO-1",
                        "owner_thread_id": "zero-owner",
                        "dispatch_id": "DISPATCH-ZERO-1",
                        "lease_epoch": 1,
                    },
                    "to_lease": {
                        "task_id": "ZERO-2",
                        "owner_thread_id": "zero-owner",
                        "dispatch_id": "DISPATCH-ZERO-2",
                        "lease_epoch": 2,
                    },
                    "transition_kind": "recovery_replacement",
                    "transition_receipt": "recover-zero-2",
                    "transitioned_at_utc": "2026-07-27T00:11:00Z",
                }
            ]
            passed = run_record(replacement, state)
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)


if __name__ == "__main__":
    unittest.main()
