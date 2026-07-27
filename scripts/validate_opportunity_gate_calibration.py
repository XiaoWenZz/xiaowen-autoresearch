#!/usr/bin/env python3
"""Validate a retrospective Opportunity Search admission calibration artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PASS = "PASS_OPPORTUNITY_GATE_CALIBRATION"
FAIL = "FAIL_OPPORTUNITY_GATE_CALIBRATION"
SCHEMA_V1 = "opportunity-gate-calibration-v1"
SCHEMA_V2 = "opportunity-gate-calibration-v2"
SCHEMAS = {SCHEMA_V1, SCHEMA_V2}
PROBE = "PROBE"
ADMISSION_VALUES = {
    PROBE,
    "HOLD_INFORMATION",
    "HOLD_CARRIER",
    "DROP_PROBLEM_EXACT_REDUCTION",
    "DROP_NO_DECISION",
    "ROUTE_BROADER_ARTIFACT",
}
RETENTION_VALUES = {
    "PROBE_READY",
    "EVIDENCE_GAP_LEAD",
    "BROADER_ARTIFACT_LEAD",
    "CLOSED",
}
EXPECTED_RETENTION = {
    "PROBE": "PROBE_READY",
    "HOLD_INFORMATION": "EVIDENCE_GAP_LEAD",
    "HOLD_CARRIER": "EVIDENCE_GAP_LEAD",
    "ROUTE_BROADER_ARTIFACT": "BROADER_ARTIFACT_LEAD",
    "DROP_PROBLEM_EXACT_REDUCTION": "CLOSED",
    "DROP_NO_DECISION": "CLOSED",
}


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(payload: dict[str, Any]) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    controls = payload.get("controls")
    schema = payload.get("schema_version")
    if schema not in SCHEMAS:
        errors.append(f"schema_version must be one of {sorted(SCHEMAS)}")
    is_v2 = schema == SCHEMA_V2
    for field in ("domain", "gate_version", "evidence_freeze", "decision_rule"):
        if not nonempty_string(payload.get(field)):
            errors.append(f"missing non-empty {field}")
    if not isinstance(controls, list):
        errors.append("controls must be a list")
        controls = []

    identifiers: set[str] = set()
    positive_count = 0
    negative_count = 0
    false_rejects = 0
    hard_false_rejects = 0
    probe_misses = 0
    false_admits = 0
    over_retained_negatives = 0

    for index, control in enumerate(controls):
        prefix = f"controls[{index}]"
        if not isinstance(control, dict):
            errors.append(f"{prefix} must be an object")
            continue
        identifier = control.get("id")
        if not nonempty_string(identifier):
            errors.append(f"{prefix}.id must be non-empty")
        elif identifier in identifiers:
            errors.append(f"duplicate control id: {identifier}")
        else:
            identifiers.add(identifier)

        kind = control.get("kind")
        if kind == "retrospective_positive":
            positive_count += 1
        elif kind == "negative_control":
            negative_count += 1
        else:
            errors.append(f"{prefix}.kind must be retrospective_positive or negative_control")

        for field in (
            "pre_signal_state",
            "expected_problem_admission",
            "observed_problem_admission",
            "contribution_forecast",
            "gate_decision_rationale",
        ):
            if not nonempty_string(control.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")

        sources = control.get("source_paths")
        if not isinstance(sources, list) or not sources or not all(nonempty_string(item) for item in sources):
            errors.append(f"{prefix}.source_paths must be a non-empty string list")

        expected = control.get("expected_problem_admission")
        observed = control.get("observed_problem_admission")
        if expected not in ADMISSION_VALUES:
            errors.append(f"{prefix}.expected_problem_admission is invalid")
        if observed not in ADMISSION_VALUES:
            errors.append(f"{prefix}.observed_problem_admission is invalid")
        if kind == "retrospective_positive" and expected != PROBE:
            errors.append(f"{prefix} retrospective positive must expect PROBE")
        if kind == "negative_control" and expected == PROBE:
            errors.append(f"{prefix} negative control cannot expect PROBE")

        retention = control.get("retention_state")
        if is_v2:
            if retention not in RETENTION_VALUES:
                errors.append(f"{prefix}.retention_state is invalid")
            if not nonempty_string(control.get("next_evidence_action")):
                errors.append(f"{prefix}.next_evidence_action must be non-empty")
            expected_retention = EXPECTED_RETENTION.get(observed)
            if expected_retention is not None and retention != expected_retention:
                errors.append(
                    f"{prefix}.retention_state must be {expected_retention} "
                    f"for observed admission {observed}"
                )

        if kind == "retrospective_positive" and observed != PROBE:
            probe_misses += 1
            if is_v2:
                if retention == "CLOSED":
                    hard_false_rejects += 1
            else:
                false_rejects += 1
        if kind == "negative_control" and observed == PROBE:
            false_admits += 1
        if (
            is_v2
            and kind == "negative_control"
            and observed != PROBE
            and retention in {"EVIDENCE_GAP_LEAD", "BROADER_ARTIFACT_LEAD"}
        ):
            over_retained_negatives += 1

    if positive_count < 3:
        errors.append("at least three retrospective positives are required")
    if negative_count < 3:
        errors.append("at least three negative controls are required")
    if not is_v2 and false_rejects:
        errors.append(f"gate has {false_rejects} retrospective false rejects")
    if is_v2 and hard_false_rejects:
        errors.append(f"gate has {hard_false_rejects} hard retrospective false rejects")
    if false_admits:
        errors.append(f"gate has {false_admits} negative false admits")

    if is_v2:
        summary = {
            "control_count": len(controls),
            "false_admits": false_admits,
            "hard_false_rejects": hard_false_rejects,
            "negative_controls": negative_count,
            "over_retained_negatives": over_retained_negatives,
            "positive_controls": positive_count,
            "probe_misses": probe_misses,
        }
    else:
        summary = {
            "control_count": len(controls),
            "false_admits": false_admits,
            "false_rejects": false_rejects,
            "negative_controls": negative_count,
            "positive_controls": positive_count,
        }
    declared = payload.get("summary")
    if declared is not None and declared != summary:
        errors.append(f"declared summary does not match computed summary: {summary}")
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        errors = ["top-level JSON value must be an object"]
        summary: dict[str, int] = {}
    else:
        errors, summary = validate(payload)
    result = {
        "artifact": str(args.artifact),
        "errors": errors,
        "summary": summary,
        "verdict": PASS if not errors else FAIL,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
