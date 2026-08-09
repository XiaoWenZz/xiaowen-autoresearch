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

External Pro remains inside the current scientific role rather than the
Controller. The Controller may decide that a named ambiguity merits one
bounded advisory, but it only routes the request and later absorbs the owner's
locally verified decision record. Explorer owns discovery/neighbor prompts;
an eligible Audit owns contract, estimand, signal-versus-implementation,
contribution, Confirmation and closure prompts. Executor may not use Pro to
reinterpret evidence or change a frozen contract. Pro creates no role, task,
lease, lane, pin or scientific authority. A minimal outcome-free read
obligation in the Controller snapshot is the sole exception; it tracks delivery
to the eligible owner, not the Pro conversation's scientific content or state.

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
objective reactivates. Lite and Pro advisory tasks are never auto-pinned. The
sole standing exception is the user-designated canonical `Audit · Workflow
Evolution` session: keep it pinned while active, idle, or `COMPLETE`, and unpin
only after explicit retirement, verified permanent ownership transfer, or the
user's request. Its pin is navigation/availability only and creates no Managed
role, lease, authority, heartbeat, state entry, or right to block science.
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

For a persistent Managed event, the Controller performs atomic terminal
absorption: read the evidence and limitations, record the scoped disposition,
close any real watchdog, and commit exactly one next action: `dispatch_next`,
`explicit_hold`, `owner_approval_required`, or `scoped_close`. This applies to
every actionable terminal, including `PROBE`, `PASS_R0*`, `PASS_R1*`,
`PASS_R2*`, `PROFILE_*`, `ENGINEERING_*`, `CONTRACT_CONFLICT`,
`HOLD_ACCESS_CHANNEL`, and `CARRIER_STOP`. The released worker is not part of
this transaction and needs no `FINAL_ACK` or receiver ping.
`dispatch_next` is incomplete until the next worker record and contract
revision are registered with their own callback/watchdog state. A latest
terminal `delivered` state is complete worker delivery. Record
`controller_action` only when a true shared-state commit is needed; validation
rejects only a malformed transaction or dangling dispatch target, never the
absence of an ACK.

`dispatch_next` additionally requires the successful dispatch receipt and
matching task-bound activation/callback lease evidence. Before that one send,
Controller derives the planned post-CAS minimum revision and includes it with
the exact successor objective, owner/role, six-field completion binding,
predecessor terminal event, and either one exact prospective remote-job
projection or an explicit no-remote-job assertion. The destination first emits
`PASS_MODEL_ROUTE`, then uses the read-only `await-successor-activation` command
with that same job expectation. A lower revision is a bounded transient wait;
at or above the floor, objective, owner, role, binding, absorbed event, managed
role and job expectation must all match or fail closed. No repository, remote,
GPU, model/data/protected read, write, terminal, final or objective decision
precedes PASS. Controller performs `activate-successor` immediately after the
sole dispatch receipt, atomically prebinding the prospective job when present,
without a destination ACK, so there is no read-before-CAS finalization and no
extra handoff roundtrip. The Controller may not send a user-visible status/final
before that activation exists. A boilerplate
“Controller decides whether” is not `owner_approval_required` when standing
delegation already covers the frozen bounded action. `explicit_hold` names one
real blocker, its observer, event/absolute-check trigger, and next evidence
action in existing task state; it does not create a backlog or lane merely to
certify the hold.

On PASS, `await-successor-activation` returns one machine-derived
`terminal_identity_projection`. The producer starts its terminal object from
that projection instead of reconstructing identity fields: every role copies
the exact nested six-field `completion_binding`, and an Executor also copies
the returned `startup_chain_authority`, including explicit JSON `null`. This
fuses prospective terminal identity into the existing activation barrier; it
creates no generator, sidecar, validator or extra roundtrip. Independent body
fields remain the producer's responsibility, and callback preparation still
reparses the immutable file and fails closed on any projection drift.

Treat `ENGINEERING_*`, `CONTRACT_CONFLICT`, `HOLD_ACCESS_CHANNEL`, and
`CARRIER_STOP` as worker-local terminals, never Controller route decisions. When the candidate
remains open or `UNTESTED`, terminal absorption is incomplete until the
Controller records exactly one of: a successfully activated same-idea
successor (`DELEGATED`/`dispatch_next`), or one finite genuine external/authority
blocker with reopening fact, observer, trigger or absolute `next_check_at`, and
`resolution_deadline` (`BLOCKED`/`explicit_hold`). `DONE` requires the exact
candidate scope to be scientifically `CLOSED`; an internal engineering,
carrier, contract, source/code/algebra, estimand/identification, weak-signal or
contribution gap must be routed to an owner, never stored as an open archive. A worker recommendation
such as “keep open,” “do not launch,” “no automatic successor,” or its
`NEXT_ACTION` cannot discharge this Controller duty. `OPEN_WITHOUT_OWNER` is an
invalid lifecycle state, not an idle candidate.

The core invariant is **open means owned**. If `candidate_state != CLOSED`, one
decision-complete Explorer, Audit, or Executor owns the cheapest current action
unless progress depends on a finite genuine external fact or unavailable
authority. At material gates, persistent bottlenecks, or high-risk routes,
proactively route one bounded Pro falsification/cross-check through the eligible
Explorer/Audit even when a local answer exists, then require local verification.
Controller never authors or reads the scientific advisory; Pro
is not an owner or authority. If no bounded action and no external fact can
change the scoped decision, perform admissible scientific close/route instead
of leaving `OPEN/DONE`.

