# Managed state schema

Load this reference only when a real Managed trigger requires durable state.
Lite work uses its existing repository records and the user-visible task; it
does not initialize this tree.

## 1. Directory and version contract

```text
<task>/
├── AGENTS.md
├── state/
│   ├── charter.json
│   ├── progress.json
│   ├── heartbeat.json
│   ├── directions.jsonl
│   ├── evidence.jsonl
│   ├── claims.jsonl
│   ├── iterations.jsonl
│   ├── approvals.jsonl
│   └── workers.jsonl
├── runs/                 # one manifest per run ID
├── artifacts/            # raw and derived artifacts
├── logs/events.jsonl
└── reports/
```

Use schema `1.3` for new durable tasks. Keep JSONL append-only: a correction
appends a record naming `supersedes_id`. Do not rewrite evidence history.
`scripts/validate_task.py --legacy-read` may inspect an older tree but returns a
non-authoritative result; legacy state cannot grant readiness or evidence
authority.

Both governance tracks use `operating_weight=managed`:

```text
scout / managed
confirmatory / managed
```

`program_id` and `epoch_id` are both null for a standalone Managed task, or
both non-empty when an already-established Program binds the task. Never invent
a Program/Epoch merely because durable recovery is needed.

## 2. Proportionate readiness

All ready tasks freeze `research_question`, success/failure criteria, stop
conditions, strongest baseline identity, claim boundary,
`protocol.data_boundary`, and a valid `protocol.frozen_at`. The
`governance_admission_proof` names the actual Managed trigger.

Task-specific requirements are deliberately different:

- `literature`: no seed policy or utility metric is required. Bind the public or
  protected source boundary and the decision-complete source/claim question.
- `engineering`: bind `code_version`, `real_carrier_path`, `profile_metrics`,
  `analysis_plan`, and `utility_blind=true`. This R1 profile measures runtime,
  VRAM, stability, throughput, or cost—not scientific utility—and requires no
  power plan.
- Scout `experiment|mixed`: bind code, dataset/version/split, seed policy,
  analysis plan, exact run bindings, and primary metrics. Freeze `2` or `3`
  necessary arms, `6` paired bundles, MPE, guard comparator, strongest fair
  baseline, mechanism deletion when distinct, outcome/action table, and compute
  cap. Final power and multiplicity are not first-Scout readiness gates.
- Confirmatory `experiment|mixed`: additionally bind the complete power plan,
  multiplicity plan, full claim-proportionate baseline scope, and external-
  validity scope required by the final claim.

A Scout may yield a `SCOUT_SIGNAL`, scoped negative/null result, diagnostic, or
carrier stop. It cannot contain an accepted claim. Promotion creates a
prospective Confirmatory protocol and fresh confirmation evidence; it never
relabels observed Scout outcomes as independent confirmation.

## 3. Ownership

| File | Sole writer/authority | Meaning |
|---|---|---|
| `charter.json` | owner/Controller | Frozen question, protocol, budget, permissions |
| `progress.json` | Controller | Current status, next action, exact blocker |
| `heartbeat.json` | active worker | Optional liveness lease; never scientific progress |
| `directions.jsonl` | Controller | Structural directions and named replications |
| `evidence.jsonl` | producer/verifier | Observations, provenance, verification, limitations |
| `claims.jsonl` | author/independent Audit | Scoped claim and adjudication lifecycle |
| `iterations.jsonl` | Controller | One outcome record per completed iteration |
| `approvals.jsonl` | owner/Controller | Requested and decided authority changes |
| `workers.jsonl` | Controller | Dispatch, delivery, recovery, optional shared commit |
| `runs/*.json` | Executor | Bound run identity and reproducibility record |
| `logs/events.jsonl` | active roles | Operational events; not scientific authority |

Exactly one owner writes a live run or shared record. An evidence producer, its
verifier, and the adjudicator of an accepted claim are registered, distinct
workers on distinct task sessions. The verifier and adjudicator are canonical
Audit roles. Same-model agreement is not independence.

## 4. Worker terminal and callback

Append one immutable record per worker transition. Keep `worker_id` stable and
give each transition a unique `worker_record_id`.

