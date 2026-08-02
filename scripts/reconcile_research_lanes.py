#!/usr/bin/env python3
"""Validate one compact global research-lane snapshot.

This helper is deliberately small. It does not schedule work, inspect remote
state, or decide science. It only rejects the controller states that previously
allowed a route-local terminal to strand the global zero-GPU or Pro lanes.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IDLE_PROOF_CATEGORIES = {
    "current_route",
    "gpu_queue_prerequisites",
    "partial_audits",
    "new_problem_opportunity_search",
}
BACKLOG_STATES = {"admitted", "blocked", "not_decision_changing"}
OPPORTUNITY_STATES = {"active", "admitted", "blocked", "budget_exhausted"}
NEXT_ACTIONS = {"dispatch_next", "validated_idle", "queued", "explicit_hold"}
ACTIVE_THREAD_STATES = {"active"}
GPU_RUNNING_STATES = {"accepted_stabilizing", "running"}
GPU_QUEUE_STATES = {"blocked", "launch_ready"}
PROGRESS_DUE_HANDLING = {"continuity_check_in_progress", "recovery_dispatched"}
WATCHDOG_DUE_HANDLING = {"check_in_progress", "terminal_recovery_dispatched"}
DECISION_CRITICAL_ZERO_GPU_KINDS = {
    "audit",
    "contract_design",
    "evidence_architecture",
    "opportunity_search",
    "research",
    "result_analysis",
    "scientific_interpretation",
}
QUEUE_AUTHORITY_KINDS = {
    "validated_experiment_record",
    "durable_terminal_packet",
    "frozen_prospective_contract",
}
PRO_LIVE_STATES = {"submitted", "generating", "cooldown_held"}
PRO_DUE_HANDLING = {"in_progress", "dispatcher_busy", "cooldown_held"}
TERMINAL_CALLBACK_STATES = {
    "none",
    "pending",
    "delivered",
    "acknowledged",
    "not_available",
}
PRO_CALLBACK_OBSERVATION_STATES = {"stale", "duplicate", "closed"}
PRO_EFFECT_KEYS = {"adjudication", "dispatch", "ack"}
PRO_CALLBACK_EVENT_STATES = {"registered", "consumed", "closed"}
LEASE_TRANSITION_KINDS = {
    "completed_successor",
    "issued_after_completion",
    "recovery_replacement",
    "revoked_without_replacement",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("top-level value must be an object")
    return value


def load_json_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    """Parse and hash one immutable in-memory read of a lane snapshot."""
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("top-level value must be an object")
    return value, hashlib.sha256(payload).hexdigest()


def require_list(record: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = record.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be a list")
        return []
    return value


def task_id(value: Any) -> str | None:
    if isinstance(value, dict):
        candidate = value.get("task_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def canonical_sha256_string(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lease_tuple(value: Any) -> tuple[str, str, str, int] | None:
    if not isinstance(value, dict):
        return None
    task = value.get("task_id")
    owner = value.get("owner_thread_id")
    dispatch = value.get("dispatch_id")
    epoch = value.get("lease_epoch")
    if not all(nonempty_string(item) for item in (task, owner, dispatch)):
        return None
    if not positive_int(epoch):
        return None
    return task, owner, dispatch, epoch


def lease_dict(binding: tuple[str, str, str, int]) -> dict[str, Any]:
    task, owner, dispatch, epoch = binding
    return {
        "task_id": task,
        "owner_thread_id": owner,
        "dispatch_id": dispatch,
        "lease_epoch": epoch,
    }


def pro_callback_binding(
    value: Any,
) -> tuple[str, str, int, int, str] | None:
    if not isinstance(value, dict):
        return None
    job = value.get("job_id")
    owner = value.get("owner_thread_id")
    owner_generation = value.get("owner_generation")
    job_generation = value.get("job_generation")
    event_key = value.get("callback_event_key")
    if not all(nonempty_string(item) for item in (job, owner, event_key)):
        return None
    if not positive_int(owner_generation) or not positive_int(job_generation):
        return None
    return job, owner, owner_generation, job_generation, event_key


def pro_callback_binding_dict(
    binding: tuple[str, str, int, int, str], state: str
) -> dict[str, Any]:
    job, owner, owner_generation, job_generation, event_key = binding
    return {
        "job_id": job,
        "owner_thread_id": owner,
        "owner_generation": owner_generation,
        "job_generation": job_generation,
        "callback_event_key": event_key,
        "state": state,
    }


def pro_actionable_records(record: dict[str, Any]) -> list[dict[str, Any]]:
    pro = record.get("pro_advisory_lane")
    if not isinstance(pro, dict):
        return []
    records: list[dict[str, Any]] = []
    # Observation-only stale/duplicate/closed callbacks must have no durable
    # generation effect. Only live work and accepted current responses can
    # advance owner/job floors.
    for key in ("live_jobs", "response_ready"):
        values = pro.get(key)
        if isinstance(values, list):
            records.extend(item for item in values if isinstance(item, dict))
    return records


def pro_generation_maps(
    record: dict[str, Any],
) -> tuple[dict[str, int], dict[str, int]]:
    owners: dict[str, int] = {}
    jobs: dict[str, int] = {}
    for item in pro_actionable_records(record):
        binding = pro_callback_binding(item)
        if binding is None:
            continue
        job, owner, owner_generation, job_generation, _ = binding
        owners[owner] = max(owners.get(owner, 0), owner_generation)
        jobs[job] = max(jobs.get(job, 0), job_generation)
    return owners, jobs


def response_ready_callbacks(record: dict[str, Any]) -> list[dict[str, Any]]:
    pro = record.get("pro_advisory_lane")
    if not isinstance(pro, dict) or not isinstance(pro.get("response_ready"), list):
        return []
    return [item for item in pro["response_ready"] if isinstance(item, dict)]


def validate_worker_registry(
    value: Any, errors: list[str]
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        errors.append("worker_registry must be a list")
        return {}

    registry: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(value):
        prefix = f"worker_registry[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        owner = entry.get("owner_thread_id")
        if not nonempty_string(owner):
            errors.append(f"{prefix} requires owner_thread_id")
            continue
        if owner in registry:
            errors.append(f"worker_registry has duplicate owner_thread_id {owner}")
            continue
        maximum = entry.get("max_lease_epoch")
        if not positive_int(maximum):
            errors.append(f"{prefix}.max_lease_epoch must be a positive integer")
        current = entry.get("current_lease")
        if current is not None:
            binding = lease_tuple(current)
            if binding is None:
                errors.append(f"{prefix}.current_lease must be a complete lease tuple or null")
            else:
                if binding[1] != owner:
                    errors.append(f"{prefix}.current_lease owner must match registry owner")
                if positive_int(maximum) and binding[3] != maximum:
                    errors.append(
                        f"{prefix}.current_lease epoch must equal durable max_lease_epoch"
                    )
        registry[owner] = entry
    return registry


def validate_terminal_history(value: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append("terminal_idempotency_history must be a list")
        return []

    history: list[dict[str, Any]] = []
    seen_event_states: set[tuple[str, str]] = set()
    for index, entry in enumerate(value):
        prefix = f"terminal_idempotency_history[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if lease_tuple(entry) is None:
            errors.append(f"{prefix} requires a complete source lease tuple")
        event = entry.get("terminal_event_id")
        if not nonempty_string(event):
            errors.append(f"{prefix} requires terminal_event_id")
        state = entry.get("callback_delivery_state")
        if state not in {"delivered", "acknowledged"}:
            errors.append(
                f"{prefix}.callback_delivery_state must be delivered or acknowledged"
            )
        elif nonempty_string(event):
            event_state = (event, state)
            if event_state in seen_event_states:
                errors.append(
                    f"terminal_idempotency_history duplicates {state} record for terminal_event_id {event}"
                )
            else:
                seen_event_states.add(event_state)
        if not nonempty_string(entry.get("callback_receipt")):
            errors.append(f"{prefix} requires callback_receipt")
        parse_utc(entry.get("delivered_at_utc"), f"{prefix}.delivered_at_utc", errors)
        history.append(entry)
    return history


def validate_lease_transitions(
    value: Any, errors: list[str]
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append("lease_transitions must be a list")
        return []
    transitions: list[dict[str, Any]] = []
    for index, entry in enumerate(value):
        prefix = f"lease_transitions[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        owner = entry.get("owner_thread_id")
        if not nonempty_string(owner):
            errors.append(f"{prefix} requires owner_thread_id")
        if not positive_int(entry.get("prior_max_lease_epoch")):
            errors.append(f"{prefix}.prior_max_lease_epoch must be a positive integer")
        for key in ("from_lease", "to_lease"):
            candidate = entry.get(key)
            if candidate is not None:
                binding = lease_tuple(candidate)
                if binding is None:
                    errors.append(f"{prefix}.{key} must be a complete lease tuple or null")
                elif binding[1] != owner:
                    errors.append(f"{prefix}.{key} owner must match transition owner")
        if entry.get("transition_kind") not in LEASE_TRANSITION_KINDS:
            errors.append(
                f"{prefix}.transition_kind must be one of {sorted(LEASE_TRANSITION_KINDS)}"
            )
        if not nonempty_string(entry.get("transition_receipt")):
            errors.append(f"{prefix} requires transition_receipt")
        parse_utc(entry.get("transitioned_at_utc"), f"{prefix}.transitioned_at_utc", errors)
        transitions.append(entry)
    return transitions


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def empty_watermark(controller_thread_id: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "controller_thread_id": controller_thread_id,
        "generation": 0,
        "owner_registry": {},
        "terminal_history": [],
        "acknowledged_terminal_events": {},
        "pro_owner_generations": {},
        "pro_job_generations": {},
        "pro_callback_event_keys": {},
        "transition_fingerprints": [],
        "last_record_sha256": None,
    }


def load_watermark(path: Path, controller_thread_id: Any) -> dict[str, Any]:
    if not path.exists():
        return empty_watermark(controller_thread_id)
    value = load_json(path)
    if value.get("schema_version") != 1:
        raise ValueError("durable lane watermark schema_version must be 1")
    if value.get("controller_thread_id") != controller_thread_id:
        raise ValueError("durable lane watermark controller_thread_id mismatch")
    if not isinstance(value.get("owner_registry"), dict):
        raise ValueError("durable lane watermark owner_registry must be an object")
    if not isinstance(value.get("terminal_history"), list):
        raise ValueError("durable lane watermark terminal_history must be a list")
    if not isinstance(value.get("acknowledged_terminal_events"), dict):
        raise ValueError(
            "durable lane watermark acknowledged_terminal_events must be an object"
        )
    if not isinstance(value.get("transition_fingerprints"), list):
        raise ValueError("durable lane watermark transition_fingerprints must be a list")
    for key in (
        "pro_owner_generations",
        "pro_job_generations",
        "pro_callback_event_keys",
    ):
        if key not in value:
            value[key] = {}
        elif not isinstance(value[key], dict):
            raise ValueError(f"durable lane watermark {key} must be an object")
    for key in ("pro_owner_generations", "pro_job_generations"):
        for identifier, generation in value[key].items():
            if not nonempty_string(identifier) or not positive_int(generation):
                raise ValueError(
                    f"durable lane watermark {key} requires non-empty IDs and positive generations"
                )
    stable_slots: dict[tuple[str, int], str] = {}
    for event_key, binding_value in value["pro_callback_event_keys"].items():
        if not nonempty_string(event_key) or not isinstance(binding_value, dict):
            raise ValueError(
                "durable lane watermark pro_callback_event_keys is malformed"
            )
        binding = pro_callback_binding(binding_value)
        if binding is None or binding[4] != event_key:
            raise ValueError(
                "durable lane watermark pro_callback_event_keys has an incomplete binding"
            )
        if binding_value.get("state") not in PRO_CALLBACK_EVENT_STATES:
            raise ValueError(
                "durable lane watermark pro_callback_event_keys has an invalid state"
            )
        slot = (binding[0], binding[3])
        if slot in stable_slots and stable_slots[slot] != event_key:
            raise ValueError(
                "durable lane watermark binds one Pro job generation to multiple callback event keys"
            )
        stable_slots[slot] = event_key
    return value


def registry_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = record.get("worker_registry")
    if not isinstance(entries, list):
        return {}
    return {
        entry["owner_thread_id"]: entry
        for entry in entries
        if isinstance(entry, dict) and nonempty_string(entry.get("owner_thread_id"))
    }


def validate_durable_chronology(
    record: dict[str, Any],
    watermark: dict[str, Any],
    record_sha256: str,
    errors: list[str],
) -> None:
    current_registry = registry_map(record)
    prior_registry = watermark.get("owner_registry", {})
    same_committed_record = watermark.get("last_record_sha256") == record_sha256
    transitions = record.get("lease_transitions")
    if not isinstance(transitions, list):
        transitions = []
    transition_fingerprints = {
        canonical_sha256(item) for item in transitions if isinstance(item, dict)
    }
    prior_transition_fingerprints = set(
        watermark.get("transition_fingerprints", [])
    )
    matched_transition_fingerprints: set[str] = set()

    for owner, prior in prior_registry.items():
        current = current_registry.get(owner)
        if current is None:
            errors.append(
                f"worker_registry cannot omit durable owner_thread_id {owner}"
            )
            continue
        prior_max = prior.get("max_lease_epoch")
        current_max = current.get("max_lease_epoch")
        if positive_int(prior_max) and positive_int(current_max) and current_max < prior_max:
            errors.append(
                f"worker_registry[{owner}].max_lease_epoch is below durable watermark"
            )

        prior_current = lease_tuple(prior.get("current_lease"))
        current_current = lease_tuple(current.get("current_lease"))
        if prior_current == current_current or same_committed_record:
            continue
        matching = [
            transition
            for transition in transitions
            if isinstance(transition, dict)
            and transition.get("owner_thread_id") == owner
            and lease_tuple(transition.get("from_lease")) == prior_current
            and lease_tuple(transition.get("to_lease")) == current_current
            and transition.get("prior_max_lease_epoch") == prior_max
        ]
        if len(matching) != 1:
            errors.append(
                f"worker_registry[{owner}] current lease change requires exactly one durable transition from the prior watermark"
            )
        else:
            fingerprint = canonical_sha256(matching[0])
            matched_transition_fingerprints.add(fingerprint)
            if fingerprint in prior_transition_fingerprints:
                errors.append(
                    f"worker_registry[{owner}] lease transition receipt was already consumed"
                )
        if current_current is not None and prior_current is not None:
            if current_current[3] <= prior_current[3]:
                errors.append(
                    f"worker_registry[{owner}] replacement lease_epoch must be strictly greater than the prior current lease"
                )
        if current_current is not None and positive_int(prior_max):
            if current_current[3] <= prior_max:
                errors.append(
                    f"worker_registry[{owner}] newly issued lease_epoch must exceed the durable watermark"
                )

    # Records may carry cumulative transition history. Previously consumed
    # fingerprints are inert; every newly introduced receipt must be the
    # unique receipt for an actual prior-current -> current-current change.
    unmatched_transition_fingerprints = (
        transition_fingerprints
        - prior_transition_fingerprints
        - matched_transition_fingerprints
    )
    if unmatched_transition_fingerprints:
        errors.append(
            "lease_transitions contains a receipt not matched to a durable current-lease change"
        )
    terminal = record.get("terminal_transaction")
    if (
        matched_transition_fingerprints
        and isinstance(terminal, dict)
        and terminal.get("callback_state") == "acknowledged"
    ):
        acknowledged_at = parse_utc(
            terminal.get("acknowledged_at_utc"),
            "terminal_transaction.acknowledged_at_utc",
            errors,
        )
        for index, transition in enumerate(transitions):
            if (
                not isinstance(transition, dict)
                or canonical_sha256(transition)
                not in matched_transition_fingerprints
            ):
                continue
            transitioned_at = parse_utc(
                transition.get("transitioned_at_utc"),
                f"lease_transitions[{index}].transitioned_at_utc",
                errors,
            )
            if (
                transitioned_at is not None
                and acknowledged_at is not None
                and transitioned_at > acknowledged_at
            ):
                errors.append(
                    f"lease_transitions[{index}] durable transition must precede FINAL_ACK"
                )

    current_history = record.get("terminal_idempotency_history")
    if not isinstance(current_history, list):
        current_history = []
    current_history_fingerprints = {canonical_sha256(item) for item in current_history}
    for prior_entry in watermark.get("terminal_history", []):
        if canonical_sha256(prior_entry) not in current_history_fingerprints:
            errors.append(
                "terminal_idempotency_history must preserve every durable prior record"
            )

    terminal = record.get("terminal_transaction")
    if isinstance(terminal, dict) and terminal.get("callback_state") == "acknowledged":
        callback = terminal.get("delivered_callback")
        if isinstance(callback, dict):
            event = callback.get("terminal_event_id")
            source = lease_tuple(callback)
            prior_acks = watermark.get("acknowledged_terminal_events", {})
            if nonempty_string(event) and event in prior_acks and not same_committed_record:
                errors.append(
                    f"terminal_event_id {event} was already acknowledged in the durable watermark"
                )
            # An exact replay is checked against the post-transaction
            # watermark, where a same-owner completed successor may already
            # have advanced max_lease_epoch. The original record hash is the
            # idempotency proof; different records must still match the
            # pre-transaction owner floor.
            if source is not None and not same_committed_record:
                prior_owner = prior_registry.get(source[1])
                if isinstance(prior_owner, dict):
                    prior_max = prior_owner.get("max_lease_epoch")
                    if positive_int(prior_max) and source[3] != prior_max:
                        errors.append(
                            "acknowledged terminal callback lease_epoch must equal the owner's pre-transaction durable watermark"
                        )

    prior_pro_owners = watermark.get("pro_owner_generations", {})
    prior_pro_jobs = watermark.get("pro_job_generations", {})
    prior_pro_events = watermark.get("pro_callback_event_keys", {})
    current_pro_owners, current_pro_jobs = pro_generation_maps(record)
    pro = record.get("pro_advisory_lane")
    actionable: list[dict[str, Any]] = []
    live_actionable_ids: set[int] = set()
    observations: list[dict[str, Any]] = []
    if isinstance(pro, dict):
        for key in ("live_jobs", "response_ready"):
            values = pro.get(key)
            if isinstance(values, list):
                candidates = [item for item in values if isinstance(item, dict)]
                actionable.extend(candidates)
                if key == "live_jobs":
                    live_actionable_ids.update(id(item) for item in candidates)
        values = pro.get("callback_observations")
        if isinstance(values, list):
            observations = [item for item in values if isinstance(item, dict)]

    prior_slot_bindings = {
        (binding[0], binding[3]): binding
        for value in prior_pro_events.values()
        if (binding := pro_callback_binding(value)) is not None
    }
    current_actionable_bindings = {
        binding[4]: binding
        for item in actionable
        if (binding := pro_callback_binding(item)) is not None
    }
    current_slot_bindings = {
        (binding[0], binding[3]): binding
        for binding in current_actionable_bindings.values()
    }

    for item in actionable:
        binding = pro_callback_binding(item)
        if binding is None:
            continue
        job, owner, owner_generation, job_generation, event_key = binding
        if positive_int(prior_pro_owners.get(owner)) and owner_generation < prior_pro_owners[owner]:
            errors.append(
                f"Pro owner {owner} generation is below the durable watermark"
            )
        if positive_int(prior_pro_jobs.get(job)) and job_generation < prior_pro_jobs[job]:
            errors.append(
                f"Pro job {job} generation is below the durable watermark"
            )
        prior_event = prior_pro_events.get(event_key)
        prior_binding = pro_callback_binding(prior_event)
        if prior_binding is not None and prior_binding != binding:
            errors.append(
                f"Pro callback event key {event_key} is rebound to a different job/owner generation"
            )
        prior_slot = prior_slot_bindings.get((job, job_generation))
        if prior_slot is not None and prior_slot != binding:
            errors.append(
                f"Pro job {job} generation {job_generation} changed its stable callback event key"
            )
        if id(item) in live_actionable_ids and isinstance(prior_event, dict):
            if prior_event.get("state") == "consumed":
                errors.append(
                    f"live Pro job {job} reuses already consumed callback event {event_key}"
                )
            elif prior_event.get("state") == "closed":
                errors.append(
                    f"live Pro job {job} reopens closed callback event {event_key}"
                )

    accepted_current_bindings = {
        binding[4]: binding
        for item in response_ready_callbacks(record)
        if (binding := pro_callback_binding(item)) is not None
    }
    for item in response_ready_callbacks(record):
        binding = pro_callback_binding(item)
        if binding is None:
            continue
        job, owner, owner_generation, job_generation, event_key = binding
        owner_floor = max(
            int(prior_pro_owners.get(owner, 0)),
            int(current_pro_owners.get(owner, 0)),
        )
        job_floor = max(
            int(prior_pro_jobs.get(job, 0)),
            int(current_pro_jobs.get(job, 0)),
        )
        if owner_generation < owner_floor or job_generation < job_floor:
            errors.append(
                f"Pro callback event {event_key} is stale and must be observation-only"
            )
        prior_event = prior_pro_events.get(event_key)
        if (
            isinstance(prior_event, dict)
            and prior_event.get("state") == "consumed"
            and not same_committed_record
        ):
            errors.append(
                f"Pro callback event {event_key} was already consumed and must be observation-only"
            )
        if isinstance(prior_event, dict) and prior_event.get("state") == "closed":
            errors.append(
                f"Pro callback event {event_key} belongs to a closed job generation and must be observation-only"
            )

    for item in observations:
        binding = pro_callback_binding(item)
        if binding is None:
            continue
        job, owner, owner_generation, job_generation, event_key = binding
        disposition = item.get("disposition")
        known_binding = pro_callback_binding(prior_pro_events.get(event_key))
        if known_binding is None:
            known_binding = accepted_current_bindings.get(event_key)
        if known_binding is not None and known_binding != binding:
            errors.append(
                f"Pro callback observation {event_key} conflicts with its stable binding"
            )
        slot_binding = prior_slot_bindings.get((job, job_generation))
        if slot_binding is None:
            slot_binding = current_slot_bindings.get((job, job_generation))
        if slot_binding is not None and slot_binding != binding:
            errors.append(
                f"Pro callback observation for {job} generation {job_generation} conflicts with its stable event key"
            )
        if disposition == "duplicate":
            prior_event = prior_pro_events.get(event_key)
            prior_consumed = (
                isinstance(prior_event, dict)
                and prior_event.get("state") == "consumed"
            )
            if not prior_consumed and event_key not in accepted_current_bindings:
                errors.append(
                    f"duplicate Pro callback observation {event_key} has no accepted original event"
                )
        elif disposition == "stale":
            owner_floor = max(
                int(prior_pro_owners.get(owner, 0)),
                int(current_pro_owners.get(owner, 0)),
            )
            job_floor = max(
                int(prior_pro_jobs.get(job, 0)),
                int(current_pro_jobs.get(job, 0)),
            )
            if owner_generation >= owner_floor and job_generation >= job_floor:
                errors.append(
                    f"stale Pro callback observation {event_key} does not trail a generation floor"
                )
        elif disposition == "closed" and event_key in current_actionable_bindings:
            errors.append(
                f"closed Pro callback observation {event_key} cannot remain live or response_ready"
            )


def advance_watermark(
    record: dict[str, Any], watermark: dict[str, Any], record_sha256: str
) -> dict[str, Any]:
    if watermark.get("last_record_sha256") == record_sha256:
        return watermark
    next_value = {
        "schema_version": 1,
        "controller_thread_id": record.get("controller_thread_id"),
        "generation": int(watermark.get("generation", 0)),
        "owner_registry": registry_map(record),
        "terminal_history": record.get("terminal_idempotency_history", []),
        "acknowledged_terminal_events": dict(
            watermark.get("acknowledged_terminal_events", {})
        ),
        "pro_owner_generations": dict(
            watermark.get("pro_owner_generations", {})
        ),
        "pro_job_generations": dict(
            watermark.get("pro_job_generations", {})
        ),
        "pro_callback_event_keys": dict(
            watermark.get("pro_callback_event_keys", {})
        ),
        "transition_fingerprints": sorted(
            set(watermark.get("transition_fingerprints", []))
            | {
                canonical_sha256(item)
                for item in record.get("lease_transitions", [])
                if isinstance(item, dict)
            }
        ),
        "last_record_sha256": record_sha256,
    }
    terminal = record.get("terminal_transaction")
    if isinstance(terminal, dict) and terminal.get("callback_state") == "acknowledged":
        callback = terminal.get("delivered_callback")
        if isinstance(callback, dict) and nonempty_string(
            callback.get("terminal_event_id")
        ):
            next_value["acknowledged_terminal_events"][
                callback["terminal_event_id"]
            ] = callback
    owner_generations, job_generations = pro_generation_maps(record)
    for owner, generation in owner_generations.items():
        next_value["pro_owner_generations"][owner] = max(
            int(next_value["pro_owner_generations"].get(owner, 0)), generation
        )
    for job, generation in job_generations.items():
        next_value["pro_job_generations"][job] = max(
            int(next_value["pro_job_generations"].get(job, 0)), generation
        )
    pro = record.get("pro_advisory_lane")
    live_jobs = pro.get("live_jobs", []) if isinstance(pro, dict) else []
    for item in live_jobs:
        binding = pro_callback_binding(item)
        if binding is None:
            continue
        event_key = binding[4]
        if event_key not in next_value["pro_callback_event_keys"]:
            next_value["pro_callback_event_keys"][event_key] = (
                pro_callback_binding_dict(binding, "registered")
            )
    for item in response_ready_callbacks(record):
        binding = pro_callback_binding(item)
        if binding is None:
            continue
        event_key = binding[4]
        next_value["pro_callback_event_keys"][event_key] = (
            pro_callback_binding_dict(binding, "consumed")
        )
    observations = pro.get("callback_observations", []) if isinstance(pro, dict) else []
    for item in observations:
        if not isinstance(item, dict) or item.get("disposition") != "closed":
            continue
        binding = pro_callback_binding(item)
        if binding is None:
            continue
        event_key = binding[4]
        prior = next_value["pro_callback_event_keys"].get(event_key)
        if (
            isinstance(prior, dict)
            and prior.get("state") == "registered"
            and pro_callback_binding(prior) == binding
        ):
            # The callback stays non-actionable (zero adjudication/dispatch/ACK),
            # but its first valid registered->closed lifecycle transition is
            # durable so the same generation can never be reopened.
            next_value["pro_callback_event_keys"][event_key] = (
                pro_callback_binding_dict(binding, "closed")
            )
    effect_keys = (
        "owner_registry",
        "terminal_history",
        "acknowledged_terminal_events",
        "pro_owner_generations",
        "pro_job_generations",
        "pro_callback_event_keys",
        "transition_fingerprints",
    )
    if all(next_value[key] == watermark.get(key) for key in effect_keys):
        return watermark
    next_value["generation"] += 1
    return next_value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def validate_final_ack_terminal_artifact(
    record: dict[str, Any], errors: list[str]
) -> None:
    terminal = record.get("terminal_transaction")
    if not isinstance(terminal, dict) or terminal.get("callback_state") != "acknowledged":
        return
    artifact = terminal.get("terminal_artifact")
    if not isinstance(artifact, dict):
        errors.append(
            "FINAL_ACK requires terminal_artifact path and callback_bound_sha256"
        )
        return
    path_value = artifact.get("path")
    digest_value = artifact.get("callback_bound_sha256")
    callback = terminal.get("delivered_callback")
    history = record.get("terminal_idempotency_history")
    bound_history: list[dict[str, Any]] = []
    if isinstance(callback, dict) and isinstance(history, list):
        bound_history = [
            item
            for item in history
            if isinstance(item, dict)
            and item.get("callback_delivery_state") == "delivered"
            and all(
                item.get(key) == callback.get(key)
                for key in (
                    "task_id",
                    "owner_thread_id",
                    "dispatch_id",
                    "lease_epoch",
                    "terminal_event_id",
                    "callback_receipt",
                )
            )
        ]
    if len(bound_history) != 1:
        errors.append(
            "FINAL_ACK terminal artifact must bind exactly one delivered callback history record"
        )
    else:
        if bound_history[0].get("terminal_path") != path_value:
            errors.append(
                "FINAL_ACK terminal_artifact path must match callback-bound terminal_path"
            )
        if bound_history[0].get("callback_bound_sha256") != digest_value:
            errors.append(
                "FINAL_ACK terminal_artifact digest must match callback-bound history digest"
            )
    if not nonempty_string(path_value):
        errors.append("FINAL_ACK terminal_artifact requires a non-empty path")
        return
    terminal_path = Path(path_value)
    if not terminal_path.is_absolute():
        errors.append("FINAL_ACK terminal_artifact path must be absolute")
        return
    if not canonical_sha256_string(digest_value):
        errors.append(
            "FINAL_ACK terminal_artifact callback_bound_sha256 must be canonical 64-hex"
        )
        return
    if artifact.get("callback_delivered") is not True:
        errors.append("FINAL_ACK terminal_artifact requires callback_delivered=true")
    if not terminal_path.is_file():
        errors.append(
            f"FINAL_ACK terminal_artifact path is not a local file: {terminal_path}"
        )
        return
    try:
        actual = sha256_file(terminal_path)
    except OSError as exc:
        errors.append(f"FINAL_ACK cannot hash terminal artifact {terminal_path}: {exc}")
        return
    if actual.lower() != digest_value.lower():
        errors.append(
            "FINAL_ACK terminal artifact digest mismatch: "
            f"callback_bound={digest_value.lower()} current={actual}"
        )


def validate_current_lease_against_registry(
    current: Any,
    prefix: str,
    registry: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    binding = lease_tuple(current)
    if binding is None:
        return
    owner = binding[1]
    entry = registry.get(owner)
    if entry is None:
        errors.append(f"{prefix} owner is absent from durable worker_registry")
        return
    maximum = entry.get("max_lease_epoch")
    if positive_int(maximum) and binding[3] < maximum:
        errors.append(f"{prefix}.lease_epoch is below durable max_lease_epoch")
    registered = lease_tuple(entry.get("current_lease"))
    if registered != binding:
        errors.append(f"{prefix} must exactly match worker_registry.current_lease")


def parse_utc(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty UTC timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be an ISO-8601 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed.astimezone(timezone.utc)


def validate_task_lease(
    value: dict[str, Any],
    prefix: str,
    controller_thread_id: Any,
    observed_at: datetime | None,
    errors: list[str],
) -> None:
    for key in ("task_id", "owner_thread_id", "dispatch_id"):
        if not nonempty_string(value.get(key)):
            errors.append(f"{prefix} requires non-empty {key}")
    if not positive_int(value.get("lease_epoch")):
        errors.append(f"{prefix}.lease_epoch must be a positive integer")

    activation = value.get("activation_evidence")
    if not isinstance(activation, dict):
        errors.append(f"{prefix} requires task-bound activation_evidence")
    else:
        for key in ("task_id", "owner_thread_id", "dispatch_id", "lease_epoch"):
            if activation.get(key) != value.get(key):
                errors.append(
                    f"{prefix}.activation_evidence.{key} must match the current lease"
                )
        if activation.get("observed_thread_status") not in ACTIVE_THREAD_STATES:
            errors.append(
                f"{prefix}.activation_evidence requires observed_thread_status=active"
            )
        if not nonempty_string(activation.get("activation_receipt")):
            errors.append(
                f"{prefix}.activation_evidence requires activation_receipt"
            )
        activated_at = parse_utc(
            activation.get("observed_at_utc"),
            f"{prefix}.activation_evidence.observed_at_utc",
            errors,
        )
        if (
            observed_at is not None
            and activated_at is not None
            and activated_at > observed_at
        ):
            errors.append(f"{prefix}.activation_evidence cannot be future-dated")

    callback = value.get("callback_binding")
    if not isinstance(callback, dict):
        errors.append(f"{prefix} requires callback_binding")
    else:
        for key in ("task_id", "owner_thread_id", "dispatch_id", "lease_epoch"):
            if callback.get(key) != value.get(key):
                errors.append(
                    f"{prefix}.callback_binding.{key} must match the current lease"
                )
        if callback.get("terminal_event_id") != value.get("terminal_event_id"):
            errors.append(
                f"{prefix}.callback_binding.terminal_event_id must match the task"
            )
        if callback.get("controller_thread_id") != controller_thread_id:
            errors.append(
                f"{prefix}.callback_binding.controller_thread_id must match the controller"
            )


def validate_recovery_binding(
    handling: Any,
    current: dict[str, Any],
    prefix: str,
    allowed_states: set[str],
    errors: list[str],
) -> None:
    if not isinstance(handling, dict):
        errors.append(f"{prefix} requires task-bound recovery evidence")
        return
    if handling.get("state") not in allowed_states:
        errors.append(f"{prefix}.state must be one of {sorted(allowed_states)}")
    for key in ("task_id", "owner_thread_id", "dispatch_id", "lease_epoch"):
        if handling.get(key) != current.get(key):
            errors.append(f"{prefix}.{key} must match the current lease")
    if not nonempty_string(handling.get("recovery_receipt")):
        errors.append(f"{prefix} requires recovery_receipt")
    if handling.get("state") == "recovery_dispatched":
        errors.append(
            f"{prefix} recovery_dispatched must revoke the old lease and replace the current running task"
        )


def validate_gpu_queue_authority(
    item: Any, index: int, errors: list[str]
) -> None:
    prefix = f"gpu_queue[{index}]"
    if not isinstance(item, dict):
        errors.append(f"{prefix} must be an object")
        return
    for key in ("task_id", "owner_thread_id", "launch_prerequisite"):
        if not isinstance(item.get(key), str) or not item[key].strip():
            errors.append(f"{prefix} requires non-empty {key}")

    queue_state = item.get("queue_state")
    if queue_state not in GPU_QUEUE_STATES:
        errors.append(
            f"{prefix}.queue_state must be one of {sorted(GPU_QUEUE_STATES)}"
        )
    if queue_state == "blocked" and not item.get("blocking_fact"):
        errors.append(f"{prefix} blocked item requires blocking_fact")

    authority = item.get("latest_authority")
    if not isinstance(authority, dict):
        errors.append(f"{prefix} requires latest_authority")
        return
    if authority.get("checked_against_latest_terminal") is not True:
        errors.append(
            f"{prefix}.latest_authority must be checked against the latest terminal"
        )
    if authority.get("source_kind") not in QUEUE_AUTHORITY_KINDS:
        errors.append(
            f"{prefix}.latest_authority.source_kind must be one of "
            f"{sorted(QUEUE_AUTHORITY_KINDS)}"
        )
    for key in ("authority_id", "evidence_path"):
        if not isinstance(authority.get(key), str) or not authority[key].strip():
            errors.append(f"{prefix}.latest_authority requires non-empty {key}")
    if authority.get("queue_disposition") != "queue_gpu":
        errors.append(
            f"{prefix}.latest_authority.queue_disposition must be queue_gpu"
        )


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not isinstance(record.get("controller_thread_id"), str):
        errors.append("controller_thread_id must be a string")

    observed_at = parse_utc(
        record.get("observed_at_utc"),
        "observed_at_utc",
        errors,
    )

    worker_registry = validate_worker_registry(record.get("worker_registry"), errors)
    terminal_history = validate_terminal_history(
        record.get("terminal_idempotency_history"), errors
    )
    validate_lease_transitions(record.get("lease_transitions"), errors)

    gpu_queue = require_list(record, "gpu_queue", errors)
    zero_backlog = require_list(record, "zero_gpu_backlog", errors)
    result_queue = require_list(record, "result_analysis_queue", errors)

    for index, item in enumerate(gpu_queue):
        validate_gpu_queue_authority(item, index, errors)

    for index, item in enumerate(zero_backlog):
        if not isinstance(item, dict):
            errors.append(f"zero_gpu_backlog[{index}] must be an object")
            continue
        if task_id(item) is None:
            errors.append(f"zero_gpu_backlog[{index}] requires task_id")
        state = item.get("status")
        if state not in BACKLOG_STATES:
            errors.append(
                f"zero_gpu_backlog[{index}].status must be one of "
                f"{sorted(BACKLOG_STATES)}"
            )
        if state == "blocked":
            prefix = f"zero_gpu_backlog[{index}]"
            for key in (
                "reopening_fact",
                "reopening_predicate",
                "observer_thread_id",
                "next_evidence_action",
            ):
                if not nonempty_string(item.get(key)):
                    errors.append(f"{prefix} blocked item requires non-empty {key}")
            trigger = item.get("reopen_trigger_ref")
            next_check = item.get("next_check_at_utc")
            if not nonempty_string(trigger) and next_check is None:
                errors.append(
                    f"{prefix} blocked item requires reopen_trigger_ref or next_check_at_utc"
                )
            if next_check is not None:
                check_at = parse_utc(next_check, f"{prefix}.next_check_at_utc", errors)
                if (
                    observed_at is not None
                    and check_at is not None
                    and observed_at >= check_at
                ):
                    errors.append(f"{prefix} blocked HOLD next check is due")
        if state == "admitted":
            for key in ("owner_thread_id", "start_prerequisite"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append(
                        f"zero_gpu_backlog[{index}] admitted item requires non-empty {key}"
                    )
            if item.get("useful_under_all_pending_gpu_outcomes") is not True:
                errors.append(
                    f"zero_gpu_backlog[{index}] admitted item must be useful under "
                    "all pending GPU outcomes"
                )

    opportunity = record.get("opportunity_search")
    if not isinstance(opportunity, dict):
        errors.append("opportunity_search must be an object")
        opportunity = {}
    opportunity_state = opportunity.get("status")
    if opportunity_state not in OPPORTUNITY_STATES:
        errors.append(
            f"opportunity_search.status must be one of {sorted(OPPORTUNITY_STATES)}"
        )
    if opportunity_state == "blocked" and not opportunity.get("reopening_fact"):
        errors.append("blocked opportunity_search requires reopening_fact")
    if opportunity_state in {"active", "admitted"} and not opportunity.get("task_id"):
        errors.append(f"{opportunity_state} opportunity_search requires task_id")

    zero_running = record.get("zero_gpu_running")
    zero_is_idle = zero_running == "explicit_idle"
    if not zero_is_idle:
        if not isinstance(zero_running, dict):
            errors.append(
                "zero_gpu_running must be an active task object or explicit_idle"
            )
        else:
            if task_id(zero_running) is None:
                errors.append("active zero_gpu_running requires task_id")
            for key in (
                "owner_thread_id",
                "kind",
                "expected_reasoning_effort",
                "terminal_event_id",
                "dispatch_receipt",
            ):
                if not isinstance(zero_running.get(key), str) or not zero_running[key].strip():
                    errors.append(f"active zero_gpu_running requires non-empty {key}")
            if zero_running.get("owner_thread_status") not in ACTIVE_THREAD_STATES:
                errors.append(
                    "active zero_gpu_running requires owner_thread_status=active"
                )
            if zero_running.get("callback_registered") is not True:
                errors.append(
                    "active zero_gpu_running requires callback_registered=true"
                )
            validate_task_lease(
                zero_running,
                "zero_gpu_running",
                record.get("controller_thread_id"),
                observed_at,
                errors,
            )
            validate_current_lease_against_registry(
                zero_running,
                "zero_gpu_running",
                worker_registry,
                errors,
            )
            effort = zero_running.get("expected_reasoning_effort")
            kind = zero_running.get("kind")
            if effort not in {"high", "max"}:
                errors.append(
                    "active zero_gpu_running expected_reasoning_effort must be high or max"
                )
            elif kind in DECISION_CRITICAL_ZERO_GPU_KINDS and effort != "max":
                errors.append(
                    f"decision-critical zero_gpu_running kind {kind} requires max reasoning"
                )
            progress_due = parse_utc(
                zero_running.get("progress_due_at_utc"),
                "zero_gpu_running.progress_due_at_utc",
                errors,
            )
            progress_overdue = (
                observed_at is not None
                and progress_due is not None
                and observed_at >= progress_due
            )
            handling = zero_running.get("progress_due_handling")
            if progress_overdue or handling is not None:
                validate_recovery_binding(
                    handling,
                    zero_running,
                    "zero_gpu_running.progress_due_handling",
                    PROGRESS_DUE_HANDLING,
                    errors,
                )

    gpu_running = record.get("gpu_running")
    if gpu_running is not None:
        if not isinstance(gpu_running, dict):
            errors.append("gpu_running must be an object or null")
        else:
            for key in (
                "task_id",
                "owner_thread_id",
                "execution_id",
                "terminal_event_id",
            ):
                if not isinstance(gpu_running.get(key), str) or not gpu_running[key].strip():
                    errors.append(f"gpu_running requires non-empty {key}")
            if gpu_running.get("observed_state") not in GPU_RUNNING_STATES:
                errors.append(
                    f"gpu_running.observed_state must be one of {sorted(GPU_RUNNING_STATES)}"
                )
            watchdog = gpu_running.get("watchdog")
            if not isinstance(watchdog, dict):
                errors.append("gpu_running requires watchdog object")
            else:
                if not isinstance(watchdog.get("automation_id"), str) or not watchdog[
                    "automation_id"
                ].strip():
                    errors.append("gpu_running.watchdog requires automation_id")
                if watchdog.get("state") != "active":
                    errors.append("gpu_running.watchdog.state must be active")
                expected_watchdog_bindings = {
                    "task_id": gpu_running.get("task_id"),
                    "execution_id": gpu_running.get("execution_id"),
                    "target_thread_id": gpu_running.get("owner_thread_id"),
                    "terminal_event_id": gpu_running.get("terminal_event_id"),
                    "wake_owner_thread_id": gpu_running.get("owner_thread_id"),
                    "controller_thread_id": record.get("controller_thread_id"),
                }
                for key, expected in expected_watchdog_bindings.items():
                    if watchdog.get(key) != expected:
                        errors.append(
                            f"gpu_running.watchdog.{key} must match the live job binding"
                        )
                watchdog_due = parse_utc(
                    watchdog.get("next_check_due_at_utc"),
                    "gpu_running.watchdog.next_check_due_at_utc",
                    errors,
                )
                watchdog_overdue = (
                    observed_at is not None
                    and watchdog_due is not None
                    and observed_at >= watchdog_due
                )
                due_handling = watchdog.get("due_handling")
                if watchdog_overdue or due_handling is not None:
                    if not isinstance(due_handling, dict):
                        errors.append(
                            "gpu_running.watchdog.due_handling requires job-bound evidence"
                        )
                    else:
                        if due_handling.get("state") not in WATCHDOG_DUE_HANDLING:
                            errors.append(
                                "gpu_running.watchdog.due_handling.state must be one of "
                                f"{sorted(WATCHDOG_DUE_HANDLING)}"
                            )
                        for key in (
                            "task_id",
                            "execution_id",
                            "automation_id",
                            "terminal_event_id",
                        ):
                            expected = (
                                watchdog.get("automation_id")
                                if key == "automation_id"
                                else gpu_running.get(key)
                            )
                            if due_handling.get(key) != expected:
                                errors.append(
                                    "gpu_running.watchdog.due_handling."
                                    f"{key} must match the live watchdog"
                                )
                        if not nonempty_string(due_handling.get("recovery_receipt")):
                            errors.append(
                                "gpu_running.watchdog.due_handling requires recovery_receipt"
                            )

    launch_ready = [
        item
        for item in gpu_queue
        if isinstance(item, dict) and item.get("queue_state") == "launch_ready"
    ]
    launch_in_progress = record.get("gpu_launch_in_progress")
    if gpu_running is None and launch_ready:
        if not isinstance(launch_in_progress, dict):
            errors.append(
                "launch-ready GPU work without gpu_running requires gpu_launch_in_progress"
            )
        else:
            for key in (
                "task_id",
                "owner_thread_id",
                "terminal_event_id",
                "dispatch_receipt",
            ):
                if not isinstance(launch_in_progress.get(key), str) or not launch_in_progress[
                    key
                ].strip():
                    errors.append(
                        f"gpu_launch_in_progress requires non-empty {key}"
                    )
            if launch_in_progress.get("owner_thread_status") not in ACTIVE_THREAD_STATES:
                errors.append(
                    "gpu_launch_in_progress requires owner_thread_status=active"
                )
            validate_task_lease(
                launch_in_progress,
                "gpu_launch_in_progress",
                record.get("controller_thread_id"),
                observed_at,
                errors,
            )
            validate_current_lease_against_registry(
                launch_in_progress,
                "gpu_launch_in_progress",
                worker_registry,
                errors,
            )
            expected_launch = task_id(launch_ready[0])
            if task_id(launch_in_progress) != expected_launch:
                errors.append(
                    "gpu_launch_in_progress must own the first launch-ready GPU queue item"
                )
    elif launch_in_progress not in (None, {}):
        errors.append(
            "gpu_launch_in_progress must be absent unless launch-ready work has no live GPU"
        )

    current_owner_leases: dict[str, set[tuple[str, str, str, int]]] = {}
    for current in (zero_running, launch_in_progress):
        binding = lease_tuple(current)
        if binding is None:
            continue
        current_owner_leases.setdefault(binding[1], set()).add(binding)
    for owner, bindings in current_owner_leases.items():
        if len(bindings) > 1:
            errors.append(
                f"owner_thread_id {owner} holds multiple current task leases"
            )

    admitted_backlog = [
        item
        for item in zero_backlog
        if isinstance(item, dict) and item.get("status") == "admitted"
    ]

    if zero_is_idle:
        if admitted_backlog:
            errors.append("explicit_idle is invalid while admitted zero-GPU work exists")
        if opportunity_state not in {"blocked", "budget_exhausted"}:
            errors.append(
                "explicit_idle requires Opportunity Search to be blocked with one "
                "reopening fact or budget_exhausted"
            )
        idle_proof = record.get("idle_proof")
        if not isinstance(idle_proof, dict):
            errors.append("explicit_idle requires idle_proof")
        else:
            categories = idle_proof.get("evaluated_categories")
            if not isinstance(categories, list) or set(categories) != IDLE_PROOF_CATEGORIES:
                errors.append(
                    "idle_proof.evaluated_categories must exactly cover "
                    f"{sorted(IDLE_PROOF_CATEGORIES)}"
                )
            if not idle_proof.get("reason"):
                errors.append("idle_proof requires reason")
            if not idle_proof.get("reopening_fact"):
                errors.append("idle_proof requires reopening_fact")
    elif record.get("idle_proof") not in (None, {}):
        errors.append("idle_proof must be absent when zero-GPU work is running")

    ready_analysis = [
        item
        for item in result_queue
        if isinstance(item, dict) and item.get("status") == "ready"
    ]
    if ready_analysis:
        for index, item in enumerate(result_queue):
            if not isinstance(item, dict) or item.get("status") != "ready":
                continue
            authority = item.get("terminal_authority")
            if not isinstance(authority, dict):
                errors.append(
                    f"result_analysis_queue[{index}] ready item requires "
                    "terminal_authority"
                )
                continue
            for key in ("terminal_id", "evidence_path"):
                if not isinstance(authority.get(key), str) or not authority[key].strip():
                    errors.append(
                        f"result_analysis_queue[{index}].terminal_authority "
                        f"requires non-empty {key}"
                    )
        expected = task_id(ready_analysis[0])
        if expected is None:
            errors.append("ready result-analysis item requires task_id")
        elif task_id(zero_running) != expected:
            errors.append(
                "ready GPU result analysis must preempt ordinary zero-GPU work"
            )

    if (record.get("gpu_running") is not None or gpu_queue) and zero_is_idle:
        if opportunity_state not in {"blocked", "budget_exhausted"}:
            errors.append(
                "GPU running/queued never justifies zero-GPU idle; Opportunity Search "
                "must run, be admitted, or carry a precise block/exhaustion proof"
            )

    terminal = record.get("terminal_transaction")
    if not isinstance(terminal, dict):
        errors.append("terminal_transaction must be an object")
        terminal = {}
    callback_state = terminal.get("callback_state")
    if callback_state not in TERMINAL_CALLBACK_STATES:
        errors.append(
            "terminal_transaction.callback_state must be one of "
            f"{sorted(TERMINAL_CALLBACK_STATES)}"
        )
    if callback_state == "acknowledged":
        if terminal.get("ack_kind") != "FINAL_ACK":
            errors.append("acknowledged terminal requires ack_kind=FINAL_ACK")
        final_ack_receipt = terminal.get("final_ack_receipt")
        if not nonempty_string(final_ack_receipt):
            errors.append(
                "acknowledged terminal requires a non-empty final_ack_receipt tool receipt"
            )
        delivered_callback = terminal.get("delivered_callback")
        history_matches: list[dict[str, Any]] = []
        if not isinstance(delivered_callback, dict):
            errors.append(
                "acknowledged terminal requires delivered_callback lease provenance"
            )
        else:
            source_binding = lease_tuple(delivered_callback)
            if source_binding is None:
                errors.append(
                    "terminal_transaction.delivered_callback requires a complete source lease tuple"
                )
            if not nonempty_string(delivered_callback.get("terminal_event_id")):
                errors.append(
                    "terminal_transaction.delivered_callback requires terminal_event_id"
                )
            if not nonempty_string(delivered_callback.get("callback_receipt")):
                errors.append(
                    "terminal_transaction.delivered_callback requires callback_receipt"
                )
            elif (
                nonempty_string(final_ack_receipt)
                and final_ack_receipt == delivered_callback.get("callback_receipt")
            ):
                errors.append(
                    "final_ack_receipt must be distinct from the delivery callback_receipt"
                )
            history_matches = [
                entry
                for entry in terminal_history
                if entry.get("callback_delivery_state") == "delivered"
                and all(
                    entry.get(key) == delivered_callback.get(key)
                    for key in (
                        "task_id",
                        "owner_thread_id",
                        "dispatch_id",
                        "lease_epoch",
                        "terminal_event_id",
                        "callback_receipt",
                    )
                )
            ]
            if len(history_matches) != 1:
                errors.append(
                    "acknowledged terminal delivered_callback must match exactly one durable terminal idempotency record"
                )
            if source_binding is not None:
                source_registry = worker_registry.get(source_binding[1])
                if source_registry is None:
                    errors.append(
                        "acknowledged terminal callback owner is absent from durable worker_registry"
                    )
                elif (
                    positive_int(source_registry.get("max_lease_epoch"))
                    and source_binding[3] > source_registry["max_lease_epoch"]
                ):
                    errors.append(
                        "acknowledged terminal callback lease exceeds durable max_lease_epoch"
                    )
        if terminal.get("portfolio_reconciled") is not True:
            errors.append(
                "acknowledged terminal requires portfolio_reconciled=true"
            )
        next_action = terminal.get("next_action")
        if not isinstance(next_action, dict):
            errors.append("acknowledged terminal requires next_action object")
        else:
            kind = next_action.get("kind")
            if kind not in NEXT_ACTIONS:
                errors.append(
                    f"next_action.kind must be one of {sorted(NEXT_ACTIONS)}"
                )
            if kind == "dispatch_next" and not next_action.get("task_id"):
                errors.append("dispatch_next requires task_id")
            if kind == "dispatch_next":
                for key in (
                    "owner_thread_id",
                    "terminal_event_id",
                    "dispatch_receipt",
                ):
                    if not isinstance(next_action.get(key), str) or not next_action[key].strip():
                        errors.append(f"dispatch_next requires non-empty {key}")
                if next_action.get("owner_thread_status") not in ACTIVE_THREAD_STATES:
                    errors.append("dispatch_next requires owner_thread_status=active")
                validate_task_lease(
                    next_action,
                    "terminal_transaction.next_action",
                    record.get("controller_thread_id"),
                    observed_at,
                    errors,
                )
                dispatched_binding = lease_tuple(next_action)
                live_bindings = {
                    binding
                    for binding in (
                        lease_tuple(zero_running),
                        lease_tuple(launch_in_progress),
                    )
                    if binding is not None
                }
                if dispatched_binding not in live_bindings:
                    errors.append(
                        "dispatch_next lease must exactly match active zero-GPU work or GPU launch owner"
                    )
            if kind == "queued":
                for key in ("task_id", "owner_thread_id", "start_prerequisite"):
                    if not isinstance(next_action.get(key), str) or not next_action[key].strip():
                        errors.append(f"queued next action requires non-empty {key}")
                queued_ids = {
                    task_id(item)
                    for item in [*gpu_queue, *zero_backlog]
                    if isinstance(item, dict)
                }
                if task_id(next_action) not in queued_ids:
                    errors.append("queued next action must match a durable backlog item")
            if kind == "explicit_hold":
                for key in (
                    "task_id",
                    "owner_thread_id",
                    "reopening_fact",
                    "reopening_predicate",
                    "observer_thread_id",
                    "next_evidence_action",
                ):
                    if not isinstance(next_action.get(key), str) or not next_action[key].strip():
                        errors.append(f"explicit_hold requires non-empty {key}")
                if not nonempty_string(next_action.get("reopen_trigger_ref")) and next_action.get(
                    "next_check_at_utc"
                ) is None:
                    errors.append(
                        "explicit_hold requires reopen_trigger_ref or next_check_at_utc"
                    )
                if next_action.get("next_check_at_utc") is not None:
                    parse_utc(
                        next_action.get("next_check_at_utc"),
                        "terminal_transaction.next_action.next_check_at_utc",
                        errors,
                    )
                matching_holds = [
                    item
                    for item in zero_backlog
                    if isinstance(item, dict)
                    and item.get("status") == "blocked"
                    and task_id(item) == task_id(next_action)
                    and item.get("reopening_fact") == next_action.get("reopening_fact")
                    and item.get("reopening_predicate")
                    == next_action.get("reopening_predicate")
                    and item.get("observer_thread_id")
                    == next_action.get("observer_thread_id")
                    and item.get("reopen_trigger_ref")
                    == next_action.get("reopen_trigger_ref")
                    and item.get("next_check_at_utc")
                    == next_action.get("next_check_at_utc")
                    and item.get("next_evidence_action")
                    == next_action.get("next_evidence_action")
                ]
                if not matching_holds:
                    errors.append(
                        "explicit_hold must match one blocked backlog item with the same reopening predicate, observer, trigger and next evidence action"
                    )
            if kind == "validated_idle" and not zero_is_idle:
                errors.append("validated_idle requires zero_gpu_running=explicit_idle")
        if terminal.get("watchdog_state") == "active":
            errors.append("acknowledged terminal cannot retain an active old watchdog")
        reconciled_at = parse_utc(
            terminal.get("portfolio_reconciled_at_utc"),
            "terminal_transaction.portfolio_reconciled_at_utc",
            errors,
        )
        acknowledged_at = parse_utc(
            terminal.get("acknowledged_at_utc"),
            "terminal_transaction.acknowledged_at_utc",
            errors,
        )
        if isinstance(next_action, dict) and next_action.get("kind") == "dispatch_next":
            activation = next_action.get("activation_evidence")
            activation_at = parse_utc(
                activation.get("observed_at_utc")
                if isinstance(activation, dict)
                else None,
                "terminal_transaction.next_action.activation_evidence.observed_at_utc",
                errors,
            )
            if (
                activation_at is not None
                and reconciled_at is not None
                and activation_at < reconciled_at
            ):
                errors.append(
                    "dispatch_next activation evidence must follow durable portfolio reconciliation"
                )
            if (
                activation_at is not None
                and acknowledged_at is not None
                and activation_at > acknowledged_at
            ):
                errors.append(
                    "dispatch_next activation evidence must precede FINAL_ACK"
                )
        if (
            reconciled_at is not None
            and acknowledged_at is not None
            and acknowledged_at < reconciled_at
        ):
            errors.append(
                "final terminal ACK must follow durable portfolio reconciliation"
            )
        if history_matches and reconciled_at is not None:
            delivered_at = parse_utc(
                history_matches[0].get("delivered_at_utc"),
                "terminal_idempotency_history delivered_at_utc",
                errors,
            )
            if delivered_at is not None and reconciled_at < delivered_at:
                errors.append(
                    "durable portfolio reconciliation must follow callback delivery"
                )
            if (
                delivered_at is not None
                and observed_at is not None
                and delivered_at > observed_at
            ):
                errors.append(
                    "callback delivery time cannot be later than the snapshot observation"
                )
        if (
            reconciled_at is not None
            and observed_at is not None
            and reconciled_at > observed_at
        ):
            errors.append(
                "portfolio reconciliation time cannot be later than the snapshot observation"
            )
        if (
            acknowledged_at is not None
            and observed_at is not None
            and acknowledged_at > observed_at
        ):
            errors.append(
                "FINAL_ACK time cannot be later than the snapshot observation"
            )
        if terminal.get("delivery_intent_durable") is not True:
            errors.append(
                "acknowledged terminal requires delivery_intent_durable=true"
            )

    pro = record.get("pro_advisory_lane")
    if not isinstance(pro, dict):
        errors.append("pro_advisory_lane must be an object")
        pro = {}
    live_jobs = pro.get("live_jobs")
    queued_reviews = pro.get("queue")
    response_ready = pro.get("response_ready")
    callback_observations = pro.get("callback_observations", [])
    if not isinstance(live_jobs, list):
        errors.append("pro_advisory_lane.live_jobs must be a list")
        live_jobs = []
    if not isinstance(queued_reviews, list):
        errors.append("pro_advisory_lane.queue must be a list")
        queued_reviews = []
    if not isinstance(response_ready, list):
        errors.append("pro_advisory_lane.response_ready must be a list")
        response_ready = []
    if not isinstance(callback_observations, list):
        errors.append("pro_advisory_lane.callback_observations must be a list")
        callback_observations = []
    live_job_ids: set[str] = set()
    actionable_event_keys: set[str] = set()
    for index, item in enumerate(live_jobs):
        prefix = f"pro_advisory_lane.live_jobs[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in (
            "job_id",
            "decision",
            "polling_owner",
            "completion_callback_thread_id",
        ):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"{prefix} requires non-empty {key}")
        binding = pro_callback_binding(item)
        if binding is None:
            errors.append(
                f"{prefix} requires owner_thread_id, callback_event_key, and positive owner_generation/job_generation"
            )
        else:
            job, owner, _, _, event_key = binding
            if job in live_job_ids:
                errors.append(f"pro_advisory_lane has duplicate live job_id {job}")
            live_job_ids.add(job)
            if event_key in actionable_event_keys:
                errors.append(
                    f"pro_advisory_lane has duplicate actionable callback_event_key {event_key}"
                )
            actionable_event_keys.add(event_key)
            if item.get("polling_owner") != owner:
                errors.append(f"{prefix}.polling_owner must match owner_thread_id")
        if item.get("completion_callback_configured") is not True:
            errors.append(
                f"{prefix} requires completion_callback_configured=true"
            )
        status = item.get("status")
        if status not in PRO_LIVE_STATES:
            errors.append(
                f"{prefix}.status must be one of {sorted(PRO_LIVE_STATES)}"
            )
        submitted_at = parse_utc(
            item.get("submitted_at_utc"), f"{prefix}.submitted_at_utc", errors
        )
        if (
            submitted_at is not None
            and observed_at is not None
            and submitted_at > observed_at
        ):
            errors.append(f"{prefix}.submitted_at_utc cannot be later than observed_at_utc")
        due_at = parse_utc(
            item.get("next_check_due_at_utc"),
            f"{prefix}.next_check_due_at_utc",
            errors,
        )
        if (
            status in {"submitted", "generating"}
            and observed_at is not None
            and due_at is not None
            and observed_at >= due_at
            and item.get("due_handling") not in PRO_DUE_HANDLING
        ):
            errors.append(
                f"{prefix} is due; set due_handling to one of "
                f"{sorted(PRO_DUE_HANDLING)} without resetting its due time"
            )
    if response_ready:
        first = response_ready[0]
        if not isinstance(first, dict) or not isinstance(first.get("job_id"), str):
            errors.append(
                "pro_advisory_lane.response_ready[0] requires job_id"
            )
        elif pro.get("adjudicating_job_id") != first["job_id"]:
            errors.append(
                "oldest response_ready Pro job must be claimed for adjudication"
            )
        ready_job_ids: set[str] = set()
        owner_generations, job_generations = pro_generation_maps(record)
        for index, item in enumerate(response_ready):
            prefix = f"pro_advisory_lane.response_ready[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for key in ("job_id", "decision", "owner_thread_id", "response_artifact"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append(f"{prefix} requires non-empty {key}")
            binding = pro_callback_binding(item)
            if binding is None:
                errors.append(
                    f"{prefix} requires callback_event_key and positive owner_generation/job_generation"
                )
            else:
                job, owner, owner_generation, job_generation, event_key = binding
                if job in ready_job_ids or job in live_job_ids:
                    errors.append(
                        f"Pro job_id {job} cannot be duplicated or both live and response_ready"
                    )
                ready_job_ids.add(job)
                if event_key in actionable_event_keys:
                    errors.append(
                        f"pro_advisory_lane has duplicate actionable callback_event_key {event_key}"
                    )
                actionable_event_keys.add(event_key)
                if item.get("callback_disposition") != "current":
                    errors.append(
                        f"{prefix}.callback_disposition must be current; stale/duplicate/closed callbacks are observation-only"
                    )
                if owner_generation < owner_generations.get(owner, owner_generation):
                    errors.append(
                        f"{prefix} has stale owner_generation and must be observation-only"
                    )
                if job_generation < job_generations.get(job, job_generation):
                    errors.append(
                        f"{prefix} has stale job_generation and must be observation-only"
                    )
            completed_at = parse_utc(
                item.get("completed_at_utc"),
                f"{prefix}.completed_at_utc",
                errors,
            )
            if (
                completed_at is not None
                and observed_at is not None
                and completed_at > observed_at
            ):
                errors.append(
                    f"{prefix}.completed_at_utc cannot be later than observed_at_utc"
                )
    else:
        ready_job_ids = set()

    actionable_records = [
        item
        for item in [*live_jobs, *response_ready]
        if isinstance(item, dict) and pro_callback_binding(item) is not None
    ]
    actionable_owner_floors: dict[str, int] = {}
    actionable_job_floors: dict[str, int] = {}
    for item in actionable_records:
        binding = pro_callback_binding(item)
        assert binding is not None
        job, owner, owner_generation, job_generation, _ = binding
        actionable_owner_floors[owner] = max(
            actionable_owner_floors.get(owner, 0), owner_generation
        )
        actionable_job_floors[job] = max(
            actionable_job_floors.get(job, 0), job_generation
        )
    for item in actionable_records:
        binding = pro_callback_binding(item)
        assert binding is not None
        job, owner, owner_generation, job_generation, event_key = binding
        if owner_generation < actionable_owner_floors[owner]:
            errors.append(
                f"actionable Pro callback {event_key} is below the current owner generation"
            )
        if job_generation < actionable_job_floors[job]:
            errors.append(
                f"actionable Pro callback {event_key} is below the current job generation"
            )

    observation_ids: set[str] = set()
    for index, item in enumerate(callback_observations):
        prefix = f"pro_advisory_lane.callback_observations[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        observation_id = item.get("observation_id")
        if not nonempty_string(observation_id):
            errors.append(f"{prefix} requires observation_id")
        elif observation_id in observation_ids:
            errors.append(f"duplicate Pro callback observation_id {observation_id}")
        else:
            observation_ids.add(observation_id)
        binding = pro_callback_binding(item)
        if binding is None:
            errors.append(
                f"{prefix} requires a complete job/owner/generation/event-key binding"
            )
            continue
        job, _, _, _, _ = binding
        disposition = item.get("disposition")
        if disposition not in PRO_CALLBACK_OBSERVATION_STATES:
            errors.append(
                f"{prefix}.disposition must be one of {sorted(PRO_CALLBACK_OBSERVATION_STATES)}"
            )
        effects = item.get("effect_counts")
        if not isinstance(effects, dict) or set(effects) != PRO_EFFECT_KEYS:
            errors.append(
                f"{prefix}.effect_counts must exactly contain {sorted(PRO_EFFECT_KEYS)}"
            )
        elif any(effects[key] != 0 for key in PRO_EFFECT_KEYS):
            errors.append(
                f"{prefix} stale/duplicate/closed callback must have zero local effects"
            )
        observed_callback_at = parse_utc(
            item.get("observed_at_utc"),
            f"{prefix}.observed_at_utc",
            errors,
        )
        if (
            observed_callback_at is not None
            and observed_at is not None
            and observed_callback_at > observed_at
        ):
            errors.append(
                f"{prefix}.observed_at_utc cannot be later than snapshot observed_at_utc"
            )
        if disposition == "closed":
            closed_at = parse_utc(
                item.get("closed_at_utc"),
                f"{prefix}.closed_at_utc",
                errors,
            )
            if (
                observed_callback_at is not None
                and closed_at is not None
                and observed_callback_at < closed_at
            ):
                errors.append(f"{prefix} closed observation predates slot closure")
            if (
                closed_at is not None
                and observed_at is not None
                and closed_at > observed_at
            ):
                errors.append(
                    f"{prefix}.closed_at_utc cannot be later than snapshot observed_at_utc"
                )
        if pro.get("adjudicating_job_id") == job and job not in ready_job_ids:
            errors.append(
                f"{prefix} observation-only callback cannot own local adjudication"
            )
    ready_reviews = [
        item
        for item in queued_reviews
        if isinstance(item, dict) and item.get("status") == "decision_ready"
    ]
    blocked = pro.get("dispatcher_blocked") is True or pro.get("cooldown_held") is True
    if ready_reviews and len(live_jobs) < 3 and not blocked:
        errors.append(
            "decision-ready Pro review must be submitted while a Pro slot is free"
        )
    if (
        not live_jobs
        and not queued_reviews
        and not response_ready
        and not pro.get("explicit_idle_reason")
    ):
        errors.append(
            "empty Pro lane requires explicit_idle_reason; do not silently leave it idle"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate global GPU, zero-GPU, result-analysis and Pro lanes."
    )
    parser.add_argument("record", type=Path)
    parser.add_argument(
        "--state",
        type=Path,
        required=True,
        help="durable cross-snapshot lease chronology watermark",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate against the watermark without advancing it",
    )
    args = parser.parse_args()

    try:
        record, record_sha256 = load_json_snapshot(args.record)
    except ValueError as exc:
        print(f"FAIL_RESEARCH_LANES: {exc}")
        return 2

    lock_path = args.state.with_name(f".{args.state.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            watermark = load_watermark(
                args.state, record.get("controller_thread_id")
            )
        except ValueError as exc:
            print(f"FAIL_RESEARCH_LANES: {exc}")
            return 2

        errors = validate(record)
        validate_durable_chronology(record, watermark, record_sha256, errors)
        # This is the final local authority read before a FINAL_ACK can advance
        # the durable watermark. A mismatch therefore has no ACK/watermark effect.
        validate_final_ack_terminal_artifact(record, errors)
        if errors:
            print("FAIL_RESEARCH_LANES")
            for error in errors:
                print(f"- {error}")
            return 1

        if not args.check_only:
            next_watermark = advance_watermark(record, watermark, record_sha256)
            # A duplicate/stale observation or exact replay has no durable
            # effect. Avoid even a serialization-only rewrite so legacy
            # schema-1 bytes and file metadata remain untouched.
            if next_watermark is not watermark:
                atomic_write_json(args.state, next_watermark)

    print("PASS_RESEARCH_LANES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