An attributed `SCOUT_SIGNAL` also remains open until the same Controller turn
binds one Contribution Gate owner/action or a genuine blocker with reopening
fact, observer, and trigger. The signal never self-promotes, but a user-visible
status/final cannot leave it ownerless between Scout adjudication and the Gate.

Reconcile only the shared resources actually touched by the Managed event. A
GPU/remote completion may require its run, ownership and result-analysis queue;
a local source or R0 completion requires none of the GPU, zero-GPU, Pro, lane,
dashboard, or global-idle machinery. Load
[portfolio-lanes.md](portfolio-lanes.md) only when a real shared lane changes.

The persistent heartbeat is a native recovery turn of the same singleton
Controller thread, not a second Controller and not a notification-only role.
The desktop scheduler resumes that existing thread when it is idle, with its
Controller tools and project binding. Therefore one heartbeat turn may and
must finish Controller-only work: register and verify a prebound terminal,
absorb it, dispatch the decision-complete successor, confirm matching
activation, reconcile title/pin/cursor, and commit the state CAS. It may route
an unresolved decision to Audit, but it must not redo Explorer/Audit/Executor
semantics, independently interpret protected science, invent evidence, or
create filler.

This preserves the already user-authorized desktop singleton; it does not
authorize installing one where none exists. Without that prior authorization,
terminal callbacks and explicit Controller resume remain the recovery path.

Maintain exactly one persistent Controller-global continuity heartbeat through
idle periods and worker/job completions. Adjust its cadence in place; do not
create a faster or slower duplicate, external watcher, temporary App Server,
Stop/UserPrompt hook, or second automation. Its checks remain bounded and
silent while work is healthy. Add the exact process/job/output/ETA check only
for a live remote job without native wake, clear only that job entry at
terminal, and never delete the global automation. A concept explanation, side
question, or unrelated user-visible final does not cancel pending Controller
work; the next native heartbeat resumes it idempotently within the configured
cadence.

For a Managed Executor authorized to submit one unattended remote job, bind the
complete existing `remote_jobs` record in the same `activate-successor` CAS and
make the destination activation barrier verify that exact projection before
launch. The record begins `monitor_state=ACTIVE` and
`wake_delivery={state:NONE, claim_token:null, observation_id:null}`. A successor
with no planned job verifies the explicit no-job case. Do not defer registration
until after submission or reconstruct it after completion as the normal route;
generic Controller replacement remains only bounded legacy recovery. This is
one existing state projection and one CAS, not a new receipt, callback, owner or
handoff. A prospectively bound `ACTIVE/NONE` record is a monitoring obligation,
not evidence that submission already occurred: before its `late_threshold`, an
absent unit and absent expected files alone create zero terminal or wake effect.
At the threshold, wake the same owner to reconcile launch identity rather than
inventing a scientific or job outcome.

Keep that heartbeat prompt static. Store only operational pointers in the
rebuildable Controller control snapshot: revision/checksum, active objectives,
canonical role threads and cursors, lifecycle/next action, prebound
`completion_binding`, identity-only `pending_absorptions`, remote job identity,
ETA/late threshold, bounded file-presence expectations, minimal Pro read
obligations, and absorbed terminal IDs. `completion_binding` freezes task,
dispatch, lease epoch, contract revision, terminal event ID and immutable
terminal path before delegation. A terminal observation verifies that binding
and the file envelope, sets `TERMINAL_PENDING_ABSORPTION`, and keeps the old
cursor behind the terminal until the same Controller verifies and absorbs it.
The snapshot never stores terminal scientific prose or a recommended
successor. A Pro read obligation contains only the
objective/conversation/reader identities, submit/update timestamps,
`scope_revision`, `scope_sha256`, `batch_mode=NON_BLOCKING|BLOCKING_HIGH_RISK`,
nullable `blocking_gate_id`, response-observed metadata and
`NONE -> CLAIMED -> SENT` wake delivery. `NON_BLOCKING` is the default and may
not create a blocked objective or release its local owner. A
`BLOCKING_HIGH_RISK` batch must match one exact objective gate created in an
earlier snapshot revision. Legacy advisory shapes are invalid for validation,
replacement, migration, or wake delivery. The snapshot contains no prompt,
reply, summary, disposition, source claim or scientific interpretation. It is
a cache, never scientific/shared-state authority; raw
outcomes, metrics, predictions, claims, secrets, and model/data payloads are
forbidden. Thread APIs, immutable terminals, and scheduler/process state remain
the facts from which a missing or corrupt snapshot is rebuilt.