```json
{
  "worker_record_id": "WR-B1-003",
  "worker_id": "B1-executor",
  "thread_id": "019f...",
  "program_id": null,
  "epoch_id": null,
  "contract_revision": "v0",
  "role": "Executor",
  "status": "completed",
  "callback_state": "delivered",
  "terminal_event_id": "TERM-B1-001",
  "reclaim_deadline": null,
  "watchdog_id": "monitor-b1",
  "watchdog_state": "paused",
  "artifact_paths": ["artifacts/B1/outcome.json"],
  "recorded_at": "2026-07-22T09:00:00Z",
  "supersedes_id": "WR-B1-002"
}
```

Statuses are `dispatched`, `running`, `needs_attention`, `completed`, `failed`,
`cancelled`, and `reclaimed`. Callback states are `pending`, `delivered`,
`acknowledged`, and `not_available`.

- `delivered` means one bounded send produced a successful tool receipt. It
  releases the worker immediately and is a valid terminal state; no ACK or
  receiver ping is required.
- `acknowledged` is optional and records a Controller-side shared-state commit.
  It still never blocks or wakes the released worker.
- `not_available` records ambiguous/unavailable delivery with one reclaim
  deadline. The worker does not resend.
- A delivered or acknowledged terminal has one stable `terminal_event_id` and
  a paused/not-required watchdog. Controller effects are idempotent by that ID.

When a true shared-state commit needs certification, `controller_action` may
record one transaction and one of `dispatch_next`, `explicit_hold`,
`owner_approval_required`, or `scoped_close`. `dispatch_next` binds an actually
registered successor record and contract revision. No field such as
`worker_notified`, `RECEIPT_ONLY`, or `FINAL_ACK` is required.

The nested six-field `completion_binding` is the sole terminal identity
authority. A top-level `terminal_event_id` or `terminal_path` is an optional
compatibility mirror and, when present, must equal the nested value. Generate
the existing callback with `controller_control_state.py
prepare-terminal-callback`: it reads and fully validates the sealed regular
non-symlink file, opens every parent component with no-follow directory
handles, rejects write bits or stat changes, and resolves the current
objective/dispatch/lease identity locally. The transport envelope is
receipt-only and contains exactly `terminal_event_id`, `objective_id`,
`owner_thread_id`, `terminal_path`, `final_bytes`, `final_sha256`,
`disposition`, `next_action`, and nullable `fresh_thread_reason`; it never
emits `terminal_body` or `completion_binding`. Missing legacy disposition or
next-action values remain null; non-null text is capped at 2048 UTF-8 bytes,
and a fresh-thread reason must be allowlisted. Sending is rejected locally on
any body/mirror/envelope/registry conflict. The Controller passes those exact
byte/hash receipt fields to `observe-terminal`; a same-path replacement after
callback preparation fails before revision, cursor, owner or pending state
changes. The immutable source-task final is recovery fallback, never the
normal envelope source. Callback repetition is transport evidence, not a
second identity authority or permission to accept a disposition.

Schema v5 binds terminal identity before delegation and persists an
identity-only recovery barrier:

```json
{
  "completion_binding": {
    "task_id": "task-id",
    "dispatch_id": "dispatch-id",
    "lease_epoch": 1,
    "contract_revision": "R2-v3",
    "terminal_event_id": "TERM-...",
    "terminal_path": "/private/tmp/TERM-.../terminal.json"
  },
  "pending_absorptions": [{
    "terminal_event_id": "TERM-...",
    "objective_id": "OBJ-...",
    "owner_thread_id": "019f...",
    "completion_binding_sha256": "<sha256>",
    "terminal_bytes": 1234,
    "terminal_sha256": "<sha256>",
    "verification_state": "IDENTITY_VERIFIED"
  }]
}
```

