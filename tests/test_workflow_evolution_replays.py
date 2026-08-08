from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass, field
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts.controller_control_state import (
    StateError,
    canonical_bytes,
    cmd_derive_startup_chain_id,
    derive_startup_chain_id,
    require_startup_chain_id,
    write_state,
)


ROOT = Path(__file__).parents[1]
WORKSPACE = Path(
    os.environ.get(
        "XAR_WORKSPACE_ROOT",
        "/Users/xiaowen/Documents/Obsidian Vault/003_科研",
    )
)
REPLAY_FIXTURE = json.loads(
    (ROOT / "tests" / "fixtures" / "replays" / "zero_science_events.json").read_text(
        encoding="utf-8"
    )
)
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
ORCHESTRATION = (ROOT / "references" / "orchestration.md").read_text(
    encoding="utf-8"
)
STATE_SCHEMA = (ROOT / "references" / "state-schema.md").read_text(
    encoding="utf-8"
)

HARD_PROJECTION = (
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
SCIENTIFIC_PROJECTION = {
    key: f"frozen-{key}-identity" for key in HARD_PROJECTION
}
PRODUCTION_ENTRYPOINT = "public-cli->prepare_run->coordinator->worker-bootstrap"
ZERO_UTILITY_BARRIER = "READY_BEFORE_FIRST_UTILITY"
CANONICAL_STARTUP_CHAIN_ID = derive_startup_chain_id(
    SCIENTIFIC_PROJECTION,
    PRODUCTION_ENTRYPOINT,
    ZERO_UTILITY_BARRIER,
)


def seal_json(path: Path, payload: dict[str, object]) -> dict[str, str]:
    data = canonical_bytes(payload)
    path.write_bytes(data)
    path.chmod(0o444)
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()}


