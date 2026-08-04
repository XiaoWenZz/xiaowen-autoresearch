# Research integrity rules

Use this reference before literature synthesis, experiment design, statistical interpretation, claim drafting, review, or adjudication.

## Contents

1. Claim discipline
2. Outcome conditioning and venue labels
3. Public-source and strict-blind access
4. Specificity claims
5. Pre-registration
6. Proportional readiness
7. First real Scout default
8. Proxy estimands and gate calibration
9. Statistics
10. Baselines and controls
11. Literature and citations
12. Evidence and negative results
13. Scientific progress versus activity
14. Closure confidence and scoped NO-GO
15. Review and adjudication
16. Reporting

## Claim discipline

- Label a source-supported statement as a **fact** only after checking the primary source.
- Label an explanation derived from evidence as an **inference** and state its scope and alternatives.
- Label an untested mechanism or expected outcome as a **hypothesis**.
- Match claim strength to task, seed, dataset, protocol, and sample coverage.
- Do not turn a diagnostic, smoke test, or gate into method-success language.
- A Scout result is a `SCOUT_SIGNAL`, diagnostic, scoped negative result, or carrier-level stop. It cannot establish method superiority or an accepted publication-facing claim.

## Outcome conditioning and venue labels

- A request to continue until a good, significant, positive, or publishable
  result authorizes persistent bounded work, not favorable-outcome stopping,
  selective reporting, threshold relaxation, or repeated tuning until success.
- Define each candidate's budget, gate, and terminal conditions before its
  outcomes are visible. Start a fresh charter when moving to another candidate.
- A prospectively frozen staged design may expand only through its declared
  action table and maximum ceiling. A material screening signal may justify a
  prospective GPU-envelope amendment for future or disjoint evidence, but it
  cannot enlarge the observed attempt, change its analysis, or rescue it after
  protected-outcome access.
- Treat “A-tier viable,” venue fit, and reviewer-interest labels as planning
  judgments only. They cannot establish acceptance probability, scientific
  quality, or a publication-facing claim.
- Do not replace importance, irreducibility, novelty, identifiability, or
  evidence feasibility with one uncalibrated numeric LLM or reviewer score.
- Before a method-search experiment, require a decision table for positive,
  negative, and ambiguous outcomes. If every branch leads to more variants,
  the run is exploratory activity without a bounded stopping rule.
- Do not use publication-stage novelty, irreducibility, specificity,
  scalability, or venue readiness to block a cheap, interpretable
  problem-existence witness. Apply those gates at Contribution Selection after
  a material signal.

## Public-source and strict-blind access

Choose the access mode before dispatch. `public_source` is the default for
Opportunity Search and ordinary public-literature `R0`. It permits reading the
complete public primary paper, including method, results, appendix, tables and
figures, plus paper-declared official code and documentation. Preserve source
identity and claim mapping. Public benchmark values are prior literature
evidence; they are not the candidate's own protected scientific outcome and do
not trigger no-rescue.

Use `strict_result_blind` only when a prospectively frozen independence or
anti-anchoring decision names the exact result family that must remain unseen
and explains why ordinary source criticism is insufficient. Strict blindness
means preventing those bytes from entering the model context, not reading them
and promising to ignore them.

| access mode | pre-dispatch source state | dispatch decision |
|---|---|---|
| `public_source` | verified public primary locator | `PROCEED_R0` |
| `strict_result_blind` | safe tree/packet validated | `DISPATCH_STRICT_R0` |
| `strict_result_blind` | safe tree/packet missing or invalid | `BLOCK_PRE_DISPATCH_ACCESS` |

Before a strict-blind Audit is dispatched, the current owner performs one
deterministic mechanical preflight: freeze exact files, URLs, API fields,
archive members, or source-code paths; strip forbidden result-bearing fields or
sections without rendering them into model-visible output; bind exact source
identities; and validate both the allowlist and forbidden-field absence. This
preflight is not a Program, lease, lane, terminal, or separate research role.
If it fails, the Audit is not dispatchable. Do not launch an Audit to discover
that its access tree is missing.

