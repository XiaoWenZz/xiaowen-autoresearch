---
name: xiaowen-autoresearch
description: "Control bounded research from opportunity discovery through problem Scouts, contribution selection, confirmation, adjudication, recovery, and handoff. Use for research questions, literature or claim audits, scientific contract design, multi-stage experiment programs, protected evidence, remote/GPU work, external advisory, stalled routes, and decision-critical interpretation. Do not invoke this skill in a pure implementation or execution worker after one frozen contract has already fixed the question, edit surface, commands, evidence boundary, budget, terminal, and callback; that worker reads only applicable AGENTS.md files, the frozen contract, target source, and necessary tests."
---

# Xiaowen AutoResearch

Optimize decision-relevant evidence per unit cost. Use this skill as the
research control plane, not as default runtime machinery for every task that
contains the word “research.”

## 1. Resolve authority and side effects

Before acting:

1. Read the complete applicable `AGENTS.md` chain, starting from its router and
   following only the domain and child rules that apply to the target. Read a
   bound contract or manifest only when the action uses it. This skill cannot
   override platform, system, developer, or `AGENTS.md` authority.
2. State repository, branch, remote, environment, scope, and owner before a
   write, launch, remote diagnosis, or protected-evidence action. Preserve
   unrelated dirty work.
3. Discover matching sessions only before creating or continuing a persistent
   worker, dispatching remote/unattended work, or mutating shared research
   state. A user-visible local single-owner task is already its owner; do not
   create a registry, chronology, lease, or duplicate task for non-duplication.
4. Classify the action as routine/reversible, prospectively authorized bounded
   execution, or approval-required. Paid, public, production, destructive,
   protected-evidence, budget-changing, and claim-changing actions require
   explicit authority.

Stop on a decision-critical authority conflict.

## 2. Choose operating weight before orchestration

Default to `operating_weight=lite`. Classify by side effects and coordination,
not by the labels “research,” “audit,” “Scout,” or “multi-step.”
`Lite` removes coordination machinery only; it does not waive the scientific
hard controls in section 6. Lite covers one local owner and one bounded route
using existing records. A user-visible task is the task capsule and delivery
surface. Lite creates:

- zero Program/Epoch, dispatch, lease, activation, lane, ledger, registry, or
  chronology records;
- zero watchdog, heartbeat, continuity automation, callback sink, or blocking
  callback ACK roundtrip;
- no duplicate task capsule; and
- at most one terminal only when durable evidence is genuinely needed,
  otherwise only the user-visible final response.

A local source/literature/code/workflow audit, a local single-session Scout,
and one one-shot Pro advisory remain Lite. Do not generate per-file sidecars or
apply `0444` merely because a task is research-related; use immutable evidence
handling only when the artifact enters a real scientific evidence chain.

Escalate to Managed only when at least one trigger is real:

- a remote or unattended process can outlive the active turn;
- protected outcomes will be accessed;
- multiple write-capable owners must coordinate;
- a shared global research state, queue, or write lease must change;
- a paid, public, production, irreversible, or third-party action is required;
  or
- a Confirmatory scientific decision requires independent ownership.

Record the trigger once, then load Managed references. Remove Managed runtime
state when the trigger closes. Do not retrofit Managed ceremony onto completed Lite work.

Use `governance_track=scout` for reversible problem-existence evidence and
`governance_track=confirmatory` for public-test access, publication-facing
claims, or expensive/irreversible evidence.

## 3. Select one route and load one layer

Read only the row for the selected route. Read a conditional reference only
when its named trigger exists.

| Route | Required references | Conditional trigger |
| --- | --- | --- |
| Local Lite workflow/code audit | none | [research-integrity.md](references/research-integrity.md) only when the task interprets literature, evidence, or scientific claims |
| Opportunity Search | [problem-space.md](references/problem-space.md), [portfolio-search.md](references/portfolio-search.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) only for a repeated/multi-candidate Program; [external-opportunity-search-prompts.md](references/external-opportunity-search-prompts.md) only to construct that prompt |
| Problem Scout / scientific contract | [problem-space.md](references/problem-space.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) only when the Scout belongs to a Program/Epoch |
| Contribution / verification / adjudication | [portfolio-search.md](references/portfolio-search.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) for Program decisions; [gate-backtesting.md](references/gate-backtesting.md) only for retrospective calibration |
| Managed controller / recovery | [orchestration.md](references/orchestration.md), [portfolio-lanes.md](references/portfolio-lanes.md) | [state-schema.md](references/state-schema.md) only when durable Managed state is actually required |
| External advisory | the selected scientific route's references | [orchestration.md](references/orchestration.md) only for persistent asynchronous delivery or recovery |
| Knowledge-map handoff | [research-map-maintenance.md](references/research-map-maintenance.md) | [research-integrity.md](references/research-integrity.md) when adding or changing a claim |

