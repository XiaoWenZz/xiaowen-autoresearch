import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.controller_control_state import (
    StateError,
    canonical_bytes,
    cmd_absorb_and_block,
    cmd_activate_successor,
    cmd_replace,
    read_state,
    validate_state,
    write_state,
)
from tests.test_controller_control_state import (
    base_state,
    completion_binding,
    observe_and_verify,
    remote_job,
    sealed_startup_authority,
    successor_args,
    write_and_verify,
)


class ProaStateToolRecheckTest(unittest.TestCase):
    def test_second_zero_utility_implementation_requires_a_bounded_continuation(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            state_path = directory / "controller-state.json"
            first_revision = write_and_verify(
                state_path, base_state(), "TERM-PR8-ZERO-1"
            )
            second_binding = completion_binding(
                str(directory / "zero-successor-2.json"), "pr8-zero-2"
            )
            with redirect_stdout(io.StringIO()):
                cmd_activate_successor(
                    successor_args(
                        state=str(state_path),
                        expected_revision=first_revision,
                        terminal_event_id="TERM-PR8-ZERO-1",
                        new_objective_id="objective-2",
                        new_completion_binding_json=json.dumps(second_binding),
                        executor_continuation_kind="ZERO_UTILITY_IMPLEMENTATION",
                    )
                )

            first_successor = read_state(state_path)
            observed_revision = observe_and_verify(
                state_path, first_successor["revision"], "objective-2"
            )
            third_binding = completion_binding(
                str(directory / "zero-successor-3.json"), "pr8-zero-3"
            )
            before_second_zero = read_state(state_path)
            with self.assertRaises(StateError):
                with redirect_stdout(io.StringIO()):
                    cmd_activate_successor(
                        successor_args(
                            state=str(state_path),
                            expected_revision=observed_revision,
                            objective_id="objective-2",
                            new_objective_id="objective-3",
                            terminal_event_id=second_binding["terminal_event_id"],
                            new_completion_binding_json=json.dumps(third_binding),
                            executor_continuation_kind="ZERO_UTILITY_IMPLEMENTATION",
                            clear_remote_job_id=[],
                        )
                    )
            self.assertEqual(read_state(state_path), before_second_zero)

    def test_second_carrier_with_the_same_sealed_authority_requires_progress(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            state_path = directory / "controller-state.json"
            authority = sealed_startup_authority(
                directory, rounds=(1,), suffix="pr8-carrier"
            )
            state = base_state()
            state["objectives"][0]["startup_chain_authority"] = authority
            first_revision = write_and_verify(
                state_path, state, "TERM-PR8-CARRIER-1"
            )
            second_binding = completion_binding(
                str(directory / "carrier-successor-2.json"), "pr8-carrier-2"
            )
            with redirect_stdout(io.StringIO()):
                cmd_activate_successor(
                    successor_args(
                        state=str(state_path),
                        expected_revision=first_revision,
                        terminal_event_id="TERM-PR8-CARRIER-1",
                        new_objective_id="objective-2",
                        new_completion_binding_json=json.dumps(second_binding),
                        executor_continuation_kind="CARRIER",
                    )
                )

            first_successor = read_state(state_path)
            self.assertEqual(
                first_successor["objectives"][0]["startup_chain_authority"], authority
            )
            observed_revision = observe_and_verify(
                state_path, first_successor["revision"], "objective-2"
            )
            third_binding = completion_binding(
                str(directory / "carrier-successor-3.json"), "pr8-carrier-3"
            )
            before_second_carrier = read_state(state_path)
            with self.assertRaises(StateError):
                with redirect_stdout(io.StringIO()):
                    cmd_activate_successor(
                        successor_args(
                            state=str(state_path),
                            expected_revision=observed_revision,
                            objective_id="objective-2",
                            new_objective_id="objective-3",
                            terminal_event_id=second_binding["terminal_event_id"],
                            new_completion_binding_json=json.dumps(third_binding),
                            executor_continuation_kind="CARRIER",
                            clear_remote_job_id=[],
                        )
                    )
            self.assertEqual(read_state(state_path), before_second_carrier)

    def test_internal_semantic_witness_cannot_be_used_as_external_blocker(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            state_path = directory / "controller-state.json"
            revision = write_and_verify(
                state_path, base_state(), "TERM-PR8-INTERNAL-WITNESS"
            )

            witness_binding = completion_binding(
                str(directory / "internal-semantic-witness.json"), "pr8-internal"
            )
            witness_data = canonical_bytes(
                {
                    "external_blocker_attestation": {
                        "version": 1,
                        "reason_code": "REQUIRED_AUTHORITY_UNAVAILABLE",
                        "external_fact": False,
                        "owner_can_resolve": True,
                        "finding": "local implementation missing",
                        "repair": "same owner repair",
                    }
                }
            )
            witness_path = Path(witness_binding["terminal_path"])
            witness_path.write_bytes(witness_data)
            witness_path.chmod(0o444)
            blocker = {
                "kind": "EXTERNAL_FACT",
                "reopening_fact": "The external authority becomes available.",
                "observer": "Controller",
                "trigger": "EXTERNAL_AUTHORITY_AVAILABLE",
                "next_check_at": None,
                "resolution_deadline": "2099-01-01T00:00:00Z",
                "reason_code": "REQUIRED_AUTHORITY_UNAVAILABLE",
                "evidence_ref": (
                    f"{witness_path}#sha256={hashlib.sha256(witness_data).hexdigest()}"
                ),
            }
            before = read_state(state_path)
            with self.assertRaises(StateError):
                with redirect_stdout(io.StringIO()):
                    cmd_absorb_and_block(
                        type(
                            "Args",
                            (),
                            {
                                "state": str(state_path),
                                "expected_revision": revision,
                                "objective_id": "objective-1",
                                "terminal_event_id": "TERM-PR8-INTERNAL-WITNESS",
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
            self.assertEqual(read_state(state_path), before)

    def test_validate_state_rejects_two_active_jobs_for_one_objective_owner(self) -> None:
        state = base_state()
        duplicate = remote_job(
            job_id="job-2", objective_id="objective-1", owner_thread_id="worker-1"
        )
        duplicate["host"] = "ecnuhpc"
        state["remote_jobs"].append(duplicate)
        with self.assertRaises(StateError):
            validate_state(state)

    def test_generic_replace_cannot_remove_remote_job_membership(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            state_path = directory / "controller-state.json"
            write_state(state_path, base_state(), -1)
            candidate = read_state(state_path)
            candidate["remote_jobs"] = []
            candidate_path = directory / "candidate.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            before = read_state(state_path)
            with self.assertRaises(StateError):
                with redirect_stdout(io.StringIO()):
                    cmd_replace(
                        type(
                            "Args",
                            (),
                            {
                                "state": str(state_path),
                                "input": str(candidate_path),
                                "expected_revision": before["revision"],
                            },
                        )()
                    )
            self.assertEqual(read_state(state_path), before)


if __name__ == "__main__":
    unittest.main()
