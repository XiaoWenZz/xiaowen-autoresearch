import hashlib
import io
import json
import multiprocessing
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.controller_control_state import (
    StateError,
    active_state_projection,
    cmd_absorb_and_block,
    cmd_absorb_nonblocking_advisory,
    canonical_bytes,
    checksum_path,
    cmd_activate_successor,
    cmd_advance_cursors,
    cmd_claim_advisory,
    cmd_close_objective,
    cmd_complete_advisory,
    cmd_derive_startup_chain_id,
    cmd_migrate_v2,
    cmd_migrate_v3,
    cmd_observe_terminal,
    cmd_record_startup_attempt,
    cmd_reconcile_open,
    cmd_replace,
    cmd_verify_pending_terminal,
    completion_binding_sha256,
    derive_startup_chain_id,
    read_state,
    validate_state,
    write_state,
)


def completion_binding(
    terminal_path: str = "/private/tmp/TERM-AUTHORITY-1.json",
    suffix: str = "1",
) -> dict:
    return {
        "task_id": f"task-{suffix}",
        "dispatch_id": f"dispatch-{suffix}",
        "lease_epoch": 1,
        "contract_revision": f"contract-{suffix}",
        "terminal_event_id": f"TERM-AUTHORITY-{suffix}",
        "terminal_path": terminal_path,
    }


def remote_job(
    *,
    job_id: str = "job-2",
    objective_id: str = "objective-2",
    owner_thread_id: str = "worker-1",
) -> dict:
    return {
        "job_id": job_id,
        "objective_id": objective_id,
        "owner_thread_id": owner_thread_id,
        "host": "dual5090",
        "unit": f"{job_id}.service",
        "output_path": f"/home/xiaowen/runs/{job_id}",
        "expected_files": ["terminal.json"],
        "eta": "2026-08-09T12:00:00Z",
        "late_threshold": "2026-08-09T13:00:00Z",
        "monitor_state": "ACTIVE",
        "wake_delivery": {
            "state": "NONE",
            "claim_token": None,
            "observation_id": None,
        },
    }


def base_state(terminal_path: str = "/private/tmp/TERM-AUTHORITY-1.json") -> dict:
    return {
        "schema_version": 5,
        "revision": 0,
        "updated_at": "2026-08-05T00:00:00Z",
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
                "completion_binding": completion_binding(terminal_path),
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
        "remote_jobs": [
            {
                "job_id": "job-1",
                "objective_id": "objective-1",
                "owner_thread_id": "worker-1",
                "host": "dual5090",
                "unit": "job-1.service",
                "output_path": "/home/xiaowen/runs/job-1",
                "expected_files": ["terminal.json"],
                "eta": "2026-08-05T01:00:00Z",
                "late_threshold": "2026-08-05T02:00:00Z",
                "monitor_state": "ACTIVE",
                "wake_delivery": {"state": "NONE", "claim_token": None, "observation_id": None},
            }
        ],
        "advisory_reads": [],
        "absorbed_advisory_scopes": [],
        "pending_absorptions": [],
        "absorbed_terminal_event_ids": [],
    }


class ActiveProjectionTest(unittest.TestCase):
    def test_active_projection_omits_replay_history_bodies(self) -> None:
        state = base_state()
        state["absorbed_terminal_event_ids"] = [
            f"TERM-ABSORBED-{index:04d}" for index in range(330)
        ]
        state["objectives"].append(
            {
                "objective_id": "objective-closed",
                "candidate_id": "candidate-closed",
                "candidate_state": "CLOSED",
                "stage": "SCOPED_CLOSE",
                "scientific_outcome": "PRESERVED_IN_CANONICAL_STATE_ONLY",
                "lifecycle": "DONE",
                "next_action": "NONE",
                "owner_thread_id": None,
                "owner_role": None,
                "owner_state": None,
                "completion_binding": None,
                "blocker": None,
            }
        )

        projection = active_state_projection(state)

        self.assertEqual(projection["projection"], "active")
        self.assertEqual(
            [item["objective_id"] for item in projection["objectives"]],
            ["objective-1"],
        )
        self.assertNotIn("absorbed_terminal_event_ids", projection)
        self.assertNotIn("absorbed_advisory_scopes", projection)
        self.assertEqual(
            projection["history_summary"]["absorbed_terminal_event_ids"]["count"],
            330,
        )
        self.assertEqual(
            projection["history_summary"]["closed_objectives"]["count"], 1
        )
        self.assertLess(
            len(canonical_bytes(projection)),
            len(canonical_bytes(state)) // 2,
        )


def observe_and_verify(path: Path, revision: int, objective_id: str = "objective-1") -> int:
    state = read_state(path)
    objective = next(item for item in state["objectives"] if item["objective_id"] == objective_id)
    binding = objective["completion_binding"]
    terminal = Path(binding["terminal_path"])
    terminal_body = {"completion_binding": binding}
    if objective.get("owner_role") == "Executor":
        terminal_body["startup_chain_authority"] = objective.get(
            "startup_chain_authority"
        )
        terminal_body["executor_continuation_phase"] = objective.get(
            "executor_continuation_phase", "NONE"
        )
    terminal_data = canonical_bytes(terminal_body)
    terminal.write_bytes(terminal_data)
    terminal.chmod(0o444)
    cmd_observe_terminal(
        type(
            "Args",
            (),
            {
                "state": str(path),
                "expected_revision": revision,
                "objective_id": objective_id,
                "owner_thread_id": objective["owner_thread_id"],
                "observation_id": "fixture-observation",
                "expected_terminal_bytes": len(terminal_data),
                "expected_terminal_sha256": hashlib.sha256(terminal_data).hexdigest(),
                "terminal_cursor": "fixture-terminal-cursor",
                "source_final_turn_id": "fixture-final-turn",
            },
        )()
    )
    cmd_verify_pending_terminal(
        type(
            "Args",
            (),
            {
                "state": str(path),
                "expected_revision": revision + 1,
                "terminal_event_id": binding["terminal_event_id"],
                "completion_binding_sha256": completion_binding_sha256(binding),
                "controller_verification_ref": "fixture-controller-turn",
            },
        )()
    )
    return revision + 2


def set_terminal_binding(state: dict, path: Path, terminal_event_id: str) -> None:
    binding = state["objectives"][0]["completion_binding"]
    binding["terminal_event_id"] = terminal_event_id
    binding["terminal_path"] = str(path.parent / f"{terminal_event_id}.json")


def write_and_verify(path: Path, state: dict, terminal_event_id: str) -> int:
    set_terminal_binding(state, path, terminal_event_id)
    write_state(path, state, -1)
    return observe_and_verify(path, 0)


def successor_args(**overrides: object) -> object:
    values: dict[str, object] = {
        "state": "",
        "expected_revision": 0,
        "objective_id": "objective-1",
        "new_objective_id": "objective-2",
        "terminal_event_id": "TERM-AUTHORITY-1",
        "old_owner_thread_id": "worker-1",
        "new_owner_thread_id": "worker-1",
        "fresh_thread_reason": None,
        "fresh_thread_evidence_ref": None,
        "new_owner_role": "Executor",
        "executor_continuation_kind": "ZERO_UTILITY_IMPLEMENTATION",
        "new_owner_state": "ACTIVE",
        "new_owner_title": "Executor · Candidate Two · ACTIVE",
        "new_cursor": "cursor:activation",
        "new_candidate_state": "OPEN",
        "new_stage": "R3_ACTIVE",
        "new_scientific_outcome": "UNOBSERVED",
        "new_next_action": "WAIT_EXECUTOR_TERMINAL",
        "new_completion_binding_json": json.dumps(
            completion_binding("/private/tmp/TERM-AUTHORITY-2.json", "2")
        ),
        "new_remote_job_json": None,
        "clear_remote_job_id": ["job-1"],
        "clear_advisory_id": [],
    }
    values.update(overrides)
    return type("Args", (), values)()


def sealed_startup_authority(
    directory: Path,
    *,
    rounds: tuple[int, ...] = (1, 2),
    suffix: str = "main",
    entrypoint_suffix: str = "",
) -> dict:
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
    production_entrypoint = (
        "public-cli->prepare_run->coordinator" + entrypoint_suffix
    )
    zero_utility_barrier = "READY_BEFORE_FIRST_UTILITY"
    chain_id = derive_startup_chain_id(
        scientific_projection,
        production_entrypoint,
        zero_utility_barrier,
    )
    contract_path = directory / f"startup-contract-{suffix}.json"
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
    attempt_records = []
    for repair_round in rounds:
        attempt_path = directory / f"startup-attempt-{suffix}-{repair_round}.json"
        attempt_data = canonical_bytes(
            {
                "startup_chain_attempt": {
                    "attempt_id": f"{suffix}-attempt-{repair_round:03d}",
                    "startup_chain_id": chain_id,
                    "repair_round": repair_round,
                    "boundary": "PRE_UTILITY_FAILURE",
                    "utility_observed": False,
                    "protected_access": False,
                }
            }
        )
        attempt_path.write_bytes(attempt_data)
        attempt_path.chmod(0o444)
        attempt_records.append(
            {
                "path": str(attempt_path),
                "sha256": hashlib.sha256(attempt_data).hexdigest(),
            }
        )
    return {
        "startup_chain_id": chain_id,
        "contract_path": str(contract_path),
        "contract_sha256": hashlib.sha256(contract_data).hexdigest(),
        "prior_attempt_records": attempt_records,
    }


def advisory_record(**overrides: object) -> dict:
    values: dict[str, object] = {
        "advisory_id": "advisory-1",
        "objective_id": "objective-1",
        "conversation_thread_id": "pro-thread-1",
        "reader_thread_id": "audit-thread-1",
        "reader_role": "Audit",
        "submitted_at": "2026-08-05T00:10:00Z",
        "submitted_thread_updated_at": 100,
        "not_before": "2026-08-05T00:20:00Z",
        "scope_revision": 1,
        "scope_sha256": "a" * 64,
        "batch_mode": "NON_BLOCKING",
        "decision_gate": "NON_BLOCKING",
        "blocking_gate_id": None,
        "monitor_state": "AWAITING_RESPONSE",
        "observed_thread_updated_at": None,
        "wake_delivery": {"state": "NONE", "claim_token": None, "observation_id": None},
    }
    values.update(overrides)
    return values


def audit_owner_state() -> dict:
    state = base_state()
    state["objectives"][0].update(
        {"stage": "R2_AUDIT", "owner_role": "Audit", "owner_state": "ACTIVE"}
    )
    state["managed_roles"][0].update(
        {
            "role": "Audit",
            "title": "Audit · Candidate One · ACTIVE",
            "state": "ACTIVE",
        }
    )
    state["remote_jobs"] = []
    return state


def scoped_close_record() -> dict:
    return {
        "basis": "PROSPECTIVE_SCOPED_MPE_FAILURE",
        "scope": "exact finite Scout cell",
        "evidence_ref": "terminal-1",
        "reopening_fact": "A distinct prospective estimand is frozen.",
        "independent_audit_terminal_id": "audit-1",
        "evidence_eligible": True,
        "prospective_action_table_pass": True,
        "finite_cell_complete": True,
        "preregistered_mpe_failure": True,
        "scope_boundary_preserved": True,
        "adversarial_review_pass": True,
        "powered_negative_claimed": False,
    }


def close_args(path: Path, **overrides: object) -> object:
    values: dict[str, object] = {
        "state": str(path),
        "expected_revision": 0,
        "objective_id": "objective-1",
        "terminal_event_id": "TERM-CLOSE-1",
        "old_owner_thread_id": "worker-1",
        "new_stage": "SCOPED_CLOSE",
        "new_scientific_outcome": "OBSERVED_BELOW_MPE_SCOPED_CLOSED",
        "new_next_action": "NO_SUCCESSOR_UNLESS_REOPENED",
        "closure_json": json.dumps(scoped_close_record()),
        "clear_remote_job_id": [],
        "clear_advisory_id": [],
    }
    values.update(overrides)
    return type("Args", (), values)()