Callback preparation, observation, verification and final absorption all use
one sealed-terminal parser: valid UTF-8 JSON object, exact six-field nested
binding, exact optional mirrors, allowlisted no-symlink path, immutable inode,
stable bytes and digest. Duplicate keys, `NaN`, `Infinity`, `-Infinity`, finite-
syntax overflow such as `1e9999`, and a boolean masquerading as integer
`lease_epoch`, and Unicode surrogate code units in keys or values are rejected;
canonical emission enforces the same scalar/non-finite boundary. The final path
component opens with `O_NOFOLLOW|O_NONBLOCK` before `fstat`, so a FIFO or other
non-regular node cannot block the singleton before the regular-file gate.
`observe-terminal` records a pending item only after
that parser passes and the reread bytes/digest equal the delivered callback,
marks the owner `TERMINAL_PENDING_ABSORPTION`, and leaves
the cursor unchanged. `verify-pending-terminal` reparses and promotes only that
exact digest to `CONTROLLER_VERIFIED`. `activate-successor`, `close-objective`,
and `absorb-and-block` reparse again, then atomically remove the pending item,
append the absorbed ID, reconcile ownership, and bind the next completion
identity where applicable. A delegated completion `terminal_event_id` must be
globally fresh against both pending and absorbed IDs; successor activation
rejects reuse before CAS, and snapshot validation rejects any active/absorbed
intersection. No external Controller-wake outbox is part of v5:
the existing desktop singleton heartbeat resumes the same Controller thread.
Crash recovery repeats these idempotent state-tool steps in the same Controller
wake; terminal or dispatch ambiguity is reconciled from bound IDs before retry.
All snapshot readers share-lock the stable control-directory inode. Every
normal, migration and recovery writer exclusively locks it, rereads the
revision/checksum under that lock, validates the transition, and commits both
files before unlock; exactly one competing Controller/Executor CAS can succeed.

`await-successor-activation` is a prospective read-only startup barrier, not a
state transition. Controller places the planned `activate-successor` revision,
successor objective/owner/role, exact six-field completion binding, absorbed
predecessor event, and either one exact remote-job projection or an explicit
no-remote-job assertion in the activation prompt. When present,
`activate-successor --new-remote-job-json` appends that one `ACTIVE/NONE` job in
the same Controller CAS that activates its matching Executor objective and
owner. The destination shared-lock polls for at most 30 seconds. Revision below
the floor returns bounded `WAIT_ACTIVATION_COMMIT`; at or above it the full
tuple, absorbed-event set, absence from pending, managed-role match, and exact
job expectation are mandatory. It never writes the snapshot, checksum,
terminal or another artifact. Timeout cannot terminalize, finalize, mutate or
reinterpret the objective; Controller recovery reconciles the original
dispatch ID without blind resend.

On PASS the same command returns `terminal_identity_projection`, containing the
exact nested `completion_binding`; for an Executor it also contains the current
`startup_chain_authority` as the exact object or explicit JSON `null`. The
producer initializes its terminal from this projection rather than hand-writing
the identity fields. This is a read-only projection of already committed state,
not a second authority or artifact, and the sealed callback/observation parser
still rejects any mismatch.

The prebound `ACTIVE/NONE` job is an obligation to monitor, not proof that the
remote submit already succeeded. An absent unit and absent expected files before
`late_threshold` have zero effect; the threshold wakes the same owner for launch
identity reconciliation without inventing a job or scientific outcome.

Every `advance-cursors` update includes
`source_turn_state=IN_PROGRESS|FINAL`. A `FINAL + NON_TERMINAL` Executor update
is accepted only when exactly one matching `ACTIVE` remote job with `NONE` wake
delivery already exists. Otherwise the CAS rejects without moving the cursor,
preserving the prebound terminal and same-owner recovery path. This does not
prevent a runtime from rendering a malformed final; it prevents Controller
continuity from accepting that final as ordinary progress. Terminal cursors
retain the separate absorbed-event barrier.

For prospective budgets, the already-debited predecessor and governance cost
remain cumulative. Only elapsed execution after durable successor activation
enters the new Executor's frozen execution-wall predicate; pre-CAS barrier time
is still reported governance/token cost, not an execution debit. This is no
credit, reset or ceiling expansion: genuine post-CAS exhaustion still fails
closed, and existing terminals are never retroactively rescued.

When a valid snapshot omitted an objective that was already dispatch-bound in
immutable runtime facts, `rebuild-add-objective` is the sole recovery-only CAS.
It preserves every existing objective, role, job, advisory, pending item and
absorbed ID; adds exactly one `OPEN/DELEGATED/ACTIVE` objective plus its matching
role; requires an allowlisted immutable terminal path with exact byte count and
SHA-256, exact body binding and mirrors; and records a nonempty recovery-evidence
reference. An Executor terminal must carry `startup_chain_authority` explicitly
as the exact object or `null`; rebuild restores and revalidates the object before
CAS, while a missing field or digest drift fails with the snapshot unchanged. It
never absorbs the terminal: the Controller must still run `observe-terminal`,
verify the pending identity, and complete one ordinary absorption transaction.
This command cannot replace normal prospective completion binding or repair an
ambiguous or missing dispatch fact.

