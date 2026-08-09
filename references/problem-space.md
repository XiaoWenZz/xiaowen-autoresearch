# Problem-space and specificity gate

Use this reference before generating method candidates, resetting a Program to
a new problem family, claiming that a contribution is federation-, PEFT-, or
dynamic-decision-specific, or deciding whether a proposed Scout is worth its
cost.

## Contents

1. Ground the problem
2. Apply specificity deletion tests
3. Search reductions before solutions
4. Apply the zero-compute falsification ladder
5. Separate repair from contribution
6. Apply proportional R0--R3 readiness
7. Qualify the carrier
8. Design a decision-complete witness
9. Minimal record

## Ground the problem

Write one problem thesis, not a list of methods:

```text
affected actor or population:
decision or operation:
observed failure and decision unit:
target estimand and minimum practical effect:
federation/deployment constraints:
strongest current simple practice:
cheapest controlled/formal or natural witness and naturality status:
evidence status and uncertainty:
claimed mechanism and necessary support statistic:
strongest mechanism-deletion control:
hard topic exclusions:
```

Before generating candidates, inventory the strongest existing evidence in the
workspace and primary artifacts: prior scoped closures, reopening conditions,
cached estimands, operative source/code definitions, and the closest verified
neighbor or preserving reduction. Distinguish reusable evidence from stale
queue state, implementation history, and unverified review prose. A new
session, repository, carrier, or method name does not reset this inventory.
Use the inventory to avoid rediscovering a closed prediction; do not turn it
into a second literature review or state tree.

Derive one ephemeral anti-repeat view for the current search: at most five
exact closed fingerprints, five active or `HOLD` uncertainties, three strongest
generic reductions, and the current scope. Do not persist it, build a graph,
create a capsule, or treat it as evidence.

Separate:

- **observed**: directly measured under the target or a justified preserving
  protocol;
- **analytically established**: a formal construction, counterexample, or
  theorem establishes the failure under explicit target-compatible
  assumptions;
- **source-supported**: a primary source establishes the failure under a
  materially compatible setting;
- **hypothesized**: plausible but not yet observed under the target contract.

Separate opportunity admission from method admission:

- an **Opportunity Search** may admit a hypothesized failure when the affected
  actor, loss, target estimand, practical-effect floor, candidate controlled or
  formal witness, and decision-changing action are concrete;
- a **method portfolio** requires an observed, analytically established, or
  source-supported material failure plus a residual method operation.

If the key failure is hypothesized, hold named-method generation and make the
next artifact a bounded problem-existence witness. Do not require complete
novelty, specificity, or a paper path merely to measure the problem. A
literature gap, taxonomy cell, heterogeneous dataset, selectable
parameterization, or varying score still does not by itself establish one.

For empirical claims, use an adequate carrier: it must expose the causal
bottleneck, contain the target sampling/decision unit, support the strongest
simple baseline, and admit a positive control. Do not interpret a negative
from a carrier known beforehand to suppress the mechanism, and do not use an
inadequate first carrier as permission for post-hoc carrier hopping.

## Apply specificity deletion tests

Record `survives`, `broadens`, or `fails` for each applicable test:

At Opportunity Search, these tests set `contribution_forecast`; they do not
close a concrete actor-level problem merely because federation, PEFT, or a
proposed method kernel can be deleted. A broadened problem remains eligible
for a cheap controlled witness when it is inside the owner's research
boundary. Use deletion as a pre-signal `DROP_PROBLEM_EXACT_REDUCTION` only when
the deletion also supplies a verified complete solution to the same actor
decision under the closure rule below.

1. **Federation deletion**: if centralized pooling or a single trainer replaces
   federation, does the same failure, operation, and estimand remain? If yes,
   identify the exact federation constraint that changes the solution;
   otherwise the contribution is generic optimization or systems work. For a
   collaboration claim, also delete cross-party transfer while preserving
   local training and deployment. If local-only or isolated execution closes
   the effect, the evidence supports personalization or contamination removal,
   not federated collaboration.
2. **PEFT deletion**: if the full model or an unconstrained update replaces
   PEFT, does the bottleneck remain unchanged? If yes, identify the
   adapter-native algebra, capacity, state, or communication constraint;
   otherwise do not claim PEFT specificity.
3. **Dynamic-decision deletion**: can one static, phase-static, round-robin,
   shared-capacity, or strongest simple action close the material oracle
   headroom at matched discovery and deployment cost? If yes, a controller or
   online selector is not yet needed.
4. **Operation deletion**: after replacing the proposed parameterization with
   its represented function/state and applying the strongest classical or
   generic operator, what non-preserved operation, theorem, or information
   constraint remains? If none remains, the candidate is a composition, not a
   new method kernel.

`Broadens` is not a scientific failure. Write the broadened thesis explicitly
and preserve it when it remains inside the user's actual search boundary. It is
an exclusion only from a Program whose frozen objective genuinely requires the
narrower specificity; do not silently use a narrower internal Program to
override broader user authorization.