Inside a valid strict-blind task, do not use surfaces that transitively load the
forbidden family, such as search snippets, result-bearing `README` sections,
preview cards, rendered index pages, cached summaries, metrics, plots,
predictions, labels, logits, or public-test outputs. Prefer field-selective APIs
or exact raw objects already admitted by the safe tree.

If forbidden bytes reach a strict-blind owner, invalidate only that exact blind
attempt and exclude the value from its reasoning. Do not archive or drop the
candidate, create an exposure artifact family, generate a packet successor,
dispatch a fresh Audit, or self-retry. A later fresh-owner attempt requires an
explicit new decision after a safe tree is already validated; it is never an
automatic `exposure -> packet -> fresh-audit` cascade. Exposure is a protocol-
control event, not scientific evidence.

A session that has seen forbidden bytes is not eligible for a later
strict-blind Audit, even after compaction or summary. Use one fresh unexposed owner
after the safe tree passes; do not treat context reduction as erasure.

## Specificity claims

- Claim federation specificity only when deleting federation changes the
  problem or feasible solution under a named information, heterogeneity,
  communication, coordination, or deployment constraint.
- Claim collaborative federated benefit only when the proposed intervention
  has incremental value over local-only or isolated execution under a carrier
  with materially nonzero cross-party interaction. Removing harmful averaging
  is a repair result unless beneficial transfer is separately identified.
- Claim PEFT specificity only when deleting the adapter constraint removes a
  material algebraic, capacity, state, or communication bottleneck.
- Claim a dynamic policy is needed only after the strongest matched-cost
  static, phase-static, rotation, or shared-capacity reduction leaves material,
  identifiable residual value.
- Claim a new method kernel only after operating on the represented
  function/state fails to reduce the proposal to a verified classical or
  generic operator.
- A failed specificity test may reveal a valid broader problem. Reframe it
  honestly and return it to Portfolio Search; do not preserve the narrower
  label for novelty.

## Pre-registration

Before an evidentiary run, record:

1. research question and hypothesis;
2. independent, dependent, and control variables;
3. primary metric and directional expectation;
4. initial sample or complete paired-seed tranche and its power rationale; an
   unknown-variance calibration Scout must instead freeze a finite ceiling and
   a screening-only claim, never imply final power;
5. maximum staged ceiling and `expand | futility | hold` actions;
6. exclusions, data cleaning, and failure handling;
7. stopping rule, sequential adjustment or disjoint follow-up analysis;
8. the claim the run can support or falsify.

If these change after results are visible, preserve the original plan, record the amendment, and label the new analysis exploratory. Never silently redefine success.

### Proportional readiness

Use `R0`--`R3` only as shorthand inside the existing planning record, not as a
new lifecycle, state tree, or artifact family:

- `R0`: freeze the smallest carrier/next-cell envelope—actor, lawful inputs,
  exact next cell, identities needed to make it interpretable, protected-
  outcome boundary, matched-cost invariant, hard invalidators, and cap.
- `R1`: keep at most one active outcome-blind real-carrier-path or train-source
  mechanical smoke/profile contract for that exact cell. Prefer the minimal
  code path that the scientific Scout will execute. A pure synthetic smoke has
  scientific conversion value only when that controlled synthetic carrier is
  itself the preregistered scientific witness; otherwise it is engineering
  evidence only. An unchanged-protocol outcome-blind repair may rerun under a
  new attempt identity within the existing cap; a carrier, arm, estimand,
  threshold, or scientific-contract change returns to prospective adjudication.
- `R2`: freeze a scientific contract proportionate to its claim. A first
  descriptive Scout binds exact code/config/data/model/carrier/attempt identity,
  `2` or `3` necessary arms, `6` paired bundles, estimand, MPE, metric, guard,
  strongest complete fair baseline, distinct mechanism deletion when
  applicable, analysis/action table, stops, exposure, finite cap, and evidence
  handling. It does not require final power or multiplicity and claims only a
  descriptive `SCOUT_SIGNAL`, guard stop, variance/covariance calibration, and
  observed cost. System profiles see no utility; utility-bearing calibration
  units are disjoint or count in the frozen Scout sequence. Final superiority,
  powered negative, or scientific closure additionally requires complete power,
  multiplicity, full claim-proportionate baselines, and external-validity scope.
