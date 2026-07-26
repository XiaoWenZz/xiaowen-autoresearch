from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "reconcile_research_lanes.py"


def run_record(record: dict[str, object]) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "lanes.json"
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            text=True,
            capture_output=True,
            check=False,
        )


def base_record() -> dict[str, object]:
    return {
        "controller_thread_id": "controller",
        "gpu_running": {"task_id": "GPU-1", "owner_thread_id": "gpu-owner"},
        "gpu_queue": [
            {
                "task_id": "GPU-2",
                "owner_thread_id": "gpu-owner-2",
                "launch_prerequisite": "GPU-1 terminal",
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
            "task_id": "ZERO-1",
            "owner_thread_id": "zero-owner",
            "kind": "opportunity_search",
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
            "live_jobs": [{"job_id": "PRO-1"}],
            "queue": [],
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
            "task_id": "ANALYZE-GPU-1",
            "owner_thread_id": "analysis-owner",
            "kind": "result_analysis",
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
            "portfolio_reconciled": False,
            "watchdog_state": "paused",
            "next_action": {"kind": "dispatch_next", "task_id": "ZERO-1"},
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
            "explicit_idle_reason": None,
        }
        result = run_record(record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be submitted", result.stdout)

        record["pro_advisory_lane"]["cooldown_held"] = True
        result = run_record(record)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
