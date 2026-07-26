# Orchestration and authorization

Use this reference before creating work sessions, unattended work, subagent delegation, scheduled callbacks, remote jobs, recovery, or structural pivots.

## Contents

1. Roles and decision authority
2. Controller, work sessions, and subagents
3. Governance tracks and process budget
4. Advisory review budget
5. Blocker taxonomy
6. Action classes
7. Iteration contract
8. Liveness and leases
9. Progress and stall detection
10. Fresh session versus resume
11. Long-running jobs
12. Recovery
13. Stop and escalation

## Roles and decision authority

| Role | May do | Must not do |
|---|---|---|
| Owner | set charter, approve Class C actions, appoint or serve as an independent adjudicator | approve hidden protocol changes or accept a claim they produced as worker |
| Orchestrator | choose bounded next step, manage budget/state, decide routing | fabricate evidence or accept Confirmatory/publication-facing claims without independent adjudication |
| Worker | execute one direction, write artifacts/evidence | change charter or adjudicate own claims |
| Verifier | reproduce, falsify, check provenance | edit raw worker artifacts |
| Guardian | check lease, restart/nudge, report liveness | interpret results, edit evidence, report another role's conclusions |
| Adjudicator | decide challenged claims from evidence/rebuttal | rely on an uncalibrated self-score |

Use separate sessions for independence when possible. Independence means separate task context and no leaked expected answer, not merely a different reviewer persona.

A separate session of the same model is useful procedural red-teaming, but must not be described as external scientific replication. Strong independence comes from separate code paths, clean checkouts, held-out data, independent validators, different implementations, or human/external review.

## Controller, work sessions, and subagents

Use three distinct orchestration layers when the runtime provides them:

```text
owner <-> controller session
             -> persistent bounded work session
                    -> optional short-lived subagents
```

The controller session is the control plane. It maintains the Program/Epoch
ledger, admits opportunities, freezes and amends worker contracts, accounts for
cumulative budgets, registers live work, summarizes evidence, and decides
scientific routing such as `probe`, `hold`, `drop`, promotion requests, and
scoped closure. It records but does not self-accept Confirmatory or publication-
facing claims. Claim acceptance belongs to an independent adjudicator; owner
approval remains separately required only for charter and Class C actions.
Unless the owner explicitly chooses otherwise, progress questions and
scientific guidance return to this session.

A work session is a persistent, inspectable evidence-production context. It
handles exactly one admitted Problem Scout, confirmatory contract, or named
uncertainty. Its contract must state:

- question and single unresolved uncertainty;
- work type and explicit reasoning effort (`max` for audit/research/analysis
  by default; `high` for implementation/execution by default);
- source, data, leakage, and deployment boundary;
- allowed actions and tools;
- attention, time, compute, API, and external-action budget;
- expected artifacts, evidence, limitations, and validation command;
- positive, negative, and ambiguous stop/action rules;
- conditions for pause, cancellation, reclamation, or return to the controller.

Register each work session with `worker_id`, session/thread ID, Program/Epoch,
contract revision, host/worktree or repository, role, frozen uncertainty,
budget, status, artifact/state paths, last source-of-truth check, and stop,
cancel, or reclaim condition. For a persistent worker, also record
`callback_state`, `terminal_event_id`, `reclaim_deadline`, `watchdog_id`, and
`watchdog_state`. Prefer compact waits or bounded status snapshots to routine
polling. Operational details may stay in the work session; every decision-
changing result and limitation must return to the controller ledger.

At dispatch, also register one completion-return mechanism when the runtime
supports worker-initiated callbacks or event-driven thread wakeups. Prefer this
push path over periodic status polling. The callback contract must:

- target the owning controller session, not create another research session;
- identify the exact worker session and source-of-truth artifact paths;
- wake on worker completion, failure, or a request requiring owner attention;
- remain quiet and avoid extra polling while ordinary work is still active;
- read evidence and limitations before controller adjudication rather than
  forwarding the worker's verdict as accepted;
- preserve the frozen Program/Epoch budgets and action table;
- disable or pause itself after a terminal controller result or owner blocker
  is recorded, preventing duplicate adjudications.

For Codex work sessions, terminal delivery is **callback-first**. The worker
must persist and validate its terminal packet, call `send_message_to_thread`
to the registered controller, and receive a successful tool receipt before
emitting its local final response. If the push call fails or is unavailable,
the worker must report `callback_delivery=unconfirmed`; its local final is not
a completed handoff. The controller records the post-dispatch `wait_threads`
cursor and installs or retargets one low-frequency fallback that can recover a
completed final exactly once using the terminal event or final-turn ID.
Do not treat a visible `completed` thread state as proof that controller
delivery occurred.

