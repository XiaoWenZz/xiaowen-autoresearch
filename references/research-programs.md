# Research programs, epochs, and circuit breakers

Use this reference when research direction search spans multiple portfolio
versions, candidate pivots, repositories, Scouts, or external reviews. Its
purpose is to bound aggregate search effort; it must not create another
experiment state machine.

## Contents

1. Hierarchy
2. Program and epoch budgets
3. Decision cadence and attention budget
4. Action admission and dependency gates
5. Mechanism fingerprint
6. New-epoch test
7. Paper-path stress test
8. Search-admission calibration
9. Post-signal evidence priority gate
10. Circuit breakers
11. External review
12. Positive-signal attribution gate
13. Scientific-yield audit
14. Progress dashboard
15. Minimal program record

## Hierarchy

Use:

```text
Research Program
  -> Research Epoch
     -> one Opportunity ledger
        -> at most one Problem Scout
           -> Contribution Gate
              -> Confirmatory
```

A **Program** is one resource-bounded attempt to obtain decision-changing
evidence within an agenda. An **Epoch** is one causal question with a fixed
target-estimand family, bottleneck, information contract, and terminal
condition. Do not force a broad field agenda into one narrow Epoch.

Keep one active evidence-collecting Program and one active
evidence-collecting Epoch per umbrella objective or shared decision budget by
default. Independently chartered unrelated Programs may coexist when their
authorization and resource budgets do not overlap. Portfolio filenames,
revisions, rebuttals, candidate names, new sessions, and new repositories do
not replenish Program or Epoch budgets.

For Scout Lite, a compact planning record containing `program_id`, `epoch_id`,
budgets, fingerprints, and decisions is sufficient. Do not initialize managed
state solely to represent this hierarchy.

## Program and epoch budgets

Freeze cumulative budgets before evidence. Defaults:

| Scope | Default cumulative limit |
|---|---:|
| active evidence-collecting Programs | 1 |
| active evidence-collecting Epochs in a Program | 1 |
| Epochs opened by one narrow Program | 2 |
| problem-existence Scouts per causal link | 2 |
| mechanism-map refreshes in one Epoch | 1 |
| opportunity briefs in one Epoch, including dropped/renamed briefs | 6 |
| pre-evidence external reviews in one Program | 2 |
| new experiment repositories in one Program | 2 |

A prospectively justified Program may use different limits when the task
genuinely requires purposeful replications or heterogeneous mechanisms. Freeze
the reason and cap before results; never expand them because prior outcomes
were negative. Closing an Epoch does not replenish Program budget.

Two related Scouts failing the same causal link normally close that route.
Two unrelated mechanisms failing consume the Program resource budget but do
not establish a scientific Program-level NO-GO. If a broad Program exhausts
its frozen resources without selection, report:

```text
SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION
```

Use `NO_OPPORTUNITY_UNDER_<BOUNDARY>` only for a narrow, explicitly enumerated
problem family. A new date, version, name, carrier, or taxonomy is not a
boundary change.

Start a search clock at Epoch freeze. Freeze the portfolio decision deadline
and planning/review cap; by default, planning consumes no more than 25% of the
Program's total wall-time or review-attention budget before producing
`probe`, `hold`, or a search terminal. Exceeding the clock does not authorize a
weaker witness: resolve one named source uncertainty, close a narrow
opportunity family, or report search-budget exhaustion.

## Decision cadence and attention budget

Treat human/LLM planning, review, coding, monitoring, and context reconstruction
as active research attention, separate from queued or unattended runtime.
Freeze an attention cap using the most reliable available unit: active hours,
material work blocks, external-review calls, or tokens when the runtime exposes
them. Do not invent token precision when it is unavailable.

Unless prospectively changed, write one compact decision capsule after four
hours of active attention or 24 hours of wall time, whichever comes first:

```text
current problem and candidate:
new verified fact or falsified hypothesis:
candidate, gate, or claim-boundary change:
binding uncertainty:
cumulative attention and compute:
next decision-changing action:
```

Append it to the existing Program/portfolio ledger; do not create another
report, state tree, or approval. A checkpoint never requires a favorable
result. If no candidate disposition, causal uncertainty, gate, claim boundary,
or next action changed, stop adding reviews, infrastructure, and experiments.
Choose the smallest direct witness, run a source/algebraic reduction, or close
the route.

## Action admission and dependency gates