## Search reductions before solutions

For each grounded problem, check in this order:

1. the closest primary-source method addressing the same object;
2. the strongest generic algorithmic family addressing the same estimand;
3. the classical mathematical or systems operation on the represented
   function/state;
4. the strongest simple deployable baseline under matched information and
   total cost.

Search by both object and operation. Exact keyword absence is not novelty.
Verify the primary source and write the preservation map for estimand,
information, cost, temporal dynamics, and deployment constraints.

Classify the reduction before disposition:

- if it preserves and solves the actor-level problem under the same estimand,
  information, cost, dynamics, and deployment constraints, drop the
  opportunity;
- if it preserves only the proposed method operation, drop that method kernel
  but retain the underlying problem for another artifact when it remains;
- if preservation is uncertain, hold the method claim and resolve the named
  uncertainty, but do not block a cheap problem measurement whose
  interpretation is independent of novelty.

Do not add carriers, names, auxiliary losses, routers, or review rounds to
rescue an exactly reduced method.

### Pre-signal closure rule

A generic reduction may close an actor-level problem before measurement only
when all of these are true:

1. one primary implementation, formal construction, or source-faithful
   executable microcase witnesses the complete reduction;
2. the same actor can execute it before the decision using only the same lawful
   observables;
3. operation order, rendezvous, persistent state, storage, work, physical
   bytes, latency, serving path, recipients, and estimand are preserved or
   explicitly matched;
4. the witness already determines the relevant action or removes every
   decision-changing outcome of the proposed Scout; and
5. no empirical remainder about the actor-level loss survives.

A composition assembled from separate papers, a hypothetical omniscient
central controller, or a statement that an observable is "copyable" is not
such a witness. It is `CHALLENGE_UNVERIFIED_JOINT_FEASIBILITY` and belongs in
the Scout baseline until compatibility is demonstrated. Likewise, a known
generic repair may make the future contribution `LIKELY_REPAIR` without
eliminating the need to measure whether the broken operation causes a material
loss.

## Apply the zero-compute falsification ladder

Before opening a repository or spending empirical budget, try to kill the
mechanism in this order:

1. inspect the operative equation, algorithm, data contract, and source-code
   path in the primary artifact; do not test a remembered or paraphrased
   version of the method;
2. normalize all parameterizations to the represented function, state,
   information set, and deployment output;
3. derive invariances, equivalences, conservation laws, and limiting cases,
   decompose self/local terms from cross-unit or interaction terms, then
   attempt the strongest preserving reduction;
4. construct the smallest positive instance, null instance, and nuisance
   counterexample that distinguish the proposed mechanism from a
   representation artifact or simpler explanation;
5. inspect existing cached artifacts only when their protocol preserves the
   required distinction.

Record the **unresolved empirical remainder**: the exact quantity or causal link
that source inspection and analysis cannot decide. Exclude the candidate when
the audit falsifies its premise or reduces it to an existing operation. Hold it
when the operative source or preservation map remains unverified. Only an
unresolved empirical remainder may consume Scout evidence budget.

Here "unresolved" includes a source-supported or analytically plausible
actor-level loss whose effect size is unknown. Do not require the remainder to
be federation-only, non-copyable, naturally occurring, or publication-novel
before a scoped controlled Scout.

This ladder is not experimental evidence and does not prove effectiveness. Its
purpose is to prevent experiments whose only possible contribution is
correcting a paper misreading, locating a code path, or rediscovering an
algebraic identity.

## Separate repair from contribution

Define two contrasts whenever a proposal repairs a naive, invalid, unstable, or
known-mismatched operation:

- **repair contrast**: proposed intervention versus the broken operation;
- **contribution contrast**: proposed intervention versus the strongest valid
  simpler alternative that preserves information, state, work, cost, and
  deployment as far as the claim requires.

Include a mechanism-deletion control that removes the claimed causal ingredient
while preserving the rest. Depending on the problem, this may be local-only,
no-op, static, phase-static, matched-state, dense/generic-operator, or
shared-capacity execution. A repair contrast may establish that the original
operation is harmful. Only a nontrivial contribution contrast can establish
that the proposed mechanism is needed.

## Apply proportional R0--R3 readiness

Do not import a complete scientific contract into problem-admission readiness:

- `R0` freezes only the actor and action, lawful pre-decision inputs, the exact
  smallest next cell, matched-cost invariants, fatal invalidators, a hard cap,
  the cheapest decision-complete problem-existence witness, and the strongest
  baseline's identity, fairness and constructability. It does not require the
  baseline to be fully reproduced or executed.
