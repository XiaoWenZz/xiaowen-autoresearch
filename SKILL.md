---
name: xiaowen-autoresearch
description: "Control bounded research discovery, Scouts, confirmation, adjudication, recovery, and handoff. Use for decision-critical sources, contracts, protected evidence, remote/GPU work, advisory, or interpretation. Do not invoke for a simple concept explanation or in a pure implementation/execution worker after the frozen contract fixes the question, edit surface, commands, evidence boundary, budget, terminal, and callback."
---

# Xiaowen AutoResearch

Optimize decision-relevant evidence per unit cost. This is a control plane, not
default machinery for every research-labelled task.

## 1. Resolve authority and side effects

1. Read the complete applicable `AGENTS.md` chain and any contract/manifest the
   action uses. This skill cannot override platform, system, developer, or
   `AGENTS.md` authority.
2. State repository, branch, remote, environment, scope, and owner before a
   write, launch, remote diagnosis, or protected-evidence action. Preserve
   unrelated dirty work.
3. Discover matching sessions only for a persistent worker, remote/unattended
   dispatch, or shared-state mutation. A local single-owner task is already its
   owner; create no registry, chronology, lease, or duplicate task.
4. Classify the action as routine/reversible, prospectively authorized bounded
   execution, or approval-required. Paid-service use, publication/public-facing
   communication, production, destructive, protected-evidence, budget-changing,
   and claim-changing actions require explicit authority.

Stop on a decision-critical authority conflict.

## 2. Choose operating weight before orchestration

Default to `operating_weight=lite`. Classify by side effects and coordination,
not by the labels “research,” “audit,” “Scout,” or “multi-step.”
`Lite` removes coordination machinery, not section 6 hard controls. It covers
one local owner and bounded route. A user-visible task is the task capsule and
delivery surface. Lite creates:

- no new Program/Epoch record for one-off Lite work; reuse the existing compact
  planning record when a repeated Program already exists, and create no
  dispatch, lease, activation, lane, ledger, registry, or chronology record;
- zero watchdog, heartbeat, continuity automation, callback sink, or blocking
  callback ACK roundtrip;
- no duplicate task capsule; and
- at most one terminal only when durable evidence is genuinely needed,
  otherwise only the user-visible final response.

Local source/literature/code/workflow audits, one local Scout, and one-shot Pro
advisory remain Lite. Sidecars or `0444` apply only to real evidence-chain
artifacts, never merely to research-labelled work.

Escalate to Managed only when at least one trigger is real:

- a remote or unattended process can outlive the active turn;
- protected outcomes will be accessed;
- multiple write-capable owners must coordinate;
- a shared global research state, queue, or write lease must change;
- a paid-service, publication/public-facing, production, irreversible, or
  third-party mutation is required;
  or
- a Confirmatory scientific decision requires independent ownership.

Record the trigger once, load Managed references, and remove its runtime state
when the trigger closes. Never retrofit Managed ceremony onto Lite work.

Use track `scout` for reversible problem evidence; use `confirmatory` for
public-test, publication-facing, expensive, or irreversible evidence.

## 3. Select one route and load one layer

Read only the row for the selected route. Read a conditional reference only
when its named trigger exists.

| Route | Required references | Conditional trigger |
| --- | --- | --- |
| Local Lite workflow/code audit | none | [research-integrity.md](references/research-integrity.md) only when the task interprets literature, evidence, or scientific claims |
| Opportunity Search | [problem-space.md](references/problem-space.md), [research-integrity.md](references/research-integrity.md) | [portfolio-search.md](references/portfolio-search.md) only for repeated, multi-candidate, or cross-candidate selection; [research-programs.md](references/research-programs.md) only when a Program already exists; [external-opportunity-search-prompts.md](references/external-opportunity-search-prompts.md) only to construct that prompt |
| Problem Scout / scientific contract | [problem-space.md](references/problem-space.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) only when the Scout belongs to a Program/Epoch |
| Contribution / verification / adjudication | [portfolio-search.md](references/portfolio-search.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) for Program decisions; [gate-backtesting.md](references/gate-backtesting.md) only for retrospective calibration |
| Managed controller / recovery | [orchestration.md](references/orchestration.md) | [portfolio-lanes.md](references/portfolio-lanes.md) only when a real shared lane changes; [state-schema.md](references/state-schema.md) only when durable Managed state is actually required |
| External advisory | the selected scientific route's references | [orchestration.md](references/orchestration.md) only for persistent asynchronous delivery or recovery |
| Knowledge-map handoff | [research-map-maintenance.md](references/research-map-maintenance.md) | [research-integrity.md](references/research-integrity.md) when adding or changing a claim |