- `R3`: begin scientific execution only after `R2` and every applicable
  integrity, fairness, provenance, exposure, and authority control passes.

An `R1` failure is engineering or carrier evidence, never a scientific
negative. Full-program portability, future profiles, or Confirmatory surfaces
cannot block `R1` unless they change the next cell's identity or safety. Expose
no scientific outcome before `R2` is frozen; any later scientific-contract
change follows the existing amendment, new-attempt, and no-rescue rules.

## First real Scout default

### Novelty and fatal carrier gate

- Rank a candidate's problem value, causal depth, residual novelty, and
  FedFT/PEFT specificity before implementation convenience. Carrier availability
  cannot turn Opportunity Search into a search for easy experiments.
- Once a `PROBE` is admitted, optimize for the shortest lawful path to one real,
  controlled, interpretable Scout outcome. Before implementation, apply only
  three fatal carrier checks:
  1. **Semantic/intervention conformance:** preserve actor, decision time,
     lawful information, feasible action set, common parent, complete persistent
     state transition, recipients, and estimand. Every arm acts on the same
     pre-policy work product; action-dependent retraining, post-action
     information, or a different adaptation trajectory is a `HARD_BLOCK`.
  2. **Lawful identity/exposure:** identify model, code, data, weights,
     licenses/use, and train/calibration/evaluation exposure. Ambiguous identity,
     authorization, or prohibited exposure is not profileable.
  3. **Observable identifiable contrast:** expose a real primary metric and
     freeze the strongest complete simple matched baseline's identity, fairness,
     and constructability. Match actor, time, information, parent/work product,
     calibration opportunity, implementation quality, and relevant resources;
     make the baseline runnable at `R1` and execute the exact comparison at
     `R2/R3`. An action-restricted comparator is a mechanism deletion, not the
     strongest baseline when a simple complete same-action-set baseline is
     constructable.
  Reject a semantically mismatched named carrier at this gate.
- Missing official code is not a fatal check. Build the smallest controlled
  carrier from scratch when those three checks can pass within the exploratory
  envelope. A full five- or nine-arm platform, exact publication-grade physical
  ledger, final power, full recipient matrix, every endpoint, and every paper
  baseline are not prerequisites for the first problem-existence Scout.
- Bind those semantic fields and the matched-cost invariant directly to the
  executable carrier in the Scout contract before profiling. Include hidden
  trainable or persistent shared state and whether the chosen action persists
  into the next claimed transition. Any unmapped or altered field is a
  `HARD_BLOCK`; a one-step carrier supports only immediate-recipient claims,
  not cumulative chronology. This compact mapping is not a carrier dossier.

### Time and dual-5090 exploratory envelope

Define `time-to-first-scientific-outcome` from the causal fingerprint's first
`PROBE` admission. The clock never resets for carrier changes, implementation
rewrites, candidate versions, archives, or owner transfers. It stops only at a
sealed real candidate-versus-complete-baseline metric after all currently
prescribed pairs, or a separately frozen severe-harm boundary, reach their
terminal action. Partial `n0`, synthetic fixtures, profiles, model loading,
mechanical failures, documents, jobs, carrier invalidity, and evidence-gap
archives do not count.

Report both the time distribution and the fraction of **all admitted probes**
reaching a valid outcome by `T+72 h`. Keep archived, invalid, resource-held,
active-censored, and incomplete probes in the denominator. An SLA breach is a
process diagnosis; it cannot reset the clock, change novelty rank, or justify a
weaker carrier.

For an available dual-RTX-5090 host and a one-to-three-day decision target, use
these defaults unless a prospectively stricter candidate cap is already bound:

