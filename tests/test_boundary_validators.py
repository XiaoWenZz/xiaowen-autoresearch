from __future__ import annotations

import hashlib
import json
import re
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
                0,
                not_evaluated.stdout + not_evaluated.stderr,
            )
            self.assertEqual(
                json.loads(not_evaluated.stdout)["access_chronology"]["status"],
                "NOT_EVALUATED",
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
                "--trusted-access-ledger",
                ledger,
                "--plan-frozen-at",
                "2026-07-21T00:00:00Z",
            )
            self.assertEqual(regressed.returncode, 1)
            self.assertIn("regresses append-only chronology", regressed.stderr)


if __name__ == "__main__":
    unittest.main()
