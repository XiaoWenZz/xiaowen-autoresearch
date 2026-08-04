# Opportunity portfolio, contribution selection, and negative synthesis

Use this reference when several research opportunities compete for a bounded
problem-existence budget, after a signal must be mapped to an honest
contribution, or when multiple scoped negatives might support a higher-level
artifact.

Read [problem-space.md](problem-space.md) first. Keep two decisions separate:

1. **Opportunity Search** asks whether a problem is worth measuring.
2. **Contribution Selection** asks, after a material signal, whether a method
   or other artifact is novel, irreducible, scalable, and worth confirming.

Do not import the second decision's proof burden into the first.

## Contents

1. Optional repeated-Program boundary
2. Divergent and convergent passes
3. Opportunity brief and admission
4. Joint-feasibility certificate
5. Contribution brief and exclusions
6. Venue-viability screen
7. Selection and calibration
8. Negative synthesis gate
9. Minimal selection record

## Optional repeated-Program boundary

Opportunity Search is pre-charter planning that selects which bounded Problem
Scout is worth opening. Contribution Selection happens only after a material
signal, except when the artifact is itself a source/algebraic audit or theorem.
Neither stage is an acceptance forecast.

- When an existing repeated Program already governs the search, apply its
  hierarchy/circuit breakers and freeze its IDs and remaining budget. Otherwise
  keep `program_id=null` and `epoch_id=null` in one Lite task-bound decision
  record; Opportunity Search never creates a Program/Epoch merely to rank
  candidates.
- Freeze one umbrella objective and the scientific or operational constraints.
- Freeze a search boundary: candidate cap, primary-source scope, decision
  deadline, and maximum planning effort.
- Keep at most three active opportunity briefs and one evidence-collecting
  Problem Scout.
- Keep at most six opportunity briefs cumulatively across the initial map and
  sole refresh by default. A brief counts when it has an actor-level thesis and
  distinct prediction, even if immediately dropped or renamed.
- Maintain one living decision record with timestamped amendments. When an
  existing Program applies, a new filename, version, session, repository,
  carrier, or method label does not reset its budgets.
- Interpret “continue until good” as successive bounded decisions. A favorable
  sign is never a stopping rule. Budget exhaustion is operational state, not
  proof that a broad field has no viable opportunity.

## Divergent and convergent passes

Do not generate and kill ideas in one pass.

### Source observatory

For a broad or recency-sensitive search, run a source-first observatory before
the divergent pass:

- screen the current and previous 18 months of the relevant primary
  proceedings, recent forward neighbors, appendices, limitations, negative
  ablations, sensitivity results, and paper-declared official code;
- extract empirical anomalies, failed assumptions, unresolved tail behavior,
  missing controls, and expensive or unstable operations;
- target at least 20 primary papers for a day-scale FedFT/FedPEFT search unless
  a named source-access blocker makes that impossible; and
- keep one source/anomaly table. For each row, record a stable
  `source_family_id` and descriptive `assumption_lineage` for the actor,
  information, chronology, state, or deployment premise it inherits. Treat a
  paper, its appendix, declared official code, and maintainer-authored issue or
  PR as one source family. Do not create one governance packet per paper.

The observatory is a search-input refresh, not evidence that a paper's claimed
problem or method is correct. It prevents a stale atlas or bottom-up component
taxonomy from defining the full candidate universe.

Source-family and assumption-lineage fields are descriptive retrieval
telemetry. Record reused, correlated, and unknown ancestry rather than
manufacturing distinct labels. Paper or family counts cannot establish
conceptual diversity, independence, novelty, or problem admission, and no
numeric LLM or expert novelty score may replace the source/reduction checks.

### Divergent pass

- Generate up to 20 raw problem leads without `probe`, `hold`, `drop`, novelty, venue,
  or reviewer scores.
- Cover at least six substantively different problem spaces by default for a
  broad FedFT/FedPEFT batch.
- State only the actor, decision, suspected material loss, causal transition,
  and one falsifiable prediction. A raw lead may be broad or incomplete.
- Do not require a natural carrier, complete preserving composition, method
  kernel, specificity proof, or paper path during this pass.
