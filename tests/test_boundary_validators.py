from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROMPT_VALIDATOR = SKILL_ROOT / "scripts" / "validate_opportunity_prompt.py"
PROMPT_TEMPLATE = SKILL_ROOT / "assets" / "opportunity-search-prompt-template.md"
GATE_VALIDATOR = SKILL_ROOT / "scripts" / "validate_opportunity_gate_calibration.py"
GATE_TEMPLATE = SKILL_ROOT / "assets" / "opportunity-gate-calibration-template.json"
FRAME_VALIDATOR = SKILL_ROOT / "scripts" / "validate_prospective_frame.py"


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
    )


class BoundaryValidatorsTest(unittest.TestCase):
    def test_source_first_high_recall_v4_template_passes_when_filled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
            text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "frozen value", text)
            prompt.write_text(text, encoding="utf-8")
            result = run(PROMPT_VALIDATOR, prompt)
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["verdict"], "PASS_EXTERNAL_OPPORTUNITY_PROMPT_STRUCTURE")

    def test_process_delta_controls_are_required_in_external_prompt(self) -> None:
        replacements = {
            "source_family_id": "source family",
            "R0 -> R1 -> R2 -> R3": "readiness sequence",
            "numeric LLM or expert novelty score": "reviewer judgment",
        }
        for removed, replacement in replacements.items():
            with self.subTest(removed=removed), tempfile.TemporaryDirectory() as temp:
                prompt = Path(temp) / "prompt.md"
                text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
                text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "frozen value", text)
                self.assertIn(removed, text)
                prompt.write_text(text.replace(removed, replacement), encoding="utf-8")
                result = run(PROMPT_VALIDATOR, prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_process_delta_inversions_fail_closed(self) -> None:
        additions = {
            "Require source_family_id Jaccard threshold or assign DROP_NO_DECISION to problem_admission.":
                "source-family telemetry cannot gate problem admission",
            "mechanism_depth determines problem_admission as PROBE.":
                "mechanism depth cannot determine problem admission",
            "R1 may read and interpret protected scientific outcomes.":
                "R1 cannot access scientific outcomes",
            "R2 is frozen after the scientific outcome.":
                "R2 cannot follow scientific outcomes",
            "A numeric novelty score >= 4 determines problem_admission.":
                "numeric novelty score cannot gate admission",
        }
        for addition, expected_error in additions.items():
            with self.subTest(addition=addition), tempfile.TemporaryDirectory() as temp:
                prompt = Path(temp) / "prompt.md"
                text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
                text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "frozen value", text)
                prompt.write_text(text + "\n" + addition + "\n", encoding="utf-8")
                result = run(PROMPT_VALIDATOR, prompt)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(expected_error, result.stdout)

    def test_canonical_prompt_rejects_static_mutation_or_appended_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
            text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "frozen value", text)
            for mutation in (
                text.replace("Opportunity Search ->", "Opportunity Review ->", 1),
                text + "\nHarmless-looking appended policy.\n",
            ):
                prompt.write_text(mutation, encoding="utf-8")
                result = run(PROMPT_VALIDATOR, prompt)
                self.assertEqual(result.returncode, 1)
                self.assertIn("not an exact assembly of the canonical template", result.stdout)

    def test_mutable_slot_is_assembly_valid_but_semantic_inversion_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
            text = text.replace(
                "{{REQUIRED_OUTPUT_ORDER}}",
                "R1 may read and interpret protected scientific outcomes.",
            )
            text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "frozen value", text)
            prompt.write_text(text, encoding="utf-8")
            result = run(PROMPT_VALIDATOR, prompt)
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertNotIn(
                "prompt is not an exact assembly of the canonical template",
                payload["errors"],
            )
            self.assertIn("R1 cannot access scientific outcomes", payload["errors"])

    def test_prompt_stage_inversion_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            prompt.write_text(
                "Confirmatory then Opportunity Search then Problem Scout then Contribution Gate\n"
                "FACT INFERENCE HYPOTHESIS actor target estimand causal bottleneck strongest preserving\n"
                "mechanism-deletion positive negative ambiguous primary-source scoped closure at most one\n"
                "ADMIT_TO_PROBLEM_SCOUT SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION field-level NO-GO\n",
                encoding="utf-8",
            )
            result = run(PROMPT_VALIDATOR, prompt)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("stage inversion", result.stdout)

    def test_legacy_prompt_without_two_stage_admission_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            prompt.write_text(
                "Opportunity Search -> Problem Scout -> Contribution Gate -> Confirmatory\n"
                "FACT INFERENCE HYPOTHESIS actor target estimand causal bottleneck strongest preserving\n"
                "mechanism-deletion positive negative ambiguous primary-source scoped closure at most one\n"
                "ADMIT_TO_PROBLEM_SCOUT SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION field-level NO-GO\n",
                encoding="utf-8",
            )
            result = run(PROMPT_VALIDATOR, prompt)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing source-first-high-recall-v4 schema marker", result.stdout)
            self.assertIn("missing separate problem admission", result.stdout)
            self.assertIn("missing separate contribution forecast", result.stdout)

    def test_high_recall_v3_prompt_is_rejected_after_v4_cutover(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
            text = text.replace(
                "source-first-high-recall-v4",
                "high-recall-v3",
            )
            text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "frozen value", text)
            prompt.write_text(text, encoding="utf-8")
            result = run(PROMPT_VALIDATOR, prompt)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing source-first-high-recall-v4 schema marker", result.stdout)

    def test_noncopyable_pre_signal_hard_gate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
            text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "frozen value", text)
            text += (
                "\nA candidate must expose a non-copyable federation-only observable "
                "or reject it before Problem Scout.\n"
            )
            prompt.write_text(text, encoding="utf-8")
            result = run(PROMPT_VALIDATOR, prompt)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pre-signal hard-gate inversion", result.stdout)

    def test_copyability_drop_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
            text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "frozen value", text)
            text += "\nAssign DROP_PROBLEM_EXACT_REDUCTION when an observable is copyable.\n"
            prompt.write_text(text, encoding="utf-8")
            result = run(PROMPT_VALIDATOR, prompt)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pre-signal hard-gate inversion", result.stdout)

    def test_gate_calibration_template_passes(self) -> None:
        result = run(GATE_VALIDATOR, GATE_TEMPLATE)
        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["verdict"], "PASS_OPPORTUNITY_GATE_CALIBRATION")
        self.assertEqual(payload["summary"]["positive_controls"], 3)
        self.assertEqual(payload["summary"]["negative_controls"], 3)

    def test_gate_calibration_fails_on_retrospective_false_reject(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "calibration.json"
            payload = json.loads(GATE_TEMPLATE.read_text(encoding="utf-8"))
            payload["controls"][0]["observed_problem_admission"] = "HOLD_CARRIER"
            payload.pop("summary")
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            result = run(GATE_VALIDATOR, artifact)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "retention_state must be EVIDENCE_GAP_LEAD",
                result.stdout,
            )

    def test_retention_cannot_compensate_for_retrospective_positive_probe_miss(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "calibration.json"
            payload = json.loads(GATE_TEMPLATE.read_text(encoding="utf-8"))
            payload["controls"][0]["observed_problem_admission"] = "HOLD_INFORMATION"
            payload["controls"][0]["retention_state"] = "EVIDENCE_GAP_LEAD"
            payload["controls"][0]["next_evidence_action"] = "resolve one source gap"
            payload.pop("summary")
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            result = run(GATE_VALIDATOR, artifact)
            self.assertEqual(result.returncode, 1)
            self.assertIn("retrospective positive PROBE misses", result.stdout)

    def test_exposure_ledger_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            ledger = root / "ledger.jsonl"
            manifest.write_text(
                json.dumps({"entries": [{"paper_id": "P1", "confirmation_tier": "P"}]}) + "\n",
                encoding="utf-8",
            )
            ledger.write_text(
                json.dumps(
                    {
                        "event_id": "EV1",
                        "artifact_id": "P1",
                        "exposure_type": "claim",
                        "observed_at": "2026-07-21T00:00:00Z",
                        "source": "review",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            result = run(
                FRAME_VALIDATOR,
                "--manifest",
                manifest,
                "--exposure-ledger",
                ledger,
                "--freeze-at",
                "2026-07-22T00:00:00Z",
            )
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "INVALID_FRESHNESS_LEDGER")
            self.assertEqual(payload["mismatch_count"], 1)

    def test_d14_trusted_access_ledger_enforces_plan_before_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            ledger = root / "trusted-access-ledger.jsonl"
            manifest.write_text(
                json.dumps(
                    {"entries": [{"paper_id": "P1", "confirmation_tier": "D"}]}
                )
                + "\n",
                encoding="utf-8",
            )
            ledger.write_text(
                json.dumps(
                    {
                        "event_id": "ACCESS-1",
                        "artifact_id": "P1",
                        "exposure_type": "result",
                        "observed_at": "2026-07-21T00:01:00Z",
                        "source": "trusted-local-access-ledger",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            not_evaluated = run(
                FRAME_VALIDATOR,
                "--manifest",
                manifest,
                "--exposure-ledger",
                ledger,
                "--freeze-at",
                "2026-07-21T00:02:00Z",
            )
            self.assertEqual(
                not_evaluated.returncode,
                2,
                not_evaluated.stdout + not_evaluated.stderr,
            )
            self.assertEqual(
                json.loads(not_evaluated.stdout)["status"],
                "INVALID_ACCESS_MODE",
            )

            for label, plan_frozen_at in (
                ("before_access", "2026-07-21T00:00:00Z"),
                ("same_time", "2026-07-21T00:01:00Z"),
                ("after_access", "2026-07-21T00:02:00Z"),
            ):
                with self.subTest(label=label):
                    result = run(
                        FRAME_VALIDATOR,
                        "--manifest",
                        manifest,
                        "--exposure-ledger",
                        ledger,
                        "--freeze-at",
                        "2026-07-21T00:02:00Z",
                        "--access-mode",
                        "protected",
                        "--trusted-access-ledger",
                        ledger,
                        "--plan-frozen-at",
                        plan_frozen_at,
                    )
                    payload = json.loads(result.stdout)
                    if label == "before_access":
                        self.assertEqual(
                            result.returncode, 0, result.stdout + result.stderr
                        )
                        self.assertEqual(
                            payload["access_chronology"]["status"],
                            "PASS_PLAN_BEFORE_ACCESS",
                        )
                        expected_sha256 = hashlib.sha256(ledger.read_bytes()).hexdigest()
                        self.assertEqual(
                            payload["access_chronology"]["sha256"], expected_sha256
                        )
                        self.assertEqual(
                            payload["exposure_ledger"]["sha256"], expected_sha256
                        )
                    else:
                        self.assertEqual(result.returncode, 2)
                        self.assertEqual(
                            payload["status"], "INVALID_ACCESS_CHRONOLOGY"
                        )
                        self.assertEqual(
                            payload["access_chronology"]["status"],
                            "INVALID_PLAN_ACCESS_CHRONOLOGY",
                        )

            ledger.write_text(
                "\n".join(
                    json.dumps(item)
                    for item in (
                        {
                            "event_id": "ACCESS-LATE",
                            "artifact_id": "P1",
                            "exposure_type": "result",
                            "observed_at": "2026-07-21T00:03:00Z",
                            "source": "trusted-local-access-ledger",
                        },
                        {
                            "event_id": "ACCESS-EARLY",
                            "artifact_id": "P1",
                            "exposure_type": "result",
                            "observed_at": "2026-07-21T00:01:00Z",
                            "source": "trusted-local-access-ledger",
                        },
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            regressed = run(
                FRAME_VALIDATOR,
                "--manifest",
                manifest,
                "--exposure-ledger",
                ledger,
                "--freeze-at",
                "2026-07-21T00:04:00Z",
                "--access-mode",
                "protected",
                "--trusted-access-ledger",
                ledger,
                "--plan-frozen-at",
                "2026-07-21T00:00:00Z",
            )
            self.assertEqual(regressed.returncode, 1)
            self.assertIn("regresses append-only chronology", regressed.stderr)

    def test_public_source_mode_is_inferred_only_without_protected_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            ledger = root / "ledger.jsonl"
            manifest.write_text(
                json.dumps({"entries": [{"paper_id": "P1", "confirmation_tier": "E"}]})
                + "\n",
                encoding="utf-8",
            )
            ledger.write_text(
                json.dumps(
                    {
                        "event_id": "CLAIM-1",
                        "artifact_id": "P1",
                        "exposure_type": "claim",
                        "observed_at": "2026-07-21T00:00:00Z",
                        "source": "public review",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            result = run(
                FRAME_VALIDATOR,
                "--manifest",
                manifest,
                "--exposure-ledger",
                ledger,
                "--freeze-at",
                "2026-07-22T00:00:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["access_mode"]["value"], "public_source")
            self.assertTrue(payload["access_mode"]["inferred"])
            self.assertEqual(
                payload["access_chronology"]["status"],
                "NOT_APPLICABLE_PUBLIC_SOURCE",
            )

    def test_risk_mode_rejects_unknown_ledger_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            ledger = root / "ledger.jsonl"
            manifest.write_text(
                json.dumps({"entries": [{"paper_id": "P1", "confirmation_tier": "P"}]})
                + "\n",
                encoding="utf-8",
            )
            ledger.write_text(
                json.dumps(
                    {
                        "event_id": "ACCESS-UNKNOWN",
                        "artifact_id": "P2",
                        "exposure_type": "result",
                        "observed_at": "2026-07-21T00:01:00Z",
                        "source": "trusted-local-access-ledger",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            result = run(
                FRAME_VALIDATOR,
                "--manifest",
                manifest,
                "--exposure-ledger",
                ledger,
                "--freeze-at",
                "2026-07-21T00:02:00Z",
                "--access-mode",
                "protected",
                "--trusted-access-ledger",
                ledger,
                "--plan-frozen-at",
                "2026-07-21T00:00:00Z",
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(
                json.loads(result.stdout)["status"],
                "INVALID_UNKNOWN_LEDGER_ARTIFACT",
            )

    def test_strict_result_blind_safe_tree_is_exact_text_only_and_fail_closed(self) -> None:
        def invoke_case(case: str) -> subprocess.CompletedProcess[str]:
            case_root = root / case
            safe_root = case_root / "safe"
            if case == "root-symlink":
                real_root = case_root / "real-safe"
                real_root.mkdir(parents=True)
                safe_root.symlink_to(real_root, target_is_directory=True)
            else:
                safe_root.mkdir(parents=True)
            source = safe_root / "paper.md"
            source.write_text("method-only safe source\n", encoding="utf-8")
            helper = case_root / "helper.py"
            helper.write_text("print('safe helper')\n", encoding="utf-8")
            manifest = case_root / "manifest.json"
            ledger = case_root / "ledger.jsonl"
            ledger.write_text("", encoding="utf-8")
            entries = [
                {
                    "paper_id": "P1",
                    "confirmation_tier": "P",
                    "path": "paper.md",
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                }
            ]
            if case == "hash-mismatch":
                entries[0]["sha256"] = "0" * 64
            elif case == "unlisted":
                (safe_root / "extra.txt").write_text("extra\n", encoding="utf-8")
            elif case == "symlink":
                (safe_root / "alias.md").symlink_to(source)
            elif case == "opaque":
                opaque = safe_root / "archive.zip"
                opaque.write_bytes(b"PK\x03\x04")
                entries.append(
                    {
                        "paper_id": "P2",
                        "confirmation_tier": "P",
                        "path": "archive.zip",
                        "sha256": hashlib.sha256(opaque.read_bytes()).hexdigest(),
                    }
                )
            elif case == "forbidden":
                source.write_text("method-only SECRET result\n", encoding="utf-8")
                entries[0]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest.write_text(
                json.dumps(
                    {
                        "entries": entries,
                        "operational_access": {
                            "authority_readable_paths": [
                                str(source.resolve()),
                                str(helper.resolve()),
                            ],
                            "helper_paths": [
                                {
                                    "path": str(helper.resolve()),
                                    "sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
                                }
                            ],
                            "locator_only_paths": [str((case_root / "future-output.json").resolve())],
                            "activation_argv": [str(helper.resolve()), "--safe"],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            return run(
                FRAME_VALIDATOR,
                "--manifest",
                manifest,
                "--exposure-ledger",
                ledger,
                "--freeze-at",
                "2026-07-21T00:00:00Z",
                "--access-mode",
                "strict_result_blind",
                "--trusted-access-ledger",
                ledger,
                "--plan-frozen-at",
                "2026-07-20T00:00:00Z",
                "--safe-source-root",
                safe_root,
                "--forbidden-text",
                "SECRET",
            )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            passing = invoke_case("pass")
            self.assertEqual(passing.returncode, 0, passing.stdout + passing.stderr)
            self.assertEqual(
                json.loads(passing.stdout)["safe_source_validation"]["status"],
                "PASS_SAFE_SOURCE_TREE",
            )

            for case, expected in (
                ("hash-mismatch", "sha256 mismatch"),
                ("unlisted", "manifest/file set mismatch"),
                ("symlink", "contains symlink"),
                ("root-symlink", "root must be a real directory"),
                ("opaque", "opaque file type"),
                ("forbidden", "forbidden byte sequence"),
            ):
                with self.subTest(case=case):
                    result = invoke_case(case)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["status"], "BLOCK_PRE_DISPATCH_ACCESS")
                    self.assertIn(expected, payload["safe_source_validation"]["reason"])

    def test_strict_result_blind_operational_access_frame_is_exact_and_fail_closed(self) -> None:
        def setup_case() -> tuple[Path, dict[str, object], Path, Path, Path, Path]:
            case_root = Path(tempfile.mkdtemp())
            self.addCleanup(shutil.rmtree, case_root, ignore_errors=True)
            safe_root = case_root / "safe"
            safe_root.mkdir()
            source = safe_root / "paper.md"
            source.write_text("method-only safe source\n", encoding="utf-8")
            helper = case_root / "helper.py"
            helper.write_text("print('safe helper')\n", encoding="utf-8")
            ledger = case_root / "ledger.jsonl"
            ledger.write_text("", encoding="utf-8")
            source_path = str(source.resolve())
            helper_path = str(helper.resolve())
            payload: dict[str, object] = {
                "entries": [
                    {
                        "paper_id": "P1",
                        "confirmation_tier": "P",
                        "path": "paper.md",
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    }
                ],
                "operational_access": {
                    "authority_readable_paths": [source_path, helper_path],
                    "helper_paths": [
                        {
                            "path": helper_path,
                            "sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
                        }
                    ],
                    "locator_only_paths": [
                        str((case_root / "future-output.json").resolve()),
                        str((case_root / ".codex" / "state_5.sqlite").resolve()),
                    ],
                    "activation_argv": [helper_path, "--safe"],
                },
            }
            manifest = case_root / "manifest.json"
            return case_root, payload, manifest, ledger, safe_root, helper

        def invoke(payload: dict[str, object], manifest: Path, ledger: Path, safe_root: Path) -> subprocess.CompletedProcess[str]:
            manifest.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            return run(
                FRAME_VALIDATOR,
                "--manifest",
                manifest,
                "--exposure-ledger",
                ledger,
                "--freeze-at",
                "2026-07-21T00:00:00Z",
                "--access-mode",
                "strict_result_blind",
                "--trusted-access-ledger",
                ledger,
                "--plan-frozen-at",
                "2026-07-20T00:00:00Z",
                "--safe-source-root",
                safe_root,
            )

        case_root, payload, manifest, ledger, safe_root, helper = setup_case()
        passing = invoke(payload, manifest, ledger, safe_root)
        self.assertEqual(passing.returncode, 0, passing.stdout + passing.stderr)
        passing_payload = json.loads(passing.stdout)
        self.assertEqual(
            passing_payload["operational_access_validation"]["status"],
            "PASS_OPERATIONAL_ACCESS_FRAME",
        )
        self.assertEqual(
            passing_payload["operational_access_validation"]["locator_only_path_count"],
            2,
        )

        def expect_block(label: str, expected: str, mutate: object) -> None:
            with self.subTest(case=label):
                mutated = json.loads(json.dumps(payload))
                mutate(mutated)
                result = invoke(mutated, manifest, ledger, safe_root)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                body = json.loads(result.stdout)
                self.assertEqual(body["status"], "BLOCK_PRE_DISPATCH_ACCESS")
                self.assertIn(expected, body["operational_access_validation"]["reason"])

        expect_block(
            "missing operational frame",
            "requires top-level operational_access object",
            lambda body: body.pop("operational_access"),
        )
        other_helper = case_root / "other-helper.py"
        other_helper.write_text("print('other')\n", encoding="utf-8")
        expect_block(
            "helper not readable",
            "not in authority_readable_paths",
            lambda body: body["operational_access"]["helper_paths"].__setitem__(
                0,
                {
                    "path": str(other_helper.resolve()),
                    "sha256": hashlib.sha256(other_helper.read_bytes()).hexdigest(),
                },
            ),
        )
        expect_block(
            "safe source not readable",
            "safe-tree file is not in authority_readable_paths",
            lambda body: body["operational_access"]["authority_readable_paths"].remove(
                str((safe_root / "paper.md").resolve())
            ),
        )
        expect_block(
            "directory broad parent",
            "regular file, not a directory or special file",
            lambda body: body["operational_access"]["authority_readable_paths"].__setitem__(
                0, str(case_root.resolve())
            ),
        )
        for sensitive_kind, sensitive_path in (
            ("memories", case_root / ".codex" / "memories" / "record.md"),
            ("state db", case_root / ".codex" / "state_5.sqlite"),
        ):
            sensitive_path.parent.mkdir(parents=True, exist_ok=True)
            sensitive_path.write_text("history\n", encoding="utf-8")
            expect_block(
                f"sensitive {sensitive_kind}",
                "sensitive .codex history/state path",
                lambda body, path=sensitive_path: body["operational_access"]["authority_readable_paths"].__setitem__(
                    0, str(path.resolve())
                ),
            )
        symlink = case_root / "helper-alias.py"
        symlink.symlink_to(helper)
        expect_block(
            "symlink",
            "regular non-symlink file",
            lambda body: body["operational_access"]["authority_readable_paths"].__setitem__(
                0, str(symlink)
            ),
        )
        special = case_root / "helper.pipe"
        os.mkfifo(special)
        expect_block(
            "special file",
            "regular file, not a directory or special file",
            lambda body: body["operational_access"]["authority_readable_paths"].__setitem__(
                0, str(special.resolve())
            ),
        )
        expect_block(
            "relative path",
            "canonical and absolute",
            lambda body: body["operational_access"]["authority_readable_paths"].__setitem__(
                0, "paper.md"
            ),
        )
        expect_block(
            "noncanonical path",
            "canonical and absolute",
            lambda body: body["operational_access"]["authority_readable_paths"].__setitem__(
                0, str(safe_root.resolve()) + "/./paper.md"
            ),
        )
        source_path = str((safe_root / "paper.md").resolve())
        expect_block(
            "duplicate path",
            "duplicates path",
            lambda body: body["operational_access"]["authority_readable_paths"].__setitem__(
                1, source_path
            ),
        )
        expect_block(
            "locator overlap",
            "locator_only_paths must be disjoint",
            lambda body: body["operational_access"]["locator_only_paths"].__setitem__(
                0, source_path
            ),
        )
        expect_block(
            "helper hash mismatch",
            "sha256 mismatch",
            lambda body: body["operational_access"]["helper_paths"][0].__setitem__(
                "sha256", "0" * 64
            ),
        )
        expect_block(
            "absolute argv unbound",
            "absolute path is not in the bound readable/locator set",
            lambda body: body["operational_access"]["activation_argv"].append(
                str((case_root / "unbound.txt").resolve())
            ),
        )
        expect_block(
            "bare executable",
            "executable must be a canonical absolute authority_readable_path",
            lambda body: body["operational_access"]["activation_argv"].__setitem__(
                0, "python3"
            ),
        )
        locator_executable = payload["operational_access"]["locator_only_paths"][0]
        expect_block(
            "locator-only executable",
            "executable must be a canonical absolute authority_readable_path",
            lambda body: body["operational_access"]["activation_argv"].__setitem__(
                0, locator_executable
            ),
        )
        expect_block(
            "activation shell metacharacter",
            "shell metacharacters",
            lambda body: body["operational_access"]["activation_argv"].append("--flag;echo"),
        )


if __name__ == "__main__":
    unittest.main()
