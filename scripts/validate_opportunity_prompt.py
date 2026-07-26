#!/usr/bin/env python3
"""Structural lint for assembled external Opportunity Search prompts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PASS = "PASS_EXTERNAL_OPPORTUNITY_PROMPT_STRUCTURE"
FAIL = "FAIL_EXTERNAL_OPPORTUNITY_PROMPT_STRUCTURE"


def has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def validate(text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not has_any(
        text,
        (r"OPPORTUNITY_SEARCH_SCHEMA\s*:\s*high-recall-v2",),
    ):
        errors.append("missing high-recall-v2 schema marker")

    placeholders = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
    if placeholders:
        errors.append("unresolved placeholders: " + ", ".join(placeholders))

    stages = ["Opportunity Search", "Problem Scout", "Contribution Gate", "Confirmatory"]
    positions = [text.lower().find(stage.lower()) for stage in stages]
    if any(position < 0 for position in positions):
        errors.append("missing full stage chain: " + " -> ".join(stages))
    elif positions != sorted(positions):
        errors.append("stage inversion: expected " + " -> ".join(stages))

    required = {
        "evidence labels FACT / INFERENCE / HYPOTHESIS": (
            r"\bFACT\b[\s\S]{0,500}\bINFERENCE\b[\s\S]{0,500}\bHYPOTHESIS\b",
            r"\bFACT\b[\s\S]*\bINFERENCE\b[\s\S]*\bHYPOTHESIS\b",
        ),
        "actor-level decision": (r"actor", r"affected actor", r"受影响.*主体", r"行动者"),
        "target estimand": (r"target estimand", r"目标估计量", r"目标量"),
        "causal bottleneck": (r"causal bottleneck", r"因果瓶颈"),
        "strongest preserving reduction": (r"strongest preserving", r"最强.*保持.*约化"),
        "divergent pass": (r"divergent pass", r"发散.*pass", r"发散阶段"),
        "convergent pass": (r"convergent pass", r"收敛.*pass", r"收敛阶段"),
        "label-free ideation": (
            r"do not assign[^.\n]{0,160}(PROBE|HOLD|DROP)",
            r"不(?:要|得)[^。\n]{0,120}(?:PROBE|HOLD|DROP)",
        ),
        "separate problem admission": (r"problem_admission", r"problem admission", r"问题准入"),
        "separate contribution forecast": (
            r"contribution_forecast",
            r"contribution forecast",
            r"贡献预判",
        ),
        "forecast cannot determine admission": (
            r"never use[^.\n]{0,120}contribution_forecast[^.\n]{0,120}problem_admission",
            r"forecast[^.\n]{0,120}(?:cannot|must not)[^.\n]{0,120}admission",
            r"贡献预判[^。\n]{0,120}不得[^。\n]{0,120}准入",
        ),
        "joint-feasibility certificate": (
            r"joint-feasibility certificate",
            r"joint feasibility certificate",
            r"联合可行性.*(?:证书|检查表)",
        ),
        "joint-feasibility dimensions": (
            r"observables[\s\S]{0,1500}ordering[\s\S]{0,1500}rendezvous[\s\S]{0,1500}(state|storage)[\s\S]{0,1500}(objective|architecture)[\s\S]{0,1500}(cost|bytes|latency|compute)[\s\S]{0,1500}deployment",
            r"可观测[\s\S]{0,1500}顺序[\s\S]{0,1500}(?:会合|参与窗口)[\s\S]{0,1500}(?:状态|存储)[\s\S]{0,1500}(?:目标|架构)[\s\S]{0,1500}(?:成本|字节|延迟|算力)[\s\S]{0,1500}部署",
        ),
        "controlled-carrier admission": (
            r"controlled carrier[^.\n]{0,160}(adequate|admissible)",
            r"受控(?:载体|carrier)[^。\n]{0,120}(?:足够|可准入)",
        ),
        "conditional natural-carrier gate": (
            r"natural carrier[^.\n]{0,220}(only when|only if)",
            r"自然(?:载体|carrier)[^。\n]{0,160}只有当",
        ),
        "three positive calibration controls": (
            r"at least three retrospective positives",
            r"至少三个.*历史正例",
            r"至少 3 个.*历史正例",
        ),
        "three negative calibration controls": (
            r"at least three negative",
            r"至少三个.*负例",
            r"至少 3 个.*负例",
        ),
        "mechanism-deletion control": (r"mechanism[- ]deletion", r"机制删除"),
        "positive / negative / ambiguous actions": (
            r"positive[\s\S]{0,200}negative[\s\S]{0,200}ambiguous",
            r"正向[\s\S]{0,200}负向[\s\S]{0,200}模糊",
        ),
        "primary-source contract": (r"primary[- ]source", r"primary source", r"原始来源"),
        "scoped closure semantics": (r"scoped closure", r"exact fingerprint", r"精确.*关闭"),
        "one selected Scout": (r"at most one", r"最多选择一个", r"唯一.*Scout"),
        "Scout admission terminal": (r"ADMIT_TO_PROBLEM_SCOUT",),
        "search-exhaustion terminal": (r"SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION",),
        "exact-reduction admission status": (r"DROP_PROBLEM_EXACT_REDUCTION",),
        "no-decision admission status": (r"DROP_NO_DECISION",),
        "broader-artifact route": (r"ROUTE_BROADER_ARTIFACT",),
        "field-level no-go guard": (r"field-level NO-GO", r"领域级.*NO-GO", r"不是.*NO-GO"),
        "deferred publication burden": (
            r"do not require[^.\n]{0,240}(paper path|conference|novelty matrix)",
            r"不(?:要|得)要求[^。\n]{0,180}(?:论文路径|完整创新性|会议)",
        ),
    }
    for label, patterns in required.items():
        if not has_any(text, patterns):
            errors.append(f"missing {label}")

    if not has_any(
        text,
        (
            r"do not require[^\n]{0,120}official",
            r"official[^\n]{0,120}(not required|is not required)",
            r"不要求[^\n]{0,120}official",
            r"无需[^\n]{0,120}官方",
        ),
    ):
        warnings.append("official executable code is not explicitly non-mandatory")

    if has_any(text, (r"\bNO_STRONG_IDEA\b", r"\bNO_VIABLE_IDEA\b")):
        warnings.append("broad no-idea label present; verify it is prohibited rather than allowed")

    divergent_position = text.lower().find("divergent pass")
    convergent_position = text.lower().find("convergent pass")
    if divergent_position >= 0 and convergent_position >= 0 and divergent_position > convergent_position:
        errors.append("search-pass inversion: divergent pass must precede convergent pass")

    if len(text.split()) < 450 and len(text) < 2500:
        warnings.append("prompt is unusually short for a bounded external Opportunity Search")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", type=Path)
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    args = parser.parse_args()

    text = args.prompt.read_text(encoding="utf-8")
    errors, warnings = validate(text)
    payload = {
        "errors": errors,
        "prompt": str(args.prompt),
        "verdict": PASS if not errors else FAIL,
        "warnings": warnings,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