A delegated Executor objective may additionally bind exactly one
`startup_chain_authority`:

```json
{
  "startup_chain_authority": {
    "startup_chain_id": "startup-chain-sha256:<64-hex>",
    "contract_path": "/private/tmp/contract.json",
    "contract_sha256": "<64-hex>",
    "prior_attempt_records": [
      {"path": "/private/tmp/attempt-001.json", "sha256": "<64-hex>"}
    ]
  }
}
```

The list itself is the complete pre-dispatch set and its length is the count.
`activate-successor` verifies the sealed contract and every bound record before
the CAS, while the objective guard prevents generic replacement from changing
or removing this authority. Executor successor transitions preserve the exact
chain/contract and record prefix, carry an omitted repeated argument forward,
and may append only the next consecutive sealed record. Shrink/substitution
fails before CAS; replacement first crosses to Audit. Inside the unchanged
delegated Executor, `record-startup-attempt` is the sole same-objective CAS: it
checks owner, outcome blindness, exact immutable digest and consecutive round,
then appends exactly one record while leaving terminal identity, roles, jobs,
advisories and pending/absorbed IDs unchanged. Its exact retry is idempotent.
This operation needs no terminal, callback, activation or Controller route. A
finite `BLOCKED` state retains the authority and `reconcile-open` revalidates it
before reopening the Executor; scientific close removes it. Every prospective
Executor terminal mirrors the exact authority or explicit `null`, so recovery
cannot silently reset a consumed budget. `derive-startup-chain-id` accepts only
the snapshot and objective ID, re-verifies the same bytes, and has no caller
channel for a replacement contract or omitted history.

The delegated Executor alone may invoke this one matching-objective/owner
`record-startup-attempt` CAS under the parent AGENTS chain. Every generic,
lifecycle, routing, terminal, role, job, advisory and owner-transfer state write
remains Controller-only.

A delegated v4 Executor without startup authority may carry the objective-local
`legacy_terminal_schema=V4_EXECUTOR_NO_STARTUP_AUTHORITY_MIRROR` applicability
tag after migration, including while active with no observed terminal. The tag
persists until that objective's later legacy callback/verification/absorption,
which removes it atomically. Generic replacement cannot create/remove it, and
new v5 state cannot seed it. This compatibility path never binds or resets
startup authority and is invalid for prospective v5 terminals.

Controller context-window alarms are read-only and scoped to one
`physical_controller_context_epoch`. Before any new dispatch or route, run
`workflow_evolution_gate.py controller-context-window` against the existing
SQLite thread pointer. After the latest top-level `compacted` or
`event_msg/context_compacted`, use at most the latest 20
`last_token_usage.input_tokens`: fewer than 20 is `ALLOW`; 20 consecutive
values above 128000 is `PAUSE_NEW_OBJECTIVE_ADMISSION`; otherwise median above
96000 is `REQUIRE_ROLLOVER`; all other windows are `ALLOW`. Median 64000 and
p95 96000 are diagnostic targets only. The JSON gate emits no state or
artifact, returns nonzero only for the two blocking decisions, and parser
failure is distinct from an executed decision. An atomic rollover increments
the epoch, resets its rolling window and consecutive counter, and occurs at
most once per epoch. The alarm may pause only new-objective admission;
terminal absorption, safety, existing-owner continuity and blocker recovery
remain nonblocking.

Normal successor activation reuses the canonical thread and canonical role.
When `new_owner_thread_id != old_owner_thread_id`, `activate-successor` requires
exactly one allowlisted `fresh_thread_reason` plus a nonempty immutable
`fresh_thread_evidence_ref`:

- `PROTECTED_RESULT_INDEPENDENCE`;
- `STRICT_BLIND_EXPOSURE_REPLACEMENT`;
- `INDEPENDENT_VERIFICATION_OR_ADJUDICATION`;
- `WRITE_OWNERSHIP_TRANSFER`;
- `INDEPENDENT_REPRODUCTION_OR_ANTI_ANCHORING`; or
- `VERIFIED_CONTEXT_ISOLATION_REQUIRED`; or
- `OWNER_THREAD_UNAVAILABLE_AFTER_RECOVERY_PROOF`.

