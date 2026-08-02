from __future__ import annotations

import copy
import hashlib
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
    record: dict[str, object],
    state_path: Path | None = None,
    *,
    migrate_final_ack: bool = True,
    check_only: bool = False,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temp:
        record = copy.deepcopy(record)
        path = Path(temp) / "lanes.json"
        effective_state = state_path or Path(temp) / "watermark.json"
        terminal = record.get("terminal_transaction")
        if (
            migrate_final_ack
            and isinstance(terminal, dict)
            and terminal.get("callback_state") == "acknowledged"
        ):
            terminal.setdefault("ack_kind", "FINAL_ACK")
            terminal.setdefault("final_ack_receipt", "final-ack-tool-receipt")
            if "terminal_artifact" not in terminal:
                terminal_path = Path(temp) / "terminal-packet.json"
                terminal_path.write_bytes(b'{"status":"frozen"}\n')
                terminal["terminal_artifact"] = {
                    "path": str(terminal_path),
                    "callback_bound_sha256": hashlib.sha256(
                        terminal_path.read_bytes()
                    ).hexdigest(),
                    "callback_delivered": True,
                }
            artifact = terminal.get("terminal_artifact")
            callback = terminal.get("delivered_callback")
            history = record.get("terminal_idempotency_history")
            if (
                isinstance(artifact, dict)
                and isinstance(callback, dict)
                and isinstance(history, list)
            ):
                for item in history:
                    if not isinstance(item, dict):
                        continue
                    if all(
                        item.get(key) == callback.get(key)
                        for key in (
                            "task_id",
                            "owner_thread_id",
                            "dispatch_id",
                            "lease_epoch",
                            "terminal_event_id",
                            "callback_receipt",
                        )
                    ):
                        item.setdefault("terminal_path", artifact.get("path"))
                        item.setdefault(
                            "callback_bound_sha256",
                            artifact.get("callback_bound_sha256"),
                        )
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        command = [
            sys.executable,
            str(VALIDATOR),
            str(path),
            "--state",
            str(effective_state),
        ]
        if check_only:
            command.append("--check-only")
        return subprocess.run(
            command,
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
                    "owner_thread_id": "controller",
                    "owner_generation": 1,
                    "job_generation": 1,
                    "callback_event_key": "PRO-CALLBACK-PRO-1-G1",
                    "completion_callback_thread_id": "controller",
                    "completion_callback_configured": True,
                    "submitted_at_utc": "2026-07-27T00:00:00Z",
                    "next_check_due_at_utc": "2026-07-27T00:15:00Z",
                    "status": "submitted",
                }
            ],
            "queue": [],
            "response_ready": [],
            "callback_observations": [],
            "explicit_idle_reason": None,
        },
    }


def acknowledged_record(terminal_path: Path, digest: str) -> dict[str, object]:
    record = base_record()
    record["terminal_idempotency_history"][0].update(
        {
            "terminal_path": str(terminal_path),
            "callback_bound_sha256": digest,
        }
    )
    record["terminal_transaction"] = {
        "callback_state": "acknowledged",
        "ack_kind": "FINAL_ACK",
        "final_ack_receipt": "final-ack-tool-receipt",
        "delivered_callback": delivered_callback_fields(),
        "terminal_artifact": {
            "path": str(terminal_path),
            "callback_bound_sha256": digest,
            "callback_delivered": True,
        },
        "portfolio_reconciled": True,
        "portfolio_reconciled_at_utc": "2026-07-27T00:03:00Z",
        "acknowledged_at_utc": "2026-07-27T00:06:00Z",
        "delivery_intent_durable": True,
        "watchdog_state": "paused",
        "next_action": {
            "kind": "queued",
            "task_id": "GPU-2",
            "owner_thread_id": "gpu-owner-2",
            "start_prerequisite": "GPU-1 terminal",
        },
    }
    return record


