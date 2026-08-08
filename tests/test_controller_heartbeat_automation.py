import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


AUTOMATION_ID = "fedft-controller-global-continuity"
CONTROLLER_THREAD_ID = "019f88d2-2512-75f0-a90d-c4b71e488607"
AUTOMATIONS_ROOT = Path(
    os.environ.get(
        "XAR_AUTOMATIONS_ROOT",
        Path(__file__).parent / "fixtures" / "automations",
    )
)
AUTOMATION = AUTOMATIONS_ROOT / AUTOMATION_ID / "automation.toml"
SKILL_ROOT = Path(
    os.environ.get("XAR_SKILL_ROOT", Path(__file__).resolve().parents[1])
)
STATE_TOOL_REFERENCES = (
    "${CODEX_HOME}/skills/xiaowen-autoresearch/scripts/"
    "controller_control_state.py",
    "/Users/xiaowen/.codex/skills/xiaowen-autoresearch/scripts/"
    "controller_control_state.py",
)
SCHEMA_V5_FIXTURE = {
    "schema_version": 5,
    "revision": 0,
    "updated_at": "2026-08-08T00:00:00Z",
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
            "candidate_state": "OPEN",
            "stage": "R2_SCOUT",
            "scientific_outcome": "UNOBSERVED",
            "lifecycle": "DELEGATED",
            "next_action": "WAIT_TERMINAL",
            "owner_thread_id": "worker-1",
            "owner_role": "Executor",
            "owner_state": "WAITING_EXTERNAL",
            "completion_binding": {
                "task_id": "task-1",
                "dispatch_id": "dispatch-1",
                "lease_epoch": 1,
                "contract_revision": "contract-1",
                "terminal_event_id": "TERM-HEARTBEAT-FIXTURE-1",
                "terminal_path": "/private/tmp/TERM-HEARTBEAT-FIXTURE-1.json",
            },
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
    "remote_jobs": [],
    "advisory_reads": [],
    "absorbed_advisory_scopes": [],
    "pending_absorptions": [],
    "absorbed_terminal_event_ids": [],
}


def load(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


class ControllerHeartbeatAutomationTest(unittest.TestCase):
    def test_frozen_singleton_fixture_uses_native_controller_recovery_contract(self) -> None:
        config = load(AUTOMATION)
        self.assertEqual(config["id"], AUTOMATION_ID)
        self.assertEqual(config["kind"], "heartbeat")
        self.assertEqual(config["status"], "ACTIVE")
        self.assertEqual(config["target_thread_id"], CONTROLLER_THREAD_ID)
        self.assertEqual(config["rrule"], "FREQ=MINUTELY;INTERVAL=30")

        prompt = config["prompt"]
        references = [item for item in STATE_TOOL_REFERENCES if item in prompt]
        self.assertEqual(len(references), 1)

        for phrase in (
            "schema_version=5",
            "每次 wake 都是该同一 Controller thread 的恢复事务",
            "terminal verify/absorb/route/dispatch/activation/close/finite-block/title/pin/state-CAS",
            "final 前必须 drain",
            "completion_binding",
            "pending_absorption",
            "observe-terminal",
            "verify-pending-terminal",
            "activate-successor",
            "close-objective",
            "absorb-and-block",
            "planned minimum revision",
            "await-successor-activation",
            "without an extra ACK",
            "30-minute cadence is recovery only",
            "Validate/deduplicate worker issue envelopes",
            "019fdcaf-75b6-7603-9519-31f49789ee29",
            "no signal means no message or resend",
            "workflow_evolution_gate.py in Shadow Mode",
            "25M/75M zero-output token bands",
            "every eighth absorbed terminal",
            "Never infer science from activity",
            "不得充当 Explorer/Audit/Executor",
            "不得创建 Goal、Pro sink、外部 watcher",
            "绝不删除或复制",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, prompt)

        for obsolete in (
            "你只负责 operational continuity fallback；不充当 Controller",
            "NOTIFY Controller 执行完整 absorption/route/owner 事务",
            "heartbeat 不能选择 successor",
            "不得创建 task/session/owner/automation",
            "controller_control_state_v5.py",
            "FREQ=MINUTELY;INTERVAL=15",
        ):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(obsolete, prompt)

    def test_configured_canonical_tool_executes_schema_v5_validate_and_show(self) -> None:
        config = load(AUTOMATION)
        prompt = config["prompt"]
        references = [item for item in STATE_TOOL_REFERENCES if item in prompt]
        self.assertEqual(len(references), 1)
        self.assertNotIn("controller_control_state_v5.py", prompt)

        tool = SKILL_ROOT / "scripts" / "controller_control_state.py"
        self.assertTrue(tool.is_file(), f"canonical state tool missing: {tool}")
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            state = Path(tmp) / "controller-state-v5.json"
            data = (
                json.dumps(
                    SCHEMA_V5_FIXTURE,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            state.write_bytes(data)
            state.with_name(state.name + ".sha256").write_text(
                f"{hashlib.sha256(data).hexdigest()}  {state.name}\n",
                encoding="utf-8",
            )
            validated = subprocess.run(
                [sys.executable, str(tool), "validate", "--state", str(state)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)
            self.assertEqual(json.loads(validated.stdout)["status"], "PASS")
            shown = subprocess.run(
                [sys.executable, str(tool), "show", "--state", str(state)],
                capture_output=True,
                check=False,
            )
            self.assertEqual(shown.returncode, 0, shown.stderr.decode("utf-8"))
            self.assertEqual(shown.stdout, data)

    def test_only_one_active_heartbeat_targets_the_controller(self) -> None:
        active = []
        for path in AUTOMATIONS_ROOT.glob("*/automation.toml"):
            config = load(path)
            if (
                config.get("kind") == "heartbeat"
                and config.get("status") == "ACTIVE"
                and config.get("target_thread_id") == CONTROLLER_THREAD_ID
            ):
                active.append(config.get("id"))
        self.assertEqual(active, [AUTOMATION_ID])


if __name__ == "__main__":
    unittest.main()