Controller updates use compare-and-swap revision, checksum verification, fsync,
and atomic replace. Every canonical read takes a shared process lock on the
stable control-directory inode; every normal, migration and recovery write
takes the exclusive lock, rereads revision/checksum inside it, validates the
transition and commits the state/checksum pair before release. Thus the narrow
Executor startup-record writer and Controller cannot both accept the same
revision. Terminal absorption, successor activation, pin/title
reconciliation, and the matching snapshot revision form one Controller
transaction. On a terminal, pass the delivered callback's `final_bytes` and
`final_sha256` to `observe-terminal`; it reparses the file and rejects any
replacement before state mutation. Validate the decision-complete boundary, then call
`verify-pending-terminal`. After a successful dispatch receipt and matching activation, use
the state tool's `activate-successor` CAS to absorb the exact terminal, replace
the old Managed owner, bind the activated successor and clear only explicitly
named finished jobs/advisories. `close-objective` and `absorb-and-block` require
the same verified pending identity. Never represent a handoff as separate
cursor, terminal and owner updates. The heartbeat reads
the snapshot first, calls one thread-list operation, batch-waits only the named
active roles, and labels every cursor update `NON_TERMINAL` or `TERMINAL`.
Every `advance-cursors` update carries `source_turn_state=IN_PROGRESS|FINAL`.
It rejects a terminal cursor unless its exact `terminal_event_id` is already in
`absorbed_terminal_event_ids`; an unseen, unidentified, or unabsorbed final
stays before the cursor while that same Controller completes the full lifecycle
transaction. It also rejects `FINAL + NON_TERMINAL` from an Executor unless
exactly one same-objective/same-owner `ACTIVE/NONE` remote job is already in
`remote_jobs`. The Controller then keeps the cursor before that final and sends
one same-owner recovery wake to seal the prebound terminal; it does not wait for
the user, invent a job after completion as the normal path, or create a new
Executor. A legitimate long-job return advances only against its prospectively
registered job. A crash before absorption
leaves the pending record and cursor barrier for the next heartbeat. A crash
around successor dispatch is reconciled from the bound dispatch ID, runtime
receipt and matching activation before any retry; ambiguous delivery is never
blindly resent. It advances accepted cursors only through a bounded CAS command,
and executes only the fixed systemd/file-presence monitor shape. From the same
single thread-list result it may compare a named Pro conversation's `updatedAt`
against its post-submit baseline after `not_before`; on an idle newer response
it claims one advisory wake, sends only response-ready metadata to the named
Explorer/Audit, and marks `SENT`. It never opens the page or reads the response.
Ambiguous `CLAIMED` is never resent. Controller removes the obligation only
after `SENT` delivery and the owner's locally verified terminal are absorbed in
the exact gated transition. Candidate plus scope hash is unique across active
and absorbed batches; changing a free revision cannot resubmit it. If a `SENT`
reader becomes idle or completes while the obligation remains, the singleton
wakes Controller to recover/absorb that record; it does not read or interpret it.
Only `claim-advisory-wake` may perform `AWAITING_RESPONSE/NONE ->
RESPONSE_OBSERVED/CLAIMED`, and only `complete-advisory-wake` may perform
`CLAIMED -> SENT`; generic replacement and initial snapshot creation may not
seed or advance those observations.

An interactive authentication, credential, or approval boundary with its
existing UI or PTY still live is not a completed Executor turn. Show the exact
user action in commentary and keep the same task, turn, session, objective,
terminal binding, and PTY `IN_PROGRESS`; do not emit final, close the PTY,
invent a remote job, poll, or create a replacement owner while awaiting the
user. Continue in that same turn after the user acts. If the runtime cannot
preserve an in-progress turn, seal the prebound terminal with the genuine
external-authority block and an exact reopen trigger; never substitute
`FINAL + NON_TERMINAL`. If such a malformed final is nevertheless observed,
Controller keeps the cursor before it and sends only the existing same-owner
recovery wake.
An observed `NON_BLOCKING` batch may use the standalone
`absorb-nonblocking-advisory` CAS so its local terminal is absorbed without
changing objective lifecycle. `BLOCKING_HIGH_RISK` may never use that command.

For a pre-utility engineering terminal, decision-complete validation also
requires the bounded-root inventory and allowlisted reason defined below. Keep
that inventory only in the immutable terminal; the Controller snapshot stores
its identity, never the diagnostic prose. A terminal that supplies only a
generic `ENGINEERING_INVALID`, `CARRIER_STOP`, `PRECHECK_FAILED`, `UNKNOWN`, or
similar label is `MALFORMED_TERMINAL`: it creates zero scientific, lifecycle,
blocker, budget-reset, or successor effect. Keep the cursor before it and use
the existing recovery path for the same objective; never dispatch a fresh
Executor or create a new attempt merely because the generic terminal exists.

Keep the Controller logically singleton while allowing physical context
rollover. A worker callback carries only the compact receipt fields
`terminal_event_id`, `objective_id`, `owner_thread_id`, immutable
`path/bytes/sha256`, `disposition`, `next_action`, and nullable
`fresh_thread_reason`; that reason is a non-authoritative worker suggestion.
Before compact absorption, resolve the event against the current objective,
owner/role registry, dispatch receipt, lease epoch, contract revision and
terminal digest. Open the immutable terminal on any mismatch; only Controller
may accept a fresh-thread reason with its evidence reference. Reconstruct a rolled-over Controller from the
checksum-bound snapshot, immutable terminals and runtime facts; do not replay
raw transcripts. For the initial 30-day rollout, keep the rolling 20-event
Controller input median at or below 64k tokens and p95 at or below 96k; a median
above 96k forces compact/rollover before the next route, and 20 consecutive
events above 128k pause new-objective admission until recovery. Measure these
within one `physical_controller_context_epoch`: atomic rollover increments the
epoch and resets its window and consecutive counter, at most once per epoch.
A threshold never delays terminal absorption, safety action, existing-owner
continuity, or blocker recovery; it pauses only new-objective admission and
creates no role, artifact, or lifecycle. These are operational efficiency
alarms, never scientific acceptance or closure gates.
Invalid, stale, or contradictory state wakes the Controller for rebuild; it
does not invent an owner, successor, terminal, job, or scientific meaning.
If a valid snapshot omitted one already dispatch-bound objective, rebuild only
from the immutable terminal envelope plus matching runtime dispatch/final-turn
facts. The v5 `rebuild-add-objective` CAS may append exactly that one objective
and matching active role while preserving all existing state. An Executor
terminal explicitly mirrors its exact `startup_chain_authority` or `null`;
rebuild restores and revalidates it, and missing or digest-drifted authority
fails before CAS. It does not absorb the terminal or authorize a successor;
ordinary observe, verify and absorption steps remain mandatory. Never use
reconstruction to retrofit an unbound dispatch or choose among ambiguous
identities.