def response_ready_record(
    *,
    owner_generation: int = 1,
    job_generation: int = 1,
    event_key: str = "PRO-CALLBACK-PRO-DONE-G1",
) -> dict[str, object]:
    record = base_record()
    record["pro_advisory_lane"] = {
        "live_jobs": [],
        "queue": [],
        "response_ready": [
            {
                "job_id": "PRO-DONE",
                "decision": "theory bottleneck",
                "owner_thread_id": "controller",
                "owner_generation": owner_generation,
                "job_generation": job_generation,
                "callback_event_key": event_key,
                "callback_disposition": "current",
                "response_artifact": "/evidence/pro-done.json",
                "completed_at_utc": "2026-07-27T00:05:00Z",
            }
        ],
        "callback_observations": [],
        "adjudicating_job_id": "PRO-DONE",
        "explicit_idle_reason": None,
    }
    return record


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
                "owner_thread_status": "active",
                "dispatch_receipt": "receipt-zero-1",
            },
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("portfolio_reconciled=true", result.stdout)

        record["terminal_transaction"]["portfolio_reconciled"] = True
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("activation evidence must precede FINAL_ACK", result.stdout)

        record["terminal_transaction"]["acknowledged_at_utc"] = (
            "2026-07-27T00:06:00Z"
        )
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
                    "owner_generation": 1,
                    "job_generation": 1,
                    "callback_event_key": "PRO-CALLBACK-PRO-DONE-G1",
                    "callback_disposition": "current",
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
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("activation evidence must precede FINAL_ACK", result.stdout)

        record["terminal_transaction"]["acknowledged_at_utc"] = (
            "2026-07-27T00:06:00Z"
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
            "acknowledged_at_utc": "2026-07-27T00:06:00Z",
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

    def test_same_record_final_ack_replay_survives_atomic_successor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            terminal_path = root / "terminal-packet.json"
            terminal_path.write_bytes(b'{"status":"frozen"}\n')
            digest = hashlib.sha256(terminal_path.read_bytes()).hexdigest()
            state = root / "watermark.json"

            pretransaction = base_record()
            pretransaction["terminal_idempotency_history"][0].update(
                {
                    "terminal_path": str(terminal_path),
                    "callback_bound_sha256": digest,
                }
            )
            source_lease = {
                "task_id": "SOURCE-1",
                "owner_thread_id": "source-owner",
                "dispatch_id": "DISPATCH-SOURCE-1",
                "lease_epoch": 1,
            }
            pretransaction["worker_registry"] = [
                {
                    "owner_thread_id": "source-owner",
                    "max_lease_epoch": 1,
                    "current_lease": source_lease,
                }
            ]
            pretransaction["zero_gpu_running"] = {
                **task_lease_fields(
                    "SOURCE-1",
                    "source-owner",
                    "DISPATCH-SOURCE-1",
                    1,
                    "TERM-SOURCE-1",
                ),
                "owner_thread_status": "active",
                "kind": "opportunity_search",
                "expected_reasoning_effort": "max",
                "callback_registered": True,
                "dispatch_receipt": "receipt-source-1",
                "progress_due_at_utc": "2026-07-27T00:20:00Z",
            }
            pretransaction["opportunity_search"] = {
                "status": "active",
                "task_id": "SOURCE-1",
            }
            seeded = run_record(pretransaction, state)
            self.assertEqual(seeded.returncode, 0, seeded.stdout + seeded.stderr)

            record = acknowledged_record(terminal_path, digest)
            successor = {
                **task_lease_fields(
                    "SOURCE-NEXT",
                    "source-owner",
                    "DISPATCH-SOURCE-NEXT",
                    2,
                    "TERM-SOURCE-NEXT",
                ),
                "owner_thread_status": "active",
                "kind": "opportunity_search",
                "expected_reasoning_effort": "max",
                "callback_registered": True,
                "dispatch_receipt": "receipt-source-next",
                "progress_due_at_utc": "2026-07-27T00:20:00Z",
            }
            record["zero_gpu_running"] = successor
            record["opportunity_search"] = {
                "status": "active",
                "task_id": "SOURCE-NEXT",
            }
            record["worker_registry"] = [
                {
                    "owner_thread_id": "source-owner",
                    "max_lease_epoch": 2,
                    "current_lease": {
                        "task_id": "SOURCE-NEXT",
                        "owner_thread_id": "source-owner",
                        "dispatch_id": "DISPATCH-SOURCE-NEXT",
                        "lease_epoch": 2,
                    },
                }
            ]
            record["lease_transitions"] = [
                {
                    "owner_thread_id": "source-owner",
                    "prior_max_lease_epoch": 1,
                    "from_lease": {
                        "task_id": "SOURCE-1",
                        "owner_thread_id": "source-owner",
                        "dispatch_id": "DISPATCH-SOURCE-1",
                        "lease_epoch": 1,
                    },
                    "to_lease": {
                        "task_id": "SOURCE-NEXT",
                        "owner_thread_id": "source-owner",
                        "dispatch_id": "DISPATCH-SOURCE-NEXT",
                        "lease_epoch": 2,
                    },
                    "transition_kind": "completed_successor",
                    "transition_receipt": "receipt-source-atomic-successor",
                    "transitioned_at_utc": "2026-07-27T00:04:00Z",
                }
            ]
            record["terminal_transaction"]["next_action"] = {
                **successor,
                "kind": "dispatch_next",
            }

            late_transition = copy.deepcopy(record)
            late_transition["lease_transitions"][0]["transitioned_at_utc"] = (
                "2026-07-27T00:07:00Z"
            )
            before_late_transition = state.read_bytes()
            rejected_late_transition = run_record(
                late_transition,
                state,
                migrate_final_ack=False,
            )
            self.assertNotEqual(rejected_late_transition.returncode, 0)
            self.assertIn(
                "durable transition must precede FINAL_ACK",
                rejected_late_transition.stdout,
            )
            self.assertEqual(state.read_bytes(), before_late_transition)

            advanced = run_record(record, state, migrate_final_ack=False)
            self.assertEqual(advanced.returncode, 0, advanced.stdout + advanced.stderr)
            advanced_bytes = state.read_bytes()
            advanced_state = json.loads(advanced_bytes)
            self.assertEqual(advanced_state["generation"], 2)
            self.assertEqual(
                advanced_state["owner_registry"]["source-owner"]["max_lease_epoch"],
                2,
            )

            replay = run_record(
                record,
                state,
                migrate_final_ack=False,
                check_only=True,
            )
            self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
            self.assertEqual(state.read_bytes(), advanced_bytes)

            changed = copy.deepcopy(record)
            changed["observed_at_utc"] = "2026-07-27T00:11:00Z"
            rejected = run_record(
                changed,
                state,
                migrate_final_ack=False,
                check_only=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("already acknowledged", rejected.stdout)
            self.assertEqual(state.read_bytes(), advanced_bytes)

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
            passed_bytes = state.read_bytes()

            cumulative_history = copy.deepcopy(replacement)
            cumulative_history["observed_at_utc"] = "2026-07-27T00:12:00Z"
            replayed_history = run_record(cumulative_history, state)
            self.assertEqual(
                replayed_history.returncode,
                0,
                replayed_history.stdout + replayed_history.stderr,
            )
            self.assertEqual(state.read_bytes(), passed_bytes)

    def test_d04_final_ack_recomputes_callback_bound_terminal_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            terminal_path = root / "terminal-packet.json"
            terminal_path.write_bytes(b'{"status":"frozen"}\n')
            correct_digest = hashlib.sha256(terminal_path.read_bytes()).hexdigest()

            for label, digest, remove_file, expected in (
                ("malformed", "not-a-sha", False, "canonical 64-hex"),
                ("mismatch", "0" * 64, False, "digest mismatch"),
                ("missing", correct_digest, True, "is not a local file"),
            ):
                with self.subTest(label=label):
                    if remove_file:
                        terminal_path.unlink(missing_ok=True)
                    else:
                        terminal_path.write_bytes(b'{"status":"frozen"}\n')
                    state = root / f"{label}-watermark.json"
                    result = run_record(
                        acknowledged_record(terminal_path, digest),
                        state,
                        migrate_final_ack=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stdout)
                    self.assertFalse(state.exists(), "failed FINAL_ACK advanced watermark")

            terminal_path.write_bytes(b'{"status":"frozen"}\n')
            state = root / "healthy-watermark.json"
            result = run_record(
                acknowledged_record(terminal_path, correct_digest),
                state,
                migrate_final_ack=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(state.is_file())

            lifecycle_state = root / "lifecycle-watermark.json"
            delivered = base_record()
            delivered["terminal_idempotency_history"][0].update(
                {
                    "terminal_path": str(terminal_path),
                    "callback_bound_sha256": correct_digest,
                }
            )
            delivered["terminal_transaction"]["callback_state"] = "delivered"
            delivered_result = run_record(delivered, lifecycle_state)
            self.assertEqual(
                delivered_result.returncode,
                0,
                delivered_result.stdout + delivered_result.stderr,
            )
            acknowledged_result = run_record(
                acknowledged_record(terminal_path, correct_digest),
                lifecycle_state,
                migrate_final_ack=False,
            )
            self.assertEqual(
                acknowledged_result.returncode,
                0,
                acknowledged_result.stdout + acknowledged_result.stderr,
            )

            legacy_state = root / "legacy-watermark.json"
            legacy_delivered = run_record(base_record(), legacy_state)
            self.assertEqual(legacy_delivered.returncode, 0)
            legacy_upgrade = run_record(
                acknowledged_record(terminal_path, correct_digest),
                legacy_state,
                migrate_final_ack=False,
            )
            self.assertNotEqual(legacy_upgrade.returncode, 0)
            self.assertIn("must preserve every durable prior record", legacy_upgrade.stdout)

    def test_d06_unknown_callback_state_is_rejected(self) -> None:
        record = base_record()
        record["terminal_transaction"]["callback_state"] = "self_attested_done"
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("callback_state must be one of", result.stdout)

    def test_d06_final_ack_requires_kind_and_distinct_tool_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            terminal_path = Path(temp) / "terminal-packet.json"
            terminal_path.write_bytes(b'{"status":"frozen"}\n')
            digest = hashlib.sha256(terminal_path.read_bytes()).hexdigest()
            cases = []
            missing_kind = acknowledged_record(terminal_path, digest)
            del missing_kind["terminal_transaction"]["ack_kind"]
            cases.append(("missing_kind", missing_kind, "ack_kind=FINAL_ACK"))
            receipt_only = acknowledged_record(terminal_path, digest)
            receipt_only["terminal_transaction"]["ack_kind"] = "RECEIPT_ONLY"
            cases.append(("receipt_only", receipt_only, "ack_kind=FINAL_ACK"))
            missing_receipt = acknowledged_record(terminal_path, digest)
            missing_receipt["terminal_transaction"]["final_ack_receipt"] = None
            cases.append(("missing_receipt", missing_receipt, "final_ack_receipt"))
            shared_receipt = acknowledged_record(terminal_path, digest)
            shared_receipt["terminal_transaction"]["final_ack_receipt"] = (
                shared_receipt["terminal_transaction"]["delivered_callback"][
                    "callback_receipt"
                ]
            )
            cases.append(("shared_receipt", shared_receipt, "must be distinct"))
            future_ack = acknowledged_record(terminal_path, digest)
            future_ack["terminal_transaction"].update(
                {
                    "portfolio_reconciled_at_utc": "2099-01-01T00:00:00Z",
                    "acknowledged_at_utc": "2099-01-01T00:00:01Z",
                }
            )
            cases.append(
                (
                    "future_ack",
                    future_ack,
                    "later than the snapshot observation",
                )
            )
            for label, record, expected in cases:
                with self.subTest(label=label):
                    state = Path(temp) / f"{label}-watermark.json"
                    result = run_record(
                        record,
                        state,
                        migrate_final_ack=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stdout)
                    self.assertFalse(state.exists())

    def test_d07_current_callback_generation_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "watermark.json"
            record = response_ready_record()
            first = run_record(record, state)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            first_state = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(first_state["generation"], 1)
            self.assertIn(
                "PRO-CALLBACK-PRO-DONE-G1",
                first_state["pro_callback_event_keys"],
            )
            self.assertEqual(
                first_state["pro_callback_event_keys"][
                    "PRO-CALLBACK-PRO-DONE-G1"
                ]["state"],
                "consumed",
            )

            replay = run_record(record, state)
            self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
            replay_state = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(replay_state, first_state)

            stable_state = Path(temp) / "stable-key-watermark.json"
            live_record = base_record()
            registered = run_record(live_record, stable_state)
            self.assertEqual(registered.returncode, 0, registered.stdout + registered.stderr)
            registered_state = json.loads(stable_state.read_text(encoding="utf-8"))
            self.assertEqual(
                registered_state["pro_callback_event_keys"][
                    "PRO-CALLBACK-PRO-1-G1"
                ]["state"],
                "registered",
            )

            response = base_record()
            completed_job = copy.deepcopy(
                response["pro_advisory_lane"]["live_jobs"][0]
            )
            completed_job.update(
                {
                    "callback_event_key": "PRO-CALLBACK-CHANGED",
                    "callback_disposition": "current",
                    "response_artifact": "/evidence/pro-1.json",
                    "completed_at_utc": "2026-07-27T00:05:00Z",
                }
            )
            response["pro_advisory_lane"] = {
                "live_jobs": [],
                "queue": [],
                "response_ready": [completed_job],
                "callback_observations": [],
                "adjudicating_job_id": "PRO-1",
                "explicit_idle_reason": None,
            }
            before_changed_key = stable_state.read_bytes()
            changed_key = run_record(response, stable_state)
            self.assertNotEqual(changed_key.returncode, 0)
            self.assertIn("changed its stable callback event key", changed_key.stdout)
            self.assertEqual(stable_state.read_bytes(), before_changed_key)

            completed_job["callback_event_key"] = "PRO-CALLBACK-PRO-1-G1"
            accepted = run_record(response, stable_state)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            consumed_state = json.loads(stable_state.read_text(encoding="utf-8"))
            self.assertEqual(
                consumed_state["pro_callback_event_keys"][
                    "PRO-CALLBACK-PRO-1-G1"
                ]["state"],
                "consumed",
            )

    def test_d07_observation_noops_and_registered_closure_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "watermark.json"
            anchor = base_record()
            live = anchor["pro_advisory_lane"]["live_jobs"][0]
            live["owner_generation"] = 2
            live["job_generation"] = 2
            live["callback_event_key"] = "PRO-CALLBACK-PRO-1-G2"
            first = run_record(anchor, state)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            anchor_state = json.loads(state.read_text(encoding="utf-8"))

            contradictory = copy.deepcopy(anchor)
            contradictory["pro_advisory_lane"]["callback_observations"] = [
                {
                    "observation_id": "OBS-CLOSED-LIVE",
                    "job_id": "PRO-1",
                    "owner_thread_id": "controller",
                    "owner_generation": 2,
                    "job_generation": 2,
                    "callback_event_key": "PRO-CALLBACK-PRO-1-G2",
                    "disposition": "closed",
                    "effect_counts": {"adjudication": 0, "dispatch": 0, "ack": 0},
                    "closed_at_utc": "2026-07-27T00:04:00Z",
                    "observed_at_utc": "2026-07-27T00:06:00Z",
                }
            ]
            before_contradiction = state.read_bytes()
            rejected_contradiction = run_record(contradictory, state)
            self.assertNotEqual(rejected_contradiction.returncode, 0)
            self.assertIn("cannot remain live or response_ready", rejected_contradiction.stdout)
            self.assertEqual(state.read_bytes(), before_contradiction)

            observation_only = copy.deepcopy(anchor)
            observation_only["pro_advisory_lane"]["callback_observations"] = [
                {
                    "observation_id": "OBS-STALE-1",
                    "job_id": "PRO-1",
                    "owner_thread_id": "controller",
                    "owner_generation": 1,
                    "job_generation": 1,
                    "callback_event_key": "PRO-CALLBACK-PRO-1-G1",
                    "disposition": "stale",
                    "effect_counts": {"adjudication": 0, "dispatch": 0, "ack": 0},
                    "observed_at_utc": "2026-07-27T00:06:00Z",
                },
                {
                    "observation_id": "OBS-CLOSED-1",
                    "job_id": "PRO-CLOSED",
                    "owner_thread_id": "controller",
                    "owner_generation": 999,
                    "job_generation": 999,
                    "callback_event_key": "PRO-CALLBACK-PRO-CLOSED-G999",
                    "disposition": "closed",
                    "effect_counts": {"adjudication": 0, "dispatch": 0, "ack": 0},
                    "closed_at_utc": "2026-07-27T00:04:00Z",
                    "observed_at_utc": "2026-07-27T00:06:00Z",
                },
            ]
            before_observation_only = state.read_bytes()
            observed = run_record(observation_only, state)
            self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
            self.assertEqual(state.read_bytes(), before_observation_only)
            observed_state = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(observed_state, anchor_state)
            self.assertEqual(
                observed_state["pro_callback_event_keys"],
                anchor_state["pro_callback_event_keys"],
            )
            self.assertEqual(observed_state["pro_owner_generations"], {"controller": 2})
            self.assertNotIn("PRO-CLOSED", observed_state["pro_job_generations"])

            closed_snapshot = copy.deepcopy(anchor)
            closed_snapshot["pro_advisory_lane"] = {
                "live_jobs": [],
                "queue": [],
                "response_ready": [],
                "callback_observations": [
                    {
                        "observation_id": "OBS-CLOSED-REGISTERED",
                        "job_id": "PRO-1",
                        "owner_thread_id": "controller",
                        "owner_generation": 2,
                        "job_generation": 2,
                        "callback_event_key": "PRO-CALLBACK-PRO-1-G2",
                        "disposition": "closed",
                        "effect_counts": {
                            "adjudication": 0,
                            "dispatch": 0,
                            "ack": 0,
                        },
                        "closed_at_utc": "2026-07-27T00:04:00Z",
                        "observed_at_utc": "2026-07-27T00:06:00Z",
                    }
                ],
                "explicit_idle_reason": "registered job generation closed",
            }
            closed = run_record(closed_snapshot, state)
            self.assertEqual(closed.returncode, 0, closed.stdout + closed.stderr)
            closed_state = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(closed_state["generation"], anchor_state["generation"] + 1)
            self.assertEqual(
                closed_state["pro_callback_event_keys"][
                    "PRO-CALLBACK-PRO-1-G2"
                ]["state"],
                "closed",
            )

            closed_bytes = state.read_bytes()
            replayed_closure = copy.deepcopy(closed_snapshot)
            replayed_closure["pro_advisory_lane"]["callback_observations"][0].update(
                {
                    "observation_id": "OBS-CLOSED-REGISTERED-REPLAY",
                    "observed_at_utc": "2026-07-27T00:07:00Z",
                }
            )
            replayed = run_record(replayed_closure, state)
            self.assertEqual(replayed.returncode, 0, replayed.stdout + replayed.stderr)
            self.assertEqual(state.read_bytes(), closed_bytes)

            reopened = response_ready_record(
                owner_generation=2,
                job_generation=2,
                event_key="PRO-CALLBACK-PRO-1-G2",
            )
            reopened_response = reopened["pro_advisory_lane"]["response_ready"][0]
            reopened_response["job_id"] = "PRO-1"
            reopened["pro_advisory_lane"]["adjudicating_job_id"] = "PRO-1"
            before_reopen = state.read_bytes()
            rejected_reopen = run_record(reopened, state)
            self.assertNotEqual(rejected_reopen.returncode, 0)
            self.assertIn("belongs to a closed job generation", rejected_reopen.stdout)
            self.assertEqual(state.read_bytes(), before_reopen)

            stale_ready = response_ready_record(
                owner_generation=1,
                job_generation=1,
                event_key="PRO-CALLBACK-PRO-DONE-STALE",
            )
            before = state.read_bytes()
            rejected = run_record(stale_ready, state)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("below the durable watermark", rejected.stdout)
            self.assertEqual(state.read_bytes(), before)

    def test_d07_duplicate_event_key_has_no_second_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "watermark.json"
            current = response_ready_record()
            first = run_record(current, state)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            first_state = json.loads(state.read_text(encoding="utf-8"))

            duplicate_ready = response_ready_record()
            duplicate_ready["observed_at_utc"] = "2026-07-27T00:11:00Z"
            before = state.read_bytes()
            rejected = run_record(duplicate_ready, state)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("already consumed", rejected.stdout)
            self.assertEqual(state.read_bytes(), before)

            observation = base_record()
            observation["observed_at_utc"] = "2026-07-27T00:12:00Z"
            observation["pro_advisory_lane"] = {
                "live_jobs": [],
                "queue": [],
                "response_ready": [],
                "callback_observations": [
                    {
                        "observation_id": "OBS-DUPLICATE-1",
                        "job_id": "PRO-DONE",
                        "owner_thread_id": "controller",
                        "owner_generation": 1,
                        "job_generation": 1,
                        "callback_event_key": "PRO-CALLBACK-PRO-DONE-G1",
                        "disposition": "duplicate",
                        "effect_counts": {
                            "adjudication": 0,
                            "dispatch": 0,
                            "ack": 0,
                        },
                        "observed_at_utc": "2026-07-27T00:12:00Z",
                    }
                ],
                "explicit_idle_reason": "duplicate callback observed; no live work",
            }
            settled = copy.deepcopy(observation)
            settled["pro_advisory_lane"]["callback_observations"] = []
            settled_result = run_record(settled, state)
            self.assertEqual(
                settled_result.returncode,
                0,
                settled_result.stdout + settled_result.stderr,
            )
            settled_state = json.loads(state.read_text(encoding="utf-8"))
            before_observation = state.read_bytes()
            accepted_observation = run_record(observation, state)
            self.assertEqual(
                accepted_observation.returncode,
                0,
                accepted_observation.stdout + accepted_observation.stderr,
            )
            self.assertEqual(state.read_bytes(), before_observation)
            observed_state = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(observed_state, settled_state)
            self.assertEqual(
                observed_state["pro_callback_event_keys"],
                first_state["pro_callback_event_keys"],
            )

            conflicting = copy.deepcopy(observation)
            conflicting_observation = conflicting["pro_advisory_lane"][
                "callback_observations"
            ][0]
            conflicting_observation["job_id"] = "PRO-OTHER"
            before_conflict = state.read_bytes()
            rejected_conflict = run_record(conflicting, state)
            self.assertNotEqual(rejected_conflict.returncode, 0)
            self.assertIn("conflicts with its stable binding", rejected_conflict.stdout)
            self.assertEqual(state.read_bytes(), before_conflict)
            replay = run_record(observation, state)
            self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
            self.assertEqual(
                json.loads(state.read_text(encoding="utf-8")), observed_state
            )

            poisoned = copy.deepcopy(observation)
            poisoned["lease_transitions"] = [
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
                    "transition_receipt": "poison-future-zero-2",
                    "transitioned_at_utc": "2026-07-27T00:11:00Z",
                }
            ]
            before_poison = state.read_bytes()
            rejected_poison = run_record(poisoned, state)
            self.assertNotEqual(rejected_poison.returncode, 0)
            self.assertIn("not matched to a durable current-lease change", rejected_poison.stdout)
            self.assertEqual(state.read_bytes(), before_poison)

    def test_d07_future_dated_pro_events_have_no_watermark_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            future_live = base_record()
            future_live["pro_advisory_lane"]["live_jobs"][0][
                "submitted_at_utc"
            ] = "2099-01-01T00:00:00Z"
            live_state = root / "future-live-watermark.json"
            rejected_live = run_record(future_live, live_state)
            self.assertNotEqual(rejected_live.returncode, 0)
            self.assertIn("submitted_at_utc cannot be later", rejected_live.stdout)
            self.assertFalse(live_state.exists())

            future_response = response_ready_record()
            future_response["pro_advisory_lane"]["response_ready"][0][
                "completed_at_utc"
            ] = "2099-01-01T00:00:00Z"
            response_state = root / "future-response-watermark.json"
            rejected_response = run_record(future_response, response_state)
            self.assertNotEqual(rejected_response.returncode, 0)
            self.assertIn("completed_at_utc cannot be later", rejected_response.stdout)
            self.assertFalse(response_state.exists())

            observation_state = root / "future-observation-watermark.json"
            anchor = base_record()
            live = anchor["pro_advisory_lane"]["live_jobs"][0]
            live["owner_generation"] = 2
            live["job_generation"] = 2
            live["callback_event_key"] = "PRO-CALLBACK-PRO-1-G2"
            seeded = run_record(anchor, observation_state)
            self.assertEqual(seeded.returncode, 0, seeded.stdout + seeded.stderr)
            before_observation = observation_state.read_bytes()

            future_observation = copy.deepcopy(anchor)
            future_observation["pro_advisory_lane"]["callback_observations"] = [
                {
                    "observation_id": "OBS-STALE-FUTURE",
                    "job_id": "PRO-1",
                    "owner_thread_id": "controller",
                    "owner_generation": 1,
                    "job_generation": 1,
                    "callback_event_key": "PRO-CALLBACK-PRO-1-G1",
                    "disposition": "stale",
                    "effect_counts": {"adjudication": 0, "dispatch": 0, "ack": 0},
                    "observed_at_utc": "2099-01-01T00:00:00Z",
                }
            ]
            rejected_observation = run_record(future_observation, observation_state)
            self.assertNotEqual(rejected_observation.returncode, 0)
            self.assertIn("cannot be later than snapshot", rejected_observation.stdout)
            self.assertEqual(observation_state.read_bytes(), before_observation)

            future_closure = copy.deepcopy(anchor)
            future_closure["pro_advisory_lane"] = {
                "live_jobs": [],
                "queue": [],
                "response_ready": [],
                "callback_observations": [
                    {
                        "observation_id": "OBS-CLOSED-FUTURE",
                        "job_id": "PRO-1",
                        "owner_thread_id": "controller",
                        "owner_generation": 2,
                        "job_generation": 2,
                        "callback_event_key": "PRO-CALLBACK-PRO-1-G2",
                        "disposition": "closed",
                        "effect_counts": {
                            "adjudication": 0,
                            "dispatch": 0,
                            "ack": 0,
                        },
                        "closed_at_utc": "2099-01-01T00:00:00Z",
                        "observed_at_utc": "2026-07-27T00:09:00Z",
                    }
                ],
                "explicit_idle_reason": "registered generation closed",
            }
            rejected_closure = run_record(future_closure, observation_state)
            self.assertNotEqual(rejected_closure.returncode, 0)
            self.assertIn("closed_at_utc cannot be later", rejected_closure.stdout)
            self.assertEqual(observation_state.read_bytes(), before_observation)

    def test_d07_legacy_exact_replay_does_not_rewrite_watermark(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "watermark.json"
            record = base_record()
            seeded = run_record(record, state)
            self.assertEqual(seeded.returncode, 0, seeded.stdout + seeded.stderr)

            legacy = json.loads(state.read_text(encoding="utf-8"))
            legacy.pop("pro_owner_generations")
            legacy.pop("pro_job_generations")
            legacy.pop("pro_callback_event_keys")
            state.write_text(
                json.dumps(legacy, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            legacy_bytes = state.read_bytes()

            replay = run_record(record, state)
            self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
            self.assertEqual(state.read_bytes(), legacy_bytes)


if __name__ == "__main__":
    unittest.main()
