import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path, PurePosixPath
from unittest import mock

import scripts.controller_control_state as controller_state

from scripts.controller_control_state import (
    StateError,
    build_parser,
    canonical_bytes,
    checksum_path,
    cmd_activate_successor,
    cmd_advance_cursors,
    cmd_migrate_v4_native_heartbeat,
    cmd_observe_terminal,
    cmd_prepare_terminal_callback,
    cmd_rebuild_add_objective,
    cmd_derive_startup_chain_id,
    cmd_verify_pending_terminal,
    completion_binding_sha256,
    derive_startup_chain_id,
    read_state,
    validate_state,
    write_state,
)


def args(**values: object) -> object:
    return type("Args", (), values)()


def binding(terminal: Path, suffix: str = "1") -> dict:
    return {
        "task_id": f"task-{suffix}",
        "dispatch_id": f"dispatch-{suffix}",
        "lease_epoch": 1,
        "contract_revision": f"contract-{suffix}",
        "terminal_event_id": f"TERM-{suffix}",
        "terminal_path": str(terminal),
    }


def base_state(terminal: Path) -> dict:
    return {
        "schema_version": 5,
        "revision": 0,
        "updated_at": "2026-08-06T00:00:00Z",
        "controller": {
            "thread_id": "controller-1",
            "project_id": "project-1",
            "cwd": "/workspace",
            "title": "Controller · Research · ACTIVE",
            "pin_required": True,
        },
        "objectives": [
            {
                "objective_id": "objective-1",
                "candidate_id": "candidate-1",
                "candidate_state": "OPEN",
                "stage": "R2",
                "scientific_outcome": "UNOBSERVED",
                "lifecycle": "DELEGATED",
                "next_action": "WAIT_TERMINAL",
                "owner_thread_id": "worker-1",
                "owner_role": "Audit",
                "owner_state": "ACTIVE",
                "completion_binding": binding(terminal),
            }
        ],
        "managed_roles": [
            {
                "thread_id": "worker-1",
                "role": "Audit",
                "title": "Audit · Candidate One · ACTIVE",
                "state": "ACTIVE",
                "pin_required": True,
                "cursor": "cursor:before",
            }
        ],
        "remote_jobs": [],
        "advisory_reads": [],
        "absorbed_advisory_scopes": [],
        "pending_absorptions": [],
        "absorbed_terminal_event_ids": [],
    }


def frozen_terminal(
    directory: Path,
    name: str = "terminal.json",
    *,
    suffix: str = "1",
    body: str | None = None,
) -> Path:
    path = directory / name
    if body is None:
        path.write_bytes(canonical_bytes({"completion_binding": binding(path, suffix)}))
    else:
        path.write_text(body, encoding="utf-8")
    path.chmod(0o444)
    return path


def sealed_startup_authority(directory: Path) -> dict:
    scientific_projection = {
        key: f"frozen-{key}"
        for key in (
            "scientific_identity",
            "estimand",
            "metric",
            "baseline",
            "seeds",
            "exposure",
            "authority",
            "budget",
            "stop",
            "claim",
        )
    }
    production_entrypoint = "public-cli->prepare_run->coordinator"
    zero_utility_barrier = "READY_BEFORE_FIRST_UTILITY"
    chain_id = derive_startup_chain_id(
        scientific_projection,
        production_entrypoint,
        zero_utility_barrier,
    )
    contract_path = directory / "recovery-startup-contract.json"
    contract_data = canonical_bytes(
        {
            "startup_chain_binding": {
                "scientific_projection": scientific_projection,
                "production_entrypoint": production_entrypoint,
                "zero_utility_barrier": zero_utility_barrier,
            }
        }
    )
    contract_path.write_bytes(contract_data)
    contract_path.chmod(0o444)
    records = []
    for repair_round in (1, 2):
        record_path = directory / f"recovery-startup-attempt-{repair_round}.json"
        record_data = canonical_bytes(
            {
                "startup_chain_attempt": {
                    "attempt_id": f"recovery-attempt-{repair_round}",
                    "startup_chain_id": chain_id,
                    "repair_round": repair_round,
                    "boundary": "PRE_UTILITY_FAILURE",
                    "utility_observed": False,
                    "protected_access": False,
                }
            }
        )
        record_path.write_bytes(record_data)
        record_path.chmod(0o444)
        records.append(
            {
                "path": str(record_path),
                "sha256": hashlib.sha256(record_data).hexdigest(),
            }
        )
    return {
        "startup_chain_id": chain_id,
        "contract_path": str(contract_path),
        "contract_sha256": hashlib.sha256(contract_data).hexdigest(),
        "prior_attempt_records": records,
    }


def write_v4(path: Path, state: dict) -> None:
    data = canonical_bytes(state)
    path.write_bytes(data)
    checksum_path(path).write_text(
        f"{hashlib.sha256(data).hexdigest()}  {path.name}\n", encoding="utf-8"
    )


def observe(
    path: Path,
    revision: int = 0,
    *,
    expected_terminal_bytes: int | None = None,
    expected_terminal_sha256: str | None = None,
) -> None:
    state = read_state(path)
    terminal = Path(state["objectives"][0]["completion_binding"]["terminal_path"])
    terminal_data = terminal.read_bytes()
    cmd_observe_terminal(
        args(
            state=str(path),
            expected_revision=revision,
            objective_id="objective-1",
            owner_thread_id="worker-1",
            observation_id="observation-1",
            expected_terminal_bytes=(
                len(terminal_data)
                if expected_terminal_bytes is None
                else expected_terminal_bytes
            ),
            expected_terminal_sha256=(
                hashlib.sha256(terminal_data).hexdigest()
                if expected_terminal_sha256 is None
                else expected_terminal_sha256
            ),
            terminal_cursor="cursor:terminal",
            source_final_turn_id="turn-final-1",
        )
    )


