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
WORKSPACE_AGENTS_VALUE = os.environ.get("XAR_WORKSPACE_AGENTS")
WORKSPACE_AGENTS = Path(WORKSPACE_AGENTS_VALUE) if WORKSPACE_AGENTS_VALUE else None


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
            "one-shot Pro advisory remain Lite",
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
        self.assertIn("The contract itself is the only task capsule", router)
        self.assertIn("Fuse deterministic checks", router)
        self.assertIn("do not wake a model for each check", router)
        self.assertIn("A local executor returns its final directly", router)
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
            "make one bounded top-level send",
            "release the worker on a successful receipt",
            "never resend an ambiguous delivery",
            "An ACK never blocks the worker",
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
        self.assertIn("One pre-registered Controller fallback recovers", router)
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
            "end only after one open-loop audit maps every named action to `DONE`",
            "externally/authority `BLOCKED`",
            "`DELEGATED` with a successful receipt",
            "A concept explanation, status reply, or side question does not clear an active objective",
            "unless the user replaces/cancels it or its authority changes",
            "Execute any safe current next decision instead of leaving it as prose",
            "Do not persist this audit or create Program, lease, callback, sidecar, heartbeat, `RECEIPT_ONLY`, `FINAL_ACK`, or receiver machinery",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        self.assertIn("An ACK never blocks the worker", router)

    def test_pro_is_risk_triggered_one_shot_not_sink_lifecycle(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "For a `HIGH` closure",
            "submit one Pro rebuttal, read once",
            "no sink, polling, duplicate, or follow-up",
            "Record only its trigger, disposition, decision effect, and final confidence",
            "never hard-close from unavailability",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

    def test_pro_generation_is_off_critical_path_without_polling_machinery(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "Keep Pro off the critical path",
            "submit once, continue local work",
            "current owner make at most one state-only check after local work completes",
            "Add no monitor, poll loop, sink, automation, lifecycle, duplicate, or follow-up",
            "On `READY`, read once and verify",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)

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
            "Packet, locator, sidecar, and file checks stay inside the current owner as mechanical preflight",
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
            self.assertIn("rerun under a new attempt identity within the existing cap", text)
            self.assertIn("returns to prospective adjudication", text)

    @unittest.skipUnless(
        WORKSPACE_AGENTS is not None and WORKSPACE_AGENTS.is_file(),
        "set XAR_WORKSPACE_AGENTS to enable workspace integration checks",
    )
    def test_outcome_blind_engineering_loop_does_not_create_callback_ceremony(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        workspace = flat(Path(os.environ["XAR_WORKSPACE_AGENTS"]))
        for phrase in (
            "one uninterrupted Executor loop",
            "root cause -> exact patch -> exact-path smoke -> validation -> authorized run",
            "Do not terminate, mint a contract/task/lease/version",
            "A new run/output identity preserves provenance",
        ):
            with self.subTest(router_phrase=phrase):
                self.assertIn(phrase, router)
        for phrase in (
            "one uninterrupted engineering loop",
            "without an intermediate terminal, Controller callback, contract, task, lease",
            "scientific identity, exposure, authority, budget, or protected-outcome state",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)
        self.assertIn("One repair authorization includes diagnosis, patch", workspace)
        self.assertIn("Do not mint an intermediate contract, task, lease", workspace)

    @unittest.skipUnless(
        WORKSPACE_AGENTS is not None and WORKSPACE_AGENTS.is_file(),
        "set XAR_WORKSPACE_AGENTS to enable workspace integration checks",
    )
    def test_explorer_pauses_only_on_true_multi_card_saturation(self) -> None:
        router = flat(SKILL)
        lanes = flat(PORTFOLIO_LANES)
        workspace = flat(Path(os.environ["XAR_WORKSPACE_AGENTS"]))
        for text in (router, lanes, workspace):
            with self.subTest(source=str(text[:80])):
                self.assertIn("per candidate/version", text)
                self.assertIn("not a portfolio-wide mutex", text)
                self.assertIn("every currently usable, authorized card", text)
                self.assertIn("waits solely for capacity", text)
                self.assertIn("Blocked", text)
                self.assertIn("empty cards do not count", text)
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
            "Controller routes and accepts",
            "Explorer owns one complete source-to-`PROBE` loop",
            "Audit owns the whole `R0` decision in one owner/terminal",
            "Executor enters only after a complete implementation contract is frozen",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        self.assertIn("A single Audit is not a global serialization lock", orchestration)

    def test_idea_boundaries_reuse_records_and_canonical_sessions(self) -> None:
        router = flat(SKILL)
        for phrase in (
            "reuse the existing task capsule, decision record, and terminal/closure record",
            "Do not include the prior idea's raw transcript",
            "use `/compact` only when decision-relevant history has become materially redundant",
            "reuse the canonical role session only after a runtime-supported compact/reset succeeds",
            "Record selection is not context isolation",
            "open one fresh session, transfer the canonical role binding",
            "close/archive the prior session so no duplicate owner remains",
            "load only the authoritative section and directly referenced evidence needed to resolve it",
            "complete record only for an unresolved decision-critical contradiction",
            "never load a prior raw transcript",
            "Never collapse `ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`, `CARRIER_STOP`, or `UNOBSERVED` into a scientific negative",
            "A contract change creates a new candidate/version and preserves the old records",
            "not a new data protocol, capsule, schema, lifecycle, context-bootstrap layer, automation, or evidence substitute",
            "They cannot change the research contract, metric, seed, budget, stop rule, or protected/outcome boundary",
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

    def test_open_candidate_cannot_end_without_owner_or_explicit_archive(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        workspace = flat(WORKSPACE_AGENTS) if WORKSPACE_AGENTS is not None else ""

        for phrase in (
            "After `ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`, or `CARRIER_STOP`",
            "`OPEN_WITHOUT_OWNER`",
            "a successful same-idea successor receipt",
            "`BLOCKED` with one reopening fact/observer/trigger",
            "non-active evidence-gap archive with a reopening fact",
            "the Controller owns the route",
        ):
            with self.subTest(router_phrase=phrase):
                self.assertIn(phrase, router)

        for phrase in (
            "worker-local terminals, never Controller route decisions",
            "terminal absorption is incomplete",
            "A worker recommendation",
            "cannot discharge this Controller duty",
            "`OPEN_WITHOUT_OWNER` is an invalid lifecycle state",
            "wake the Controller for lifecycle repair",
            "it cannot choose the scientific successor",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)

        if workspace:
            for phrase in (
                "`ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`, and `CARRIER_STOP` are local execution terminals",
                "Controller absorption is incomplete",
                "`OPEN_WITHOUT_OWNER`",
                "The Controller—not the Executor—owns",
                "global continuity heartbeat must flag an ownerless open candidate",
            ):
                with self.subTest(workspace_phrase=phrase):
                    self.assertIn(phrase, workspace)

    def test_managed_runtime_binding_and_model_routing_are_explicit(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        for phrase in (
            "verify its saved Project ID, cwd/repository, candidate/version, and canonical role",
            "A projectless or unverified worker has no scientific/shared-state authority",
            "Pin only active Managed canonical roles that need Controller follow-up",
            "Lite and Pro advisory tasks are never auto-pinned",
            "At each Controller resume, activation, state transition, and terminal",
            "use runtime APIs to reconcile pins",
            "`gpt-5.6-sol max`",
            "`gpt-5.6-sol xhigh`",
            "`gpt-5.6-sol high`",
            "`gpt-5.6-luna max`",
            "Bind the route to the active objective",
            "Keep model and effort stable until that objective's terminal",
            "Reclassify only a separately bounded successor",
            "Resume the same canonical session on `gpt-5.6-luna max`",
            "Never create another role or session solely to change model",
            "never substitute `luna max` for `sol xhigh/max`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
        self.assertIn("A projectless task", orchestration)
        self.assertIn("Lite and Pro advisory tasks are never auto-pinned", orchestration)
        for phrase in (
            "call `set_thread_pinned`",
            "The route is sticky for the active objective",
            "Do not switch model while one objective is in flight",
            "Reclassify only after terminal absorption or an explicit redispatch",
            "Do not create an Implementer, Runner, second owner, or new session",
        ):
            with self.subTest(orchestration_phrase=phrase):
                self.assertIn(phrase, orchestration)

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
            self.assertIn(
                "`<Role> · <candidate-or-bounded-scope> · <STATE>`",
                workspace,
            )
            self.assertIn("Keep the sidebar pinned set synchronized", workspace)
            self.assertIn("`gpt-5.6-luna` with `max`", workspace)

    def test_controller_global_continuity_heartbeat_is_persistent_singleton(self) -> None:
        router = flat(SKILL)
        orchestration = flat(ORCHESTRATION)
        workspace = flat(WORKSPACE_AGENTS) if WORKSPACE_AGENTS is not None else ""

        for phrase in (
            "one persistent Controller-global continuity heartbeat",
            "remains active through idle periods and worker/job completions",
            "clear only the exact job block",
            "never delete the global automation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, router)
                self.assertIn(phrase, orchestration)
                if workspace:
                    self.assertIn(phrase, workspace)

        self.assertIn("Adjust its cadence in place", orchestration)
        self.assertIn("do not create a faster or slower duplicate", orchestration)
        self.assertIn("The explicitly owner-authorized Controller-global singleton", orchestration)

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
        for phrase in (
            "Default to `operating_weight=lite`",
            "`public_source` is the default",
            "`BLOCK_PRE_DISPATCH_ACCESS`; the Audit is not launched",
            "Full license coverage, power/seed design, natural prevalence, full recipient matrix",
            "A successful tool receipt releases the worker immediately",
            "never waits for `RECEIPT_ONLY`, `FINAL_ACK` or a receiver ping",
            "Reconcile only shared resources touched by the Managed event",
            "Batch zero-delta dashboard, Curator, closed-alias and Atlas maintenance after 3--5 decision milestones",
            "Do not trigger dashboard work for source fetches",
            "`closure_risk=LOW|HIGH`",
            "`PROVISIONAL_CLOSE_PENDING_REBUTTAL` or `HOLD_INFORMATION`",
            "Pro is a standard risk-triggered advisory",
            "`CONFIRM_SCOPED_CLOSE | NARROW_CLOSE | REOPEN_R0 | HOLD_INFORMATION`",
            "any `UNKNOWN` is `HIGH`",
            "a multi-source composition is never one complete witness",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, workspace + " " + router)

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
        integrity = flat(INTEGRITY)

        for phrase in (
            "outcome-blind real-carrier minimal code path",
            "no-utility real-path system profile",
            "pure synthetic smoke has conversion value only when",
            "claim-proportionate scientific contract",
            "`2` or `3` necessary arms",
            "`6` paired bundles",
            "primary metric, MPE, guard comparator",
            "Final superiority or scientific closure additionally requires complete power",
            "`UNKNOWN_TO_SYSTEM_PROFILE`",
            "`UNKNOWN_TO_CALIBRATION`",
            "`UNKNOWN_TO_SCOUT`",
            "`DEFERRED_TO_CONFIRMATION`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, workspace)
                self.assertIn(phrase, workspace + " " + integrity)

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
