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
| Controller | route bounded work, freeze authority, accept evidence, choose the next gate | perform the Explorer/Audit/Executor's scientific semantics or accept a Confirmatory/publication claim without independent adjudication |
| Explorer | complete one source-to-`PROBE` loop and return at most one admitted candidate | split source, brief, locator, or packet checks across workers; accept its own claim |
| Audit | complete the whole `R0` reduction/readiness decision in one owner and one terminal | delegate individual predicates to successor Audits; execute scientific outcomes |
| Executor | implement or run only after one complete implementation/execution contract is frozen | redefine the question, gate, estimand, baseline, exposure, or scientific contract |

Keep role separation at decision boundaries, not at every file operation. A
packet, locator, sidecar, hash, license lookup, or deterministic safe-source
preflight stays inside the current Explorer or Audit owner and is never a new
research role or session. Same-model separation is procedural red-teaming, not
external scientific replication. Confirmatory claim acceptance still requires
an independent adjudicator or owner who did not produce the decisive evidence.

While one Audit runs, the Explorer may search a substantively different
problem space when no protected result analysis is pending, no real GPU
saturation blocks useful work, and the two owners do not share write authority.
A single Audit is not a global serialization lock.

## Controller, work sessions, and subagents

Use three distinct orchestration layers when the runtime provides them:

```text
owner <-> controller session
             -> persistent bounded work session
                    -> optional short-lived subagents
```

The Controller is the routing and acceptance plane. It admits opportunities,
freezes or amends contracts, accounts for existing budgets, accepts returned
evidence, and chooses `probe`, `hold`, `drop`, promotion, or scoped closure. It
does not reproduce the Explorer's source synthesis, the Audit's R0 semantics,
or the Executor's implementation. Program/Epoch and shared ledgers exist only
when the route already has a real Managed or repeated-Program trigger.

A work session is a persistent, inspectable evidence-production context used
only when a session boundary has decision value. An Explorer receives one
complete source-to-`PROBE` loop; an Audit receives the complete `R0`; an
Executor receives one frozen implementation contract. Its contract states:

- question and single unresolved uncertainty;
- exact model family and reasoning effort from the routing matrix below;
- source, data, leakage, and deployment boundary;
- allowed actions and tools;
- attention, time, compute, API, and external-action budget;
- expected artifacts, evidence, limitations, and validation command;
- positive, negative, and ambiguous stop/action rules;
- conditions for pause, cancellation, reclamation, or return to the controller.

Before creating or reusing a persistent Managed worker, verify the runtime's
actual saved Project ID, cwd, repository, branch/remote, candidate/version,
canonical role, and owner task. Echo them in the dispatch record. A projectless
task or a worker whose Project/cwd/repository binding cannot be verified is
never canonical and receives no scientific or shared-state authority. If the
runtime exposes no Project/session/pin API, keep bounded work in the current
verified in-Project task or report the operational limitation; do not translate
it into `CARRIER_STOP`, scientific `HOLD`, or permission to create a projectless
substitute.

Keep only the live Managed objective pinned: the sole Controller and each
active canonical Explorer, Audit, or Executor whose terminal needs Controller
follow-up. Pin a verified successor at activation; unpin its predecessor only
after terminal acceptance and routing. Unpin completed, superseded, archived,
or merely reusable sessions, and pin them again only when a real Managed
objective reactivates. Lite and Pro advisory tasks are never auto-pinned.
At every Controller resume, activation, reuse, material state change, terminal
absorption and pre-final audit, recompute this set from live thread state and
call `set_thread_pinned`; do not trust an earlier message or desired-state
record as proof that the sidebar changed. An API failure is an explicit
operational limitation, not permission to claim synchronization.

Give every persistent Controller, Explorer, Audit, or Executor session the canonical sidebar title
`<Role> · <candidate-or-bounded-scope> · <STATE>`. `Role` is one of
`Controller|Explorer|Audit|Executor`; `STATE` is one of
`ACTIVE|WAITING_EXTERNAL|HOLD|BLOCKED|COMPLETE`. Use a stable human-readable
candidate/version, or a bounded scope when none exists; do not substitute raw
task, dispatch, lease, terminal, or hash IDs for the scope. Set the title at
verified activation, update it on reuse or a material phase/state change, and
remove stale `ACTIVE` at terminal absorption. Titles are navigation only, not
authority, evidence, a registry, or a lifecycle; exact IDs remain in existing
durable records.
Use `set_thread_title` when the runtime exposes it, and verify the live title
alongside the pin set. Never leave a completed or waiting role titled `ACTIVE`.

