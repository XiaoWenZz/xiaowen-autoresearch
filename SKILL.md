---
name: xiaowen-autoresearch
description: "Control bounded research from opportunity discovery through problem Scouts, contribution selection, confirmation, adjudication, recovery, and handoff. Use for research questions, literature or claim audits, scientific contract design, multi-stage experiment programs, protected evidence, remote/GPU work, external advisory, stalled routes, and decision-critical interpretation. Do not invoke this skill in a pure implementation or execution worker after one frozen contract has already fixed the question, edit surface, commands, evidence boundary, budget, terminal, and callback; that worker reads only applicable AGENTS.md files, the frozen contract, target source, and necessary tests."
---

# Xiaowen AutoResearch

Optimize decision-relevant evidence per unit cost. This skill is the research
control plane: it selects a scientific route, freezes authority, and interprets
evidence. It is not the execution plane for a frozen implementation task.

## 1. Resolve authority

Before a research action:

1. Read the complete applicable `AGENTS.md` chain and the directly bound
   contract or manifest. This skill cannot override platform, system,
   developer, or `AGENTS.md` authority.
2. State repository, branch, remote, environment, scope, and owner before a
   write, launch, remote diagnosis, or protected-evidence action. Preserve
   unrelated dirty work.
3. For a named Program, Epoch, Scout, experiment, or persistent task, discover
   matching sessions and resolve one canonical owner before dispatch.
4. Classify the action as read-only/routine, prospectively authorized bounded
   execution, or approval-required. Paid, public, production, destructive,
   protected-evidence, budget-changing, and claim-changing actions need their
   explicit authority.

Stop on a decision-critical authority conflict.

## 2. Select one route and load one layer

Keep `Opportunity Search -> Problem Scout -> Contribution Gate ->
Confirmatory` distinct. Select one primary route and read only the references
in its row. Read a conditional reference only when its named trigger exists.

| Route | Required references | Conditional trigger |
| --- | --- | --- |
| Opportunity Search | [problem-space.md](references/problem-space.md), [portfolio-search.md](references/portfolio-search.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) for repeated/multi-candidate Programs; [external-opportunity-search-prompts.md](references/external-opportunity-search-prompts.md) only to construct that external prompt |
| Problem Scout / scientific contract | [problem-space.md](references/problem-space.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) when the Scout belongs to a Program/Epoch |
| Contribution / verification / adjudication | [portfolio-search.md](references/portfolio-search.md), [research-integrity.md](references/research-integrity.md) | [research-programs.md](references/research-programs.md) for Program decisions; [gate-backtesting.md](references/gate-backtesting.md) only for retrospective calibration |
| Managed controller / recovery | [orchestration.md](references/orchestration.md), [portfolio-lanes.md](references/portfolio-lanes.md) | [state-schema.md](references/state-schema.md) only when durable managed state is actually required |
| External advisory | The selected scientific route's references | [orchestration.md](references/orchestration.md) only for asynchronous delivery, recovery, or a persistent reviewer |
| Knowledge-map handoff | [research-map-maintenance.md](references/research-map-maintenance.md) | [research-integrity.md](references/research-integrity.md) when adding or changing a claim |

A route transition requires the new row before the transitioning action. Do not
preload all references.

### Execution-plane exclusion

After the Controller freezes one complete implementation contract, dispatch a
fresh pure executor when parent research history is unnecessary. Do not invoke
or load this skill in that executor. Its entire instruction set is:

- applicable `AGENTS.md` files;
- the single frozen contract;
- target source and immutable evaluator/launcher/finalizer;
- necessary tests and exact allowed commands; and
- the exact terminal and callback destination.

The contract itself is the only task capsule. Do not create a second capsule,
lifecycle protocol, receipt schema, telemetry gate, or context-bootstrap
reference. The executor makes no scientific, portfolio, novelty, budget, or
claim decision. Any required contract change returns to the control plane.

When the frozen path contains deterministic tests, canaries, bounded
stabilization, finalization, and terminal validation, run them through one
fused command or long-lived local process. Let that process perform the real
health/progress checks and emit one completion event; do not wake a model for
each check.

Keep Codex thread transport outside that fused local action. The executor may
discover the supported top-level thread tools once when they are not already
exposed, but `functions.exec` must not invoke `send_message_to_thread`,
`wait_threads`, or another Codex thread operation. After terminal freeze, use
ordinary top-level delivery and ACK waiting. Emit no commentary or local final
from first activation until the ACK has been delivered.

