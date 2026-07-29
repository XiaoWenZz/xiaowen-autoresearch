from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "SKILL.md"


class SkillRouterTest(unittest.TestCase):
    def test_core_router_is_compact_but_not_empty(self) -> None:
        lines = SKILL.read_text(encoding="utf-8").splitlines()
        self.assertGreaterEqual(len(lines), 200)
        self.assertLessEqual(len(lines), 300)

    def test_frontmatter_excludes_pure_execution_workers(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        self.assertIn("Do not invoke this skill in a pure implementation", frontmatter)
        self.assertIn("the frozen contract", frontmatter)

    def test_every_direct_reference_link_resolves(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        linked = set(re.findall(r"\]\((references/[^)]+\.md)\)", text))
        self.assertGreater(len(linked), 0)
        for relative in linked:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file(), relative)

    def test_execution_plane_has_no_runtime_governance_family(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        flat = " ".join(text.split())
        self.assertIn("Do not invoke or load this skill in that executor", flat)
        self.assertIn("The contract itself is the only task capsule", flat)
        self.assertIn("one fused command or long-lived local process", flat)
        self.assertIn("do not wake a model for each check", flat)
        self.assertIn("Keep Codex thread transport outside that fused local action", flat)
        self.assertIn("functions.exec` must not invoke `send_message_to_thread`", flat)
        self.assertIn("ordinary top-level delivery and ACK waiting", flat)
        for forbidden in (
            "references/context-bootstrap.md",
            "scripts/context_capsule.py",
            "PENDING_CALLBACK_TELEMETRY",
            "context-callback-receipt",
            "controller-receipt.json",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
        self.assertFalse((ROOT / "references" / "context-bootstrap.md").exists())
        self.assertFalse((ROOT / "scripts" / "context_capsule.py").exists())
        self.assertFalse((ROOT / "tests" / "test_context_capsule.py").exists())

    def test_lite_is_default_and_managed_triggers_are_explicit(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        flat = " ".join(text.split())
        required = (
            "Default to `operating_weight=lite`",
            "no managed state file, no lease registry, no lane snapshot, no watchdog",
            "more than one session or owner",
            "remote/GPU, paid, public, or unattended",
            "Confirmatory or publication-facing",
            "Remove managed runtime state when the trigger closes",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, flat)

    def test_mechanical_receiver_is_one_shot_and_non_adjudicating(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        flat = " ".join(text.split())
        required = (
            "one pre-bound, one-shot receiver",
            "exact task/dispatch/lease/terminal tuple",
            "terminal path and digest",
            "callback ordering, idempotency",
            "writes one immutable ACK",
            "real message-tool receipt",
            "must not interpret evidence or choose the next route",
            "long-lived research Controller receives only the compact post-closure receipt",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, flat)

    def test_receiver_activation_is_absolute_and_single_boundary(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        flat = " ".join(text.split())
        required = (
            "absolute repository/workdir",
            "absolute terminal path and digest",
            "absolute ACK path",
            "receiver destination, and worker target",
            "compact, LF-only receiver activation",
            "fail-closed canonical encoding",
            "ordinary top-level `send_message_to_thread` call",
            "ordinary top-level `wait_threads` call",
            "must not reread or rehash the terminal, poll status, inspect logs",
            "hide either thread operation inside `functions.exec`",
            "may not discover a cwd or path",
            "separately read `AGENTS.md` or the contract",
            "runs one deterministic local command in the bound absolute workdir",
            "Only on validation success",
            "bound worker target",
            "must not call a Codex thread operation from `functions.exec`",
            "emit commentary before ACK",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, flat)
        self.assertNotIn("exactly one post-terminal model/tool boundary", flat)
        self.assertNotIn("only model/tool boundary through ACK", flat)

    def test_cross_stage_hard_controls_remain(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        flat = " ".join(text.split())
        required = (
            "cannot override platform, system, developer, or `AGENTS.md` authority",
            "protected outcomes",
            "Outcome-blind repair stays inside the unchanged contract and budget",
            "one canonical owner",
            "callback_delivery=unconfirmed",
            "Pro and same-model review are advisory",
            "Absolute token totals and governance file counts are diagnostics",
            "Telemetry is external read-only evaluation after callback",
            "first executor activation through successful receiver ACK message-tool delivery",
            "Controller's later receipt and adjudication separately",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, flat)

    def test_managed_dirty_behaviors_are_not_duplicated_in_router(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        flat = " ".join(text.split())
        for detailed_policy in (
            "Define backlog saturation narrowly",
            "Apply `solve-or-bind` before retaining any `HOLD`",
            "After an independently verified negative, do not equate closure",
        ):
            with self.subTest(detailed_policy=detailed_policy):
                self.assertNotIn(detailed_policy, text)
        self.assertIn(
            "single source for the preserved continuous-search, finite-HOLD, and",
            flat,
        )

    def test_documented_helpers_exist_and_exclude_capsule_helper(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        helpers = set(re.findall(r"python3 (scripts/[^ ]+\.py) --help", text))
        self.assertGreater(len(helpers), 0)
        self.assertNotIn("scripts/context_capsule.py", helpers)
        for relative in helpers:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
