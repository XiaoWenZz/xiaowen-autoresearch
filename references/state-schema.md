# State schema

Use this reference when initializing, resuming, repairing, or validating a research task.

## Contents

1. Directory contract
2. Governance tracks
3. State ownership
4. Record schemas
5. Run manifest
6. Status transitions

## 1. Directory contract

This full directory is for **Managed Scout** and **Confirmatory** work. Do not
create it for a Scout Lite already governed by a repository `AGENTS.md` unless
unattended recovery, multiple writers, leases, paid execution, or promotion
compatibility creates a concrete need.

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
├── runs/                 # one immutable manifest per run ID
├── artifacts/            # raw outputs and derived artifacts
├── logs/
│   └── events.jsonl
└── reports/              # handoff, audit, or final reports
```

Keep JSONL append-only. Correct a record by appending a superseding record that names `supersedes_id`; do not rewrite history.

The helpers create this durable skeleton only for Managed Scout and full
Confirmatory work. In Scout, `directions.jsonl`, `evidence.jsonl`, and
`claims.jsonl` may remain empty; this preserves promotion compatibility without
forcing premature claim bureaucracy.

### Scout Lite minimum

```text
<existing-repo>/
├── AGENTS.md
├── <protocol-or-config>       # frozen question, metric, baseline, data/seed/budget/claim boundary
├── <run>/manifest.json        # unique code/config/data/environment identity
├── <run>/raw-result.*
└── <outcome-record>           # recomputed gate, limitations, next decision
```

One file may cover protocol and config. One terminal result may cover manifest
completion and outcome. Do not duplicate identical identities across files
solely to satisfy a template.

## 2. Governance tracks

`charter.json` must set `governance_track` to `scout` or `confirmatory` and
`operating_weight` to `managed` or `full` for newly initialized durable tasks.
The valid pairs are `scout/managed` and `confirmatory/full`. Scout Lite uses the
minimum repository contract above and does not initialize this state tree.
Legacy tasks without these fields validate with an inference warning.

### Scout

Required before execution:

- a grounded problem thesis or, when the problem is still hypothesized, an
  explicit problem-existence objective;
- frozen question, hypothesis, scope, primary metric, strongest baseline, and claim boundary;
- explicit `protocol.data_boundary`, data/code identity where applicable, seed or schedule policy, analysis plan, fixed budget, and stop conditions;
- for method-search Scouts, applicable federation/PEFT/dynamic/operation
  deletion results and a positive/negative/ambiguous outcome decision table;
- `governance.pre_evidence_iteration_budget` (default 2) and a `promotion_trigger`;
- pre-run manifest and raw artifacts for every evidentiary execution.

A Scout may produce only a `SCOUT_SIGNAL`, scoped negative result, diagnostic, or carrier-level stop. It may not contain an `accepted` claim.

For Scout Lite, these fields live in the protocol/config and manifest rather
than `charter.json`. The semantic requirements remain; the directory skeleton
does not.

### Confirmatory

Use the full direction, evidence, claim, verification, and adjudication graph. Confirmatory is required before public-test access, publication-facing method comparison, expensive or irreversible evidence collection, or accepting a scientific claim.

Promotion requires a timestamped charter amendment, a frozen confirmation protocol, a fresh confirmation set, and updated `progress.governance_track`. Do not relabel already observed Scout outcomes as independent confirmation.

Suggested charter fields:

```json
{
  "program_id": "<stable Program id>",
  "epoch_id": "<stable Epoch id>",
  "governance_track": "scout",
  "operating_weight": "managed",
  "governance_admission_proof": "<exact Scout Lite limitation requiring durable state>",
  "problem_thesis": "<affected population, failure, decision unit, deployment constraint, evidence status>",
  "specificity": {
    "federation_deletion": "<survives|broadens|fails|not_applicable>",
    "peft_deletion": "<survives|broadens|fails|not_applicable>",
    "dynamic_deletion": "<survives|broadens|fails|not_applicable>",
    "operation_deletion": "<survives|broadens|fails|not_applicable>"
  },
  "strongest_baseline": "<matched strongest reduction or baseline>",
  "claim_boundary": "<exact statement this task may support or falsify>",
  "governance": {
    "pre_evidence_iteration_budget": 2,
    "promotion_trigger": "<predeclared gate for confirmatory promotion>",
    "outcome_actions": {
      "positive": "<exact promotion action>",
      "negative": "<exact closure or narrowing action>",
      "ambiguous": "<one predeclared diagnostic or hold>"
    }
  },
  "protocol": {
    "data_boundary": "<allowed splits and forbidden evaluation access>"
  }
}
```

## 3. State ownership

| File | Writer | Meaning |
|---|---|---|
| `charter.json` | owner/orchestrator | Frozen objective, protocol, budget, and permissions |
| `progress.json` | orchestrator | Current phase, iteration, next action, blockers, stale count |
| `heartbeat.json` | current worker | Liveness lease only; never scientific progress |
| `directions.jsonl` | orchestrator | Structural directions and explicit replications |
| `evidence.jsonl` | worker/verifier | Observations with provenance and verification state |
| `claims.jsonl` | author/verifier/adjudicator | Claim lifecycle and evidence links |
| `iterations.jsonl` | orchestrator | One outcome record per completed iteration |
| `approvals.jsonl` | owner/orchestrator | Requested and decided authorization changes |
| `workers.jsonl` | controller/orchestrator | Append-only worker dispatch, callback delivery, acknowledgement, reclamation, and watchdog state |
| `runs/*.json` | worker | Reproducibility manifest for one execution |
| `logs/events.jsonl` | all roles | Operational events and decisions |

Allow only one active orchestrator lease. Guardians may refresh/check liveness, restart a worker, or request attention; they must not edit evidence or adjudicate claims.

## 4. Record schemas

All timestamps use RFC 3339 UTC, such as `2026-07-14T08:30:00Z`. IDs are stable strings unique within the task.

### Worker and callback

Use one immutable record per worker state transition. Keep `worker_id` stable
and give every appended transition a unique `worker_record_id`. The latest
valid record is current state.

```json
{
  "worker_record_id": "WR-B1-003",
  "worker_id": "B1-evidence-worker",
  "thread_id": "019f...",
  "program_id": "P1",
  "epoch_id": "P1-E1",
  "contract_revision": "v0",
  "role": "evidence-worker",
  "status": "completed",
  "callback_state": "acknowledged",
  "terminal_event_id": "TERM-B1-001",
  "reclaim_deadline": null,
  "watchdog_id": "monitor-b1",
  "watchdog_state": "paused",
  "artifact_paths": ["artifacts/B1/outcome.json"],
  "recorded_at": "2026-07-22T09:00:00Z",
  "supersedes_id": "WR-B1-002"
}
```

Allowed worker statuses are `dispatched`, `running`, `needs_attention`,
`completed`, `failed`, `cancelled`, and `reclaimed`. Allowed callback states are
`pending`, `delivered`, `acknowledged`, and `not_available`. A delivered or
acknowledged callback requires a stable `terminal_event_id`; duplicate terminal
events must not create a second adjudication. `not_available` requires an
explicit reclaim deadline. An acknowledged terminal requires its watchdog to
be `paused` or `not_required`. Allowed watchdog states are `active`, `paused`,
and `not_required`; use `active` at dispatch when a fallback watchdog exists.
Delivery and acknowledgement may be separate records, but an atomic controller
read-and-ack may append `acknowledged` directly without a synthetic delivered
record.

For schema `1.2+`, a terminal `acknowledged` record must also contain:

```json
{
  "controller_action": {
    "transaction_id": "CTX-B1-001",
    "disposition": "accept Stage A only",
    "next_action": "dispatch_next",
    "worker_notified": true,
    "decided_at": "2026-07-22T09:00:00Z",
    "next_worker_record_id": "WR-B1-004",
    "next_contract_revision": "cycle0b-v0"
  }
}
```

Allowed `next_action` values are `dispatch_next`, `explicit_hold`,
`owner_approval_required`, and `scoped_close`. `dispatch_next` requires a later
active worker record with the named record ID and contract revision. The same
terminal event must retain one stable transaction ID. A latest terminal
`delivered` record is an incomplete controller transaction and fails
validation until it is acknowledged; message delivery or scientific
adjudication alone is not closure.

### Direction

```json
{
  "direction_id": "D003",
  "iteration": 3,
  "hypothesis": "The effect is caused by initialization rather than aggregation.",
  "mechanism": "Controlled initialization ablation",
  "changed_variables": ["initialization_policy"],
  "expected_observation": "The gap disappears under matched initialization.",
  "structural_delta": "Replace deployment tuning with a causal control.",
  "fingerprint": "init-ablation-matched-seeds-v1",
  "is_replication": false,
  "status": "planned"
}
```

For a replication, set `is_replication: true` and add `replicates_direction_id`.

### Evidence

```json
{
  "evidence_id": "E014",
  "kind": "negative_result",
  "summary": "Matched initialization did not close the gap on QNLI seed 43.",
  "run_id": "R20260714-003",
  "provenance": {
    "source": "artifacts/R20260714-003/metrics.json",
    "captured_at": "2026-07-14T08:30:00Z",
    "artifact_sha256": "<sha256>"
  },
  "verification": {
    "status": "verified",
    "method": "Recomputed with scripts/validate_metrics.py",
    "verified_at": "2026-07-14T08:35:00Z"
  },
  "supports_claims": ["C006"],
  "limitations": ["One task and one seed"]
}
```

Allowed evidence kinds: `source`, `experiment`, `observation`, `negative_result`, and `diagnostic`. Allowed verification states: `unverified`, `partial`, and `verified`.

### Claim

```json
{
  "claim_id": "C006",
  "claim_type": "inference",
  "text": "Initialization alone is unlikely to explain the observed gap.",
  "status": "challenged",
  "evidence_ids": ["E014"],
  "scope": "QNLI, seed 43, matched-budget protocol",
  "limitations": ["Not yet replicated across seeds"],
  "adjudication": null
}
```

Allowed claim types: `fact`, `inference`, and `hypothesis`. Allowed statuses: `proposed`, `supported`, `challenged`, `rebuttal-ready`, `pending-rebuttal`, `accepted`, `rejected`, and `withdrawn`.

An accepted claim requires verified evidence and an adjudication object containing `decision`, `reviewer_role`, `independent: true`, `rationale`, and `decided_at`. The worker that generated the evidence cannot be the sole adjudicator.

### Iteration

```json
{
  "iteration_id": "I003",
  "iteration": 3,
  "direction_id": "D003",
  "started_at": "2026-07-14T07:00:00Z",
  "ended_at": "2026-07-14T08:40:00Z",
  "outcome": "negative_result",
  "evidence_ids": ["E014"],
  "validation": [{"command": "python3 -m pytest tests/test_metrics.py", "status": "pass"}],
  "next_action": "Replicate on seeds 42 and 44 before changing the claim."
}
```

Allowed outcomes: `progress`, `negative_result`, `replication`, `diagnostic`, `stale`, and `blocked`. Only `stale` increments consecutive `stale_count`; all evidence-bearing outcomes reset it.

### Approval

```json
{
  "approval_id": "A002",
  "action": "increase_compute_budget",
  "scope": "Add two A100 seed replications, maximum 8 GPU-hours",
  "status": "approved",
  "requested_at": "2026-07-14T08:45:00Z",
  "decided_at": "2026-07-14T09:00:00Z",
  "expires_at": "2026-07-15T09:00:00Z"
}
```

## 5. Run manifest

Create `runs/<run-id>.json` before execution. For a completed experimental run, include:

```json
{
  "schema_version": "1.0",
  "run_id": "R20260714-003",
  "task_id": "example-1234abcd",
  "status": "completed",
  "question": "Does matched initialization close the gap?",
  "hypothesis_ids": ["H001"],
  "code_version": {"git_commit": "<sha>", "dirty": false},
  "config": {"path": "configs/init_ablation.yaml", "sha256": "<sha256>"},
  "dataset": {"name": "QNLI", "version": "<version>", "split": "validation"},
  "environment": {"host": "cluster-a", "accelerator": "A100", "software": "environment.lock"},
  "seeds": [43],
  "primary_metrics": ["accuracy"],
  "started_at": "2026-07-14T07:00:00Z",
  "ended_at": "2026-07-14T08:30:00Z",
  "artifacts": ["artifacts/R20260714-003/metrics.json"],
  "validation": [{"command": "python3 scripts/check_run.py R20260714-003", "status": "pass"}],
  "result_summary": "No material gap reduction.",
  "anomalies": [],
  "protocol_deviations": []
}
```

Never use labels such as `latest`, `new`, or `final2` as run IDs. Use stable IDs and immutable manifests.

## 6. Status transitions

Use task statuses `draft`, `ready`, `running`, `waiting_external`, `needs_approval`, `completed`, and `blocked`.

```text
draft -> ready -> running -> completed
                   |  |-> waiting_external -> running
                   |  |-> needs_approval -> running
                   |  `-> blocked
                   `----> ready (only after a recorded protocol amendment)
```

Do not mark `completed` because a budget ended. Report incomplete work explicitly. Use `blocked` only when a concrete blocker prevents meaningful in-scope progress and the recovery attempts are recorded.

For `progress.blockers`, prefer objects with `severity` (`HARD_BLOCK`, `CHALLENGE`, or `POLISH`), `description`, `decision_impact`, and `next_check`. Only a `HARD_BLOCK` justifies blocking evidentiary execution.
