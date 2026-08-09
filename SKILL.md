---
name: xiaowen-autoresearch
description: "Control bounded research discovery, Scouts, confirmation, adjudication, recovery, and handoff. Use for decision-critical sources, contracts, protected evidence, remote/GPU work, advisory, or interpretation. Do not invoke for a simple concept explanation or in a pure implementation/execution worker after the frozen contract fixes the question, edit surface, commands, evidence boundary, budget, terminal, and callback."
---

# Xiaowen AutoResearch

Optimize evidence per cost; never add machinery by label.

## 1. Resolve authority and side effects

1. Read the applicable `AGENTS.md` chain and used contract/manifest. This skill
   cannot override platform, system, developer, or
   `AGENTS.md` authority.
2. State repository, branch, remote, environment, scope, and owner before a
   write, launch, remote diagnosis, or protected-evidence action. Preserve
   unrelated dirty work.
3. Discover matching sessions only for persistent work, remote/unattended
   dispatch, or shared-state mutation. A local single-owner task is its owner;
   create no registry, chronology, lease, or duplicate task.
4. Classify as routine/reversible, authorized bounded, or approval-required.
   Paid/public/production/destructive/protected-evidence/budget- or claim-changing
   actions require authority.

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

Local source/literature/code/workflow audits, one local Scout, bounded Pro
batches, and one-shot Pro closure advisory remain Lite. Sidecars or `0444`
apply only to real evidence-chain artifacts.

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

Read the selected row and only trigger-matched conditional references.

| Route | Required references | Conditional trigger |
| --- | --- | --- |
| Local Lite workflow/code audit | none | [research-integrity.md](references/research-integrity.md) only when the task interprets literature, evidence, or scientific claims |
| Opportunity Search | [problem-space.md](references/problem-space.md), [research-integrity.md](references/research-integrity.md) | [portfolio-search.md](references/portfolio-search.md) only for repeated, multi-candidate, or cross-candidate selection; [research-programs.md](references/research-programs.md) only when a Program already exists; [external-opportunity-search-prompts.md](references/external-opportunity-search-prompts.md) only to construct that prompt |
| Problem Scout / scientific contract | [problem-space.md](references/problem-space.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) only when the Scout belongs to a Program/Epoch |
| Contribution / verification / adjudication | [portfolio-search.md](references/portfolio-search.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) for Program decisions; [gate-backtesting.md](references/gate-backtesting.md) only for retrospective calibration |
| Managed controller / recovery | [orchestration.md](references/orchestration.md) | [portfolio-lanes.md](references/portfolio-lanes.md) only when a real shared lane changes; [state-schema.md](references/state-schema.md) only when durable Managed state is actually required |
| External Pro | selected route references | [external-opportunity-search-prompts.md](references/external-opportunity-search-prompts.md) for discovery; [orchestration.md](references/orchestration.md) only on an independent Managed trigger |
| Knowledge-map handoff | [research-map-maintenance.md](references/research-map-maintenance.md) | [research-integrity.md](references/research-integrity.md) when adding or changing a claim |

Load a new route row before transition; never preload all references.

## 4. Exclude the frozen execution plane

Keep role boundaries: Controller routes/accepts; Explorer owns one complete
source-to-`PROBE` loop; Audit owns the whole `R0` decision in one owner/terminal;
Executor enters only after a complete implementation contract freezes. Packet,
locator, sidecar, and file checks stay in the current owner as preflight.

Reuse the idea's task capsule and durable records, never its raw transcript.
Use `/compact` only after decision-relevant history becomes redundant. Reuse a
canonical role across ideas only after verifiable runtime compact/reset;
record selection is not isolation. Otherwise transfer the role once and retire
the predecessor. A strict-blind owner exposed to forbidden bytes stays
ineligible after compaction.

For a missing field/hash, load only the authoritative section and directly
referenced evidence needed to resolve it; load the complete record only for an
unresolved decision-critical contradiction, and never load a prior raw
transcript. Never collapse `ENGINEERING_INVALID`, `HOLD_ACCESS_CHANNEL`,
`CARRIER_STOP`, or `UNOBSERVED` into a scientific negative. A contract change
creates a new candidate/version and preserves the old records.

Before Managed reuse/create, verify Project ID, cwd/repository,
candidate/version and role or grant no shared-state authority. Pin
Managed roles needing follow-up, never Lite/Pro; `Audit · Workflow Evolution`
stays pinned through idle/`COMPLETE` until retirement,
transfer, or user request, gaining no role, authority, lease, heartbeat, or
state; then reconcile via runtime APIs.