A route transition requires the new row before the transitioning action. Do not
preload all references.

## 4. Exclude the frozen execution plane

After one complete implementation contract freezes the question, edit surface,
commands, evidence boundary, budget, terminal, and callback destination,
dispatch a fresh pure executor and do not invoke or load this skill there. The
contract itself is the only task capsule. Give the executor only applicable
`AGENTS.md`, the contract, target source/evaluator, necessary tests, and exact
allowed commands.

Do not create a second capsule, lifecycle protocol, receipt schema, telemetry
gate, or context-bootstrap layer. Use one fused command or long-lived local
process for deterministic tests, canaries, stabilization, finalization, and
terminal validation; do not wake a model for each check. A user-visible local
executor returns its final directly. A persistent Managed executor uses the
callback rule in section 8.

## 5. Route reasoning effort

- Use `max` for formulation, sources/neighbors, scientific contracts, audits,
  causal/statistical/algebraic analysis, interpretation, route decisions,
  independent review, and adjudication.
- Use `high` for outcome-blind implementation, refactoring, testing,
  deterministic integration, environment setup, and execution under a frozen
  contract.
- Raise implementation to `max` when conflicting authority, evidence validity,
  concurrency, or data integrity appears. Lower effort only after the remaining work is demonstrably mechanical.

## 6. Preserve scientific hard controls

- Freeze the question, hypothesis, actor, estimand, primary metric, strongest
  baseline, identity, power, thresholds, exposure boundary, schedule/seeds,
  budgets, stop rule, analysis, and exact claim boundary before evidentiary
  execution.
- Use primary sources for definitions, settings, and decision-critical claims.
  Incomplete neighbor work is challenged or held, never novelty.
- Run source/code/algebra and the strongest preserving-reduction checks before
  expensive empirical work. Establish problem existence before method
  performance.
- Keep baselines fair and execution prospective. Never change metrics, subsets,
  seeds, stopping, carriers, or claims in response to a protected outcome.
- Enforce protected/public-test exposure isolation. Outcome-blind repair stays
  inside the unchanged contract and budget; after protected outcome access,
  apply the frozen stop and no-rescue rules.
- For result-blind work, establish a safe source tree and result stripping
  before any fetch. If the access channel can auto-load results, hold the
  channel before exposure; see [research-integrity.md](references/research-integrity.md).
- Bind evidence-bearing runs to code, config, data, environment, seed, and run
  identity. Preserve raw outputs, failures, anomalies, and deviations before
  interpretation.
- Separate liveness, engineering validity, scientific disposition, and claim
  status. Files, tests, callbacks, and compute are not scientific progress.
- Report negative/null results narrowly. A failed carrier, contract, Scout, or
  method claim is not a field-wide NO-GO.
- A worker may recommend but cannot self-accept a Confirmatory or
  publication-facing claim. Pro and same-model review are advisory.
- Store no secret in prompts, contracts, manifests, logs, or reports.

No token target, artifact count, retry count, reviewer verdict, or governance
ratio can convert an unresolved scientific, exposure, fairness, provenance,
budget, or reproducibility defect into `PASS`.

## 7. Run the minimal scientific loop

1. **Source-ground:** start from primary observations, ablations, limitations,
   sensitivity, and code; name the actor, loss, constraints, carrier, simple
   practice, and falsifiable decision.
2. **Kill cheaply:** test definitions/implementations, the strongest reduction,
   joint feasibility, and null/nuisance controls. A generic operation closes
   only when one verified complete witness solves the same actor decision under
   every matched contract field.
3. **Select:** compare at most three active briefs; admit at most one `PROBE`.
4. **Freeze:** write the smallest sufficient scientific contract and decision
   terminal. Do not prebuild downstream methods.
5. **Execute:** use the cheapest real witness and baseline-first canary.
6. **Seal:** freeze and validate raw evidence before interpretation; recompute
   the estimand independently when required.
7. **Decide:** emit one scoped disposition with evidence and uncertainty.
8. **Promote only after signal:** refresh primary neighbors and apply novelty,
   irreducibility, specificity, mechanism, evidence-scale, and paper-path gates.