class ControllerControlStateTest(unittest.TestCase):
    def test_valid_state_round_trips_with_checksum(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            written = write_state(path, base_state(), -1)
            self.assertEqual(written["revision"], 0)
            self.assertEqual(read_state(path), written)
            self.assertTrue(path.with_name(path.name + ".sha256").is_file())

    def test_compare_and_swap_rejects_stale_revision(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            with self.assertRaisesRegex(StateError, "revision conflict"):
                write_state(path, base_state(), -1)

    def test_delegated_objective_requires_owner(self) -> None:
        state = base_state()
        del state["objectives"][0]["owner_thread_id"]
        with self.assertRaisesRegex(StateError, "missing keys"):
            validate_state(state)

    def test_delegated_owner_must_match_active_role(self) -> None:
        state = base_state()
        state["objectives"][0]["owner_state"] = "ACTIVE"
        with self.assertRaisesRegex(StateError, "does not match managed role"):
            validate_state(state)

    def test_managed_role_title_prefix_must_match_role(self) -> None:
        state = base_state()
        state["managed_roles"][0]["title"] = "Audit · Candidate One · WAITING_EXTERNAL"
        with self.assertRaisesRegex(StateError, "title role does not match role"):
            validate_state(state)

    def test_blocked_objective_requires_reopening_observer_trigger(self) -> None:
        state = base_state()
        objective = state["objectives"][0]
        objective["candidate_state"] = "BLOCKED"
        objective["lifecycle"] = "BLOCKED"
        for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
            objective.pop(key)
        objective["blocker"] = {"reopening_fact": "FACT", "observer": "OWNER"}
        with self.assertRaisesRegex(StateError, "missing keys"):
            validate_state(state)

    def test_blocked_candidate_requires_reopening_observer_trigger(self) -> None:
        state = base_state()
        objective = state["objectives"][0]
        objective["candidate_state"] = "BLOCKED"
        objective["lifecycle"] = "BLOCKED"
        for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
            objective.pop(key)
        with self.assertRaisesRegex(StateError, "blocker must be an object"):
            validate_state(state)

    def test_valid_blocker_must_be_external_and_finite(self) -> None:
        state = base_state()
        objective = state["objectives"][0]
        objective.update({"candidate_state": "BLOCKED", "lifecycle": "BLOCKED"})
        for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
            objective.pop(key)
        objective["blocker"] = {
            "kind": "INTERNAL_ENGINEERING",
            "reopening_fact": "External service recovers.",
            "observer": "Controller",
            "trigger": "SERVICE_RECOVERED",
            "next_check_at": None,
            "resolution_deadline": "2026-08-06T00:00:00Z",
        }
        with self.assertRaisesRegex(StateError, "blocker.kind"):
            validate_state(state)
        objective["blocker"]["kind"] = "EXTERNAL_FACT"
        self.assertIs(validate_state(state), state)

    def test_open_done_archive_is_invalid(self) -> None:
        state = base_state()
        objective = state["objectives"][0]
        objective.update({"lifecycle": "DONE", "reopening_fact": "A later witness appears."})
        for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
            objective.pop(key)
        with self.assertRaisesRegex(StateError, "OPEN/DONE is invalid"):
            validate_state(state)

    def test_engineering_failure_cannot_close_candidate(self) -> None:
        state = base_state()
        objective = state["objectives"][0]
        objective.update(
            {
                "candidate_state": "CLOSED",
                "lifecycle": "DONE",
                "reopening_fact": "A repaired implementation becomes available.",
                "idea_closure": {
                    "basis": "ENGINEERING_INVALID",
                    "scope": "exact cell",
                    "evidence_ref": "terminal-1",
                    "reopening_fact": "A repaired implementation becomes available.",
                },
            }
        )
        for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
            objective.pop(key)
        with self.assertRaisesRegex(StateError, "basis must be one of"):
            validate_state(state)

    def test_valid_scientific_negative_requires_eligibility_power_and_audit(self) -> None:
        state = base_state()
        objective = state["objectives"][0]
        objective.update(
            {
                "candidate_state": "CLOSED",
                "lifecycle": "DONE",
                "reopening_fact": "A new prospectively distinct estimand is frozen.",
                "idea_closure": {
                    "basis": "VALID_SCIENTIFIC_NEGATIVE",
                    "scope": "frozen exact estimand",
                    "evidence_ref": "terminal-1",
                    "reopening_fact": "A new prospectively distinct estimand is frozen.",
                    "independent_audit_terminal_id": "audit-1",
                    "evidence_eligible": True,
                    "prospective_action_table_pass": True,
                    "power_or_futility_pass": False,
                },
            }
        )
        for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
            objective.pop(key)
        with self.assertRaisesRegex(StateError, "power_or_futility_pass must be true"):
            validate_state(state)
        objective["idea_closure"]["power_or_futility_pass"] = True
        self.assertIs(validate_state(state), state)

    def test_scoped_mpe_failure_is_not_encoded_as_powered_negative(self) -> None:
        state = base_state()
        objective = state["objectives"][0]
        objective.update(
            {
                "candidate_state": "CLOSED",
                "lifecycle": "DONE",
                "idea_closure": {
                    "basis": "PROSPECTIVE_SCOPED_MPE_FAILURE",
                    "scope": "exact finite Scout cell",
                    "evidence_ref": "terminal-1",
                    "reopening_fact": "A distinct prospective estimand is frozen.",
                    "independent_audit_terminal_id": "audit-1",
                    "evidence_eligible": True,
                    "prospective_action_table_pass": True,
                    "finite_cell_complete": True,
                    "preregistered_mpe_failure": True,
                    "scope_boundary_preserved": True,
                    "adversarial_review_pass": True,
                    "powered_negative_claimed": True,
                },
            }
        )
        for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
            objective.pop(key)
        with self.assertRaisesRegex(StateError, "powered_negative_claimed must be false"):
            validate_state(state)
        objective["idea_closure"]["powered_negative_claimed"] = False
        self.assertIs(validate_state(state), state)

    def test_external_impossibility_reason_is_allowlisted(self) -> None:
        state = base_state()
        objective = state["objectives"][0]
        objective.update(
            {
                "candidate_state": "CLOSED",
                "lifecycle": "DONE",
                "reopening_fact": "Required data becomes lawfully available.",
                "idea_closure": {
                    "basis": "EXTERNAL_IMPOSSIBILITY",
                    "scope": "frozen exact carrier",
                    "evidence_ref": "audit-1",
                    "reopening_fact": "Required data becomes lawfully available.",
                    "reason_code": "IMPLEMENTATION_BUG",
                    "observer": "Controller",
                    "trigger": "Required data is released.",
                    "unavoidable": True,
                },
            }
        )
        for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
            objective.pop(key)
        with self.assertRaisesRegex(StateError, "not an allowed external impossibility"):
            validate_state(state)
        objective["idea_closure"]["reason_code"] = "DATA_UNAVAILABLE"
        self.assertIs(validate_state(state), state)

    def test_checksum_tampering_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            state = json.loads(path.read_text(encoding="utf-8"))
            state["controller"]["title"] = "Controller · Changed · ACTIVE"
            path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "checksum mismatch"):
                read_state(path)

    def test_job_wake_state_is_fail_closed(self) -> None:
        state = base_state()
        state["remote_jobs"][0]["wake_delivery"] = {
            "state": "CLAIMED",
            "claim_token": None,
            "observation_id": "obs-1",
        }
        with self.assertRaisesRegex(StateError, "claimed identifiers"):
            validate_state(state)

    def test_advisory_read_is_minimal_and_scientific_owner_bound(self) -> None:
        state = base_state()
        state["advisory_reads"] = [advisory_record()]
        self.assertIs(validate_state(state), state)

        state["advisory_reads"][0]["reader_role"] = "Controller"
        with self.assertRaisesRegex(StateError, "reader_role must be Explorer or Audit"):
            validate_state(state)

    def test_explicit_advisory_batch_modes_are_bounded(self) -> None:
        state = base_state()
        advisory = advisory_record(advisory_id="advisory-nonblocking-1")
        state["advisory_reads"] = [advisory]
        self.assertIs(validate_state(state), state)

        advisory["blocking_gate_id"] = "SHOULD_NOT_BLOCK"
        with self.assertRaisesRegex(StateError, "must be null for NON_BLOCKING"):
            validate_state(state)

        advisory.update(
            {
                "batch_mode": "BLOCKING_HIGH_RISK",
                "decision_gate": "BLOCKING_HIGH_RISK",
                "blocking_gate_id": "DURABLE_HIGH_RISK_CLOSE",
                "reader_thread_id": "worker-1",
            }
        )
        state["objectives"][0].update({"owner_role": "Audit", "owner_state": "ACTIVE"})
        state["managed_roles"][0].update(
            {"role": "Audit", "title": "Audit · Candidate One · ACTIVE", "state": "ACTIVE"}
        )
        state["objectives"][0]["advisory_blocking_gate"] = {
            "blocking_gate_id": "DURABLE_HIGH_RISK_CLOSE",
            "transition": "CLOSE_OBJECTIVE",
            "target_stage": "SCOPED_CLOSE",
            "authority_ref": "terminal://prospective-close-gate",
        }
        self.assertIs(validate_state(state), state)
        advisory["reader_thread_id"] = "audit-thread-1"
        with self.assertRaisesRegex(StateError, "blocking reader must be the current scientific owner"):
            validate_state(state)

    def test_advisory_channel_has_one_inflight_batch_and_rejects_duplicate_scope(self) -> None:
        state = audit_owner_state()
        first = advisory_record(scope_sha256="b" * 64)
        second = dict(first, advisory_id="advisory-2")
        state["advisory_reads"] = [first, second]
        with self.assertRaisesRegex(StateError, "already has an in-flight advisory batch"):
            validate_state(state)

        second["conversation_thread_id"] = "pro-thread-2"
        with self.assertRaisesRegex(StateError, "duplicates an in-flight advisory scope"):
            validate_state(state)

        second["scope_revision"] = 2
        with self.assertRaisesRegex(StateError, "duplicates an in-flight advisory scope"):
            validate_state(state)

    def test_legacy_advisory_cannot_be_validated_or_written(self) -> None:
        state = base_state()
        legacy = advisory_record()
        for key in ("scope_revision", "scope_sha256", "batch_mode", "blocking_gate_id"):
            legacy.pop(key)
        legacy["decision_gate"] = "BEFORE_NEXT_SCIENTIFIC_ROUTE_DECISION"
        state["advisory_reads"] = [legacy]
        with self.assertRaisesRegex(StateError, "missing keys"):
            validate_state(state)

        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "missing keys"):
                cmd_replace(
                    type(
                        "Args",
                        (),
                        {"state": str(path), "input": str(candidate_path), "expected_revision": 0},
                    )()
                )

            fabricated = base_state()
            fabricated["advisory_reads"] = [
                advisory_record(
                    submitted_at=None,
                    submitted_thread_updated_at=None,
                    monitor_state="RESPONSE_OBSERVED",
                    observed_thread_updated_at=101,
                    wake_delivery={
                        "state": "SENT",
                        "claim_token": "fabricated-claim",
                        "observation_id": "fabricated-observation",
                    },
                )
            ]
            candidate_path.write_text(json.dumps(fabricated), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "new advisory must start AWAITING_RESPONSE"):
                cmd_replace(
                    type(
                        "Args",
                        (),
                        {"state": str(path), "input": str(candidate_path), "expected_revision": 0},
                    )()
                )

    def test_generic_replace_cannot_claim_advisory(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["advisory_reads"] = [advisory_record()]
            write_state(path, state, -1)

            fabricated = read_state(path)
            advisory = fabricated["advisory_reads"][0]
            advisory["monitor_state"] = "RESPONSE_OBSERVED"
            advisory["observed_thread_updated_at"] = 101
            advisory["wake_delivery"] = {
                "state": "CLAIMED",
                "claim_token": "fabricated-claim",
                "observation_id": "fabricated-observation",
            }
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(fabricated), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "only by claim-advisory-wake"):
                cmd_replace(
                    type(
                        "Args",
                        (),
                        {"state": str(path), "input": str(candidate_path), "expected_revision": 0},
                    )()
                )
            self.assertEqual(read_state(path)["advisory_reads"][0]["monitor_state"], "AWAITING_RESPONSE")

    def test_generic_replace_cannot_complete_advisory(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["advisory_reads"] = [advisory_record()]
            write_state(path, state, -1)
            cmd_claim_advisory(
                type(
                    "Args",
                    (),
                    {
                        "state": str(path),
                        "advisory_id": "advisory-1",
                        "expected_revision": 0,
                        "claim_token": "claim-1",
                        "observation_id": "observation-1",
                        "observed_thread_updated_at": 101,
                    },
                )()
            )

            fabricated = read_state(path)
            fabricated["advisory_reads"][0]["wake_delivery"]["state"] = "SENT"
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(fabricated), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "only by complete-advisory-wake"):
                cmd_replace(
                    type(
                        "Args",
                        (),
                        {"state": str(path), "input": str(candidate_path), "expected_revision": 1},
                    )()
                )
            self.assertEqual(
                read_state(path)["advisory_reads"][0]["wake_delivery"]["state"],
                "CLAIMED",
            )

    def test_initial_write_cannot_seed_observed_sent_advisory(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["advisory_reads"] = [
                advisory_record(
                    monitor_state="RESPONSE_OBSERVED",
                    observed_thread_updated_at=101,
                    wake_delivery={
                        "state": "SENT",
                        "claim_token": "fabricated-claim",
                        "observation_id": "fabricated-observation",
                    },
                )
            ]
            with self.assertRaisesRegex(StateError, "new advisory must start AWAITING_RESPONSE"):
                write_state(path, state, -1)
            self.assertFalse(path.exists())

    def test_high_risk_gate_cannot_clear_after_generic_fabricated_delivery(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            initial = audit_owner_state()
            set_terminal_binding(initial, path, "TERM-CLOSE-1")
            write_state(path, initial, -1)
            gated = read_state(path)
            gated["objectives"][0]["advisory_blocking_gate"] = {
                "blocking_gate_id": "GATE-CLOSE-1",
                "transition": "CLOSE_OBJECTIVE",
                "target_stage": "SCOPED_CLOSE",
                "authority_ref": "terminal://prospective-close-gate",
            }
            write_state(path, gated, 0)
            awaiting = read_state(path)
            awaiting["advisory_reads"] = [
                advisory_record(
                    reader_thread_id="worker-1",
                    batch_mode="BLOCKING_HIGH_RISK",
                    decision_gate="BLOCKING_HIGH_RISK",
                    blocking_gate_id="GATE-CLOSE-1",
                    scope_sha256="f" * 64,
                )
            ]
            write_state(path, awaiting, 1)

            fabricated = read_state(path)
            advisory = fabricated["advisory_reads"][0]
            advisory["monitor_state"] = "RESPONSE_OBSERVED"
            advisory["observed_thread_updated_at"] = 101
            advisory["wake_delivery"] = {
                "state": "CLAIMED",
                "claim_token": "fabricated-claim",
                "observation_id": "fabricated-observation",
            }
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(fabricated), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "only by claim-advisory-wake"):
                cmd_replace(
                    type(
                        "Args",
                        (),
                        {"state": str(path), "input": str(candidate_path), "expected_revision": 2},
                    )()
                )
            verified_revision = observe_and_verify(path, 2)
            with self.assertRaisesRegex(StateError, "is not observed with SENT delivery"):
                cmd_close_objective(
                    close_args(
                        path,
                        expected_revision=verified_revision,
                        clear_advisory_id=["advisory-1"],
                    )
                )

    def test_blocking_gate_must_preexist_and_is_unique(self) -> None:
        state = audit_owner_state()
        state["objectives"][0]["advisory_blocking_gate"] = {
            "blocking_gate_id": "GATE-X",
            "transition": "CLOSE_OBJECTIVE",
            "target_stage": "SCOPED_CLOSE",
            "authority_ref": "terminal://gate-x",
        }
        first = advisory_record(
            batch_mode="BLOCKING_HIGH_RISK",
            decision_gate="BLOCKING_HIGH_RISK",
            blocking_gate_id="GATE-X",
            scope_sha256="b" * 64,
            reader_thread_id="worker-1",
        )
        second = advisory_record(
            advisory_id="advisory-2",
            conversation_thread_id="pro-thread-2",
            batch_mode="BLOCKING_HIGH_RISK",
            decision_gate="BLOCKING_HIGH_RISK",
            blocking_gate_id="GATE-X",
            scope_sha256="c" * 64,
            reader_thread_id="worker-1",
        )
        state["advisory_reads"] = [first, second]
        with self.assertRaisesRegex(StateError, "duplicates an active blocking gate"):
            validate_state(state)

        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, audit_owner_state(), -1)
            simultaneous = read_state(path)
            simultaneous["objectives"][0]["advisory_blocking_gate"] = state["objectives"][0][
                "advisory_blocking_gate"
            ]
            simultaneous["advisory_reads"] = [first]
            with self.assertRaisesRegex(StateError, "gate bound in the previous state"):
                write_state(path, simultaneous, 0)

            prebound = read_state(path)
            prebound["objectives"][0]["advisory_blocking_gate"] = state["objectives"][0][
                "advisory_blocking_gate"
            ]
            write_state(path, prebound, 0)
            removable = read_state(path)
            removable["objectives"][0].pop("advisory_blocking_gate")
            candidate_path = Path(tmp) / "remove-gate.json"
            candidate_path.write_text(json.dumps(removable), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "cannot change or remove blocking gate"):
                cmd_replace(
                    type(
                        "Args",
                        (),
                        {"state": str(path), "input": str(candidate_path), "expected_revision": 1},
                    )()
                )

    def test_absorbed_scope_cannot_be_resubmitted_with_new_revision(self) -> None:
        state = base_state()
        state["absorbed_terminal_event_ids"] = ["TERM-LOCAL-1"]
        state["absorbed_advisory_scopes"] = [
            {
                "candidate_id": "candidate-1",
                "scope_sha256": "d" * 64,
                "local_validation_terminal_event_id": "TERM-LOCAL-1",
            }
        ]
        state["advisory_reads"] = [advisory_record(scope_revision=99, scope_sha256="d" * 64)]
        with self.assertRaisesRegex(StateError, "repeats an absorbed advisory scope"):
            validate_state(state)

    def test_generic_replace_cannot_rebind_owner_or_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            candidate = read_state(path)
            candidate["objectives"][0]["owner_thread_id"] = "worker-2"
            candidate["managed_roles"][0].update(
                {
                    "thread_id": "worker-2",
                    "title": "Executor · Candidate One · WAITING_EXTERNAL",
                }
            )
            candidate["remote_jobs"][0]["owner_thread_id"] = "worker-2"
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "generic replacement cannot change owner/lifecycle"):
                cmd_replace(
                    type(
                        "Args",
                        (),
                        {"state": str(path), "input": str(candidate_path), "expected_revision": 0},
                    )()
                )
            self.assertEqual(read_state(path)["objectives"][0]["owner_thread_id"], "worker-1")

    def test_validate_state_rejects_duplicate_delegated_owner_thread(self) -> None:
        state = base_state()
        duplicate = dict(state["objectives"][0])
        duplicate.update(
            {
                "objective_id": "objective-2",
                "candidate_id": "candidate-2",
                "stage": "R1_IMPLEMENTATION",
                "next_action": "WAIT_SECOND_TERMINAL",
            }
        )
        state["objectives"].append(duplicate)
        with self.assertRaisesRegex(StateError, "duplicate delegated owner_thread_id worker-1"):
            validate_state(state)

    def test_reconcile_open_cannot_assign_blocked_objective_to_existing_delegated_owner(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["objectives"].append(
                {
                    "objective_id": "objective-2",
                    "candidate_id": "candidate-2",
                    "candidate_state": "BLOCKED",
                    "stage": "WAIT_EXTERNAL",
                    "scientific_outcome": "UNOBSERVED",
                    "lifecycle": "BLOCKED",
                    "next_action": "CHECK_EXTERNAL_FACT",
                    "blocker": {
                        "kind": "EXTERNAL_FACT",
                        "reopening_fact": "A required external artifact becomes available.",
                        "observer": "Controller",
                        "trigger": "ARTIFACT_AVAILABLE",
                        "next_check_at": "2026-08-06T00:00:00Z",
                        "resolution_deadline": "2026-08-07T00:00:00Z",
                    },
                }
            )
            write_state(path, state, -1)
            transitions = [
                {
                    "objective_id": "objective-2",
                    "new_objective_id": "objective-2",
                    "stage": "R1_IMPLEMENTATION",
                    "scientific_outcome": "UNOBSERVED",
                    "next_action": "WAIT_SECOND_TERMINAL",
                    "owner_thread_id": "worker-1",
                    "owner_role": "Executor",
                    "owner_state": "WAITING_EXTERNAL",
                    "owner_title": "Executor · Candidate One · WAITING_EXTERNAL",
                    "cursor": None,
                    "recovery_evidence_ref": "terminal://artifact-available-proof",
                    "completion_binding": completion_binding(
                        str(Path(tmp) / "recovered-terminal.json"), "recovered"
                    ),
                }
            ]
            with self.assertRaisesRegex(StateError, "duplicate delegated owner_thread_id worker-1"):
                cmd_reconcile_open(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 0,
                            "transitions_json": json.dumps(transitions),
                            "remote_jobs_json": json.dumps(state["remote_jobs"]),
                        },
                    )()
                )
            unchanged = read_state(path)
            self.assertEqual(unchanged["revision"], 0)
            blocked = next(item for item in unchanged["objectives"] if item["objective_id"] == "objective-2")
            self.assertEqual(blocked["lifecycle"], "BLOCKED")

    def test_v4_reconcile_open_cannot_rebind_a_delegated_owner(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            transitions = [
                {
                    "objective_id": "objective-1",
                    "new_objective_id": "objective-1",
                    "stage": "AUDIT_ACTIVE",
                    "scientific_outcome": "UNOBSERVED",
                    "next_action": "WAIT_AUDIT_TERMINAL",
                    "owner_thread_id": "audit-1",
                    "owner_role": "Audit",
                    "owner_state": "ACTIVE",
                    "owner_title": "Audit · Candidate One · ACTIVE",
                    "cursor": None,
                    "recovery_evidence_ref": "terminal://recovery-proof",
                    "completion_binding": completion_binding(
                        str(Path(tmp) / "recovered-terminal.json"), "recovered"
                    ),
                }
            ]
            with self.assertRaisesRegex(StateError, "may only reopen a BLOCKED objective"):
                cmd_reconcile_open(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 0,
                            "transitions_json": json.dumps(transitions),
                            "remote_jobs_json": "[]",
                        },
                    )()
                )

    def test_v4_reconcile_open_requires_and_records_recovery_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            objective = state["objectives"][0]
            objective.update(
                {
                    "candidate_state": "BLOCKED",
                    "stage": "WAIT_EXTERNAL",
                    "lifecycle": "BLOCKED",
                    "next_action": "CHECK_EXTERNAL_FACT",
                    "blocker": {
                        "kind": "EXTERNAL_FACT",
                        "reopening_fact": "A required external artifact becomes available.",
                        "observer": "Controller",
                        "trigger": "ARTIFACT_AVAILABLE",
                        "next_check_at": "2026-08-06T00:00:00Z",
                        "resolution_deadline": "2026-08-07T00:00:00Z",
                    },
                }
            )
            for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
                objective.pop(key)
            state["managed_roles"] = []
            state["remote_jobs"] = []
            write_state(path, state, -1)
            transitions = [
                {
                    "objective_id": "objective-1",
                    "new_objective_id": "objective-1",
                    "stage": "AUDIT_ACTIVE",
                    "scientific_outcome": "UNOBSERVED",
                    "next_action": "WAIT_AUDIT_TERMINAL",
                    "owner_thread_id": "audit-1",
                    "owner_role": "Audit",
                    "owner_state": "ACTIVE",
                    "owner_title": "Audit · Candidate One · ACTIVE",
                    "cursor": None,
                    "recovery_evidence_ref": "terminal://artifact-available-proof",
                    "completion_binding": completion_binding(
                        str(Path(tmp) / "recovered-terminal.json"), "recovered"
                    ),
                }
            ]
            cmd_reconcile_open(
                type(
                    "Args",
                    (),
                    {
                        "state": str(path),
                        "expected_revision": 0,
                        "transitions_json": json.dumps(transitions),
                        "remote_jobs_json": "[]",
                    },
                )()
            )
            reopened = read_state(path)["objectives"][0]
            self.assertEqual(reopened["owner_thread_id"], "audit-1")
            self.assertEqual(
                reopened["owner_recovery_evidence_ref"], "terminal://artifact-available-proof"
            )

    def test_nonblocking_advisory_does_not_block_scoped_close(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["remote_jobs"] = []
            state["advisory_reads"] = [
                advisory_record(reader_thread_id="worker-1", scope_sha256="e" * 64)
            ]
            revision = write_and_verify(path, state, "TERM-CLOSE-1")
            cmd_close_objective(close_args(path, expected_revision=revision))
            closed = read_state(path)
            self.assertEqual(closed["objectives"][0]["lifecycle"], "DONE")
            self.assertEqual([item["advisory_id"] for item in closed["advisory_reads"]], ["advisory-1"])

    def test_blocking_advisory_enforces_exact_gate_until_local_absorption(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            initial = audit_owner_state()
            set_terminal_binding(initial, path, "TERM-CLOSE-1")
            write_state(path, initial, -1)

            gated = read_state(path)
            gated["objectives"][0]["advisory_blocking_gate"] = {
                "blocking_gate_id": "GATE-CLOSE-1",
                "transition": "CLOSE_OBJECTIVE",
                "target_stage": "SCOPED_CLOSE",
                "authority_ref": "terminal://prospective-close-gate",
            }
            write_state(path, gated, 0)

            awaiting = read_state(path)
            awaiting["advisory_reads"] = [
                advisory_record(
                    reader_thread_id="worker-1",
                    batch_mode="BLOCKING_HIGH_RISK",
                    decision_gate="BLOCKING_HIGH_RISK",
                    blocking_gate_id="GATE-CLOSE-1",
                    scope_sha256="f" * 64,
                )
            ]
            write_state(path, awaiting, 1)
            verified_revision = observe_and_verify(path, 2)

            with self.assertRaisesRegex(StateError, "exact blocking gate requires one"):
                cmd_close_objective(close_args(path, expected_revision=verified_revision))
            with self.assertRaisesRegex(StateError, "is not observed with SENT delivery"):
                cmd_close_objective(
                    close_args(
                        path,
                        expected_revision=verified_revision,
                        clear_advisory_id=["advisory-1"],
                    )
                )

            cmd_claim_advisory(
                type(
                    "Args",
                    (),
                    {
                        "state": str(path),
                        "advisory_id": "advisory-1",
                        "expected_revision": verified_revision,
                        "claim_token": "claim-close-1",
                        "observation_id": "observation-close-1",
                        "observed_thread_updated_at": 101,
                    },
                )()
            )
            cmd_complete_advisory(
                type(
                    "Args",
                    (),
                    {
                        "state": str(path),
                        "advisory_id": "advisory-1",
                        "expected_revision": verified_revision + 1,
                        "claim_token": "claim-close-1",
                    },
                )()
            )
            cmd_close_objective(
                close_args(
                    path,
                    expected_revision=verified_revision + 2,
                    clear_advisory_id=["advisory-1"],
                )
            )
            closed = read_state(path)
            self.assertEqual(closed["advisory_reads"], [])
            self.assertNotIn("advisory_blocking_gate", closed["objectives"][0])
            self.assertEqual(
                closed["absorbed_advisory_scopes"],
                [
                    {
                        "candidate_id": "candidate-1",
                        "scope_sha256": "f" * 64,
                        "local_validation_terminal_event_id": "TERM-CLOSE-1",
                    }
                ],
            )

    def test_advisory_response_wake_is_exactly_once_cas(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["advisory_reads"] = [advisory_record()]
            write_state(path, state, -1)
            with self.assertRaisesRegex(StateError, "is not observed with SENT delivery"):
                cmd_absorb_nonblocking_advisory(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "advisory_id": "advisory-1",
                            "expected_revision": 0,
                            "local_validation_terminal_event_id": "TERM-PRO-EARLY",
                        },
                    )()
                )
            claim = type("Args", (), {
                "state": str(path),
                "advisory_id": "advisory-1",
                "expected_revision": 0,
                "claim_token": "claim-1",
                "observation_id": "obs-1",
                "observed_thread_updated_at": 101,
            })()
            cmd_claim_advisory(claim)
            observed = read_state(path)["advisory_reads"][0]
            self.assertEqual(observed["monitor_state"], "RESPONSE_OBSERVED")
            self.assertEqual(observed["wake_delivery"]["state"], "CLAIMED")

            with self.assertRaisesRegex(StateError, "already RESPONSE_OBSERVED"):
                cmd_claim_advisory(type("Args", (), {
                    "state": str(path),
                    "advisory_id": "advisory-1",
                    "expected_revision": 1,
                    "claim_token": "claim-2",
                    "observation_id": "obs-2",
                    "observed_thread_updated_at": 102,
                })())

            complete = type("Args", (), {
                "state": str(path),
                "advisory_id": "advisory-1",
                "expected_revision": 1,
                "claim_token": "claim-1",
            })()
            cmd_complete_advisory(complete)
            self.assertEqual(read_state(path)["advisory_reads"][0]["wake_delivery"]["state"], "SENT")

            cmd_absorb_nonblocking_advisory(
                type(
                    "Args",
                    (),
                    {
                        "state": str(path),
                        "advisory_id": "advisory-1",
                        "expected_revision": 2,
                        "local_validation_terminal_event_id": "TERM-PRO-LOCAL-1",
                    },
                )()
            )
            absorbed = read_state(path)
            self.assertEqual(absorbed["advisory_reads"], [])
            self.assertIn("TERM-PRO-LOCAL-1", absorbed["absorbed_terminal_event_ids"])
            self.assertEqual(
                absorbed["absorbed_advisory_scopes"][0]["local_validation_terminal_event_id"],
                "TERM-PRO-LOCAL-1",
            )

    def test_already_observed_advisory_can_bind_reader_without_fabricated_baseline(self) -> None:
        state = base_state()
        state["advisory_reads"] = [
            advisory_record(
                advisory_id="advisory-ready-1",
                submitted_at=None,
                submitted_thread_updated_at=None,
                not_before="2026-08-05T00:00:00Z",
                monitor_state="RESPONSE_OBSERVED",
                observed_thread_updated_at=101.5,
                wake_delivery={"state": "SENT", "claim_token": "direct-1", "observation_id": "obs-1"},
            )
        ]
        self.assertIs(validate_state(state), state)

    def test_v2_migration_requires_checksum_and_writes_v5(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            legacy = base_state()
            legacy["schema_version"] = 2
            legacy.pop("advisory_reads")
            data = canonical_bytes(legacy)
            path.write_bytes(data)
            checksum_path(path).write_text(
                f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
                encoding="utf-8",
            )
            candidate = base_state()
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            cmd_migrate_v2(type("Args", (), {
                "state": str(path),
                "input": str(candidate_path),
                "expected_revision": 0,
            })())
            migrated = read_state(path)
            self.assertEqual(migrated["schema_version"], 5)
            self.assertEqual(migrated["revision"], 1)
            self.assertEqual(migrated["advisory_reads"], [])

    def test_v3_migration_requires_explicit_v5_candidate(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            legacy = base_state()
            legacy["schema_version"] = 3
            data = canonical_bytes(legacy)
            path.write_bytes(data)
            checksum_path(path).write_text(
                f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
                encoding="utf-8",
            )
            candidate = base_state()
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            cmd_migrate_v3(type("Args", (), {
                "state": str(path),
                "input": str(candidate_path),
                "expected_revision": 0,
            })())
            migrated = read_state(path)
            self.assertEqual(migrated["schema_version"], 5)
            self.assertEqual(migrated["revision"], 1)

    def test_v3_migration_cannot_upgrade_legacy_advisory_into_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            legacy = base_state()
            legacy["schema_version"] = 3
            legacy_advisory = advisory_record()
            for key in ("scope_revision", "scope_sha256", "batch_mode", "blocking_gate_id"):
                legacy_advisory.pop(key)
            legacy_advisory["decision_gate"] = "BEFORE_NEXT_SCIENTIFIC_ROUTE_DECISION"
            legacy["advisory_reads"] = [legacy_advisory]
            data = canonical_bytes(legacy)
            path.write_bytes(data)
            checksum_path(path).write_text(
                f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
                encoding="utf-8",
            )
            candidate = base_state()
            candidate["advisory_reads"] = [advisory_record()]
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            with self.assertRaisesRegex(StateError, "legacy advisory obligations cannot be migrated"):
                cmd_migrate_v3(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "input": str(candidate_path),
                            "expected_revision": 0,
                        },
                    )()
                )

    def test_remote_monitor_fields_are_allowlisted(self) -> None:
        state = base_state()
        state["remote_jobs"][0]["host"] = "unknown-host"
        with self.assertRaisesRegex(StateError, "host is not allowlisted"):
            validate_state(state)

        state = base_state()
        state["remote_jobs"][0]["output_path"] = "/tmp/untrusted"
        with self.assertRaisesRegex(StateError, "outside allowlisted roots"):
            validate_state(state)

        state = base_state()
        state["remote_jobs"][0]["expected_files"] = ["../terminal.json"]
        with self.assertRaisesRegex(StateError, "must be basenames"):
            validate_state(state)

    def test_cursor_advancement_is_bounded_and_compare_and_swap_bound(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            args = type("Args", (), {
                "state": str(path),
                "expected_revision": 0,
                "updates_json": json.dumps([
                    {
                        "thread_id": "worker-1",
                        "expected_cursor": None,
                        "new_cursor": "cursor:1",
                        "observation_kind": "NON_TERMINAL",
                        "source_turn_state": "IN_PROGRESS",
                    }
                ]),
            })()
            cmd_advance_cursors(args)
            self.assertEqual(read_state(path)["managed_roles"][0]["cursor"], "cursor:1")

            stale = type("Args", (), {
                "state": str(path),
                "expected_revision": 1,
                "updates_json": json.dumps([
                    {
                        "thread_id": "worker-1",
                        "expected_cursor": None,
                        "new_cursor": "cursor:2",
                        "observation_kind": "NON_TERMINAL",
                        "source_turn_state": "IN_PROGRESS",
                    }
                ]),
            })()
            with self.assertRaisesRegex(StateError, "expected_cursor does not match"):
                cmd_advance_cursors(stale)

    def test_cursor_must_not_cross_unabsorbed_terminal(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            args = type("Args", (), {
                "state": str(path),
                "expected_revision": 0,
                "updates_json": json.dumps([{
                    "thread_id": "worker-1",
                    "expected_cursor": None,
                    "new_cursor": "cursor:terminal",
                    "observation_kind": "TERMINAL",
                    "source_turn_state": "FINAL",
                    "terminal_event_id": "TERM-1",
                }]),
            })()
            with self.assertRaisesRegex(StateError, "is not absorbed"):
                cmd_advance_cursors(args)
            self.assertIsNone(read_state(path)["managed_roles"][0]["cursor"])

    def test_cursor_may_cross_already_absorbed_terminal(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["absorbed_terminal_event_ids"] = ["TERM-1"]
            write_state(path, state, -1)
            args = type("Args", (), {
                "state": str(path),
                "expected_revision": 0,
                "updates_json": json.dumps([{
                    "thread_id": "worker-1",
                    "expected_cursor": None,
                    "new_cursor": "cursor:terminal",
                    "observation_kind": "TERMINAL",
                    "source_turn_state": "FINAL",
                    "terminal_event_id": "TERM-1",
                }]),
            })()
            cmd_advance_cursors(args)
            self.assertEqual(read_state(path)["managed_roles"][0]["cursor"], "cursor:terminal")

    def test_executor_final_without_registered_job_requires_same_owner_recovery(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["objectives"][0]["owner_state"] = "ACTIVE"
            state["managed_roles"][0].update(
                {
                    "state": "ACTIVE",
                    "title": "Executor · Candidate One · ACTIVE",
                }
            )
            state["remote_jobs"] = []
            write_state(path, state, -1)
            args = type("Args", (), {
                "state": str(path),
                "expected_revision": 0,
                "updates_json": json.dumps([{
                    "thread_id": "worker-1",
                    "expected_cursor": None,
                    "new_cursor": "cursor:nonterminal-final",
                    "observation_kind": "NON_TERMINAL",
                    "source_turn_state": "FINAL",
                }]),
            })()
            output = io.StringIO()
            with redirect_stdout(output):
                cmd_advance_cursors(args)
            self.assertEqual(json.loads(output.getvalue())["status"], "RECOVERY_REQUIRED")
            recovered = read_state(path)
            self.assertIsNone(recovered["managed_roles"][0]["cursor"])
            self.assertTrue(
                recovered["objectives"][0]["next_action"].startswith(
                    "SAME_OWNER_TERMINAL_RECOVERY:v1:worker-1:cursor:nonterminal-final:"
                )
            )

            # Exact transient-authentication fast path: the same live owner and
            # PTY remain ordinary in-progress work, with no invented remote job.
            args.expected_revision = 1
            args.updates_json = json.dumps([{
                "thread_id": "worker-1",
                "expected_cursor": None,
                "new_cursor": "cursor:interactive-auth-in-progress",
                "observation_kind": "NON_TERMINAL",
                "source_turn_state": "IN_PROGRESS",
            }])
            cmd_advance_cursors(args)
            self.assertEqual(
                read_state(path)["managed_roles"][0]["cursor"],
                "cursor:interactive-auth-in-progress",
            )

    def test_executor_final_without_job_materializes_same_owner_recovery_idempotently(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["objectives"][0].update(
                {
                    "owner_state": "ACTIVE",
                    "executor_continuation_phase": "CARRIER_USED",
                }
            )
            state["managed_roles"][0].update(
                {
                    "state": "ACTIVE",
                    "title": "Executor · Candidate One · ACTIVE",
                }
            )
            state["remote_jobs"] = []
            write_state(path, state, -1)
            update = {
                "thread_id": "worker-1",
                "expected_cursor": None,
                "new_cursor": "cursor:final-recovery",
                "observation_kind": "NON_TERMINAL",
                "source_turn_state": "FINAL",
            }
            output = io.StringIO()
            with redirect_stdout(output):
                cmd_advance_cursors(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 0,
                            "updates_json": json.dumps([update]),
                        },
                    )()
                )
            first = read_state(path)
            first_payload = json.loads(output.getvalue())
            self.assertEqual(first_payload["status"], "RECOVERY_REQUIRED")
            self.assertEqual(first["revision"], 1)
            self.assertIsNone(first["managed_roles"][0]["cursor"])
            expected_next_action = (
                "SAME_OWNER_TERMINAL_RECOVERY:v1:worker-1:cursor:final-recovery:"
                "V0FJVF9URVJNSU5BTA"
            )
            self.assertEqual(first["objectives"][0]["next_action"], expected_next_action)
            self.assertEqual(first["objectives"][0]["executor_continuation_phase"], "CARRIER_USED")
            projection = active_state_projection(first)
            self.assertEqual(projection["objectives"][0]["next_action"], expected_next_action)

            replay = io.StringIO()
            with redirect_stdout(replay):
                cmd_advance_cursors(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 0,
                            "updates_json": json.dumps([update]),
                        },
                    )()
                )
            self.assertEqual(json.loads(replay.getvalue())["status"], "RECOVERY_REQUIRED")
            self.assertEqual(read_state(path), first)

            different = dict(update, new_cursor="cursor:final-recovery-other")
            with self.assertRaisesRegex(StateError, "cannot overwrite existing recovery"):
                cmd_advance_cursors(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 1,
                            "updates_json": json.dumps([different]),
                        },
                    )()
                )
            self.assertEqual(read_state(path), first)

    def test_executor_final_recovery_batch_returns_every_same_owner_recovery(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["objectives"][0].update(
                {
                    "owner_state": "ACTIVE",
                    "completion_binding": completion_binding(
                        "/private/tmp/TERM-RECOVERY-BATCH-1.json", "batch-1"
                    ),
                }
            )
            state["managed_roles"][0].update(
                {
                    "state": "ACTIVE",
                    "title": "Executor · Candidate One · ACTIVE",
                }
            )
            state["objectives"].append(
                {
                    "objective_id": "objective-batch-2",
                    "candidate_id": "candidate-batch-2",
                    "candidate_state": "OPEN",
                    "stage": "R2_SCOUT",
                    "scientific_outcome": "UNOBSERVED",
                    "lifecycle": "DELEGATED",
                    "next_action": "WAIT_TERMINAL",
                    "owner_thread_id": "worker-batch-2",
                    "owner_role": "Executor",
                    "owner_state": "ACTIVE",
                    "completion_binding": completion_binding(
                        "/private/tmp/TERM-RECOVERY-BATCH-2.json", "batch-2"
                    ),
                }
            )
            state["managed_roles"].append(
                {
                    "thread_id": "worker-batch-2",
                    "role": "Executor",
                    "title": "Executor · Candidate Batch Two · ACTIVE",
                    "state": "ACTIVE",
                    "pin_required": True,
                    "cursor": None,
                }
            )
            state["remote_jobs"] = []
            write_state(path, state, -1)
            updates = [
                {
                    "thread_id": "worker-1",
                    "expected_cursor": None,
                    "new_cursor": "cursor:batch-final-1",
                    "observation_kind": "NON_TERMINAL",
                    "source_turn_state": "FINAL",
                },
                {
                    "thread_id": "worker-batch-2",
                    "expected_cursor": None,
                    "new_cursor": "cursor:batch-final-2",
                    "observation_kind": "NON_TERMINAL",
                    "source_turn_state": "FINAL",
                },
            ]
            output = io.StringIO()
            with redirect_stdout(output):
                cmd_advance_cursors(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 0,
                            "updates_json": json.dumps(updates),
                        },
                    )()
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["status"], "RECOVERY_REQUIRED")
            self.assertEqual(len(payload["recoveries"]), 2)
            self.assertNotIn("owner_thread_id", payload)
            recovered = read_state(path)
            self.assertEqual(recovered["revision"], 1)
            self.assertEqual(
                [role["cursor"] for role in recovered["managed_roles"]],
                [None, None],
            )
            self.assertTrue(
                recovered["objectives"][0]["next_action"].startswith(
                    "SAME_OWNER_TERMINAL_RECOVERY:v1:worker-1:cursor:batch-final-1:"
                )
            )
            self.assertTrue(
                recovered["objectives"][1]["next_action"].startswith(
                    "SAME_OWNER_TERMINAL_RECOVERY:v1:worker-batch-2:cursor:batch-final-2:"
                )
            )

    def test_executor_final_recovery_fails_closed_for_duplicate_jobs_terminal_or_malformed_action(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            path = directory / "controller-state.json"
            state = base_state(str(directory / "prebound-terminal.json"))
            state["objectives"][0]["owner_state"] = "ACTIVE"
            state["managed_roles"][0].update(
                {
                    "state": "ACTIVE",
                    "title": "Executor · Candidate One · ACTIVE",
                }
            )
            duplicate = remote_job(
                job_id="job-duplicate",
                objective_id="objective-1",
                owner_thread_id="worker-1",
            )
            state["remote_jobs"].append(duplicate)
            write_state(path, state, -1)
            update = {
                "thread_id": "worker-1",
                "expected_cursor": None,
                "new_cursor": "cursor:duplicate-job",
                "observation_kind": "NON_TERMINAL",
                "source_turn_state": "FINAL",
            }
            with self.assertRaisesRegex(StateError, "exactly one active registered remote job"):
                cmd_advance_cursors(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 0,
                            "updates_json": json.dumps([update]),
                        },
                    )()
                )
            self.assertEqual(read_state(path)["revision"], 0)

            terminal_state_path = directory / "terminal-state.json"
            terminal_state = base_state(str(directory / "prebound-terminal-present.json"))
            terminal_state["objectives"][0]["owner_state"] = "ACTIVE"
            terminal_state["managed_roles"][0].update(
                {
                    "state": "ACTIVE",
                    "title": "Executor · Candidate One · ACTIVE",
                }
            )
            terminal_state["remote_jobs"] = []
            write_state(terminal_state_path, terminal_state, -1)
            terminal_path = Path(
                terminal_state["objectives"][0]["completion_binding"]["terminal_path"]
            )
            terminal_path.write_bytes(
                canonical_bytes(
                    {
                        "completion_binding": terminal_state["objectives"][0][
                            "completion_binding"
                        ],
                        "startup_chain_authority": None,
                        "executor_continuation_phase": "NONE",
                    }
                )
            )
            terminal_path.chmod(0o444)
            try:
                with self.assertRaisesRegex(StateError, "matching terminal; observe-terminal first"):
                    cmd_advance_cursors(
                        type(
                            "Args",
                            (),
                            {
                                "state": str(terminal_state_path),
                                "expected_revision": 0,
                                "updates_json": json.dumps([update]),
                            },
                        )()
                    )
                self.assertEqual(read_state(terminal_state_path)["revision"], 0)
            finally:
                terminal_path.chmod(0o644)
                terminal_path.unlink()

            malformed_path = directory / "malformed-state.json"
            malformed_state = base_state(str(directory / "malformed-terminal.json"))
            malformed_state["objectives"][0]["owner_state"] = "ACTIVE"
            malformed_state["objectives"][0]["next_action"] = (
                "SAME_OWNER_TERMINAL_RECOVERY:v1:worker-1:cursor:bad:%%%"
            )
            malformed_state["managed_roles"][0].update(
                {
                    "state": "ACTIVE",
                    "title": "Executor · Candidate One · ACTIVE",
                }
            )
            malformed_state["remote_jobs"] = []
            write_state(malformed_path, malformed_state, -1)
            with self.assertRaisesRegex(StateError, "recovery is malformed"):
                cmd_advance_cursors(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(malformed_path),
                            "expected_revision": 0,
                            "updates_json": json.dumps([update]),
                        },
                    )()
                )
            self.assertEqual(read_state(malformed_path)["revision"], 0)

    def test_executor_final_recovery_does_not_bypass_matching_pending_absorption(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            path = directory / "pending-state.json"
            state = base_state(str(directory / "pending-terminal.json"))
            state["objectives"][0]["owner_state"] = "ACTIVE"
            state["managed_roles"][0].update(
                {
                    "state": "ACTIVE",
                    "title": "Executor · Candidate One · ACTIVE",
                }
            )
            state["remote_jobs"] = []
            write_state(path, state, -1)
            observe_and_verify(path, 0)
            update = {
                "thread_id": "worker-1",
                "expected_cursor": None,
                "new_cursor": "cursor:pending-final",
                "observation_kind": "NON_TERMINAL",
                "source_turn_state": "FINAL",
            }
            with self.assertRaisesRegex(StateError, "matching terminal pending absorption"):
                cmd_advance_cursors(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 2,
                            "updates_json": json.dumps([update]),
                        },
                    )()
                )
            pending_state = read_state(path)
            self.assertEqual(pending_state["revision"], 2)
            self.assertNotIn(
                "SAME_OWNER_TERMINAL_RECOVERY:v1",
                pending_state["objectives"][0]["next_action"],
            )

    def test_executor_final_may_wait_on_one_registered_active_remote_job(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            write_state(path, base_state(), -1)
            args = type("Args", (), {
                "state": str(path),
                "expected_revision": 0,
                "updates_json": json.dumps([{
                    "thread_id": "worker-1",
                    "expected_cursor": None,
                    "new_cursor": "cursor:waiting-job",
                    "observation_kind": "NON_TERMINAL",
                    "source_turn_state": "FINAL",
                }]),
            })()
            cmd_advance_cursors(args)
            self.assertEqual(
                read_state(path)["managed_roles"][0]["cursor"], "cursor:waiting-job"
            )

    def test_activate_successor_atomically_absorbs_and_reuses_owner(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            revision = write_and_verify(path, base_state(), "TERM-AUTHORITY-1")
            args = successor_args(state=str(path), expected_revision=revision)
            cmd_activate_successor(args)
            state = read_state(path)
            self.assertEqual(state["revision"], revision + 1)
            self.assertEqual(state["objectives"][0]["objective_id"], "objective-2")
            self.assertEqual(state["objectives"][0]["owner_thread_id"], "worker-1")
            self.assertEqual(state["managed_roles"][0]["thread_id"], "worker-1")
            self.assertEqual(state["remote_jobs"], [])
            self.assertNotIn("fresh_thread_reason", state["objectives"][0])
            self.assertIn("TERM-AUTHORITY-1", state["absorbed_terminal_event_ids"])

    def test_activate_successor_atomically_prebinds_one_remote_job(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["objectives"][0]["startup_chain_authority"] = sealed_startup_authority(
                Path(tmp), suffix="remote-job"
            )
            revision = write_and_verify(path, state, "TERM-AUTHORITY-1")
            job = remote_job()
            cmd_activate_successor(
                successor_args(
                    state=str(path),
                    expected_revision=revision,
                    executor_continuation_kind="CARRIER",
                    new_remote_job_json=json.dumps(job),
                )
            )
            self.assertEqual(read_state(path)["remote_jobs"], [job])

    def test_activate_successor_rejects_remote_job_for_wrong_owner(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["objectives"][0]["startup_chain_authority"] = sealed_startup_authority(
                Path(tmp), suffix="wrong-owner"
            )
            revision = write_and_verify(path, state, "TERM-AUTHORITY-1")
            job = remote_job(owner_thread_id="wrong-owner")
            with self.assertRaisesRegex(StateError, "remote job owner_thread_id mismatch"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        executor_continuation_kind="CARRIER",
                        new_remote_job_json=json.dumps(job),
                    )
                )
            self.assertEqual(read_state(path)["revision"], revision)

    def test_activate_successor_reuses_same_executor_without_fork_reason(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            revision = write_and_verify(path, base_state(), "TERM-AUTHORITY-1")
            args = successor_args(
                state=str(path),
                expected_revision=revision,
                new_owner_thread_id="worker-1",
                fresh_thread_reason=None,
            )
            cmd_activate_successor(args)
            state = read_state(path)
            self.assertEqual(state["objectives"][0]["owner_thread_id"], "worker-1")
            self.assertNotIn("fresh_thread_reason", state["objectives"][0])

    def test_activate_successor_rejects_unjustified_or_role_changing_fork(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            revision = write_and_verify(path, base_state(), "TERM-AUTHORITY-1")
            with self.assertRaisesRegex(StateError, "requires an allowlisted fresh_thread_reason"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path), expected_revision=revision, new_owner_thread_id="worker-2"
                    )
                )
            with self.assertRaisesRegex(StateError, "requires an allowlisted fresh_thread_reason"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        new_owner_thread_id="worker-2",
                        fresh_thread_reason="MODEL_SWITCH",
                        fresh_thread_evidence_ref="terminal://model-switch",
                    )
                )
            with self.assertRaisesRegex(StateError, "requires immutable fresh_thread_evidence_ref"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        new_owner_thread_id="worker-2",
                        fresh_thread_reason="VERIFIED_CONTEXT_ISOLATION_REQUIRED",
                    )
                )
            with self.assertRaisesRegex(StateError, "requires a canonical role change"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        new_owner_thread_id="worker-2",
                        fresh_thread_reason="WRITE_OWNERSHIP_TRANSFER",
                        fresh_thread_evidence_ref="terminal://ownership-transfer",
                    )
                )
            with self.assertRaisesRegex(StateError, "requires an Audit successor"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        new_owner_thread_id="worker-2",
                        fresh_thread_reason="PROTECTED_RESULT_INDEPENDENCE",
                        fresh_thread_evidence_ref="terminal://protected-independence",
                    )
                )
            with self.assertRaisesRegex(StateError, "must preserve the canonical role"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        new_owner_thread_id="worker-2",
                        new_owner_role="Audit",
                        executor_continuation_kind=None,
                        new_owner_title="Audit · Candidate Two · ACTIVE",
                        fresh_thread_reason="VERIFIED_CONTEXT_ISOLATION_REQUIRED",
                        fresh_thread_evidence_ref="terminal://context-rollover",
                    )
                )
            with self.assertRaisesRegex(StateError, "same-thread successor must preserve the canonical role"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        new_owner_thread_id="worker-1",
                        fresh_thread_reason=None,
                        new_owner_role="Audit",
                        executor_continuation_kind=None,
                        new_owner_title="Audit · Candidate Two · ACTIVE",
                    )
                )

    def test_activate_successor_allows_evidenced_same_role_context_rollover(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            state = base_state()
            state["objectives"][0]["startup_chain_authority"] = sealed_startup_authority(
                Path(tmp), suffix="context-rollover"
            )
            revision = write_and_verify(path, state, "TERM-AUTHORITY-1")
            cmd_activate_successor(
                successor_args(
                    state=str(path),
                    expected_revision=revision,
                    new_owner_thread_id="worker-2",
                    executor_continuation_kind="CARRIER",
                    fresh_thread_reason="VERIFIED_CONTEXT_ISOLATION_REQUIRED",
                    fresh_thread_evidence_ref="terminal://context-epoch-2",
                )
            )
            objective = read_state(path)["objectives"][0]
            self.assertEqual(objective["owner_thread_id"], "worker-2")
            self.assertEqual(objective["fresh_thread_evidence_ref"], "terminal://context-epoch-2")

    def test_successor_cannot_reuse_pending_or_absorbed_terminal_event_id(self) -> None:
        state = base_state()
        current_event = state["objectives"][0]["completion_binding"][
            "terminal_event_id"
        ]
        state["absorbed_terminal_event_ids"] = [current_event]
        with self.assertRaisesRegex(StateError, "already absorbed"):
            validate_state(state)

        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            path = directory / "controller-state.json"
            initial = base_state()
            initial["absorbed_terminal_event_ids"] = ["TERM-HISTORICAL"]
            revision = write_and_verify(path, initial, "TERM-NO-REUSE")
            before = read_state(path)
            reused_binding = completion_binding(
                str(directory / "future-successor-terminal.json"),
                "future",
            )
            reused_binding["terminal_event_id"] = "TERM-NO-REUSE"
            with self.assertRaisesRegex(StateError, "pending or absorbed"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        terminal_event_id="TERM-NO-REUSE",
                        new_completion_binding_json=json.dumps(reused_binding),
                    )
                )
            self.assertEqual(read_state(path), before)

            historical_binding = completion_binding(
                str(directory / "historical-successor-terminal.json"),
                "historical",
            )
            historical_binding["terminal_event_id"] = "TERM-HISTORICAL"
            historical_before = read_state(path)
            with self.assertRaisesRegex(StateError, "pending or absorbed"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        terminal_event_id="TERM-NO-REUSE",
                        new_completion_binding_json=json.dumps(historical_binding),
                    )
                )
            self.assertEqual(read_state(path), historical_before)

    def test_controller_thread_cannot_be_managed_owner(self) -> None:
        state = base_state()
        state["managed_roles"][0]["thread_id"] = "controller-1"
        state["objectives"][0]["owner_thread_id"] = "controller-1"
        with self.assertRaisesRegex(StateError, "Controller thread cannot also be a managed role"):
            validate_state(state)

    def test_new_v5_state_cannot_seed_legacy_terminal_applicability(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            state = base_state()
            state["objectives"][0][
                "legacy_terminal_schema"
            ] = "V4_EXECUTOR_NO_STARTUP_AUTHORITY_MIRROR"
            path = Path(tmp) / "controller-state.json"
            with self.assertRaisesRegex(StateError, "initial state cannot seed"):
                write_state(path, state, -1)
            self.assertFalse(path.exists())

    def test_successor_activation_prebinds_verified_startup_authority_and_generic_replace_cannot_mutate_it(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            contract_path = directory / "startup-contract.json"
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
            authority = {
                "startup_chain_id": derive_startup_chain_id(
                    scientific_projection,
                    production_entrypoint,
                    zero_utility_barrier,
                ),
                "contract_path": str(contract_path),
                "contract_sha256": hashlib.sha256(contract_data).hexdigest(),
                "prior_attempt_records": [],
            }

            path = directory / "controller-state.json"
            state = base_state()
            revision = write_and_verify(path, state, "TERM-STARTUP-AUTHORITY")
            cmd_activate_successor(
                successor_args(
                    state=str(path),
                    expected_revision=revision,
                    terminal_event_id="TERM-STARTUP-AUTHORITY",
                    executor_continuation_kind="CARRIER",
                    new_startup_chain_authority_json=json.dumps(authority),
                )
            )
            activated = read_state(path)
            self.assertEqual(
                activated["objectives"][0]["startup_chain_authority"], authority
            )

            changed = json.loads(json.dumps(activated))
            changed["objectives"][0]["startup_chain_authority"][
                "contract_sha256"
            ] = "f" * 64
            with self.assertRaisesRegex(
                StateError, "generic replacement cannot change owner/lifecycle"
            ):
                write_state(path, changed, activated["revision"])
            unchanged = read_state(path)
            self.assertEqual(unchanged["revision"], activated["revision"])
            self.assertEqual(
                unchanged["objectives"][0]["startup_chain_authority"], authority
            )

    def test_same_executor_cas_consumes_two_startup_repairs_without_terminal_route(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            complete_authority = sealed_startup_authority(directory)
            empty_authority = json.loads(json.dumps(complete_authority))
            empty_authority["prior_attempt_records"] = []
            state = base_state()
            state["objectives"][0]["owner_state"] = "ACTIVE"
            state["objectives"][0]["startup_chain_authority"] = empty_authority
            state["managed_roles"][0]["state"] = "ACTIVE"
            state["managed_roles"][0]["title"] = "Executor · Candidate One · ACTIVE"
            state["remote_jobs"] = []
            path = directory / "controller-state.json"
            written = write_state(path, state, -1)
            original_binding = json.loads(
                json.dumps(written["objectives"][0]["completion_binding"])
            )
            original_role = json.loads(json.dumps(written["managed_roles"][0]))

            def derive() -> dict:
                output = io.StringIO()
                with redirect_stdout(output):
                    cmd_derive_startup_chain_id(
                        type(
                            "Args",
                            (),
                            {"state": str(path), "objective_id": "objective-1"},
                        )()
                    )
                return json.loads(output.getvalue())

            initial_decision = derive()
            self.assertEqual(initial_decision["pre_utility_failures_recorded"], 0)
            self.assertIsNone(initial_decision["authorized_repair_round"])
            self.assertEqual(
                initial_decision["disposition"], "RUN_INITIAL_STARTUP_WITNESS"
            )

            # A future round cannot be consumed before its predecessor.
            second_ref = complete_authority["prior_attempt_records"][1]
            with self.assertRaisesRegex(StateError, "consecutive|round 1"):
                cmd_record_startup_attempt(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 0,
                            "objective_id": "objective-1",
                            "owner_thread_id": "worker-1",
                            "attempt_record_path": second_ref["path"],
                            "attempt_record_sha256": second_ref["sha256"],
                        },
                    )()
                )
            self.assertEqual(read_state(path)["revision"], 0)

            # Generic state replacement still cannot spend the repair budget.
            generic = read_state(path)
            generic["objectives"][0]["startup_chain_authority"] = json.loads(
                json.dumps(complete_authority)
            )
            generic["objectives"][0]["startup_chain_authority"][
                "prior_attempt_records"
            ] = complete_authority["prior_attempt_records"][:1]
            with self.assertRaisesRegex(
                StateError, "generic replacement cannot change owner/lifecycle"
            ):
                write_state(path, generic, 0)

            first_ref = complete_authority["prior_attempt_records"][0]
            first_command = type(
                "Args",
                (),
                {
                    "state": str(path),
                    "expected_revision": 0,
                    "objective_id": "objective-1",
                    "owner_thread_id": "worker-1",
                    "attempt_record_path": first_ref["path"],
                    "attempt_record_sha256": first_ref["sha256"],
                },
            )()
            cmd_record_startup_attempt(first_command)
            after_first = read_state(path)
            self.assertEqual(after_first["revision"], 1)
            self.assertEqual(len(after_first["objectives"]), 1)
            self.assertEqual(after_first["managed_roles"], [original_role])
            self.assertEqual(after_first["pending_absorptions"], [])
            self.assertEqual(after_first["absorbed_terminal_event_ids"], [])
            self.assertEqual(
                after_first["objectives"][0]["completion_binding"], original_binding
            )
            first_decision = derive()
            self.assertEqual(first_decision["pre_utility_failures_recorded"], 1)
            self.assertEqual(first_decision["authorized_repair_round"], 1)
            self.assertEqual(
                first_decision["disposition"], "MINIMAL_REPAIR_IN_SAME_EXECUTOR"
            )
            self.assertEqual(
                first_decision["on_full_witness_failure"],
                "RECORD_STARTUP_ATTEMPT",
            )

            # Lost-receipt retry is idempotent even with the pre-CAS revision.
            retry_output = io.StringIO()
            with redirect_stdout(retry_output):
                cmd_record_startup_attempt(first_command)
            self.assertEqual(
                json.loads(retry_output.getvalue())["status"], "ALREADY_APPLIED"
            )
            self.assertEqual(read_state(path)["revision"], 1)

            with self.assertRaisesRegex(StateError, "owner does not match"):
                cmd_record_startup_attempt(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 1,
                            "objective_id": "objective-1",
                            "owner_thread_id": "different-worker",
                            "attempt_record_path": second_ref["path"],
                            "attempt_record_sha256": second_ref["sha256"],
                        },
                    )()
                )
            with self.assertRaisesRegex(StateError, "digest does not match"):
                cmd_record_startup_attempt(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": 1,
                            "objective_id": "objective-1",
                            "owner_thread_id": "worker-1",
                            "attempt_record_path": second_ref["path"],
                            "attempt_record_sha256": "f" * 64,
                        },
                    )()
                )
            self.assertEqual(read_state(path)["revision"], 1)

            cmd_record_startup_attempt(
                type(
                    "Args",
                    (),
                    {
                        "state": str(path),
                        "expected_revision": 1,
                        "objective_id": "objective-1",
                        "owner_thread_id": "worker-1",
                        "attempt_record_path": second_ref["path"],
                        "attempt_record_sha256": second_ref["sha256"],
                    },
                )()
            )
            final = read_state(path)
            self.assertEqual(final["revision"], 2)
            self.assertEqual(len(final["objectives"]), 1)
            self.assertEqual(final["managed_roles"], [original_role])
            self.assertEqual(final["pending_absorptions"], [])
            self.assertEqual(final["absorbed_terminal_event_ids"], [])
            derived = derive()
            self.assertEqual(derived["pre_utility_failures_recorded"], 2)
            self.assertEqual(derived["authorized_repair_round"], 2)
            self.assertEqual(
                derived["disposition"],
                "CLEAN_CHAIN_REIMPLEMENTATION_IN_SAME_EXECUTOR",
            )
            self.assertEqual(
                derived["on_full_witness_failure"],
                "BOUNDED_ROOT_CAUSE_INVENTORY",
            )

    def test_executor_and_controller_writers_share_one_process_atomic_cas(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            complete_authority = sealed_startup_authority(directory)
            empty_authority = json.loads(json.dumps(complete_authority))
            empty_authority["prior_attempt_records"] = []
            state = base_state()
            state["objectives"][0]["owner_state"] = "ACTIVE"
            state["objectives"][0]["startup_chain_authority"] = empty_authority
            state["managed_roles"][0]["state"] = "ACTIVE"
            state["managed_roles"][0]["title"] = (
                "Executor · Candidate One · ACTIVE"
            )
            state["remote_jobs"] = []
            path = directory / "controller-state.json"
            write_state(path, state, -1)
            first_ref = complete_authority["prior_attempt_records"][0]

            context = multiprocessing.get_context("fork")
            executor_at_commit = context.Event()
            release_executor = context.Event()
            results = context.Queue()

            def executor_writer() -> None:
                import scripts.controller_control_state as state_module

                original_atomic_write = state_module._atomic_write
                delayed = False

                def delayed_atomic_write(
                    target: Path, data: bytes, mode: int = 0o640
                ) -> None:
                    nonlocal delayed
                    if not delayed and Path(target) == path:
                        delayed = True
                        executor_at_commit.set()
                        release_executor.wait(1.0)
                    original_atomic_write(target, data, mode)

                state_module._atomic_write = delayed_atomic_write
                try:
                    output = io.StringIO()
                    with redirect_stdout(output):
                        cmd_record_startup_attempt(
                            type(
                                "Args",
                                (),
                                {
                                    "state": str(path),
                                    "expected_revision": 0,
                                    "objective_id": "objective-1",
                                    "owner_thread_id": "worker-1",
                                    "attempt_record_path": first_ref["path"],
                                    "attempt_record_sha256": first_ref["sha256"],
                                },
                            )()
                        )
                    results.put(("Executor", "PASS", output.getvalue()))
                except Exception as exc:  # pragma: no cover - asserted in parent
                    results.put(("Executor", type(exc).__name__, str(exc)))
                finally:
                    state_module._atomic_write = original_atomic_write

            def controller_writer() -> None:
                try:
                    if not executor_at_commit.wait(3.0):
                        raise RuntimeError("Executor did not reach its commit boundary")
                    candidate = read_state(path)
                    candidate["objectives"][0]["stage"] = (
                        "CONTROLLER_CONCURRENT_UPDATE"
                    )
                    write_state(path, candidate, 0)
                    results.put(("Controller", "PASS", ""))
                except Exception as exc:  # pragma: no cover - asserted in parent
                    results.put(("Controller", type(exc).__name__, str(exc)))
                finally:
                    release_executor.set()

            executor = context.Process(target=executor_writer)
            controller = context.Process(target=controller_writer)
            executor.start()
            controller.start()
            executor.join(6.0)
            controller.join(6.0)
            if executor.is_alive():
                executor.terminate()
                executor.join()
                self.fail("Executor writer did not terminate")
            if controller.is_alive():
                controller.terminate()
                controller.join()
                self.fail("Controller writer did not terminate")
            self.assertEqual(executor.exitcode, 0)
            self.assertEqual(controller.exitcode, 0)

            outcomes = [results.get(timeout=2.0), results.get(timeout=2.0)]
            self.assertEqual(sum(item[1] == "PASS" for item in outcomes), 1)
            conflicts = [item for item in outcomes if "revision conflict" in item[2]]
            self.assertEqual(len(conflicts), 1, outcomes)
            final = read_state(path)
            self.assertEqual(final["revision"], 1)
            self.assertEqual(final["pending_absorptions"], [])
            self.assertEqual(final["absorbed_terminal_event_ids"], [])
            self.assertEqual(
                len(
                    final["objectives"][0]["startup_chain_authority"]
                    ["prior_attempt_records"]
                ),
                1,
            )

    def test_successor_activation_rejects_unbound_or_digest_drifted_startup_contract(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            path = directory / "controller-state.json"
            state = base_state()
            revision = write_and_verify(path, state, "TERM-STARTUP-DRIFT")
            authority = {
                "startup_chain_id": "startup-chain-sha256:" + "a" * 64,
                "contract_path": str(directory / "missing-contract.json"),
                "contract_sha256": "b" * 64,
                "prior_attempt_records": [],
            }
            with self.assertRaisesRegex(StateError, "unavailable or symlinked component"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        terminal_event_id="TERM-STARTUP-DRIFT",
                        new_startup_chain_authority_json=json.dumps(authority),
                    )
                )
            unchanged = read_state(path)
            self.assertEqual(unchanged["revision"], revision)
            self.assertNotIn(
                "startup_chain_authority", unchanged["objectives"][0]
            )

    def test_executor_successor_cannot_shrink_or_replace_startup_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            full_authority = sealed_startup_authority(directory)
            state = base_state()
            state["objectives"][0]["startup_chain_authority"] = full_authority
            path = directory / "controller-state.json"
            revision = write_and_verify(path, state, "TERM-STARTUP-MONOTONIC")

            shrunk = json.loads(json.dumps(full_authority))
            shrunk["prior_attempt_records"] = []
            with self.assertRaisesRegex(StateError, "cannot shrink|monotonic"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        terminal_event_id="TERM-STARTUP-MONOTONIC",
                        executor_continuation_kind="CARRIER",
                        new_startup_chain_authority_json=json.dumps(shrunk),
                    )
                )
            replacement = sealed_startup_authority(
                directory,
                rounds=(),
                suffix="replacement",
                entrypoint_suffix="->replacement",
            )
            with self.assertRaisesRegex(StateError, "Audit|replace"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        terminal_event_id="TERM-STARTUP-MONOTONIC",
                        executor_continuation_kind="CARRIER",
                        new_startup_chain_authority_json=json.dumps(replacement),
                    )
                )
            unchanged = read_state(path)
            self.assertEqual(unchanged["revision"], revision)
            self.assertEqual(
                unchanged["pending_absorptions"][0]["terminal_event_id"],
                "TERM-STARTUP-MONOTONIC",
            )
            self.assertEqual(
                unchanged["objectives"][0]["startup_chain_authority"],
                full_authority,
            )

            # Omitting a repeated JSON argument carries the current authority
            # forward; it never means delete/reset.
            cmd_activate_successor(
                successor_args(
                    state=str(path),
                    expected_revision=revision,
                    terminal_event_id="TERM-STARTUP-MONOTONIC",
                    executor_continuation_kind="CARRIER",
                    new_startup_chain_authority_json=None,
                )
            )
            activated = read_state(path)
            self.assertEqual(
                activated["objectives"][0]["startup_chain_authority"],
                full_authority,
            )

    def test_executor_successor_may_append_only_the_next_startup_attempt(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            full_authority = sealed_startup_authority(directory)
            first_round_authority = json.loads(json.dumps(full_authority))
            first_round_authority["prior_attempt_records"] = full_authority[
                "prior_attempt_records"
            ][:1]
            state = base_state()
            state["objectives"][0][
                "startup_chain_authority"
            ] = first_round_authority
            path = directory / "controller-state.json"
            revision = write_and_verify(path, state, "TERM-STARTUP-APPEND")
            cmd_activate_successor(
                successor_args(
                    state=str(path),
                    expected_revision=revision,
                    terminal_event_id="TERM-STARTUP-APPEND",
                    executor_continuation_kind="CARRIER",
                    new_startup_chain_authority_json=json.dumps(full_authority),
                )
            )
            activated = read_state(path)
            self.assertEqual(
                activated["objectives"][0]["startup_chain_authority"],
                full_authority,
            )

    def test_finite_block_and_reopen_preserve_and_revalidate_startup_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            authority = sealed_startup_authority(directory)
            attestation_path = directory / "external-blocker-attestation.json"
            attestation_data = canonical_bytes(
                {
                    "external_blocker_attestation": {
                        "version": 1,
                        "kind": "EXTERNAL_FACT",
                        "reason_code": "REQUIRED_AUTHORITY_UNAVAILABLE",
                        "external_fact": True,
                        "owner_can_resolve": False,
                    }
                }
            )
            attestation_path.write_bytes(attestation_data)
            attestation_path.chmod(0o444)
            state = base_state()
            state["objectives"][0]["startup_chain_authority"] = authority
            path = directory / "controller-state.json"
            revision = write_and_verify(path, state, "TERM-STARTUP-BLOCK")
            blocker = {
                "kind": "EXTERNAL_FACT",
                "reopening_fact": "The exact external launch authority becomes available.",
                "observer": "Controller",
                "trigger": "EXTERNAL_LAUNCH_AUTHORITY_AVAILABLE",
                "next_check_at": None,
                "resolution_deadline": "2026-08-09T00:00:00Z",
                "reason_code": "REQUIRED_AUTHORITY_UNAVAILABLE",
                "evidence_ref": (
                    f"{attestation_path}#sha256={hashlib.sha256(attestation_data).hexdigest()}"
                ),
            }
            cmd_absorb_and_block(
                type(
                    "Args",
                    (),
                    {
                        "state": str(path),
                        "expected_revision": revision,
                        "objective_id": "objective-1",
                        "terminal_event_id": "TERM-STARTUP-BLOCK",
                        "old_owner_thread_id": "worker-1",
                        "new_stage": "WAIT_EXTERNAL_AUTHORITY",
                        "new_scientific_outcome": "UNOBSERVED",
                        "new_next_action": "REOPEN_ON_BOUND_TRIGGER",
                        "blocker_json": json.dumps(blocker),
                        "clear_remote_job_id": ["job-1"],
                        "clear_advisory_id": [],
                    },
                )()
            )
            blocked = read_state(path)
            self.assertEqual(blocked["objectives"][0]["lifecycle"], "BLOCKED")
            self.assertEqual(
                blocked["objectives"][0]["startup_chain_authority"], authority
            )

            transitions = [
                {
                    "objective_id": "objective-1",
                    "new_objective_id": "objective-1",
                    "stage": "EXECUTOR_STARTUP",
                    "scientific_outcome": "UNOBSERVED",
                    "next_action": "RUN_EXACT_STARTUP_WITNESS",
                    "owner_thread_id": "worker-2",
                    "owner_role": "Executor",
                    "owner_state": "ACTIVE",
                    "owner_title": "Executor · Candidate One · ACTIVE",
                    "cursor": None,
                    "recovery_evidence_ref": "terminal://external-authority-restored",
                    "completion_binding": completion_binding(
                        str(directory / "TERM-STARTUP-REOPEN.json"), "reopen"
                    ),
                }
            ]
            reconcile_args = type(
                "Args",
                (),
                {
                    "state": str(path),
                    "expected_revision": blocked["revision"],
                    "transitions_json": json.dumps(transitions),
                    "remote_jobs_json": "[]",
                },
            )()

            attempt_path = Path(authority["prior_attempt_records"][1]["path"])
            original_attempt = attempt_path.read_bytes()
            attempt_path.unlink()
            attempt_path.write_bytes(canonical_bytes({"tampered": True}))
            attempt_path.chmod(0o444)
            with self.assertRaisesRegex(StateError, "digest does not match"):
                cmd_reconcile_open(reconcile_args)
            still_blocked = read_state(path)
            self.assertEqual(still_blocked["revision"], blocked["revision"])
            self.assertEqual(
                still_blocked["objectives"][0]["startup_chain_authority"],
                authority,
            )
            attempt_path.unlink()
            attempt_path.write_bytes(original_attempt)
            attempt_path.chmod(0o444)
            cmd_reconcile_open(
                reconcile_args
            )
            reopened = read_state(path)
            self.assertEqual(
                reopened["objectives"][0]["startup_chain_authority"], authority
            )
            output = io.StringIO()
            with redirect_stdout(output):
                cmd_derive_startup_chain_id(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "objective_id": "objective-1",
                        },
                    )()
                )
            derived = json.loads(output.getvalue())
            self.assertEqual(derived["pre_utility_failures_recorded"], 2)
            self.assertEqual(derived["authorized_repair_round"], 2)
            self.assertEqual(
                derived["disposition"],
                "CLEAN_CHAIN_REIMPLEMENTATION_IN_SAME_EXECUTOR",
            )
            self.assertEqual(
                derived["on_full_witness_failure"],
                "BOUNDED_ROOT_CAUSE_INVENTORY",
            )

    def test_smi_internal_grant_handler_blocker_rejected_before_cas(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            revision = write_and_verify(path, base_state(), "TERM-SMI-GRANT-HANDLER")
            before = read_state(path)
            blocker = {
                "kind": "EXTERNAL_FACT",
                "reopening_fact": "Grant handler implementation is repaired.",
                "observer": "Controller",
                "trigger": "GRANT_HANDLER_REPAIRED",
                "next_check_at": None,
                "resolution_deadline": "2026-08-10T00:00:00Z",
                "reason_code": "INTERNAL_GRANT_HANDLER",
                "evidence_ref": "/private/tmp/not-used.json#sha256=" + "0" * 64,
            }
            with self.assertRaisesRegex(StateError, "blocker.reason_code"):
                cmd_absorb_and_block(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": revision,
                            "objective_id": "objective-1",
                            "terminal_event_id": "TERM-SMI-GRANT-HANDLER",
                            "old_owner_thread_id": "worker-1",
                            "new_stage": "R2_SCOUT",
                            "new_scientific_outcome": "UNOBSERVED",
                            "new_next_action": "REPAIR_GRANT_HANDLER",
                            "blocker_json": json.dumps(blocker),
                            "clear_remote_job_id": ["job-1"],
                            "clear_advisory_id": [],
                        },
                    )()
                )
            after = read_state(path)
            self.assertEqual(after["revision"], before["revision"])
            self.assertEqual(after["pending_absorptions"], before["pending_absorptions"])
            self.assertEqual(after["objectives"][0]["owner_thread_id"], "worker-1")

    def test_tta_throughput_parking_blocker_rejected_before_cas(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            revision = write_and_verify(path, base_state(), "TERM-TTA-THROUGHPUT-PARKING")
            before = read_state(path)
            blocker = {
                "kind": "EXTERNAL_FACT",
                "reopening_fact": "Throughput parking is removed by implementation work.",
                "observer": "Controller",
                "trigger": "THROUGHPUT_PARKING_REMOVED",
                "next_check_at": None,
                "resolution_deadline": "2026-08-10T00:00:00Z",
                "reason_code": "THROUGHPUT_PARKING",
                "evidence_ref": "/private/tmp/not-used.json#sha256=" + "1" * 64,
            }
            with self.assertRaisesRegex(StateError, "blocker.reason_code"):
                cmd_absorb_and_block(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": revision,
                            "objective_id": "objective-1",
                            "terminal_event_id": "TERM-TTA-THROUGHPUT-PARKING",
                            "old_owner_thread_id": "worker-1",
                            "new_stage": "R2_SCOUT",
                            "new_scientific_outcome": "UNOBSERVED",
                            "new_next_action": "REPAIR_THROUGHPUT_PATH",
                            "blocker_json": json.dumps(blocker),
                            "clear_remote_job_id": ["job-1"],
                            "clear_advisory_id": [],
                        },
                    )()
                )
            after = read_state(path)
            self.assertEqual(after["revision"], before["revision"])
            self.assertEqual(after["pending_absorptions"], before["pending_absorptions"])
            self.assertEqual(after["objectives"][0]["owner_thread_id"], "worker-1")

    def test_p59_absent_runner_hold_blocker_rejected_before_cas(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            revision = write_and_verify(path, base_state(), "TERM-P59-ABSENT-RUNNER-HOLD")
            before = read_state(path)
            blocker = {
                "kind": "EXTERNAL_FACT",
                "reopening_fact": "A runner is provisioned after the HOLD.",
                "observer": "Controller",
                "trigger": "RUNNER_PROVISIONED",
                "next_check_at": None,
                "resolution_deadline": "2026-08-10T00:00:00Z",
                "reason_code": "ABSENT_RUNNER_HOLD",
                "evidence_ref": "/private/tmp/not-used.json#sha256=" + "2" * 64,
            }
            with self.assertRaisesRegex(StateError, "blocker.reason_code"):
                cmd_absorb_and_block(
                    type(
                        "Args",
                        (),
                        {
                            "state": str(path),
                            "expected_revision": revision,
                            "objective_id": "objective-1",
                            "terminal_event_id": "TERM-P59-ABSENT-RUNNER-HOLD",
                            "old_owner_thread_id": "worker-1",
                            "new_stage": "R2_SCOUT",
                            "new_scientific_outcome": "UNOBSERVED",
                            "new_next_action": "WAIT_FOR_RUNNER_PROVISIONING",
                            "blocker_json": json.dumps(blocker),
                            "clear_remote_job_id": ["job-1"],
                            "clear_advisory_id": [],
                        },
                    )()
                )
            after = read_state(path)
            self.assertEqual(after["revision"], before["revision"])
            self.assertEqual(after["pending_absorptions"], before["pending_absorptions"])
            self.assertEqual(after["objectives"][0]["owner_thread_id"], "worker-1")

    def test_p59_carrier_without_authority_rejected_before_cas(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            revision = write_and_verify(path, base_state(), "TERM-P59-CARRIER-NO-AUTHORITY")
            before = read_state(path)
            with self.assertRaisesRegex(StateError, "CARRIER.*startup_chain_authority"):
                cmd_activate_successor(
                    successor_args(
                        state=str(path),
                        expected_revision=revision,
                        terminal_event_id="TERM-P59-CARRIER-NO-AUTHORITY",
                        executor_continuation_kind="CARRIER",
                    )
                )
            after = read_state(path)
            self.assertEqual(after["revision"], before["revision"])
            self.assertEqual(after["pending_absorptions"], before["pending_absorptions"])
            self.assertEqual(after["objectives"][0]["owner_thread_id"], "worker-1")

    def test_same_owner_zero_utility_implementation_continuation_succeeds(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            revision = write_and_verify(path, base_state(), "TERM-ZERO-UTILITY-CONTINUATION")
            cmd_activate_successor(
                successor_args(
                    state=str(path),
                    expected_revision=revision,
                    terminal_event_id="TERM-ZERO-UTILITY-CONTINUATION",
                    executor_continuation_kind="ZERO_UTILITY_IMPLEMENTATION",
                )
            )
            after = read_state(path)
            self.assertEqual(after["revision"], revision + 1)
            self.assertEqual(after["objectives"][0]["owner_thread_id"], "worker-1")
            self.assertEqual(after["objectives"][0]["owner_role"], "Executor")
            self.assertEqual(after["objectives"][0]["candidate_state"], "OPEN")
            self.assertEqual(after["objectives"][0]["scientific_outcome"], "UNOBSERVED")
            self.assertNotIn("executor_continuation_kind", after["objectives"][0])

    def test_close_objective_atomically_absorbs_and_releases_owner(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            path = directory / "controller-state.json"
            state = base_state()
            state["remote_jobs"] = []
            state["objectives"][0][
                "startup_chain_authority"
            ] = sealed_startup_authority(directory)
            revision = write_and_verify(path, state, "TERM-CLOSE-1")
            closure = {
                "basis": "PROSPECTIVE_SCOPED_MPE_FAILURE",
                "scope": "exact finite Scout cell",
                "evidence_ref": "terminal-1",
                "reopening_fact": "A distinct prospective estimand is frozen.",
                "independent_audit_terminal_id": "audit-1",
                "evidence_eligible": True,
                "prospective_action_table_pass": True,
                "finite_cell_complete": True,
                "preregistered_mpe_failure": True,
                "scope_boundary_preserved": True,
                "adversarial_review_pass": True,
                "powered_negative_claimed": False,
            }
            args = type("Args", (), {
                "state": str(path),
                "expected_revision": revision,
                "objective_id": "objective-1",
                "terminal_event_id": "TERM-CLOSE-1",
                "old_owner_thread_id": "worker-1",
                "new_stage": "SCOPED_CLOSE",
                "new_scientific_outcome": "OBSERVED_BELOW_MPE_SCOPED_CLOSED",
                "new_next_action": "NO_SUCCESSOR_UNLESS_REOPENED",
                "closure_json": json.dumps(closure),
                "clear_remote_job_id": [],
                "clear_advisory_id": [],
            })()
            cmd_close_objective(args)
            closed = read_state(path)
            self.assertEqual(closed["objectives"][0]["candidate_state"], "CLOSED")
            self.assertEqual(closed["objectives"][0]["lifecycle"], "DONE")
            self.assertNotIn(
                "startup_chain_authority", closed["objectives"][0]
            )
            self.assertEqual(closed["managed_roles"], [])
            self.assertIn("TERM-CLOSE-1", closed["absorbed_terminal_event_ids"])

    def test_v3_reconcile_rejects_open_done(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            legacy = base_state()
            legacy["schema_version"] = 3
            objective = legacy["objectives"][0]
            objective.update({
                "candidate_state": "OPEN",
                "lifecycle": "DONE",
                "reopening_fact": "A bounded witness becomes available.",
            })
            for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
                objective.pop(key)
            legacy["managed_roles"] = []
            legacy["remote_jobs"] = []
            data = canonical_bytes(legacy)
            path.write_bytes(data)
            checksum_path(path).write_text(
                f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
                encoding="utf-8",
            )
            transitions = [{
                "objective_id": "objective-1",
                "new_objective_id": "objective-1-route",
                "stage": "AUDIT_ACTIVE",
                "scientific_outcome": "UNOBSERVED",
                "next_action": "WAIT_AUDIT_TERMINAL",
                "owner_thread_id": "audit-1",
                "owner_role": "Audit",
                "owner_state": "ACTIVE",
                "owner_title": "Audit · Candidate One Route · ACTIVE",
                "cursor": "cursor:activation",
                "recovery_evidence_ref": "terminal://v3-reconciliation",
                "completion_binding": completion_binding(
                    str(Path(tmp) / "recovered-terminal.json"), "recovered"
                ),
            }]
            with self.assertRaisesRegex(StateError, "only reopen a BLOCKED objective"):
                cmd_reconcile_open(type("Args", (), {
                    "state": str(path),
                    "expected_revision": 0,
                    "transitions_json": json.dumps(transitions),
                    "remote_jobs_json": "[]",
                })())

    def test_v3_reconcile_cannot_rebind_delegated_owner_without_fresh_reason(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            legacy = base_state()
            legacy["schema_version"] = 3
            data = canonical_bytes(legacy)
            path.write_bytes(data)
            checksum_path(path).write_text(
                f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
                encoding="utf-8",
            )
            transitions = [{
                "objective_id": "objective-1",
                "new_objective_id": "objective-1",
                "stage": "R3_ACTIVE",
                "scientific_outcome": "UNOBSERVED",
                "next_action": "WAIT_EXECUTOR_TERMINAL",
                "owner_thread_id": "worker-2",
                "owner_role": "Executor",
                "owner_state": "ACTIVE",
                "owner_title": "Executor · Candidate One · ACTIVE",
                "cursor": None,
                "recovery_evidence_ref": "terminal://generic-recovery-proof",
                "completion_binding": completion_binding(
                    str(Path(tmp) / "recovered-terminal.json"), "recovered"
                ),
            }]
            with self.assertRaisesRegex(StateError, "only reopen a BLOCKED objective"):
                cmd_reconcile_open(type("Args", (), {
                    "state": str(path),
                    "expected_revision": 0,
                    "transitions_json": json.dumps(transitions),
                    "remote_jobs_json": "[]",
                })())

    def test_v3_reconcile_cannot_change_delegated_role_with_recovery_ref_only(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            legacy = base_state()
            legacy["schema_version"] = 3
            data = canonical_bytes(legacy)
            path.write_bytes(data)
            checksum_path(path).write_text(
                f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
                encoding="utf-8",
            )
            transitions = [{
                "objective_id": "objective-1",
                "new_objective_id": "objective-1",
                "stage": "AUDIT_ACTIVE",
                "scientific_outcome": "UNOBSERVED",
                "next_action": "WAIT_AUDIT_TERMINAL",
                "owner_thread_id": "audit-2",
                "owner_role": "Audit",
                "owner_state": "ACTIVE",
                "owner_title": "Audit · Candidate One · ACTIVE",
                "cursor": None,
                "recovery_evidence_ref": "terminal://generic-recovery-proof",
                "completion_binding": completion_binding(
                    str(Path(tmp) / "recovered-terminal.json"), "recovered"
                ),
            }]
            with self.assertRaisesRegex(StateError, "only reopen a BLOCKED objective"):
                cmd_reconcile_open(type("Args", (), {
                    "state": str(path),
                    "expected_revision": 0,
                    "transitions_json": json.dumps(transitions),
                    "remote_jobs_json": "[]",
                })())

    def test_v3_reconcile_migrates_only_finite_blocked_recovery(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            path = Path(tmp) / "controller-state.json"
            legacy = base_state()
            legacy["schema_version"] = 3
            objective = legacy["objectives"][0]
            objective.update(
                {
                    "candidate_state": "BLOCKED",
                    "stage": "WAIT_EXTERNAL",
                    "lifecycle": "BLOCKED",
                    "next_action": "CHECK_EXTERNAL_FACT",
                    "blocker": {
                        "kind": "EXTERNAL_FACT",
                        "reopening_fact": "A required external artifact becomes available.",
                        "observer": "Controller",
                        "trigger": "ARTIFACT_AVAILABLE",
                        "next_check_at": "2026-08-06T00:00:00Z",
                        "resolution_deadline": "2026-08-07T00:00:00Z",
                    },
                }
            )
            for key in ("owner_thread_id", "owner_role", "owner_state", "completion_binding"):
                objective.pop(key)
            legacy["managed_roles"] = []
            legacy["remote_jobs"] = []
            data = canonical_bytes(legacy)
            path.write_bytes(data)
            checksum_path(path).write_text(
                f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
                encoding="utf-8",
            )
            transitions = [{
                "objective_id": "objective-1",
                "new_objective_id": "objective-1",
                "stage": "AUDIT_ACTIVE",
                "scientific_outcome": "UNOBSERVED",
                "next_action": "WAIT_AUDIT_TERMINAL",
                "owner_thread_id": "audit-1",
                "owner_role": "Audit",
                "owner_state": "ACTIVE",
                "owner_title": "Audit · Candidate One · ACTIVE",
                "cursor": None,
                "recovery_evidence_ref": "terminal://artifact-available-proof",
                "completion_binding": completion_binding(
                    str(Path(tmp) / "recovered-terminal.json"), "recovered"
                ),
            }]
            cmd_reconcile_open(type("Args", (), {
                "state": str(path),
                "expected_revision": 0,
                "transitions_json": json.dumps(transitions),
                "remote_jobs_json": "[]",
            })())
            migrated = read_state(path)
            self.assertEqual(migrated["schema_version"], 5)
            self.assertEqual(migrated["objectives"][0]["lifecycle"], "DELEGATED")
            self.assertEqual(migrated["objectives"][0]["owner_thread_id"], "audit-1")


if __name__ == "__main__":
    unittest.main()
