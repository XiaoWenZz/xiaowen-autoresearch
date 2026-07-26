# External Opportunity Search prompt

`OPPORTUNITY_SEARCH_SCHEMA: high-recall-v2`

You are an expert research PI. Conduct a fresh, high-recall but
evidence-bounded Opportunity Search for `{{DOMAIN}}`.

Evidence freeze: `{{EVIDENCE_FREEZE_DATE}}`

Target artifact and venue window: `{{TARGET_ARTIFACT_AND_VENUE}}`

This request authorizes research search and one proposed Problem Scout only. It
does not authorize code, repository creation, data access, compute, public-test
use, or a publication claim.

## 1. Scope

Allowed scope:

{{ALLOWED_SCOPE}}

Hard exclusions:

{{HARD_EXCLUSIONS}}

Implementation freedom and resource boundary:

{{IMPLEMENTATION_AND_RESOURCE_BOUNDARY}}

## 2. Scientific stage

Keep these stages distinct:

```text
Opportunity Search -> Problem Scout -> Contribution Gate -> Confirmatory
```

This prompt requests Opportunity Search. Do not require publication-grade
novelty, irreducibility, natural external validity, narrow domain specificity,
scalability, official executable code, or a completed paper path before
admitting a cheap interpretable problem witness. Record them only in
`contribution_forecast`.

Never use `contribution_forecast` to determine `problem_admission`.
Official executable code is not required for Opportunity admission.

## 3. Current domain profile

Authoritative profile or ledger:

{{DOMAIN_PROFILE_AND_LEDGER}}

Current problem-space map and primary-source neighborhood:

{{PROBLEM_SPACE_AND_NEIGHBORS}}

## 4. Scoped closures

Treat every entry below as an exact fingerprint closure, not a keyword or
field-level NO-GO.

{{SCOPED_CLOSURES_WITH_REOPENING_CONDITIONS}}

Reject a candidate only when it revives the same target estimand and causal
bottleneck with changes limited to carrier, seed, rank, checkpoint, horizon,
selector, representation, or name. A candidate may remain distinct by changing
the actor-level decision, target estimand, causal bottleneck, information
contract, or deployment constraint with a new falsifiable prediction.

## 5. Source contract

{{PRIMARY_SOURCE_CONTRACT}}

Label substantive statements as `FACT`, `INFERENCE`, or `HYPOTHESIS`, in that
order when summarizing a brief. If only metadata, an abstract, or a secondary
report is available, mark the internal operation unverified. “No exact
duplicate found” is corpus-scoped, not an absence proof.

## 6. Admission calibration

Before searching, reconstruct at least three retrospective positives using only
their pre-signal information and at least three negative controls: exact
duplicates, vacuous taxonomy cells, no-decision leads, or exact reductions.

Every positive must receive `problem_admission: PROBE`; every negative must stay
out of `PROBE`. Report false rejects and false admits. If a positive is rejected
because novelty, naturality, specificity, scalability, or paper path is
unknown, revise the gate before relying on the search terminal.

## 7. Divergent pass

Generate at least `{{RAW_LEAD_MINIMUM}}` raw leads across at least
`{{PROBLEM_SPACE_MINIMUM}}` substantively different problem spaces.

For each raw lead state only:

1. actor and decision;
2. suspected material loss;
3. causal transition;
4. one falsifiable prediction.

Do not assign novelty, venue, reviewer, `PROBE`, `HOLD`, or `DROP` labels during
this pass. Do not require a natural carrier, complete preserving composition,
method kernel, specificity proof, or paper path. Preserve broader artifact
routes instead of killing them for failing narrow specificity.

## 8. Convergent pass and counted briefs

Ground the raw leads in primary sources and collapse them by causal fingerprint
into at most `{{COUNTED_BRIEF_CAP}}` counted briefs. Keep at most three active
briefs and select at most one Problem Scout.

Each counted brief must contain:

1. actor, decision, material loss, and evidence status;
2. target estimand and justified minimum practical effect;
3. causal bottleneck and necessary mechanism-support condition;
4. information, cost, temporal, and deployment constraints;
5. nearest primary-source neighbor;
6. strongest preserving reduction at the actor-problem level;
7. adequate controlled or natural carrier;
8. cheapest decision-complete witness;
9. positive, negative, and ambiguous actions;
10. causal fingerprint and prior-closure check;
11. separate statuses:

```text
problem_admission:
  PROBE | HOLD_INFORMATION | HOLD_CARRIER | DROP_PROBLEM_EXACT_REDUCTION |
  DROP_NO_DECISION | ROUTE_BROADER_ARTIFACT
contribution_forecast:
  UNASSESSED_PRE_SIGNAL | CHALLENGED_NEIGHBOR | LIKELY_REPAIR |
  LIKELY_GENERIC | PLAUSIBLE_IF_SIGNAL
```

Additional domain-specific required fields:

{{DOMAIN_SPECIFIC_BRIEF_FIELDS}}

A source-grounded controlled carrier is adequate for scoped problem existence.
A natural carrier is a pre-Scout hard requirement only when natural occurrence
constitutes the actor, event timing, resource constraint, or information
asymmetry. Otherwise move naturality and external validity to Contribution or
Confirmatory.

## 9. Joint-feasibility certificate

Before a composition of papers or operations can assign
`DROP_PROBLEM_EXACT_REDUCTION`, certify all of:

| Field | Question |
|---|---|
| observables | Are all inputs available to the actor before the decision? |
| ordering | Can the operations run in the claimed temporal order? |
| rendezvous | Are extra client/server availability windows allowed and charged? |
| state/storage | Can required checkpoints, heads, logs, versions and optimizer state coexist? |
| objective/architecture | Are losses, adapters, tokenizers and backbones compatible? |
| total cost | Are discovery, bytes, latency, compute, calibration, replay and rollback matched? |
| deployment | Does the composition preserve the same recipient and utility? |
| witness | Is compatibility shown by a primary implementation, formal construction, or source-faithful microcase? |

If any decision-critical field is unverified, return
`CHALLENGE_UNVERIFIED_JOINT_FEASIBILITY`. The composition may be a mandatory
Scout baseline, but it cannot close the actor-level problem before measurement.

## 10. Selection

Compare the Top 3 on problem importance, plausibility, identifiability,
joint-feasibility risk, Scout cost, and decision value before
`{{DEADLINE}}`. Keep novelty and paper viability only in the separate
contribution forecast.

Select at most one `ADMIT_TO_PROBLEM_SCOUT` candidate. It needs:

1. one-sentence problem thesis;
2. formal actor, state, observables, decision, estimand, and budget;
3. strongest jointly feasible preserving baseline;
4. a 1--3 day controlled or natural witness with matched budgets, primary
   actor metric, minimum practical effect, uncertainty rule, positive/null
   controls, mechanism deletion, and exact positive/negative/ambiguous actions;
5. one conditional contribution challenge to revisit only after a material
   Scout signal.

Do not require a provisional method implementation, full novelty matrix,
multi-setting confirmation, or conference paper path in this response.

## 11. Terminal semantics

If one opportunity is worth measuring, return:

```text
PROBE_WORTHY_METHOD_OPPORTUNITY_FOUND
ADMIT_TO_PROBLEM_SCOUT
```

If the bounded search returns no probe, return:

```text
SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION
```

The second state is an operational search terminal, not a field-level NO-GO or
proof that `{{DOMAIN}}` has no strong ideas.

## 12. Required output order

{{REQUIRED_OUTPUT_ORDER}}

Finish with a primary-source bibliography that states the role of every source
in the argument. Do not choose a method name first and then invent a problem.
