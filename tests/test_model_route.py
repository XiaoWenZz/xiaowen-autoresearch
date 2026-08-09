from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validate_model_route import (
    RouteReceipt,
    load_rollout_receipt,
    validate_receipt,
)


ROOT = Path(__file__).parents[1]
VALIDATOR = ROOT / "scripts" / "validate_model_route.py"


class ModelRouteTest(unittest.TestCase):
    def luna_receipt(self, **overrides: object) -> RouteReceipt:
        values: dict[str, object] = {
            "action_class": "frozen_deterministic",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "context_eligible": True,
            "receipt_source": "durable_rollout",
            "agent_role": "luna_worker",
            "parent_thread_id": "parent-1",
            "multi_agent_version": "v1",
        }
        values.update(overrides)
        return RouteReceipt(**values)  # type: ignore[arg-type]

    def write_rollout(self, root: Path, **overrides: object) -> Path:
        session = {
            "id": "child-1",
            "parent_thread_id": "parent-1",
            "agent_role": "luna_worker",
            "agent_nickname": "Popper",
            "multi_agent_version": "v1",
        }
        turn = {"model": "gpt-5.6-luna", "effort": "max"}
        for key, value in overrides.items():
            if key in turn:
                turn[key] = value
            else:
                session[key] = value
        path = root / "rollout.jsonl"
        path.write_text(
            "\n".join(
                json.dumps(event)
                for event in (
                    {"type": "session_meta", "payload": session},
                    {"type": "event_msg", "payload": {"type": "task_started"}},
                    {"type": "turn_context", "payload": turn},
                )
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def write_same_thread_rollout(
        self,
        root: Path,
        *,
        thread_id: str = "executor-1",
        route_dispatch_id: str = "luna-route-1",
        duplicate_marker: bool = False,
        stale_marker: bool = False,
        marker_before_context: bool = False,
        omit_marker_turn_id: bool = False,
        model: str = "gpt-5.6-luna",
        effort: str = "max",
        name: str = "same-thread-rollout.jsonl",
        marker_text: str | None = None,
    ) -> Path:
        marker = {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "internal_chat_message_metadata_passthrough": (
                    {} if omit_marker_turn_id else {
                        "turn_id": "old-turn" if stale_marker else "turn-1"
                    }
                ),
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            marker_text
                            if marker_text is not None
                            else f"LUNA_ROUTE_DISPATCH_ID={route_dispatch_id}"
                        ),
                    }
                ],
            },
        }
        events = [
            {"type": "session_meta", "payload": {"id": thread_id}},
        ]
        if stale_marker or marker_before_context:
            events.append(marker)
        events.append(
            {
                "type": "turn_context",
                "payload": {
                    "model": model,
                    "effort": effort,
                    "multi_agent_version": "v2",
                    "turn_id": "turn-1",
                },
            }
        )
        if not stale_marker and not marker_before_context:
            events.append(marker)
            if duplicate_marker:
                events.append(marker)
        path = root / name
        path.write_text(
            "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
        )
        return path

    def observed_codex_delegation_envelope(self, route_dispatch_id: str) -> str:
        return (
            "<codex_delegation>\n"
            "  <source_thread_id>019fdcaf-75b6-7603-9519-31f49789ee29</source_thread_id>\n"
            f"  <input>LUNA_ROUTE_DISPATCH_ID={route_dispatch_id}\n"
            "ACTION_CLASS=frozen_deterministic\n"
            "MODE=Lite same-thread route canary\n"
            "</input>\n"
            "</codex_delegation>"
        )

    def test_frozen_deterministic_route_requires_luna_max(self) -> None:
        self.assertEqual(
            validate_receipt(
                self.luna_receipt(), expected_parent_thread_id="parent-1"
            ),
            ("gpt-5.6-luna", "max"),
        )
        with self.assertRaisesRegex(ValueError, "runtime route mismatch"):
            validate_receipt(
                self.luna_receipt(model="gpt-5.6-sol", effort="xhigh"),
                expected_parent_thread_id="parent-1",
            )

    def test_real_carrier_requires_sol_xhigh(self) -> None:
        self.assertEqual(
            validate_receipt(RouteReceipt("real_carrier", "gpt-5.6-sol", "xhigh")),
            ("gpt-5.6-sol", "xhigh"),
        )
        with self.assertRaisesRegex(ValueError, "runtime route mismatch"):
            validate_receipt(RouteReceipt("real_carrier", "gpt-5.6-luna", "max"))

    def test_decision_ambiguity_forces_sol_max(self) -> None:
        self.assertEqual(
            validate_receipt(
                RouteReceipt(
                    "bounded_engineering",
                    "gpt-5.6-sol",
                    "max",
                    decision_ambiguity=True,
                )
            ),
            ("gpt-5.6-sol", "max"),
        )

    def test_protected_exposure_and_unfrozen_context_reject_luna(self) -> None:
        for receipt in (
            self.luna_receipt(protected_exposed=True),
            self.luna_receipt(context_eligible=False),
        ):
            with self.subTest(receipt=receipt), self.assertRaises(ValueError):
                validate_receipt(receipt, expected_parent_thread_id="parent-1")

    def test_luna_requires_named_durable_role_parent_and_supported_version(self) -> None:
        cases = (
            (self.luna_receipt(receipt_source="direct"), "durable rollout"),
            (self.luna_receipt(agent_role="default"), "agent_role=luna_worker"),
            (
                self.luna_receipt(multi_agent_version="v3"),
                "multi_agent_version=v1 or v2",
            ),
            (self.luna_receipt(parent_thread_id="other"), "parent binding mismatch"),
        )
        for receipt, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                validate_receipt(receipt, expected_parent_thread_id="parent-1")

    def test_luna_named_child_accepts_v2_with_same_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_rollout(Path(raw), multi_agent_version="v2")
            receipt = load_rollout_receipt(
                path,
                action_class="frozen_deterministic",
                context_eligible=True,
                protected_exposed=False,
                decision_ambiguity=False,
            )
            self.assertEqual(receipt.multi_agent_version, "v2")
            self.assertEqual(receipt.agent_role, "luna_worker")
            self.assertEqual(receipt.model, "gpt-5.6-luna")
            self.assertEqual(receipt.effort, "max")
            self.assertEqual(
                validate_receipt(receipt, expected_parent_thread_id="parent-1"),
                ("gpt-5.6-luna", "max"),
            )

    def test_luna_v2_named_child_rejects_wrong_role_model_and_parent(self) -> None:
        cases = (
            ({"agent_role": "default"}, "agent_role=luna_worker"),
            ({"model": "gpt-5.6-sol"}, "runtime route mismatch"),
            ({"parent_thread_id": "other"}, "parent binding mismatch"),
        )
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            for overrides, message in cases:
                with self.subTest(message=message):
                    path = self.write_rollout(
                        root, multi_agent_version="v2", **overrides
                    )
                    receipt = load_rollout_receipt(
                        path,
                        action_class="frozen_deterministic",
                        context_eligible=True,
                        protected_exposed=False,
                        decision_ambiguity=False,
                    )
                    with self.assertRaisesRegex(ValueError, message):
                        validate_receipt(
                            receipt, expected_parent_thread_id="parent-1"
                        )

    def test_same_thread_luna_binds_current_thread_and_exact_dispatch(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_same_thread_rollout(Path(raw))
            receipt = load_rollout_receipt(
                path,
                action_class="frozen_deterministic",
                context_eligible=True,
                protected_exposed=False,
                decision_ambiguity=False,
                route_mode="same_thread",
                expected_route_dispatch_id="luna-route-1",
            )
            self.assertEqual(
                validate_receipt(
                    receipt,
                    expected_thread_id="executor-1",
                    expected_route_dispatch_id="luna-route-1",
                ),
                ("gpt-5.6-luna", "max"),
            )
            self.assertEqual(receipt.thread_id, "executor-1")
            self.assertEqual(receipt.turn_id, "turn-1")
            self.assertIsNone(receipt.agent_role)

    def test_same_thread_luna_accepts_marker_before_context_in_same_turn(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_same_thread_rollout(
                Path(raw), marker_before_context=True
            )
            receipt = load_rollout_receipt(
                path,
                action_class="frozen_deterministic",
                context_eligible=True,
                protected_exposed=False,
                decision_ambiguity=False,
                route_mode="same_thread",
                expected_route_dispatch_id="luna-route-1",
            )
            self.assertEqual(receipt.turn_id, "turn-1")

    def test_same_thread_luna_accepts_codex_delegation_envelope(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            route_dispatch_id = "XAR-PR3-LIVE-CANARY-20260809-001"
            path = self.write_same_thread_rollout(
                Path(raw),
                route_dispatch_id=route_dispatch_id,
                marker_text=self.observed_codex_delegation_envelope(route_dispatch_id),
            )
            receipt = load_rollout_receipt(
                path,
                action_class="frozen_deterministic",
                context_eligible=True,
                protected_exposed=False,
                decision_ambiguity=False,
                route_mode="same_thread",
                expected_route_dispatch_id=route_dispatch_id,
            )
            self.assertEqual(receipt.route_dispatch_id, route_dispatch_id)

    def test_same_thread_luna_rejects_arbitrary_prose_prefix(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_same_thread_rollout(
                Path(raw),
                marker_text="Prompt: LUNA_ROUTE_DISPATCH_ID=luna-route-1",
            )
            with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
                load_rollout_receipt(
                    path,
                    action_class="frozen_deterministic",
                    context_eligible=True,
                    protected_exposed=False,
                    decision_ambiguity=False,
                    route_mode="same_thread",
                    expected_route_dispatch_id="luna-route-1",
                )

    def test_same_thread_luna_rejects_wrong_thread_and_dispatch(self) -> None:
        receipt = self.luna_receipt(
            route_mode="same_thread",
            agent_role=None,
            parent_thread_id=None,
            multi_agent_version="v2",
            thread_id="executor-1",
            turn_id="turn-1",
            route_dispatch_id="luna-route-1",
        )
        with self.assertRaisesRegex(ValueError, "thread binding mismatch"):
            validate_receipt(
                receipt,
                expected_thread_id="executor-2",
                expected_route_dispatch_id="luna-route-1",
            )
        with self.assertRaisesRegex(ValueError, "route dispatch mismatch"):
            validate_receipt(
                receipt,
                expected_thread_id="executor-1",
                expected_route_dispatch_id="luna-route-2",
            )

    def test_same_thread_luna_rejects_stale_or_duplicate_marker(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            for path, dispatch in (
                (
                    self.write_same_thread_rollout(
                        root, stale_marker=True, name="stale.jsonl"
                    ),
                    "luna-route-1",
                ),
                (
                    self.write_same_thread_rollout(
                        root,
                        route_dispatch_id="luna-route-2",
                        duplicate_marker=True,
                        name="duplicate.jsonl",
                    ),
                    "luna-route-2",
                ),
                (
                    self.write_same_thread_rollout(
                        root,
                        route_dispatch_id="luna-route-3",
                        omit_marker_turn_id=True,
                        name="missing-turn-id.jsonl",
                    ),
                    "luna-route-3",
                ),
            ):
                with self.subTest(path=path), self.assertRaisesRegex(
                    ValueError, "missing or ambiguous"
                ):
                    load_rollout_receipt(
                        path,
                        action_class="frozen_deterministic",
                        context_eligible=True,
                        protected_exposed=False,
                        decision_ambiguity=False,
                        route_mode="same_thread",
                        expected_route_dispatch_id=dispatch,
                    )

    def test_load_rollout_receipt_uses_metadata_not_worker_prose(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_rollout(Path(raw))
            with path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "type": "response_item",
                            "payload": {
                                "text": "agent_role=other model=gpt-5.6-sol effort=low"
                            },
                        }
                    )
                    + "\n"
                )
            receipt = load_rollout_receipt(
                path,
                action_class="frozen_deterministic",
                context_eligible=True,
                protected_exposed=False,
                decision_ambiguity=False,
            )
            self.assertEqual(receipt.agent_role, "luna_worker")
            self.assertEqual(receipt.model, "gpt-5.6-luna")
            self.assertEqual(
                validate_receipt(receipt, expected_parent_thread_id="parent-1"),
                ("gpt-5.6-luna", "max"),
            )

    def test_cli_is_read_only_and_fails_closed_on_wrong_receipt(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--action-class",
                "frozen_deterministic",
                "--model",
                "gpt-5.6-sol",
                "--effort",
                "xhigh",
                "--context-eligible",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL_MODEL_ROUTE", result.stdout)

    def test_cli_accepts_exact_named_luna_rollout(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_rollout(Path(raw))
            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--action-class",
                    "frozen_deterministic",
                    "--rollout-path",
                    str(path),
                    "--expected-parent-thread-id",
                    "parent-1",
                    "--context-eligible",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS_MODEL_ROUTE: gpt-5.6-luna/max", result.stdout)
            self.assertIn("agent_role=luna_worker", result.stdout)

    def test_cli_accepts_exact_same_thread_luna_rollout(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_same_thread_rollout(Path(raw))
            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--action-class",
                    "frozen_deterministic",
                    "--rollout-path",
                    str(path),
                    "--route-mode",
                    "same_thread",
                    "--expected-thread-id",
                    "executor-1",
                    "--expected-route-dispatch-id",
                    "luna-route-1",
                    "--context-eligible",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS_MODEL_ROUTE: gpt-5.6-luna/max", result.stdout)
            self.assertIn("route_mode=same_thread", result.stdout)


if __name__ == "__main__":
    unittest.main()
