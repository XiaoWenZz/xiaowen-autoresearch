# Managed shared resources

Load this reference only when a Managed event actually changes a shared GPU
execution/queue, a result-analysis queue, a persistent worker lease, or durable
terminal recovery. Lite work, ordinary Opportunity Search, public-source R0,
local engineering, Pro advisory, dashboard maintenance, and capacity labels do
not load it.

This is not a global portfolio scheduler. It creates no zero-GPU lane, Pro
lane, idle proof, continuous-search obligation, finite-HOLD timer, automatic
post-negative diagnosis, or callback ACK gate. Reconcile only resources touched
by the event.

## 1. Authority and ownership

Before retaining a GPU queue item, check its latest authority in this order:

```text
validated experiment record
> durable terminal packet
> frozen prospective contract
> LLM-Wiki synthesis
> operational chat
```

Wiki/dashboard/chat may nominate an item but cannot override a newer hold,
cancellation, exposure boundary, budget cap, carrier failure, or scientific
terminal. Each queue item binds:

- task and canonical owner;
- `blocked` plus one blocking fact, or `launch_ready`;
- the checked authority kind, ID, evidence path, and `queue_gpu` disposition;
- launch prerequisite and exact prospective contract; and
- hard compute/cost/exposure ceilings.

Only a frozen prospective contract, verified scientific terminal, or explicit
owner approval can authorize the queue. Search exhaustion, carrier/access
failure, a report, a model verdict, or spare GPU capacity cannot.

One owner holds at most one current persistent task lease. The durable worker
registry preserves its maximum issued epoch and exact current lease. A new
epoch needs one activation/transfer receipt; revocation/reclamation is explicit.
Stale-epoch callbacks and snapshots have zero effect.

## 2. GPU execution and result analysis

A `launch_ready` item with no live GPU job binds exactly one activated launch
owner and successful dispatch receipt. A live job binds task, owner, execution
ID, terminal event, current worker lease, and one active job-specific watchdog.
The watchdog binds the same job and owner, has an absolute next check, and—only
when overdue—one bounded recovery receipt. It never becomes a progress poll.

After launch, verify scheduler/process acceptance and one immediate liveness
observation. Record job ID, code/config identity, logs, artifacts, expected
completion, check/cancel commands, and return mechanism, then release the
foreground task.

A result-analysis item independently binds the terminal ID and evidence path
that made it ready. This helper validates that binding; it does not invent a
global priority/preemption lane or decide scientific meaning.

## 3. Staged GPU allocation

When independent ideas are already launch-ready, allocate the smallest valid
paired-seed tranche breadth-first. Concurrency changes wall time, not aggregate
GPU-hours or inference validity. Freeze in the existing contract:

- complete paired bundles, keeping all arms of one bundle together;
- smallest initial tranche and maximum staged ceiling;
- prospective `expand | futility | hold` actions;
- valid sequential adjustment or disjoint follow-up units for final inference;
- per-job safety/paid ceilings; and
- protected-data and exposure boundaries.

There is no automatic cap expansion. A later tranche inside the frozen action
table and maximum ceiling is preauthorized. Any higher ceiling or changed
carrier/estimand/contract is a prospective new authority decision made before
its outcomes; it cannot rescue or reinterpret an observed attempt.

An initial positive is screening `SCOUT_SIGNAL`. A weak/null tranche closes
only what its prospectively valid futility rule can support. Do not reuse
screening units as unadjusted final evidence.

Before first GPU placement, require the dated bounded neighbor map, strongest
simple fair baseline, and cheapest witness defined by the problem-space route.
That prevents obvious duplication but does not establish novelty. After a
material signal, apply the Contribution Gate before paper-scale expansion.

## 4. Terminal idempotency

A Managed worker freezes one terminal and sends once. Successful tool receipt
sets `callback_state=delivered`, pauses/removes the watchdog, and releases the
worker. Delivery needs no `RECEIPT_ONLY`, `FINAL_ACK`, receiver ping, or
portfolio-wide recomputation.

The Controller applies at most one effect per `terminal_event_id`. Duplicate
delivery with the same binding is a no-op; conflicting binding or digest fails.
An optional `acknowledged` state exists only to certify a real Controller
shared-state commit. It never blocks or wakes the worker. A `dispatch_next`
commit must bind an activated current lease and dispatch receipt. An
`explicit_hold` records one blocker, reopening fact, observer, concrete trigger,
and next evidence action in existing task state; it creates no backlog lane.

## 5. Minimal snapshot and validator

New snapshots use schema `2` and include only present shared resources:

```text
schema_version: 2
controller_thread_id
observed_at_utc
worker_registry
lease_transitions
terminal_idempotency_history
gpu_running                 # null or one live job
gpu_queue                   # ordered blocked/launch_ready items
gpu_launch_in_progress      # null or one activated owner
result_analysis_queue
terminal_transaction        # optional delivered/shared-commit state
```

Validate and atomically advance the durable lease/terminal watermark:

```bash
python3 scripts/reconcile_research_lanes.py \
  /path/to/shared-resources.json \
  --state /path/to/shared-resources-watermark.json
```

Use `--check-only` for a diagnostic read that must not advance the watermark.
The watermark contains only worker epochs, terminal idempotency history, and
lease-transition fingerprints. Legacy snapshots may still contain
`zero_gpu_*`, `opportunity_search`, `idle_proof`, or `pro_advisory_lane`; the
validator reports them as ignored non-authority and never writes them into the
watermark.

This helper validates orchestration consistency only. It does not schedule
work, query remote state, authorize compute, interpret results, establish
novelty, or turn an engineering/access failure into a scientific decision.