| field | default exploratory bound |
| --- | --- |
| fatal carrier decision | by `T+12 h` after `PROBE` admission |
| first semantically valid adaptation-and-evaluation path | by `T+24 h`; loading or job submission does not qualify |
| first scientific Scout outcome | by `T+72 h` |
| outcome-blind real-path profile | at most `4` aggregate RTX-5090 GPU-hours |
| scientific arms | `2` or `3` necessary arms |
| paired seed bundles | deterministic candidate/version-derived order; `n0=3`, `nmax=6`; randomized/counterbalanced arm order |
| total exploratory compute | at most `96` aggregate RTX-5090 GPU-hours, including profile and all arms |
| scientific run wall time | at most `48 h`, using at most two GPUs; whole paired bundles stay on one GPU |

Classify unknowns before acting:

| class | routing |
| --- | --- |
| `HARD_BLOCK` | wrong actor/time/action/parent/state/recipient/estimand; leakage; unlawful or ambiguous assets; no real metric or complete matched baseline |
| `UNKNOWN_TO_SYSTEM_PROFILE` | runtime, memory, compilation, numerical stability, throughput, failure frequency, per-pair cost, and cap fit |
| `UNKNOWN_TO_CALIBRATION` | paired variance/covariance; use disjoint units or count them in the frozen Scout sequence |
| `UNKNOWN_TO_SCOUT` | effect direction/magnitude, guard behavior, action frequency, and mechanism diagnostic |
| `DEFERRED_TO_CONFIRMATION` | inferential sample size/power, multiplicity, full baselines, external validity, and paper-level mechanism evidence |

A system profile may change only batch size, precision, compilation,
checkpointing, and other non-scientific execution settings; it must not inspect
primary, guard, or mechanism utility. After any utility exposure, changing the
candidate, baseline, branch definitions, diagnostics, thresholds, MPE, guard,
metric, strata, or seed order creates a new version with disjoint Scout units.

The `96` GPU-hour/`48 h` envelope is a ceiling, not an allocation. Unused GPU,
an SLA, or available budget never entitles an extra arm, seed, endpoint,
candidate, or profile. There is no automatic cap expansion. If a pre-utility
real profile establishes that the frozen minimal faithful Scout cannot fit and
no cheaper faithful carrier exists, stop that attempt. Any higher ceiling needs
explicit prospective authority for a new attempt/version with hardware, cap,
arms, seeds, question, exposure and outcome actions frozen before utility
access. It uses disjoint evidence and cannot rescue or reinterpret the stopped
attempt. Without that authority, use `HOLD_INFORMATION` with an exact resource
reopening fact, not an evidence gap or scientific negative.

### First-Scout contract and action table

The default first Scout contains:

1. the candidate decision policy;
2. the strongest complete simple matched baseline, using the candidate's
   feasible action set when such a simple policy is constructable; and
3. a mechanism deletion or necessary null only when it is distinct from arm 2.

Two arms suffice when the candidate is itself the simplest lawful policy over
the complete action set. If it adds learned/structured policy, history, or
nontrivial calibration, use three: candidate, simplest complete same-action-set
rule, and action-restricted mechanism deletion. Do not call the deletion the
strongest baseline merely because it is easy to implement.

For a harm-prevention claim, freeze the retained parent/no-action state as the
guard comparator, even when its metric can be obtained without another
adaptation run. Candidate-versus-baseline alone cannot show that both avoided
the same recipient harm.

Before outcome access freeze the exact candidate/version, carrier and asset
identities, origin/recipient construction, parent and persistent state, metric,
MPE, exact guard statistic/comparator, six-seed order, paired unit/GPU mapping,
randomized or counterbalanced arm order, one mechanism statistic, failures and
missingness, any severe-harm boundary, analysis code, compute cap, and every
action below. Publication-scale coverage follows only after material signal.