## 3. Choose operating weight

Default to `operating_weight=lite`.

Lite means one owner, one bounded route, existing project records, no managed
state file, no lease registry, no lane snapshot, no watchdog, and no continuity
automation. A local single-session Scout does not acquire managed machinery
merely because it has several steps.

Load managed orchestration only when at least one trigger is real:

- more than one session or owner must coordinate;
- remote/GPU, paid, public, or unattended work can outlive the active turn;
- callback loss or recovery must be handled;
- Confirmatory or publication-facing evidence needs independent ownership; or
- a shared queue/lease must prevent concurrent writes.

Record the trigger before increasing weight. Remove managed runtime state when
the trigger closes; do not retain it as ceremony.

Use `governance_track=scout` for reversible problem-existence evidence and
`governance_track=confirmatory` for public-test access, publication-facing
claims, or expensive/irreversible evidence.

## 4. Route reasoning effort

- Use `max` for research formulation, sources/neighbors, scientific contracts,
  audits, causal/statistical/algebraic analysis, interpretation, route
  decisions, independent review, and adjudication.
- Use `high` for outcome-blind implementation, refactoring, testing,
  deterministic integration, environment setup, and execution under a frozen
  contract.
- Raise implementation to `max` when conflicting authority, evidence validity,
  concurrency, or data integrity appears.
- Lower effort only after the step is demonstrably mechanical.

## 5. Cross-stage hard controls

These controls remain hard without copying every route-specific procedure:

- Freeze the question, hypothesis, actor, estimand, primary metric, strongest
  relevant baseline, data/exposure boundary, schedule/seeds, per-attempt and
  staged budget, stop rule, analysis, and exact claim boundary before
  evidentiary execution.
- Use primary sources for definitions, methods, settings, and
  decision-critical claims. Incomplete neighbor work is challenged or held,
  never novelty.
- Run source/code/algebra and strongest preserving-reduction checks before
  expensive empirical work. Establish problem existence before method
  performance.
- Keep baselines fair and execution prospective. Never change thresholds,
  metrics, subsets, seeds, stopping, carriers, or claims in response to a
  protected or scientific outcome.
- Enforce the frozen exposure contract for protected outcomes, labels,
  predictions, held-out rows, utilities, logits, and public-test results.
  Outcome-blind repair stays inside the unchanged contract and budget.
- Bind every evidence-bearing run to code, config, data, environment, seed, and
  run identity. Preserve raw outputs, failures, anomalies, deviations, and
  immutable evidence before interpretation.
- Separate liveness, engineering validity, scientific disposition, and claim
  status. Files, commits, tests, tokens, callbacks, and GPU hours are not
  scientific progress by themselves.
- Report negative/null results honestly and narrowly. A failed carrier,
  contract, Scout, or method claim is not a field-wide NO-GO.
- A worker may recommend but cannot self-accept a Confirmatory or
  publication-facing claim. Pro and same-model review are advisory.
- Store no secret in prompts, contracts, state, manifests, logs, or reports.

No token target, artifact count, retry count, reviewer verdict, or governance
ratio can convert an unresolved scientific, exposure, fairness, provenance,
budget, or reproducibility defect into `PASS`. Absolute token totals and
governance file counts are diagnostics, not execution gates or early-stop
cutoffs.

## 6. Minimal scientific loop

1. **Ground:** name who incurs which measurable loss, under which constraints,
   on which adequate carrier, against which simple practice.
2. **Kill cheaply:** check primary definitions/implementations, the strongest
   preserving reduction, source/license/capacity feasibility, the smallest
   joint-carrier witness, and null/nuisance controls.
3. **Select:** compare at most three active briefs; admit at most one `PROBE`.
   Route the rest before repository construction.
4. **Freeze:** write one smallest sufficient scientific contract and exact
   decision terminal. Do not prebuild downstream methods.
5. **Execute:** send a frozen implementation task to the execution plane; use
   the cheapest real witness and baseline-first canary.
6. **Seal:** freeze and validate raw evidence before interpretation; recompute
   the estimand independently when required.
7. **Decide:** emit one scoped scientific disposition with its evidence and
   uncertainty.
8. **Promote only after signal:** refresh primary neighbors and apply novelty,
   irreducibility, specificity, mechanism, evidence-scale, and paper-path
   checks before Contribution or Confirmatory work.