- `R1` permits one active outcome-blind implementation/profile smoke contract
  at a time for that exact cell. It contains no protected, held-out,
  public-test, or scientific payload, and its failure is engineering/carrier
  evidence rather than a scientific negative. It makes the bound real carrier
  and baseline runnable without reading utility. An unchanged-protocol repair
  keeps the same scientific attempt/owner/objective and may replace unsafe
  partial state with a clean `carrier_generation`; a carrier or scientific-
  contract change returns to prospective adjudication.
- A first descriptive `R2` freezes exact code/config/data/model/carrier identity
  and exposure; `2` or `3` necessary arms; `6` paired bundles; estimand, primary
  metric, MPE, guard comparator, strongest complete fair baseline, distinct
  mechanism deletion when applicable, analysis/action table, finite compute
  cap, stop rule, and screening-only claim. It does not require final power,
  multiplicity, every paper baseline, a full recipient matrix, or
  publication-scale external validity.
- Confirmatory/final `R2` additionally freezes the complete power and
  multiplicity plan, full claim-proportionate baseline family, external-validity
  scope, and any publication-level mechanism evidence needed for superiority,
  a powered negative, or scientific closure.
- `R3` executes scientific evidence only after `R2` and the applicable
  integrity, authority, provenance, and fairness gates pass.

Full license coverage, power and seed arithmetic, natural prevalence, a full
recipient matrix, full-carrier portability, and publication-scale external
validity are not default `R0` fatal gates. Move them to `R1` or `R2` unless one
is necessary to identify the exact next cell or keep that cell lawful and safe.
An unresolved later-stage field is a named downstream requirement, not a reason
to kill a cheap interpretable `R0`.

A source-grounded controlled synthetic generator, executable microcase, or
formal fixture may establish scoped problem existence when it preserves the
actor decision, lawful information, chronology, state, matched costs,
recipients required by the estimand, and fatal invalidators. It cannot establish
natural prevalence or external validity; test those only after the controlled
signal exists.

## Qualify the carrier

Before `R1`, apply only fatal identity and runnability checks: the carrier must
preserve the frozen actor, decision time, lawful pre-action information, action
set/common parent and persistent state transition, sampling unit/recipients and
estimand; name lawful code/model/data/exposure identity; expose the real primary
metric; make the strongest fair baseline constructable; and have a plausible
minimal execution path inside the frozen profile cap. A mismatch is
`HARD_BLOCK`; missing official code is not.

Route rather than hold the remaining unknowns. Runtime, VRAM, numerical
stability, throughput and per-pair cost go to one outcome-blind real-path
profile. Paired variance/covariance goes to disjoint calibration or counts in
the frozen Scout. Effect direction/magnitude, guard behavior, mechanism
statistics and whether the base loss exceeds MPE go to the Scout. Final power,
multiplicity, full baselines and external validity wait for Confirmation.

If a carrier is known structurally to erase the claimed actor transition or
make the real metric/baseline impossible, reject that carrier before execution.
Do not interpret an unknown mechanism magnitude as a carrier failure or use a
predictable null as permission for a post-hoc carrier ladder. A synthetic
fixture whose necessary interaction term is zero may validate algebra or
sensitivity, but it cannot establish the corresponding real mechanism.

## Design a decision-complete witness

Before spending evidence budget, write:

```text
uncertainty being reduced:
unresolved empirical remainder:
observation:
positive outcome -> exact action:
negative outcome -> exact action:
ambiguous outcome -> one predeclared diagnostic or hold:
cost and deadline:
```

The witness is decision-complete only when:

- the positive outcome unlocks the Contribution Gate, a specific next claim,
  or one named method-kernel test;
- the negative outcome closes or materially narrows the exact route;
- ambiguity has at most one prospective resolution and cannot start an
  open-ended rescue ladder;
- the result is measured in, or has a calibrated bridge to, the final decision
  unit;
- no cheaper source, code, algebraic, cached-artifact, or deterministic
  micro-check can retire the same uncertainty;
- the primary contribution contrast is against the strongest
  mechanism-deletion alternative, not only a known-broken baseline;
- at least one feasible outcome changes the next scientific decision.

If positive and negative outcomes both lead to “try more variants,” do not run
the witness. Redesign the estimand or close the candidate.

## Minimal record

Keep the gate to one screen:

```text
problem thesis:
stage: opportunity | problem-scout | contribution
evidence status:
R0 actor/action/lawful inputs:
R0 exact next cell, matched-cost invariants and cap:
R0 fatal invalidators and cheapest witness:
later-stage carrier/power/license/naturality requirements:
federation deletion:
PEFT deletion:
dynamic-decision deletion:
operation deletion:
strongest preserving reduction:
necessary mechanism-support condition:
mechanism-deletion control:
repair contrast versus contribution contrast:
remaining non-preserved operation:
zero-compute audit:
unresolved empirical remainder:
decision-complete witness:
disposition:
```

This is a Search artifact, not experimental evidence. Reuse it in the portfolio
ledger rather than creating another state tree or review document.
