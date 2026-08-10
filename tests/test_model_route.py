from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validate_model_route import (
    LEGACY_ROUTE_DISPATCH_MARKER,
    ROUTE_DISPATCH_MARKER,
    RouteReceipt,
    _build_same_thread_prompt_bytes,
    build_named_child_prompt_bytes,
    build_same_thread_prompt,
    build_same_thread_prompt_bytes,
    load_rollout_receipt,
    validate_receipt,
    validate_same_thread_prompt,
    _has_exact_route_dispatch,
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
            "thread_id": "child-1",
            "turn_id": "turn-1",
            "first_turn_id": "turn-1",
            "route_dispatch_id": "luna-route-1",
            "capsule_bytes": 1,
            "capsule_sha256": "0" * 64,
        }
        values.update(overrides)
        return RouteReceipt(**values)  # type: ignore[arg-type]

    def write_rollout(self, root: Path, **overrides: object) -> Path:
        route_dispatch_id = str(overrides.pop("route_dispatch_id", "named-child-route-1"))
        capsule_path = root / "capsule.txt"
        capsule_path.write_bytes(b"capsule body\n")
        capsule_bytes = capsule_path.read_bytes()
        session = {
            "id": "child-1",
            "parent_thread_id": "parent-1",
            "agent_role": "luna_worker",
            "agent_nickname": "Popper",
            "multi_agent_version": "v1",
        }
        turn = {
            "model": "gpt-5.6-luna",
            "effort": "max",
            "turn_id": "turn-1",
            "first_turn_id": "turn-1",
            "context_eligible": True,
            "capsule_bytes": len(capsule_bytes),
            "capsule_sha256": hashlib.sha256(capsule_bytes).hexdigest(),
            "route_dispatch_id": route_dispatch_id,
        }
        for key, value in overrides.items():
            if key in turn:
                turn[key] = value
            else:
                session[key] = value
        path = root / "rollout.jsonl"
        canonical = build_named_child_prompt_bytes(
            route_dispatch_id,
            capsule_path,
        ).decode("utf-8")
        events = (
            {"type": "session_meta", "payload": session},
            {"type": "event_msg", "payload": {"type": "task_started"}},
            {"type": "turn_context", "payload": turn},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "internal_chat_message_metadata_passthrough": {"turn_id": "turn-1"},
                    "content": [{"type": "input_text", "text": canonical}],
                },
            },
        )
        path.write_text(
            "\n".join(json.dumps(event) for event in events) + "\n",
            encoding="utf-8",
        )
        return path

    def load_named_rollout_for_test(self, rollout: Path, capsule: Path) -> RouteReceipt:
        return load_rollout_receipt(
            rollout,
            action_class="frozen_deterministic",
            context_eligible=True,
            protected_exposed=False,
            decision_ambiguity=False,
            expected_parent_thread_id="parent-1",
            expected_thread_id="child-1",
            expected_turn_id="turn-1",
            expected_first_turn_id="turn-1",
            expected_route_dispatch_id="named-child-route-1",
            capsule_path=capsule,
        )

    def write_same_thread_rollout(
        self,
        root: Path,
        *,
        action_class: str = "bounded_engineering",
        thread_id: str = "executor-1",
        route_dispatch_id: str = "luna-route-1",
        duplicate_marker: bool = False,
        stale_marker: bool = False,
        marker_before_context: bool = False,
        omit_marker_turn_id: bool = False,
        model: str = "gpt-5.6-sol",
        effort: str = "high",
        name: str = "same-thread-rollout.jsonl",
        marker_text: str | None = None,
    ) -> Path:
        capsule_path = root / "capsule.txt"
        capsule_path.write_text("capsule body\n", encoding="utf-8")
        canonical = _build_same_thread_prompt_bytes(
            route_dispatch_id, capsule_path, action_class=action_class
        ).decode("utf-8")
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
                            else canonical
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

    def observed_codex_delegation_envelope(self, canonical_prompt: str) -> str:
        return (
            "<codex_delegation>\n"
            "  <source_thread_id>019fdcaf-75b6-7603-9519-31f49789ee29</source_thread_id>\n"
            f"  <input>{canonical_prompt}"
            "</input>\n"
            "</codex_delegation>"
        )

    def write_capsule(
        self, root: Path, name: str, content: str | bytes
    ) -> tuple[Path, bytes]:
        path = root / name
        capsule_bytes = content.encode("utf-8") if isinstance(content, str) else content
        path.write_bytes(capsule_bytes)
        return path, capsule_bytes

    def test_same_thread_prompt_builder_replays_p59_and_smi_capsules(self) -> None:
        capsules = (
            (
                "p59-r2-identity-conformance.txt",
                "P59 R2 identity conformance\nidentity=SCOUT_COMPLETE.identity\n",
            ),
            (
                "smi-attempt-003-full-carrier.txt",
                "SMI Attempt-003 full-carrier implementation\r\ncarrier=full\r\n",
            ),
        )
        route_dispatch_id = "DISPATCH-PR8-SAME-THREAD-20260810-001"
        marker = f"{ROUTE_DISPATCH_MARKER}{route_dispatch_id}\n".encode("utf-8")
        preamble = "PASS_MODEL_ROUTE: gpt-5.6-sol/high\nawait-successor-activation\n".encode()
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            for name, capsule in capsules:
                with self.subTest(name=name):
                    path, capsule_bytes = self.write_capsule(root, name, capsule)
                    built_bytes = build_same_thread_prompt_bytes(
                        route_dispatch_id, path, action_class="bounded_engineering"
                    )
                    self.assertEqual(built_bytes, marker + preamble + capsule_bytes)
                    self.assertEqual(
                        build_same_thread_prompt(
                            route_dispatch_id, path, action_class="bounded_engineering"
                        ),
                        (marker + preamble + capsule_bytes).decode("utf-8"),
                    )
                    validate_same_thread_prompt(
                        built_bytes, route_dispatch_id, action_class="bounded_engineering"
                    )
                    self.assertEqual(
                        built_bytes.count(ROUTE_DISPATCH_MARKER.encode("utf-8")), 1
                    )

    def test_same_thread_prompt_builder_replays_sol_and_luna_routes(self) -> None:
        routes = (
            ("bounded_engineering", "gpt-5.6-sol/high"),
            ("real_carrier", "gpt-5.6-sol/xhigh"),
            ("scientific_decision", "gpt-5.6-sol/max"),
        )
        route_dispatch_id = "DISPATCH-PR8-ROUTE-PREAMBLE-20260810-001"
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            path, capsule_bytes = self.write_capsule(root, "capsule.txt", "body\n")
            for action_class, route in routes:
                with self.subTest(action_class=action_class):
                    built = build_same_thread_prompt_bytes(
                        route_dispatch_id, path, action_class=action_class
                    )
                    expected = (
                        f"{ROUTE_DISPATCH_MARKER}{route_dispatch_id}\n"
                        f"PASS_MODEL_ROUTE: {route}\n"
                        "await-successor-activation\n"
                    ).encode("utf-8")
                    self.assertEqual(built, expected + capsule_bytes)
                    validate_same_thread_prompt(
                        built, route_dispatch_id, action_class=action_class
                    )
                    self.assertNotIn(LEGACY_ROUTE_DISPATCH_MARKER.encode(), built)

    def test_same_thread_prompt_validator_rejects_marker_shape_errors(self) -> None:
        route_dispatch_id = "luna-route-1"
        marker = f"{ROUTE_DISPATCH_MARKER}{route_dispatch_id}"
        cases = {
            "absent": "capsule body",
            "duplicate": f"{marker}\n{marker}\ncapsule body",
            "wrong id": f"{ROUTE_DISPATCH_MARKER}other-route\ncapsule body",
            "hidden": f"{marker}\ncapsule body hides {ROUTE_DISPATCH_MARKER}other-route",
            "not first": f"capsule body\n{marker}\n",
            "missing preamble": f"{marker}\ncapsule body",
            "wrong preamble": (
                f"{marker}\nPASS_MODEL_ROUTE: gpt-5.6-sol/xhigh\n"
                "await-successor-activation\ncapsule body"
            ),
            "legacy": f"{LEGACY_ROUTE_DISPATCH_MARKER}{route_dispatch_id}\n",
        }
        for name, prompt in cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_same_thread_prompt(
                    prompt, route_dispatch_id, action_class="bounded_engineering"
                )

    def test_public_same_thread_helpers_require_sol_action_class(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            capsule = Path(raw) / "capsule.txt"
            capsule.write_text("capsule body\n", encoding="utf-8")
            with self.assertRaises(TypeError):
                build_same_thread_prompt_bytes("route-1", capsule)  # type: ignore[call-arg]
            with self.assertRaises(TypeError):
                build_same_thread_prompt("route-1", capsule)  # type: ignore[call-arg]
            with self.assertRaises(TypeError):
                validate_same_thread_prompt("prompt", "route-1")  # type: ignore[call-arg]
            for helper in (
                build_same_thread_prompt_bytes,
                build_same_thread_prompt,
            ):
                with self.subTest(helper=helper.__name__), self.assertRaisesRegex(
                    ValueError, "same-thread prompt"
                ):
                    helper(
                        "route-1", capsule, action_class="frozen_deterministic"
                    )
            with self.assertRaisesRegex(ValueError, "same-thread prompt"):
                validate_same_thread_prompt(
                    "prompt", "route-1", action_class="frozen_deterministic"
                )

    def test_same_thread_prompt_builder_rejects_invalid_ids_and_capsules(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            path, _ = self.write_capsule(root, "capsule.txt", "capsule body\n")
            for route_dispatch_id in (
                "",
                " ",
                "bad/id",
                "bad\nid",
                "_bad-leading-token",
            ):
                with self.subTest(route_dispatch_id=route_dispatch_id), self.assertRaises(
                    ValueError
                ):
                    build_same_thread_prompt(
                        route_dispatch_id, path, action_class="bounded_engineering"
                    )

            for name, content in (
                ("marker-right.txt", "body LUNA_ROUTE_DISPATCH_ID=luna-route-1\n"),
                ("marker-wrong.txt", "LUNA_ROUTE_DISPATCH_ID=other-route\nbody\n"),
            ):
                marker_path, _ = self.write_capsule(root, name, content)
                with self.subTest(name=name), self.assertRaisesRegex(
                    ValueError, "route dispatch marker"
                ):
                    build_same_thread_prompt(
                        "luna-route-1", marker_path, action_class="bounded_engineering"
                    )

            directory = root / "capsule-directory"
            directory.mkdir()
            with self.assertRaisesRegex(ValueError, "regular"):
                build_same_thread_prompt(
                    "luna-route-1", directory, action_class="bounded_engineering"
                )

            symlink = root / "capsule-link"
            symlink.symlink_to(path)
            with self.assertRaisesRegex(ValueError, "regular"):
                build_same_thread_prompt(
                    "luna-route-1", symlink, action_class="bounded_engineering"
                )

            invalid_utf8, _ = self.write_capsule(root, "invalid-utf8", b"\xff\xfe")
            with self.assertRaisesRegex(ValueError, "UTF-8"):
                build_same_thread_prompt(
                    "luna-route-1", invalid_utf8, action_class="bounded_engineering"
                )

            unreadable, _ = self.write_capsule(root, "unreadable", b"body")
            unreadable.chmod(0)
            try:
                with self.assertRaisesRegex(ValueError, "readable"):
                    build_same_thread_prompt(
                        "luna-route-1", unreadable, action_class="bounded_engineering"
                    )
            finally:
                unreadable.chmod(0o600)

    def test_cli_builds_same_thread_prompt_to_stdout_verbatim(self) -> None:
        route_dispatch_id = "XAR-PR8-SAME-THREAD-20260810-001"
        capsule_bytes = "capsule\nwith\r\noriginal bytes\n".encode("utf-8")
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            path, _ = self.write_capsule(root, "capsule.txt", capsule_bytes)
            before = path.read_bytes()
            luna_result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--build-same-thread-prompt",
                    "--action-class",
                    "frozen_deterministic",
                    "--route-dispatch-id",
                    route_dispatch_id,
                    "--capsule-path",
                    str(path),
                ],
                capture_output=True,
                check=False,
            )
            self.assertEqual(luna_result.returncode, 1)
            self.assertIn("same-thread prompt", luna_result.stdout.decode())
            self.assertEqual(path.read_bytes(), before)
            sol_result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--build-same-thread-prompt",
                    "--action-class",
                    "bounded_engineering",
                    "--route-dispatch-id",
                    route_dispatch_id,
                    "--capsule-path",
                    str(path),
                ],
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                sol_result.returncode, 0, sol_result.stderr.decode()
            )
            self.assertTrue(
                sol_result.stdout.startswith(
                    (
                        f"{ROUTE_DISPATCH_MARKER}{route_dispatch_id}\n"
                        "PASS_MODEL_ROUTE: gpt-5.6-sol/high\n"
                        "await-successor-activation\n"
                    ).encode()
                )
            )
            self.assertEqual(sol_result.stderr, b"")
            self.assertEqual(path.read_bytes(), before)

    def test_cli_build_route_prompt_replays_exact_bytes_for_both_modes(self) -> None:
        route_dispatch_id = "XAR-PR9-CANONICAL-BUILD-20260810-001"
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            path, _ = self.write_capsule(root, "capsule.txt", b"child capsule\n")
            cases = (
                ("same_thread", "bounded_engineering"),
                ("named_child", "frozen_deterministic"),
            )
            for route_mode, action_class in cases:
                with self.subTest(route_mode=route_mode):
                    expected = (
                        _build_same_thread_prompt_bytes(
                            route_dispatch_id, path, action_class=action_class
                        )
                        if route_mode == "same_thread"
                        else build_named_child_prompt_bytes(
                            route_dispatch_id, path
                        )
                    )
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(VALIDATOR),
                            "--build-route-prompt",
                            "--route-mode",
                            route_mode,
                            "--action-class",
                            action_class,
                            "--route-dispatch-id",
                            route_dispatch_id,
                            "--capsule-path",
                            str(path),
                        ],
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertEqual(result.stdout, expected)
                    self.assertEqual(result.stderr, b"")
                    if route_mode == "named_child":
                        self.assertIn(
                            b"return-diff-and-validation-to-parent\n",
                            result.stdout,
                        )
                        self.assertNotIn(
                            b"await-successor-activation\n",
                            result.stdout,
                        )
            missing_action = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--build-route-prompt",
                    "--route-mode",
                    "named_child",
                    "--route-dispatch-id",
                    route_dispatch_id,
                    "--capsule-path",
                    str(path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(missing_action.returncode, 1)
            self.assertIn("action-class is required", missing_action.stdout)

    def test_frozen_deterministic_route_requires_luna_max(self) -> None:
        self.assertEqual(
            validate_receipt(
                self.luna_receipt(),
                expected_parent_thread_id="parent-1",
                expected_thread_id="child-1",
                expected_turn_id="turn-1",
                expected_first_turn_id="turn-1",
                expected_route_dispatch_id="luna-route-1",
            ),
            ("gpt-5.6-luna", "max"),
        )
        with self.assertRaisesRegex(ValueError, "runtime route mismatch"):
            validate_receipt(
                self.luna_receipt(model="gpt-5.6-sol", effort="xhigh"),
                expected_parent_thread_id="parent-1",
                expected_thread_id="child-1",
                expected_turn_id="turn-1",
                expected_first_turn_id="turn-1",
                expected_route_dispatch_id="luna-route-1",
            )

    def test_real_carrier_requires_sol_xhigh(self) -> None:
        self.assertEqual(
            validate_receipt(
                RouteReceipt(
                    "real_carrier",
                    "gpt-5.6-sol",
                    "xhigh",
                    receipt_source="durable_rollout",
                    route_mode="same_thread",
                    thread_id="thread-1",
                    turn_id="turn-1",
                    route_dispatch_id="dispatch-1",
                ),
                expected_thread_id="thread-1",
                expected_route_dispatch_id="dispatch-1",
            ),
            ("gpt-5.6-sol", "xhigh"),
        )
        with self.assertRaisesRegex(ValueError, "runtime route mismatch"):
            validate_receipt(
                RouteReceipt(
                    "real_carrier",
                    "gpt-5.6-luna",
                    "max",
                    receipt_source="durable_rollout",
                    route_mode="same_thread",
                    thread_id="thread-1",
                    turn_id="turn-1",
                    route_dispatch_id="dispatch-1",
                ),
                expected_thread_id="thread-1",
                expected_route_dispatch_id="dispatch-1",
            )

    def test_decision_ambiguity_never_silently_retiers_explicit_sol_class(self) -> None:
        self.assertEqual(
            validate_receipt(
                RouteReceipt(
                    "real_carrier",
                    "gpt-5.6-sol",
                    "xhigh",
                    decision_ambiguity=True,
                    receipt_source="durable_rollout",
                    route_mode="same_thread",
                    thread_id="thread-1",
                    turn_id="turn-1",
                    route_dispatch_id="dispatch-1",
                ),
                expected_thread_id="thread-1",
                expected_route_dispatch_id="dispatch-1",
            ),
            ("gpt-5.6-sol", "xhigh"),
        )
        with self.assertRaisesRegex(ValueError, "decision-ambiguous"):
            validate_receipt(
                self.luna_receipt(decision_ambiguity=True),
                expected_parent_thread_id="parent-1",
                expected_thread_id="child-1",
                expected_turn_id="turn-1",
                expected_first_turn_id="turn-1",
                expected_route_dispatch_id="luna-route-1",
            )

    def test_protected_exposure_and_unfrozen_context_reject_luna(self) -> None:
        for receipt in (
            self.luna_receipt(protected_exposed=True),
            self.luna_receipt(context_eligible=False),
        ):
            with self.subTest(receipt=receipt), self.assertRaises(ValueError):
                validate_receipt(
                    receipt,
                    expected_parent_thread_id="parent-1",
                    expected_thread_id="child-1",
                    expected_turn_id="turn-1",
                    expected_first_turn_id="turn-1",
                    expected_route_dispatch_id="luna-route-1",
                )

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
                validate_receipt(
                    receipt,
                    expected_parent_thread_id="parent-1",
                    expected_thread_id="child-1",
                    expected_turn_id="turn-1",
                    expected_first_turn_id="turn-1",
                    expected_route_dispatch_id="luna-route-1",
                )

    def test_named_child_requires_exact_expected_current_and_first_turns(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected current turn"):
            validate_receipt(
                self.luna_receipt(),
                expected_parent_thread_id="parent-1",
                expected_thread_id="child-1",
                expected_first_turn_id="turn-1",
                expected_route_dispatch_id="luna-route-1",
            )
        with self.assertRaisesRegex(ValueError, "expected first turn"):
            validate_receipt(
                self.luna_receipt(),
                expected_parent_thread_id="parent-1",
                expected_thread_id="child-1",
                expected_turn_id="turn-1",
                expected_route_dispatch_id="luna-route-1",
            )
        with self.assertRaisesRegex(ValueError, "turn binding"):
            validate_receipt(
                self.luna_receipt(),
                expected_parent_thread_id="parent-1",
                expected_thread_id="child-1",
                expected_turn_id="other-turn",
                expected_first_turn_id="turn-1",
                expected_route_dispatch_id="luna-route-1",
            )

    def test_luna_named_child_accepts_v2_with_same_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            for version in ("v1", "v2"):
                with self.subTest(version=version):
                    path = self.write_rollout(
                        Path(raw), multi_agent_version=version, name=f"{version}.jsonl"
                    )
                    receipt = load_rollout_receipt(
                        path,
                        action_class="frozen_deterministic",
                        context_eligible=True,
                        protected_exposed=False,
                        decision_ambiguity=False,
                        expected_parent_thread_id="parent-1",
                        expected_thread_id="child-1",
                        expected_turn_id="turn-1",
                        expected_first_turn_id="turn-1",
                        expected_route_dispatch_id="named-child-route-1",
                        capsule_path=Path(raw) / "capsule.txt",
                    )
                    self.assertEqual(receipt.multi_agent_version, version)
                    self.assertEqual(receipt.agent_role, "luna_worker")
                    self.assertEqual(receipt.model, "gpt-5.6-luna")
                    self.assertEqual(receipt.effort, "max")
                    self.assertEqual(
                        validate_receipt(
                            receipt,
                            expected_parent_thread_id="parent-1",
                            expected_thread_id="child-1",
                            expected_turn_id="turn-1",
                            expected_first_turn_id="turn-1",
                            expected_route_dispatch_id="named-child-route-1",
                        ),
                        ("gpt-5.6-luna", "max"),
                    )

    def test_named_child_binds_child_turn_and_capsule_and_rejects_history_or_truncation(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            capsule = root / "capsule.txt"
            capsule.write_bytes(b"capsule body\n")
            base = self.write_rollout(root, name="base.jsonl")
            with self.assertRaisesRegex(ValueError, "child binding"):
                load_rollout_receipt(
                    base,
                    action_class="frozen_deterministic",
                    context_eligible=True,
                    protected_exposed=False,
                    decision_ambiguity=False,
                    expected_parent_thread_id="parent-1",
                    expected_thread_id="wrong-child",
                    expected_turn_id="turn-1",
                    expected_first_turn_id="turn-1",
                    expected_route_dispatch_id="named-child-route-1",
                    capsule_path=capsule,
                )

            truncated = root / "truncated.jsonl"
            lines = base.read_text(encoding="utf-8").splitlines()
            response = json.loads(lines[-1])
            response["payload"]["content"][0]["text"] = response["payload"]["content"][0]["text"][:-1]
            lines[-1] = json.dumps(response)
            truncated.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
                self.load_named_rollout_for_test(truncated, capsule)

            history = root / "history.jsonl"
            history.write_text(
                base.read_text(encoding="utf-8")
                + json.dumps(
                    {
                        "type": "turn_context",
                        "payload": {
                            "model": "gpt-5.6-luna",
                            "effort": "max",
                            "turn_id": "old-turn",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "no-history"):
                self.load_named_rollout_for_test(history, capsule)

            successor_preamble = root / "successor-preamble.jsonl"
            successor_preamble.write_text(
                base.read_text(encoding="utf-8").replace(
                    "return-diff-and-validation-to-parent",
                    "await-successor-activation",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
                self.load_named_rollout_for_test(successor_preamble, capsule)

            missing_context = root / "missing-context-eligible.jsonl"
            context_lines = base.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(context_lines):
                event = json.loads(line)
                if event.get("type") == "turn_context":
                    event["payload"].pop("context_eligible")
                    context_lines[index] = json.dumps(event)
                    break
            missing_context.write_text(
                "\n".join(context_lines) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "durable context eligibility"):
                self.load_named_rollout_for_test(missing_context, capsule)

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
                    if message != "runtime route mismatch":
                        with self.assertRaisesRegex(ValueError, message):
                            load_rollout_receipt(
                                path,
                                action_class="frozen_deterministic",
                                context_eligible=True,
                                protected_exposed=False,
                                decision_ambiguity=False,
                                expected_parent_thread_id="parent-1",
                                expected_thread_id="child-1",
                                expected_turn_id="turn-1",
                                expected_first_turn_id="turn-1",
                                expected_route_dispatch_id="named-child-route-1",
                                capsule_path=root / "capsule.txt",
                            )
                    else:
                        receipt = load_rollout_receipt(
                            path,
                            action_class="frozen_deterministic",
                            context_eligible=True,
                            protected_exposed=False,
                            decision_ambiguity=False,
                            expected_parent_thread_id="parent-1",
                            expected_thread_id="child-1",
                            expected_turn_id="turn-1",
                            expected_first_turn_id="turn-1",
                            expected_route_dispatch_id="named-child-route-1",
                            capsule_path=root / "capsule.txt",
                        )
                        with self.assertRaisesRegex(ValueError, message):
                            validate_receipt(
                                receipt,
                                    expected_parent_thread_id="parent-1",
                                    expected_thread_id="child-1",
                                    expected_turn_id="turn-1",
                                    expected_first_turn_id="turn-1",
                                    expected_route_dispatch_id="named-child-route-1",
                            )

    def test_same_thread_luna_fails_before_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_same_thread_rollout(Path(raw))
            with self.assertRaisesRegex(ValueError, "before effects"):
                load_rollout_receipt(
                    path,
                    action_class="frozen_deterministic",
                    context_eligible=True,
                    protected_exposed=False,
                    decision_ambiguity=False,
                    route_mode="same_thread",
                    expected_route_dispatch_id="luna-route-1",
                    capsule_path=Path(raw) / "capsule.txt",
                )

    def test_same_thread_luna_marker_before_context_fails_before_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_same_thread_rollout(
                Path(raw), marker_before_context=True
            )
            with self.assertRaisesRegex(ValueError, "before effects"):
                load_rollout_receipt(
                    path,
                    action_class="frozen_deterministic",
                    context_eligible=True,
                    protected_exposed=False,
                    decision_ambiguity=False,
                    route_mode="same_thread",
                    expected_route_dispatch_id="luna-route-1",
                    capsule_path=Path(raw) / "capsule.txt",
                )

    def test_same_thread_sol_accepts_codex_delegation_envelope(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            route_dispatch_id = "XAR-PR3-LIVE-CANARY-20260809-001"
            capsule_path = root / "capsule.txt"
            capsule_path.write_text("capsule body\n", encoding="utf-8")
            path = self.write_same_thread_rollout(
                root,
                route_dispatch_id=route_dispatch_id,
                action_class="bounded_engineering",
                model="gpt-5.6-sol",
                effort="high",
                marker_text=self.observed_codex_delegation_envelope(
                    build_same_thread_prompt_bytes(
                        route_dispatch_id,
                        capsule_path,
                        action_class="bounded_engineering",
                    ).decode("utf-8")
                ),
            )
            receipt = load_rollout_receipt(
                path,
                action_class="bounded_engineering",
                context_eligible=False,
                protected_exposed=False,
                decision_ambiguity=False,
                route_mode="same_thread",
                expected_route_dispatch_id=route_dispatch_id,
                expected_source_thread_id="019fdcaf-75b6-7603-9519-31f49789ee29",
                capsule_path=capsule_path,
            )
            self.assertEqual(receipt.route_dispatch_id, route_dispatch_id)

    def test_same_thread_receipt_rebuilds_exact_capsule_and_envelope(self) -> None:
        route_dispatch_id = "strict-route-1"
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            capsule = root / "capsule.txt"
            capsule.write_bytes(b"capsule body\n")
            canonical = build_same_thread_prompt_bytes(
                route_dispatch_id, capsule, action_class="bounded_engineering"
            )
            envelope = self.observed_codex_delegation_envelope(canonical.decode())

            def assert_rejected(body: str, name: str) -> None:
                rollout = self.write_same_thread_rollout(
                    root,
                    route_dispatch_id=route_dispatch_id,
                    marker_text=body,
                    name=name,
                )
                with self.subTest(name=name), self.assertRaisesRegex(
                    ValueError, "missing or ambiguous"
                ):
                    load_rollout_receipt(
                        rollout,
                        action_class="bounded_engineering",
                        context_eligible=False,
                        protected_exposed=False,
                        decision_ambiguity=False,
                        route_mode="same_thread",
                        expected_route_dispatch_id=route_dispatch_id,
                        expected_source_thread_id="019fdcaf-75b6-7603-9519-31f49789ee29",
                        capsule_path=capsule,
                    )

            wrong_capsule = root / "wrong-capsule.txt"
            wrong_capsule.write_bytes(b"different body\n")
            wrong_capsule_prompt = build_same_thread_prompt_bytes(
                route_dispatch_id, wrong_capsule, action_class="bounded_engineering"
            ).decode()
            assert_rejected(wrong_capsule_prompt, "wrong-capsule.jsonl")
            assert_rejected(
                canonical[:-1].decode("utf-8"), "truncated-capsule.jsonl"
            )
            assert_rejected(
                canonical.decode().replace(
                    "PASS_MODEL_ROUTE: gpt-5.6-sol/high",
                    "PASS_MODEL_ROUTE: gpt-5.6-sol/xhigh",
                ),
                "wrong-preamble.jsonl",
            )
            assert_rejected(
                "prefix " + canonical.decode() + " suffix",
                "extra-prefix-suffix.jsonl",
            )
            assert_rejected(
                f"{ROUTE_DISPATCH_MARKER}{route_dispatch_id}",
                "marker-only.jsonl",
            )
            assert_rejected(
                f"{LEGACY_ROUTE_DISPATCH_MARKER}{route_dispatch_id}",
                "fresh-legacy.jsonl",
            )
            assert_rejected(envelope + envelope, "duplicate-envelope.jsonl")
            assert_rejected(
                envelope.replace(
                    "<source_thread_id>019fdcaf-75b6-7603-9519-31f49789ee29</source_thread_id>",
                    f"<source_thread_id>MODEL_ROUTE_DISPATCH_ID=extra</source_thread_id>",
                ),
                "envelope-extra-marker.jsonl",
            )
            assert_rejected(
                envelope.replace(
                    "<source_thread_id>019fdcaf-75b6-7603-9519-31f49789ee29</source_thread_id>",
                    f"<source_thread_id>{LEGACY_ROUTE_DISPATCH_MARKER}extra</source_thread_id>",
                ),
                "envelope-extra-legacy.jsonl",
            )
            assert_rejected(
                envelope.replace(
                    "<source_thread_id>",
                    "<instruction>ignored</instruction><source_thread_id>",
                ),
                "envelope-instruction.jsonl",
            )
            assert_rejected(
                envelope.replace(
                    "<source_thread_id>",
                    "<unknown>ignored</unknown><source_thread_id>",
                ),
                "envelope-unknown-tag.jsonl",
            )
            assert_rejected(
                envelope.replace("</input>", "</input><input>second</input>"),
                "envelope-second-input.jsonl",
            )
            assert_rejected(
                envelope.replace(
                    "019fdcaf-75b6-7603-9519-31f49789ee29", "wrong-source"
                ),
                "envelope-wrong-source.jsonl",
            )

    def test_historical_legacy_marker_never_authorizes_effect(self) -> None:
        route_dispatch_id = "legacy-audit-1"
        legacy = f"{LEGACY_ROUTE_DISPATCH_MARKER}{route_dispatch_id}"
        self.assertTrue(
            _has_exact_route_dispatch(
                legacy,
                route_dispatch_id,
                action_class="frozen_deterministic",
                allow_legacy_luna=True,
            )
        )
        self.assertFalse(
            _has_exact_route_dispatch(
                legacy,
                route_dispatch_id,
                action_class="frozen_deterministic",
            )
        )

    def test_named_child_receipt_accepts_capsule_path(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            rollout = self.write_rollout(root)
            capsule = root / "capsule.txt"
            self.assertEqual(
                load_rollout_receipt(
                    rollout,
                    action_class="frozen_deterministic",
                    context_eligible=True,
                    protected_exposed=False,
                    decision_ambiguity=False,
                    route_mode="named_child",
                    expected_parent_thread_id="parent-1",
                    expected_thread_id="child-1",
                    expected_turn_id="turn-1",
                    expected_first_turn_id="turn-1",
                    expected_route_dispatch_id="named-child-route-1",
                    capsule_path=capsule,
                ).route_dispatch_id,
                "named-child-route-1",
            )

    def test_same_thread_sol_accepts_generic_marker_and_rejects_legacy_marker(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            route_dispatch_id = "sol-route-1"
            generic = self.write_same_thread_rollout(
                root,
                action_class="bounded_engineering",
                route_dispatch_id=route_dispatch_id,
                model="gpt-5.6-sol",
                effort="high",
                name="generic.jsonl",
            )
            receipt = load_rollout_receipt(
                generic,
                action_class="bounded_engineering",
                context_eligible=False,
                protected_exposed=False,
                decision_ambiguity=False,
                route_mode="same_thread",
                expected_route_dispatch_id=route_dispatch_id,
                capsule_path=root / "capsule.txt",
            )
            self.assertEqual(
                validate_receipt(
                    receipt,
                    expected_thread_id="executor-1",
                    expected_route_dispatch_id=route_dispatch_id,
                ),
                ("gpt-5.6-sol", "high"),
            )
            legacy = self.write_same_thread_rollout(
                root,
                action_class="bounded_engineering",
                route_dispatch_id=route_dispatch_id,
                marker_text=f"{LEGACY_ROUTE_DISPATCH_MARKER}{route_dispatch_id}",
                model="gpt-5.6-sol",
                effort="high",
                name="legacy-sol.jsonl",
            )
            with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
                load_rollout_receipt(
                    legacy,
                    action_class="bounded_engineering",
                    context_eligible=False,
                    protected_exposed=False,
                    decision_ambiguity=False,
                    route_mode="same_thread",
                    expected_route_dispatch_id=route_dispatch_id,
                    capsule_path=root / "capsule.txt",
                )
            with self.assertRaisesRegex(ValueError, "before effects"):
                load_rollout_receipt(
                    legacy,
                    action_class="frozen_deterministic",
                    context_eligible=True,
                    protected_exposed=False,
                    decision_ambiguity=True,
                    route_mode="same_thread",
                    expected_route_dispatch_id=route_dispatch_id,
                    capsule_path=root / "capsule.txt",
                )

    def test_same_thread_sol_rejects_wrong_binding_or_model(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            route_dispatch_id = "sol-route-2"
            path = self.write_same_thread_rollout(
                root,
                action_class="real_carrier",
                route_dispatch_id=route_dispatch_id,
                model="gpt-5.6-sol",
                effort="xhigh",
                name="sol-xhigh.jsonl",
            )
            receipt = load_rollout_receipt(
                path,
                action_class="real_carrier",
                context_eligible=False,
                protected_exposed=False,
                decision_ambiguity=False,
                route_mode="same_thread",
                expected_route_dispatch_id=route_dispatch_id,
                capsule_path=root / "capsule.txt",
            )
            self.assertEqual(
                validate_receipt(
                    receipt,
                    expected_thread_id="executor-1",
                    expected_route_dispatch_id=route_dispatch_id,
                ),
                ("gpt-5.6-sol", "xhigh"),
            )
            with self.assertRaisesRegex(ValueError, "same-thread thread binding"):
                validate_receipt(
                    receipt,
                    expected_thread_id="executor-2",
                    expected_route_dispatch_id=route_dispatch_id,
                )
            with self.assertRaisesRegex(ValueError, "same-thread route dispatch"):
                validate_receipt(
                    receipt,
                    expected_thread_id="executor-1",
                    expected_route_dispatch_id="other-route",
                )
            with self.assertRaisesRegex(ValueError, "runtime route mismatch"):
                validate_receipt(
                    RouteReceipt(
                        action_class="real_carrier",
                        model="gpt-5.6-luna",
                        effort="max",
                        receipt_source="durable_rollout",
                        route_mode="same_thread",
                        thread_id="executor-1",
                        turn_id="turn-1",
                        route_dispatch_id=route_dispatch_id,
                    ),
                    expected_thread_id="executor-1",
                    expected_route_dispatch_id=route_dispatch_id,
                )

    def test_same_thread_scientific_decision_sol_max_accepts_canonical(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            dispatch_id = "scientific-route-1"
            path = self.write_same_thread_rollout(
                root,
                action_class="scientific_decision",
                route_dispatch_id=dispatch_id,
                model="gpt-5.6-sol",
                effort="max",
            )
            receipt = load_rollout_receipt(
                path,
                action_class="scientific_decision",
                context_eligible=False,
                protected_exposed=False,
                decision_ambiguity=False,
                route_mode="same_thread",
                expected_route_dispatch_id=dispatch_id,
                capsule_path=root / "capsule.txt",
            )
            self.assertEqual(
                validate_receipt(
                    receipt,
                    expected_thread_id="executor-1",
                    expected_route_dispatch_id=dispatch_id,
                ),
                ("gpt-5.6-sol", "max"),
            )

    def test_same_thread_luna_rejects_arbitrary_prose_prefix_before_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            path = self.write_same_thread_rollout(
                Path(raw),
                marker_text="Prompt: LUNA_ROUTE_DISPATCH_ID=luna-route-1",
            )
            with self.assertRaisesRegex(ValueError, "before effects"):
                load_rollout_receipt(
                    path,
                    action_class="frozen_deterministic",
                    context_eligible=True,
                    protected_exposed=False,
                    decision_ambiguity=False,
                    route_mode="same_thread",
                    expected_route_dispatch_id="luna-route-1",
                    capsule_path=Path(raw) / "capsule.txt",
                )

    def test_same_thread_luna_wrong_thread_and_dispatch_fail_before_effects(self) -> None:
        receipt = self.luna_receipt(route_mode="same_thread")
        with self.assertRaisesRegex(ValueError, "before effects"):
            validate_receipt(
                receipt,
                expected_thread_id="executor-2",
                expected_route_dispatch_id="luna-route-1",
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
                    ValueError, "before effects"
                ):
                    load_rollout_receipt(
                        path,
                        action_class="frozen_deterministic",
                        context_eligible=True,
                        protected_exposed=False,
                        decision_ambiguity=False,
                        route_mode="same_thread",
                        expected_route_dispatch_id=dispatch,
                        capsule_path=root / "capsule.txt",
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
                expected_parent_thread_id="parent-1",
                expected_thread_id="child-1",
                expected_turn_id="turn-1",
                expected_first_turn_id="turn-1",
                expected_route_dispatch_id="named-child-route-1",
                capsule_path=Path(raw) / "capsule.txt",
            )
            self.assertEqual(receipt.agent_role, "luna_worker")
            self.assertEqual(receipt.model, "gpt-5.6-luna")
            self.assertEqual(
                validate_receipt(
                    receipt,
                    expected_parent_thread_id="parent-1",
                    expected_thread_id="child-1",
                    expected_turn_id="turn-1",
                    expected_first_turn_id="turn-1",
                    expected_route_dispatch_id="named-child-route-1",
                ),
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
                    "--expected-thread-id",
                    "child-1",
                    "--expected-turn-id",
                    "turn-1",
                    "--expected-first-turn-id",
                    "turn-1",
                    "--expected-route-dispatch-id",
                    "named-child-route-1",
                    "--capsule-path",
                    str(Path(raw) / "capsule.txt"),
                    "--context-eligible",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS_MODEL_ROUTE: gpt-5.6-luna/max", result.stdout)
            self.assertIn("agent_role=luna_worker", result.stdout)

    def test_cli_rejects_same_thread_frozen_luna_before_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            path = self.write_same_thread_rollout(root)
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
                    "--capsule-path",
                    str(root / "capsule.txt"),
                    "--context-eligible",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("before effects", result.stdout)

    def test_cli_same_thread_rollout_requires_capsule(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as raw:
            root = Path(raw)
            path = self.write_same_thread_rollout(
                root,
                action_class="bounded_engineering",
                model="gpt-5.6-sol",
                effort="high",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--action-class",
                    "bounded_engineering",
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
            self.assertEqual(result.returncode, 1)
            self.assertIn("requires --capsule-path", result.stdout)


if __name__ == "__main__":
    unittest.main()
