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