Apply this test before an action expected to take more than about 15 minutes,
create another decision-critical artifact, request external review, or spend
compute:

```text
decision that could change:
uncertainty being retired:
smallest sufficient output:
cheaper source/code/algebra/cached check considered:
cheapest competing action and why this action is not dominated:
upstream gate already satisfied:
attention/compute cap:
discard or stop condition:
```

Record it as one row in the living Program or portfolio ledger. Do not create a
new charter, approval, readiness record, or verifier merely to document the
test. If no feasible output changes a named decision, do not perform the
action. Permission, idle GPU time, a waiting job, an available reviewer, or a
desire to “keep progressing” does not by itself establish scientific value.

Treat the research path as a dependency graph:

```text
problem existence -> mechanism necessity -> method kernel -> confirmation
```

An upstream result authorizes only the next unresolved node. While a parent
gate is pending, parallel work must remain useful under its positive, negative,
and ambiguous outcomes. Source verification needed in every branch, exact-path
smokes, and reusable data-integrity checks may qualify. Building the proposed
method, full baseline matrix, next-stage verifier, paper narrative, or another
candidate portfolio usually does not.

Scale proof burden with claim maturity. Search freezes the decision boundary
and source/algebraic audit. Scout Lite freezes scientific decision invariants
and records operational identity at launch. Confirmatory work adds full
preregistration, evidence-to-claim mapping, and independent adjudication. Do
not import Confirmatory trust machinery backward merely because it is already
available.

## Post-signal evidence priority gate

Trigger this gate when a Problem Scout produces its first material signal.
Before any further contract, authorization, journal, validator, infrastructure,
or procedural-review task, append this capsule to the existing living ledger:

```text
next scientific decision:
direct evidence that would decide it:
named validity blocker:
how the blocker could invalidate that evidence:
one repair cap:
one binary recheck:
fallback executable claim or artifact:
remaining attention and governance 20% cap:
```

Treat work as **governance-only** when it adds no target, mechanism, source,
code, algebraic, or outcome evidence that can change the next scientific
decision. Tests, commits, schemas, authorization layers, journals, validators,
review packets, and recovery packaging are governance-only unless they close
the single named blocker preventing that direct evidence.

Apply these defaults until the next decision-changing scientific observation:

1. permit one bounded patch and one recheck restricted to the predeclared
   executable witnesses;
2. spend no more than 20% of the remaining active-attention budget on
   governance-only work;
3. do not let a recheck expand into open-ended red teaming; record a newly
   discovered blocker as a challenge rather than automatically opening another
   repair;
4. if the new blocker would invalidate the next observation after the repair
   allowance is consumed, emit
   `GOVERNANCE_BUDGET_EXCEEDED_POST_SIGNAL` and choose
   `DOWNGRADE_CLAIM_TO_EXECUTABLE_BOUNDARY` or `HOLD_VALIDITY`;
5. do not create another version, schema family, verifier family, trust layer,
   or review round to escape this terminal.

Preserve the material Scout signal when this gate trips. It blocks only the
unsupported promotion or execution path. A cheaper direct source, code, or
algebraic discriminator remains admissible when it changes the scientific
decision without depending on the invalid machinery.

## Mechanism fingerprint

Each opportunity brief must record:

```text
problem object:
causal bottleneck:
provisional intervention or witness:
target estimand:
information contract:
strongest preserving reduction:
distinct falsifiable prediction:
```

Maintain a closure ledger of prior fingerprints and the assumption each result
falsified. Before a probe, state why the new actor-level prediction is not
already closed.

Treat opportunities as the same latent route when the target estimand and causal
bottleneck remain unchanged and the intervention differs only by
representation, carrier, selector, rank, seed, checkpoint, horizon, or
component partition. They consume the same Epoch budget.

Count an opportunity once it has an actor-level thesis and distinct prediction.
Immediate drop still consumes search budget; renaming or temporarily marking it
inactive does not remove that cost.

## New-epoch test

Open a new Epoch only when at least one item changes substantively:

- target estimand;
- causal bottleneck with a distinct prospective prediction;
- information or deployment constraint.

Changing intended artifact after a Problem Scout is a Contribution-Gate
reframe, not automatically a new Epoch. Open a new evidence charter before
collecting artifact-specific evidence; prior evidence remains Scout evidence
and does not become confirmation.

## Paper-path stress test

For a publication-targeted candidate, test at the Contribution Gate whether
the observed Scout signal can support a credible paper path. Write at most one
page containing:

1. contribution sentence;
2. main theorem or mechanism claim;
3. decisive figure or table unlocked by the Scout;
4. strongest baseline and reviewer objection;
5. at least two feasible Confirmatory settings;
6. disposition if the Scout is negative.

Exclude or hold the publication artifact if novelty, importance, evidence
scalability, or a paper path remains structurally unresolved. Preserve the
Problem Scout outcome and consider a different artifact honestly. This is a
planning test, not publication evidence.

For a deadline-bound venue target, prospectively freeze a submission-facing
candidate-selection date, a confirmation-start date, and a final
claim-reduction date. Before the first date, optimize Opportunity Search for
cheap decision-complete problem evidence. After a material signal, require the
Contribution Gate to pass importance, surviving novelty residual,
irreducibility, mechanism identifiability, claimed specificity, evidence
scalability, and one reviewer-critical test before paper-scale implementation.
If the gate cannot be resolved before the confirmation-start date, pivot the
artifact or select another route; do not spend the remaining schedule on a
method whose novelty or mechanism residual is still unknown.

## Search-admission calibration

When Opportunity Search rules are new or materially changed, forward-test them
before relying on a broad search conclusion:

1. for a broad-domain gate, choose at least three retrospective positive
   directions and reconstruct only the information available before each first
   material signal;
2. choose at least three obvious duplicates, vacuous taxonomy cells,
   no-decision leads, or exactly reduced negatives;
3. require the gate to admit every positive to a cheap Problem Scout and keep
   every negative out of `PROBE`;
4. record which field caused any error.

If the positive is rejected only because publication-stage novelty,
specificity, scalability, or venue facts were unavailable, revise the
Opportunity gate. This calibration evaluates the search process; it never
changes scientific thresholds or promotes the historical case.

## Circuit breakers

Pause the Program or Epoch when any condition holds:

1. two related Scouts fail the same causal link; close that route;
2. the frozen resource/attention budget is exhausted; report operational
   search exhaustion unless the boundary is narrow enough for scientific
   closure;
3. a new portfolio filename or version is used without a substantive Epoch
   change;
4. planning/review artifacts outnumber decision-changing evidence artifacts
   by more than 3:1;
5. the next action changes only carrier, seed, rank, checkpoint, horizon,
   component identity, selector, or threshold;
6. governance or implementation grows while the target estimand remains
   unobserved;
7. the initial opportunity map and its one refresh return no probe; report
   search exhaustion or a narrow-boundary no-opportunity result;
8. the frozen search clock expires without a complete portfolio disposition;
9. two contribution briefs fail the same specificity deletion or preserving
   reduction while proposing no distinct causal prediction; do not apply this
   circuit breaker to distinct actor-level opportunity theses;
10. after a material signal, the single governance repair/recheck allowance or
    its 20% attention cap is exhausted before another decision-changing
    scientific observation.

After a circuit breaker, permit only a route closure/synthesis record,
knowledge handoff, `SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION`, a justified
narrow-boundary no-opportunity result, or a substantively new Program
proposal. Do not launch a new Scout from the pause itself.

For circuit breaker 10, preserve the observed signal and use the post-signal
terminal: downgrade the claim or artifact to its executable valid boundary, or
hold validity. Do not open another governance version. Direct source, code, or
algebraic evidence that does not depend on the blocked machinery may still
resolve the next scientific decision.

## External review

During Opportunity Search, an external review may generate bounded problem
theses inside the frozen user boundary, but each thesis must name an actor,
loss, estimand, evidence status, strongest reduction, and cheap witness. Do not
accept titles or method combinations as candidates.

After one opportunity is `probe`, use each Pro, LLM, or human pre-evidence
review to resolve one named uncertainty:

- direct-neighbor coverage;
- preserving reduction;
- theorem validity;
- carrier identifiability;
- reviewer-critical experiment.

Do not request unrestricted idea generation after a Scout is selected. A
review may defend, exclude, revise, or hold a candidate; it cannot authorize a
repository, Scout, or budget reset. Any proposed pivot returns to the living
Program ledger unless it passes the new-Program test.

## Positive-signal attribution gate

Before a positive Scout unlocks another carrier, a named method, a full
baseline matrix, or Confirmatory work:

1. verify that the realized carrier statistic required by the claimed
   mechanism is materially present above uncertainty;
