---
name: xiaowen-autoresearch
description: "Run or recover bounded research from broad opportunity discovery through problem-existence Scouts, contribution selection, confirmation, verification, adjudication, and handoff. Use for autonomous or long-horizon literature, ML or systems research, direction search, evidence-bounded Pro or external-review prompt construction, remote experiment loops, claim audits, stalled projects, and repeated pivots. Separates high-recall opportunity admission from publication-grade novelty and irreducibility gates while preserving fixed budgets, reproducible evidence, positive-signal attribution, and scoped closure. Do not use for one-off questions, a single code edit, or unbounded unattended execution."
---

# Xiaowen AutoResearch

Optimize for decision-relevant evidence per unit cost. Preserve research
integrity without turning early discovery into a publication-readiness exam.

## Route the request

Choose one primary mode:

- **Opportunity Search**: compare bounded, testable problem theses and select a
  cheap witness; optimize recall without requiring a paper-ready contribution.
- **Problem Scout**: execute one reversible problem-existence or mechanism
  witness.
- **Contribution Gate**: after a signal, select the honest artifact and apply
  novelty, irreducibility, specificity, and paper-path tests.
- **Setup / Iterate**: create a bounded charter or execute the next falsifiable,
  budgeted step.
- **Recover**: reconstruct live state after interruption or context compaction.
- **Verify**: audit evidence, reproduction, citations, statistics, or claim strength.
- **Adjudicate**: resolve challenged claims after rebuttal and review.
- **Handoff**: stop active work and leave a reproducible continuation record.

Keep `Opportunity Search -> Problem Scout -> Contribution Gate ->
Confirmatory` distinct. An opportunity can be worth measuring before novelty,
specificity, or paper path is resolved. A positive Problem Scout is not method
evidence; a failed Contribution Gate does not erase the observation.

Choose the governance track first, then its operating weight:

- `governance_track=scout`: bounded, reversible problem-existence or mechanism
  evidence. Use `operating_weight=lite` by default; use `managed` only when
  unattended recovery, multiple workers/sessions, paid execution, or a
  persistent lease requires durable state.
- `governance_track=confirmatory`: public-test access, accepted or publication-
  facing claims, or expensive/irreversible evidence. Use
  `operating_weight=full` and independent adjudication.

Before changing weight or track, record a **governance-admission proof** naming
the exact trigger. Existing helpers, workflow familiarity, or a preference for
more bookkeeping are not admission reasons.

## Controller-worker session architecture

For a long-running or multi-session Program, use a persistent controller plus
bounded work sessions. The controller owns routing (`probe/hold/drop`), frozen
contracts, Program/Epoch budgets, worker registration, and the next scientific
decision. It records claim adjudication but must not self-accept a Confirmatory
or publication-facing claim. Keep owner authorization and independent claim
adjudication separate as specified in
[references/orchestration.md](references/orchestration.md).

Give each work session one frozen uncertainty and require evidence,
limitations, validation, and artifact paths. Register an event-driven return
path and an idempotent terminal event; use a low-frequency heartbeat only as a
lost-callback watchdog. Use subagents only for bounded, outcome-invariant
execution fan-out. Neither another session nor a same-model subagent is
external scientific replication. Session architecture alone does not admit
Managed Scout.

A terminal callback is a high-priority controller state transition, not
ordinary conversational context. Before returning to unrelated work, complete
the schema-defined callback transaction: evidence read, scoped disposition,
worker notification, idempotent acknowledgement, completed-event watchdog
pause, and exactly one committed next action. Message delivery or scientific
adjudication alone is not callback closure.

Use **callback-first terminal ordering** for every persistent Codex work
session. The dispatch prompt must name the controller thread, an idempotent
terminal-event key, and the callback mechanism. At terminal, the worker must:

1. write and validate the durable terminal evidence;
2. call `send_message_to_thread` (or the runtime's equivalent push callback)
   to the named controller and receive a successful tool receipt;
3. only then emit its own local final response.

A local final response without a confirmed push receipt is
`callback_delivery=unconfirmed`, not a completed handoff. Immediately after
dispatch, the controller must retain the `wait_threads` cursor and create or
retarget one low-frequency lost-callback fallback. That fallback may recover a
completed final exactly once by terminal event or final-turn ID, but it is not
the normal delivery path. Never rely on the worker's local final response alone
to wake the controller.

## Read before acting

1. Read every applicable `AGENTS.md`; identify repository, branch, remote, target environment, and permitted scope.
2. Read [references/problem-space.md](references/problem-space.md) before grounding or reframing an opportunity and before applying specificity or preserving-reduction tests.
3. Read [references/portfolio-search.md](references/portfolio-search.md) before Opportunity Search, candidate ranking, Contribution Gate, or negative synthesis.
4. Read [references/research-programs.md](references/research-programs.md) before opening or revising a multi-candidate Program/Epoch, starting a second Scout, changing mechanism families, or continuing after repeated route closures.
5. Read [references/state-schema.md](references/state-schema.md) only before creating, resuming, or validating Managed/Confirmatory task state.
6. Read [references/research-integrity.md](references/research-integrity.md) before evidence, literature closure, gate changes, or claims.
7. Read [references/orchestration.md](references/orchestration.md) before work sessions, unattended loops, subagents, callbacks, remote jobs, recovery, or structural pivots.
8. Read [references/research-map-maintenance.md](references/research-map-maintenance.md) before creating or updating an editable research map and whenever a milestone handoff names one.
9. Read [references/external-opportunity-search-prompts.md](references/external-opportunity-search-prompts.md) before constructing a Pro, Deep Research, human-review, or other external Opportunity Search prompt; start from [assets/opportunity-search-prompt-template.md](assets/opportunity-search-prompt-template.md) when a reusable prompt artifact is requested.

## Non-negotiable controls

Apply these to both governance tracks:

- Freeze the question, hypothesis, primary metric, strongest relevant baseline, data/leakage boundary, seed or schedule policy, fixed budget, stop condition, and exact claim boundary before evidentiary execution.
- Create a run manifest before execution; preserve code/config/data/environment identity, raw outputs, failed runs, anomalies, and deviations.
- Separate liveness, engineering progress, scientific progress, and claim status. A heartbeat proves only that a process is alive.
- Count falsification, negative results, justified replication, and resolved diagnostics as progress when they reduce uncertainty.
- Never let a worker accept its own claim. A separate session of the same model is procedural review, not external scientific replication.
- Honor an explicit owner standing delegation for narrowly defined pre-outcome
  integrity repairs. The controller may auto-approve and continue in the same
  work session only when the repair is deterministic, source-traceable,
  leakage- or reproducibility-strengthening, outcome-blind, inside the frozen
  source universe, and preserves actor, estimand, planned sample counts, seeds,
  metrics, strongest baselines, budget, stopping rule, analysis, outcome table,
  and claim boundary. Record one dated amendment and fail closed when any
  condition is uncertain. Do not turn standing delegation into authority for
  public-test access, outcome-conditioned preprocessing, budget/claim changes,
  destructive/external actions, or stage promotion.
- Treat requests to continue until a good, significant, or publishable result as authorization for persistent bounded search, never for conditioning stopping, selection, thresholds, or reporting on a favorable outcome.
- When freshness, prospectiveness, held-out status, or Tier P is
  decision-critical, append relevant metadata, claim, source, data, result,
  model, and design access to one cross-task exposure ledger and validate it
  before freeze and first linked access. Do not impose this ledger on work that
  makes no freshness or held-out claim.
- Store no secrets in state, prompts, manifests, logs, or reports.

## Scientific sequencing

- Ground one measurable problem thesis before generating solution candidates.
  Identify who incurs what loss, under which federation/deployment constraints,
  in which decision unit, on what adequate carrier, and against which simple
  practice. A conjectured but concrete problem may enter a bounded
  problem-existence witness; it may not yet justify a named method.
- Interpret **method-first** as choosing the intended contribution type, not as
  implementing the method first. Execution remains problem-first and
  signal-first.
- Apply the federation-, PEFT-, dynamic-decision-, and operation-deletion tests
  in [references/problem-space.md](references/problem-space.md). A candidate
  that survives only after adding an arbitrary domain label is not specific;
  reframe it at the broader level when that broader thesis remains inside the
  user's actual boundary. Specificity failure blocks only the specificity claim.
- Before implementing a new method or an expensive baseline reproduction,
  freeze one contribution sentence, the nearest primary-source neighbors, the
  target estimand, and the cheapest observation that would show the proposed
  mechanism is actually needed. If novelty is already closed, pivot before
  building the method.
- Preserve one living neighbor table from Opportunity Search through every
  handoff. Classify `exact`, `partial-operation`, and `generic-reduction`
  neighbors, search by operation as well as method name, and carry relevant
  appendix/robustness results forward. A partial/missing search terminal or a
  `non-exhaustive` audit leaves novelty at `CHALLENGED_NEIGHBOR`; no exact
  isomorphic paper is not evidence of novelty. Keep this to one bounded table
  and decision record, not a verifier or state family.
- Before assigning empirical budget, run the zero-compute falsification ladder
  in [references/problem-space.md](references/problem-space.md): inspect the
  operative source definition and implementation, normalize the proposal to
  its represented function or state, test algebraic invariances and preserving
  reductions, and construct the smallest positive, null, and nuisance cases.
  State the unresolved empirical remainder. Do not run an experiment to answer
  a source-reading, implementation-definition, or algebraic-equivalence
  question.
- Before a mechanism Scout, state one necessary mechanism-support condition,
  the carrier statistic that reveals it, and a mechanism-deletion control that
  preserves the remaining information, state, work, and cost. Check the
  condition before method comparison. If it is absent or unidentifiable, use
  the run only as a fixture/problem-existence witness or close the scoped route.
- Separate a **repair contrast** against a known broken or naive baseline from
  the **contribution contrast** against the strongest valid simpler
  alternative. A large repair effect does not establish the claimed mechanism,
  collaboration, or method kernel when local-only, no-op, static, matched-state,
  or generic-operator behavior explains it.
- When the contribution is not yet locked, compare at most three active
  opportunity briefs. Apply problem-level hard exclusions before a Problem
  Scout. Defer venue viability, full novelty, and method irreducibility to the
  Contribution Gate after a material signal.
- Bound repeated search inside one Research Program and Research Epoch as
  defined in [references/research-programs.md](references/research-programs.md).
  Portfolio revisions, new names, sessions, repositories, or carrier swaps do
  not reset cumulative candidate, Scout, review, or pivot budgets.
- Treat venue viability as a post-signal planning decision, not a
  problem-measurement prerequisite, acceptance prediction, or scientific
  result. Do not use an uncalibrated numeric reviewer or LLM score as a gate.
- Establish problem existence before method performance. Start with the most
  plausible bounded carrier and the strongest simple reduction; do not build a
  controller merely because scores, gradients, magnitudes, or raw argmax labels
  vary.
- Treat `problem existence -> mechanism necessity -> method kernel ->
  confirmation` as a dependency chain. An upstream gate authorizes only its
  immediate successor. Do not prebuild a downstream method, benchmark matrix,
  verifier family, or review package while a parent gate can still close the
  route. Parallel work is admissible only when it remains useful under every
  feasible parent outcome.
- Require the first witness to be decision-complete: before execution, map a
  positive, negative, and ambiguous outcome to one exact promotion, closure, or
  predeclared diagnostic action. If every outcome merely generates more
  variants, the witness is not decision-relevant and must be redesigned.
- Open an empirical Scout only when at least one feasible outcome changes the
  next scientific decision and no cheaper source, code, algebraic, cached-
  artifact, or deterministic micro-check can answer the same uncertainty.
  Reuse the portfolio ledger to record this experiment-worthiness check; do
  not create another approval or state artifact.
- Enter a **Theory Gate** before opening another artifact or carrier Scout when
  the project explicitly declares theory-first, or when two carrier-level stops
  expose the same identification or information bottleneck. Freeze the
  contribution sentence and target estimand, strongest preserving reduction,
  candidate theorem with assumptions and failure conditions, positive/null/
  nuisance counterexamples, minimum data contract, and one falsifying
  observation. Exit by selecting a theorem-discriminating witness, revising the
  claim, or closing the route. Do not impose this gate on every empirical Scout.
- Delay publication-grade baseline reproduction, public-test access, and
  matched multi-seed comparison until the problem-existence Scout passes,
  unless reproduction is itself the frozen objective or is necessary to
  interpret the Scout.
- Write the evidence chain from every cheap proxy to the final target estimand.
  An uncalibrated local, common-state, short-horizon, or validation-only proxy
  may gate promotion, but cannot by itself establish full-trajectory
  superiority, permanent scientific closure, or a field-level conclusion.
- When introducing a new diagnostic or promotion gate, include a known positive
  control and a negative or static control when feasible. Synthetic controls
  may calibrate sensitivity but cannot support the real-world method claim.
- Before trusting a new or materially changed Opportunity Search gate, test a
  broad-domain gate on at least three retrospective positives at their
  pre-signal information states and three obvious negatives/duplicates. Every
  positive must reach a cheap probe and every negative must stay out of one. If
  publication-stage unknowns reject a positive, the search gate is
  miscalibrated.
- Treat a change from method to benchmark, systems artifact, certificate, or
  reproduction as a Contribution-Gate reframe. Open a new charter only before
  collecting evidence for the new artifact; do not erase the existing signal.
- For a publication-targeted candidate, run the paper-path stress test at the
  Contribution Gate, after problem existence is established.

## Governance budget

- Freeze Program/Epoch identity, cumulative budgets, search clock, evidence
  clock, observation boundary, and remaining budget before evidence.
- Apply the action-admission, attention, circuit-breaker, and positive-signal
  attribution rules in
  [references/research-programs.md](references/research-programs.md); reuse one
  living ledger and never reset budget through a new name, session, carrier,
  repository, or context window.
- Produce the frozen Scout estimand within at most two outcome-blind engineering
  repairs or 20% of its total budget, whichever comes first. A repair is legal
  only when protected outcomes remain unread and model, data, split, metric,
  threshold, seed, baseline, and stopping policy are unchanged. Record each
  prospective patch, exact-path smoke, new run ID, and cumulative charge.
  After observing an estimand, reruns are replication or follow-up.
- Freeze decision invariants before evidence and record implementation identity
  at launch. Do not promote incidental filenames, hashes, or verifier identities
  into gates unless changing them could change the scientific decision.
- After the first material signal, apply the **post-signal evidence priority
  gate** in [references/research-programs.md](references/research-programs.md):
  permit at most one bounded repair and one witness-scoped recheck, cap
  governance-only attention at 20%, and use one proportionate verifier. A
  second distinct governance blocker before new scientific evidence forces
  claim/artifact downgrade or `HOLD`; do not open another governance version.
  Tests, commits, and governance artifacts are not scientific progress.
- Report the uncertainty retired, whether the next decision changed, actual
  compute/attention, retries, and decision-critical artifacts. A positive Scout
  is only `SCOUT_SIGNAL`, never an accepted method claim.

## Blocker taxonomy

Classify every objection before deciding whether work stops:

- **HARD_BLOCK**: leakage or invalid evaluation; unauthorized protocol/claim/budget change; missing strongest baseline for the primary comparison; identity/reproducibility failure that could change the result; unauthorized external or destructive action. Stop or repair before evidence collection.
- **CHALLENGE**: plausible novelty overlap, alternative mechanism, missing secondary ablation, engineering risk, or incomplete generalization. Record it and continue the cheapest discriminating Scout unless it becomes a hard block.
- **POLISH**: documentation, presentation, or non-decision-critical completeness. Defer until evidence warrants it.

Do not promote every concern into a gate. Do not hide a true hard block as “exploration.”

## Workflow

### Opportunity Search gate before step 0

- Freeze the Program/Epoch identity, actual user boundary, resource and
  attention budget, source scope, deadline, and at most three active
  opportunity briefs. Use one living ledger; do not create a new Portfolio file
  for each refresh.
- Use a fast three-pass default: `map <=45 minutes`, `top-three primary-source
  verification <=90 minutes`, and `decision <=15 minutes`. Reuse the existing
  portfolio/knowledge neighbor index, search object names and constituent
  operations, inspect backward references, recent forward neighbors and
  appendix/robustness results, then stop. Extend only for one named inaccessible
  primary source or unresolved preserving reduction.
- Spend at least 80% of idea-search attention on primary sources, operation
  mapping, reductions and falsification, and at most 20% on orchestration and
  records. Use one living table and one decision record; create no candidate
  repository, validator, schema or contract family during idea search.
- Separate a label-free divergent pass from the convergent audit. During the
  divergent pass, generate raw actor/decision/loss transitions across at least
  four problem spaces without novelty, venue, reviewer, `probe`, `hold`, or
  `drop` judgments. Only the convergent pass grounds, merges, and routes them.
- For each opportunity, record the affected actor, decision, failure status,
  target estimand and practical-effect floor, deployment/information
  constraints, strongest current practice, adequate controlled or natural
  carrier/source, cheapest witness, and a positive/negative/ambiguous action
  table.
- Record two independent states:
  `problem_admission = PROBE | HOLD_INFORMATION | HOLD_CARRIER |
  DROP_PROBLEM_EXACT_REDUCTION | DROP_NO_DECISION |
  ROUTE_BROADER_ARTIFACT`, and
  `contribution_forecast = UNASSESSED_PRE_SIGNAL | CHALLENGED_NEIGHBOR |
  LIKELY_REPAIR | LIKELY_GENERIC | PLAUSIBLE_IF_SIGNAL`. Never use the second
  state to determine the first.
- Apply source/code/algebra checks before compute. Drop an opportunity only
  when the actor-level problem is absent, solved by a verified and jointly
  feasible preserving reduction under matched information/cost/dynamics/
  deployment, unmeasurable under the contract, or no feasible outcome changes
  a decision.
- Before a multi-paper composition closes a problem, certify that its
  observables, operation order, client rendezvous, state/storage, objective and
  architecture, bytes/latency/compute, and deployment recipient coexist under
  one contract. Missing decision-critical feasibility is a challenge and
  baseline obligation, not a pre-signal closure.
- A source-grounded controlled carrier may establish scoped problem existence.
  Require a natural carrier pre-Scout only when natural occurrence constitutes
  the actor, event timing, resource limit, or information asymmetry; otherwise
  naturality is a Contribution/Confirmatory question.
- Unverified novelty, failed narrow specificity, missing paper path, or an
  occupied proposed method may block method promotion but do not block a cheap
  problem-existence probe when the underlying problem remains.
- Select at most one active Problem Scout. Prefer the cheapest decisive
  witness, then problem magnitude. Venue potential may break a tie but is not a
  hard admission gate.
- Before repository creation or GPU queue placement, require a dated
  `BOUNDED_NEIGHBOR_MAP_COMPLETE` record for the selected candidate containing
  exact, partial-operation and generic-reduction neighbors, occupied claims,
  residual operation, strongest simple baseline and cheapest witness. This is
  a bounded obvious-neighbor check, not publication-grade novelty proof.
  Missing it forces `HOLD_INFORMATION`, not speculative implementation.
- Keep at most one representative per causal fingerprint. Replacing a carrier,
  parameterization, selector, rank, checkpoint, or label is not a new
  opportunity when the distinct prediction is unchanged.
- If the bounded search exhausts its resources without a probe, report
  `SEARCH_BUDGET_EXHAUSTED_WITHOUT_SELECTION`. Use `NO_OPPORTUNITY_UNDER_<NARROW
  BOUNDARY>` only when the frozen problem family is narrow enough for that
  statement. Never report a field-level NO-GO from search exhaustion.
- Validate any materially changed broad admission rule on at least three
  retrospective positives at their pre-signal information states and three
  obvious negatives/duplicates before relying on it. Report false rejects and
  false admits.

### 0. Lock the Problem Scout and evidence chain

- Link the witness to the frozen problem thesis: affected population,
  current failure magnitude, deployment constraint, and decision unit.
- State the provisional artifact family without locking a paper contribution.
- Complete only the source/mechanism audit needed to avoid measuring a known
  identity or an already-solved actor-level problem. Defer full novelty and
  paper-path review to the Contribution Gate.
- Write `target estimand -> proxy estimand -> gate -> allowed claim`. Mark every
  unvalidated arrow. If the proxy-to-target arrow is unvalidated, the Scout may
  only decide promotion for that proxy contract.
- Name the strongest simple/static reduction and include its discovery or
  profiling cost when the deployment comparison requires total-cost fairness.
- Name the carrier statistic required for the claimed mechanism to operate and
  the strongest control that deletes only that mechanism. Make the primary
  contribution contrast prospective; a comparison only to a broken baseline
  can establish repair, not method necessity.
- Set the evidence-clock deadline and maximum decision-critical artifacts
  before implementation begins.
- Freeze `positive -> action`, `negative -> action`, and
  `ambiguous -> at most one diagnostic` before the first witness.

### 1. Establish the boundary

- Report repository, branch, remote, target environment, and scope before changing code, jobs, deployment files, or shared data.
- If the workspace is new, create its `AGENTS.md` before other project content.
- Choose and record `governance_track`, `operating_weight`, and the applicable
  governance-admission proof; classify intended actions using
  `references/orchestration.md`.

### 2. Initialize or recover state

For Scout Lite inside an existing repository, **do not initialize a parallel task-state tree**. Use the repository's `AGENTS.md`, one frozen protocol/config, a unique run manifest, raw artifacts, and a concise outcome record.

Use the state helpers only for a Managed Scout or full Confirmatory task whose unattended recovery, multiple workers, leases, approvals, or evidence/claim graph justify them. For a new Managed Scout:

```bash
python3 scripts/init_task.py <task-dir> \
  --title "<title>" \
  --objective "<objective>" \
  --task-type mixed \
  --governance-track scout \
  --max-iterations 6 \
  --max-runtime-hours 12
```

To add durable coordination state to an existing governed Scout repository
after a concrete Lite limitation is observed, first amend its `AGENTS.md` with
the governance-admission proof, then use the same command with
`--adopt-existing`. This mode must not overwrite the repository rules or
existing artifacts.

Use `--governance-track confirmatory` for a Confirmatory task. For an existing managed task, read:

1. task `AGENTS.md`;
2. `state/charter.json` and `state/progress.json`;
3. latest iteration, approval, heartbeat, and event records;
4. active run manifests and referenced artifacts.

Do not infer live state from conversation history when durable state exists.

### 3. Freeze the smallest sufficient charter

Record question, hypothesis, scope, success/failure criteria, primary metric, strongest baseline, protocol, data boundary, versions, seed policy, budget, authorization, and stop conditions. For Scout Lite, this may be one config or short protocol section. For managed state, run:

```bash
python3 scripts/validate_task.py <task-dir> --ready
```

Do not start evidentiary work until the chosen lightweight or managed freeze is complete. Preserve scientific changes as timestamped amendments; never rewrite history. Engineering repairs that leave the freeze byte-for-byte unchanged need a new run ID and anomaly record, not a new scientific contract.

For Scout, preregister only what is necessary to decide the frozen witness. For Confirmatory, also preregister statistical analysis, full comparison fairness, evidence/claim mapping, and adjudication.

When an applicable `AGENTS.md` names a project knowledge base, include its
question/project backlinks in each new, unfrozen charter using the workspace's
existing fields. Use the workspace's explicit null value when no reusable
knowledge delta is expected. Do not create a knowledge-base dependency in
workspaces that do not define one.

### 4. Design one bounded iteration

- Change one critical factor where practical.
- State hypothesis, expected observation, variables, controls, budget, and falsification condition before execution.
- Prefer validation-only audits and cached/cheap witnesses before training.
- Distinguish exploratory follow-up from confirmation.
- Reuse a direction only for explicit replication, bug repair, or robustness testing.

### 5. Execute within authorization

- Execute Class A actions directly.
- Execute Class B only when the charter names type, target, and budget.
- Stop for Class C approval; continue safe independent work when it cannot bias the pending decision.
- For a long job, verify submission and record ID, environment, logs, artifacts, and check/cancel commands. Do not continuously poll unless monitoring was requested.
- While a job, reviewer, scheduler, or approval is pending, do only
  action-admitted work that is useful under every feasible pending outcome.
  Do not spend downstream method, confirmation, or publication budget merely
  because wall-clock time is available.
- Run one real data/model end-to-end smoke before an immutable Scout attempt when cheap. Synthetic/unit coverage cannot substitute for the exact loader, state, mask, optimizer, and launch environment path.
- Repair ordinary in-scope engineering defects directly. Request new approval only when the repair crosses a Class C boundary; immutability of a failed run does not make an unchanged-protocol code fix a new research question.
- When the owner has prospectively delegated a bounded Class-C repair family as
  specified above, record the controller decision and execute it without a new
  owner round trip. Optimize for time to the frozen estimand, not approval
  volume.

### GPU / zero-GPU pipeline coupling

Schedule GPU execution and zero-GPU research as separate lanes connected by
durable artifacts:

```text
zero-GPU prepare or audit -> ordered GPU queue -> GPU evidence
-> zero-GPU recompute and adjudicate
```

- While a GPU job runs, use the zero-GPU lane for the next bounded candidate
  whose work remains useful under every feasible live-job outcome. Do not turn
  the zero-GPU worker into a progress poller.
- A zero-GPU candidate terminal is incomplete unless it returns exactly one of
  `QUEUE_GPU`, `HOLD` with one reopening fact, or `DROP` with a scoped reason.
- A GPU queue entry must bind its canonical owner, frozen uncertainty and
  contract, profile and full-run caps, prerequisites, dependency on earlier
  results, completion callback, and zero-GPU result-analysis owner.
- GPU completion preempts ordinary zero-GPU preparation: validate raw evidence,
  independently recompute the frozen estimand, interpret the scoped terminal,
  and reroute the queue.
- Start another queued GPU item during that analysis only when a prospective
  dependency check shows that no possible result can change the new item's
  contract or scientific decision. Otherwise leave it queued.
- Reconcile satisfied reopening facts against older holds so an obsolete hold
  does not strand an experiment. Reuse the existing evidence; do not add a new
  governance framework merely to change queue state.
- Treat `zero_gpu_running=explicit_idle` as fail-closed. Before declaring it,
  enumerate unresolved current-route questions, prerequisites of ordered GPU
  queue entries, and partial/non-exhaustive literature or source/code/algebra
  audits; route each as `admitted`, `blocked` with one reopening fact, or
  `not_decision_changing`. Missing this `idle_proof` invalidates the closure.
  Waiting for GPU does not justify idling outcome-independent work.
- Give every zero-GPU dispatch an event-driven terminal callback to the
  controller. If that callback cannot wake the controller, install one named
  low-frequency continuity fallback. It may only catch an unhandled terminal
  or invalid idle state and dispatch an already admitted successor; it must not
  poll GPU/protected evidence, invent filler, or outlive the bounded route.
- Report four separate fields: `gpu_running`, ordered `gpu_queue`,
  `zero_gpu_running`, and `result_analysis_queue`. “No currently executable
  queue item” must not be reported as “no experiment exists.”

### 6. Record evidence before interpretation

- Save raw artifacts and validation output first.
- Append structured records with `scripts/update_state.py`; do not hand-edit prior JSONL records.
- In Scout Lite, a run manifest, raw result, recomputed gate, and scoped outcome are sufficient. Do not backfill a full evidence/claim/state graph merely because helpers exist.
- In Confirmatory, record each claim as `fact`, `inference`, or `hypothesis`, link evidence IDs, and state limitations.
- Mark anomalous, null, and negative outcomes explicitly.

### 7. Assess progress and stalls

Classify an iteration as `progress`, `negative_result`, `replication`, `diagnostic`, `stale`, or `blocked`.

- Use `stale` only when it adds no evidence, reduces no uncertainty, resolves no engineering issue, and is not a justified replication.
- After two stale iterations, propose a structural pivot inside the charter or request an amendment.
- After three related scoped route closures by default—or earlier when two
  expose the same concrete mechanism—run the negative-synthesis gate in
  [references/portfolio-search.md](references/portfolio-search.md). Keep
  unrelated negatives separate; do not assemble them into a paper narrative.
- Close a route after two related Scouts fail the same causal link. Unrelated
  failures consume the frozen Program budget but do not justify a scientific
  Program-level closure. When a broad Program exhausts resources, report
  search exhaustion rather than `no viable candidate`.
- Require every synthesis prerequisite: a shared target-estimand family, one
  mechanism that predicts all results and exceptions, compatible protocols and
  strongest baselines or a preserving reduction, purposeful carrier coverage,
  and one fresh falsifiable estimand. If any prerequisite is absent, stop the
  synthesis audit without a bridge experiment and return any proposed unified
  artifact to the living Opportunity/Contribution ledger as appropriate.
- Waiting on a scheduler, failed hypothesis, or metric variance is not itself a stall.
- Lead status reports with problem existence, novelty residual, mechanism
  status, paper-path feasibility, Program/Epoch status, and the next exact
  decision. Treat commit count, document count, jobs, GPU utilization, and
  verifier surface as secondary operational diagnostics.

### 8. Promote, verify, or close

After a material Problem Scout signal, run the Contribution Gate:

- identify the strongest preserving reduction and residual operation;
- verify the nearest primary-source neighbors;
- apply federation/PEFT/dynamic specificity only at the level claimed;
- test incremental value beyond the mechanism-deletion alternative;
- choose the honest artifact: method, benchmark/audit, systems artifact,
  certificate/theory, reproduction, or scoped negative result;
- apply evidence-scalability and paper-path tests only when publication is the
  objective.

Use `selected`, `held`, or `excluded`. Unverified novelty can hold a method
claim without discarding the observed problem. Reframing the artifact does not
rewrite prior evidence; freeze a new charter before collecting new evidence.

Promote only when the frozen Scout gate passes and the next claim matters.
Create an amendment that changes `governance_track` to `confirmatory`, freezes
the confirmation protocol, and activates the evidence/claim/adjudication path.
Never treat Scout data as the independent confirmation set.

Passing a venue-viability screen does not promote evidence. It only means that
a positive or decision-changing Scout could justify Confirmatory work.

Close or mark NO-GO only at the narrowest justified scope. A closure needs at least one of:

- a formal or empirically verified reduction preserving estimand, information,
  cost, dynamics, and deployment constraints, with joint feasibility under one
  actor contract;
- a replicated, high-confidence negative under an adequate carrier and strongest baseline;
- failure of a preregistered minimum practical-effect gate.

Otherwise use `challenged`, `hold`, `inconclusive`, or `carrier-level stop`. “A related paper exists” is not a NO-GO result.

Search-budget exhaustion is an operational terminal state, not scientific
evidence. Do not convert it into a field-level or broad-agenda NO-GO.

For Confirmatory claims:

- re-run the narrowest relevant validation;
- verify primary-source citations;
- have a reviewer attempt falsification, leakage detection, alternative explanations, and reproduction;
- allow structured rebuttal before rejection;
- accept only claims backed by verified evidence and an explicit independent adjudication record.

### 9. Stop or hand off cleanly

Stop on a charter condition, exhausted budget, repeated hard blocker, completed objective, or required approval. Handoff:

- Program/Epoch identity, status, consumed and remaining cumulative budget,
  mechanism fingerprint, closure-ledger effect, and any circuit breaker;
- question, track, protocol, versions, and authorization boundary;
- completed/active runs, including negative results;
- exact artifact, log, and state paths;
- accepted, challenged, unresolved, or Scout-only signals;
- validation commands and outcomes;
- status of every live job, lease, callback, transfer, or external operation,
  including its check and cancel command when applicable;
- repository state: either a clean worktree or the exact modified/untracked
  file list, what remains unvalidated, and whether those changes are safe to
  resume;
- one exact first resume command or action;
- highest-value next action and why.

At charter freeze, independently verified outcome, promotion, scoped stop,
pivot, or archive, perform a **milestone knowledge handoff** only when the
applicable workspace rules or charter name a destination. Preserve the
experiment record first; treat knowledge pages and editable maps as synthesis
and navigation layers, never raw evidence. Update only decision-changing state,
decisive evidence, exact claim boundary, strongest remaining reduction, and
reopening condition. Exclude heartbeats, queue state, routine retries, and
intermediate metrics. Follow
[references/research-map-maintenance.md](references/research-map-maintenance.md)
when the destination includes an editable map. If a destination is unavailable
or dirty, report its sync as pending without blocking scientific closure unless
the workspace explicitly requires it. Reuse existing records; add no state
machine, verifier family, or approval gate solely for synchronization.

Never declare completion while required work, live jobs, or blocking validation failures remain.

## Deterministic helpers

Run with Python 3.10+ on POSIX; append locking uses `fcntl`.

- `scripts/init_task.py`: initialize Managed Scout or full Confirmatory state without overwriting content.
- `scripts/update_state.py`: append immutable JSONL records or atomically refresh a heartbeat lease.
- `scripts/validate_task.py`: validate track, state consistency, run manifests, evidence/claim links, stale accounting, and ready gates.
- `scripts/validate_prospective_frame.py`: derive prospective/claim-exposed/design-exposed tiers from one append-only cross-task exposure ledger and fail on a stale declared frame.
- `scripts/validate_opportunity_prompt.py`: lint a high-recall-v2 external Opportunity Search prompt for unresolved placeholders, stage/pass inversion, missing two-state admission, unguarded natural-carrier burden, missing joint-feasibility semantics, and an incomplete decision contract.
- `scripts/validate_opportunity_gate_calibration.py`: validate a retrospective broad-gate decision table with at least three pre-signal positives, three negatives, and zero false rejects/admissions under the proposed gate.

Script success establishes structural validity only; it never establishes scientific truth.