A route transition requires the new row before the transitioning action. Do not
preload all references.

## 4. Exclude the frozen execution plane

Keep these boundaries: the Controller routes and accepts; the Explorer owns one
complete source-to-`PROBE` loop; the Audit owns the whole `R0` decision in one
owner/terminal; the Executor enters only after a complete implementation
contract is frozen. Packet, locator, sidecar, and file checks stay inside the
current owner as mechanical preflight.

At an idea boundary, reuse the existing task capsule, decision record, and
terminal/closure record. Do not include the prior idea's raw transcript. For
the same idea, use `/compact` only
when decision-relevant history has become materially redundant. On an idea
switch, reuse the canonical role session only after a runtime-supported
compact/reset succeeds and isolation is verifiable. Record selection is not
context isolation; otherwise open one fresh session, transfer the canonical
role binding, and close/archive the prior session so no duplicate owner remains.
A strict-blind owner exposed to forbidden bytes stays ineligible even after
compaction; use a fresh unexposed owner.

For a missing field/hash, load only the authoritative section and directly
referenced evidence needed to resolve it; load the complete record only for an
unresolved decision-critical contradiction, and never load a prior raw
transcript. Never collapse `ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`,
`CARRIER_STOP`, or `UNOBSERVED` into a scientific negative. A contract change
creates a new candidate/version and preserves the old records.

Before a persistent Managed worker is created or reused, verify its saved
Project ID, cwd/repository, candidate/version, and canonical role. A projectless
or unverified worker has no scientific/shared-state authority. Pin only active
Managed canonical roles that need Controller follow-up. At each Controller
resume, activation, state transition, and terminal, use runtime APIs to
reconcile pins; Lite and Pro advisory tasks are never auto-pinned.

Name each persistent research-role session
`<Role> · <candidate-or-bounded-scope> · <STATE>` and update it at activation,
reuse, material phase/state change, and terminal absorption with the runtime
title API; never rely on conversation memory alone.

Maintain one persistent Controller-global continuity heartbeat; it remains
active through idle periods and worker/job completions. Adjust cadence in place;
add a remote-job block only while live, clear only the exact job block, and
never delete the global automation. It may reconcile liveness, pins/titles,
completions, and owners, but cannot research, read protected results, launch, or
certify science.

They are not a new data protocol, capsule, schema, lifecycle, context-bootstrap
layer, automation, or evidence substitute. They cannot change the research
contract, metric, seed, budget, stop rule, or protected/outcome boundary.

After a complete contract freezes question, edits, commands, evidence, budget,
terminal, and callback, dispatch a fresh pure executor and do not invoke or load
this skill there. The contract itself is the only task capsule: applicable
`AGENTS.md`, contract, evaluator, tests, commands. Add no lifecycle, receipt,
telemetry, or context. Freeze weight/track, candidate/version, exposure,
model/effort, GPU cap, and claim tier; downstream must not rederive defaults.
Fuse deterministic checks; do not wake a
model for each check. A local executor returns its final directly.

Use one post-freeze fast path in one uninterrupted Executor loop: identity/cap;
repo/carrier; read-only code/evaluation preflight; no-utility minimal sanity;
one root-caused targeted patch; at most one clean reimplementation if identity
is unchanged; fused validation/exact cells; write structured raw outputs; hand
exact paths/hashes to the validator. No intermediate Controller callback or
task/version. Stop on an unresolved root, external fact, or
scientific/authority/exposure/budget/protected change. A new run/output identity
preserves provenance.

## 5. Route model and reasoning effort

- `gpt-5.6-sol max`: formulation, sources/neighbors, contracts, Audit,
  scientific analysis/interpretation, routes, closure, and adjudication.
- `gpt-5.6-sol xhigh`: first real-carrier Scout Executor, complex implementation,
  remote integration/debugging, and evidence-bearing execution.
- `gpt-5.6-sol high`: bounded frozen-contract implementation, testing,
  deterministic integration, and routine execution.
- `gpt-5.6-luna max`: high-volume deterministic rehash/sync/package/rerun or
  simple outcome-invariant repair only; never scientific adjudication.