- Preserve leads that broaden outside the requested subfield. Broadening is
  evidence about the artifact family, not proof that the underlying problem is
  absent.

### Convergent pass

- Ground the raw leads in sources, merge them by causal fingerprint, and create
  at most eight causal fingerprints and at most six one-screen opportunity
  briefs.
- Apply prior exact closures and actor-level reductions only now.
- Record problem admission and contribution forecast as independent fields:

```text
problem_admission:
  PROBE | HOLD_INFORMATION | HOLD_CARRIER | DROP_PROBLEM_EXACT_REDUCTION |
  DROP_NO_DECISION | ROUTE_BROADER_ARTIFACT
contribution_forecast:
  UNASSESSED_PRE_SIGNAL | CHALLENGED_NEIGHBOR | LIKELY_REPAIR |
  LIKELY_GENERIC | PLAUSIBLE_IF_SIGNAL
```

Also record one descriptive, non-binding `mechanism_depth` value:

```text
NEW_ACTOR_DECISION | NEW_INFORMATION_CHRONOLOGY_STATE |
NEW_CAUSAL_MECHANISM | OPERATION_RECOMBINATION
```

This field is retrieval and cross-merge telemetry, not a novelty claim, score,
admission gate, or contribution verdict.

The contribution forecast must not determine problem admission. An occupied
method kernel, failed narrow specificity, or missing paper path can challenge a
future method contribution while the actor-level problem remains worth a cheap
measurement.

Add one operational state without changing the scientific labels:

```text
retention_state:
  PROBE_READY | EVIDENCE_GAP_LEAD | BROADER_ARTIFACT_LEAD | CLOSED
```

Map `PROBE` to `PROBE_READY`, `HOLD_INFORMATION`/`HOLD_CARRIER` to
`EVIDENCE_GAP_LEAD`, `ROUTE_BROADER_ARTIFACT` to
`BROADER_ARTIFACT_LEAD`, and only the two `DROP_*` states to `CLOSED`.
This prevents a batch-level “no nominee” terminal from silently erasing a
problem that remains actionable but is not yet launch-ready.

## Opportunity brief and admission

Keep a pre-signal brief to one screen:

1. affected actor, decision, and observed/source-supported/analytical/
   hypothesized failure;
2. target estimand, current-practice baseline, and practical-effect floor;
3. deployment/information constraints and an adequate controlled or natural
   carrier/source;
4. strongest problem-level preserving reduction;
5. cheapest decision-complete witness and data/leakage boundary;
6. positive/negative/ambiguous actions, cost, and deadline;
7. causal fingerprint and prior-closure check;
8. separate `problem_admission` and `contribution_forecast`.
9. `retention_state` plus one bounded evidence-acquisition action or exact
   reopening fact for every retained lead.

Create no repository or remote job before one brief has
`problem_admission: PROBE`; a local one-screen ledger is sufficient.

An unverified neighbor blocks a novelty claim, not a problem measurement. Mark
the opportunity `HOLD_INFORMATION` or `HOLD_CARRIER` only when the missing
source, observable, or carrier could show that the actor-level problem itself
is solved or that every feasible witness is uninterpretable.

Keep `HOLD_INFORMATION` and `HOLD_CARRIER` in a retained evidence-gap backlog
when one bounded source, code, algebra, carrier-discovery, or controlled-witness
step could change admission. If no such step exists, record the precise
reopening fact and close only the active search transaction, not the lead.
Keep `ROUTE_BROADER_ARTIFACT` live when the broadened thesis remains inside the
owner's research boundary; narrow FedFT specificity cannot silently discard a
valid systems, optimization, benchmark, audit, or theory problem.

A source-grounded controlled carrier is adequate for a scoped
problem-existence Scout. Require a natural carrier before the Scout only when
the actor, resource constraint, event timing, or information asymmetry is
constituted by a naturally occurring trace and would be manufactured by the
control. Otherwise move naturality and external validity to Contribution or
Confirmatory.

Drop before a Problem Scout only when:

- a verified, jointly feasible reduction solves the actor-level problem under
  the same estimand, information, cost, dynamics, and deployment constraints;
- a prior closure already falsified the same distinct prediction and only the
  carrier, rank, seed, checkpoint, horizon, selector, or representation changed;