Model switching, deterministic hash/path/schema/import/package checks,
validator retry, safe-access mechanics, unchanged repair, and unchanged rerun
are not fresh-thread reasons. A same-thread successor records no reason and may
not silently change its canonical role. `WRITE_OWNERSHIP_TRANSFER` requires a
canonical role change. `PROTECTED_RESULT_INDEPENDENCE` and
`INDEPENDENT_VERIFICATION_OR_ADJUDICATION` require an Audit successor. Exposure
replacement, anti-anchoring, context isolation and proved owner loss preserve
the prior role. `reconcile-open` may reopen only a previously finite `BLOCKED`
objective, including during v3 migration, and requires its own immutable recovery
evidence. A delegated v3 owner migrates unchanged before any constrained
successor transition; generic replacement cannot rebind an owner or lifecycle.

For the rebuildable Controller control snapshot, apply **open means owned**:
`DONE` is legal only when the exact candidate is scientifically `CLOSED`;
otherwise lifecycle is `DELEGATED` with a matching active owner, or finite
`BLOCKED` only on a genuine external fact/unavailable authority with reopening
fact, observer, trigger or `next_check_at`, and `resolution_deadline`.
Each owner thread appears on at most one `DELEGATED` objective; sharing one
thread across open objectives creates a terminal path that cannot close atomically.
Internal repair, constructability, contract, source/code/algebra,
estimand/identification, weak-signal, or contribution work is never a durable
blocker or inactive archive.

Every v4 Pro obligation uses explicit batch semantics; legacy advisory shapes
are invalid for validation, replacement, migration and wake delivery. An
`advisory_reads` entry contains
only routing and metadata fields:

```json
{
  "advisory_id": "ADV-014",
  "objective_id": "OBJ-003",
  "conversation_thread_id": "chatgpt-thread-id",
  "reader_thread_id": "audit-thread-id",
  "reader_role": "Audit",
  "submitted_at": "2026-08-06T08:00:00+08:00",
  "submitted_thread_updated_at": 12345.0,
  "not_before": "2026-08-06T08:05:00+08:00",
  "scope_revision": 2,
  "scope_sha256": "<lowercase-sha256>",
  "batch_mode": "NON_BLOCKING",
  "decision_gate": "NON_BLOCKING",
  "blocking_gate_id": null,
  "monitor_state": "AWAITING_RESPONSE",
  "observed_thread_updated_at": null,
  "wake_delivery": {"state": "NONE", "claim_token": null, "observation_id": null}
}
```

Modes are `NON_BLOCKING` and `BLOCKING_HIGH_RISK`. Non-blocking is the ordinary
case and cannot create a blocked objective, release its owner, or suppress local
work. High-risk mode requires `decision_gate=BLOCKING_HIGH_RISK` and one nonempty
prospectively named `blocking_gate_id`. The objective first binds that gate in a
separate revision as
`{blocking_gate_id, transition, target_stage, authority_ref}`; one active gate
is unique and blocks only the exact transition/stage. It clears only with one
observed `SENT` reply and a locally absorbed validation terminal in that same
transition. One physical conversation has at most one in-flight entry. Active
and absorbed scopes are unique by `(candidate_id, scope_sha256)`; changing
`scope_revision` cannot resubmit the same scope. Absorption appends
`{candidate_id, scope_sha256, local_validation_terminal_event_id}` to
`absorbed_advisory_scopes`. Prompt, reply, summary, sources, conclusions,
metrics and protected content never enter the snapshot.

Every new snapshot advisory begins `AWAITING_RESPONSE/NONE`. Only the dedicated
`claim-advisory-wake` and `complete-advisory-wake` CAS operations may advance it
to `RESPONSE_OBSERVED/CLAIMED` and then `SENT`; generic replacement cannot seed,
claim or complete response metadata.

After response delivery and local verification, a `NON_BLOCKING` batch may be
removed by `absorb-nonblocking-advisory`, which atomically appends its local
terminal ID and consumed scope without changing objective lifecycle. A
`BLOCKING_HIGH_RISK` batch is rejected by that command and clears only inside
its exact `activate-successor` or `close-objective` transition.