For Lite/local work, the task itself is the ownership record; do not create a
new Program, lease, lane, watchdog, or callback state. When the work belongs to
an existing repeated Program, reuse its compact planning record without adding
Managed state. Only a persistent Managed worker records the minimum live
identity, contract revision, owner, budget, status, source-of-truth path,
reclaim condition, and completion event needed for its actual coordination
risk. Prefer event delivery and bounded snapshots to polling.

At dispatch, also register one completion-return mechanism when the runtime
supports worker-initiated callbacks or event-driven thread wakeups. Prefer this
push path over periodic status polling. The callback contract must:

- target the owning controller session, not create another research session;
- identify the exact worker session and source-of-truth artifact paths;
- wake on worker completion, failure, or a request requiring owner attention;
- remain quiet and avoid extra polling while ordinary work is still active;
- read evidence and limitations before controller adjudication rather than
  forwarding the worker's verdict as accepted;
- preserve hard per-job and per-attempt ceilings plus the prospectively
  recorded Program/Epoch GPU planning envelope and authorized staged action
  table;
- disable or pause itself after a terminal controller result or owner blocker
  is recorded, preventing duplicate adjudications.

Dispatch intent is not liveness. Persist the successful dispatch receipt, then
take one compact post-dispatch task snapshot. Record a worker as active only if
that evidence echoes the current
`task_id + owner_thread_id + dispatch_id + lease_epoch`. The same tuple binds
explicit reasoning effort, terminal callback and an absolute
next-progress/reclaim deadline. Generic thread activity is insufficient. One
owner holds at most one current task lease. The living worker registry stores
the maximum issued epoch and exact current lease. The lane reconciler reads and
atomically advances one locked external chronology watermark, so a later
snapshot cannot lower the prior floor by rewriting its own fields. When the deadline is due, recovery evidence must echo the same
tuple; once redispatch occurs, revoke the old lease and install the activated
higher epoch before calling the lane running. Ignore late stale-epoch events.

Use callbacks only for persistent Managed work, never for a user-visible Lite
task. Treat delivery as **at-least-once wake plus idempotent exactly-once
effect**, not exactly-once transport through every layer.

Before dispatch, register one bounded fallback that can recover the frozen
terminal from its event or final-turn ID without reading protected evidence.
That fallback is the only retry authority; the worker never owns retry.
Record it in existing durable Controller state that survives Controller
restart; volatile memory alone is not fallback registration. Do not create a
new registry, outbox, or receipt family solely for callback recovery.

The worker freezes one terminal, then makes one ordinary top-level
`send_message_to_thread` call with the runtime's bounded timeout. A successful
tool receipt releases worker ownership and permits the local final immediately;
the worker does not wait for `RECEIPT_ONLY`, `FINAL_ACK`, or a receiver ping.
If the call is unavailable, times out, or returns an ambiguous result, record
`callback_delivery=unconfirmed`, emit the local final, and do not resend. The
controller's registered fallback may recover that terminal once from its
`terminal_event_id` or final-turn ID.

Treat `terminal_event_id` as the idempotency key for Controller effects. Bind a
delivered event to its source `task_id + owner_thread_id + dispatch_id +
lease_epoch` and terminal digest. The first valid delivery may create one
scientific or shared-state effect; every duplicate creates zero additional
effects. Do not append transport history merely to prove that a duplicate was
seen. An ACK is asynchronous and optional except when the Controller must
certify a true shared-state commit; even then it closes the Controller
transaction and does not block the user-visible worker. Pause or remove a
fallback after the event has been recovered or processed.

Do not treat a visible `completed` thread state as proof that delivery occurred.
Do not turn send timeout into an infinite wait, a retry loop, a fresh receiver,
or a second worker.

For a persistent Managed event, the Controller reads the evidence and
limitations, records its scoped disposition, closes any real watchdog, and
commits exactly one next action: `dispatch_next`, `explicit_hold`,
`owner_approval_required`, or `scoped_close`. The released worker is not part
of this transaction and needs no `FINAL_ACK` or receiver ping.
`dispatch_next` is incomplete until the next worker record and contract
revision are registered with their own callback/watchdog state. A latest
terminal `delivered` state is complete worker delivery. Record
`controller_action` only when a true shared-state commit is needed; validation
rejects only a malformed transaction or dangling dispatch target, never the
absence of an ACK.