| frozen branch | action and claim boundary |
| --- | --- |
| invalid identity, leakage, failed arm, or broken matched-cost invariant | `ENGINEERING_INVALID` or exact `CARRIER_STOP`; no scientific inference |
| at `n0=3`, a separately frozen severe-harm boundary is crossed | stop for the guard and report every outcome; ordinary tail/mean guards wait for `nmax` |
| at `n0=3`, any other positive or negative valid result | mandatory unchanged continuation through seeds 4--6; no positive label, version selection, method change, cap escalation, effect claim, or promotion |
| external infrastructure failure | rerun the same seed unchanged only when demonstrably external; apply the frozen failure rule to method-induced failure |
| at `nmax=6`, all pairs/failures are accounted for, mean effect meets MPE, guards and mechanism direction pass, median paired effect is positive, and at least four of six paired effects are positive | descriptive `SCOUT_SIGNAL`; route to Contribution Gate |
| at `nmax=6`, validity passes but the signal rule does not | `HOLD_INFORMATION` diagnostic; no superiority, powered negative, or scientific close |
| six valid pairs cannot complete within the frozen cap | `HOLD_INFORMATION` resource/incomplete Scout; no scientific negative |

Every `SCOUT_SIGNAL` carries: “descriptive six-paired-bundle portfolio screen;
selected on Scout data; not inference, superiority, a powered negative,
definitive effect estimate, or scientific closure.” Never use its unshrunk
effect as the confirmatory target. Final inference uses disjoint follow-up seeds
or a prospectively valid sequential adjustment.

`SCOUT_SIGNAL` does not authorize Confirmation by itself. Apply these gates in the same
record, not a new lifecycle: (0) lock all Scout code, units, outcomes, failures,
and exclusions; (1) refresh nearest-neighbor residual and carrier conformance;
(2) freeze an independent powered/multiplicity-aware design with disjoint seeds;
(3) add only baselines and deletions needed to isolate the mechanism; (4) test
external validity across the scopes the claim names; and (5) complete final
inference, failure reporting, resource accounting, and reproducibility. Failure
at any gate revises or archives the scoped claim; Scout outcomes cannot rescue it.

### Anti-stall routing

- If a route remains in synthetic, engineering, or documentation gates, perform
  one complete root-cause inventory and then choose exactly one: minimal real
  carrier, structurally simplified new candidate/version, or evidence-gap
  archive. A renamed ledger, serializer, manifest, or carrier dossier is not a
  new root cause and receives no further repair cycle.
- An admitted `PROBE` plus a constructable lawful Scout outranks more idea
  search and more carrier documentation. Idle GPU is not scientific demand and
  never authorizes filler, weak baselines, low-quality ideas, or favorable-
  outcome stopping; it removes compute scarcity as an excuse for delay.

## Proxy estimands and gate calibration

- Write the target estimand and every proxy estimand separately. Examples that
  require an explicit bridge include one-step value versus trajectory AUC,
  common-state counterfactuals versus policy-induced state, validation loss
  versus public-test accuracy, and service balance versus population risk.
- Classify each bridge as proved, empirically calibrated, assumed, or unknown.
  An unknown bridge limits the result to `no promotion under this proxy`; it
  cannot establish superiority or permanent scientific closure.
- Calibrate a new diagnostic or promotion gate on a known positive case and a
  negative/static control when feasible. Report sensitivity failures instead
  of silently tightening or weakening thresholds.
- Calibrate a new or materially changed Opportunity Search gate separately:
  for a broad-domain gate, reconstruct at least three retrospective positives
  at their pre-signal information states and three obvious
  negatives/duplicates. The gate should admit every positive to a cheap probe
  and keep every negative out without requiring publication-stage facts.
- Justify thresholds by minimum practical effect, decision utility, power, or a
  prospectively declared engineering tolerance. A round number alone is not a
  scientific rationale.
- Separate selection uncertainty, winner's-curse or multiple-comparison
  effects, training-seed variance, and evaluation-example variance. Replaying
  only the selected top two does not estimate all of them.

## Statistics

