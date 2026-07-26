# Global research lanes

Use this reference when a controller dispatches or closes persistent research
work. It fixes one concrete failure: a route-local terminal must not strand the
global zero-GPU or Pro capacity.

## Invariant

Maintain these portfolio fields independently:

```text
gpu_running
gpu_queue
zero_gpu_running
result_analysis_queue
pro_advisory_lane
```

`GPU queued` means an implementation is ready to wait for compute. It does not
mean research is globally blocked. Unless GPU evidence is ready for analysis,
the zero-GPU lane moves to the next bounded problem-space Opportunity Search
whose output remains useful under every pending GPU outcome.

`explicit_idle` is exceptional and fail-closed. It is valid only when:

1. no result-analysis item is ready;
2. no admitted current-route source/code/algebra task exists;
3. every GPU-queue prerequisite has been classified;
4. every partial or non-exhaustive neighbor audit has been classified;
5. new-problem Opportunity Search is either blocked by one reopening fact or
   its prospectively frozen search budget is exhausted; and
6. no decision-ready Pro review is waiting while a Pro slot is available.

Do not use lack of an immediately executable experiment as proof of global
idle.

Before admitting or retaining any GPU queue entry, reconcile it against the
latest durable authority in this order:

```text
validated experiment record
> durable terminal packet
> frozen prospective contract
> LLM-Wiki synthesis
> operational chat state
```

Wiki or atlas state may nominate a candidate, but it cannot override a newer
qualification hold, generic-artifact routing, source-governance hold, budget
hold or terminal cancellation. Bind each queue entry to the latest checked
authority ID, evidence path, owner, launch prerequisite and the explicit
`queue_gpu` disposition. A ready result-analysis item likewise binds the
terminal ID and evidence path that made it ready.

## Atomic terminal transaction

Handle a terminal in this order:

```text
read durable evidence and limitations
-> apply the scoped disposition
-> ACK the idempotent terminal event
-> recompute the global portfolio queue
-> start result analysis, dispatch one admitted successor, or validate idle
-> retarget or pause the old callback fallback
-> return to the owner
```

Do not mark the transaction complete between ACK and portfolio reconciliation.
A task-specific worker may recommend a local next action, but only the
controller may set global lane status.

GPU result analysis preempts ordinary Opportunity Search. Finish or checkpoint
the bounded search task without reading the result, then run the frozen
result-analysis contract. Resume search only after the scientific route is
rerouted.

## Legitimate Opportunity Search versus filler

A new problem-space search is admitted only when it has:

- one named scientific or deployment decision that could change;
- a bounded user/domain boundary and search clock;
- a distinct actor, target estimand or causal bottleneck rather than a renamed
  carrier, selector, rank, seed or checkpoint;
- a primary-source and operation-neighbor plan;
- a cheapest decision-complete witness;
- a cap of three active briefs and one selected Scout;
- work useful under all feasible outcomes of pending GPU jobs; and
- a terminal of `QUEUE_GPU`, `HOLD` with one reopening fact, or `DROP` with a
  scoped reason.

Search is filler when it merely consumes idle capacity, repeats a closed causal
fingerprint, prebuilds a downstream method, produces no decision-changing
output, or has no bounded stop condition.

## ICLR-targeted innovation contract

For a publication objective such as the September ICLR deadline, use two
different gates.

Before GPU queue placement, require a dated bounded neighbor map:

- exact object/method neighbors;
- partial-operation neighbors;
- generic or classical preserving reductions;
- relevant appendix and robustness evidence;
- occupied claims;
- the residual actor-level question;
- strongest simple baseline; and
- cheapest problem-existence witness.

This gate prevents obvious duplication. It does not assert novelty and must not
reject a cheap problem measurement merely because complete publication novelty
is not yet proved.

After a material Scout signal, require the Contribution Gate to resolve:

- material importance in the target decision unit;
- surviving novelty residual against verified primary neighbors;
- irreducibility against jointly feasible preserving reductions;
- mechanism identifiability beyond the repair contrast;
- federation and PEFT specificity at the exact level claimed;
- evidence scalability across adequate carriers, seeds and uncertainty units;
- a feasible confirmation path before the submission freeze; and
- the strongest reviewer objection with one fair decision-changing test.

A failure of narrow FedFT specificity routes a valid broader artifact; it does
not erase the observed problem. A closed novelty residual blocks the method
claim before paper-scale implementation. Do not use Pro or an LLM score as
novelty authority; verify every decision-critical source locally.

## Minimal durable snapshot

Keep one compact JSON snapshot in the existing controller or Program ledger.
Do not create a new state tree. Validate it before reporting terminal closure:

```bash
python3 scripts/reconcile_research_lanes.py /path/to/research-lanes.json
```

The snapshot records:

- the controller thread;
- current GPU task and ordered GPU queue;
- current zero-GPU task and bounded backlog;
- ready result-analysis tasks;
- Opportunity Search state;
- terminal callback/ACK/watchdog/next-action state;
- live and queued Pro reviews; and
- an idle proof only when `zero_gpu_running=explicit_idle`.

Every GPU queue item also records `latest_authority` with
`checked_against_latest_terminal=true`, its source kind, authority ID, evidence
path and `queue_disposition=queue_gpu`. This prevents a current hold from being
silently replaced by an older Wiki or atlas state.

The helper checks orchestration consistency only. It does not schedule work,
inspect remote state, authorize compute, or establish scientific novelty.
