from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "SKILL.md"
INTERFACE = ROOT / "agents" / "openai.yaml"
REFERENCES = ROOT / "references"
WORKSPACE_AGENTS_VALUE = os.environ.get("XAR_WORKSPACE_AGENTS")
WORKSPACE_AGENTS = Path(WORKSPACE_AGENTS_VALUE) if WORKSPACE_AGENTS_VALUE else None

BASELINE_SKILL_BYTES = 21_199
BASELINE_SKILL_LINES = 345
EXPECTED_HOT_REFERENCES = {
    "references/orchestration.md",
    "references/problem-space.md",
    "references/research-integrity.md",
    "references/research-map-maintenance.md",
    "references/state-schema.md",
}


def skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def skill_body() -> str:
    return skill_text().split("---", 2)[2]


def frontmatter() -> dict[str, object]:
    raw = skill_text().split("---", 2)[1]
    name_match = re.search(r"(?m)^name:\s*(\S+)\s*$", raw)
    description_match = re.search(r"(?ms)^description:\s*>-\s*\n(?P<body>(?:  .*\n?)+)$", raw)
    if name_match is None or description_match is None:
        raise AssertionError("Skill frontmatter is not the expected minimal scalar shape")
    description = " ".join(line.strip() for line in description_match.group("body").splitlines())
    return {"name": name_match.group(1), "description": description}


def interface_metadata() -> dict[str, str]:
    result: dict[str, str] = {}
    for match in re.finditer(r'(?m)^  (?P<key>[a-z_]+):\s+(?P<value>".*")$', INTERFACE.read_text(encoding="utf-8")):
        value = json.loads(match.group("value"))
        if not isinstance(value, str):
            raise AssertionError("Interface metadata values must be strings")
        result[match.group("key")] = value
    return result


def sections() -> dict[str, str]:
    result: dict[str, str] = {}
    heading = "preamble"
    chunks: list[str] = []
    for line in skill_body().splitlines():
        if line.startswith("## "):
            result[heading] = re.sub(r"\s+", " ", "\n".join(chunks)).strip()
            heading = line[3:]
            chunks = []
        else:
            chunks.append(line)
    result[heading] = re.sub(r"\s+", " ", "\n".join(chunks)).strip()
    return result