- Freeze every staged-sampling branch before outcomes: complete paired seed
  bundles, initial tranche, maximum ceiling, and explicit expansion, futility,
  and hold decisions. Schedule every arm of one paired bundle on the same GPU;
  parallelize only complete bundles across GPUs.
- In the default six-pair Scout, `n0=3` has no positive stop: every valid
  positive or negative continues unchanged to all six unless a separately
  frozen severe-harm rule stops it. A different interim design needs valid
  prospective sequential accounting and still cannot create final evidence.
- Close a route from a weak or null small tranche only when a predeclared
  adequately powered futility boundary is met. Otherwise report
  `HOLD_INFORMATION`; absence of a screening signal is not a powered negative.
- Do not add trials merely because a result is non-significant. Use a preregistered fixed sample size, a justified power analysis, or a valid sequential design.
- Report uncertainty appropriate to the sampling unit. Multiple samples from one model checkpoint do not replace independent training seeds.
- Separate problem-sampling uncertainty, training-seed variance, evaluator variance, and API/model-version drift.
- Correct or disclose multiple comparisons and researcher degrees of freedom.
- Report all planned conditions, failed runs, exclusions, and deviations.
- Treat ceiling and floor effects as design limitations, not permission to search for a better-looking endpoint.

## Baselines and controls

- Equalize data, compute, seeds, evaluation, checkpoints, and implementation quality where the claim requires a fair comparison.
- Distinguish a stable baseline from an oracle or upper bound.
- Separate a repair contrast against a known-broken operation from a
  contribution contrast against the strongest valid simpler alternative.
  Include a mechanism-deletion control whenever it can preserve all other
  decision-relevant information, state, work, cost, and deployment behavior.
- Match feasible action sets when a simple complete policy is constructable.
  A restricted-action comparator may isolate action granularity, but it does
  not test policy novelty against the strongest complete simple alternative.
- Avoid cross-paper number comparisons unless protocol equivalence is demonstrated.
- Change one critical factor per confirmatory experiment when practical.
- Include discovery, warm-up, profiling, probing, and selector cost whenever
  the claim compares deployable total-cost methods. A static action discovered
  by an exhaustive oracle is not a zero-cost deployment baseline unless its
  discovery is independently amortized and reported as such.

## Literature and citations

- Search for relevance and counterevidence, not prestige. Institution, venue, citation count, and recency are discovery signals, not truth scores.
- Search by mathematical/system operation as well as domain object. Exact
  keyword absence cannot establish novelty when a classical or generic
  preserving reduction exists.
- Verify 100% of citations attached to substantive claims. Confirm title, authors, year, venue/status, and—most importantly—the exact claim in the source.
- Prefer original papers, official documentation, datasets, and standards over summaries.
- Preserve source URL or identifier, retrieval date, quoted location or section, and claim mapping.
- Treat anonymous, inaccessible, or metadata-only references as unverified until the content can be inspected.
- Do not manufacture a taxonomy gap by requiring empty cells.

## Evidence and negative results

- Save raw outputs before selecting examples or computing summaries.
- Treat an unexpectedly large positive effect as an attribution question:
  inspect leakage, scale/state/information mismatches, degenerate limiting
  cases, and the strongest simpler reduction before promotion.
- Preserve failed and null results with the same provenance fields as positive results.
- Count a negative result as progress when it falsifies a hypothesis, narrows a mechanism, or prevents repeated work.
- Do not select the best iteration, seed, checkpoint, or reviewer score as the sole reported result.
- Distinguish observed data from interpretation and future conjecture.

## Scientific progress versus activity

- Lead progress reports with problem existence, novelty residual, mechanism
  status, paper-path feasibility, Program/Epoch status, and the next exact
  uncertainty.
- Treat commits, files, documents, repositories, jobs, GPU utilization,
  verifier layers, and review volume as operational diagnostics only.
- Do not equate many incompatible scoped closures with progress toward one
  paper contribution. State separately whether evidence can be synthesized
  under a shared estimand, mechanism, protocol, and strongest baseline.
