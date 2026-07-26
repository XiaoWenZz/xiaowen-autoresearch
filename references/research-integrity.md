# Research integrity rules

Use this reference before literature synthesis, experiment design, statistical interpretation, claim drafting, review, or adjudication.

## Contents

1. Claim discipline
2. Outcome conditioning and venue labels
3. Specificity claims
4. Pre-registration
5. Proxy estimands and gate calibration
6. Statistics
7. Baselines and controls
8. Literature and citations
9. Evidence and negative results
10. Scientific progress versus activity
11. Scoped closure and NO-GO
12. Review and adjudication
13. Reporting

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
4. sample size or compute budget rationale;
5. exclusions, data cleaning, and failure handling;
6. stopping rule and statistical analysis;
7. the claim the run can support or falsify.

If these change after results are visible, preserve the original plan, record the amendment, and label the new analysis exploratory. Never silently redefine success.

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

## Scoped closure and NO-GO

Do not infer “nothing is worth doing” from overlap, one failed implementation, or one static carrier. Close only the narrowest estimand justified by one of:

1. a formal or empirically verified reduction that preserves the estimand,
   information access, cost accounting, temporal dynamics, and deployment
   constraints, and whose composed operations are jointly feasible for the same
   actor under one timing/state/communication contract;
2. a replicated high-confidence negative on an adequate carrier against the strongest relevant baseline;
3. failure of a preregistered minimum practical-effect threshold.

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