class ControllerTerminalRecoveryTest(unittest.TestCase):
    def test_valid_v5_requires_prebound_completion_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            terminal = Path(tmp) / "terminal.md"
            state = base_state(terminal)
            self.assertIs(validate_state(state), state)
            del state["objectives"][0]["completion_binding"]
            with self.assertRaisesRegex(StateError, "completion_binding"):
                validate_state(state)

    def test_observe_is_prebound_idempotent_and_holds_cursor(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory)
            state_path = directory / "state.json"
            write_state(state_path, base_state(terminal), -1)
            observe(state_path)
            observed = read_state(state_path)
            self.assertEqual(
                observed["objectives"][0]["owner_state"],
                "TERMINAL_PENDING_ABSORPTION",
            )
            self.assertEqual(len(observed["pending_absorptions"]), 1)
            self.assertEqual(observed["managed_roles"][0]["cursor"], "cursor:before")
            observe(state_path, 1)
            self.assertEqual(read_state(state_path)["revision"], 1)

    def test_executor_terminal_explicitly_mirrors_null_startup_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory)
            state = base_state(terminal)
            state["objectives"][0]["owner_role"] = "Executor"
            state["managed_roles"][0]["role"] = "Executor"
            state["managed_roles"][0]["title"] = "Executor · Candidate One · ACTIVE"
            state_path = directory / "state.json"
            write_state(state_path, state, -1)
            with self.assertRaisesRegex(
                StateError, "explicitly bind startup_chain_authority"
            ):
                observe(state_path)
            self.assertEqual(read_state(state_path)["revision"], 0)

            terminal.chmod(0o644)
            terminal.write_bytes(
                canonical_bytes(
                    {
                        "completion_binding": state["objectives"][0][
                            "completion_binding"
                        ],
                        "startup_chain_authority": None,
                    }
                )
            )
            terminal.chmod(0o444)
            observe(state_path)
            self.assertEqual(read_state(state_path)["revision"], 1)

    def test_rebuild_add_objective_is_atomic_idempotent_and_preserves_state(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory, "terminal-1.md")
            recovered_terminal = frozen_terminal(
                directory, "terminal-2.json", suffix="2"
            )
            state_path = directory / "state.json"
            initial = base_state(terminal)
            write_state(state_path, initial, -1)
            recovered_binding = binding(recovered_terminal, "2")
            recovered_binding["contract_revision"] = 2
            recovered_terminal.chmod(0o644)
            recovered_terminal.write_bytes(
                canonical_bytes({"completion_binding": recovered_binding})
            )
            recovered_terminal.chmod(0o444)
            recovered_bytes = recovered_terminal.read_bytes()
            command = args(
                state=str(state_path),
                expected_revision=0,
                objective_id="objective-2",
                candidate_id="candidate-2",
                stage="PORTFOLIO_RECOVERY",
                scientific_outcome="UNOBSERVED",
                next_action="WAIT_TERMINAL",
                owner_thread_id="worker-2",
                owner_role="Audit",
                owner_title="Audit · Candidate Two · ACTIVE",
                cursor=None,
                recovery_evidence_ref="thread://worker-2/turn/final-2",
                completion_binding_json=json.dumps(recovered_binding),
                terminal_bytes=len(recovered_bytes),
                terminal_sha256=hashlib.sha256(recovered_bytes).hexdigest(),
            )
            cmd_rebuild_add_objective(command)
            rebuilt = read_state(state_path)
            self.assertEqual(rebuilt["revision"], 1)
            self.assertEqual(rebuilt["objectives"][0], initial["objectives"][0])
            self.assertEqual(rebuilt["objectives"][1]["completion_binding"], recovered_binding)
            self.assertEqual(rebuilt["managed_roles"][1]["thread_id"], "worker-2")
            self.assertEqual(
                rebuilt["objectives"][1]["owner_recovery_evidence_ref"],
                "thread://worker-2/turn/final-2",
            )

            command.expected_revision = 1
            cmd_rebuild_add_objective(command)
            self.assertEqual(read_state(state_path)["revision"], 1)

    def test_rebuild_executor_restores_and_revalidates_startup_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory, "terminal-1.json")
            recovered_terminal = directory / "executor-recovery-terminal.json"
            recovered_binding = binding(recovered_terminal, "executor-recovery")
            recovered_binding["contract_revision"] = 2
            authority = sealed_startup_authority(directory)
            state_path = directory / "state.json"
            write_state(state_path, base_state(terminal), -1)

            def write_recovery_terminal(authority_value: object = ...):
                body = {"completion_binding": recovered_binding}
                if authority_value is not ...:
                    body["startup_chain_authority"] = authority_value
                if recovered_terminal.exists():
                    recovered_terminal.chmod(0o644)
                recovered_terminal.write_bytes(canonical_bytes(body))
                recovered_terminal.chmod(0o444)
                data = recovered_terminal.read_bytes()
                return len(data), hashlib.sha256(data).hexdigest()

            def command(size: int, digest: str, *, expected_revision: int = 0):
                return args(
                    state=str(state_path),
                    expected_revision=expected_revision,
                    objective_id="objective-executor-recovery",
                    candidate_id="candidate-executor-recovery",
                    stage="EXECUTOR_STARTUP_RECOVERY",
                    scientific_outcome="UNOBSERVED",
                    next_action="RETURN_BOUNDED_ROOT_CAUSE_INVENTORY",
                    owner_thread_id="executor-recovery-worker",
                    owner_role="Executor",
                    owner_title="Executor · Startup Recovery · ACTIVE",
                    cursor=None,
                    recovery_evidence_ref="thread://executor-recovery/final",
                    completion_binding_json=json.dumps(recovered_binding),
                    terminal_bytes=size,
                    terminal_sha256=digest,
                )

            drifted = json.loads(json.dumps(authority))
            drifted["contract_sha256"] = "f" * 64
            size, digest = write_recovery_terminal(drifted)
            with self.assertRaisesRegex(StateError, "digest does not match"):
                cmd_rebuild_add_objective(command(size, digest))
            self.assertEqual(read_state(state_path)["revision"], 0)

            size, digest = write_recovery_terminal(authority)
            cmd_rebuild_add_objective(command(size, digest))
            rebuilt = read_state(state_path)
            recovered = next(
                objective
                for objective in rebuilt["objectives"]
                if objective["objective_id"] == "objective-executor-recovery"
            )
            self.assertEqual(recovered["startup_chain_authority"], authority)
            output = io.StringIO()
            with redirect_stdout(output):
                cmd_derive_startup_chain_id(
                    args(
                        state=str(state_path),
                        objective_id="objective-executor-recovery",
                    )
                )
            decision = json.loads(output.getvalue())
            self.assertEqual(decision["pre_utility_failures_recorded"], 2)
            self.assertEqual(decision["authorized_repair_round"], 2)
            self.assertEqual(
                decision["disposition"],
                "CLEAN_CHAIN_REIMPLEMENTATION_IN_SAME_EXECUTOR",
            )
            self.assertEqual(
                decision["on_full_witness_failure"],
                "BOUNDED_ROOT_CAUSE_INVENTORY",
            )

            missing_terminal = directory / "executor-missing-authority.json"
            missing_binding = binding(missing_terminal, "missing-authority")
            missing_terminal.write_bytes(
                canonical_bytes({"completion_binding": missing_binding})
            )
            missing_terminal.chmod(0o444)
            missing_data = missing_terminal.read_bytes()
            with self.assertRaisesRegex(
                StateError, "must explicitly bind startup_chain_authority"
            ):
                cmd_rebuild_add_objective(
                    args(
                        state=str(state_path),
                        expected_revision=1,
                        objective_id="objective-missing-authority",
                        candidate_id="candidate-missing-authority",
                        stage="EXECUTOR_STARTUP_RECOVERY",
                        scientific_outcome="UNOBSERVED",
                        next_action="RECOVER_AUTHORITY",
                        owner_thread_id="executor-missing-worker",
                        owner_role="Executor",
                        owner_title="Executor · Missing Authority · ACTIVE",
                        cursor=None,
                        recovery_evidence_ref="thread://executor-missing/final",
                        completion_binding_json=json.dumps(missing_binding),
                        terminal_bytes=len(missing_data),
                        terminal_sha256=hashlib.sha256(missing_data).hexdigest(),
                    )
                )
            self.assertEqual(read_state(state_path)["revision"], 1)

    def test_rebuild_add_objective_rejects_terminal_envelope_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory, "terminal-1.md")
            recovered_terminal = frozen_terminal(
                directory, "terminal-2.json", suffix="2"
            )
            state_path = directory / "state.json"
            write_state(state_path, base_state(terminal), -1)
            with self.assertRaisesRegex(StateError, "terminal envelope"):
                cmd_rebuild_add_objective(
                    args(
                        state=str(state_path),
                        expected_revision=0,
                        objective_id="objective-2",
                        candidate_id="candidate-2",
                        stage="PORTFOLIO_RECOVERY",
                        scientific_outcome="UNOBSERVED",
                        next_action="WAIT_TERMINAL",
                        owner_thread_id="worker-2",
                        owner_role="Audit",
                        owner_title="Audit · Candidate Two · ACTIVE",
                        cursor=None,
                        recovery_evidence_ref="thread://worker-2/turn/final-2",
                        completion_binding_json=json.dumps(binding(recovered_terminal, "2")),
                        terminal_bytes=len(recovered_terminal.read_bytes()),
                        terminal_sha256="0" * 64,
                    )
                )
            self.assertEqual(read_state(state_path)["revision"], 0)

    def test_pending_identity_detects_changed_terminal(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory)
            state_path = directory / "state.json"
            write_state(state_path, base_state(terminal), -1)
            observe(state_path)
            terminal.chmod(0o644)
            terminal.write_text("changed\n", encoding="utf-8")
            terminal.chmod(0o444)
            with self.assertRaisesRegex(StateError, "valid UTF-8 JSON|pending identity"):
                observe(state_path, 1)

    def test_observe_rejects_non_json_missing_or_drifted_binding_before_pending(self) -> None:
        cases = (
            (b"terminal\n", "valid UTF-8 JSON"),
            (canonical_bytes({}), "completion_binding"),
            (
                canonical_bytes(
                    {
                        "completion_binding": {
                            **binding(Path("/private/tmp/placeholder.json")),
                            "dispatch_id": "dispatch-drifted",
                        }
                    }
                ),
                "dispatch/lease registry",
            ),
        )
        for index, (body, message) in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory(
                dir="/private/tmp"
            ) as tmp:
                directory = Path(tmp)
                terminal = directory / "terminal.json"
                expected = binding(terminal)
                if index == 2:
                    body = canonical_bytes(
                        {
                            "completion_binding": {
                                **expected,
                                "dispatch_id": "dispatch-drifted",
                            }
                        }
                    )
                terminal.write_bytes(body)
                terminal.chmod(0o444)
                state_path = directory / "state.json"
                write_state(state_path, base_state(terminal), -1)
                with self.assertRaisesRegex(StateError, message):
                    observe(state_path)
                unchanged = read_state(state_path)
                self.assertEqual(unchanged["revision"], 0)
                self.assertEqual(unchanged["pending_absorptions"], [])
                self.assertEqual(unchanged["managed_roles"][0]["cursor"], "cursor:before")

    def test_cursor_cannot_cross_unabsorbed_pending_terminal(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory)
            state_path = directory / "state.json"
            write_state(state_path, base_state(terminal), -1)
            observe(state_path)
            with self.assertRaisesRegex(StateError, "not absorbed"):
                cmd_advance_cursors(
                    args(
                        state=str(state_path),
                        expected_revision=1,
                        updates_json=json.dumps(
                            [
                                {
                                    "thread_id": "worker-1",
                                    "expected_cursor": "cursor:before",
                                    "new_cursor": "cursor:after",
                                    "observation_kind": "TERMINAL",
                                    "source_turn_state": "FINAL",
                                    "terminal_event_id": "TERM-1",
                                }
                            ]
                        ),
                    )
                )

    def test_same_native_controller_turn_can_verify_and_activate(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory)
            successor_terminal = directory / "successor.md"
            state_path = directory / "state.json"
            write_state(state_path, base_state(terminal), -1)
            observe(state_path)
            digest = completion_binding_sha256(
                read_state(state_path)["objectives"][0]["completion_binding"]
            )
            cmd_verify_pending_terminal(
                args(
                    state=str(state_path),
                    expected_revision=1,
                    terminal_event_id="TERM-1",
                    completion_binding_sha256=digest,
                    controller_verification_ref="controller-turn-1",
                )
            )
            cmd_activate_successor(
                args(
                    state=str(state_path),
                    expected_revision=2,
                    objective_id="objective-1",
                    new_objective_id=None,
                    terminal_event_id="TERM-1",
                    old_owner_thread_id="worker-1",
                    new_owner_thread_id="worker-1",
                    fresh_thread_reason=None,
                    fresh_thread_evidence_ref=None,
                    new_owner_role="Audit",
                    new_owner_state="ACTIVE",
                    new_owner_title="Audit · Candidate One · ACTIVE",
                    new_cursor="cursor:new",
                    new_candidate_state="OPEN",
                    new_stage="R2B",
                    new_scientific_outcome="UNOBSERVED",
                    new_next_action="CONTINUE",
                    new_completion_binding_json=json.dumps(
                        binding(successor_terminal, "2")
                    ),
                    clear_remote_job_id=[],
                    clear_advisory_id=[],
                )
            )
            final = read_state(state_path)
            self.assertEqual(final["pending_absorptions"], [])
            self.assertIn("TERM-1", final["absorbed_terminal_event_ids"])
            self.assertEqual(final["objectives"][0]["owner_state"], "ACTIVE")
            self.assertEqual(
                final["objectives"][0]["completion_binding"]["terminal_event_id"],
                "TERM-2",
            )

    def test_migrate_v4_adds_native_pending_schema_without_wake_outbox(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory)
            state_path = directory / "state.json"
            legacy = base_state(terminal)
            legacy["schema_version"] = 4
            legacy.pop("pending_absorptions")
            legacy["objectives"][0].pop("completion_binding")
            write_v4(state_path, legacy)
            bindings_path = directory / "bindings.json"
            bindings_path.write_text(
                json.dumps(
                    [
                        {
                            "objective_id": "objective-1",
                            "completion_binding": binding(terminal),
                            "terminal_observation": None,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            cmd_migrate_v4_native_heartbeat(
                args(
                    state=str(state_path),
                    expected_revision=0,
                    bindings_json=str(bindings_path),
                )
            )
            migrated = read_state(state_path)
            self.assertEqual(migrated["schema_version"], 5)
            self.assertNotIn("controller_wake", migrated)
            self.assertEqual(migrated["pending_absorptions"], [])

    def test_active_v4_executor_can_finish_legacy_terminal_after_migration(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = directory / "future-legacy-terminal.json"
            successor_terminal = directory / "future-v5-successor.json"
            state_path = directory / "state.json"
            legacy = base_state(terminal)
            legacy["schema_version"] = 4
            legacy.pop("pending_absorptions")
            legacy["objectives"][0].pop("completion_binding")
            legacy["objectives"][0]["owner_role"] = "Executor"
            legacy["managed_roles"][0]["role"] = "Executor"
            legacy["managed_roles"][0]["title"] = (
                "Executor · Candidate One · ACTIVE"
            )
            write_v4(state_path, legacy)
            future_binding = binding(terminal)
            bindings_path = directory / "bindings.json"
            bindings_path.write_text(
                json.dumps(
                    [
                        {
                            "objective_id": "objective-1",
                            "completion_binding": future_binding,
                            "terminal_observation": None,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            cmd_migrate_v4_native_heartbeat(
                args(
                    state=str(state_path),
                    expected_revision=0,
                    bindings_json=str(bindings_path),
                )
            )
            migrated = read_state(state_path)
            self.assertEqual(migrated["revision"], 1)
            self.assertEqual(migrated["pending_absorptions"], [])
            self.assertEqual(
                migrated["objectives"][0]["legacy_terminal_schema"],
                "V4_EXECUTOR_NO_STARTUP_AUTHORITY_MIRROR",
            )

            terminal_data = canonical_bytes(
                {"completion_binding": future_binding}
            )
            terminal.write_bytes(terminal_data)
            terminal.chmod(0o444)
            callback = io.StringIO()
            with redirect_stdout(callback):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )
            callback_body = json.loads(callback.getvalue())
            self.assertNotIn(
                "startup_chain_authority", callback_body["terminal_body"]
            )
            observe(
                state_path,
                revision=1,
                expected_terminal_bytes=len(terminal_data),
                expected_terminal_sha256=hashlib.sha256(terminal_data).hexdigest(),
            )
            observed = read_state(state_path)
            self.assertEqual(observed["revision"], 2)
            self.assertEqual(len(observed["pending_absorptions"]), 1)
            cmd_verify_pending_terminal(
                args(
                    state=str(state_path),
                    expected_revision=2,
                    terminal_event_id="TERM-1",
                    completion_binding_sha256=completion_binding_sha256(
                        future_binding
                    ),
                    controller_verification_ref="controller:active-v4-verify",
                )
            )
            cmd_activate_successor(
                args(
                    state=str(state_path),
                    expected_revision=3,
                    objective_id="objective-1",
                    new_objective_id=None,
                    terminal_event_id="TERM-1",
                    old_owner_thread_id="worker-1",
                    new_owner_thread_id="worker-1",
                    fresh_thread_reason=None,
                    fresh_thread_evidence_ref=None,
                    new_owner_role="Executor",
                    new_owner_state="ACTIVE",
                    new_owner_title="Executor · Candidate One · ACTIVE",
                    new_cursor="cursor:v5-successor",
                    new_candidate_state="OPEN",
                    new_stage="V5_SUCCESSOR",
                    new_scientific_outcome="UNOBSERVED",
                    new_next_action="RUN_PROSPECTIVE_V5_WITNESS",
                    new_completion_binding_json=json.dumps(
                        binding(successor_terminal, "2")
                    ),
                    clear_remote_job_id=[],
                    clear_advisory_id=[],
                )
            )
            final = read_state(state_path)
            self.assertEqual(final["revision"], 4)
            self.assertEqual(final["pending_absorptions"], [])
            self.assertIn("TERM-1", final["absorbed_terminal_event_ids"])
            self.assertNotIn("legacy_terminal_schema", final["objectives"][0])

    def test_v4_executor_terminal_without_new_mirror_remains_absorbable(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = frozen_terminal(directory)
            successor_terminal = directory / "successor-terminal.json"
            state_path = directory / "state.json"
            legacy = base_state(terminal)
            legacy["schema_version"] = 4
            legacy.pop("pending_absorptions")
            legacy["objectives"][0].pop("completion_binding")
            legacy["objectives"][0]["owner_role"] = "Executor"
            legacy["managed_roles"][0]["role"] = "Executor"
            legacy["managed_roles"][0]["title"] = (
                "Executor · Candidate One · ACTIVE"
            )
            write_v4(state_path, legacy)
            bindings_path = directory / "bindings.json"
            bindings_path.write_text(
                json.dumps(
                    [
                        {
                            "objective_id": "objective-1",
                            "completion_binding": binding(terminal),
                            "terminal_observation": {
                                "terminal_cursor": "cursor:legacy-terminal",
                                "source_final_turn_id": "turn:legacy-final",
                                "observation_id": "observation:legacy-v4",
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )
            cmd_migrate_v4_native_heartbeat(
                args(
                    state=str(state_path),
                    expected_revision=0,
                    bindings_json=str(bindings_path),
                )
            )
            migrated = read_state(state_path)
            self.assertEqual(migrated["revision"], 1)
            self.assertEqual(
                migrated["objectives"][0]["legacy_terminal_schema"],
                "V4_EXECUTOR_NO_STARTUP_AUTHORITY_MIRROR",
            )
            self.assertEqual(len(migrated["pending_absorptions"]), 1)

            callback = io.StringIO()
            with redirect_stdout(callback):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )
            callback_body = json.loads(callback.getvalue())
            self.assertNotIn(
                "startup_chain_authority", callback_body["terminal_body"]
            )

            terminal_data = terminal.read_bytes()
            observe(
                state_path,
                revision=1,
                expected_terminal_bytes=len(terminal_data),
                expected_terminal_sha256=hashlib.sha256(terminal_data).hexdigest(),
            )
            self.assertEqual(read_state(state_path)["revision"], 1)
            cmd_verify_pending_terminal(
                args(
                    state=str(state_path),
                    expected_revision=1,
                    terminal_event_id="TERM-1",
                    completion_binding_sha256=completion_binding_sha256(
                        migrated["objectives"][0]["completion_binding"]
                    ),
                    controller_verification_ref="controller:legacy-v4-verify",
                )
            )
            cmd_activate_successor(
                args(
                    state=str(state_path),
                    expected_revision=2,
                    objective_id="objective-1",
                    new_objective_id=None,
                    terminal_event_id="TERM-1",
                    old_owner_thread_id="worker-1",
                    new_owner_thread_id="worker-1",
                    fresh_thread_reason=None,
                    fresh_thread_evidence_ref=None,
                    new_owner_role="Executor",
                    new_owner_state="ACTIVE",
                    new_owner_title="Executor · Candidate One · ACTIVE",
                    new_cursor="cursor:successor",
                    new_candidate_state="OPEN",
                    new_stage="EXECUTOR_SUCCESSOR",
                    new_scientific_outcome="UNOBSERVED",
                    new_next_action="RUN_PROSPECTIVE_STARTUP_WITNESS",
                    new_completion_binding_json=json.dumps(
                        binding(successor_terminal, "2")
                    ),
                    clear_remote_job_id=[],
                    clear_advisory_id=[],
                )
            )
            final = read_state(state_path)
            self.assertEqual(final["revision"], 3)
            self.assertEqual(final["pending_absorptions"], [])
            self.assertIn("TERM-1", final["absorbed_terminal_event_ids"])
            self.assertNotIn("legacy_terminal_schema", final["objectives"][0])

    def test_external_watcher_commands_are_not_exposed(self) -> None:
        choices = build_parser()._subparsers._group_actions[0].choices
        for command in (
            "claim-controller-wake",
            "complete-controller-wake",
            "rearm-controller-wake",
            "arm-controller-wake-guard",
        ):
            self.assertNotIn(command, choices)
        self.assertIn("migrate-v4-native-heartbeat", choices)
        self.assertIn("rebuild-add-objective", choices)
        self.assertIn("observe-terminal", choices)
        self.assertIn("verify-pending-terminal", choices)
        self.assertIn("prepare-terminal-callback", choices)
        self.assertIn("derive-startup-chain-id", choices)
        self.assertIn("record-startup-attempt", choices)

    def test_callback_is_generated_from_sealed_file_and_current_binding(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = directory / "terminal.json"
            state_path = directory / "state.json"
            state = base_state(terminal)
            body = {
                "completion_binding": state["objectives"][0]["completion_binding"],
                "terminal_event_id": "TERM-1",
                "candidate_state": "OPEN",
            }
            data = canonical_bytes(body)
            terminal.write_bytes(data)
            terminal.chmod(0o444)
            write_state(state_path, state, -1)
            output = io.StringIO()
            with redirect_stdout(output):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["completion_binding"], body["completion_binding"])
            self.assertEqual(payload["final_bytes"], len(data))
            self.assertEqual(payload["final_sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(payload["terminal_body"], body)

    def test_observe_rejects_terminal_replaced_after_callback_before_state_mutation(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = directory / "terminal.json"
            state_path = directory / "state.json"
            state = base_state(terminal)
            binding_value = state["objectives"][0]["completion_binding"]
            body_a = {
                "completion_binding": binding_value,
                "candidate_state": "OPEN",
                "diagnostic": "A",
            }
            data_a = canonical_bytes(body_a)
            terminal.write_bytes(data_a)
            terminal.chmod(0o444)
            write_state(state_path, state, -1)
            callback_output = io.StringIO()
            with redirect_stdout(callback_output):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )
            callback = json.loads(callback_output.getvalue())

            terminal.unlink()
            terminal.write_bytes(
                canonical_bytes(
                    {
                        "completion_binding": binding_value,
                        "candidate_state": "OPEN",
                        "diagnostic": "B",
                    }
                )
            )
            terminal.chmod(0o444)
            with self.assertRaisesRegex(StateError, "delivered callback envelope"):
                observe(
                    state_path,
                    expected_terminal_bytes=callback["final_bytes"],
                    expected_terminal_sha256=callback["final_sha256"],
                )
            unchanged = read_state(state_path)
            self.assertEqual(unchanged["revision"], 0)
            self.assertEqual(unchanged["pending_absorptions"], [])
            self.assertEqual(unchanged["managed_roles"][0]["cursor"], "cursor:before")
            self.assertEqual(unchanged["objectives"][0]["owner_thread_id"], "worker-1")

    def test_callback_and_observe_reject_boolean_lease_epoch_before_state_mutation(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = directory / "terminal.json"
            state_path = directory / "state.json"
            state = base_state(terminal)
            bool_binding = dict(state["objectives"][0]["completion_binding"])
            bool_binding["lease_epoch"] = True
            data = canonical_bytes({"completion_binding": bool_binding})
            terminal.write_bytes(data)
            terminal.chmod(0o444)
            write_state(state_path, state, -1)

            with self.assertRaisesRegex(StateError, "lease_epoch must be a positive integer"):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )
            with self.assertRaisesRegex(StateError, "lease_epoch must be a positive integer"):
                observe(
                    state_path,
                    expected_terminal_bytes=len(data),
                    expected_terminal_sha256=hashlib.sha256(data).hexdigest(),
                )
            unchanged = read_state(state_path)
            self.assertEqual(unchanged["revision"], 0)
            self.assertEqual(unchanged["pending_absorptions"], [])
            self.assertEqual(unchanged["managed_roles"][0]["cursor"], "cursor:before")

    def test_callback_and_observe_reject_nonfinite_json_before_state_mutation(self) -> None:
        for label, value in (
            ("nan", float("nan")),
            ("positive_infinity", float("inf")),
            ("negative_infinity", float("-inf")),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory(
                dir="/private/tmp"
            ) as tmp:
                directory = Path(tmp)
                terminal = directory / "terminal.json"
                state_path = directory / "state.json"
                state = base_state(terminal)
                body = {
                    "completion_binding": state["objectives"][0]["completion_binding"],
                    "diagnostic": value,
                }
                data = (json.dumps(body, separators=(",", ":")) + "\n").encode("utf-8")
                terminal.write_bytes(data)
                terminal.chmod(0o444)
                write_state(state_path, state, -1)

                with self.assertRaisesRegex(StateError, "non-standard JSON constant"):
                    cmd_prepare_terminal_callback(
                        args(
                            state=str(state_path),
                            objective_id="objective-1",
                            terminal_event_id="TERM-1",
                        )
                    )
                with self.assertRaisesRegex(StateError, "non-standard JSON constant"):
                    observe(
                        state_path,
                        expected_terminal_bytes=len(data),
                        expected_terminal_sha256=hashlib.sha256(data).hexdigest(),
                    )
                unchanged = read_state(state_path)
                self.assertEqual(unchanged["revision"], 0)
                self.assertEqual(unchanged["pending_absorptions"], [])
                with self.assertRaisesRegex(StateError, "non-finite value"):
                    canonical_bytes({"diagnostic": value})

    def test_callback_and_observe_reject_unicode_surrogates_before_state_mutation(self) -> None:
        for location in ("value", "key"):
            with self.subTest(location=location), tempfile.TemporaryDirectory(
                dir="/private/tmp"
            ) as tmp:
                directory = Path(tmp)
                terminal = directory / "terminal.json"
                state_path = directory / "state.json"
                state = base_state(terminal)
                state["objectives"][0]["owner_role"] = "Executor"
                state["managed_roles"][0]["role"] = "Executor"
                state["managed_roles"][0]["title"] = (
                    "Executor · Candidate One · ACTIVE"
                )
                binding_json = json.dumps(
                    state["objectives"][0]["completion_binding"],
                    separators=(",", ":"),
                )
                surrogate_escape = "\\ud800"
                if location == "value":
                    diagnostic = ',"diagnostic":"' + surrogate_escape + '"'
                else:
                    diagnostic = ',"' + surrogate_escape + '":"diagnostic"'
                data = (
                    '{"completion_binding":'
                    + binding_json
                    + ',"startup_chain_authority":null'
                    + diagnostic
                    + "}\n"
                ).encode("utf-8")
                terminal.write_bytes(data)
                terminal.chmod(0o444)
                write_state(state_path, state, -1)
                before = read_state(state_path)
                before_bytes = state_path.read_bytes()
                before_checksum = checksum_path(state_path).read_bytes()

                with self.assertRaisesRegex(StateError, "Unicode surrogate"):
                    cmd_prepare_terminal_callback(
                        args(
                            state=str(state_path),
                            objective_id="objective-1",
                            terminal_event_id="TERM-1",
                        )
                    )
                with self.assertRaisesRegex(StateError, "Unicode surrogate"):
                    observe(
                        state_path,
                        expected_terminal_bytes=len(data),
                        expected_terminal_sha256=hashlib.sha256(data).hexdigest(),
                    )
                after = read_state(state_path)
                self.assertEqual(after, before)
                self.assertEqual(state_path.read_bytes(), before_bytes)
                self.assertEqual(
                    checksum_path(state_path).read_bytes(), before_checksum
                )
                self.assertEqual(after["revision"], 0)
                self.assertEqual(after["pending_absorptions"], [])
                self.assertEqual(after["absorbed_terminal_event_ids"], [])
                self.assertEqual(
                    after["managed_roles"][0]["cursor"], "cursor:before"
                )
                self.assertEqual(
                    after["objectives"][0]["owner_thread_id"], "worker-1"
                )

        with self.assertRaisesRegex(StateError, "Unicode surrogate"):
            canonical_bytes({"diagnostic": chr(0xD800)})
        with self.assertRaisesRegex(StateError, "Unicode surrogate"):
            canonical_bytes({chr(0xD800): "diagnostic"})

    def test_callback_and_observe_reject_finite_syntax_float_overflow_before_state_mutation(self) -> None:
        for literal in ("1e9999", "-1e9999"):
            with self.subTest(literal=literal), tempfile.TemporaryDirectory(
                dir="/private/tmp"
            ) as tmp:
                directory = Path(tmp)
                terminal = directory / "terminal.json"
                state_path = directory / "state.json"
                state = base_state(terminal)
                binding_json = json.dumps(
                    state["objectives"][0]["completion_binding"],
                    separators=(",", ":"),
                )
                data = (
                    '{"completion_binding":'
                    + binding_json
                    + ',"diagnostic":'
                    + literal
                    + "}\n"
                ).encode("utf-8")
                terminal.write_bytes(data)
                terminal.chmod(0o444)
                write_state(state_path, state, -1)

                with self.assertRaisesRegex(StateError, "non-finite"):
                    cmd_prepare_terminal_callback(
                        args(
                            state=str(state_path),
                            objective_id="objective-1",
                            terminal_event_id="TERM-1",
                        )
                    )
                with self.assertRaisesRegex(StateError, "non-finite"):
                    observe(
                        state_path,
                        expected_terminal_bytes=len(data),
                        expected_terminal_sha256=hashlib.sha256(data).hexdigest(),
                    )
                unchanged = read_state(state_path)
                self.assertEqual(unchanged["revision"], 0)
                self.assertEqual(unchanged["pending_absorptions"], [])
                self.assertEqual(
                    unchanged["managed_roles"][0]["cursor"], "cursor:before"
                )

    def test_callback_rejects_incomplete_or_conflicting_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = directory / "terminal.json"
            state_path = directory / "state.json"
            state = base_state(terminal)
            binding_value = state["objectives"][0]["completion_binding"]
            incomplete = dict(binding_value)
            incomplete.pop("terminal_event_id")
            terminal.write_bytes(canonical_bytes({"completion_binding": incomplete}))
            terminal.chmod(0o444)
            write_state(state_path, state, -1)
            with self.assertRaisesRegex(StateError, "missing keys: terminal_event_id"):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )

            terminal.chmod(0o644)
            terminal.write_bytes(
                canonical_bytes(
                    {
                        "completion_binding": binding_value,
                        "terminal_event_id": "TERM-CONFLICT",
                    }
                )
            )
            terminal.chmod(0o444)
            with self.assertRaisesRegex(StateError, "top-level terminal_event_id mirror"):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )

    def test_digest_pinned_legacy_terminal_binding_projection(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            for missing in (frozenset(), frozenset({"terminal_event_id", "terminal_path"})):
                terminal = directory / ("legacy-" + str(len(missing)) + ".json")
                expected = binding(terminal)
                raw_binding = dict(expected)
                for key in missing:
                    raw_binding.pop(key)
                raw_binding["legacy_envelope_field"] = "preserved"
                body = {"completion_binding": raw_binding}
                if "terminal_event_id" in missing:
                    body["terminal_event_id"] = expected["terminal_event_id"]
                data = canonical_bytes(body)
                terminal.write_bytes(data)
                terminal.chmod(0o444)
                compatibility = {
                    str(terminal): {
                        "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "missing_from_binding": missing,
                        "allow_missing_startup_authority_mirror": bool(missing),
                    }
                }
                with mock.patch.dict(
                    controller_state.LEGACY_TERMINAL_COMPLETION_BINDING_PROJECTIONS,
                    compatibility,
                ):
                    observed_data, observed_body = controller_state._read_bound_terminal(
                        terminal,
                        expected,
                        None,
                        require_startup_authority_mirror=bool(missing),
                    )
                self.assertEqual(observed_data, data)
                self.assertEqual(observed_body, body)

    def test_digest_pinned_audit_terminal_may_carry_successor_startup_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = directory / "audit-terminal.json"
            expected = binding(terminal)
            authority = sealed_startup_authority(directory)
            body = {
                "completion_binding": expected,
                "startup_chain_authority": authority,
            }
            data = canonical_bytes(body)
            terminal.write_bytes(data)
            terminal.chmod(0o444)
            compatibility = {
                str(terminal): {
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "missing_from_binding": frozenset(),
                    "allow_missing_startup_authority_mirror": False,
                    "allow_unbound_startup_authority_mirror": True,
                }
            }
            with mock.patch.dict(
                controller_state.LEGACY_TERMINAL_COMPLETION_BINDING_PROJECTIONS,
                compatibility,
            ):
                observed_data, observed_body = controller_state._read_bound_terminal(
                    terminal,
                    expected,
                    None,
                )
            self.assertEqual(observed_data, data)
            self.assertEqual(observed_body, body)

    def test_digest_pinned_projection_rejects_content_drift_without_strict_fallback(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            terminal = Path(tmp) / "legacy-terminal.json"
            expected = binding(terminal)
            legacy_data = canonical_bytes(
                {
                    "completion_binding": {
                        **expected,
                        "legacy_envelope_field": "preserved",
                    }
                }
            )
            strict_data = canonical_bytes({"completion_binding": expected})
            terminal.write_bytes(strict_data)
            terminal.chmod(0o444)
            compatibility = {
                str(terminal): {
                    "bytes": len(legacy_data),
                    "sha256": hashlib.sha256(legacy_data).hexdigest(),
                    "missing_from_binding": frozenset(),
                    "allow_missing_startup_authority_mirror": False,
                }
            }
            with mock.patch.dict(
                controller_state.LEGACY_TERMINAL_COMPLETION_BINDING_PROJECTIONS,
                compatibility,
            ):
                with self.assertRaisesRegex(
                    StateError, "legacy terminal compatibility identity mismatch"
                ):
                    controller_state._read_bound_terminal(terminal, expected)

    def test_callback_rejects_mutable_or_registry_drifted_terminal(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = directory / "terminal.json"
            state_path = directory / "state.json"
            state = base_state(terminal)
            binding_value = state["objectives"][0]["completion_binding"]
            drifted = dict(binding_value)
            drifted["dispatch_id"] = "dispatch-drifted"
            terminal.write_bytes(canonical_bytes({"completion_binding": drifted}))
            terminal.chmod(0o444)
            write_state(state_path, state, -1)
            with self.assertRaisesRegex(StateError, "dispatch/lease registry"):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )

            terminal.chmod(0o644)
            terminal.write_bytes(canonical_bytes({"completion_binding": binding_value}))
            with self.assertRaisesRegex(StateError, "immutable to ordinary writes"):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )

    def test_callback_rejects_symlink_and_hardlink_terminal_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            target = directory / "target.json"
            symlink = directory / "terminal-symlink.json"
            target_state = base_state(symlink)
            target.write_bytes(
                canonical_bytes(
                    {"completion_binding": target_state["objectives"][0]["completion_binding"]}
                )
            )
            target.chmod(0o444)
            symlink.symlink_to(target)
            state_path = directory / "symlink-state.json"
            write_state(state_path, target_state, -1)
            with self.assertRaisesRegex(StateError, "unavailable|non-symlink"):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )

            hardlink = directory / "terminal-hardlink.json"
            hardlink_state = base_state(hardlink)
            target.chmod(0o644)
            target.write_bytes(
                canonical_bytes(
                    {"completion_binding": hardlink_state["objectives"][0]["completion_binding"]}
                )
            )
            target.chmod(0o444)
            os.link(target, hardlink)
            hardlink_state_path = directory / "hardlink-state.json"
            write_state(hardlink_state_path, hardlink_state, -1)
            with self.assertRaisesRegex(StateError, "link count must be one"):
                cmd_prepare_terminal_callback(
                    args(
                        state=str(hardlink_state_path),
                        objective_id="objective-1",
                        terminal_event_id="TERM-1",
                    )
                )

    def test_fifo_terminal_fails_without_blocking_callback_or_observe(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            terminal = directory / "terminal.fifo"
            state_path = directory / "state.json"
            os.mkfifo(terminal, 0o444)
            terminal.chmod(0o444)
            write_state(state_path, base_state(terminal), -1)
            before = read_state(state_path)
            before_bytes = state_path.read_bytes()
            before_checksum = checksum_path(state_path).read_bytes()
            tool = (
                Path(__file__).resolve().parents[1]
                / "scripts"
                / "controller_control_state.py"
            )
            commands = (
                [
                    sys.executable,
                    str(tool),
                    "prepare-terminal-callback",
                    "--state",
                    str(state_path),
                    "--objective-id",
                    "objective-1",
                    "--terminal-event-id",
                    "TERM-1",
                ],
                [
                    sys.executable,
                    str(tool),
                    "observe-terminal",
                    "--state",
                    str(state_path),
                    "--expected-revision",
                    "0",
                    "--objective-id",
                    "objective-1",
                    "--owner-thread-id",
                    "worker-1",
                    "--observation-id",
                    "fifo-observation",
                    "--expected-terminal-bytes",
                    "1",
                    "--expected-terminal-sha256",
                    "0" * 64,
                    "--terminal-cursor",
                    "cursor:fifo",
                    "--source-final-turn-id",
                    "turn:fifo",
                ],
            )
            for command in commands:
                with self.subTest(command=command[2]):
                    completed = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=2.0,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    failure = json.loads(completed.stdout)
                    self.assertEqual(failure["status"], "FAIL")
                    self.assertIn("regular non-symlink file", failure["error"])
                    self.assertEqual(read_state(state_path), before)
                    self.assertEqual(state_path.read_bytes(), before_bytes)
                    self.assertEqual(
                        checksum_path(state_path).read_bytes(), before_checksum
                    )

    def test_parent_symlink_cannot_escape_terminal_root_for_callback_or_observe(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            allowed = directory / "allowed"
            outside = directory / "outside"
            allowed.mkdir(mode=0o750)
            outside.mkdir(mode=0o750)
            link = allowed / "link"
            link.symlink_to(outside, target_is_directory=True)
            terminal_via_link = link / "terminal.json"
            expected_binding = binding(terminal_via_link)
            outside_terminal = outside / "terminal.json"
            outside_terminal.write_bytes(
                canonical_bytes({"completion_binding": expected_binding})
            )
            outside_terminal.chmod(0o444)
            state_path = directory / "state.json"
            with mock.patch(
                "scripts.controller_control_state.TERMINAL_ROOTS",
                (PurePosixPath(str(allowed)),),
            ):
                write_state(state_path, base_state(terminal_via_link), -1)
                for action in ("callback", "observe"):
                    with self.subTest(action=action), self.assertRaisesRegex(
                        StateError, "symlinked component"
                    ):
                        if action == "callback":
                            cmd_prepare_terminal_callback(
                                args(
                                    state=str(state_path),
                                    objective_id="objective-1",
                                    terminal_event_id="TERM-1",
                                )
                            )
                        else:
                            observe(state_path)
                unchanged = read_state(state_path)
                self.assertEqual(unchanged["revision"], 0)
                self.assertEqual(unchanged["pending_absorptions"], [])

if __name__ == "__main__":
    unittest.main()