During idea search, spend at least 75% on sources/code/falsification and at most
15% on governance. Reuse one source/anomaly table, neighbor table, and decision record.

## 8. Complete without callback ceremony

For user-visible Lite, final is delivery only after one open-loop audit: every
named action is `DONE`, `BLOCKED` by an external fact or need for new authority,
or `DELEGATED` with a successful receipt. A concept explanation, status reply,
or side question does not clear an unfinished active research objective unless
the user explicitly replaces/cancels it or its authority boundary changes.
Execute any safe current next decision instead of leaving it only as final
prose. End only when the bounded decision is complete, genuinely blocked, or
its next action needs new authority.
Do not persist this audit or create Program, lease, callback, sidecar, heartbeat,
`RECEIPT_ONLY`, `FINAL_ACK`, or receiver machinery.

When durable Lite evidence is needed, keep one terminal with only:

- identity and exact scope;
- evidence paths/digests and validation;
- `FACT / INFERENCE / HYPOTHESIS` plus one scoped disposition; and
- one next action or reopening fact.

Add `knowledge_reads` and `knowledge_writeback` only when a decision-changing
research terminal actually hands reusable evidence to the configured synthesis
authority. A local workflow/code audit does not need those fields. Do not edit
a frozen scientific terminal; attach a correction only when the real evidence
chain requires append-only provenance.

For a persistent Managed worker, freeze one unique terminal and make one
ordinary top-level send with a bounded tool timeout. Apply this decision table:

Before dispatch, the Controller must register one bounded fallback capable of
recovering that terminal by event or final-turn ID. That fallback is the only
retry authority; the worker never owns retry.

| Send result | Worker action | Controller action |
| --- | --- | --- |
| successful tool receipt | release ownership and emit the local final immediately; do not wait for ACK | process asynchronously |
| unavailable, timeout, or ambiguous | record `callback_delivery=unconfirmed`, emit the local final, and do not resend | recover once from terminal event or final-turn ID |
| duplicate terminal event | no worker retry | deduplicate and apply zero additional scientific/shared-state effects |

Use at-least-once wake with idempotent exactly-once effect; do not pursue
exactly-once transport at every layer. An ACK is asynchronous and optional
except when the Controller must certify a true shared-state commit. It never
blocks a user-visible worker. Detailed Managed reconciliation belongs only in
[orchestration.md](references/orchestration.md).

Use `PROBE`/`QUEUE_*` for admitted prospective work, `HOLD` for one unresolved
fact plus reopening trigger, `DROP` for a scoped reduction/failed exact claim,
and `ENGINEERING_INVALID` outside scientific evidence. A valid negative/null
retires only the uncertainty its contract measured.

## 9. Use Managed behavior only after a trigger

Only after a Managed trigger exists, load
[orchestration.md](references/orchestration.md) and
[portfolio-lanes.md](references/portfolio-lanes.md). Load
[state-schema.md](references/state-schema.md) and state/lane helpers only when
durable shared state is required. Callback/event delivery is primary; model
polling is not progress work.

## 10. Use external advisory as a one-shot

Use Pro only when an independent reasoning path can change a named decision.
Freeze local facts or the local diff first. For Lite, submit once, read once,
and stop: no sink task, job lifecycle, polling loop, heartbeat, duplicate, or
follow-up. If real Pro is unavailable, preserve concise `PRO_UNAVAILABLE`
evidence and continue independently.

Use persistent asynchronous delivery only when a Managed trigger independently
exists. Preserve the exact response and verify decision-critical claims
locally. Do not send secrets, protected evidence, raw histories, private paths,
or scientific payloads. Advisory agreement is not novelty, validity,
acceptance, or permission.

Recover from durable repository/contract/terminal authority, not chat memory.
Ignore stale epochs and duplicate terminal IDs.

## Existing deterministic helpers

Use an existing helper only when its route requires it; do not add a new
runtime governance family:

```bash
python3 scripts/init_task.py --help
python3 scripts/update_state.py --help
python3 scripts/validate_task.py --help
python3 scripts/validate_prospective_frame.py --help
python3 scripts/validate_opportunity_prompt.py --help
python3 scripts/validate_opportunity_gate_calibration.py --help
python3 scripts/reconcile_research_lanes.py --help
```

After changing source, config, contract, or execution code, run the narrowest
relevant validation and report the exact command with PASS/FAIL.