For `ecnuhpc`, use a queue-first A100 policy. Once a contract is explicitly
A100-admissible and launch-ready, submit it to Slurm immediately even when all
cards are allocated; the Slurm queue, not a capacity poll, waits for resources.
Do not transfer RTX-5090 runtime/cost evidence to A100 without a prospective
no-utility A100 profile when that identity matters.

The sole owner-authorized capacity exception stays inside the existing static
Controller-global heartbeat. It is enabled only while the rebuildable snapshot
contains a `BLOCKED` objective whose exact blocker trigger is
`A100_CAPACITY_AVAILABLE`. One wake may run one read-only `ecnuhpc` Slurm node
allocation check. If no A100 is free it returns quietly; if capacity is free it
wakes the Controller. It cannot select a candidate, submit or cancel a job,
open result files, or change a contract. Remove the blocker or dispatch the job
in the same Controller transaction that consumes the trigger. Never create a
capacity-only heartbeat, poll without a compatible blocked objective, or treat
idle A100 capacity as authority for filler work.

Automation is a user-visible mutation. Use it only when an independently real
remote/unattended Managed trigger has no native completion return. Reuse the
one existing bounded fallback by durable ID, change nothing when effective
fields already match, and never create polling or a second monitor for advisory,
Lite, source-search, R0, dashboard, or unbound capacity state.

The explicitly owner-authorized Controller-global singleton above is the only
standing exception to the remote-trigger creation rule. Lite work never creates
or retargets another heartbeat merely because the global singleton exists.

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

Compute contracts must distinguish `planning_estimate` from
`hard_safety_ceiling`. The estimate is the pessimistic complete-path forecast,
including compilation, warmup, profiling, evaluation, persistence and final
validation; exceeding it is a forecast miss, not an automatic invalid terminal.
The ceiling is the unaffordable/runaway stop and must not be a point estimate:
normally set it at least `1.5x` above the pessimistic complete-path estimate,
or about `2x` while compile, profiler, asset or runtime variance remains, when
that amount is still affordable. These multipliers are lower-bound heuristics,
not target caps: when failure remains affordable, prefer a materially wider
ceiling and update only the planning estimate from outcome-blind runtime,
throughput, VRAM, asset and scheduler facts. Before protected outcome access, the
Controller may freeze a budget-only amendment directly when it remains within
an already owner-approved total envelope and changes no accelerator class,
scientific identity, exposure, metric, baseline, seeds, stops or claim. This is
not a predicate Audit or new scientific version. It must be prospective and
recorded before resumed GPU execution; an actual hard-ceiling breach still
stops the run.

The Controller may prospectively adjust staged operational timeouts up to the
already frozen hard/outer ceiling at recorded outcome-blind checkpoints,
without another Audit or scientific version. Effect sign, utility, score and
protected-result content cannot enter that dynamic decision.

GPU admission ranks surviving novelty, problem importance, causal depth and
expected decision information per affordable cost, not predicted result sign.
A material-signal probability may affect portfolio priority, but negative/null
branches remain valid evidence and favorable-outcome stopping is forbidden.
Once an admitted `PROBE` has a lawful affordable real Scout, enable that Scout
without demanding publication-scale readiness. Idle compute removes scarcity
as a delay argument but never authorizes filler or weak ideas.

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

At each bounded runtime dispatch or continuation boundary, derive model family and
reasoning effort from the remaining action and currently visible context. Pass
both explicitly for Sol routes; omission or inheritance from the predecessor,
candidate, role or reusable session fails admission. A role name never selects
an effort tier by itself. Prefer frozen deterministic work through V1 named-agent
`agent_type=luna_worker` with `fork_context=false` (or the runtime's exact
no-history equivalent) and no direct model or effort override. A full-history
fork inherits the parent agent type; V2 `task_name` labels do not load the custom
profile. When the dispatcher lacks the V1 `agent_type` field but exposes an
explicit existing-thread model override, the Sol owner may instead dispatch one
contiguous same-thread `gpt-5.6-luna/max` turn. That prompt must contain the
complete frozen capsule and exactly one unique line
`LUNA_ROUTE_DISPATCH_ID=<id>`; this fallback does not claim the custom profile
loaded. Before the action's first write, remote launch or protected read, run
`scripts/validate_model_route.py` against durable rollout metadata, including
the exact parent binding for a named child or the exact thread and route-dispatch
binding for a same-thread turn. The check is ephemeral and writes no state or
artifact; a mismatch returns to the Sol owner before effects or stops fail-closed:

- `gpt-5.6-sol` + `max`: formulation, Opportunity Search, sources/neighbors,
  material contract/authority/claim choices, causal/statistical/algebraic
  adjudication, protected-result interpretation, scientific routes and closure;
- `gpt-5.6-sol` + `xhigh`: first real-carrier Scout Executor, complex
  implementation, remote integration/debugging, and evidence-bearing execution;
- `gpt-5.6-sol` + `high`: outcome-blind independent conformance/readiness Audit
  against a frozen oracle, or bounded engineering whose diagnosis exceeds the
  frozen mechanical contract, including nonlocal behavioral uncertainty,
  ambiguous failures, numerical stability, concurrency, performance tradeoffs,
  data-integrity risk, and routine Controller recovery with no scientific or
  authority choice; and