- Count a negative route as decision progress only once. Renaming the carrier,
  representation, selector, rank, or checkpoint does not create fresh
  uncertainty when the same distinct prediction was already falsified.
- Report `SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION` when a broad search ends
  for resource reasons. Budget exhaustion is not evidence that a field has no
  viable opportunity.

## Closure confidence and scoped NO-GO

Do not infer “nothing is worth doing” from overlap, one failed implementation, or one static carrier. Close only the narrowest estimand justified by one of:

1. a formal or empirically verified reduction that preserves the estimand,
   information access, cost accounting, temporal dynamics, and deployment
   constraints, and whose composed operations are jointly feasible for the same
   actor under one timing/state/communication contract;
2. a replicated high-confidence negative on an adequate carrier against the strongest relevant baseline;
3. failure of a preregistered minimum practical-effect threshold.

Before publishing a durable scientific `DROP` or `CLOSE`, freeze a compact
closure packet inside the existing decision record. It must name:

- the exact causal fingerprint, estimand, contract fields, and narrow scope
  being retired;
- which admissible basis above is complete and the exact witness or evidence;
- the strongest counterexample, preserving-witness failure, or alternative
  explanation that could reopen the route;
- one explicit reopening fact and whether the decision removes the last active
  `PROBE`, empties the funnel, or otherwise has portfolio-wide impact; and
- `closure_risk=LOW|HIGH`, the rebuttal path, and the final confidence state.

`LOW` admission is fail-closed and binary. In the existing decision record,
mark `PASS|FAIL|UNKNOWN` for actor/action, lawful pre-action information,
chronology, state/storage, productive work, physical bytes, latency/cost,
recipients, and estimand. A mechanism-falsifier basis must also mark the
preregistered action table, stopping rule, practical-effect threshold, and
interpretation boundary. Every applicable field must be `PASS`; any `FAIL`
disqualifies that closure basis and any `UNKNOWN` forces `HIGH`. A “single
witness” must itself establish the full mapping; composing papers, partial
mappings, or unstated assumptions is never `LOW`.

Reuse the decision record and existing Audit/Controller roles. Do not create a
closure schema, sidecar family, Pro sink, polling lifecycle, or permanent new
review role.

| proposed closure basis or impact | risk | required rebuttal before durable close | allowed final state |
|---|---|---|---|
| one single formal or executable witness completely preserves actor decision, information, chronology, state, work/cost, recipients, and estimand | `LOW` | independent Audit verifies the complete witness and scope | `CONFIDENT_LOCAL` |
| a prospectively frozen, adequately powered mechanism falsifier or negative meets its declared action table | `LOW` | independent Audit verifies validity, power, action table, and scope | `CONFIDENT_LOCAL` |
| multi-paper composition, partial/generic neighbor interpretation, absence evidence, ambiguous algebra, disputed source mapping, or reviewer conflict | `HIGH` | one one-shot adversarial Pro review followed by local source verification and adjudication; if Pro is unavailable, one fresh independent local reviewer who did not produce the proposed closure | `CONFIDENT_ADVERSARIAL` only after rebuttal |
| the decision removes the last active `PROBE`, empties the funnel, closes a user-prioritized route, or could broaden beyond one fingerprint | `HIGH` override | the same adversarial review even when the underlying witness would otherwise be `LOW` | `CONFIDENT_ADVERSARIAL` only after rebuttal |

Until the required high-risk rebuttal finishes, use
`PROVISIONAL_CLOSE_PENDING_REBUTTAL` or `HOLD_INFORMATION`, not `DROP` or
`CLOSE`. If neither real Pro nor a fresh independent reviewer is available,
preserve that provisional state; unavailability is not closure evidence.

The adversarial Pro request is standardized and bounded. Freeze the local
closure packet first; submit once in the configured project, read once, and do
not follow up. Ask for (1) the strongest concrete counterexample, (2) the exact
preservation field most likely to fail, (3) the narrowest justified scope and
reopening fact, and (4) exactly one advisory disposition from
`CONFIRM_SCOPED_CLOSE | NARROW_CLOSE | REOPEN_R0 | HOLD_INFORMATION`. Verify
every decision-critical citation or formal claim locally. Record only
`pro_trigger`, `pro_disposition`, `decision_effect`, and final confidence in
the same decision record. Pro is a rebuttal generator, never closure authority.