Bind the route to the active objective, not permanently to the reusable session
and not to each microphase. Keep model and effort stable until that objective's
terminal or explicit handoff. Reclassify only a separately bounded successor.
Resume the same canonical session on `gpt-5.6-luna max` when it is purely
deterministic rehash/sync/package, unchanged-contract rerun, or root-caused
outcome-invariant repair. Never create another role or session solely to change
model.

Raise ambiguity about authority, evidence, exposure, concurrency, or data
integrity to `sol max`; never substitute `luna max` for `sol xhigh/max`.

## 6. Preserve scientific hard controls

- Apply controls proportionally. `R0` freezes actor/action/lawful inputs, next
  cell, matched-cost invariants, fatal invalidators, cap, cheapest witness, and
  baseline identity/fairness/constructability. `R1` makes the real carrier and
  baseline runnable without utility. A first descriptive `R2` freezes exact
  identity/exposure, `2`--`3` necessary arms, `6` paired bundles, metric, MPE,
  guard, baseline/deletion, actions, and finite cap. Confirmatory, superiority,
  powered-negative, or closure claims additionally require complete power,
  multiplicity, baselines, and external-validity scope. Before scientific `R3`,
  `R2` freezes the applicable contract above.
- Use primary sources for definitions, settings, and decision-critical claims.
  Incomplete neighbor work is challenged or held, never novelty.
- Establish problem existence before method performance with source/code/algebra,
  strongest reductions, and one verified complete witness for any generic close.
- Keep baselines fair and execution prospective. Never change metrics, subsets,
  seeds, stopping, carriers, or claims in response to a protected outcome.
- Enforce protected/public-test exposure isolation. Outcome-blind repair stays
  inside the unchanged contract and budget; after protected outcome access,
  apply the frozen stop and no-rescue rules.
- Distinguish public-source review from strict result blindness. Opportunity
  Search and ordinary public-source `R0` may read public primary methods,
  results, appendices, and official-code documentation; those public results
  are not the candidate's protected outcomes. Enable strict blindness only for
  one prospectively named independence or anti-anchoring decision. Its safe
  tree/result-stripped packet must pass deterministic pre-dispatch validation;
  otherwise block dispatch before an Audit sees source bytes. See
  [research-integrity.md](references/research-integrity.md).
- Bind evidence-bearing runs to code, config, data, environment, seed, and run
  identity. Preserve raw outputs, failures, anomalies, and deviations before
  interpretation.
- Derive `completed -> contract-consistent -> evidence-eligible ->
  independently verified -> claim-accepted`; deterministic prechecks may
  reject but cannot accept scientific claims. Files/tests/callbacks/compute are
  not science.
- Report negative/null results narrowly. A failed carrier, contract, Scout, or
  method claim is not a field-wide NO-GO.
- Before a durable scientific `DROP` or `CLOSE`, freeze one closure packet in the
  existing decision record: exact fingerprint/scope, admissible closure basis,
  strongest counterargument, reopening fact, impact, and `closure_risk=LOW|HIGH`.
  Do not create a new artifact family.
- `ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`, carrier/access failure, search exhaustion,
  missing sources, and incomplete neighbor work are not scientific closures and cannot retire the hypothesis.
- A worker may recommend but cannot self-accept a Confirmatory or
  publication-facing claim. Pro and same-model review are advisory.
- Store no secret in prompts, contracts, manifests, logs, or reports.

No token target, artifact count, retry count, reviewer verdict, or governance
ratio can convert an unresolved scientific, exposure, fairness, provenance,
budget, or reproducibility defect into `PASS`.

## 7. Run novelty-first to a real Scout

1. **Ground and reduce:** name actor/decision, causal gap, strongest reduction,
   null, and falsifier from primary sources/code.
2. **Select for contribution:** rank value, residual novelty, causal depth, and
   domain relevance before carrier ease; admit at most one `PROBE`.
3. **Bind early:** hard-block mismatched actor/time/information, parent/work,
   action set/state transition, lawful use, metric, or a baseline whose identity,
   fairness, or constructability fails. Do not require baseline execution at
   `R0`; make it runnable at `R1` and execute it at `R2/R3`. Missing official
   code is not a block; build a faithful carrier within cap.
4. **Freeze the first Scout:** use two or three necessary arms and all six
   paired bundles. `n0=3` is validity/guard-only; no positive stop precedes `nmax=6`.
5. **Execute the shortest real path:** `R1` prefers the carrier's minimal code
   path; pure synthetic smoke converts only when it is the preregistered witness.
   System profiles see no utility; calibration is disjoint or counts in the Scout.