- `gpt-5.6-luna` + `max`: the default for boundary-complete routine
  implementation, test writing/fixing, documentation, deterministic local
  integration, rehashing, sync, packaging, unchanged-contract reruns, and
  outcome-invariant repairs.

Choose the cheapest capable route. When both Luna max and Sol high can complete
the full frozen objective, use Luna max. Code changes, test execution, or
documentation alone are not reasons to choose Sol. Luna eligibility requires
an exact edit surface, deterministic acceptance commands, frozen evidence,
exposure, budget and stop boundaries, and no decision-critical ambiguity or
protected-result interpretation.

The Luna receipt authority is durable rollout metadata, never worker prose. A
named child requires `session_meta` plus current `turn_context` with
`agent_role=luna_worker`, `model=gpt-5.6-luna`, `effort=max`, exact
`parent_thread_id`, and `multi_agent_version=v1`. A same-thread fallback requires
the exact `session_meta.id`, latest `turn_context` model/effort/turn ID, and
exactly one matching `LUNA_ROUTE_DISPATCH_ID` user message whose durable message
metadata carries that same turn ID. Do not infer turn ownership from file order:
queued user input may be serialized before a same-turn context record. Inspect the
dispatcher before spending a spawn: absence of `agent_type` makes only the named
profile unavailable, not a separately exposed existing-thread Luna route. Do not
substitute `task_name` or create a user-visible task merely to change models. A
failed exact dispatch or durable mismatch is `RULE_TOOLING_DRIFT`.

File or module count alone is not a Sol trigger. Deterministic multi-module
work remains Luna-eligible when the edit surface, interactions, and acceptance
oracle are frozen and mechanical. Use Sol high only when diagnosis or reasoning
exceeds that contract.

Test and documentation work is Luna-eligible only when it mechanically
instantiates frozen facts and acceptance semantics. Creating or revising an
oracle, threshold, test meaning, scientific claim, contract, exposure rule,
stop rule, or authority record is not routine implementation.

An unchanged rerun is Luna-eligible when execution is fully frozen and any
protected output remains sealed. Luna acceptance is limited to prospectively
frozen outcome-blind checks such as exit status, identity, schema, byte count,
or hashes. Reading, comparing, summarizing, or acting on protected output
returns to the authorized Audit/Controller path.

Explicit routing cases:

- exact deterministic edits spanning multiple modules -> `luna/max`;
- mechanical tests or documentation copied from a frozen oracle -> `luna/max`;
- defining or changing an oracle, threshold, test semantics, contract, claim,
  exposure rule, or authority record -> not Luna;
- sealed unchanged rerun with identity/hash-only acceptance -> `luna/max`;
- inspecting or interpreting protected rerun output -> Audit/Controller, not
  merely `sol/high`.

Do not switch per microstep. One objective may contain at most one contiguous
pre-release, outcome-blind Luna segment when the oracle and visible context are
frozen. A named child or same-thread Luna turn is an execution layer under the
same Sol owner: it preserves objective, scientific role, cumulative budget and
final terminal, gains no science/authority, and creates no owner handoff,
lifecycle or state field. It returns evidence to the exact Sol owner for
real-carrier, evidence-bearing or decision work. For one failure fingerprint it
may make at most one bounded mechanical repair, then returns the fingerprint,
evidence and next diagnostic without another Luna loop. An already-running turn
cannot switch model mid-turn; same-thread fallback is a new explicitly routed
turn. The user-visible task, generic collaboration override, named-profile
catalogs and existing-thread route may differ. Luna is unavailable only when
neither exact route is exposed or durable validation fails. Then use the nearest
allowed Sol tier, report
`RULE_TOOLING_DRIFT` and its expected token-cost consequence, and never claim
Luna executed. After
protected-result exposure, never downgrade to Luna. After
decision-critical reasoning, Luna is allowed only when that decision has been
frozen into a deterministic oracle which Luna cannot reinterpret. Ambiguity in
protected results, science, acceptance semantics, exposure, authority, stops or
irreversible scope stays outcome-blind and returns to Controller/Audit. Do not
make `Lead -> Builder -> Acceptance`, planner/implementer/tester/documenter, or
model switching a persistent pipeline.

Use `gpt-5.6-sol` + `high` or `xhigh` when engineering complexity exceeds Luna
without creating scientific or authority ambiguity. Raise an Executor to
`gpt-5.6-sol` + `max` when authority, evidence validity, concurrency, data
integrity, exposure, or scientific interpretation becomes ambiguous. `luna
max` never substitutes for `sol xhigh/max` scientific work. If a named tier is
unavailable, use the nearest available `gpt-5.6-sol` tier and report the
substitution before protected/scientific work.

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
4. treat unchanged-protocol code bugs as one uninterrupted engineering loop:
   diagnose, patch, exact-path smoke, validate, and execute the already
   authorized run in the same owner without an intermediate terminal,
   Controller callback, contract, task, lease, schema, activation state, or
   approval round. A recoverable outcome-blind failure is explicitly
   `NON_TERMINAL`; do not emit `ENGINEERING_*` or `CARRIER_STOP` for it.
   Terminal only when the bounded inventory cannot identify a local fix, an
   external fact is required, or scientific identity, exposure, authority,
   budget, or protected-outcome state would change;
   this is a parent workflow invariant. A child `AGENTS.md`, attempt contract,
   manifest, path policy, or first-mismatch action table may preserve unsafe
   bytes and prohibit their reuse, but may not convert an otherwise recoverable
   pre-release outcome-blind defect into terminal, create-new scientific
   attempt, Controller/Audit handoff, or fresh owner. Reject that conflict
   before Executor dispatch;