Treat `terminal_event_id` as an idempotency key. Append delivery and
acknowledgement records rather than overwriting history. A repeated callback
with the same terminal event may refresh operational metadata but must not
create a second scientific decision. When acknowledgement is recorded, mark
the fallback watchdog `paused` or `not_required`. Use only `active`, `paused`,
or `not_required` as watchdog states; dispatch uses `active` when a fallback
exists. Delivery and acknowledgement may be separate records, but an atomic
controller read-and-ack may append `acknowledged` directly—do not manufacture a
synthetic transition merely for completeness.

Treat terminal callback handling as one controller transaction. Before
resuming unrelated owner conversation, the controller must read the evidence
and limitations, record its scoped disposition, notify the worker, pause the
completed event's watchdog, and commit exactly one next action:
`dispatch_next`, `explicit_hold`, `owner_approval_required`, or `scoped_close`.
`dispatch_next` is incomplete until the next worker record and contract
revision are registered with their own callback/watchdog state. For schema
`1.2+`, record this transaction under `controller_action`; validation must fail
for a latest terminal `delivered` state or a dangling dispatch target.

The transaction is also incomplete until the controller reconciles the global
GPU, zero-GPU, result-analysis and Pro lanes. A route-local `explicit_idle`
recommendation has no global authority. If experiments are merely queued for
GPU, dispatch the next bounded new-problem Opportunity Search unless a ready
GPU result analysis preempts it or a complete global idle proof establishes a
precise block/search-budget exhaustion. Use the compact contract in
[portfolio-lanes.md](portfolio-lanes.md), not another orchestration state tree.
Recompute queue authority from the newest validated experiment record or
durable terminal before using Wiki synthesis; stale candidate maps can nominate
an audit, but cannot launch or retain a superseded route.

A heartbeat is not a substitute for this completion callback. Use one only as
a low-frequency failure watchdog when a worker can crash, a callback can be
lost, or the runtime provides no reliable terminal event. Its checks must be
bounded and silent while the worker is ordinarily active; it must not become a
progress-report loop or the normal result-delivery path.

If the runtime has no completion-return mechanism, record a bounded manual
reclaim deadline and responsible controller in the worker registry. An
unmonitored work session whose result depends on the owner remembering to ask
for status is incomplete orchestration, not a valid handoff.

The owner may inspect or talk directly to a work session. Operational guidance
that preserves the frozen scientific contract may be executed there. A request
that changes the question, estimand, primary metric, strongest baseline, data
boundary, seed or schedule policy, budget, stopping rule, or claim boundary is
a proposed amendment only: pause affected evidence collection, send it to the
controller, record approval and budget impact, then redispatch the amended
contract. A side conversation never silently rewrites the scientific record.

Create a work session only after its candidate or named uncertainty is admitted
and its decision-complete contract is frozen. Do not create parallel generic
idea-generator sessions before `probe`, or use a new session, repository,
worker, label, or context window to reset Program/Epoch budgets. Default to one
evidence work session. Add one verifier or adversarial-audit session only when
a named procedural uncertainty cannot be resolved more cheaply; prospectively
freeze its access boundary and stop rule. Any higher concurrency must be
explicitly justified and budgeted in the charter.

Subagents are an execution layer inside an owning controller or work session.
They are appropriate for concrete, bounded, outcome-invariant tasks such as
primary-source retrieval, read-only code or algebra audits, independent metric
recomputation, or mechanical environment checks. They are not persistent
research owners and must not:

- generate parallel candidate portfolios before admission;
- change or reinterpret the frozen contract;
- adjudicate their own or their parent's claim;
- treat agreement among same-model agents as replication;
- write concurrently to the same artifact without explicit ownership or
  isolation;
- remain live merely to consume unused parallel capacity.

The owning session must reconcile subagent outputs, preserve disagreements and
limitations, and charge their attention, review, and compute to the same
Program/Epoch budget. Use a persistent work session instead when the task needs
owner-visible interaction, long-running jobs, repeated guidance, durable
recovery, an isolated context, or an auditable evidence trail across turns.

When creating or continuing any work session, pass the reasoning effort
explicitly. Raise `high` implementation/execution work to `max` when it reveals
scientific ambiguity, conflicting evidence or rules, a validity boundary, or
complex concurrency/data-integrity risk. Lower effort only when the remaining
subtask is demonstrably mechanical and outcome-independent; never downshift
unresolved scientific judgment.

This session architecture is separate from the governance-track decision. A
single bounded work session may still be Scout Lite when no durable
coordination state is needed. Cross-session unattended recovery, multiple
workers, paid execution, or a persistent lease requires a governance-admission
proof for `operating_weight=managed`; public-test, publication-facing,
expensive, or irreversible work requires `governance_track=confirmatory` and
`operating_weight=full`.