def write_startup_state(
    directory: Path,
    contract_path: Path,
    attempt_paths: list[str],
    *,
    name: str = "startup-state.json",
) -> Path:
    authority = {
        "startup_chain_id": CANONICAL_STARTUP_CHAIN_ID,
        "contract_path": str(contract_path),
        "contract_sha256": sha256_file(contract_path),
        "prior_attempt_records": [
            {"path": record_path, "sha256": sha256_file(Path(record_path))}
            for record_path in attempt_paths
        ],
    }
    state = {
        "schema_version": 5,
        "revision": 0,
        "updated_at": "2026-08-08T00:00:00Z",
        "controller": {
            "thread_id": "controller-1",
            "project_id": "project-1",
            "cwd": "/workspace",
            "title": "Controller · Research · ACTIVE",
            "pin_required": True,
        },
        "objectives": [
            {
                "objective_id": "objective-startup",
                "candidate_id": "candidate-startup",
                "candidate_state": "OPEN",
                "stage": "EXECUTOR_STARTUP",
                "scientific_outcome": "UNOBSERVED",
                "lifecycle": "DELEGATED",
                "next_action": "RUN_EXACT_STARTUP_WITNESS",
                "owner_thread_id": "executor-1",
                "owner_role": "Executor",
                "owner_state": "ACTIVE",
                "completion_binding": {
                    "task_id": "task-startup",
                    "dispatch_id": "dispatch-startup",
                    "lease_epoch": 1,
                    "contract_revision": "contract-startup",
                    "terminal_event_id": "TERM-STARTUP",
                    "terminal_path": str(directory / "future-terminal.json"),
                },
                "startup_chain_authority": authority,
            }
        ],
        "managed_roles": [
            {
                "thread_id": "executor-1",
                "role": "Executor",
                "title": "Executor · Startup Chain · ACTIVE",
                "state": "ACTIVE",
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
    state_path = directory / name
    write_state(state_path, state, -1)
    return state_path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load replay source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def extract_heredoc(source: str, marker: str) -> str:
    opener = f"<<'{marker}'"
    start = source.index(opener)
    start = source.index("\n", start) + 1
    end = source.index(f"\n{marker}\n", start)
    return source[start:end] + "\n"


def extract_shell_function(source: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^{re.escape(name)}\(\) \{{\n.*?^\}}\n",
        source,
    )
    if match is None:
        raise AssertionError(f"shell function not found: {name}")
    return match.group(0)


def materialize_prepare_run_result(module, root: Path) -> dict:
    run_root = root / "run"
    preflight = root / "preflight.json"
    contract = root / "contract.json"
    manifest = root / "manifest.json"
    preflight.write_text("{}\n", encoding="utf-8")
    contract.write_text("{}\n", encoding="utf-8")
    manifest.write_text("{}\n", encoding="utf-8")
    selection = {"selection_manifest_sha256": "selection-id", "bundles": []}
    args = argparse.Namespace(
        contract=str(contract),
        manifest=str(manifest),
        model_path=str(root / "model"),
        data_dir=str(root / "data"),
        output=str(run_root / "selection.json"),
    )
    patches = {
        "REMOTE_RUN": run_root,
        "REMOTE_PREFLIGHT": preflight,
        "validate_contract": mock.Mock(return_value={}),
        "validate_remote_preflight": mock.Mock(
            return_value={
                "selection_validation": {
                    "selection_manifest_sha256": "selection-id"
                }
            }
        ),
        "validate_scoped_environment": mock.Mock(),
        "validate_asset_paths": mock.Mock(),
        "validate_runtime_identity": mock.Mock(),
        "load_tokenizer": mock.Mock(return_value=object()),
        "select_task_bundles": mock.Mock(return_value=selection),
        "current_gpu_uuids": mock.Mock(return_value=module.REQUIRED_GPU_UUIDS),
    }
    with mock.patch.multiple(module, **patches):
        return module.prepare_run(args)


def prepare_cli_argv(module, root: Path) -> list[str]:
    return [
        "prepare-run",
        "--contract",
        str(root / "contract.json"),
        "--manifest",
        str(root / "manifest.json"),
        "--model-path",
        str(root / "model"),
        "--data-dir",
        str(root / "data"),
        "--output",
        str(root / "run" / "selection.json"),
    ]


def install_gnu_stat_shim(root: Path) -> Path:
    binary_root = root / "replay-bin"
    binary_root.mkdir()
    shim = binary_root / "stat"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import os, stat, sys\n"
        "if len(sys.argv) != 4 or sys.argv[1] != '-c': raise SystemExit(64)\n"
        "value = os.stat(sys.argv[3], follow_symlinks=False)\n"
        "if sys.argv[2] == '%a': print(oct(stat.S_IMODE(value.st_mode))[2:])\n"
        "elif sys.argv[2] == '%h': print(value.st_nlink)\n"
        "elif sys.argv[2] == '%s': print(value.st_size)\n"
        "else: raise SystemExit(64)\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return binary_root


@dataclass(frozen=True)
class PreutilityDefect:
    event_id: str
    attempt_id: str
    scientific_projection: dict[str, object] = field(
        default_factory=lambda: dict(SCIENTIFIC_PROJECTION)
    )
    production_entrypoint: str = PRODUCTION_ENTRYPOINT
    zero_utility_barrier: str = ZERO_UTILITY_BARRIER
    startup_chain_id: str | None = None
    pre_barrier: bool = True
    utility_observed: bool = False
    protected_access: bool = False
    changes_hard_projection: bool = False
    unsafe_partial_state: bool = False
    escalation_reason: str | None = None

    def __post_init__(self) -> None:
        if self.startup_chain_id is None:
            object.__setattr__(
                self,
                "startup_chain_id",
                derive_startup_chain_id(
                    self.scientific_projection,
                    self.production_entrypoint,
                    self.zero_utility_barrier,
                ),
            )


@dataclass(frozen=True)
class ReplayResult:
    repair_rounds: int
    executor_owners: int
    governance_attempts: int
    scientific_attempts: int
    carrier_generation_replacements: int
    create_new_attempts: int
    intermediate_terminals: int
    controller_roundtrips: int
    scientific_utility_observations: int
    disposition: str
    hard_projection: tuple[str, ...]
    wall_time_saved: str = "NOT_ESTIMABLE"


MATERIAL_ESCALATION_REASONS = {
    "ACCEPTANCE_OR_AUTHORITY_AMBIGUITY",
    "HARD_BUDGET_OR_ACCELERATOR_EXPANSION",
    "DESTRUCTIVE_REUSE_UNSAFE",
    "CROSS_OWNER_WRITE_CONFLICT",
    "PUBLIC_PRODUCTION_PAID_AUTH_PERMISSION",
    "UNAVAILABLE_EXTERNAL_AUTHORITY",
}


def replay_startup_chain(defects: list[PreutilityDefect]) -> ReplayResult:
    if not defects:
        raise ValueError("at least one observed defect is required")
    chain_ids = {
        require_startup_chain_id(
            defect.startup_chain_id,
            defect.scientific_projection,
            defect.production_entrypoint,
            defect.zero_utility_barrier,
        )
        for defect in defects
    }
    if len(chain_ids) != 1:
        raise ValueError("one replay must bind exactly one startup_chain_id")

    repairs = 0
    carrier_generation_replacements = 0
    for defect in defects:
        if not defect.pre_barrier:
            raise ValueError("post-barrier events use frozen no-rescue routing")
        if defect.utility_observed or defect.protected_access:
            raise ValueError("this repair loop is outcome-blind only")
        if defect.changes_hard_projection:
            raise ValueError("hard scientific projection cannot change")
        if (
            defect.escalation_reason is not None
            and defect.escalation_reason not in MATERIAL_ESCALATION_REASONS
        ):
            raise ValueError("unknown material escalation reason")
        if defect.escalation_reason is not None:
            return ReplayResult(
                repair_rounds=repairs,
                executor_owners=1,
                governance_attempts=1,
                scientific_attempts=1,
                carrier_generation_replacements=carrier_generation_replacements,
                create_new_attempts=0,
                intermediate_terminals=1,
                controller_roundtrips=1,
                scientific_utility_observations=0,
                disposition=f"ESCALATE_{defect.escalation_reason}",
                hard_projection=HARD_PROJECTION,
            )
        if repairs < 2:
            repairs += 1
        if defect.unsafe_partial_state:
            carrier_generation_replacements += 1

    if len(defects) == 1:
        disposition = "MINIMAL_REPAIR_IN_SAME_EXECUTOR"
    elif len(defects) == 2:
        disposition = "CLEAN_CHAIN_REIMPLEMENTATION_IN_SAME_EXECUTOR"
    else:
        disposition = "BOUNDED_ROOT_CAUSE_AND_IN_PLACE_REPAIR"
    return ReplayResult(
        repair_rounds=repairs,
        executor_owners=1,
        governance_attempts=1,
        scientific_attempts=1,
        carrier_generation_replacements=carrier_generation_replacements,
        create_new_attempts=0,
        intermediate_terminals=0,
        controller_roundtrips=0,
        scientific_utility_observations=0,
        disposition=disposition,
        hard_projection=HARD_PROJECTION,
    )


class WorkflowEvolutionReplayTest(unittest.TestCase):
    def test_p59_historical_prepare_run_and_real_cli_reproduce_run_id_keyerror(
        self,
    ) -> None:
        event = REPLAY_FIXTURE["events"]["p59_prepare_run_cli"]
        old_path = WORKSPACE / event["old_source"]
        fixed_path = WORKSPACE / event["fixed_source"]
        self.assertEqual(sha256_file(old_path), event["old_sha256"])
        self.assertEqual(sha256_file(fixed_path), event["fixed_sha256"])
        old = load_module(old_path, "xar_p59_old_prepare_replay")
        fixed = load_module(fixed_path, "xar_p59_fixed_prepare_replay")

        with tempfile.TemporaryDirectory() as old_tmp:
            old_root = Path(old_tmp)
            old_result = materialize_prepare_run_result(old, old_root)
            self.assertNotIn("run_id", old_result)
            with mock.patch.object(old, "prepare_run", return_value=old_result):
                with self.assertRaisesRegex(KeyError, "run_id"):
                    old.main(prepare_cli_argv(old, old_root))

        with tempfile.TemporaryDirectory() as fixed_tmp:
            fixed_root = Path(fixed_tmp)
            fixed_result = materialize_prepare_run_result(fixed, fixed_root)
            self.assertEqual(fixed_result["run_id"], fixed.RUN_ID)
            stdout = io.StringIO()
            with mock.patch.object(fixed, "prepare_run", return_value=fixed_result):
                with contextlib.redirect_stdout(stdout):
                    self.assertEqual(fixed.main(prepare_cli_argv(fixed, fixed_root)), 0)
            self.assertEqual(stdout.getvalue(), f"PASS prepare-run {fixed.RUN_ID}\n")
        self.assertFalse(event["utility_observed"])

    def test_p59_exact_attempt002_release_heredoc_reproduces_unbound_env(
        self,
    ) -> None:
        event = REPLAY_FIXTURE["events"]["p59_release_environment"]
        old_path = WORKSPACE / event["old_source"]
        old_source = old_path.read_text(encoding="utf-8")
        self.assertEqual(sha256_file(old_path), event["old_sha256"])
        release_body = extract_heredoc(old_source, "REMOTE_RELEASE")
        release_prefix = old_source[
            old_source.rindex("ssh -o BatchMode=yes dual5090", 0, old_source.index("<<'REMOTE_RELEASE'")) : old_source.index("<<'REMOTE_RELEASE'")
        ]
        self.assertNotIn("EXPECTED_RUN_ID=", release_prefix)
        self.assertIn('"$EXPECTED_RUN_ID"', release_body)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            replay_bin = install_gnu_stat_shim(root)
            project = root / "project"
            environment = root / "environment"
            cache = root / "cache"
            staging = root / "staging"
            run = root / "run"
            scratch = root / "scratch"
            for path in (project, environment / "bin", cache, staging, scratch):
                path.mkdir(parents=True, mode=0o750)
                path.chmod(0o750)
            (project / "contract.json").write_text("{}\n", encoding="utf-8")
            (project / "manifest.json").write_text("{}\n", encoding="utf-8")
            (project / "src").mkdir()
            (project / "src" / "p59_r2_scout.py").write_text("# replay stub\n")
            preflight = staging / "carrier-release-preflight.json"
            preflight.write_text(
                json.dumps(
                    {
                        "training_only_profile": {"profile_gpu_hours": 0},
                        "resource_accounting": {
                            "successor_network_bytes": 0,
                            "successor_retained_disk_bytes": 0,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            preflight.chmod(0o444)
            python_stub = environment / "bin" / "python"
            python_stub.write_text(
                "#!/bin/sh\n"
                "if [ \"${1:-}\" = '-c' ]; then printf '0\\n'; fi\n"
                "exit 0\n",
                encoding="utf-8",
            )
            python_stub.chmod(0o755)
            replay_env = os.environ.copy()
            replay_env["PATH"] = f"{replay_bin}:{replay_env['PATH']}"
            replay_env.update(
                {
                    "REMOTE_PROJECT": str(project),
                    "REMOTE_MODEL": str(root / "model"),
                    "REMOTE_DATA": str(root / "data"),
                    "REMOTE_ENV": str(environment),
                    "REMOTE_CACHE": str(cache),
                    "REMOTE_STAGING": str(staging),
                    "REMOTE_RUN": str(run),
                    "REMOTE_TMP": str(scratch),
                    "REMOTE_PREFLIGHT": str(preflight),
                    "REMOTE_LOG": str(run / "logs" / "executor.log"),
                    "EXPECTED_CONTRACT": "contract.json",
                    "EXPECTED_SELECTION_SHA256": "selection-id",
                    "EXPECTED_SEEDS": "59101,59102,59103,59104,59105,59106",
                    "ABSOLUTE_WALL_DEADLINE_EPOCH": "4102444800",
                }
            )
            replay_env.pop("EXPECTED_RUN_ID", None)
            completed = subprocess.run(
                ["bash", "-c", release_body],
                cwd=project,
                env=replay_env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertRegex(completed.stderr, r"EXPECTED_RUN_ID: unbound variable")
        self.assertFalse(event["utility_observed"])

    def test_p59_attempt003_exact_mode_gate_and_single_argv_builder(self) -> None:
        event = REPLAY_FIXTURE["events"]["p59_release_environment"]
        fixed_path = WORKSPACE / event["fixed_source"]
        fixed_source = fixed_path.read_text(encoding="utf-8")
        self.assertEqual(sha256_file(fixed_path), event["fixed_sha256"])
        function = extract_shell_function(fixed_source, "require_project_mode_0750")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            replay_bin = install_gnu_stat_shim(root)
            project = root / "project"
            project.mkdir(mode=0o755)
            script = (
                "set -euo pipefail\n"
                f"REMOTE_PROJECT={subprocess.list2cmdline([str(project)])}\n"
                "ROOT=\"$REMOTE_PROJECT\"\n"
                f"{function}\n"
                "require_project_mode_0750\n"
            )
            rejected = subprocess.run(
                ["bash", "-c", script],
                env={**os.environ, "PATH": f"{replay_bin}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rejected.returncode, 68)
            project.chmod(0o750)
            accepted = subprocess.run(
                ["bash", "-c", script],
                env={**os.environ, "PATH": f"{replay_bin}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

        self.assertIn("EXPECTED_RUN_ID='$EXPECTED_RUN_ID'", fixed_source)
        self.assertEqual(fixed_source.count("build_coordinator_argv()"), 1)
        self.assertIn("build_coordinator_argv 'internal-coordinate-r3-launch-witness'", fixed_source)
        self.assertIn("build_coordinator_argv 'internal-coordinate-r3'", fixed_source)
        self.assertIn("origin_training_started': False", fixed_source)
        self.assertIn("local_eval_forward': False", fixed_source)
        self.assertIn("utility_exposure': 'NONE'", fixed_source)

    def test_p59_two_historical_preutility_defects_share_one_owner_budget(self) -> None:
        result = replay_startup_chain(
            [
                PreutilityDefect("P59-V5-RUN-ID-KEYERROR", "attempt-001"),
                PreutilityDefect(
                    "P59-A002-EXPECTED-RUN-ID-AND-ROOT-MODE", "attempt-002"
                ),
            ]
        )
        self.assertEqual(result.repair_rounds, 2)
        self.assertEqual(result.executor_owners, 1)
        self.assertEqual(result.governance_attempts, 1)
        self.assertEqual(result.create_new_attempts, 0)
        self.assertEqual(result.intermediate_terminals, 0)
        self.assertEqual(result.controller_roundtrips, 0)
        self.assertEqual(
            result.disposition,
            "CLEAN_CHAIN_REIMPLEMENTATION_IN_SAME_EXECUTOR",
        )
        self.assertEqual(result.wall_time_saved, "NOT_ESTIMABLE")

    def test_smi_self_match_and_schema_drift_share_the_chain_bound(self) -> None:
        event = REPLAY_FIXTURE["events"]["smi_attempt_004"]
        self.assertEqual(event["process_check_false_positives"], 4)
        self.assertEqual(event["canonical_protected_outcome"], "UNOBSERVED")
        self.assertIs(event["drifted_checker_value"], False)
        checker_pid = 101
        parent_pid = 100
        run_id = "SMI-E1-V2-FREQ30-ATTEMPT004"
        executable = "/opt/smi/bin/launcher"
        processes = [
            (checker_pid, parent_pid, ["python", "check", run_id]),
            (parent_pid, 1, ["bash", "check", run_id]),
            (102, 1, [executable + "-not-anchored", run_id]),
            (103, 1, [executable, "--run-id", run_id]),
        ]
        matches = [
            pid
            for pid, ppid, argv in processes
            if pid not in {checker_pid, parent_pid}
            and ppid != checker_pid
            and argv
            and argv[0] == executable
            and run_id in argv
        ]
        self.assertEqual(matches, [103])
        canonical_fixture = {"protected_outcome": "UNOBSERVED"}
        wrong_type_fixture = {"protected_outcome": False}
        self.assertIsInstance(canonical_fixture["protected_outcome"], str)
        self.assertNotEqual(
            wrong_type_fixture["protected_outcome"],
            canonical_fixture["protected_outcome"],
        )
        result = replay_startup_chain(
            [
                PreutilityDefect("SMI-PROCESS-CHECK-SELF-MATCH", "attempt-004"),
                PreutilityDefect("SMI-UNOBSERVED-ENUM-DRIFT", "attempt-004"),
            ]
        )
        self.assertEqual(result.repair_rounds, 2)
        self.assertEqual(result.controller_roundtrips, 0)
        self.assertEqual(
            result.disposition,
            "CLEAN_CHAIN_REIMPLEMENTATION_IN_SAME_EXECUTOR",
        )
        self.assertIn("service/cgroup `MainPID` or a PID file", ORCHESTRATION)
        self.assertIn("excludes the\nchecker PID/parent", ORCHESTRATION)
        self.assertIn("canonical schema/enum authority", ORCHESTRATION)
        self.assertIn("canonical `UNOBSERVED`", ORCHESTRATION)

    def test_p56_future_reader_is_pre_freeze_startup_evidence(self) -> None:
        event = REPLAY_FIXTURE["events"]["p56_future_reader"]
        self.assertEqual(event["required_stage"], "BEFORE_SEALING")
        self.assertTrue(event["reader_must_be_mechanically_exercised"])
        result = replay_startup_chain(
            [PreutilityDefect("P56-AUDIT-READER-SELF-LOCK", "attempt-002")]
        )
        self.assertEqual(result.disposition, "MINIMAL_REPAIR_IN_SAME_EXECUTOR")
        self.assertIn("unproven future reader", ORCHESTRATION)
        self.assertIn("future-reader canaries", SKILL)

    def test_tta_egress_and_local_cuda_ipc_are_separate_witnesses(self) -> None:
        event = REPLAY_FIXTURE["events"]["tta_cuda_no_egress"]
        self.assertEqual(event["private_unix_socketpair"], "PASS")
        self.assertEqual(event["ordinary_send_recv"], "EPERM")
        self.assertEqual(event["cuda_get_device_count"], "ERROR_304")
        self.assertEqual(event["exact_denied_syscall"], "UNVERIFIED")
        result = replay_startup_chain(
            [PreutilityDefect("TTA-NO-EGRESS-CUDA-304", "scientific-003")]
        )
        self.assertEqual(result.scientific_utility_observations, 0)
        self.assertIn("egress leakage, blocked local CUDA/IPC", ORCHESTRATION)
        self.assertIn("bounded stage/error class", ORCHESTRATION)

    def test_smi_attempt007_009_wrapper_defects_stay_one_scientific_attempt(
        self,
    ) -> None:
        raw_name = REPLAY_FIXTURE["events"]["smi_attempt_007_raw_name_wrapper"]
        pointer = REPLAY_FIXTURE["events"]["smi_attempt_008_json_pointer"]
        ssh_argv = REPLAY_FIXTURE["events"]["smi_attempt_009_ssh_argv"]
        self.assertEqual(
            (raw_name["terminal_bytes"], raw_name["terminal_sha256"]),
            (
                140420,
                "c985f253922ea7033205d406062b9a77a3263bf206331e7b1f3e459065facb10",
            ),
        )
        self.assertEqual(
            (pointer["terminal_bytes"], pointer["terminal_sha256"]),
            (
                17793,
                "d3f66ff448d9d109523af07ff212af4042dad8f7ef4a272724e6fa095274a9ee",
            ),
        )
        self.assertEqual(
            (ssh_argv["terminal_bytes"], ssh_argv["terminal_sha256"]),
            (
                13405,
                "5e527eb091cacec063a7be2fc639a55480d90fce37ff943e505ec38a2a9ee605",
            ),
        )
        self.assertEqual(raw_name["validator_status"], "PASS")
        self.assertEqual(raw_name["raw_name"], "Jinja2")
        self.assertEqual(raw_name["normalized_name"], "jinja2")
        self.assertNotEqual(pointer["observed_pointer"], pointer["authority_pointer"])
        self.assertFalse(pointer["remote_receiver_started"])
        self.assertEqual(pointer["empty_directories_preserved"], 8)
        self.assertEqual(ssh_argv["remote_files_created_or_modified"], 0)
        self.assertEqual(
            ssh_argv["required_assembly"],
            "ONE_SHLEX_JOIN_POST_HOST_ARGUMENT",
        )
        for event in (raw_name, pointer, ssh_argv):
            self.assertFalse(event["release_crossed"])
            self.assertFalse(event["protected_access"])
            self.assertFalse(event["utility_observed"])

        result = replay_startup_chain(
            [
                PreutilityDefect("SMI-A007-RAW-NAME", "historical-007"),
                PreutilityDefect(
                    "SMI-A008-JSON-POINTER",
                    "historical-008",
                    unsafe_partial_state=True,
                ),
                PreutilityDefect("SMI-A009-SSH-ARGV", "historical-009"),
            ]
        )
        self.assertEqual(result.repair_rounds, 2)
        self.assertEqual(result.executor_owners, 1)
        self.assertEqual(result.governance_attempts, 1)
        self.assertEqual(result.scientific_attempts, 1)
        self.assertEqual(result.carrier_generation_replacements, 1)
        self.assertEqual(result.create_new_attempts, 0)
        self.assertEqual(result.intermediate_terminals, 0)
        self.assertEqual(result.controller_roundtrips, 0)
        self.assertEqual(result.scientific_utility_observations, 0)
        self.assertEqual(
            result.disposition,
            "BOUNDED_ROOT_CAUSE_AND_IN_PLACE_REPAIR",
        )
        flattened = " ".join(ORCHESTRATION.split())
        self.assertIn("parent workflow invariant", flattened)
        self.assertIn("`carrier_generation`", ORCHESTRATION)
        self.assertIn("first-mismatch terminal/no-repair/create-new", flattened)

    def test_material_escalation_gate_remains_fail_closed(self) -> None:
        for reason in sorted(MATERIAL_ESCALATION_REASONS):
            with self.subTest(reason=reason):
                result = replay_startup_chain(
                    [
                        PreutilityDefect("LOCAL-BUG", "attempt-001"),
                        PreutilityDefect(
                            "MATERIAL-BOUNDARY",
                            "attempt-001",
                            escalation_reason=reason,
                        ),
                    ]
                )
                self.assertEqual(result.scientific_attempts, 1)
                self.assertEqual(result.create_new_attempts, 0)
                self.assertEqual(result.intermediate_terminals, 1)
                self.assertEqual(result.controller_roundtrips, 1)
                self.assertEqual(result.disposition, f"ESCALATE_{reason}")

        with self.assertRaisesRegex(ValueError, "unknown material escalation"):
            replay_startup_chain(
                [
                    PreutilityDefect(
                        "UNKNOWN-BOUNDARY",
                        "attempt-001",
                        escalation_reason="LOCAL_WRAPPER_BUG",
                    )
                ]
            )

    def test_third_prebarrier_failure_stays_same_owner_after_inventory(self) -> None:
        result = replay_startup_chain(
            [
                PreutilityDefect("FAIL-1", "attempt-001"),
                PreutilityDefect("FAIL-2-DIFFERENT-STAGE", "attempt-002"),
                PreutilityDefect("FAIL-3-NEW-ATTEMPT-ID", "attempt-003"),
            ]
        )
        self.assertEqual(result.repair_rounds, 2)
        self.assertEqual(result.scientific_attempts, 1)
        self.assertEqual(result.intermediate_terminals, 0)
        self.assertEqual(result.controller_roundtrips, 0)
        self.assertEqual(
            result.disposition,
            "BOUNDED_ROOT_CAUSE_AND_IN_PLACE_REPAIR",
        )
        self.assertEqual(result.hard_projection, HARD_PROJECTION)

    def test_postbarrier_or_protected_event_cannot_enter_repair_loop(self) -> None:
        with self.assertRaisesRegex(ValueError, "post-barrier"):
            replay_startup_chain(
                [PreutilityDefect("POST", "attempt-001", pre_barrier=False)]
            )
        with self.assertRaisesRegex(ValueError, "outcome-blind"):
            replay_startup_chain(
                [PreutilityDefect("PROTECTED", "attempt-001", protected_access=True)]
            )
        with self.assertRaisesRegex(ValueError, "hard scientific projection"):
            replay_startup_chain(
                [
                    PreutilityDefect(
                        "IDENTITY-CHANGE",
                        "attempt-001",
                        changes_hard_projection=True,
                    )
                ]
            )

    def test_startup_chain_id_is_derived_and_cannot_reset_across_attempts(self) -> None:
        first = PreutilityDefect("FAIL-1", "attempt-001")
        second = PreutilityDefect("FAIL-2", "attempt-002")
        self.assertEqual(first.startup_chain_id, CANONICAL_STARTUP_CHAIN_ID)
        self.assertEqual(second.startup_chain_id, CANONICAL_STARTUP_CHAIN_ID)
        forged_third = PreutilityDefect(
            "FAIL-3",
            "attempt-003",
            startup_chain_id="startup-chain-sha256:" + "0" * 64,
        )
        with self.assertRaisesRegex(StateError, "canonical derivation"):
            replay_startup_chain([first, second, forged_third])
        canonical_third = PreutilityDefect("FAIL-3", "attempt-003")
        result = replay_startup_chain([first, second, canonical_third])
        self.assertEqual(result.repair_rounds, 2)
        self.assertEqual(
            result.disposition,
            "BOUNDED_ROOT_CAUSE_AND_IN_PLACE_REPAIR",
        )

    def test_canonical_tool_reads_immutable_contract_and_attempt_history(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            contract_path = directory / "contract.json"
            seal_json(
                contract_path,
                {
                    "startup_chain_binding": {
                        "scientific_projection": SCIENTIFIC_PROJECTION,
                        "production_entrypoint": PRODUCTION_ENTRYPOINT,
                        "zero_utility_barrier": ZERO_UTILITY_BARRIER,
                    }
                },
            )
            attempt_paths = []
            for repair_round in (1, 2):
                attempt_path = directory / f"attempt-{repair_round}.json"
                seal_json(
                    attempt_path,
                    {
                        "startup_chain_attempt": {
                            "attempt_id": f"attempt-{repair_round:03d}",
                            "startup_chain_id": CANONICAL_STARTUP_CHAIN_ID,
                            "repair_round": repair_round,
                            "boundary": "PRE_UTILITY_FAILURE",
                            "utility_observed": False,
                            "protected_access": False,
                        }
                    },
                )
                attempt_paths.append(str(attempt_path))
            one_failure_state = write_startup_state(
                directory,
                contract_path,
                attempt_paths[:1],
                name="one-failure-state.json",
            )
            one_stdout = io.StringIO()
            with contextlib.redirect_stdout(one_stdout):
                cmd_derive_startup_chain_id(
                    argparse.Namespace(
                        state=str(one_failure_state),
                        objective_id="objective-startup",
                    )
                )
            one_decision = json.loads(one_stdout.getvalue())
            one_replay = replay_startup_chain(
                [PreutilityDefect("FAIL-1", "attempt-001")]
            )
            self.assertEqual(one_decision["pre_utility_failures_recorded"], 1)
            self.assertEqual(one_decision["authorized_repair_round"], 1)
            self.assertEqual(one_decision["disposition"], one_replay.disposition)
            self.assertEqual(
                one_decision["on_full_witness_failure"],
                "RECORD_STARTUP_ATTEMPT",
            )

            state_path = write_startup_state(directory, contract_path, attempt_paths)
            command = argparse.Namespace(
                state=str(state_path),
                objective_id="objective-startup",
                # Caller extras are deliberately ignored: authority comes from state.
                contract=str(directory / "unbound-contract.json"),
                attempt_record=[],
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                cmd_derive_startup_chain_id(command)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["startup_chain_id"], CANONICAL_STARTUP_CHAIN_ID)
            two_replay = replay_startup_chain(
                [
                    PreutilityDefect("FAIL-1", "attempt-001"),
                    PreutilityDefect("FAIL-2", "attempt-002"),
                ]
            )
            self.assertEqual(result["pre_utility_failures_recorded"], 2)
            self.assertEqual(result["authorized_repair_round"], 2)
            self.assertEqual(result["disposition"], two_replay.disposition)
            self.assertEqual(
                result["on_full_witness_failure"],
                "BOUNDED_ROOT_CAUSE_INVENTORY",
            )

            changed_contract = directory / "changed-contract.json"
            seal_json(
                changed_contract,
                {
                    "startup_chain_binding": {
                        "scientific_projection": SCIENTIFIC_PROJECTION,
                        "production_entrypoint": PRODUCTION_ENTRYPOINT
                        + " --equivalent-spelling",
                        "zero_utility_barrier": ZERO_UTILITY_BARRIER,
                    }
                },
            )
            command.contract = str(changed_contract)
            ignored = io.StringIO()
            with contextlib.redirect_stdout(ignored):
                cmd_derive_startup_chain_id(command)
            self.assertEqual(
                json.loads(ignored.getvalue())["pre_utility_failures_recorded"],
                2,
            )

            contract_path.unlink()
            contract_path.write_bytes(changed_contract.read_bytes())
            contract_path.chmod(0o444)
            with self.assertRaisesRegex(StateError, "digest does not match"):
                cmd_derive_startup_chain_id(command)

    def test_startup_chain_cli_has_no_caller_supplied_canonical_inputs(self) -> None:
        from scripts.controller_control_state import build_parser

        parser = build_parser()
        parsed = parser.parse_args(
            [
                "derive-startup-chain-id",
                "--state",
                "/private/tmp/controller-state.json",
                "--objective-id",
                "objective-startup",
            ]
        )
        self.assertEqual(parsed.state, "/private/tmp/controller-state.json")
        command = [
            "derive-startup-chain-id",
            "--state",
            "/private/tmp/controller-state.json",
            "--objective-id",
            "objective-startup",
            "--contract",
            "/private/tmp/unbound-contract.json",
            "--attempt-record",
            "/private/tmp/omitted-or-forged-record.json",
            "--declared-startup-chain-id",
            CANONICAL_STARTUP_CHAIN_ID,
            "--scientific-projection-json",
            json.dumps(SCIENTIFIC_PROJECTION),
            "--production-entrypoint",
            PRODUCTION_ENTRYPOINT,
            "--zero-utility-barrier",
            ZERO_UTILITY_BARRIER,
        ]
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(command)

    def test_startup_chain_attempt_history_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            directory = Path(tmp)
            contract_path = directory / "contract.json"
            seal_json(
                contract_path,
                {
                    "startup_chain_binding": {
                        "scientific_projection": SCIENTIFIC_PROJECTION,
                        "production_entrypoint": PRODUCTION_ENTRYPOINT,
                        "zero_utility_barrier": ZERO_UTILITY_BARRIER,
                    }
                },
            )

            def sealed_attempt(name: str, payload: dict[str, object]) -> str:
                path = directory / name
                seal_json(path, payload)
                return str(path)

            def attempt(
                attempt_id: str,
                repair_round: int,
                *,
                chain_id: str = CANONICAL_STARTUP_CHAIN_ID,
                protected_access: bool = False,
            ) -> dict[str, object]:
                return {
                    "startup_chain_attempt": {
                        "attempt_id": attempt_id,
                        "startup_chain_id": chain_id,
                        "repair_round": repair_round,
                        "boundary": "PRE_UTILITY_FAILURE",
                        "utility_observed": False,
                        "protected_access": protected_access,
                    }
                }

            cases = {
                "missing": (
                    [sealed_attempt("missing.json", {"attempt_id": "attempt-001"})],
                    "startup_chain_attempt",
                ),
                "duplicate_round": (
                    [
                        sealed_attempt("duplicate-a.json", attempt("attempt-001", 1)),
                        sealed_attempt("duplicate-b.json", attempt("attempt-002", 1)),
                    ],
                    "duplicate repair round",
                ),
                "gapped_round": (
                    [sealed_attempt("gap.json", attempt("attempt-002", 2))],
                    "consecutive from round 1",
                ),
                "cross_chain": (
                    [
                        sealed_attempt(
                            "cross.json",
                            attempt(
                                "attempt-001",
                                1,
                                chain_id="startup-chain-sha256:" + "f" * 64,
                            ),
                        )
                    ],
                    "does not match the immutable contract",
                ),
                "protected": (
                    [
                        sealed_attempt(
                            "protected.json",
                            attempt("attempt-001", 1, protected_access=True),
                        )
                    ],
                    "outcome-blind",
                ),
            }
            for name, (record_paths, error) in cases.items():
                state_path = write_startup_state(
                    directory,
                    contract_path,
                    record_paths,
                    name=f"{name}-state.json",
                )
                with self.subTest(name=name), self.assertRaisesRegex(StateError, error):
                    cmd_derive_startup_chain_id(
                        argparse.Namespace(
                            state=str(state_path),
                            objective_id="objective-startup",
                        )
                    )

    def test_controller_recovery_uses_one_schema_and_same_wake(self) -> None:
        self.assertIn(
            "The nested six-field `completion_binding` is the sole terminal identity\nauthority",
            STATE_SCHEMA,
        )
        self.assertIn("prepare-terminal-callback", STATE_SCHEMA)
        self.assertIn("final_bytes", STATE_SCHEMA)
        self.assertIn("final_sha256", STATE_SCHEMA)
        flattened = " ".join(STATE_SCHEMA.split())
        self.assertIn("syntax overflow such as `1e9999`", STATE_SCHEMA)
        self.assertIn("Unicode surrogate code units", STATE_SCHEMA)
        self.assertIn("`O_NOFOLLOW|O_NONBLOCK`", STATE_SCHEMA)
        self.assertIn("share-lock the stable control-directory inode", STATE_SCHEMA)
        self.assertIn("exactly one competing Controller/Executor CAS can succeed", flattened)
        self.assertIn("carry an omitted repeated argument forward", STATE_SCHEMA)
        self.assertIn("revalidates it before reopening the Executor", flattened)
        self.assertIn("record-startup-attempt` is the sole same-objective CAS", flattened)
        self.assertIn("Executor terminal mirrors the exact authority or explicit `null`", flattened)
        self.assertIn("globally fresh against both pending and absorbed IDs", flattened)
        self.assertIn(
            "V4_EXECUTOR_NO_STARTUP_AUTHORITY_MIRROR", flattened
        )
        self.assertIn("same Controller wake", " ".join(STATE_SCHEMA.split()))
        self.assertFalse((ROOT / "scripts" / "controller_control_state_v5.py").exists())
        self.assertFalse((ROOT / "scripts" / "validate_failure_terminal.py").exists())


if __name__ == "__main__":
    unittest.main()