5. implement only controls that can change the witness decision;
6. if governance-only effort exceeds scientific implementation, remove
   nonessential controls and execute the direct bounded witness under the same
   evidence, authority, exposure, fairness, and budget hard controls;
7. use one proportionate verifier that recomputes primary metrics, gates, coverage, and leakage; add stronger trust machinery only for a named threat;
8. record launch, anomaly, completion, and adjudication, not routine heartbeats.
9. before the evidentiary clock, fuse every contract-listed outcome-blind
   exact-path, carrier, environment, exposure, authority, and resource check
   into one whole-chain preflight. Prefer one coherent implementation/repair
   commit and, only when evidence must be committed separately, one final
   evidence commit;
10. freeze scientific decision invariants before evidence, but record incidental
   implementation and host identity in the final launch manifest rather than
   promoting every filename, hash, schema label, readiness record, or verifier
   identity into a gate.
11. apply the decision cadence and attention budget in
    [research-programs.md](research-programs.md); context reconstruction and
    repeated review consume research budget even when GPU cost is zero.

### Exact startup-chain arming and bounded repair

Before immutable release/no-rescue arming, execute the same production startup
chain the run will use through a controlled zero-utility barrier:

`public CLI -> prepare_run -> actual return consumer -> generated remote launch
command/environment -> coordinator -> worker/bootstrap/import -> exact
isolation/device/runtime -> READY_BEFORE_FIRST_UTILITY -> controlled exit`.

The witness must use the production shell, heredoc, environment expansion,
entrypoint and runtime—not a unit mock. Its generated required-environment
projection comes from the same launcher function as release; it is not a second
manifest or authority. Reject missing or extra launch bindings, wrong root/write
modes, an unproven future reader, egress leakage, blocked local CUDA/IPC, or any
training, update, evaluation, utility, label, prediction, logit or protected
payload access. Preserve only bounded stage/error class plus digest when full
stderr would expose data. Component source, hash, cache and import checks are
prefix diagnostics; their count is never whole-chain coverage.

Process-liveness checks use service/cgroup `MainPID` or a PID file when
available; command-line fallback binds an anchored executable and excludes the
checker PID/parent. A checker imports the canonical schema/enum authority and
tests one valid plus one wrong-type fixture; it never hand-writes a synonymous
boolean such as `false` for canonical `UNOBSERVED`. These are clauses of the
same startup witness, not new validators or artifacts.

The sealed contract contains one `startup_chain_binding` with the exact hard
scientific projection, production entrypoint and zero-utility barrier. Before
Executor dispatch, the Controller binds `startup_chain_authority` in the current
objective: canonical chain ID, sealed contract path/SHA-256, and the complete
set of prior attempt-record path/SHA-256 pairs. The list length is the mechanical
count; do not duplicate it in another counter. Normal successor activation
verifies every referent before changing state, and generic replacement cannot
change or remove the authority. An Executor successor carries an omitted
authority forward; an explicit update must preserve chain/contract identity and
the entire prior-record prefix, and may append only the next consecutive sealed
record. Shrink, substitution or multi-record jumps fail before CAS. Leaving or
replacing the chain first requires an Audit successor. After each failed full
witness, that same Executor runs `controller_control_state.py
record-startup-attempt` with its objective/owner, current revision and the one
sealed record path/SHA-256. This sole same-objective CAS verifies outcome
blindness and the next consecutive round, changes only the authority record
list, and is idempotent on an exact retry; it creates no terminal, callback,
activation, new objective, owner or Controller roundtrip. This is the one
parent-AGENTS-delegated non-Controller snapshot mutation; every
other state, lifecycle, routing, terminal and ownership transition remains
Controller-only. A finite `BLOCKED`
objective retains the authority; `reconcile-open` reopens it only to an Executor
after revalidating every digest. Every prospective Executor terminal mirrors the
exact authority or explicit `null` from the activation barrier's
`terminal_identity_projection`, and `rebuild-add-objective` restores it
before normal terminal absorption. Scientific close removes it. Run
`controller_control_state.py
derive-startup-chain-id --state <snapshot> --objective-id <objective>`; the CLI
accepts no contract, record list, declared ID, projection, entrypoint or barrier
from its caller. It re-reads exactly the authority-bound files, derives their
canonical SHA-256 identity, rejects missing/digest-drifted/duplicate/gapped or
cross-chain history, and returns the consumed round plus next disposition. An
unbound replacement contract or caller-omitted history therefore has no input
channel. Create no repair ledger or sidecar.
Error fingerprint, stage, path, run ID, attempt, owner and session are
diagnostic only and cannot reset repair rounds. For this boundary,
`scientific_attempt` means the current prospective evidence unit bound by the
unchanged objective, hard scientific projection and cumulative resource
ledger. A `carrier_generation` is only a clean local implementation/filesystem
instantiation inside that unit; it is not a new task, state field, authority,
budget, owner, terminal, callback, attempt, or artifact family. Preserve the
old unsafe bytes without reusing them and note the generation only in the
existing engineering/run record when needed for reproducibility.
The initial failure record authorizes round 1, the smallest coherent repair.
The second failure record authorizes round 2, a clean chain reimplementation,
and returns `on_full_witness_failure=BOUNDED_ROOT_CAUSE_INVENTORY`; it does not
inventory before round 2 runs. Each repair reruns the complete exact startup
witness inside the same Executor/objective with no terminal, callback,
Controller roundtrip, create-new attempt or new owner. Failure after round 2
stops blind mechanical patching and requires one bounded root-cause inventory
inside that same Executor containing the startup-chain identity, both repairs
and full-witness results, bounded causes checked, unchanged contract/exposure/
budget, unopened protected state and one finite next action. The inventory is
a diagnostic escalation, not an ownership or terminal boundary. If it
identifies an outcome-invariant local fix, repair in place; if partial state is
unsafe, create a clean carrier generation inside the same objective; then rerun
the full witness with cumulative debit unchanged.

