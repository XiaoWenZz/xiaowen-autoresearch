from __future__ import annotations

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
    def test_high_recall_v3_template_passes_when_filled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
            text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "frozen value", text)
            prompt.write_text(text, encoding="utf-8")
            result = run(PROMPT_VALIDATOR, prompt)
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["verdict"], "PASS_EXTERNAL_OPPORTUNITY_PROMPT_STRUCTURE")

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
            self.assertIn("missing high-recall-v3 schema marker", result.stdout)
            self.assertIn("missing separate problem admission", result.stdout)
            self.assertIn("missing separate contribution forecast", result.stdout)

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


if __name__ == "__main__":
    unittest.main()