def markdown_links(path: Path) -> set[str]:
    return set(re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", path.read_text(encoding="utf-8")))


class SkillRouterTest(unittest.TestCase):
    def test_deletion_first_budget_and_readability(self) -> None:
        text = skill_text()
        lines = text.splitlines()

        self.assertLessEqual(len(text.encode("utf-8")), int(BASELINE_SKILL_BYTES * 0.60))
        self.assertLessEqual(len(lines), BASELINE_SKILL_LINES // 2)
        self.assertEqual(sum(line.startswith("## ") for line in lines), 8)
        self.assertLessEqual(max(map(len, lines)), 120)
        self.assertRegex(text, r"(?m)^# Xiaowen AutoResearch$")

    def test_frontmatter_targets_boundaries_and_excludes_ordinary_work(self) -> None:
        metadata = frontmatter()
        self.assertEqual(set(metadata), {"name", "description"})
        self.assertEqual(metadata["name"], "xiaowen-autoresearch")
        description = str(metadata["description"])

        self.assertRegex(
            description,
            r"(?is)scientific evidence.*prospective contracts.*protected.*remote/GPU.*claims.*closure",
        )
        self.assertRegex(
            description,
            r"(?is)Do not invoke.*ordinary literature or code.*reversible implementation/debugging.*frozen pure execution",
        )

    def test_interface_metadata_matches_the_kernel(self) -> None:
        metadata = interface_metadata()
        self.assertEqual(set(metadata), {"display_name", "short_description", "default_prompt"})
        self.assertEqual(metadata["display_name"], "Xiaowen AutoResearch")
        self.assertGreaterEqual(len(metadata["short_description"]), 25)
        self.assertLessEqual(len(metadata["short_description"]), 64)
        self.assertRegex(metadata["default_prompt"], r"^Use \$xiaowen-autoresearch\b")
        self.assertRegex(
            metadata["default_prompt"],
            r"(?i)scientific contract.*protected release.*evidence.*closure.*continuous owner",
        )

    def test_every_local_markdown_link_resolves(self) -> None:
        markdown_files = [SKILL, *sorted(REFERENCES.glob("*.md")), *sorted((ROOT / "assets").glob("*.md"))]
        for source in markdown_files:
            for target in markdown_links(source):
                if "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (source.parent / target).resolve()
                with self.subTest(source=source.name, target=target):
                    self.assertTrue(resolved.is_file(), str(resolved))

    def test_progressive_disclosure_is_trigger_matched(self) -> None:
        linked = {target for target in markdown_links(SKILL) if target.startswith("references/")}
        self.assertEqual(linked, EXPECTED_HOT_REFERENCES)

        body_sections = sections()
        load_section = body_sections["2. Load only the active boundary"]
        controller_section = body_sections["7. Use Controller v5 only on its cold boundary"]
        self.assertRegex(load_section, r"(?is)Default to Lite.*Use Managed only when")
        self.assertRegex(load_section, r"(?is)Managed activation.*long job.*external block.*orchestration\.md")
        self.assertRegex(load_section, r"(?is)state-schema\.md.*only when durable Controller state is touched")
        self.assertRegex(controller_section, r"(?is)Load the orchestration reference.*only for Managed")

    def test_hard_scientific_invariants_remain_explicit(self) -> None:
        contract = sections()["3. Freeze the evidence contract prospectively"]
        evidence = sections()["5. Enforce the hard evidence boundary"]
        independence = sections()["6. Require independence only where it changes validity"]

        for pattern in (
            r"(?is)question.*hypothesis.*estimand.*data/split/exposure",
            r"(?is)primary metric.*threshold or MPE.*seeds.*stop/action rule.*claim",
            r"(?is)strongest fair matched-cost baseline.*mechanism-deletion control",
            r"(?is)code.*config.*data.*model.*environment.*command.*output.*run identity",
            r"(?is)pessimistic decision-complete resource ceiling",
        ):
            with self.subTest(pattern=pattern):
                self.assertRegex(contract, pattern)

        for pattern in (
            r"(?is)strict_result_blind.*safe tree.*operational_access.*before dispatch",
            r"(?is)After utility or protected-outcome access.*forbid outcome-conditioned rescue",
            r"(?is)exact debit.*hard ceiling",
            r"(?is)Preserve raw outputs, failures, anomalies, and deviations before interpretation",
            r"(?is)completed.*contract-consistent.*evidence-eligible.*independently verified.*claim-accepted",
            r"(?is)negative/null conclusions scoped",
        ):
            with self.subTest(pattern=pattern):
                self.assertRegex(evidence, pattern)

        self.assertRegex(
            independence,
            r"(?is)physically distinct.*only for protected or confirmatory.*publication.*closure.*fairness/exposure",
        )

    def test_reversible_preutility_work_stays_with_one_owner(self) -> None:
        engineering = sections()["4. Keep reversible engineering in one owner"]
        for pattern in (
            r"(?is)one continuous Sol owner.*pre-utility engineering.*real carrier.*final scientific decision",
            r"(?is)Before utility or protected access.*repair path.*download.*transport.*launcher.*carrier",
            r"(?is)do not create a governance-only terminal.*new objective.*Controller lifecycle write.*user-rescue",
            r"(?is)unchanged scientific identity.*cumulative hard ceiling",
            r"(?is)carrier_generation.*same scientific attempt",
            r"(?is)FINAL\+NON_TERMINAL.*existing Controller v5 recovery",
            r"(?is)E0 candidate.*does not delegate to Luna",
        ):
            with self.subTest(pattern=pattern):
                self.assertRegex(engineering, pattern)

    def test_controller_and_external_block_remain_cold(self) -> None:
        controller = sections()["7. Use Controller v5 only on its cold boundary"]
        self.assertRegex(
            controller,
            r"(?is)only for Managed activation.*registered long jobs.*genuine external blocks.*final evidence transition",
        )
        self.assertRegex(controller, r"(?is)Keep an internal engineering gap owned")
        self.assertRegex(
            controller,
            r"(?is)finite `BLOCKED` state requires a genuine external fact.*observer.*reopening check.*deadline",
        )
        self.assertRegex(controller, r"(?is)existing v5 terminal, callback, cursor, job, and recovery semantics")

    def test_hot_path_omits_resident_choreography_and_tool_cookbooks(self) -> None:
        text = skill_text()
        forbidden = (
            r"startup_chain_authority",
            r"record-startup-attempt",
            r"workflow_evolution_gate\.py",
            r"validate_model_route\.py",
            r"(?:LUNA|MODEL)_ROUTE_DISPATCH_ID",
            r"route-dispatch-id",
            r"Lead\s*->\s*Builder",
            r"title/pin",
            r"watchdog",
        )
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE))

    def test_review_tier_and_retain_gate_are_outcome_based(self) -> None:
        review = sections()["8. Review changes and report completion"]
        self.assertRegex(
            review,
            r"(?is)broad refactors.*root-cause redesigns.*hard-boundary changes.*fixed-commit review bundle",
        )
        self.assertRegex(review, r"(?is)Narrow, reversible fixes may skip Pro")
        self.assertRegex(
            review,
            r"(?is)Retain.*only when hard reliability is non-inferior.*research throughput or operator cost improves",
        )

    def test_router_tests_do_not_lock_exact_prose(self) -> None:
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        locked_assertions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"assertIn", "assertNotIn"}
        ]
        self.assertEqual(locked_assertions, [])

    @unittest.skipUnless(WORKSPACE_AGENTS is not None, "set XAR_WORKSPACE_AGENTS for paired-router validation")
    def test_workspace_router_matches_the_continuous_owner_kernel(self) -> None:
        assert WORKSPACE_AGENTS is not None
        workspace = WORKSPACE_AGENTS.read_text(encoding="utf-8")
        self.assertRegex(workspace, r"(?is)workspace router.*live.*xiaowen-autoresearch")
        self.assertRegex(workspace, r"(?is)One continuous.*owner|one local decision-complete owner")
        for pattern in (r"(?i)scientific identity", r"(?i)protected", r"(?i)no-rescue", r"(?i)hard resource ceilings"):
            with self.subTest(pattern=pattern):
                self.assertRegex(workspace, pattern)
        self.assertIsNone(re.search(r"four roles\s+`Controller\|Explorer\|Audit\|Executor`", workspace))


if __name__ == "__main__":
    unittest.main()