Terminalize or return to Controller/Audit only for: a scientific identity,
estimand, data/split, exposure, metric/threshold, baseline, seed/schedule,
claim or stop change; acceptance or authority semantic ambiguity; hard-budget
or accelerator-class expansion; release/protected-outcome crossing;
destructive reuse/overwrite whose safety cannot be established; cross-owner
write conflict; public/production/paid/auth/permission change; or unavailable
external authority. Repair count, a new failure fingerprint, local complexity,
and path contamination avoidable by a clean carrier generation do not satisfy
that gate. Only a genuine external fact or unavailable authority may become
finite `BLOCKED`; generic engineering labels have no closure effect. Any
prospective child rule or attempt contract that imposes first-mismatch
terminal/no-repair/create-new behavior outside this gate is invalid before
dispatch. Legacy immutable attempts retain their original evidence and are not
reclassified or rescued.

Legacy immutable attempts keep their original rules. During v4 migration, each
delegated Executor lacking the later startup-authority field receives only the
objective-local applicability tag
`V4_EXECUTOR_NO_STARTUP_AUTHORITY_MIRROR`, even if its terminal is not yet
observed. The tag survives that active objective; its later callback,
verification and absorption use the legacy parser rule, then remove the tag
atomically. Generic replacement and prospective v5 state cannot create it.
New startup-chain coverage is prospective and may not reclassify, mutate or
rescue legacy evidence.
A preflight PASS proves only that the real startup path reached the barrier with
zero utility; it is not R1, R3, scientific validity or claim authority.

### Workflow Evolution Audit

Use one dedicated reusable session titled `Audit · Workflow Evolution ·
<STATE>`; its canonical role remains `Audit`, and idle work owns no snapshot
role, lease or heartbeat. By explicit user policy this one session remains
pinned while active, idle, or `COMPLETE`; pinning is navigation only and does
not make it Managed or a second Controller. Intake `PROACTIVE_REPORT` and
`AUDITOR_DISCOVERY` as untrusted leads. Every ordinary worker may fuse one
compact issue envelope into its existing final/callback; Controller validates,
fingerprint-deduplicates and batches candidate signals using the existing one
thread-list/wait result. Only when a signal exists may it inspect the fixed
Workflow Evolution task's recent envelope fingerprints and send one compact
batch; no signal means no message, ACK or resend. Trigger from existing traces
when one startup chain has at least two pre-utility transitions, terminal
recovery needs more than one Controller wake, access controls self-lock,
create-new repairs recur, whole-chain coverage fails, a model route is
unavailable/mismatched, or the user must rescue an observable workflow defect.
Every eighth absorbed terminal contributes one independent low-frequency trace
sample in that same absorption transaction; the 30-minute heartbeat only bounds
delivery/recovery latency and never creates a sample. Deduplicate, compare
backward outcome-cost measures with the forward trace, test the strongest
alternative cause, then emit one decision-complete patch set, replay and canary
with `RETAIN|ROLLBACK|NO_CHANGE`. Reliability/evidence integrity is a pass/fail
floor; decision time, engineering/idea/compute efficiency, governance
attention, recurrence and blast radius remain separate detectors.
The detector names are `FORWARD_TRACE`, `BACKWARD_OUTCOME_COST`, and
`RULE_CONFORMANCE`; scores prioritize but never establish cause.

Both intake sources use one envelope and no registry:
`source_type, detector, observed_fact, affected_stage, impact,
recurrence_clue, evidence_pointer, protected_boundary_flag,
suggested_next_check, fingerprint, rule_ref, mode`. Workers attach it to their
ordinary final/callback; Controller validates fields, drops exact fingerprints
already visible in the fixed Workflow Evolution task, and batches the remainder.
Reliability-floor events and explicit user rescue may wake that existing task
immediately; ordinary signals wait for the next existing Controller event or
30-minute recovery wake. Neither path creates state, an ACK, or a resend.

The initial token shadow detector is dispatch-scoped: 25M reported tokens with
at least two token-bearing turns and zero decision-relevant output is `SOFT`;
75M and zero output is `HARD`. After at least eight healthy comparable windows,
raise the soft threshold to the larger of 25M, twice the median, and median plus
three MAD, capped at the 75M hard boundary. Valid negative/null decisions count
as output; engineering/tests/files/terminals/reviews/GPU/token activity do not.
Use the existing SQLite thread-to-rollout pointer and only `token_count` events
after the one canonical Controller-to-owner user message containing the exact
dispatch ID, `PASS_MODEL_ROUTE:` and `await-successor-activation`; ignore later
terminal, callback, compaction, tool and prose echoes, while rejecting zero or
multiple canonical markers, nonworkspace threads and the independent ARIS task.
`scripts/workflow_evolution_gate.py`
emits Shadow Mode JSON only and creates no artifact or state.

Every finding includes a separate rule-conformance classification. A clear,
applicable, feasible isolated deviation is `EXECUTION_NONCONFORMANCE`; repeated
independent deviation or compliant zero-output is `RULE_DESIGN_DEFECT` unless a
shared tool/runtime mismatch establishes `RULE_TOOLING_DRIFT`; material
authority conflict is `AUTHORITY_CONFLICT`; unresolved applicability is
`NOT_ESTIMABLE`. Compliance never resets zero-output token burn. Scores detect
and prioritize; trace evidence is required before a persistent change.