`dispatch_next` additionally requires the successful dispatch receipt and
matching task-bound activation/callback lease evidence. `explicit_hold` names
one blocker, its observer, event/absolute-check trigger, and next evidence
action in existing task state; it does not create a backlog or lane merely to
certify the hold.

Reconcile only the shared resources actually touched by the Managed event. A
GPU/remote completion may require its run, ownership and result-analysis queue;
a local source or R0 completion requires none of the GPU, zero-GPU, Pro, lane,
dashboard, or global-idle machinery. Load
[portfolio-lanes.md](portfolio-lanes.md) only when a real shared lane changes.

A heartbeat is not a substitute for this completion callback. Use one only as
a low-frequency failure watchdog when a worker can crash, a callback can be
lost, or the runtime provides no reliable terminal event. Its checks must be
bounded and silent while the worker is ordinarily active; it must not become a
progress-report loop or the normal result-delivery path.

Automation is a user-visible mutation. Use it only when an independently real
remote/unattended Managed trigger has no native completion return. Reuse the
one existing bounded fallback by durable ID, change nothing when effective
fields already match, and never create polling or a second monitor for advisory,
Lite, source-search, R0, dashboard, or capacity state.

If the runtime has no completion-return mechanism, record a bounded manual
reclaim deadline and responsible controller in the worker registry. An
unmonitored work session whose result depends on the owner remembering to ask
for status is incomplete orchestration, not a valid handoff.

The owner may inspect or talk directly to a work session. Operational guidance
that preserves the frozen scientific contract may be executed there. A request
that changes the question, estimand, primary metric, strongest baseline, data
boundary, seed or schedule policy, a hard per-job/per-attempt, paid-service, or
maximum staged ceiling, stopping rule, or claim boundary is a proposed
amendment only: pause affected evidence collection, send it to the controller,
record approval and budget impact, then redispatch the amended contract.
Updating the aggregate GPU planning envelope alone is a prospective controller
planning action, not a scientific-contract amendment, provided no hard ceiling
or protected-data gate changes. Launching the next complete paired-seed tranche
already admitted by the frozen action table and maximum staged ceiling is not
another amendment or owner-approval round. A side conversation never silently
rewrites the scientific record.

Create a work session only after its candidate or named uncertainty is admitted
and its decision-complete contract is frozen. Do not create parallel generic
idea-generator sessions before `probe`, or use a new session, repository,
worker, label, or context window to reset Program/Epoch budgets. Default to one
evidence work session per admitted Scout or frozen contract. Multiple
independently frozen, launch-ready portfolio entries may each retain one owner
and receive breadth-first initial tranches; this does not authorize parallel
generic idea generation. Add one verifier or adversarial-audit session only
when a named procedural uncertainty cannot be resolved more cheaply;
prospectively freeze its access boundary and stop rule. Any higher concurrency
must be explicitly justified and budgeted in the charter.

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

When creating or continuing a work session, bind model family and reasoning
effort explicitly. The route is sticky for the active objective, not forever
for the reusable session and not independently for every turn or microphase:

- `gpt-5.6-sol` + `max`: formulation, Opportunity Search, sources/neighbors,
  contracts, Audits, causal/statistical/algebraic reasoning, protected-result
  interpretation, route decisions, closure, and adjudication;
- `gpt-5.6-sol` + `xhigh`: first real-carrier Scout Executor, complex
  implementation, remote integration/debugging, and evidence-bearing execution;
- `gpt-5.6-sol` + `high`: demonstrably bounded frozen-contract implementation,
  tests, deterministic integration, and routine execution; and
- `gpt-5.6-luna` + `max`: high-volume deterministic rehashing, sync, packaging,
  unchanged-contract reruns, or simple outcome-invariant repair only.

Do not switch model while one objective is in flight merely because its final
steps look mechanical; finish its terminal with the selected route. Reclassify
only after terminal absorption or an explicit redispatch creates a separately
bounded successor. If that successor is purely Luna-class work, resume the same
canonical session with `gpt-5.6-luna` + `max`. Do not create an Implementer,
Runner, second owner, or new session solely to avoid a model switch. Split roles
only for a real ownership, independence, exposure, or authority boundary.

Raise an Executor to `gpt-5.6-sol` + `max` when authority, evidence validity,
concurrency, data integrity, exposure, or scientific interpretation becomes
ambiguous. `luna max` never substitutes for `sol xhigh/max` scientific work. If
a named tier is unavailable, use the nearest available `gpt-5.6-sol` tier and
report the substitution before protected/scientific work.