Title persistent roles `<Role> · <candidate-or-bounded-scope> · <STATE>` and
update on activation, material state change and terminal absorption.

Keep one retargeted, never duplicated Controller heartbeat. Each wake resumes
that Controller, drains prebound terminal absorb/route/activate/title/pin/CAS
before final, and never redoes role semantics, interprets protected science,
creates filler or crosses an unabsorbed terminal. Slurm checks capacity only for
exact `A100_CAPACITY_AVAILABLE`. See `references/orchestration.md`.

They are no data protocol, capsule, schema, lifecycle, context-bootstrap,
automation or evidence substitute, and cannot change the research contract,
metric, seed, budget, stop rule, or protected/outcome boundary.

After a complete contract freezes question, edits, commands, evidence, budget,
terminal, and callback, activate one bounded objective in the canonical
Executor and do not invoke or load this skill there. A cross-thread successor
requires an allowlisted reason, immutable evidence reference, and valid role
mapping. The contract is the only capsule; freeze route, identity, exposure,
cap, and claim.

Use one post-freeze fast path, owner/model, and final terminal. Before
release/no-rescue, run the production chain itself—CLI -> `prepare_run` ->
consumer -> generated launch -> coordinator/bootstrap -> exact runtime—to
`READY_BEFORE_FIRST_UTILITY`, then exit with zero
training/update/eval/utility/protected access. Generate launch/witness from one
source; check env, modes, and future-reader canaries.

Bind contract/prior-record digests in `startup_chain_authority`; derive its ID
from state+objective. The same Executor CAS-appends at most two sealed failure
records, changing no terminal/callback/Controller/owner/objective; `BLOCKED`/
rebuild retain it and only Audit replaces it. IDs, paths and fingerprints cannot
reset it. Round 1 is minimal repair; round 2 is clean reimplementation then an
in-owner inventory, not terminal. Outside an orchestration escalation gate,
repair/rerun; unsafe state uses a clean `carrier_generation` within the same
scientific attempt/owner/budget. Child rules may preserve bytes but cannot
impose first-mismatch terminal/create-new. Preserve cumulative debit/ceilings.
Parent rules let that Executor use `record-startup-attempt` without terminal,
callback, Controller, owner or objective transition.
Never default to
`Lead -> Builder -> Acceptance` or two delegated objectives in one thread.

## 5. Route model and reasoning effort

- `gpt-5.6-sol max`: formulation, material authority/claim choices,
  scientific/protected interpretation and adjudication.
- `gpt-5.6-sol xhigh`: real-carrier Scout, remote integration/debugging,
  evidence execution.
- `gpt-5.6-sol high`: outcome-blind diagnosis or frozen-oracle conformance;
  file/module count is no trigger.
- `gpt-5.6-luna max`: default for frozen deterministic implementation/
  integration, tests/docs from frozen oracles, package/sync/rehash,
  sealed reruns, and repairs.

Choose cheapest capable; ties use Luna; role alone never selects effort. Freeze
edits, acceptance, evidence/exposure, budget and stop. Prefer named no-history
`agent_type=luna_worker`. If absent but an existing-thread model override exists,
use one contiguous `luna/max` turn with capsule and unique
`LUNA_ROUTE_DISPATCH_ID=<id>`. Before effects validate named-child parent or
same-thread thread/turn/dispatch via
`scripts/validate_model_route.py`; `task_name` is neither. Both preserve
owner/objective/role/budget/terminal; no authority. One repair per
fingerprint. Never route protected/scientific/authority/ambiguous decisions to
Luna.

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
  one prospectively named independence or anti-anchoring decision. Every fresh
  strict-blind owner uses only validated capsule locators; external paths are
  provenance, and a missing identity blocks before bytes. See
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

End a same-root engineering stall with one root-cause inventory in its owner,
then a minimal/clean carrier. New version/owner/route requires a material
boundary; renaming never grants repair.

Use 75% source/code/falsification and 15% governance shares only as retrospective
diagnostics from existing records, never as per-task telemetry, a sidecar, or an
acceptance gate. Compare time-to-first-scientific-outcome, time-to-valid-R1,
R0-to-R1 pass rate, access-hold rate, and governance-attention share without
creating a new measurement family; activity and GPU use are not science.