## Governance tracks and process budget

Use Scout for bounded, reversible problem-existence or falsification work. Use Confirmatory before public-test access, publication-facing comparisons, expensive or irreversible runs, or accepted claims.

For Scout:

1. default to Scout Lite; use Managed Scout only for a concrete orchestration need;
2. start an evidence clock and require the first frozen estimand within at most
   two outcome-blind engineering repairs or 20% of total Scout budget,
   whichever comes first; a repair cannot read protected outcomes or change
   model, data, split, metric, threshold, seed, baseline, or stopping policy;
3. prefer cached/cheap witnesses and one real end-to-end smoke before the evidentiary run;
4. treat unchanged-protocol code bugs as one engineering loop, not new contracts, schemas, activation states, or approval rounds;
5. implement only controls that can change the witness decision;
6. if governance-only effort exceeds scientific implementation, remove controls or bypass the framework with a direct bounded witness;
7. use one proportionate verifier that recomputes primary metrics, gates, coverage, and leakage; add stronger trust machinery only for a named threat;
8. record launch, anomaly, completion, and adjudication, not routine heartbeats.
9. freeze scientific decision invariants before evidence, but record incidental
   implementation and host identity in the final launch manifest rather than
   promoting every filename, hash, schema label, readiness record, or verifier
   identity into a gate.
10. apply the decision cadence and attention budget in
    [research-programs.md](research-programs.md); context reconstruction and
    repeated review consume research budget even when GPU cost is zero.

Before those steps, apply a **contribution lock**: one grounded problem thesis,
one primary artifact, one target estimand, one nearest-neighbor gap, and one
decision-complete problem-existence witness. Freeze the positive, negative, and
ambiguous outcome actions. Do not spend baseline-reproduction or publication-
grade verification budget until that witness passes unless reproduction is the
task itself.

Treat method-to-benchmark, benchmark-to-certificate, or mechanism-to-carrier
search as structural pivots. Close or hand off the current route, then require a
new charter and budget. Do not let a sequence of individually reasonable
follow-ups silently become a different paper.

For Confirmatory, use the full provenance, matched-budget comparison, independent verifier, evidence-to-claim mapping, and adjudication flow.

## Advisory review budget

- Use primary sources and direct experiments for resolvable questions.
- Default to at most one pre-evidence structural review and one terminal
  adjudication review per Scout.
- Require every extra review to name the unresolved decision, expected new
  information, and why a cheaper check cannot answer it.
- Do not ask a reviewer to design or adjudicate a downstream method while an
  upstream problem-existence or mechanism gate can still close the route,
  unless the review output is useful under every feasible upstream outcome.
- Treat LLM-generated reports as procedural challenges. They may change a
  claim label or reveal a missing control, but they do not add scientific
  replication or justify expanding the carrier search by themselves.

## Blocker taxonomy

Classify objections by decision impact:

- `HARD_BLOCK`: leakage or invalid evaluation; unauthorized protocol, metric, baseline, budget, or claim change; missing strongest baseline for the primary comparison; identity/reproducibility failure that could alter the result; unauthorized external/destructive action.
- `CHALLENGE`: plausible novelty overlap, alternative mechanism, secondary ablation, engineering risk, or incomplete generalization. Continue the cheapest discriminating Scout.
- `POLISH`: documentation or presentation work that cannot change the current gate.

Only `HARD_BLOCK` stops evidence collection. Reclassify with a timestamped rationale when new information changes decision impact.

## Action classes

### Class A: routine and reversible

Execute without additional approval when in scope:

- read local/public sources;
- edit the task workspace;
- run local tests, lint, builds, parsers, or dry runs;
- inspect logs, queues, APIs, and read-only external state;
- record state and produce reports.
- repair and retest an in-scope implementation bug without changing the frozen scientific protocol or budget;

### Class B: preauthorized external execution

Execute only when the charter names the action type, target, and budget:

- submit or resubmit a bounded compute job;
- call paid APIs within the recorded cap;
- write to an isolated remote experiment directory;
- restart a failed worker or scheduled callback.

Record the authorization, command or action, cost/compute estimate, ID, logs, and rollback or stop method.

### Class C: explicit approval required

Pause before:

- changing the research question, hypothesis class, data split, primary metric, seed policy, baseline, stopping rule, or claim boundary;
- increasing time, money, token, API, or compute budgets;
- using credentials for a new purpose;
- changing production or shared state, publishing, merging, messaging third parties, or creating external commitments;
- deleting, overwriting, resetting, force-pushing, or performing other destructive actions;
- proceeding when ambiguity would materially change the objective or evidence interpretation.