- the carrier cannot expose the problem or distinguish it from the strongest
  simple alternative;
- leakage, unavailable data, or infeasible compute makes the witness
  uninterpretable;
- source/code/algebra/cached evidence can already retire the uncertainty;
- both favorable and unfavorable outcomes merely trigger variants; or
- no feasible outcome changes a scientific or operational decision.

Do **not** drop solely because:

- novelty or a direct neighbor is unresolved;
- federation/PEFT/dynamic specificity broadens;
- a proposed method reduces to an existing operator while the actor-level
  problem remains;
- a paper path or multi-setting confirmation plan is not yet known; or
- the most honest artifact may be an audit, benchmark, systems result,
  certificate, reproduction, or scoped negative.

## Joint-feasibility certificate

A composition of operations from separate papers is not a preserving reduction
until one certificate shows that the same actor can execute the whole
composition under one contract. Before using a composition to assign
`DROP_PROBLEM_EXACT_REDUCTION`, record:

| Field | Required evidence |
|---|---|
| observables | every input is available to the actor before the decision |
| ordering | operations can run in the claimed temporal order |
| rendezvous | extra client/server availability is allowed and charged |
| state and storage | checkpoints, optimizer state, heads, logs and versions coexist |
| objective and architecture | losses, adapters, tokenizers and backbones are compatible |
| bytes, latency and compute | discovery, calibration, rollback and replay are matched or charged |
| deployment | the composed action preserves the same recipient and utility |
| implementation witness | a primary implementation, formal construction, or small source-faithful microcase demonstrates compatibility |

If any decision-critical field is unverified, label the composition
`CHALLENGE_UNVERIFIED_JOINT_FEASIBILITY`. It may shape the Scout baseline but
cannot close the actor-level problem before measurement. A standalone canary,
rollback, or oracle is not deployable unless its representative data, timing,
and cost are part of this certificate.

Do not satisfy this certificate by imagining a controller that can copy every
lawful observable. Require one implementation, formal construction, or
source-faithful executable microcase for the complete composition. Without
that witness, `copyable`, `centralizable`, `generic`, and failed
federation/PEFT specificity are contribution challenges rather than
problem-admission failures.

## Contribution brief and exclusions

After a material signal, add:

1. one contribution sentence and primary artifact;
2. verified neighbors and exact residual operation;
3. contribution contrast and mechanism-deletion control;
4. specificity at the level claimed;
5. evidence scalability, confirmation path, and strongest reviewer objection.

Now exclude a method/contribution when a preserving reduction removes its
residual operation, novelty is occupied, the signal is repair-only, the
mechanism is unidentifiable, or confirmation is infeasible. Preserve the
underlying Problem Scout outcome and consider another artifact honestly.

## Venue-viability screen

Apply this screen at the Contribution Gate after a material signal, or before
evidence only when the frozen objective is itself a source/theory artifact.
Do not use it to block an otherwise valid cheap Problem Scout.

Label each dimension `pass`, `challenge`, or `fail`; do not collapse the labels
into an uncalibrated numeric score.

- **Importance**: a material scientific or deployment problem exists beyond a
  small metric tweak.
- **Irreducibility**: the contribution survives the strongest generic or
  domain-adjacent reduction; otherwise reframe it at the broader level.
- **Novelty residual**: direct neighbors do not already answer the same
  estimand under the relevant constraints.
- **Mechanism identifiability**: a bounded observation can separate the claimed
  cause from the strongest alternative explanation.
- **Evidence scalability**: a passing Scout can be extended across adequate
  carriers, seeds, baselines, and uncertainty units.
- **Resource feasibility**: the confirmation path fits realistic data,
  engineering, compute, and evaluation access.
- **Reviewer resistance**: the strongest foreseeable objection has a fair,
  decision-changing test rather than a rhetorical answer.

Use “A-tier viable” only as an internal planning label. It means no known fatal
failure remains and the evidence path could support a substantial contribution;
it is not a claim about acceptance probability. Any `fail` on importance,
irreducibility, novelty residual, or mechanism identifiability blocks
publication/method selection, not preservation of the opportunity signal.
Every decision-critical `challenge` must name a bounded resolving observation;
select the route only when its first action resolves those challenges before
method implementation or expensive evidence collection.

