from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "SKILL.md"
ORCHESTRATION = ROOT / "references" / "orchestration.md"
INTEGRITY = ROOT / "references" / "research-integrity.md"


def flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class SkillRouterTest(unittest.TestCase):
    def test_core_router_is_compact_but_not_empty(self) -> None:
        lines = SKILL.read_text(encoding="utf-8").splitlines()
        self.assertGreaterEqual(len(lines), 180)
        self.assertLessEqual(len(lines), 266)

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

    def test_lite_local_single_owner_creates_no_managed_machinery(self) -> None:
        router = flat(SKILL)
        required = (
            "Default to `operating_weight=lite`",
            "Classify by side effects and coordination",
            "A user-visible task is the task capsule and delivery surface",
            "zero Program/Epoch, dispatch, lease, activation, lane, ledger, registry, or chronology records",
            "zero watchdog, heartbeat, continuity automation, callback sink, or blocking callback ACK roundtrip",
            "no duplicate task capsule",
            "at most one terminal only when durable evidence is genuinely needed",
            "local source/literature/code/workflow audit",
            "one one-shot Pro advisory remain Lite",
            "Do not retrofit Managed ceremony onto completed Lite work",
            "`Lite` removes coordination machinery only; it does not waive the scientific hard controls in section 6",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

    def test_managed_escalation_is_side_effect_triggered(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "remote or unattended process",
            "protected outcomes",
            "multiple write-capable owners",
            "shared global research state, queue, or write lease",
            "paid, public, production, irreversible, or third-party action",
            "Confirmatory scientific decision requires independent ownership",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        self.assertIn("not by the labels “research,” “audit,” “Scout,” or “multi-step.”", router)

    def test_execution_plane_has_no_runtime_governance_family(self) -> None:
        router = flat(SKILL)
        self.assertIn("do not invoke or load this skill there", router)
        self.assertIn("The contract itself is the only task capsule", router)
        self.assertIn("one fused command or long-lived local process", router)
        self.assertIn("do not wake a model for each check", router)
        self.assertIn("A user-visible local executor returns its final directly", router)
        for forbidden in (
            "one pre-bound, one-shot receiver",
            "absolute ACK path",
            "LF-only receiver activation",
            "ordinary top-level `wait_threads` call",
            "ordinary top-level delivery and ACK waiting",
            "references/context-bootstrap.md",
            "scripts/context_capsule.py",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, router)

    def test_persistent_worker_single_send_receipt_releases_immediately(self) -> None:
        router = flat(SKILL)
        managed = flat(ORCHESTRATION)
        for phrase in (
            "make one ordinary top-level send with a bounded tool timeout",
            "successful tool receipt",
            "release ownership and emit the local final immediately; do not wait for ACK",
            "worker does not wait for `RECEIPT_ONLY`, `FINAL_ACK`, or a receiver ping",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router + " " + managed)

    def test_send_timeout_is_bounded_and_terminal_is_not_retried(self) -> None:
        router = flat(SKILL)
        managed = flat(ORCHESTRATION)
        for phrase in (
            "unavailable, timeout, or ambiguous",
            "`callback_delivery=unconfirmed`",
            "emit the local final, and do not resend",
            "register one bounded fallback capable of recovering that terminal by event or final-turn ID",
            "That fallback is the only retry authority; the worker never owns retry",
            "existing durable Controller state that survives Controller restart",
            "volatile memory alone is not fallback registration",
            "Do not create a new registry, outbox, or receipt family solely for callback recovery",
            "recover once from terminal event or final-turn ID",
            "Do not turn send timeout into an infinite wait, a retry loop, a fresh receiver, or a second worker",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router + " " + managed)

    def test_duplicate_delivery_has_exactly_once_effect(self) -> None:
        router = flat(SKILL)
        managed = flat(ORCHESTRATION)
        for phrase in (
            "at-least-once wake with idempotent exactly-once effect",
            "duplicate terminal event",
            "zero additional scientific/shared-state effects",
            "every duplicate creates zero additional effects",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router + " " + managed)

    def test_user_visible_local_task_closes_open_loops_without_final_ack(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "final is delivery only after one open-loop audit",
            "named action is `DONE`",
            "`BLOCKED` by an external fact or need for new authority",
            "`DELEGATED` with a successful receipt",
            "A concept explanation, status reply, or side question does not clear an unfinished active research objective",
            "the user explicitly replaces/cancels it or its authority boundary changes",
            "Execute any safe current next decision instead of leaving it only as final prose",
            "End only when the bounded decision is complete, genuinely blocked, or its next action needs new authority",
            "Do not persist this audit or create Program, lease, callback, sidecar, heartbeat, `RECEIPT_ONLY`, `FINAL_ACK`, or receiver machinery",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        self.assertIn("It never blocks a user-visible worker", router)

    def test_pro_is_optional_one_shot_not_sink_lifecycle(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "Use Pro only when an independent reasoning path can change a named decision",
            "For Lite, submit once, read once, and stop",
            "no sink task, job lifecycle, polling loop, heartbeat, duplicate, or follow-up",
            "`PRO_UNAVAILABLE`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

    def test_result_blind_access_fails_closed_without_audit_retry_cascade(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "Freeze a safe source tree before retrieval",
            "search snippets",
            "repository or package `README` files",
            "deterministic allowlist/result-strip step",
            "`HOLD_ACCESS_CHANNEL` before fetching",
            "Record the scoped hold once in the existing final/terminal",
            "Do not create an exposure artifact family, dispatch an automatic fresh owner, or self-retry",
            "protocol-control event, never a scientific negative or candidate drop",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_cross_stage_hard_controls_remain(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "cannot override platform, system, developer, or `AGENTS.md` authority",
            "identity, power, thresholds, exposure boundary",
            "Outcome-blind repair stays inside the unchanged contract and budget",
            "after protected outcome access",
            "safe source tree and result stripping before any fetch",
            "one verified complete witness",
            "Pro and same-model review are advisory",
            "No token target, artifact count, retry count, reviewer verdict, or governance ratio can convert an unresolved scientific, exposure, fairness, provenance, budget, or reproducibility defect into `PASS`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

    def test_knowledge_handoff_is_conditional_not_default_lite_schema(self) -> None:
        router = flat(SKILL)
        self.assertIn("Add `knowledge_reads` and `knowledge_writeback` only when", router)
        self.assertIn("A local workflow/code audit does not need those fields", router)
        self.assertNotIn("Every bounded route ends with", router)

    def test_managed_dirty_behaviors_are_not_duplicated_in_router(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for detailed_policy in (
            "Define backlog saturation narrowly",
            "Apply `solve-or-bind` before retaining any `HOLD`",
            "After an independently verified negative, do not equate closure",
        ):
            with self.subTest(detailed_policy=detailed_policy):
                self.assertNotIn(detailed_policy, text)

    def test_opportunity_process_delta_is_bounded_and_nonbinding(self) -> None:
        portfolio = flat(ROOT / "references" / "portfolio-search.md")
        integrity = flat(INTEGRITY)
        for phrase in (
            "`source_family_id`",
            "descriptive retrieval telemetry",
            "descriptive, non-binding `mechanism_depth` value",
            "not a novelty claim, score, admission gate, or contribution verdict",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, portfolio)
        for phrase in (
            "not as a new lifecycle, state tree, or artifact family",
            "`R0`",
            "`R1`",
            "`R2`",
            "`R3`",
            "Expose no scientific outcome before `R2` is frozen",
            "never a scientific negative",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

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