Continue only action-admitted, outcome-invariant work while approval is
pending. Work is not worthwhile merely because it is safe or non-biasing.

An owner may give a prospective **standing delegation** for a narrow Class-C
repair family. Treat it as preapproval, not as a waiver of scientific control.
For pre-outcome data-identity, collision, or leakage repairs, the controller may
approve and continue without another owner message only when every condition is
true:

- the defect and repair are determined before any linked scientific outcome is
  accessed;
- the repair is deterministic, source-traceable, fail-closed, and strengthens
  validity rather than optimizing performance;
- it stays inside the frozen source/data universe;
- actor, estimand, planned sample counts, seed policy, primary metrics,
  strongest baseline, budget, stopping rule, analysis, outcome table, and claim
  boundary remain unchanged;
- the controller records one dated amendment, validation conditions, and the
  standing-authorization basis before execution.

Do not ask the owner again when all delegated conditions hold; resume the same
work session and preserve the cumulative budget. If any condition fails or is
ambiguous, standing delegation does not apply and explicit approval remains
required. It never covers public-test access, outcome-conditioned protocol
changes, budget increases, destructive/shared/production actions,
publication/third-party commitments, or promotion to another governance stage.

Changing `governance_track` is a charter amendment. Promotion from Scout to Confirmatory is expected when a frozen promotion gate passes; downgrading is not allowed for actions or evidence already meeting Confirmatory triggers.

## Iteration contract

Each worker receives only:

- frozen charter and applicable `AGENTS.md`;
- one direction and its non-duplication rationale;
- bounded budget and permitted tools;
- expected deliverables and validation;
- paths for run manifest, artifacts, and state records.

Require the worker to return evidence and limitations, not a success verdict.

## Liveness and leases

- Use `state/heartbeat.json` only for liveness.
- Give one worker a time-bounded lease; include `runner_id`, `last_seen_at`, and `lease_expires_at`.
- Use atomic updates through `scripts/update_state.py heartbeat`.
- A stale lease permits restart or attention, not a scientific pivot.
- Prevent duplicate execution by checking the active run ID and lease before restart.

## Progress and stall detection

Scientific progress means at least one of:

- new verified evidence;
- falsified hypothesis or narrowed uncertainty;
- justified replication or robustness result;
- resolved implementation/data/evaluation defect;
- stronger provenance or claim-boundary correction.

Mark an iteration `stale` only when none applies. After two consecutive stale iterations:

1. audit environment and evaluation validity;
2. compare the proposed direction fingerprint with prior directions;
3. propose a structural change, opposite hypothesis, or independent reproduction;
4. request a charter amendment if the pivot changes frozen protocol.

Do not force novelty when replication is required. Do not treat waiting for a scheduler, download, reviewer, or user approval as stale research.

## Fresh session versus resume

Prefer a fresh worker when reducing anchoring, testing an independent reproduction, or recovering from context saturation. Resume when continuity is required by an active terminal, browser state, uncommitted workspace, long-running job, or external transaction. In both cases, inject durable state and verify live state before acting.

## Long-running jobs

After submission:

1. verify that the scheduler or process accepted the job;
2. record job ID, environment, code/config version, logs, artifacts, expected completion, and check/cancel commands;
3. mark the task `waiting_external` when no immediate work remains;
4. return control instead of continuously polling, unless monitoring was explicitly requested;
5. on later inspection, query the source of truth before interpreting status.
6. during the wait, do not prebuild downstream stages or broaden the portfolio;
   perform only work that remains useful under every feasible job outcome.

## Recovery

On callback or context recovery:

1. read the latest compact decision capsule and its referenced durable
   artifacts; do not rebuild the scientific state from full transcripts unless
   a contradiction requires it;
2. refresh the current worker heartbeat;
3. inspect task status, lease, active run, scheduler/process state, and recent events;
4. reconcile contradictions in favor of source-of-truth systems and append a correction event;
5. restart only after proving the previous worker/job is not still active;
6. preserve the same charter unless an approved amendment exists.

## Stop and escalation

Stop execution and report when a Class C decision is required, budget is exhausted, validation shows the protocol is invalid, the same concrete blocker survives documented recovery attempts, or continuing would create unsupported claims. A stop is not a completed research objective; label the status accurately.

Do not use `NO-GO` as an orchestration shortcut. Close only the exact estimand/carrier supported by a preserving formal reduction, a replicated high-confidence negative against the strongest baseline, or a preregistered minimum-effect failure. Otherwise use `challenged`, `hold`, `inconclusive`, or `carrier-level stop` and preserve the reopening condition.