## Selection and calibration

### Opportunity selection

1. Remove only `DROP_PROBLEM_EXACT_REDUCTION` and `DROP_NO_DECISION`
   opportunities. Route broader artifacts explicitly instead of calling them
   scientific negatives.
2. Cluster by causal fingerprint.
3. Prefer the cheapest decisive witness; break ties by problem magnitude and
   decision importance.
4. Select one `PROBE`; mark alternatives with one precise admission state.
   Preserve at most one oldest `EVIDENCE_GAP_LEAD` and one
   `BROADER_ARTIFACT_LEAD` with bounded next actions. They do not enter the GPU
   queue and do not count as selected Scouts.
5. Make the probe a problem-existence or mechanism-necessity witness on the
   smallest adequate carrier. Do not begin with a new method or publication
   matrix.
6. If the map and one refresh yield no probe, report
   `SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION`, unless a narrow frozen problem
   family justifies `NO_OPPORTUNITY_UNDER_<BOUNDARY>`.

### Contribution selection

1. Require a material Problem Scout signal.
2. Apply verified neighbors, reductions, venue viability, and confirmation
   feasibility.
3. Select one artifact with `selected`, `held`, or `excluded`.
4. Run the paper-path stress test only when publication is the objective.

### Admission-rule calibration

Before relying on a new or materially changed Opportunity Search gate, test:

- at least three retrospective positives for a broad domain gate, reconstructed
  at the information state available before their first signal; and
- at least three obvious duplicates, vacuous taxonomy cells, no-decision leads,
  or exactly reduced negatives.

The gate must admit every positive to a cheap probe and keep every negative out
of `PROBE`. In a two-tier replay, report both strict probe recall and retained
recall: a positive routed to `EVIDENCE_GAP_LEAD` is a probe miss but not a hard
false reject; a positive routed to `CLOSED` is a hard false reject. Report
false admits and over-retained negatives separately. If a positive closes only
because publication-stage novelty, natural external validity, specificity,
scalability, or paper path is unknown, revise the gate before using it. For
publication- and presentation-tier backtests, follow
[gate-backtesting.md](gate-backtesting.md).
Calibration is a rule-based replay, not evidence that the historical paper
would have succeeded prospectively.

## Negative synthesis gate

Trigger this audit after three related scoped closures by default, or earlier
when two routes expose the same concrete causal mechanism. Synthesis is eligible
only when all of the following hold:

- the closures concern the same target-estimand family;
- one explicit mechanism predicts every result, including any exceptions;
- protocols and strongest baselines are compatible, or a formal reduction
  preserves their differences;
- carrier diversity tests the shared mechanism rather than pooling unrelated
  failures;
- the proposed benchmark, audit, certificate, or scoped negative contribution
  has one new falsifiable estimand.

If any condition fails, keep the outcomes as separate route-level evidence. If
the synthesis gate fails, do not open a synthesis Scout: a shared evaluation
template, slogan, or post-hoc bridge experiment cannot manufacture a shared
mechanism or compatible estimand. Return any proposed audit, benchmark, or
certificate to the active Program ledger as a candidate alongside alternatives;
it does not receive fresh budget. If all conditions pass, treat synthesis as a
contribution pivot:
close the old route, open a new charter, freeze the shared estimand and strongest
counterexample, and run the cheapest fresh problem-existence Scout. Prior
negative runs motivate the pivot but are not independent confirmation of the
new claim.

## Minimal selection records

Opportunity table:

`opportunity | actor/loss | evidence status | source family/assumption lineage | estimand/MPE | constraints | strongest problem reduction | joint feasibility | carrier/source | witness/outcomes/cost | causal fingerprint | mechanism depth | problem admission | contribution forecast`

Contribution table after signal:

`artifact | signal | neighbor status | residual operation | contribution control | specificity | importance | irreducibility | novelty | identifiability | scalability | resources | reviewer test | selected/held/excluded`

Record Program/Epoch identity, resource budget, and why the chosen witness is
cheaper and more decisive than alternatives. Do not convert missing
publication-stage fields into a pre-signal `drop`.
