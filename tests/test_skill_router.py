from __future__ import annotations

import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "SKILL.md"
ORCHESTRATION = ROOT / "references" / "orchestration.md"
INTEGRITY = ROOT / "references" / "research-integrity.md"
PROBLEM_SPACE = ROOT / "references" / "problem-space.md"
PROGRAMS = ROOT / "references" / "research-programs.md"
PORTFOLIO_SEARCH = ROOT / "references" / "portfolio-search.md"
PORTFOLIO_LANES = ROOT / "references" / "portfolio-lanes.md"
EXTERNAL_PROMPTS = ROOT / "references" / "external-opportunity-search-prompts.md"
STATE_SCHEMA = ROOT / "references" / "state-schema.md"
WORKSPACE_AGENTS_VALUE = os.environ.get("XAR_WORKSPACE_AGENTS")
WORKSPACE_AGENTS = Path(WORKSPACE_AGENTS_VALUE) if WORKSPACE_AGENTS_VALUE else None
EXPERIMENTS_AGENTS_VALUE = os.environ.get("XAR_EXPERIMENTS_AGENTS")
EXPERIMENTS_AGENTS = (
    Path(EXPERIMENTS_AGENTS_VALUE) if EXPERIMENTS_AGENTS_VALUE else None
)
CONTROL_AGENTS_VALUE = os.environ.get("XAR_CONTROL_AGENTS")
CONTROL_AGENTS = Path(CONTROL_AGENTS_VALUE) if CONTROL_AGENTS_VALUE else None


def flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def access_policy_rows() -> dict[tuple[str, str], str]:
    rows: dict[tuple[str, str], str] = {}
    for line in INTEGRITY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) == 3:
            rows[(cells[0], cells[1])] = cells[2]
    return rows


def route_rows() -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    for line in SKILL.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 3 and cells[0] not in {"Route", "---"}:
            rows[cells[0]] = (cells[1], cells[2])
    return rows