This session architecture is separate from the governance-track decision. A
short-lived bounded subagent inside one user-visible owner may remain Lite; a
persistent canonical work session needs a real Managed trigger. Cross-session
unattended recovery, multiple write-capable workers, paid execution, or a
persistent lease requires a governance-admission proof for
`operating_weight=managed`; public-test,
publication-facing, expensive, or irreversible work requires
`governance_track=confirmatory` plus explicit authority, and uses Managed only
when a Managed trigger is actually present.

## Governance tracks and process budget

Use Scout for bounded, reversible problem-existence or falsification work. Use Confirmatory before public-test access, publication-facing comparisons, expensive or irreversible runs, or accepted claims.

For Scout:

1. default to Scout Lite; use Managed Scout only for a concrete orchestration need;
2. start an evidence clock and target the first frozen estimand before either
   two outcome-blind engineering repairs or governance-only work reaching 20%
   of total Scout attention. Either threshold is an efficiency alarm, not an
   automatic scientific stop; a repair cannot read protected outcomes or
   change model, data, split, metric, threshold, seed policy, baseline, or
   stopping policy;
3. prefer cached/cheap witnesses and one real end-to-end smoke before the evidentiary run;
4. treat unchanged-protocol code bugs as one engineering loop, not new contracts, schemas, activation states, or approval rounds;
5. implement only controls that can change the witness decision;
6. if governance-only effort exceeds scientific implementation, remove
   nonessential controls and execute the direct bounded witness under the same
   evidence, authority, exposure, fairness, and budget hard controls;
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
- update an aggregate GPU planning envelope prospectively while remaining
  inside every hard ceiling and frozen staged authorization;
- repair and retest an in-scope implementation bug without changing the frozen scientific protocol or budget;

### Class B: preauthorized external execution

Execute only when the charter names the action type, target, and budget:

- submit or resubmit a bounded compute job;
- launch a later complete paired-seed tranche admitted by the frozen staged
  action table and maximum staged ceiling;
- call paid APIs within the recorded cap;
- write to an isolated remote experiment directory;
- restart a failed worker or scheduled callback.

Record the authorization, command or action, cost/compute estimate, ID, logs, and rollback or stop method.

### Class C: explicit approval required

Pause before:

- changing the research question, hypothesis class, data split, primary metric, seed policy, baseline, stopping rule, or claim boundary;
- increasing hard time, money, token, API, per-job/per-attempt compute, or
  maximum staged ceilings;
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
changes, increases beyond a hard ceiling or prospectively authorized maximum
staged ceiling, destructive/shared/production actions, publication/third-party
commitments, or promotion to another governance stage. An ordinary later
tranche already admitted inside that ceiling is not a budget increase.

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

Use a lease only when concurrent duplicate execution or a persistent remote
write is a real risk. Lite/local Explorer, Audit, deterministic preparation,
and user-visible Executor tasks have no lease or heartbeat. For a Managed
lease, keep only runner identity, source-of-truth run ID, expiry/reclaim rule,
and atomic ownership update. A stale lease permits attention or recovery, never
a scientific pivot; prove the prior run is inactive before replacement.

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

For the same idea, resume when continuity is required by an active terminal,
browser state, uncommitted workspace, long-running job, or external
transaction; compact only when decision-relevant history has become materially
redundant. On an idea switch, reuse the canonical role session only after a
runtime-supported compact/reset succeeds and its isolation is verifiable.
Otherwise open one fresh session, transfer the canonical role binding, and
close/archive the prior session so no duplicate owner remains. Never treat
record selection as context isolation. A session that has seen bytes forbidden
by a strict-blind contract cannot become an eligible strict-blind owner through
compaction. Prefer a fresh worker for independent reproduction or anti-anchoring.
In every case, inject only the minimal durable state and verify live state before
acting.

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

Stop execution and report when a Class C decision is required; a hard
per-job/per-attempt or paid-service ceiling, protected-data gate, or search or
attention budget is exhausted; validation shows the protocol is invalid; the
same concrete blocker survives documented recovery attempts; or continuing
would create unsupported claims. Exhaustion of an aggregate Program/portfolio
GPU planning envelope alone routes to `HOLD`, replanning, or prospective
amendment; it is not an automatic scientific stop. A stop is not a completed
research objective; label the status accurately.

Do not use `NO-GO` as an orchestration shortcut. Close only the exact estimand/carrier supported by a preserving formal reduction, a replicated high-confidence negative against the strongest baseline, or a preregistered minimum-effect failure. Otherwise use `challenged`, `hold`, `inconclusive`, or `carrier-level stop` and preserve the reopening condition.
