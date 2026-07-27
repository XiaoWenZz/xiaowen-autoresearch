# Temporal backtesting for research gates

Use this reference to evaluate whether Opportunity Search admits historically
valuable ideas without importing publication outcomes into the gate decision.
This is process calibration, not evidence that venue decisions equal truth.

## Questions

Measure three different properties:

1. **strict probe recall**: how many accepted positive papers would have reached
   a cheap Problem Scout;
2. **retained recall**: how many positives were either probed or preserved as a
   bounded evidence-gap/broader-artifact lead rather than hard-dropped;
3. **contribution discrimination**: whether the frozen contribution forecast
   has any ordinal association with later venue or presentation tier.

Do not call nomination yield “recall” unless the positive set and denominator
are explicit. Do not estimate precision from accepted papers alone.

## Time-slice protocol

1. Freeze the gate version, sample rule, domain boundary, paper count, venue
   set, positive/negative definitions, and analysis before selecting examples.
2. Use a stratified positive cohort from official 2026 archival proceedings,
   covering at least three venues and, when available, oral/spotlight/poster or
   equivalent presentation tiers. Prefer 12 positives for a first pass.
3. Add a separately reported negative-control cohort before claiming
   precision: verifiably rejected public submissions, workshop-only papers, or
   exact duplicates/reductions from the same period and domain. Match topic and
   evidence availability where practical.
4. For each paper, define `neighbor_cutoff` as no later than that paper's
   official publication date. Exclude later papers, later code fixes, later
   citations, later rebuttals, and later community summaries from the gate
   decision. Record ambiguous online-first dates explicitly.
5. The evaluator may read the target paper and contemporaneous code because the
   question is whether its idea would pass the gate. It must freeze
   `problem_admission`, `retention_state`, `contribution_forecast`, strongest
   neighbor/reduction, and rationale before opening the outcome labels.
6. Keep actual venue, acceptance status, presentation tier, awards, citations,
   and later impact in a separate label artifact. Open it only after every gate
   decision is hashed or otherwise frozen.
7. Verify decision-critical neighbors against primary papers or official code.
   Search by operation as well as method name. A neighbor published after the
   cutoff is recorded only as a post-hoc limitation.

## Required decision record

For each paper record:

```text
paper_id and contemporaneous source identity:
neighbor_cutoff:
actor / decision / target loss:
problem thesis and evidence status:
strongest exact neighbor:
strongest partial-operation neighbor:
strongest generic preserving reduction:
cheapest problem witness available at cutoff:
problem_admission:
retention_state:
contribution_forecast:
decision rationale:
decision_frozen_at and artifact hash:
label_opened_at:
actual venue / acceptance / presentation tier:
error class after label opening:
```

Use these error classes:

- `CORRECT_PROBE`;
- `PROBE_MISS_RETAINED`;
- `HARD_FALSE_REJECT`;
- `CORRECT_NEGATIVE_EXCLUSION`;
- `FALSE_ADMIT`;
- `OVER_RETAINED_NEGATIVE`;
- `LABEL_NOT_COMPARABLE`.

## Metrics and interpretation

Report:

```text
strict_probe_recall = positive PROBE_READY / comparable positives
retained_recall = positive non-CLOSED / comparable positives
hard_false_reject_rate = positive CLOSED / comparable positives
false_admit_rate = negative PROBE_READY / comparable negatives
over_retention_rate = negative retained non-PROBE / comparable negatives
```

Compare contribution forecasts with venue/presentation tiers only as an
exploratory ordinal table. Do not turn oral/spotlight/poster into a scientific
quality ground truth or fit an acceptance-probability score from a small,
selected sample. Report disagreements paper by paper and identify which gate
field caused them.

## Decision rule

- Any `HARD_FALSE_REJECT` caused only by missing publication-stage novelty,
  narrow specificity, natural external validity, scalability, or paper path
  requires an Opportunity-gate repair.
- Repeated `PROBE_MISS_RETAINED` cases call for reducing pre-Scout proof burden
  or improving the cheapest-witness rule; they do not justify automatic GPU
  admission.
- Any `FALSE_ADMIT` caused by an exact jointly feasible problem-level reduction
  requires strengthening the drop rule.
- High retained recall with low strict probe recall means the search is finding
  ideas but failing to convert evidence gaps into cheap witnesses.
- Calibration changes process rules only. They never retroactively validate a
  historical paper, accept novelty, or authorize compute.
