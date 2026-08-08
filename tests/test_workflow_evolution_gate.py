from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.workflow_evolution_gate import (
    HARD_TOKEN_THRESHOLD,
    ISSUE_FIELDS,
    SOFT_TOKEN_THRESHOLD,
    classify_conformance,
    evaluate_events,
    model_route_scorecard,
    relative_soft_threshold,
    token_decision,
)


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "workflow_evolution_gate.py"
WORKSPACE = Path("/Users/xiaowen/Documents/Obsidian Vault/003_科研")


def decision(**overrides: object) -> dict:
    values: dict[str, object] = {
        "thread_id": "thread-1",
        "dispatch_id": "dispatch-1",
        "token_total": SOFT_TOKEN_THRESHOLD,
        "token_turns": 2,
        "decision_output_count": 0,
        "healthy_windows": [],
    }
    values.update(overrides)
    return token_decision(**values)  # type: ignore[arg-type]


def token_event(total: int) -> dict:
    return {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"last_token_usage": {"total_tokens": total}},
        },
    }


class TokenDetectorTest(unittest.TestCase):
    def test_soft_threshold_requires_two_token_bearing_turns(self) -> None:
        self.assertEqual(decision(token_turns=1)["trigger"], "NONE")
        self.assertEqual(decision(token_turns=2)["trigger"], "SOFT")
        self.assertEqual(
            decision(token_total=SOFT_TOKEN_THRESHOLD - 1, token_turns=9)["trigger"],
            "NONE",
        )

    def test_hard_threshold_triggers_even_on_one_turn(self) -> None:
        result = decision(token_total=HARD_TOKEN_THRESHOLD, token_turns=1)
        self.assertEqual(result["trigger"], "HARD")
        self.assertIsNotNone(result["fingerprint"])

    def test_valid_negative_or_null_decision_counts_as_output(self) -> None:
        result = decision(
            token_total=HARD_TOKEN_THRESHOLD * 2,
            token_turns=10,
            decision_output_count=1,
        )
        self.assertEqual(result["trigger"], "NONE")
        self.assertIsNone(result["fingerprint"])

    def test_relative_threshold_activates_only_after_eight_comparable_windows(self) -> None:
        self.assertIsNone(relative_soft_threshold([20_000_000] * 7))
        self.assertEqual(relative_soft_threshold([20_000_000] * 8), 40_000_000)
        result = decision(
            token_total=39_999_999,
            token_turns=4,
            healthy_windows=[20_000_000] * 8,
        )
        self.assertEqual(result["soft_threshold"], 40_000_000)
        self.assertEqual(result["trigger"], "NONE")

    def test_cli_scans_only_post_dispatch_token_events(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            rollout = root / "rollout.jsonl"
            events = [
                token_event(99_000_000),
                {"type": "response_item", "payload": {"dispatch_id": "dispatch-1"}},
                token_event(12_500_000),
                token_event(12_500_000),
            ]
            rollout.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            database = root / "state.sqlite"
            connection = sqlite3.connect(database)
            connection.execute(
                "CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, cwd TEXT)"
            )
            connection.execute(
                "INSERT INTO threads VALUES (?, ?, ?)",
                ("thread-1", str(rollout), str(WORKSPACE)),
            )
            connection.commit()
            connection.close()

            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "token-window",
                    "--state-db",
                    str(database),
                    "--workspace-root",
                    str(WORKSPACE),
                    "--thread-id",
                    "thread-1",
                    "--dispatch-id",
                    "dispatch-1",
                    "--decision-output-count",
                    "0",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["token_total"], SOFT_TOKEN_THRESHOLD)
            self.assertEqual(payload["token_turns"], 2)
            self.assertEqual(payload["trigger"], "SOFT")

    def test_cli_rejects_aris_and_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            database = root / "state.sqlite"
            connection = sqlite3.connect(database)
            connection.execute(
                "CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, cwd TEXT)"
            )
            connection.execute(
                "INSERT INTO threads VALUES (?, ?, ?)",
                ("outside-thread", str(root / "missing.jsonl"), "/outside"),
            )
            connection.commit()
            connection.close()
            base = [
                sys.executable,
                str(TOOL),
                "token-window",
                "--state-db",
                str(database),
                "--thread-id",
                "outside-thread",
                "--dispatch-id",
                "dispatch-1",
                "--decision-output-count",
                "0",
            ]
            result = subprocess.run(base, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("outside", json.loads(result.stdout)["error"])

            aris = list(base)
            aris[aris.index("outside-thread")] = "019fdaac-ce48-74d1-8fa0-94bab9ee2f3e"
            result = subprocess.run(aris, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("ARIS", json.loads(result.stdout)["error"])


class TraceAndConformanceDetectorTest(unittest.TestCase):
    def test_conformance_classes_are_mutually_decision_complete(self) -> None:
        cases = (
            ({"authority_conflict": True}, "AUTHORITY_CONFLICT"),
            ({"rule_applicable": None, "rule_feasible": True}, "NOT_ESTIMABLE"),
            (
                {
                    "rule_applicable": True,
                    "rule_feasible": True,
                    "shared_tooling_drift": True,
                },
                "RULE_TOOLING_DRIFT",
            ),
            (
                {
                    "rule_applicable": True,
                    "rule_feasible": True,
                    "independent_recurrence_count": 2,
                },
                "RULE_DESIGN_DEFECT",
            ),
            (
                {
                    "rule_applicable": True,
                    "rule_feasible": True,
                    "isolated_deviation": True,
                },
                "EXECUTION_NONCONFORMANCE",
            ),
        )
        for event, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_conformance(event), expected)

    def test_forward_trace_deduplicates_and_flags_recurrence_and_wakes(self) -> None:
        common = {
            "affected_stage": "PRE_UTILITY",
            "impact": "zero science",
            "evidence_pointer": "terminal-1",
            "failure_fingerprint": "wrapper-bug",
        }
        result = evaluate_events(
            [
                dict(common, kind="CREATE_NEW_ESCALATION"),
                dict(common, kind="PREUTILITY_FAILURE"),
                {"kind": "CONTROLLER_WAKE", "objective_id": "objective-1"},
                {"kind": "CONTROLLER_WAKE", "objective_id": "objective-1"},
                {
                    "detector": "RULE_CONFORMANCE",
                    "rule_applicable": True,
                    "rule_feasible": True,
                    "shared_tooling_drift": True,
                    "evidence_pointer": "route-receipt",
                },
            ]
        )
        facts = [issue["observed_fact"] for issue in result["issues"]]
        self.assertTrue(any(fact.startswith("REPEATED_FAILURE_FINGERPRINT") for fact in facts))
        self.assertTrue(any(fact.startswith("REPEATED_CONTROLLER_WAKE") for fact in facts))
        self.assertEqual(
            result["rule_conformance"][0]["classification"], "RULE_TOOLING_DRIFT"
        )
        for issue in result["issues"]:
            self.assertEqual(set(issue), set(ISSUE_FIELDS))
            self.assertEqual(issue["mode"], "SHADOW")


class ModelRouteScorecardTest(unittest.TestCase):
    def sample(self, route: str, **overrides: object) -> dict:
        values: dict[str, object] = {
            "kind": "MODEL_ROUTE_SAMPLE",
            "comparison_key": "frozen-mechanical-edit",
            "route": route,
            "total_tokens": 10_000 if route == "LUNA" else 20_000,
            "wall_time_ms": 1_000 if route == "LUNA" else 2_000,
            "first_pass_acceptance": True,
            "retry_count": 0,
            "decision_complete_output": True,
            "reliability_pass": True,
        }
        values.update(overrides)
        return values

    def test_route_smoke_without_comparable_sol_is_not_efficiency_proof(self) -> None:
        result = model_route_scorecard([self.sample("LUNA")])
        self.assertEqual(result[0]["disposition"], "NOT_ESTIMABLE")
        self.assertEqual(result[0]["sample_count"], {"LUNA": 1, "SOL": 0})

    def test_luna_is_retain_eligible_only_when_quality_and_cost_improve(self) -> None:
        result = model_route_scorecard([self.sample("LUNA"), self.sample("SOL")])
        self.assertEqual(result[0]["disposition"], "RETAIN_ELIGIBLE")
        self.assertTrue(result[0]["reliability_noninferior"])
        self.assertTrue(result[0]["quality_noninferior"])
        self.assertTrue(result[0]["cost_improved"])

    def test_reliability_or_acceptance_regression_requires_rollback(self) -> None:
        for override in (
            {"reliability_pass": False},
            {"first_pass_acceptance": False},
            {"decision_complete_output": False},
            {"retry_count": 1},
        ):
            with self.subTest(override=override):
                result = model_route_scorecard(
                    [self.sample("LUNA", **override), self.sample("SOL")]
                )
                self.assertEqual(result[0]["disposition"], "ROLLBACK_REQUIRED")

    def test_equal_or_higher_cost_is_no_change(self) -> None:
        result = model_route_scorecard(
            [
                self.sample("LUNA", total_tokens=20_000, wall_time_ms=2_000),
                self.sample("SOL"),
            ]
        )
        self.assertEqual(result[0]["disposition"], "NO_CHANGE")

    def test_scorecard_is_part_of_existing_event_evaluation(self) -> None:
        result = evaluate_events([self.sample("LUNA"), self.sample("SOL")])
        self.assertEqual(
            result["model_route_scorecard"][0]["disposition"], "RETAIN_ELIGIBLE"
        )


if __name__ == "__main__":
    unittest.main()