Use the same Shadow detector to compare naturally occurring, mechanically
comparable Luna and Sol samples; create no benchmark task or telemetry stream.
For one comparison key report existing total tokens, wall time, first-pass
acceptance, retry count, decision-complete output and reliability-floor pass.
The route is `RETAIN_ELIGIBLE` only when Luna is reliability-noninferior, no
worse on acceptance/output/retries, and lower on both tokens and wall time;
otherwise report `ROLLBACK_REQUIRED`, `NO_CHANGE` or `NOT_ESTIMABLE`. A route
smoke proves reachability only, and the scorecard remains a detector rather than
causal or scientific evidence.

Resolve facts locally and choose reversible deterministic defaults. Batch only
the current material uncertainty frontier once. The Audit cannot trigger itself,
create telemetry or governance families, become a global mutex, or persist a
change without replay evidence and rollback.

A candidate diff, passing scratch-copy test, advisory response, or review packet
is not a completed optimization. Before `RETAIN|COMPLETE`, compare each intended
live preimage with the frozen baseline, install only those exact files, run the
required live replay/canary, byte-compare or hash the live read-back against the
accepted candidate, and send the existing consumer/Controller one non-scientific
completion message naming the exact live hash and reload instruction. If any
step fails, remain active or roll back; never claim deployment from the candidate
copy. Ordinary Pro review is nonblocking and may challenge the deployed diff
later. This is an owner completion invariant, not a new callback, receipt family,
state field, watcher, heartbeat, registry, role, or lifecycle.

Scientific projection and operational overlay remain disabled until a
deny-by-default field map, deterministic full-contract reconstruction, and
byte/semantic equivalence suite exist. The complete embedded contract remains
the only contract carrier in this rollout.

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
- Maintain one logical persistent Pro advisory channel across sequential
  bounded batches. One physical conversation has at most one in-flight batch;
  it has no queue, poll loop, follow-up turn, reader relay task, or Managed role.
- Resolve the configured project and conversation by exact runtime metadata ID
  before submission; title/label similarity is not identity. A fallback is
  allowed only when its exact ID was prospectively bound for that advisory
  class. If an ordinary channel is unavailable, record `SKIPPED_UNAVAILABLE`
  and finish local decision-complete work. A mandatory high-risk closure
  advisory instead remains one finite block; never silently use an unrelated
  conversation.
- Submit one exact-hashed authority bundle, not a summary-only prompt: the
  complete current Skill directory, every applicable parent-to-child
  `AGENTS.md`, all routed direct references, the candidate diff and validation,
  and bounded decision evidence. Exclude only secrets, credentials and
  protected model/data/result payloads. Name every exclusion and hash the files
  actually sent so later Pro review is reproducible; reuse the current task
  record rather than creating a packet registry or artifact family.
- `one-shot` means one frozen scope, one submission and one later read per
  batch. A later batch requires a material scope, evidence, or decision delta;
  reject duplicate scope hashes instead of restating the same question.
- At each material idea boundary, ask whether one Pro challenge could falsify,
  improve, or independently cross-check the route by distinguishing weak
  signal, implementation attenuation, estimand mismatch, missing strong
  reduction, contribution risk or unsafe closure. Route it when that independent
  challenge has material expected information, even if a cheaper local
  source/code/algebra/direct check already supports a provisional answer.
- Ordinary batches are `NON_BLOCKING`: Pro supplements rather than blocks local
  checks, so Explorer, Audit, implementation, and execution continue while it
  runs and the current owner remains bound. Use `BLOCKING_HIGH_RISK` only for a
  prospectively named exact transition such as durable high-risk closure. Bind
  its objective/transition/target-stage/authority tuple one revision before the
  advisory. Do not broaden or duplicate the gate; clear it only after one
  observed `SENT` reply has a locally absorbed validation terminal.
- Require every later review to name the decision, expected new information,
  and why it is not duplicating an already consumed challenge. From one reply,
  retain at most three locally verifiable leads and immediately launch at most
  one cheapest discriminating local check; do not create one Audit/Executor per
  lead.
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

Every cross-thread successor records exactly one structured
`fresh_thread_reason` and one nonempty immutable `fresh_thread_evidence_ref`.
One owner thread may hold at most one `DELEGATED` objective.
The allowlist is
`PROTECTED_RESULT_INDEPENDENCE`, `STRICT_BLIND_EXPOSURE_REPLACEMENT`,
`INDEPENDENT_VERIFICATION_OR_ADJUDICATION`, `WRITE_OWNERSHIP_TRANSFER`,
`INDEPENDENT_REPRODUCTION_OR_ANTI_ANCHORING`, or
`VERIFIED_CONTEXT_ISOLATION_REQUIRED`, or
`OWNER_THREAD_UNAVAILABLE_AFTER_RECOVERY_PROOF`. Write-ownership transfer
requires a canonical role change; protected-result independence and independent
verification/adjudication require an Audit successor; exposure replacement,
anti-anchoring, context isolation and proved owner loss preserve the prior role.
Model switch, hash/path/schema/import or
package checks, validator retry, safe-access mechanics, deterministic repair,
and unchanged-contract rerun are rejected reasons. Reusing the same thread
preserves its canonical role and records no fresh-thread reason. `reconcile-open`
is only for finite `BLOCKED -> DELEGATED` recovery with immutable evidence,
including during v3 migration. A delegated v3 owner first migrates unchanged and
then uses the constrained successor transition; `reconcile-open` cannot rebind it.

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