Do not invoke this gate for `ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`,
carrier/access failure, source unavailability, search-budget exhaustion,
no-selection, or incomplete neighbor work. These are engineering, process, or
information states and cannot scientifically retire a hypothesis. Low-risk
closures do not require a blocking Pro call; optionally sample them together
in one 3--5 milestone Pro review to detect systematic over-closure without
adding per-route latency.

A weak or null initial tranche satisfies item 3 only when the prospectively
declared futility analysis had adequate power at that tranche. Otherwise the
route remains `HOLD_INFORMATION` pending the frozen next tranche or a new
reopening fact.

“A related method exists” establishes a nearest neighbor, not closure. A simple method solving the frozen problem is scientifically informative and may close only the need for a more complex method under that contract. Record assumptions, scope, confidence, and explicit reopening conditions for every negative decision.

A source-grounded controlled carrier may support scoped problem existence.
Natural occurrence is a pre-Scout requirement only when the claimed actor,
resource constraint, event timing, or information asymmetry would otherwise be
manufactured. External validity belongs to Contribution or Confirmatory in
other cases.

Use `challenged`, `hold`, or `inconclusive` when evidence is incomplete. Route substantive criticism through rebuttal and adjudication before rejection.

Evidence from heterogeneous carriers may support a pragmatic project-route
archive, but it is not a replicated family-level negative unless the carriers
share the target estimand, protocol, sampling unit, uncertainty model, and
strongest baseline. Report individual scientific labels and the project action
separately.

Do not synthesize multiple scoped negatives into a benchmark, certificate, or
field-level claim merely because they share a topic. Require one common causal
mechanism, compatible estimands and baselines, purposeful carrier coverage, and
a fresh falsifiable synthesis estimand; then open a new charter for that pivot.

## Review and adjudication

- Use reviewers to generate falsification attempts, missing controls, alternative explanations, citation challenges, and reproducibility checks.
- For Confirmatory or publication-claim review, dispatch a fresh path-only
  Audit with the frozen claim boundary, exact paper/claim text path, raw
  result/config paths, hashes, and checklist. Exclude Executor summaries,
  persuasive review narratives, prior Pro verdicts, prior claim
  interpretations, raw conversations, and contribution forecasts. The Audit
  rebinds every input hash before semantic review.
- Before evidence, ask each external reviewer to resolve one named uncertainty
  rather than generate an unrestricted candidate tree. Reviewer-proposed
  pivots return to the active Program budget and do not authorize execution.
- Keep worker and adjudicator roles independent where practical; model-persona diversity alone does not establish independence.
- Label a same-model clean-session review as procedural red-team evidence, not external replication or independent scientific confirmation.
- Do not calibrate an LLM-generated numeric score to conference acceptance unless validated against a held-out external benchmark.
- Treat criticism as `challenged`, not automatic `rejected` or `no-go`.
- Permit a structured rebuttal, then adjudicate evidence and unresolved issues.
- Require accepted claims to cite verified evidence and an explicit decision record.
- Distinguish controller routing from claim acceptance. A controller may record
  `probe`, `hold`, `drop`, promotion, or scoped closure, but a Confirmatory or
  publication-facing `accepted` claim requires an independent adjudicator who
  did not produce the decisive evidence.

## Reporting

Lead with question, evidence, conclusion, and next step. Include:

- exact scope and protocol;
- code, config, data, environment, and seed provenance;
- central estimates and uncertainty;
- negative results and anomalies;
- facts, inferences, and hypotheses separated;
- limitations and untested generalizations;
- reproduction and validation commands.

Page count, reference count, figure count, iteration count, and self-review score are production metrics only. Never use them as scientific quality gates.