Closed scopes use one explicit closure basis. `VALID_SCIENTIFIC_NEGATIVE`
requires an independent Audit, eligible evidence, a prospective action table,
and a valid power/futility gate. `PROSPECTIVE_SCOPED_MPE_FAILURE` is narrower:
it requires a completed finite cell, failure of its preregistered MPE,
independent locally verified adversarial review, and an explicit preserved
scope boundary; it must record `powered_negative_claimed=false` and cannot be
reported as a powered population negative. `EXTERNAL_IMPOSSIBILITY` remains
limited to allowlisted unavoidable external reasons. Use the state tool's
`close-objective` CAS so terminal absorption, owner release, and the exact
closure record are one revision.

## 5. Evidence and claim eligibility

Preserve every run and engineering failure, but only eligible runs may back
verified scientific evidence. A completed run is evidence-eligible only when:

- every declared validation command passed and `protocol_deviations` is empty;
- the protocol was frozen no later than run start;
- its question, exact code identity, config digest, dataset, seeds, and primary
  metrics match its prospective `protocol.run_bindings[run_id]`; and
- all referenced local artifacts exist and match canonical SHA-256 digests.

An ineligible run remains readable as unverified diagnostic history. It cannot
back `verified` experiment/negative evidence, a supported claim, or an accepted
claim. Test exit zero and artifact presence never establish scientific value.

Schema 1.3 verified evidence includes:

```json
{
  "evidence_id": "E014",
  "kind": "negative_result",
  "summary": "No material effect under the frozen Scout contract.",
  "run_id": "R20260714-003",
  "producer_worker_id": "B1-executor",
  "provenance": {
    "source": "artifacts/R20260714-003/metrics.json",
    "captured_at": "2026-07-14T08:30:00Z",
    "artifact_sha256": "<sha256>"
  },
  "verification": {
    "status": "verified",
    "verifier_worker_id": "B1-audit",
    "verified_at": "2026-07-14T08:35:00Z"
  },
  "supports_claims": ["C006"],
  "limitations": ["Frozen carrier only"]
}
```

Evidence kinds are `source`, `experiment`, `observation`, `negative_result`, and
`diagnostic`; verification states are `unverified`, `partial`, and `verified`.
Evidence-to-claim links are bidirectional: every `supports_claims` target names
that evidence ID, and every claim evidence ID points back to that claim.

An accepted claim requires verified eligible evidence and an adjudication with
`decision`, `reviewer_role`, registered `reviewer_worker_id`,
`independent=true`, rationale, and `decided_at` after evidence verification.
The adjudicator is distinct from both producer and verifier.

## 6. Run manifest

Create `runs/<run-id>.json` before execution. The manifest binds at least:

```json
{
  "schema_version": "1.0",
  "run_id": "R20260714-003",
  "task_id": "example-1234abcd",
  "status": "completed",
  "question": "Does the frozen problem effect exceed MPE?",
  "code_version": {"git_commit": "<sha>", "dirty": false},
  "config": {"path": "configs/scout.yaml", "sha256": "<sha256>"},
  "dataset": {"name": "<name>", "version": "<version>", "split": "<split>"},
  "environment": {"host": "<host>", "accelerator": "<accelerator>"},
  "seeds": [1, 2, 3, 4, 5, 6],
  "primary_metrics": ["<metric>"],
  "started_at": "2026-07-14T07:00:00Z",
  "ended_at": "2026-07-14T08:30:00Z",
  "artifacts": [{"path": "artifacts/R20260714-003/metrics.json", "sha256": "<sha256>"}],
  "validation": [{"command": "<exact command>", "status": "pass"}],
  "result_summary": "<bounded summary>",
  "anomalies": [],
  "protocol_deviations": []
}
```

Use stable IDs, never `latest`, `new`, or `final2`. Preserve malformed, failed,
and deviated runs; classify them as engineering/diagnostic rather than deleting
or expanding them into scientific negatives.

## 7. Status transitions

Task statuses are `draft`, `ready`, `running`, `waiting_external`,
`needs_approval`, `completed`, and `blocked`.

```text
draft -> ready -> running -> completed
                   |  |-> waiting_external -> running
                   |  |-> needs_approval -> running
                   |  `-> blocked
                   `----> ready (only after a prospective amendment)
```

Budget exhaustion is not completion. `blocked` names one concrete blocker and
reopening check; it is not a scientific `DROP`. Only an actual `HARD_BLOCK`
stops evidentiary execution. A `CHALLENGE` or `POLISH` item cannot silently
become a readiness gate.