Workflow Evolution is reusable Audit scope, not a fifth role. Fuse verified
leads and traces into one replayed, rollbackable patch. Reliability is the
floor; assess time, yield, attention, recurrence/blast radius.
Default locally; batch only
material science, acceptance, exposure, authority, irreversible/public/paid/
permission or user-facing choices. Add no self-trigger, science block,
telemetry, watcher or lifecycle.

Never emit `RETAIN|COMPLETE` from a candidate-only diff: live files must
byte-match it, required checks pass, and the consumer/Controller receive the
exact live hash plus reload instruction. Advisory may review the deployed diff
later.

Use `R0`--`R3` as shorthand, never a lifecycle; follow
[problem-space.md](references/problem-space.md). Keep at most one active `R1`
per candidate/version, never portfolio-wide. Unchanged-protocol repair may rerun
within cap. Run isolated frozen Scouts in parallel; continue Explorer while any
authorized usable card can take a smallest valid tranche. Pause only when every
such card runs valid work and a launch-ready item waits solely for capacity;
blocked/profile-waiting/unavailable/empty cards do not count. Never create
filler; after three no-`PROBE` searches, run recall audit.

## 8. Complete without callback ceremony

For user-visible Lite, end only with every action `DONE`, finite
external/authority `BLOCKED`, or receipt-backed `DELEGATED`. A side question or
status does not clear an objective unless the user replaces/cancels it or its
authority changes. Execute any safe next decision. Do not persist this audit or
create Program, lease, callback, sidecar, heartbeat, `RECEIPT_ONLY`, `FINAL_ACK`,
or receiver machinery.

When durable Lite evidence is needed, keep one terminal with identity/scope,
evidence/validation, `FACT / INFERENCE / HYPOTHESIS`, one disposition, and one
next action/reopening fact. Add knowledge provenance only for a
decision-changing synthesis handoff, never a routine local workflow/code audit.
Validate rule hashes with `workflow_evolution_gate.py validate-rule-chain` before seal.

A successful tool receipt releases the worker immediately; Lite creates no receiver,
fallback, acknowledgement, or callback transaction and never waits for
`FINAL_ACK`.

Persistent Managed completion follows orchestration:
one bounded top-level send; release on successful receipt; never resend an
ambiguous delivery; ACK never blocks. Fallback has idempotent effects.

Atomically absorb every actionable terminal: `PROBE`, `PASS_R*`, `PROFILE_*`,
engineering/conflict/access/carrier stops. In that turn an open candidate becomes
receipt-and-activation-backed `DELEGATED`, or finite `BLOCKED` only on an
external fact/unavailable authority with observer, trigger/check and deadline.
`DONE` requires scientific `CLOSED`; `OPEN/DONE` and `OPEN_WITHOUT_OWNER` are
invalid and internal gaps stay owned. `dispatch_next` is incomplete before
activation. Ordinary/heartbeat wakes recover idempotently and cannot final
before safe absorb/route/activate or a finite external block.

## 9. Route Pro through the scientific owner

Controller detects and routes a Pro trigger but must not author the prompt or
adjudicate the answer. Explorer owns source/neighbor/reduction/formulation; an
eligible Audit owns contract/estimand, signal-versus-implementation,
contribution, Confirmation and closure. Executor returns ambiguity and never
uses Pro to alter frozen execution.

Use Pro proactively at material gates or bottlenecks to falsify, improve, or
cross-check a route, even when a local answer exists. Always verify locally;
skip only deterministic repair with no decision ambiguity.

Pro is never a lane, owner or authority. Use sequential one-shot batches in one
exact-ID conversation: one in-flight submit/read, no queue/follow-up/page poll,
sink or duplicate; deduplicate by candidate/scope hash. Before submission,
provide one hashed review bundle containing the complete live Skill, every
applicable `AGENTS.md`, routed direct references, candidate diff/validation and
bounded evidence. Redact only secrets and protected payloads; a summary is not
a substitute. Missing ordinary advisory is `SKIPPED_UNAVAILABLE`, never a
similar conversation. Ordinary batches are `NON_BLOCKING`;
`BLOCKING_HIGH_RISK` needs a previously bound exact gate and locally absorbed
validation. The singleton may wake an eligible Explorer/Audit but never open
Pro or create a reader. Pro grants no authority by agreement.

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

After any change, run the narrowest relevant validation and report its exact
command with PASS/FAIL.