6. **Seal and decide:** preserve raw evidence; promote only material signal.

Use the integrity reference for the Scout contract, dual-5090 envelope, SLA,
and same-root breaker. A constructable Scout outranks more dossiers; idle GPU
never authorizes filler.

End a same-root engineering stall with one root-cause inventory and a minimal
real carrier, simplified new version, or evidence-gap archive—not a rename.

Use 75% source/code/falsification and 15% governance shares only as retrospective
diagnostics from existing records, never as per-task telemetry, a sidecar, or an
acceptance gate. Compare time-to-first-scientific-outcome, time-to-valid-R1,
R0-to-R1 pass rate, access-hold rate, and governance-attention share without
creating a new measurement family; activity and GPU use are not science.

Use `R0`--`R3` as shorthand, never a lifecycle; follow
[problem-space.md](references/problem-space.md). Keep at most one active `R1`
per candidate/version; it is not a portfolio-wide mutex. An unchanged-protocol
repair may rerun within cap. Continue bounded Explorer work while any currently
usable, authorized GPU card can absorb another smallest valid complete tranche.
Independent launch-ready Scouts may run in parallel across cards or hosts with
isolated owners/repositories and frozen per-job caps. Pause Explorer for
compute saturation only when every currently usable, authorized card is
occupied by valid live work and at least one additional independently frozen,
launch-ready item waits solely for capacity. Blocked or profile-waiting items,
unavailable cards, and empty cards do not count. This never authorizes filler;
after three consecutive no-`PROBE` searches, run the recall audit.

## 8. Complete without callback ceremony

For user-visible Lite, end only after one open-loop audit maps every named
action to `DONE`, externally/authority `BLOCKED`, or `DELEGATED` with a
successful receipt. A concept explanation, status reply, or side question does
not clear an active objective unless the user replaces/cancels it or its
authority changes. Execute any safe current next decision instead of leaving it
as prose.
Do not persist this audit or create Program, lease, callback, sidecar, heartbeat,
`RECEIPT_ONLY`, `FINAL_ACK`, or receiver machinery.

When durable Lite evidence is needed, keep one terminal with identity/scope,
evidence/validation, `FACT / INFERENCE / HYPOTHESIS`, one disposition, and one
next action/reopening fact. Add knowledge provenance only for a
decision-changing synthesis handoff, never a routine local workflow/code audit.

A bounded delegated worker sends at most one ordinary completion message. A
successful tool receipt releases it immediately; Lite creates no receiver,
fallback, acknowledgement, or callback transaction and never waits for
`FINAL_ACK`.

Persistent Managed completion follows
[orchestration.md](references/orchestration.md): freeze one terminal, make one
bounded top-level send, release the worker on a successful receipt, and never
resend an ambiguous delivery. One pre-registered Controller fallback recovers
by event/final-turn ID with idempotent effects. An ACK never blocks the worker.

After `ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`, or `CARRIER_STOP`, an
open/`UNTESTED` candidate may end Controller absorption only as `DELEGATED`
with a successful same-idea successor receipt, `BLOCKED` with one reopening
fact/observer/trigger, or `DONE` as a non-active evidence-gap archive with a
reopening fact. `OPEN_WITHOUT_OWNER`, “keep open,” “do not launch,” or a worker
`NEXT_ACTION` alone is invalid; the Controller owns the route.

## 9. Use external advisory as a one-shot

Every durable scientific `DROP` or `CLOSE` follows the Closure Confidence Gate
in [research-integrity.md](references/research-integrity.md). A complete-witness
`LOW` closure may finish locally after independent Audit; a composed,
interpretive, disputed, or last-route `HIGH` closure remains provisional until
one adversarial rebuttal. Engineering/access/carrier failure and search
exhaustion are not closures and never invoke this gate.

For a `HIGH` closure, freeze local facts, submit one Pro rebuttal, read once,
verify decision-critical claims locally, and stop—no sink, polling, duplicate,
or follow-up. Record only its trigger, disposition, decision effect, and final
confidence in the existing decision record. If Pro is unavailable, use one
fresh independent local closure Audit; never hard-close from unavailability.

Keep Pro off the critical path: submit once, continue local work, then let the
current owner make at most one state-only check after local work completes.
Add no monitor, poll loop, sink, automation, lifecycle, duplicate, or follow-up.
On `READY`, read once and verify.

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
