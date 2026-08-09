from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.workflow_evolution_gate import (
    CONTEXT_MEDIAN_ROLLOVER,
    CONTEXT_WINDOW_SIZE,
    GateError,
    HARD_TOKEN_THRESHOLD,
    ISSUE_FIELDS,
    SOFT_TOKEN_THRESHOLD,
    classify_conformance,
    controller_context_decision,
    evaluate_events,
    model_route_scorecard,
    relative_soft_threshold,
    scan_controller_context_window,
    token_decision,
    validate_rule_chain_terminal,
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


def dispatch_event(dispatch_id: str = "dispatch-1") -> dict:
    return {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "PASS_MODEL_ROUTE: gpt-5.6-sol/high\n"
                        "python3 controller_control_state.py "
                        "await-successor-activation\n"
                        f"dispatch_id={dispatch_id}"
                    ),
                }
            ],
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
                dispatch_event(),
                {"type": "event_msg", "payload": {"dispatch_id": "dispatch-1"}},
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": "dispatch-1 echoed"}
                        ],
                    },
                },
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

    def test_cli_rejects_two_canonical_dispatch_markers(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            rollout = root / "rollout.jsonl"
            rollout.write_text(
                "".join(
                    json.dumps(event) + "\n"
                    for event in (dispatch_event(), token_event(1), dispatch_event())
                ),
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
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing or ambiguous", json.loads(result.stdout)["error"])

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


class ControllerContextWindowTest(unittest.TestCase):
    @staticmethod
    def session_event(thread_id: str = "thread-1") -> dict:
        return {"type": "session_meta", "payload": {"id": thread_id}}

    @staticmethod
    def token_event(value: object) -> dict:
        return {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"last_token_usage": {"input_tokens": value}},
            },
        }

    def test_precedence_and_diagnostic_p95(self) -> None:
        pause = controller_context_decision(
            [195_396] * CONTEXT_WINDOW_SIZE,
            thread_id="thread-1",
            session_id="thread-1",
            epoch_marker_line=None,
        )
        self.assertEqual(pause["decision"], "PAUSE_NEW_OBJECTIVE_ADMISSION")
        self.assertEqual(pause["count"], 20)
        self.assertEqual(pause["median"], 195_396)
        self.assertEqual(pause["p95"], 195_396)
        self.assertEqual(pause["tail_consecutive_over_128000"], 20)

        rollover = controller_context_decision(
            [100_000] * CONTEXT_WINDOW_SIZE,
            thread_id="thread-1",
            session_id="thread-1",
            epoch_marker_line=None,
        )
        self.assertEqual(rollover["decision"], "REQUIRE_ROLLOVER")
        self.assertEqual(rollover["median"], 100_000)
        self.assertGreater(rollover["median"], CONTEXT_MEDIAN_ROLLOVER)

        p95_only = controller_context_decision(
            [64_000] * 18 + [120_000] * 2,
            thread_id="thread-1",
            session_id="thread-1",
            epoch_marker_line=None,
        )
        self.assertEqual(p95_only["decision"], "ALLOW")
        self.assertEqual(p95_only["median"], 64_000)
        self.assertEqual(p95_only["p95"], 120_000)

    def test_scan_resets_after_latest_compaction_and_caps_at_latest_twenty(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            rollout = Path(raw) / "rollout.jsonl"
            events = [
                self.session_event(),
                self.token_event(195_396),
                {"type": "compacted", "payload": {}},
                {"type": "event_msg", "payload": {"type": "context_compacted"}},
                *[self.token_event(64_000) for _ in range(21)],
            ]
            rollout.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            session_id, marker_line, values = scan_controller_context_window(
                rollout, "thread-1"
            )
            self.assertEqual(session_id, "thread-1")
            self.assertEqual(marker_line, 4)
            self.assertEqual(values, [64_000] * CONTEXT_WINDOW_SIZE)

    def test_cli_emits_executed_decision_and_rejects_parser_identity_errors(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            rollout = root / "rollout.jsonl"
            rollout.write_text(
                "".join(
                    json.dumps(event) + "\n"
                    for event in [
                        self.session_event(),
                        *[self.token_event(195_396) for _ in range(20)],
                    ]
                ),
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

            command = [
                sys.executable,
                str(TOOL),
                "controller-context-window",
                "--state-db",
                str(database),
                "--workspace-root",
                str(WORKSPACE),
                "--thread-id",
                "thread-1",
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["decision"], "PAUSE_NEW_OBJECTIVE_ADMISSION")

            rollout.write_text(
                json.dumps(self.session_event("other-thread")) + "\n", encoding="utf-8"
            )
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "FAIL")
            self.assertIn("requested thread", payload["error"])


class RuleChainPresealTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.skill = self.root / "skill"
        (self.workspace / "project").mkdir(parents=True)
        (self.skill / "references").mkdir(parents=True)
        self.workspace_agents = self.workspace / "AGENTS.md"
        self.project_agents = self.workspace / "project" / "AGENTS.md"
        self.skill_file = self.skill / "SKILL.md"
        self.orchestration = self.skill / "references" / "orchestration.md"
        self.state_schema = self.skill / "references" / "state-schema.md"
        for path, value in (
            (self.workspace_agents, "workspace\n"),
            (self.project_agents, "project\n"),
            (self.skill_file, "skill\n"),
            (self.orchestration, "orchestration\n"),
            (self.state_schema, "state-schema\n"),
        ):
            path.write_text(value, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def terminal(self, rule_chain: object, *, name: str = "terminal.json") -> Path:
        path = self.root / name
        path.write_text(json.dumps({"rule_chain": rule_chain}) + "\n", encoding="utf-8")
        return path

    def validate(self, terminal: Path) -> dict:
        return validate_rule_chain_terminal(
            terminal,
            workspace_root=self.workspace,
            skill_root=self.skill,
        )

    def test_files_read_completely_projection_passes(self) -> None:
        terminal = self.terminal(
            {
                "files_read_completely": [
                    {
                        "path": str(self.workspace_agents),
                        "sha256": self.digest(self.workspace_agents),
                    },
                    {
                        "path": str(self.project_agents),
                        "sha256": self.digest(self.project_agents),
                    },
                    {
                        "path": str(self.skill_file),
                        "sha256": self.digest(self.skill_file),
                    },
                ]
            }
        )
        result = self.validate(terminal)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["checked"], 3)
        self.assertEqual(result["mismatches"], [])

    def test_named_objects_and_routed_references_pass(self) -> None:
        terminal = self.terminal(
            {
                "root_AGENTS": {
                    "path": str(self.workspace_agents),
                    "sha256": self.digest(self.workspace_agents),
                },
                "live_skill": {
                    "path": str(self.skill_file),
                    "sha256": self.digest(self.skill_file),
                },
                "routed_references": {
                    "orchestration.md": self.digest(self.orchestration),
                    "state-schema.md": self.digest(self.state_schema),
                },
            }
        )
        result = self.validate(terminal)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["checked"], 4)

    def test_cli_reports_mismatch_and_exits_two(self) -> None:
        terminal = self.terminal(
            {
                "live_skill": {
                    "path": str(self.skill_file),
                    "sha256": "0" * 64,
                }
            }
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "validate-rule-chain",
                "--terminal-json",
                str(terminal),
                "--workspace-root",
                str(self.workspace),
                "--skill-root",
                str(self.skill),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["mismatches"][0]["reported_sha256"], "0" * 64)
        self.assertEqual(
            result["mismatches"][0]["observed_sha256"], self.digest(self.skill_file)
        )

    def test_rejects_symlink_outside_root_duplicate_and_traversal(self) -> None:
        outside = self.root / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        symlink = self.skill / "linked.md"
        symlink.symlink_to(self.skill_file)
        cases = (
            {
                "linked": {"path": str(symlink), "sha256": self.digest(self.skill_file)}
            },
            {"outside": {"path": str(outside), "sha256": self.digest(outside)}},
            {"routed_references": {"../outside.md": self.digest(outside)}},
        )
        for index, rule_chain in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(GateError):
                    self.validate(self.terminal(rule_chain, name=f"unsafe-{index}.json"))

        duplicate = self.root / "duplicate.json"
        duplicate.write_text('{"rule_chain":{},"rule_chain":{}}\n', encoding="utf-8")
        with self.assertRaisesRegex(GateError, "duplicate JSON key"):
            self.validate(duplicate)

    def test_rejects_empty_malformed_and_duplicate_file_assertions(self) -> None:
        cases = (
            {},
            {"skill": {"path": str(self.skill_file), "sha256": "ABC"}},
            {
                "files_read_completely": [
                    {"path": str(self.skill_file), "sha256": self.digest(self.skill_file)},
                    {"path": str(self.skill_file), "sha256": self.digest(self.skill_file)},
                ]
            },
        )
        for index, rule_chain in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(GateError):
                    self.validate(self.terminal(rule_chain, name=f"invalid-{index}.json"))


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