class SkillRouterTest(unittest.TestCase):
    def test_core_router_stays_within_prompt_byte_budget(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("# Xiaowen AutoResearch", text)
        self.assertLessEqual(len(text.encode("utf-8")), 21_200)
        module_prefix = Path(__file__).read_text(encoding="utf-8").split("def flat", 1)[0]
        self.assertNotIn("/Users/", module_prefix)

    def test_frontmatter_excludes_pure_execution_workers(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        self.assertIn("Do not invoke for a simple concept explanation", frontmatter)
        self.assertIn("pure implementation/execution worker", frontmatter)
        self.assertIn("the frozen contract", frontmatter)

    def test_every_direct_reference_link_resolves(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        linked = set(re.findall(r"\]\((references/[^)]+\.md)\)", text))
        self.assertGreater(len(linked), 0)
        for relative in linked:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file(), relative)

    def test_all_local_markdown_links_resolve(self) -> None:
        markdown_files = [SKILL, *sorted((ROOT / "references").glob("*.md")), *sorted((ROOT / "assets").glob("*.md"))]
        for source in markdown_files:
            text = source.read_text(encoding="utf-8")
            for raw_target in re.findall(r"\]\(([^)]+)\)", text):
                target = raw_target.split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (source.parent / target).resolve()
                with self.subTest(source=source.name, target=raw_target):
                    self.assertTrue(resolved.is_file(), str(resolved))

    def test_lite_local_single_owner_creates_no_managed_machinery(self) -> None:
        router = flat(SKILL)
        required = (
            "Default to `operating_weight=lite`",
            "Classify by side effects and coordination",
            "A user-visible task is the task capsule and delivery surface",
            "no new Program/Epoch record for one-off Lite work",
            "reuse the existing compact planning record when a repeated Program already exists",
            "create no dispatch, lease, activation, lane, ledger, registry, or chronology record",
            "zero watchdog, heartbeat, continuity automation, callback sink, or blocking callback ACK roundtrip",
            "no duplicate task capsule",
            "at most one terminal only when durable evidence is genuinely needed",
            "Local source/literature/code/workflow audits",
            "bounded Pro batches, and one-shot Pro closure advisory remain Lite",
            "Never retrofit Managed ceremony onto Lite work",
            "`Lite` removes coordination machinery, not section 6 hard controls",
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
            "paid-service, publication/public-facing, production, irreversible, or third-party mutation",
            "Confirmatory scientific decision requires independent ownership",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        self.assertIn("not by the labels “research,” “audit,” “Scout,” or “multi-step.”", router)

    def test_execution_plane_has_no_runtime_governance_family(self) -> None:
        router = flat(SKILL)
        self.assertIn("do not invoke or load this skill there", router)
        self.assertIn("The contract is the only capsule", router)
        self.assertIn("production chain itself", router)
        self.assertIn("READY_BEFORE_FIRST_UTILITY", router)
        self.assertIn("one post-freeze fast path, owner/model, and final terminal", router)
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

    def test_post_freeze_fast_path_is_bounded_and_claim_safe(self) -> None:
        router = flat(SKILL)
        integrity = flat(INTEGRITY)

        for phrase in (
            "one post-freeze fast path",
            "production chain itself",
            "READY_BEFORE_FIRST_UTILITY",
            "zero training/update/eval/utility/protected access",
            "Round 1 is minimal repair",
            "round 2 is clean reimplementation",
            "in-owner inventory, not terminal",
            "changing no terminal/callback/Controller/owner/objective",
            "The contract is the only capsule",
            "freeze route, identity, exposure, cap, and claim",
            "completed -> contract-consistent -> evidence-eligible -> independently verified -> claim-accepted",
            "deterministic prechecks may reject but cannot accept scientific claims",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

        for phrase in (
            "fresh-owner path-only Audit",
            "For protected-result attribution, Confirmatory, or publication-claim review",
            "exact paper/claim text path",
            "Exclude Executor summaries",
            "rebinds every input hash",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

        problem = flat(PROBLEM_SPACE)
        self.assertIn("one ephemeral anti-repeat view", problem)
        self.assertIn(
            "Do not persist it, build a graph, create a capsule, or treat it as evidence",
            problem,
        )

    def test_managed_lane_reference_is_conditional(self) -> None:
        required, conditional = route_rows()["Managed controller / recovery"]
        self.assertEqual(required, "[orchestration.md](references/orchestration.md)")
        self.assertNotIn("portfolio-lanes.md", required)
        self.assertIn("portfolio-lanes.md", conditional)
        self.assertIn("only when a real shared lane changes", conditional)

        opportunity_required, _ = route_rows()["Opportunity Search"]
        self.assertNotIn("orchestration.md", opportunity_required)
        self.assertNotIn("portfolio-lanes.md", opportunity_required)
        self.assertNotIn("portfolio-search.md", opportunity_required)
        self.assertIn("problem-space.md", opportunity_required)
        self.assertIn("research-integrity.md", opportunity_required)
        _, opportunity_conditional = route_rows()["Opportunity Search"]
        self.assertIn("portfolio-search.md", opportunity_conditional)
        self.assertIn("repeated, multi-candidate, or cross-candidate selection", opportunity_conditional)

    def test_optional_program_and_shared_resource_boundaries_do_not_gate_lite(self) -> None:
        portfolio = flat(PORTFOLIO_SEARCH)
        programs = flat(PROGRAMS)
        lanes = flat(PORTFOLIO_LANES)
        external = flat(EXTERNAL_PROMPTS)
        for phrase in (
            "Opportunity Search never creates a Program/Epoch merely to rank candidates",
            "Do not initialize Managed state—or invent a Program/Epoch—solely to represent a one-off Lite search",
            "This is not a global portfolio scheduler",
            "creates no zero-GPU lane, Pro lane, idle proof, continuous-search obligation",
            "the external review never opens a Program/Epoch",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, " ".join((portfolio, programs, lanes, external)))
        self.assertIn(
            "retrospective workflow diagnostics from existing records, never new telemetry, sidecars, validators, or per-item gates",
            programs,
        )

    def test_persistent_worker_single_send_receipt_releases_immediately(self) -> None:
        router = flat(SKILL)
        managed = flat(ORCHESTRATION)
        for phrase in (
            "Persistent Managed completion follows",
            "one bounded top-level send",
            "release on successful receipt",
            "never resend an ambiguous delivery",
            "ACK never blocks",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        for phrase in (
            "one ordinary top-level `send_message_to_thread` call with the runtime's bounded timeout",
            "A successful tool receipt releases worker ownership",
            "the worker does not wait for `RECEIPT_ONLY`, `FINAL_ACK`, or a receiver ping",
        ):
            with self.subTest(managed_phrase=phrase):
                self.assertIn(phrase, managed)

    def test_send_timeout_is_bounded_and_terminal_is_not_retried(self) -> None:
        router = flat(SKILL)
        managed = flat(ORCHESTRATION)
        self.assertIn("never resend an ambiguous delivery", router)
        self.assertIn("Fallback has idempotent effects", router)
        for phrase in (
            "unavailable, times out, or returns an ambiguous result",
            "`callback_delivery=unconfirmed`",
            "emit the local final, and do not resend",
            "register one bounded fallback",
            "That fallback is the only retry authority; the worker never owns retry",
            "existing durable Controller state that survives Controller restart",
            "volatile memory alone is not fallback registration",
            "Do not create a new registry, outbox, or receipt family solely for callback recovery",
            "recover that terminal once from its `terminal_event_id` or final-turn ID",
            "Do not turn send timeout into an infinite wait, a retry loop, a fresh receiver, or a second worker",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, managed)

    def test_duplicate_delivery_has_exactly_once_effect(self) -> None:
        router = flat(SKILL)
        managed = flat(ORCHESTRATION)
        self.assertIn("idempotent effects", router)
        for phrase in (
            "at-least-once wake plus idempotent exactly-once effect",
            "every duplicate creates zero additional effects",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, managed)

    def test_user_visible_local_task_closes_open_loops_without_final_ack(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "end only with every action `DONE`",
            "finite external/authority `BLOCKED`",
            "receipt-backed `DELEGATED`",
            "A side question or status does not clear an objective",
            "unless the user replaces/cancels it or its authority changes",
            "Execute any safe next decision",
            "Do not persist this audit or create Program, lease, callback, sidecar, heartbeat, `RECEIPT_ONLY`, `FINAL_ACK`, or receiver machinery",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        self.assertIn("ACK never blocks", router)

    def test_pro_is_persistent_sequential_and_nonblocking_by_default(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "Pro is never a lane, owner or authority",
            "Use sequential one-shot batches",
            "Ordinary batches are `NON_BLOCKING`",
            "`BLOCKING_HIGH_RISK`",
            "previously bound exact gate",
            "locally absorbed validation",
            "authority by agreement",
            "one hashed review bundle",
            "complete live Skill",
            "every applicable `AGENTS.md`",
            "candidate diff/validation",
            "a summary is not a substitute",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

    def test_pro_generation_is_off_critical_path_without_polling_machinery(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "one in-flight submit/read, no queue/follow-up",
            "no queue/follow-up/page poll, sink or duplicate",
            "never open Pro or create a reader",
            "deduplicate by candidate/scope hash",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

    def test_pro_review_bundle_contains_complete_authority_context(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        for phrase in (
            "one hashed review bundle",
            "complete live Skill",
            "every applicable `AGENTS.md`",
            "routed direct references",
            "candidate diff/validation",
            "Redact only secrets and protected payloads",
            "a summary is not a substitute",
        ):
            with self.subTest(source="router", phrase=phrase):
                self.assertIn(phrase, router)
        for phrase in (
            "exact-hashed full authority bundle",
            "complete current Skill directory",
            "every applicable parent-to-child `AGENTS.md`",
            "candidate diff/validation",
            "prior full bundle hash",
            "every applicable authority hash are unchanged",
            "Package only Git-tracked Skill files",
            "Name every exclusion and hash the files actually sent",
            "rather than creating a packet registry or artifact family",
        ):
            with self.subTest(source="orchestration", phrase=phrase):
                self.assertIn(phrase, orchestration)

    def test_pro_is_routed_through_scientific_owner_not_controller(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        prompts = flat(EXTERNAL_PROMPTS)
        for phrase in (
            "Controller detects and routes a Pro trigger but must not author the prompt or adjudicate the answer",
            "Explorer owns source/neighbor/reduction/formulation",
            "signal-versus-implementation",
            "skip only deterministic repair with no decision ambiguity",
        ):
            with self.subTest(source="router", phrase=phrase):
                self.assertIn(phrase, router)
        for phrase in (
            "External Pro remains inside the current scientific role rather than the Controller",
            "Pro creates no role, task, lease, lane, pin or scientific authority",
            "A minimal outcome-free read obligation in the Controller snapshot is the sole exception",
            "At each material idea boundary",
        ):
            with self.subTest(source="orchestration", phrase=phrase):
                self.assertIn(phrase, orchestration)
        for phrase in (
            "Route every prompt through the scientific owner",
            "The Controller may identify the trigger and dispatch that owner",
            "never raw or per-unit protected evidence",
        ):
            with self.subTest(source="prompt", phrase=phrase):
                self.assertIn(phrase, prompts)

    def test_closure_confidence_gate_separates_science_from_operational_stops(self) -> None:
        router = flat(SKILL)
        integrity = flat(INTEGRITY)
        for phrase in (
            "freeze one closure packet in the existing decision record",
            "`closure_risk=LOW|HIGH`",
            "Do not create a new artifact family",
            "`ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`, carrier/access failure, search exhaustion, missing sources, and incomplete neighbor work are not scientific closures",
        ):
            with self.subTest(router_phrase=phrase):
                self.assertIn(phrase, router)
        for phrase in (
            "source unavailability, search-budget exhaustion, no-selection, or incomplete neighbor work",
            "cannot scientifically retire a hypothesis",
        ):
            with self.subTest(integrity_phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_low_risk_closure_needs_complete_witness_and_independent_audit(self) -> None:
        integrity = flat(INTEGRITY)
        router = flat(SKILL)
        for phrase in (
            "one single formal or executable witness completely preserves actor decision, information, chronology, state, work/cost, recipients, and estimand",
            "a prospectively frozen, adequately powered mechanism falsifier or negative meets its declared action table",
            "independent Audit verifies the complete witness and scope",
            "`CONFIDENT_LOCAL`",
            "Low-risk closures do not require a blocking Pro call",
            "mark `PASS|FAIL|UNKNOWN` for actor/action, lawful pre-action information, chronology, state/storage, productive work, physical bytes, latency/cost, recipients, and estimand",
            "Every applicable field must be `PASS`; any `FAIL` disqualifies that closure basis and any `UNKNOWN` forces `HIGH`",
            "composing papers, partial mappings, or unstated assumptions is never `LOW`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_high_risk_or_last_probe_closure_requires_adversarial_rebuttal(self) -> None:
        integrity = flat(INTEGRITY)
        router = flat(SKILL)
        for phrase in (
            "multi-paper composition, partial/generic neighbor interpretation, absence evidence, ambiguous algebra, disputed source mapping, or reviewer conflict",
            "removes the last active `PROBE`, empties the funnel, closes a user-prioritized route",
            "`HIGH` override",
            "`PROVISIONAL_CLOSE_PENDING_REBUTTAL` or `HOLD_INFORMATION`",
            "one one-shot adversarial Pro review followed by local source verification and adjudication",
            "one fresh independent local reviewer who did not produce the proposed closure",
            "`CONFIDENT_ADVERSARIAL` only after rebuttal",
            "unavailability is not closure evidence",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_closure_pro_records_only_decision_effect_in_existing_record(self) -> None:
        integrity = flat(INTEGRITY)
        router = flat(SKILL)
        for phrase in (
            "Freeze the local closure packet first; submit once in the configured project, read once, and do not follow up",
            "`pro_trigger`, `pro_disposition`, `decision_effect`, and final confidence",
            "Pro is a rebuttal generator, never closure authority",
            "Do not create a closure schema, sidecar family, Pro sink, polling lifecycle",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_public_literature_r0_defaults_to_public_source(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "`public_source` is the default for Opportunity Search and ordinary public-literature `R0`",
            "complete public primary paper",
            "including method, results, appendix, tables and figures",
            "Public benchmark values are prior literature evidence",
            "not the candidate's own protected scientific outcome",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

        rows = access_policy_rows()
        self.assertEqual(
            rows[("public_source", "verified public primary locator")],
            "PROCEED_R0",
        )

    def test_strict_blind_missing_safe_tree_blocks_before_dispatch(self) -> None:
        rows = access_policy_rows()
        self.assertEqual(
            rows[("strict_result_blind", "safe tree/packet missing or invalid")],
            "BLOCK_PRE_DISPATCH_ACCESS",
        )
        integrity = flat(INTEGRITY)
        self.assertIn("If it fails, the Audit is not dispatchable", integrity)
        self.assertIn("Do not launch an Audit to discover that its access tree is missing", integrity)

    def test_strict_blind_operational_access_frame_is_prebound_and_exact(self) -> None:
        integrity = flat(INTEGRITY)
        router = flat(SKILL)
        for phrase in (
            "`operational_access`",
            "`authority_readable_paths`",
            "`helper_paths`",
            "`locator_only_paths`",
            "`activation_argv`",
            "canonical exact absolute regular non-symlink files",
            "exact `{path, sha256}` binding",
            "are not stat'ed or opened",
            "no runtime helper/path discovery",
            "recursive or parent-root search",
            "$CODEX_HOME",
            "shell metacharacters",
            "BLOCK_PRE_DISPATCH_ACCESS",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity + " " + router)

    def test_strict_blind_capsule_and_r1_profile_stay_same_owner(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "any fresh strict-blind owner",
            "traverse only locators inside the validated capsule/safe tree",
            "outside that tree is provenance only",
            "required identity is absent from the capsule",
            "do not add a packet or validator",
            "exact interpreter",
            "dependency, driver/CUDA, GPU UUID",
            "pessimistic complete-path estimate",
            "not a separate Audit",
            "closed safe-output schema",
            "keeps the same `scientific_attempt`/owner/objective",
            "clean `carrier_generation`, never a new attempt identity",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_strict_blind_contaminated_session_is_never_reused(self) -> None:
        router = flat(SKILL)
        integrity = flat(INTEGRITY)
        self.assertIn("A strict-blind owner exposed to forbidden bytes stays ineligible", router)
        self.assertIn("not eligible for a later strict-blind Audit, even after compaction or summary", integrity)
        self.assertIn("Use one fresh unexposed owner", integrity)

    def test_exposure_does_not_create_packet_or_fresh_audit_cascade(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "invalidate only that exact blind attempt",
            "Do not archive or drop the candidate",
            "generate a packet successor",
            "dispatch a fresh Audit",
            "never an automatic `exposure -> packet -> fresh-audit` cascade",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_deterministic_safe_source_prep_stays_inside_lite_owner(self) -> None:
        integrity = flat(INTEGRITY)
        router = flat(SKILL)
        for phrase in (
            "the current owner performs one deterministic mechanical preflight",
            "This preflight is not a Program, lease, lane, terminal, or separate research role",
        ):
            with self.subTest(integrity_phrase=phrase):
                self.assertIn(phrase, integrity)
        self.assertIn(
            "Packet, locator, sidecar, and file checks stay in the current owner as preflight",
            router,
        )

    def test_r0_schema_is_minimal_and_r2_fields_are_deferred(self) -> None:
        problem = flat(PROBLEM_SPACE)
        for phrase in (
            "`R0` freezes only the actor and action, lawful pre-decision inputs, the exact smallest next cell, matched-cost invariants, fatal invalidators, a hard cap, the cheapest decision-complete problem-existence witness, and the strongest baseline's identity, fairness and constructability",
            "Full license coverage, power and seed arithmetic, natural prevalence, a full recipient matrix, full-carrier portability, and publication-scale external validity are not default `R0` fatal gates",
            "Move them to `R1` or `R2` unless one is necessary to identify the exact next cell or keep that cell lawful and safe",
            "A source-grounded controlled synthetic generator, executable microcase, or formal fixture may establish scoped problem existence",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, problem)

    def test_two_tier_r2_and_baseline_staging_do_not_block_first_scout(self) -> None:
        router = flat(SKILL)
        problem = flat(PROBLEM_SPACE)
        integrity = flat(INTEGRITY)
        for phrase in (
            "baseline identity/fairness/constructability",
            "`R1` makes the real carrier and baseline runnable without utility",
            "A first descriptive `R2` freezes exact identity/exposure",
            "Confirmatory, superiority, powered-negative, or closure claims additionally require complete power",
        ):
            with self.subTest(router_phrase=phrase):
                self.assertIn(phrase, router)
        for phrase in (
            "It does not require the baseline to be fully reproduced or executed",
            "It does not require final power, multiplicity, every paper baseline",
            "Confirmatory/final `R2` additionally freezes the complete power and multiplicity plan",
        ):
            with self.subTest(problem_phrase=phrase):
                self.assertIn(phrase, problem)
        self.assertIn("A first descriptive Scout binds exact code/config/data/model/carrier/attempt identity", integrity)
        self.assertIn("It does not require final power or multiplicity", integrity)

    def test_governance_attention_share_is_diagnostic_not_a_new_gate(self) -> None:
        router = flat(SKILL)
        self.assertIn("only as retrospective diagnostics from existing records", router)
        self.assertIn("never as per-task telemetry, a sidecar, or an acceptance gate", router)
        self.assertIn("without creating a new measurement family", router)

    def test_r1_repair_is_bounded_but_not_one_shot(self) -> None:
        problem = flat(PROBLEM_SPACE)
        integrity = flat(INTEGRITY)
        for text in (problem, integrity):
            self.assertIn("one active outcome-blind", text)
            self.assertIn("clean `carrier_generation`", text)
            self.assertIn("returns to prospective adjudication", text)
        self.assertIn("same scientific attempt/owner/objective", problem)
        self.assertIn("same `scientific_attempt`/owner/objective", integrity)

    @unittest.skipUnless(
        WORKSPACE_AGENTS is not None and WORKSPACE_AGENTS.is_file(),
        "set XAR_WORKSPACE_AGENTS to enable workspace integration checks",
    )
    def test_outcome_blind_engineering_loop_does_not_create_callback_ceremony(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        workspace = flat(Path(os.environ["XAR_WORKSPACE_AGENTS"]))
        for phrase in (
            "one post-freeze fast path, owner/model, and final terminal",
            "zero training/update/eval/utility/protected access",
            "Parent rules let that Executor use `record-startup-attempt`",
            "without terminal, callback, Controller, owner or objective transition",
        ):
            with self.subTest(router_phrase=phrase):
                self.assertIn(phrase, router)
        for phrase in (
            "one uninterrupted engineering loop",
            "without an intermediate terminal, Controller callback, contract, task, lease",
            "A recoverable outcome-blind failure is explicitly `NON_TERMINAL`",
            "scientific identity, exposure, authority, budget, or protected-outcome state",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)
        self.assertIn("One local decision-complete owner is the default", workspace)
        self.assertIn("exact startup-chain preflight", workspace)
        self.assertIn("engineering/carrier/access failure is never a scientific negative", workspace)

    def test_executor_is_one_model_one_owner_without_default_internal_pipeline(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        for phrase in (
            "A cross-thread successor requires an allowlisted reason",
            "The contract is the only capsule",
            "one post-freeze fast path, owner/model, and final terminal",
            "Never default to `Lead -> Builder -> Acceptance`",
            "production chain itself",
            "two delegated objectives in one thread",
        ):
            with self.subTest(source="router", phrase=phrase):
                self.assertIn(phrase, router)
        for phrase in (
            "one contiguous pre-release, outcome-blind Luna segment",
            "same Sol owner",
            "one failure fingerprint",
            "Do not make `Lead -> Builder -> Acceptance`",
            "Every cross-thread successor records exactly one structured",
            "Model switch, hash/path/schema/import or package checks",
            "A delegated v3 owner first migrates unchanged",
        ):
            with self.subTest(source="orchestration", phrase=phrase):
                self.assertIn(phrase, orchestration)

    def test_compact_controller_receipts_and_context_rollover_are_operational_only(self) -> None:
        orchestration = flat(ORCHESTRATION)
        state_schema = flat(STATE_SCHEMA)
        for phrase in (
            "Keep the Controller logically singleton while allowing physical context rollover",
            "compact receipt fields",
            "dispatch receipt, lease epoch, contract revision",
            "at least 8 samples have median above 96000",
            "show --projection active",
            "without paying the full reload cost",
            "show --projection full",
            "`physical_controller_context_epoch`",
            "never delays terminal absorption",
            "operational efficiency alarms, never scientific acceptance or closure gates",
        ):
            with self.subTest(source="orchestration", phrase=phrase):
                self.assertIn(phrase, orchestration)
        for phrase in (
            "The nested six-field `completion_binding` is the sole terminal identity authority",
            "prepare-terminal-callback",
            "final_bytes",
            "final_sha256",
            "`fresh_thread_reason`",
            "`fresh_thread_evidence_ref`",
            "`NON_BLOCKING` and `BLOCKING_HIGH_RISK`",
            "legacy advisory shapes are invalid",
            "`absorb-nonblocking-advisory`",
            "generic replacement cannot seed, claim or complete response metadata",
            "Each owner thread appears on at most one `DELEGATED` objective",
        ):
            with self.subTest(source="state-schema", phrase=phrase):
                self.assertIn(phrase, state_schema)

    @unittest.skipUnless(
        WORKSPACE_AGENTS is not None and WORKSPACE_AGENTS.is_file(),
        "set XAR_WORKSPACE_AGENTS to enable workspace integration checks",
    )
    def test_explorer_pauses_only_on_true_multi_card_saturation(self) -> None:
        router = flat(SKILL)
        lanes = flat(PORTFOLIO_LANES)
        workspace = flat(Path(os.environ["XAR_WORKSPACE_AGENTS"]))
        self.assertIn("per candidate/version, never portfolio-wide", router)
        self.assertIn("authorized usable card", router)
        self.assertIn("launch-ready item waits solely for capacity", router)
        self.assertIn("blocked/profile-waiting/unavailable/empty cards do not count", router)
        for phrase in (
            "per candidate/version",
            "not a portfolio-wide mutex",
            "every currently usable, authorized card",
            "waits solely for capacity",
            "Blocked",
            "empty cards do not count",
        ):
            with self.subTest(lanes_phrase=phrase):
                self.assertIn(phrase, lanes)
        self.assertIn("Research workflow semantics live in the live", workspace)
        self.assertIn("do not duplicate", workspace)
        self.assertIn("does not create a `zero_gpu` lane", lanes)
        self.assertIn("Idle capacity never authorizes filler", lanes)

    def test_novelty_first_real_scout_does_not_select_for_carrier_ease(self) -> None:
        router = flat(SKILL)
        integrity = flat(INTEGRITY)
        for phrase in (
            "rank value, residual novelty, causal depth",
            "before carrier ease",
            "Carrier availability cannot turn Opportunity Search into a search for easy experiments",
            "Missing official code is not a fatal check",
            "Build the smallest controlled carrier from scratch",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router + " " + integrity)

    def test_first_carrier_gate_is_fatal_semantics_not_publication_readiness(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "preserve actor, decision time, lawful information, feasible action set, common parent, complete persistent state transition, recipients, and estimand",
            "Every arm acts on the same pre-policy work product",
            "action-dependent retraining, post-action information, or a different adaptation trajectory is a `HARD_BLOCK`",
            "Ambiguous identity, authorization, or prohibited exposure is not profileable",
            "An action-restricted comparator is a mechanism deletion, not the strongest baseline",
            "Reject a semantically mismatched named carrier at this gate",
            "full five- or nine-arm platform",
            "are not prerequisites for the first problem-existence Scout",
            "Any unmapped or altered field is a `HARD_BLOCK`",
            "a one-step carrier supports only immediate-recipient claims, not cumulative chronology",
            "This compact mapping is not a carrier dossier",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_unknown_runtime_variance_and_cost_route_to_bounded_measurement(self) -> None:
        router = flat(SKILL)
        integrity = flat(INTEGRITY)
        self.assertIn("`UNKNOWN_TO_SYSTEM_PROFILE`", integrity)
        self.assertIn("`UNKNOWN_TO_CALIBRATION`", integrity)
        self.assertIn("paired variance/covariance; use disjoint units or count them in the frozen Scout sequence", integrity)
        self.assertIn("System profiles see no utility; calibration is disjoint or counts in the Scout", router)
        self.assertIn("A system profile may change only batch size, precision, compilation, checkpointing", integrity)
        self.assertIn("no superiority, powered negative, or scientific close", integrity)

    def test_dual_5090_default_exploratory_envelope_is_executable_and_bounded(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "by `T+12 h` after `PROBE` admission",
            "by `T+24 h`",
            "by `T+72 h`",
            "at most `4` aggregate RTX-5090 GPU-hours",
            "`2` or `3` necessary arms",
            "`n0=3`, `nmax=6`",
            "randomized/counterbalanced arm order",
            "at most `96` aggregate RTX-5090 GPU-hours",
            "at most `48 h`, using at most two GPUs",
            "ceiling, not an allocation",
            "There is no automatic cap expansion",
            "explicit prospective authority for a new attempt/version",
            "`HOLD_INFORMATION` with an exact resource reopening fact",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_first_scout_contract_is_screening_only_and_prospective(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "the candidate decision policy",
            "the strongest complete simple matched baseline",
            "a mechanism deletion or necessary null only when it is distinct from arm 2",
            "Two arms suffice when the candidate is itself the simplest lawful policy over the complete action set",
            "If it adds learned/structured policy, history, or nontrivial calibration, use three",
            "retained parent/no-action state as the guard comparator",
            "six-seed order",
            "mandatory unchanged continuation through seeds 4--6",
            "median paired effect is positive, and at least four of six paired effects are positive",
            "descriptive six-paired-bundle portfolio screen",
            "`SCOUT_SIGNAL` does not authorize Confirmation by itself",
            "refresh nearest-neighbor residual and carrier conformance",
            "deterministically compare the frozen candidate, strongest baseline, mechanism deletion, and guard/parent action and state signatures",
            "take identical actions on every frozen unit",
            "cannot attribute a mechanism effect",
            "it cannot support mechanism attribution",
            "bind one Contribution Gate owner/action in that same turn",
            "`OPEN_WITHOUT_OWNER`, not a completed handoff",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_time_to_first_scientific_outcome_excludes_activity_proxies(self) -> None:
        router = flat(SKILL)
        integrity = flat(INTEGRITY)
        self.assertIn("Define `time-to-first-scientific-outcome`", integrity)
        for phrase in (
            "causal fingerprint's first `PROBE` admission",
            "clock never resets for carrier changes, implementation rewrites, candidate versions, archives, or owner transfers",
            "Partial `n0`, synthetic fixtures, profiles, model loading, mechanical failures",
            "fraction of **all admitted probes** reaching a valid outcome by `T+72 h`",
            "Keep archived, invalid, resource-held, active-censored, and incomplete probes in the denominator",
            "cannot reset the clock, change novelty rank, or justify a weaker carrier",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)
        self.assertIn("time-to-first-scientific-outcome", router)

    def test_n0_is_guard_only_and_cannot_select_a_positive_version(self) -> None:
        router = flat(SKILL)
        integrity = flat(INTEGRITY)
        self.assertIn("`n0=3` is validity/guard-only; no positive stop precedes `nmax=6`", router)
        self.assertIn("any other positive or negative valid result", integrity)
        self.assertIn("mandatory unchanged continuation through seeds 4--6", integrity)
        self.assertIn("no positive label, version selection, method change, cap escalation, effect claim, or promotion", integrity)
        self.assertNotIn("at `n0`, primary point estimate meets MPE", integrity)

    def test_complete_baseline_and_action_deletion_are_not_conflated(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "using the candidate's feasible action set when such a simple policy is constructable",
            "Do not call the deletion the strongest baseline merely because it is easy to implement",
            "Match feasible action sets when a simple complete policy is constructable",
            "restricted-action comparator may isolate action granularity",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_utility_exposure_cannot_hide_inside_profile_or_calibration(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "it must not inspect primary, guard, or mechanism utility",
            "utility-bearing calibration units are disjoint or count in the frozen Scout sequence",
            "After any utility exposure",
            "creates a new version with disjoint Scout units",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_cap_expansion_requires_new_preutility_authority_and_no_rescue(self) -> None:
        integrity = flat(INTEGRITY)
        for phrase in (
            "Unused GPU, an SLA, or available budget never entitles an extra arm, seed, endpoint, candidate, or profile",
            "There is no automatic cap expansion",
            "explicit prospective authority for a new attempt/version",
            "It uses disjoint evidence and cannot rescue or reinterpret the stopped attempt",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, integrity)

    def test_shadow_traces_ptop_kst_rca_and_tta_follow_new_routing(self) -> None:
        router = flat(SKILL)
        integrity = flat(INTEGRITY)
        # PTOP: runtime goes to a system profile; covariance uses accounted utility units.
        self.assertIn("`UNKNOWN_TO_SYSTEM_PROFILE`", integrity)
        self.assertIn("`UNKNOWN_TO_CALIBRATION`", integrity)
        # KST: reject mismatched FedMKT-like carriers, then allow a minimal clean-room carrier.
        self.assertIn("Reject a semantically mismatched named carrier", integrity)
        self.assertIn("Build the smallest controlled carrier from scratch", integrity)
        # RCA: a renamed ledger/serializer/manifest does not get another cycle.
        self.assertIn("receives no further repair cycle", integrity)
        self.assertIn("End a same-root engineering stall with one root-cause inventory", router)
        # TTA: skip synthetic-only smoke; preserve deltas/action set and baseline roles.
        self.assertIn("Once a `PROBE` is admitted", integrity)
        self.assertIn("Prefer the minimal code path that the scientific Scout will execute", integrity)
        self.assertIn("pure synthetic smoke converts only when it is the preregistered witness", router)
        self.assertIn("same pre-policy work product", integrity)
        self.assertIn("same-action-set rule, and action-restricted mechanism deletion", integrity)
        self.assertIn("no positive label", integrity)

    def test_startup_chain_has_two_round_breaker_and_exact_witness(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        state_schema = flat(STATE_SCHEMA)

        for phrase in (
            "Bind contract/prior-record digests in `startup_chain_authority`",
            "derive its ID from state+objective",
            "same Executor CAS-appends at most two sealed failure records",
            "changing no terminal/callback/Controller/owner/objective",
            "`BLOCKED`/ rebuild retain it",
            "only Audit replaces it",
            "IDs, paths and fingerprints cannot reset it",
            "Round 1 is minimal repair",
            "round 2 is clean reimplementation",
            "in-owner inventory, not terminal",
            "`carrier_generation` within the same scientific attempt/owner/budget",
            "first-mismatch terminal/create-new",
        ):
            with self.subTest(source="router", phrase=phrase):
                self.assertIn(phrase, router)

        for phrase in (
            "### Exact startup-chain arming and bounded repair",
            "public CLI -> prepare_run -> actual return consumer",
            "READY_BEFORE_FIRST_UTILITY -> controlled exit",
            "production shell, heredoc, environment expansion",
            "required-environment projection comes from the same launcher function as release",
            "wrong root/write modes",
            "unproven future reader",
            "blocked local CUDA/IPC",
            "The sealed contract contains one `startup_chain_binding`",
            "binds `startup_chain_authority` in the current objective",
            "The list length is the mechanical count",
            "generic replacement cannot change or remove the authority",
            "carries an omitted authority forward",
            "may append only the next consecutive sealed record",
            "Shrink, substitution or multi-record jumps fail before CAS",
            "record-startup-attempt` with its objective/owner",
            "changes only the authority record list",
            "creates no terminal, callback, activation, new objective, owner or Controller roundtrip",
            "A finite `BLOCKED` objective retains the authority",
            "after revalidating every digest",
            "Every prospective Executor terminal mirrors the exact authority or explicit `null`",
            "`rebuild-add-objective` restores it",
            "controller_control_state.py derive-startup-chain-id",
            "--state <snapshot> --objective-id <objective>",
            "accepts no contract, record list, declared ID, projection, entrypoint or barrier",
            "re-reads exactly the authority-bound files",
            "caller-omitted history therefore has no input channel",
            "cannot reset repair rounds",
            "The initial failure record authorizes round 1",
            "The second failure record authorizes round 2",
            "it does not inventory before round 2 runs",
            "no terminal, callback, Controller roundtrip, create-new attempt or new owner",
            "Failure after round 2 stops blind mechanical patching",
            "The inventory is a diagnostic escalation, not an ownership or terminal boundary",
            "create a clean carrier generation inside the same objective",
            "first-mismatch terminal/no-repair/create-new behavior",
            "Only a genuine external fact or unavailable authority may become finite `BLOCKED`",
            "Legacy immutable attempts keep their original rules",
            "even if its terminal is not yet observed",
            "prospective v5 state cannot create it",
            "is not R1, R3, scientific validity or claim authority",
        ):
            with self.subTest(source="orchestration", phrase=phrase):
                self.assertIn(phrase, orchestration)

        for phrase in (
            "`record-startup-attempt` is the sole same-objective CAS",
            "leaving terminal identity, roles, jobs, advisories and pending/absorbed IDs unchanged",
            "Every prospective Executor terminal mirrors the exact authority or explicit `null`",
            "rebuild restores and revalidates the object before CAS",
            "missing field or digest drift fails with the snapshot unchanged",
            "including while active with no observed terminal",
            "new v5 state cannot seed it",
        ):
            with self.subTest(source="state-schema", phrase=phrase):
                self.assertIn(phrase, state_schema)

    @unittest.skipUnless(
        EXPERIMENTS_AGENTS is not None
        and EXPERIMENTS_AGENTS.is_file()
        and CONTROL_AGENTS is not None
        and CONTROL_AGENTS.is_file(),
        "set XAR_EXPERIMENTS_AGENTS and XAR_CONTROL_AGENTS for rule-chain checks",
    )
    def test_effective_agents_chain_delegates_only_startup_record_cas(self) -> None:
        assert EXPERIMENTS_AGENTS is not None
        assert CONTROL_AGENTS is not None
        experiments = flat(EXPERIMENTS_AGENTS)
        control = flat(CONTROL_AGENTS)
        orchestration = flat(ORCHESTRATION)
        router = flat(SKILL)
        for source, phrase in (
            (router, "Parent rules let that Executor use `record-startup-attempt`"),
            (
                orchestration,
                "one parent-AGENTS-delegated non-Controller snapshot mutation",
            ),
            (
                experiments,
                "only write exception is the currently delegated Executor invoking exactly `record-startup-attempt`",
            ),
            (
                experiments,
                "grants no other state subcommand or authority",
            ),
            (
                control,
                "One narrow exception lets the currently delegated Executor invoke exactly `record-startup-attempt`",
            ),
            (
                control,
                "grants no generic replacement, lifecycle, routing, terminal, role, job, advisory or owner-transfer authority",
            ),
        ):
            self.assertIn(phrase, source)

    def test_removed_failure_validator_family_cannot_reenter_hot_path(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        self.assertFalse((ROOT / "scripts" / "validate_failure_terminal.py").exists())
        self.assertFalse((ROOT / "tests" / "test_failure_terminal_validator.py").exists())
        for forbidden in (
            "failure-policy-binding/v1",
            "failure-fingerprint/v1",
            "### Pre-utility failure fingerprint and terminal gate",
            "Shadow modules are observational only",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, router + " " + orchestration)
        self.assertIn("Legacy immutable attempts keep their original rules", orchestration)
        self.assertIn("New startup-chain coverage is prospective", orchestration)

    def test_operating_weight_vocabulary_is_only_lite_or_managed(self) -> None:
        for path in (SKILL, ORCHESTRATION, PROGRAMS):
            text = flat(path)
            with self.subTest(path=path.name):
                self.assertNotIn("operating_weight=full", text)
                self.assertNotIn("lite | managed | full", text)
        self.assertIn("operating_weight: lite | managed", flat(PROGRAMS))

    def test_four_roles_keep_decision_complete_task_granularity(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        for phrase in (
            "Controller routes/accepts",
            "Explorer owns one complete source-to-`PROBE` loop",
            "Audit owns the whole `R0` decision in one owner/terminal",
            "Executor enters only after a complete implementation contract freezes",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        self.assertIn("A single Audit is not a global serialization lock", orchestration)

    def test_idea_boundaries_reuse_records_and_canonical_sessions(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "Reuse the idea's task capsule and durable records, never its raw transcript",
            "Use `/compact` only after decision-relevant history becomes redundant",
            "Reuse a canonical role across ideas only after verifiable runtime compact/reset",
            "record selection is not isolation",
            "transfer the role once and retire the predecessor",
            "load only the authoritative section and directly referenced evidence needed to resolve it",
            "complete record only for an unresolved decision-critical contradiction",
            "never load a prior raw transcript",
            "Never collapse `ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`, `CARRIER_STOP`, or `UNOBSERVED` into a scientific negative",
            "A contract change creates a new candidate/version and preserves the old records",
            "no data protocol, capsule, schema, lifecycle, context-bootstrap, automation or evidence substitute",
            "cannot change the research contract, metric, seed, budget, stop rule, or protected/outcome boundary",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

        for forbidden in (
            "Create a new idea capsule at every idea boundary",
            "Create a new session at every idea boundary",
            "load the complete existing record",
            "Treat operational failure as a scientific negative",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, router)

    def test_actionable_terminal_absorption_is_atomic_before_controller_final(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        workspace = flat(WORKSPACE_AGENTS) if WORKSPACE_AGENTS is not None else ""

        for phrase in (
            "Atomically absorb every actionable terminal",
            "`PROBE`, `PASS_R*`, `PROFILE_*`",
            "engineering/conflict/access/carrier stops",
            "receipt-and-activation-backed `DELEGATED`",
            "finite `BLOCKED` only on an external fact/unavailable authority with observer, trigger/check and deadline",
            "`DONE` requires scientific `CLOSED`",
            "`OPEN/DONE` and `OPEN_WITHOUT_OWNER` are invalid",
            "`dispatch_next` is incomplete before activation",
            "Ordinary/heartbeat wakes recover idempotently",
            "cannot final before safe absorb/route/activate or a finite external block",
        ):
            with self.subTest(router_phrase=phrase):
                self.assertIn(phrase, router)

        for phrase in (
            "performs atomic terminal absorption",
            "every actionable terminal, including `PROBE`, `PASS_R0*`, `PASS_R1*`",
            "`PROFILE_*`, `ENGINEERING_*`, `CONTRACT_CONFLICT`",
            "may not send a user-visible status/final before that activation exists",
            "“Controller decides whether” is not `owner_approval_required`",
            "worker-local terminals, never Controller route decisions",
            "terminal absorption is incomplete",
            "A worker recommendation",
            "cannot discharge this Controller duty",
            "`OPEN_WITHOUT_OWNER` is an invalid lifecycle state",
            "native recovery turn of the same singleton Controller thread",
            "finish Controller-only work",
            "must not redo Explorer/Audit/Executor semantics",
            "binds one Contribution Gate owner/action or a genuine blocker",
            "cannot leave it ownerless between Scout adjudication and the Gate",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)

        if workspace:
            for phrase in (
                "Controller terminal/state recovery",
                "For an open scientific candidate",
                "one decision-complete owner in the same Controller transaction",
                "finite `BLOCKED` only for a genuine external fact or unavailable authority",
                "observer, reopening trigger/check and deadline",
                "`DONE` requires scientifically `CLOSED`",
                "engineering/carrier/access failure is never a scientific negative",
            ):
                with self.subTest(workspace_phrase=phrase):
                    self.assertIn(phrase, workspace)

    def test_managed_runtime_binding_and_model_routing_are_explicit(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        for phrase in (
            "Before Managed reuse/create, verify Project ID, cwd/repository",
            "grant no shared-state authority",
            "Pin Managed roles needing follow-up",
            "never Lite/Pro",
            "reconcile via runtime APIs",
            "`gpt-5.6-sol max`",
            "`gpt-5.6-sol xhigh`",
            "`gpt-5.6-sol high`",
            "`gpt-5.6-luna max`",
            "default for frozen deterministic implementation",
            "Choose cheapest capable; ties use Luna",
            "file/module count is no trigger",
            "role alone never selects effort",
            "named no-history `agent_type=luna_worker`",
            "existing-thread model override",
            "`LUNA_ROUTE_DISPATCH_ID=<id>`",
            "named-child parent or same-thread thread/turn/dispatch",
            "One repair per fingerprint",
            "Never route protected/scientific/authority/ambiguous decisions to Luna",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        self.assertIn("A projectless task", orchestration)
        self.assertIn("Lite and Pro advisory tasks are never auto-pinned", orchestration)
        self.assertIn(
            "canonical `Audit · Workflow Evolution` session: keep it pinned",
            orchestration,
        )
        self.assertIn(
            "pin is navigation/availability only and creates no Managed",
            orchestration,
        )
        self.assertIn(
            "`Audit · Workflow Evolution` stays pinned through idle/`COMPLETE`",
            router,
        )
        self.assertTrue((ROOT / "scripts" / "validate_model_route.py").is_file())
        for phrase in (
            "call `set_thread_pinned`",
            "At each bounded runtime dispatch or continuation boundary",
            "Pass both explicitly for Sol routes",
            "omission or inheritance from the predecessor",
            "against durable rollout metadata",
            "writes no state or artifact",
            "returns to the Sol owner before effects",
            "Choose the cheapest capable route",
            "Code changes, test execution, or documentation alone",
            "Do not switch per microstep",
            "one contiguous pre-release, outcome-blind Luna segment",
            "exact parent",
            "creates no owner handoff",
            "After protected-result exposure, never downgrade to Luna",
            "deterministic oracle which Luna cannot reinterpret",
            "model switching a persistent pipeline",
            "named-profile catalogs and existing-thread route may differ",
            "RULE_TOOLING_DRIFT",
            "never claim Luna executed",
            "never worker prose",
            "with a no-history fork",
            "`multi_agent_version=v1` or `v2`",
            "A full-history fork inherits the parent agent type",
            "absence of `agent_type` makes only the named profile unavailable",
            "Do not substitute `task_name`",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)

        self.assertNotIn("simple outcome-invariant repair only", router)
        self.assertNotIn("simple outcome-invariant repair only", orchestration)

    def test_workflow_evolution_completion_requires_live_install(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)

        for phrase in (
            "Never emit `RETAIN|COMPLETE` from a candidate-only diff",
            "live files must byte-match it",
            "consumer/Controller receive the exact live hash plus reload instruction",
            "Advisory may review the deployed diff later",
        ):
            with self.subTest(router_phrase=phrase):
                self.assertIn(phrase, router)

        for phrase in (
            "passing scratch-copy test, advisory response, or review packet is not a completed optimization",
            "compare each intended live preimage with the frozen baseline",
            "run the required live replay/canary",
            "hash the live read-back against the accepted candidate",
            "one non-scientific completion message",
            "Ordinary Pro review is nonblocking",
            "not a new callback, receipt family, state field, watcher, heartbeat, registry, role, or lifecycle",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)

    def test_internal_portfolio_ordering_cannot_be_parked_as_blocked(self) -> None:
        orchestration = flat(ORCHESTRATION)
        for phrase in (
            "Internal portfolio sequencing is never a blocker authority",
            "does not satisfy `EXTERNAL_FACT` or `UNAVAILABLE_AUTHORITY`",
            "do not park it as `BLOCKED`",
        ):
            with self.subTest(source="orchestration", phrase=phrase):
                self.assertIn(phrase, orchestration)

    def test_workflow_evolution_detection_is_event_driven_shadow_and_rule_aware(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        self.assertTrue((ROOT / "scripts" / "workflow_evolution_gate.py").is_file())
        self.assertIn("Workflow Evolution is reusable Audit scope", router)
        for phrase in (
            "no signal means no message, ACK or resend",
            "30-minute heartbeat only bounds delivery/recovery latency",
            "Every eighth absorbed terminal",
            "BACKWARD_OUTCOME_COST",
            "RULE_TOOLING_DRIFT",
            "EXECUTION_NONCONFORMANCE",
            "Valid negative/null decisions count as output",
            "independent ARIS task",
            "RETAIN_ELIGIBLE",
            "route smoke proves reachability only",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)

    def test_successor_activation_barrier_is_read_only_and_pre_effect(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        schema = flat(STATE_SCHEMA)
        self.assertIn("`dispatch_next` is incomplete before activation", router)
        for phrase in (
            "planned post-CAS minimum revision",
            "No repository, remote, GPU, model/data/protected read, write",
            "without a destination ACK",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)
        for phrase in (
            "prospective read-only startup barrier",
            "WAIT_ACTIVATION_COMMIT",
            "genuine post-CAS exhaustion still fails closed",
            "never retroactively rescued",
        ):
            with self.subTest(schema_phrase=phrase):
                self.assertIn(phrase, schema)

    def test_luna_routing_boundary_cases_are_explicit(self) -> None:
        orchestration = flat(ORCHESTRATION)
        workspace = flat(WORKSPACE_AGENTS) if WORKSPACE_AGENTS is not None else ""

        for phrase in (
            "exact deterministic edits spanning multiple modules -> `luna/max`",
            "mechanical tests or documentation copied from a frozen oracle -> `luna/max`",
            "defining or changing an oracle, threshold, test semantics, contract, claim",
            "sealed unchanged rerun with identity/hash-only acceptance -> `luna/max`",
            "inspecting or interpreting protected rerun output -> Audit/Controller",
            "session_meta` plus current `turn_context",
            "same-thread fallback",
            "exact `session_meta.id`, latest `turn_context` model/effort",
            "durable message metadata carries that same turn ID",
            "preserves objective, scientific role, cumulative budget and final terminal",
            "After protected-result exposure, never downgrade to Luna",
            "decision has been frozen into a deterministic oracle",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)

        if workspace:
            self.assertIn("model family/reasoning-effort routing", workspace)
            self.assertIn("The Skill alone defines", workspace)
            self.assertNotIn("`gpt-5.6-luna`", workspace)

    def test_research_role_session_titles_are_canonical_and_stateful(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        workspace = flat(WORKSPACE_AGENTS) if WORKSPACE_AGENTS is not None else ""

        self.assertIn(
            "`<Role> · <candidate-or-bounded-scope> · <STATE>`",
            router,
        )
        for phrase in (
            "`Controller|Explorer|Audit|Executor`",
            "`ACTIVE|WAITING_EXTERNAL|HOLD|BLOCKED|COMPLETE`",
            "do not substitute raw task, dispatch, lease, terminal, or hash IDs for the scope",
            "update it on reuse or a material phase/state change",
            "remove stale `ACTIVE` at terminal absorption",
            "Titles are navigation only, not authority, evidence, a registry, or a lifecycle",
            "Use `set_thread_title` when the runtime exposes it",
            "Never leave a completed or waiting role titled `ACTIVE`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, orchestration)

        if workspace:
            self.assertIn("the four roles `Controller|Explorer|Audit|Executor`", workspace)
            self.assertIn("The Skill alone defines", workspace)

    def test_controller_global_continuity_heartbeat_is_persistent_singleton(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        workspace = flat(WORKSPACE_AGENTS) if WORKSPACE_AGENTS is not None else ""

        for phrase in (
            "one persistent Controller-global continuity heartbeat",
            "through idle periods and worker/job completions",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, orchestration)

        self.assertIn("Keep one retargeted, never duplicated Controller heartbeat", router)
        self.assertIn("Each wake resumes that Controller", router)
        self.assertIn("drains prebound terminal absorb/route/activate/title/pin/CAS before final", router)
        self.assertIn("`activate-successor` CAS", orchestration)
        self.assertIn("source_turn_state=IN_PROGRESS|FINAL", orchestration)
        self.assertIn(
            "An interactive authentication, credential, or approval boundary",
            orchestration,
        )
        self.assertIn("keep the same task, turn, session", orchestration)
        self.assertIn("never substitute `FINAL + NON_TERMINAL`", orchestration)
        self.assertIn("atomically prebinding the prospective job", orchestration)
        self.assertIn("same-owner recovery wake", orchestration)
        self.assertIn("never delete the global automation", orchestration)
        self.assertIn("already user-authorized desktop singleton", orchestration)
        self.assertIn("does not authorize installing one where none exists", orchestration)
        self.assertIn(
            "terminal callbacks and explicit Controller resume remain the recovery path",
            orchestration,
        )
        if workspace:
            self.assertIn("Controller terminal/state recovery", workspace)

        self.assertIn("Adjust its cadence in place", orchestration)
        self.assertIn("do not create a faster or slower duplicate", orchestration)
        self.assertIn("The explicitly owner-authorized Controller-global singleton", orchestration)
        for phrase in (
            "Keep that heartbeat prompt static",
            "rebuildable Controller control snapshot",
            "prebound `completion_binding`",
            "identity-only `pending_absorptions`",
            "compare-and-swap revision",
            "atomic replace",
            "`NONE -> CLAIMED -> SENT`",
            "calls one thread-list operation",
            "batch-waits only the named active roles",
            "A crash before absorption leaves the pending record",
            "ambiguous delivery is never blindly resent",
        ):
            with self.subTest(snapshot_phrase=phrase):
                self.assertIn(phrase, orchestration)

        for phrase in (
            "Slurm checks capacity only for exact `A100_CAPACITY_AVAILABLE`",
            "exact `A100_CAPACITY_AVAILABLE`",
            "never redoes role semantics, interprets protected science",
        ):
            with self.subTest(router_a100_phrase=phrase):
                self.assertIn(phrase, router)

        for phrase in (
            "use a queue-first A100 policy",
            "submit it to Slurm immediately even when all cards are allocated",
            "exact blocker trigger is `A100_CAPACITY_AVAILABLE`",
            "One wake may run one read-only `ecnuhpc` Slurm node allocation check",
            "Never create a capacity-only heartbeat",
            "unbound capacity state",
        ):
            with self.subTest(orchestration_a100_phrase=phrase):
                self.assertIn(phrase, orchestration)

    def test_recovered_funnel_denominators_are_honestly_named(self) -> None:
        portfolio = flat(PORTFOLIO_SEARCH)
        for phrase in (
            "Funnel denominators must be stage-homogeneous",
            "Do not combine brief-local `PROBE` tokens, historical selected lineages",
            "`admission-equivalent lineages`",
            "publish its exact construction",
            "remain `NOT_ESTIMABLE`",
            "missing global terminals are evidence gaps, not negative outcomes",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, portfolio)

    def test_funnel_circuit_breaker_uses_r1_and_access_failures(self) -> None:
        programs = flat(PROGRAMS)
        for phrase in (
            "three consecutively admitted `PROBE`s in one funnel produce no valid `R1`",
            "the same repairable access/tool root cause produces two `HOLD_ACCESS_CHANNEL` events",
            "pause candidate generation rather than changing ontology",
            "public-source `R0` reaches a decision",
            "strict-blind work with a missing safe tree blocks before dispatch",
            "one representative repaired `R1` to pass under an unchanged protocol and existing cap",
            "not unrelated access failures or distinct mechanisms",
            "propose one scoped closure through the Closure Confidence Gate rather than closing automatically",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, programs)

        for metric in (
            "time-to-valid-R1",
            "R0-to-R1 pass rate",
            "access-hold rate",
            "governance-attention share",
        ):
            with self.subTest(metric=metric):
                self.assertIn(metric, programs)

    @unittest.skipUnless(
        WORKSPACE_AGENTS is not None and WORKSPACE_AGENTS.is_file(),
        "set XAR_WORKSPACE_AGENTS to enable workspace integration checks",
    )
    def test_workspace_agents_matches_lite_blindness_r0_and_callback_contract(self) -> None:
        assert WORKSPACE_AGENTS is not None
        workspace = flat(WORKSPACE_AGENTS)
        router = flat(SKILL)
        integrity = flat(INTEGRITY)
        orchestration = flat(ORCHESTRATION)
        for phrase in (
            "This file is the workspace router",
            "do not duplicate its orchestration, model-routing, Pro, R0--R3, closure or recovery procedures here",
            "Default to Lite by side effects and coordination",
            "Reliability floor",
            "protected/public-test isolation",
            "finite `BLOCKED` only for a genuine external fact or unavailable authority",
            "`DONE` requires scientifically `CLOSED`",
            "`public_source` is the default",
            "Enable `strict_result_blind` only for a prospectively named independence",
            "Missing safe access blocks before an Audit sees bytes",
            "Activity, artifact/session/terminal counts, token volume and GPU utilization are process diagnostics",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, workspace)

        self.assertLess(len(WORKSPACE_AGENTS.read_bytes()), 10_000)
        self.assertIn("Default to `operating_weight=lite`", router)
        self.assertIn("`BLOCK_PRE_DISPATCH_ACCESS`", integrity)
        self.assertIn("`closure_risk=LOW|HIGH`", router)
        self.assertIn("A successful tool receipt releases the worker immediately", router)
        self.assertIn("one ordinary top-level `send_message_to_thread`", orchestration)

        for conflicting in (
            "Every research terminal callback has a hard controller completion gate",
            "Treat terminal closure as one atomic controller transaction",
            "Every zero-GPU dispatch must record",
            "Treat ChatGPT Pro as a third portfolio lane",
            "Prefer fully utilizing the three-job ceiling",
            "ICLR 2026 target",
        ):
            with self.subTest(conflicting=conflicting):
                self.assertNotIn(conflicting, workspace)

    @unittest.skipUnless(
        WORKSPACE_AGENTS is not None and WORKSPACE_AGENTS.is_file(),
        "set XAR_WORKSPACE_AGENTS to enable workspace integration checks",
    )
    def test_workspace_agents_matches_real_scout_r1_r2_and_unknown_routing(self) -> None:
        assert WORKSPACE_AGENTS is not None
        workspace = flat(WORKSPACE_AGENTS)
        router = flat(SKILL)
        integrity = flat(INTEGRITY)

        self.assertIn("proportional R0--R3 readiness", workspace)
        self.assertIn("The Skill alone defines", workspace)
        for phrase in (
            "`2` or `3` necessary arms",
            "`6` paired bundles",
            "`UNKNOWN_TO_SYSTEM_PROFILE`",
            "`UNKNOWN_TO_CALIBRATION`",
            "`UNKNOWN_TO_SCOUT`",
            "`DEFERRED_TO_CONFIRMATION`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router + " " + integrity)

        for stale in (
            "`R1`: run one outcome-blind implementation/profile smoke",
            "`R2`: freeze complete code/config/data/model/carrier identity; full cells",
        ):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, workspace)

    def test_forward_traces_are_decisive_without_successor_cascade(self) -> None:
        rows = access_policy_rows()

        public_trace = rows[("public_source", "verified public primary locator")]
        strict_missing_trace = rows[
            ("strict_result_blind", "safe tree/packet missing or invalid")
        ]

        self.assertEqual(public_trace, "PROCEED_R0")
        self.assertEqual(strict_missing_trace, "BLOCK_PRE_DISPATCH_ACCESS")
        self.assertNotIn("PACKET", strict_missing_trace)
        self.assertNotIn("AUDIT", strict_missing_trace)

    def test_cross_stage_hard_controls_remain(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "cannot override platform, system, developer, or `AGENTS.md` authority",
            "Confirmatory, superiority, powered-negative, or closure claims additionally require complete power",
            "Outcome-blind repair stays inside the unchanged contract and budget",
            "after protected outcome access",
            "Before scientific `R3`, `R2` freezes",
            "public primary methods, results, appendices, and official-code documentation",
            "one verified complete witness",
            "Pro and same-model review are advisory",
            "No token target, artifact count, retry count, reviewer verdict, or governance ratio can convert an unresolved scientific, exposure, fairness, provenance, budget, or reproducibility defect into `PASS`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

    def test_resource_forecast_is_not_the_hard_gpu_ceiling(self) -> None:
        orchestration = flat(ORCHESTRATION)
        integrity = flat(INTEGRITY)
        for phrase in (
            "planning_estimate",
            "hard_safety_ceiling",
            "exceeding it is a forecast miss, not an automatic invalid terminal",
            "not a predicate Audit or new scientific version",
            "not predicted result sign",
            "lower-bound heuristics, not target caps",
            "outcome-blind checkpoints",
        ):
            with self.subTest(source="orchestration", phrase=phrase):
                self.assertIn(phrase, orchestration)
        for phrase in (
            "outer exploratory safety ceiling",
            "A forecast miss below the ceiling is not by itself `ENGINEERING_INVALID`",
            "Queue by surviving novelty, problem importance, causal depth and expected decision information",
        ):
            with self.subTest(source="integrity", phrase=phrase):
                self.assertIn(phrase, integrity)
        if WORKSPACE_AGENTS is not None:
            workspace = flat(WORKSPACE_AGENTS)
            self.assertIn("hard resource ceilings", workspace)
            self.assertIn("The Skill alone defines", workspace)
            self.assertNotIn("planning_estimate", workspace)

    def test_knowledge_handoff_is_conditional_not_default_lite_schema(self) -> None:
        router = flat(SKILL)
        self.assertIn("Add knowledge provenance only for a decision-changing synthesis handoff", router)
        self.assertIn("never a routine local workflow/code audit", router)
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
