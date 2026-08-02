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
        (r"OPPORTUNITY_SEARCH_SCHEMA\s*:\s*source-first-high-recall-v4",),
    ):
        errors.append("missing source-first-high-recall-v4 schema marker")

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
        "source-first observatory": (
            r"source[- ]first observatory",
            r"source observatory",
            r"来源优先.*观测",
        ),
        "recent primary proceedings": (
            r"current and previous 18 months",
            r"最近 18 个月",
        ),
        "source anomaly inputs": (
            r"negative ablations[\s\S]{0,500}limitations[\s\S]{0,500}sensitivity",
            r"负向消融[\s\S]{0,500}局限[\s\S]{0,500}敏感性",
        ),
        "source-family and assumption-lineage telemetry": (
            r"source_family_id[\s\S]{0,700}assumption_lineage",
        ),
        "non-binding source-family telemetry": (
            r"(?:source.family|family counts)[\s\S]{0,700}(?:non-binding|do not establish)[\s\S]{0,700}(?:independence|novelty|problem_admission)",
        ),
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
        "separate retention state": (
            r"retention_state",
            r"retention state",
            r"保留状态",
        ),
        "evidence-gap retention": (
            r"EVIDENCE_GAP_LEAD",
            r"evidence[- ]gap lead",
            r"证据缺口.*保留",
        ),
        "broader-artifact retention": (
            r"BROADER_ARTIFACT_LEAD",
            r"broader[- ]artifact lead",
            r"更广.*产物.*保留",
        ),
        "only drops are closed": (
            r"only[^.\n]{0,160}DROP[^.\n]{0,160}CLOSED",
            r"only the two[^.\n]{0,160}DROP",
            r"只有[^。\n]{0,120}DROP[^。\n]{0,120}CLOSED",
        ),
        "retained lead next action": (
            r"retained lead[^.\n]{0,180}(next evidence action|reopening fact)",
            r"保留.*(?:下一证据动作|重新开启事实)",
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
        "proportional readiness ladder": (
            r"R0\s*->\s*R1\s*->\s*R2\s*->\s*R3",
        ),
        "scientific contract precedes scientific outcome": (
            r"R2[\s\S]{0,350}(?:identity|power)[\s\S]{0,350}before any scientific[\s\S]{0,80}outcome",
        ),
        "R1 is non-scientific": (
            r"R1[\s\S]{0,500}(?:no scientific payload|outcome-blind)[\s\S]{0,500}not a scientific negative",
        ),
        "no numeric novelty admission score": (
            r"numeric LLM or expert novelty score as an admission threshold",
        ),
        "Scout admission terminal": (r"ADMIT_TO_PROBLEM_SCOUT",),
        "search-exhaustion terminal": (r"SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION",),
        "search exhaustion preserves retained leads": (
            r"SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION[\s\S]{0,900}(retained|EVIDENCE_GAP_LEAD|BROADER_ARTIFACT_LEAD)",
            r"搜索预算耗尽[\s\S]{0,600}保留",
        ),
        "exact-reduction admission status": (r"DROP_PROBLEM_EXACT_REDUCTION",),
        "no-decision admission status": (r"DROP_NO_DECISION",),
        "broader-artifact route": (r"ROUTE_BROADER_ARTIFACT",),
        "field-level no-go guard": (r"field-level NO-GO", r"领域级.*NO-GO", r"不是.*NO-GO"),
        "deferred publication burden": (
            r"do not require[^.\n]{0,240}(paper path|conference|novelty matrix)",
            r"不(?:要|得)要求[^。\n]{0,180}(?:论文路径|完整创新性|会议)",
        ),
        "no federation-only or non-copyable pre-signal gate": (
            r"do not require[^.\n]{0,240}federation[- ]only[^.\n]{0,240}non[- ]copyable",
            r"不(?:要|得)要求[^。\n]{0,180}(?:联邦专属|federation[- ]only)[^。\n]{0,180}(?:不可复制|non[- ]copyable)",
        ),
        "single complete reduction witness": (
            r"one verified complete (?:(?:executable|formal)(?: or (?:executable|formal))? )?witness",
            r"single verified complete (?:implementation|witness|construction)",
            r"一个(?:已验证|可验证)的完整(?:可执行|形式化)?见证",
        ),
        "generic operation stays a challenge": (
            r"generic (?:operation|repair|analogue)[^.]{0,260}(?:challenge|baseline)[^.]{0,260}(?:before signal|pre-signal)",
            r"通用(?:操作|修复|类比)[^。\n]{0,160}(?:挑战|基线)[^。\n]{0,160}(?:信号前|预信号)",
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

    inversion_patterns = (
        r"(?:must|required?|only if|hard gate|reject)[^.\n]{0,220}(?:federation[- ]only|non[- ]copyable)",
        r"(?:federation[- ]only|non[- ]copyable)[^.\n]{0,220}(?:must|required?|hard gate|reject)",
        r"HARD_BOUNDARY_UNSATISFIED[\s\S]{0,500}(?:federation[- ]only|non[- ]copyable)",
        r"(?:DROP_PROBLEM_EXACT_REDUCTION|DROP_NO_DECISION)[^.\n]{0,220}(?:copyable|centralizable)",
        r"(?:copyable|centralizable)[^.\n]{0,220}(?:DROP_PROBLEM_EXACT_REDUCTION|DROP_NO_DECISION)",
    )
    for pattern in inversion_patterns:
        matches = re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        hard_match = False
        for match in matches:
            sentence_start = max(
                text.rfind(".", 0, match.start()),
                text.rfind("!", 0, match.start()),
                text.rfind("?", 0, match.start()),
                text.rfind("。", 0, match.start()),
            )
            sentence_end_candidates = [
                position
                for position in (
                    text.find(".", match.end()),
                    text.find("!", match.end()),
                    text.find("?", match.end()),
                    text.find("。", match.end()),
                )
                if position >= 0
            ]
            sentence_end = min(sentence_end_candidates) if sentence_end_candidates else len(text)
            sentence = text[sentence_start + 1 : sentence_end]
            if has_any(
                sentence,
                (
                    r"\bdo not\b",
                    r"\bmust not\b",
                    r"\bnever\b",
                    r"\bnot required\b",
                    r"\bcannot determine\b",
                    r"不(?:要|得|应)",
                    r"不能决定",
                ),
            ):
                continue
            hard_match = True
            break
        if hard_match:
            errors.append(
                "pre-signal hard-gate inversion: federation-only, non-copyable, "
                "copyability, or hypothetical centralizability cannot determine "
                "problem admission"
            )
            break

    process_delta_inversions = {
        "source-family telemetry cannot gate problem admission": (
            r"source_family_id[^.\n]{0,220}(?:Jaccard|overlap|threshold)[^.\n]{0,220}(?:DROP_|PROBE|problem_admission)",
        ),
        "mechanism depth cannot determine problem admission": (
            r"mechanism_depth[^.\n]{0,220}determines?[^.\n]{0,220}(?:problem_admission|PROBE|DROP_)",
        ),
        "R1 cannot access scientific outcomes": (
            r"R1[^.\n]{0,220}(?:may|must|can)[^.\n]{0,220}(?:read|expose|interpret)[^.\n]{0,220}(?:protected|public-test|held-out|scientific) outcomes?",
        ),
        "R2 cannot follow scientific outcomes": (
            r"R2[^.\n]{0,220}after[^.\n]{0,220}scientific outcomes?",
            r"scientific outcomes?[^.\n]{0,220}before[^.\n]{0,220}R2",
        ),
        "numeric novelty score cannot gate admission": (
            r"numeric[^.\n]{0,120}novelty score[^.\n]{0,120}>=?[^.\n]{0,120}determines?[^.\n]{0,120}(?:problem_admission|PROBE|DROP_)",
        ),
    }
    for error, patterns in process_delta_inversions.items():
        if has_any(text, patterns):
            errors.append(error)

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