2. decompose the observed effect into the claimed causal term and the strongest
   local-only, no-op, static, matched-state, generic-operator, or other
   mechanism-deletion alternative;
3. verify that information access, trainable state, local work, communication,
   and deployment state are matched or explicitly charged;
4. require the incremental contribution contrast—not only improvement over a
   known-broken baseline—to pass the frozen practical-effect gate.

Use frozen outputs and algebra first. A surprisingly large effect is a reason
to check mismatches and degeneracies, not to relax the gate or scale the
experiment. If a previously unknown reduction is discovered after observation,
preserve the original outcome and label it `repair-only signal` or
`attribution unresolved`; do not retroactively rewrite thresholds. Permit at
most one prospectively frozen discriminator when it can change the route.
Only an attributed signal may promote, subject to every other frozen conjunct.

## Scientific-yield audit

At each Scout close and Program pause, report:

```text
raw leads generated:
grounded opportunity briefs:
problem-admission probes:
protected estimands observed:
material problem signals:
signals attributed to the claimed mechanism:
contribution artifacts selected:
uncertainty retired:
next scientific decision changed: yes/no
time to first estimand:
empirical compute used:
engineering retries:
decision-critical artifacts:
planning/review/governance share:
external-review calls or material attention spent:
positive-signal attribution: attributed / repair-only / unresolved / not applicable
```

Use this funnel—not Program numbers, filenames, sessions, or repository count—to
estimate research recall and conversion. A high raw-lead count with few
grounded briefs diagnoses ideation/grounding quality. Many grounded briefs with
almost no probes diagnoses an over-strict admission gate. Many probes with no
estimands diagnoses carrier or engineering design. Material signals with no
attributed contribution diagnose mechanism quality or a too-late Contribution
Gate. These failure modes require different repairs.

Use these only to improve process, never to select scientific outcomes. A low
yield means the work produced metrics or artifacts without changing the
candidate, gate, claim boundary, or next action. In that case:

1. remove non-decision-critical governance and duplicated reviews;
2. replace the next experiment with a source/algebraic check or a more direct
   estimand when possible;
3. if the same intervention and gate would remain, do not repeat the experiment
   shape;
4. return to the unresolved causal-quantity map rather than changing only the
   carrier, name, rank, seed, checkpoint, or selector.
5. mark any downstream artifact created before its parent gate inactive and
   count the effort as process waste; preserve only necessary provenance and
   do not use sunk cost as a reason to continue.

Fast source-level falsification is high yield even when it excludes a
candidate. Large metric tables are low yield when every outcome leaves the
decision unchanged.

## Progress dashboard

Lead research status with:

| Dimension | Values |
|---|---|
| problem admission | PROBE / HOLD_INFORMATION / HOLD_CARRIER / DROP_PROBLEM_EXACT_REDUCTION / DROP_NO_DECISION / ROUTE_BROADER_ARTIFACT / budget-exhausted |
| contribution forecast | unassessed-pre-signal / challenged-neighbor / likely-repair / likely-generic / plausible-if-signal |
| problem grounding | hypothesized / source-supported / analytical / observed |
| problem existence | untested / absent / material |
| novelty residual | unverified / closed / surviving |
| mechanism | hypothesis / falsified / Scout signal |
| contribution artifact | unselected / method / audit / systems / theory / negative |
| paper path | not-applicable / absent / challenged / feasible |
| Program / Epoch | active / paused / closed |
| next decision | one exact uncertainty |

Report commits, files, branches, jobs, GPU utilization, document volume, and
verifier surface only as secondary operational diagnostics. They are not
scientific-progress metrics.

## Minimal program record

Record:

```text
program_id:
program_objective:
program_budget:
program_budget_remaining:
epoch_id:
epoch_question:
epoch_fingerprint:
governance_track: scout | confirmatory
operating_weight: lite | managed | full
governance_admission_proof:
portfolio_ledger:
selected_scout_or_search_terminal:
circuit_breaker_status:
worker_registry: NONE | <path-or-inline-records>
next_decision:
```

Use one living planning record with timestamped amendments. Freeze evidentiary
contracts and outcomes separately; never rewrite them to simplify the Program
ledger. When a persistent work session exists, its registry must preserve
`worker_id`, thread/session ID, Program/Epoch, contract revision, callback
state, terminal-event idempotency key, reclaim deadline, watchdog identity and
state, and artifact paths. Scout Lite with no persistent worker may use
`worker_registry: NONE`.