Spend early attention on primary sources, operation maps, reductions, and
falsification. Reuse one living neighbor table and one decision record.

## 7. Minimal terminal contract

Every bounded route ends with:

- task/run identity and frozen contract identity;
- evidence paths/digests and validation result;
- `FACT / INFERENCE / HYPOTHESIS` separated where interpretation occurs;
- one scoped disposition;
- one next action or one reopening fact; and
- explicit exposure, ownership, and callback state when applicable.

Use these meanings:

- `PROBE` or `QUEUE_*`: admitted prospective work, not scientific acceptance;
- `HOLD`: an exact unresolved fact plus observer/trigger/deadline/fallback;
- `DROP`: a scoped reduction or failed carrier/contract/claim;
- `ENGINEERING_INVALID`: outside scientific evidence and eligible only for
  unchanged-contract outcome-blind repair;
- valid negative/null: uncertainty retired without being relabeled positive.

For a persistent worker, freeze terminal evidence, send the exact terminal
event to the registered Controller, receive the real tool receipt, then emit
the local final. A local final without that receipt is
`callback_delivery=unconfirmed`. Controller durable reconciliation and final
ACK are control-plane responsibilities.

The fused terminal-producing process must self-validate and emit one frozen
delivery summary containing the absolute repository/workdir, absolute terminal
path and digest, exact task/dispatch/lease/owner/terminal tuple, absolute ACK
path, receiver destination, and worker target. It also emits one compact,
LF-only receiver activation with a fail-closed canonical encoding. The
executor then uses one ordinary top-level `send_message_to_thread` call to
deliver those exact bytes and one ordinary top-level `wait_threads` call for
the ACK. It must not reread or rehash the terminal, poll status, inspect logs
after terminal freeze, or hide either thread operation inside
`functions.exec`.

When closure is entirely mechanical, activate one pre-bound, one-shot receiver
with that complete summary and the exact one-action command. Its turn may not
discover a cwd or path, or separately read `AGENTS.md` or the contract. It may
discover the supported direct send tool once when necessary, then runs one
deterministic local command in the bound absolute workdir. That command
validates the exact task/dispatch/lease/terminal tuple, terminal path and
digest, callback ordering, idempotency, and scoped ownership release, and
writes one immutable ACK. Only on validation success does the receiver use one
ordinary top-level `send_message_to_thread` call to return the exact ACK to the
bound worker target and require a real message-tool receipt. It must not
interpret evidence or choose the next route. It also must not call a Codex
thread operation from `functions.exec` or emit commentary before ACK. The
long-lived research Controller receives only the compact post-closure receipt
and performs any later scientific or portfolio decision.

Telemetry is external read-only evaluation after callback. It must not enter
the worker terminal, block delivery, create a receipt-feedback protocol, or
change a scientific disposition. Measure the product window from first
executor activation through successful receiver ACK message-tool delivery,
including tool discovery, inherited context, failed attempts, and retries.
Measure the long-lived Controller's later receipt and adjudication separately.
Report input, cached input, output, and processed tokens separately; cached
input is a subset of input and none of these fields establishes billing cost.

## 8. Managed portfolio behavior

Only when managed triggers exist, load
[orchestration.md](references/orchestration.md) and
[portfolio-lanes.md](references/portfolio-lanes.md). That portfolio reference
is the single source for the preserved continuous-search, finite-HOLD, and
post-negative-diagnosis behaviors. Do not copy those policies into this router
or a worker contract.

Use [state-schema.md](references/state-schema.md) and state/lane helpers only
when their managed trigger exists. Callback/event delivery is primary; model
polling is not ordinary progress work. When no live lost-callback risk remains,
retarget a singleton to the next exact event or pause it.

## 9. External advisory and handoff

Use Pro only when an independent reasoning path can change a decision. Freeze
local evidence or the local diff first when independence matters. Continue
independent local work while an asynchronous review runs. Preserve the exact
response and verify decision-critical claims locally.

Do not send secrets, protected evidence, raw prompt/response histories, private
paths, or scientific payloads. Advisory agreement is not novelty, validity,
acceptance, or permission.

Recover from durable repository/contract/terminal authority, not chat memory.
Ignore stale epochs and duplicate terminal IDs. A handoff names source
identities, frozen boundary, remaining budget, owner, next gate, and callback
state.

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
