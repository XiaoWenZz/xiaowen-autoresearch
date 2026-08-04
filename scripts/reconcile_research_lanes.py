#!/usr/bin/env python3
"""Validate only real Managed shared resources and durable idempotency state.

This helper is intentionally not a portfolio scheduler. Legacy zero-GPU,
Opportunity Search, Pro, and global-idle fields are accepted as inert input for
old snapshots, but they are never required, validated, or advanced into the
durable watermark.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SNAPSHOT_SCHEMA_VERSION = 2
WATERMARK_SCHEMA_VERSION = 2
GPU_RUNNING_STATES = {"accepted_stabilizing", "running"}
GPU_QUEUE_STATES = {"blocked", "launch_ready"}
RESULT_ANALYSIS_STATES = {"ready", "running", "blocked"}
WATCHDOG_DUE_STATES = {"check_in_progress", "terminal_recovery_dispatched"}
CALLBACK_STATES = {
    "delivered",
    "acknowledged",
    "unconfirmed",
    "not_available",
}
QUEUE_AUTHORITY_KINDS = {
    "frozen_prospective_contract",
    "verified_scientific_terminal",
    "owner_approval",
}
LEASE_TRANSITION_KINDS = {"activate", "transfer", "revoke", "reclaim"}
CONTROLLER_ACTIONS = {
    "dispatch_next",
    "explicit_hold",
    "owner_approval_required",
    "scoped_close",
}
LEGACY_NONAUTHORITY_KEYS = {
    "zero_gpu_running",
    "zero_gpu_backlog",
    "opportunity_search",
    "idle_proof",
    "pro_advisory_lane",
}


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def parse_utc(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not nonempty_string(value):
        errors.append(f"{field} must be a non-empty RFC3339 timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be a valid RFC3339 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed.astimezone(timezone.utc)


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def lease_tuple(value: Any) -> tuple[str, str, str, int] | None:
    if not isinstance(value, dict):
        return None
    task_id = value.get("task_id")
    owner_id = value.get("owner_thread_id")
    dispatch_id = value.get("dispatch_id")
    epoch = value.get("lease_epoch")
    if not (
        nonempty_string(task_id)
        and nonempty_string(owner_id)
        and nonempty_string(dispatch_id)
        and positive_int(epoch)
    ):
        return None
    return str(task_id), str(owner_id), str(dispatch_id), int(epoch)


def callback_tuple(value: Any) -> tuple[str, str, str, int, str] | None:
    lease = lease_tuple(value)
    if lease is None or not nonempty_string(value.get("terminal_event_id")):
        return None
    return (*lease, str(value["terminal_event_id"]))


def registry_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = record.get("worker_registry")
    if not isinstance(entries, list):
        return {}
    return {
        str(entry["owner_thread_id"]): entry
        for entry in entries
        if isinstance(entry, dict) and nonempty_string(entry.get("owner_thread_id"))
    }


def validate_worker_registry(
    value: Any, *, required: bool, errors: list[str]
) -> dict[str, dict[str, Any]]:
    if value is None and not required:
        return {}
    if not isinstance(value, list):
        errors.append("worker_registry must be a list")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(value):
        prefix = f"worker_registry[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        owner = entry.get("owner_thread_id")
        if not nonempty_string(owner):
            errors.append(f"{prefix}.owner_thread_id must be non-empty")
            continue
        owner = str(owner)
        if owner in result:
            errors.append(f"worker_registry has duplicate owner_thread_id: {owner}")
        maximum = entry.get("max_lease_epoch")
        if not positive_int(maximum):
            errors.append(f"{prefix}.max_lease_epoch must be a positive integer")
        current = entry.get("current_lease")
        if current is not None:
            parsed = lease_tuple(current)
            if parsed is None:
                errors.append(f"{prefix}.current_lease is incomplete")
            else:
                if parsed[1] != owner:
                    errors.append(f"{prefix}.current_lease owner must match registry owner")
                if positive_int(maximum) and parsed[3] != maximum:
                    errors.append(
                        f"{prefix}.current_lease.lease_epoch must equal max_lease_epoch"
                    )
        result[owner] = entry
    return result


def validate_lease_transitions(value: Any, errors: list[str]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append("lease_transitions must be a list")
        return []
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, entry in enumerate(value):
        prefix = f"lease_transitions[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        transition_id = entry.get("transition_id")
        if not nonempty_string(transition_id):
            errors.append(f"{prefix}.transition_id must be non-empty")
        elif transition_id in seen:
            errors.append(f"duplicate lease transition_id: {transition_id}")
        else:
            seen.add(str(transition_id))
        if not nonempty_string(entry.get("owner_thread_id")):
            errors.append(f"{prefix}.owner_thread_id must be non-empty")
        if entry.get("kind") not in LEASE_TRANSITION_KINDS:
            errors.append(f"{prefix}.kind must be one of {sorted(LEASE_TRANSITION_KINDS)}")
        from_epoch = entry.get("from_epoch")
        to_epoch = entry.get("to_epoch")
        if from_epoch is not None and not positive_int(from_epoch):
            errors.append(f"{prefix}.from_epoch must be null or positive")
        if to_epoch is not None and not positive_int(to_epoch):
            errors.append(f"{prefix}.to_epoch must be null or positive")
        if entry.get("kind") in {"activate", "transfer"} and not positive_int(to_epoch):
            errors.append(f"{prefix} activation/transfer requires positive to_epoch")
        if not nonempty_string(entry.get("transition_receipt")):
            errors.append(f"{prefix}.transition_receipt must be non-empty")
        parse_utc(entry.get("transitioned_at_utc"), f"{prefix}.transitioned_at_utc", errors)
        result.append(entry)
    return result


def validate_terminal_history(
    value: Any, *, required: bool, errors: list[str]
) -> list[dict[str, Any]]:
    if value is None and not required:
        return []
    if not isinstance(value, list):
        errors.append("terminal_idempotency_history must be a list")
        return []
    by_event: dict[str, tuple[tuple[str, str, str, int, str], str, str | None]] = {}
    result: list[dict[str, Any]] = []
    for index, entry in enumerate(value):
        prefix = f"terminal_idempotency_history[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        binding = callback_tuple(entry)
        if binding is None:
            errors.append(f"{prefix} has incomplete task/owner/dispatch/lease/terminal binding")
            continue
        state = entry.get("callback_delivery_state")
        if state not in CALLBACK_STATES:
            errors.append(f"{prefix}.callback_delivery_state is invalid")
        receipt = entry.get("callback_receipt")
        if state in {"delivered", "acknowledged"} and not nonempty_string(receipt):
            errors.append(f"{prefix} delivered/acknowledged state requires callback_receipt")
        if state in {"delivered", "acknowledged"}:
            parse_utc(entry.get("delivered_at_utc"), f"{prefix}.delivered_at_utc", errors)
        digest = entry.get("terminal_sha256")
        if digest is not None and not (
            isinstance(digest, str)
            and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest)
        ):
            errors.append(f"{prefix}.terminal_sha256 must be canonical lowercase SHA-256")
        event = binding[4]
        fingerprint = (binding, str(receipt or ""), digest)
        if event in by_event and by_event[event] != fingerprint:
            errors.append(f"terminal_event_id {event} has conflicting duplicate delivery")
        else:
            by_event[event] = fingerprint
        result.append(entry)
    return result


def current_lease_for(
    owner: str, registry: dict[str, dict[str, Any]]
) -> tuple[str, str, str, int] | None:
    entry = registry.get(owner)
    return lease_tuple(entry.get("current_lease")) if isinstance(entry, dict) else None


def validate_bound_lease(
    value: Any,
    *,
    field: str,
    registry: dict[str, dict[str, Any]],
    expected_task: str | None = None,
    expected_owner: str | None = None,
    errors: list[str],
) -> tuple[str, str, str, int] | None:
    binding = lease_tuple(value)
    if binding is None:
        errors.append(f"{field} must bind task_id, owner_thread_id, dispatch_id, lease_epoch")
        return None
    if expected_task is not None and binding[0] != expected_task:
        errors.append(f"{field}.task_id must match {expected_task}")
    if expected_owner is not None and binding[1] != expected_owner:
        errors.append(f"{field}.owner_thread_id must match {expected_owner}")
    current = current_lease_for(binding[1], registry)
    if current != binding:
        errors.append(f"{field} must exactly match worker_registry.current_lease")
    return binding


def validate_watchdog(
    watchdog: Any,
    *,
    gpu: dict[str, Any],
    controller: str,
    observed_at: datetime | None,
    strict: bool,
    errors: list[str],
) -> None:
    if not isinstance(watchdog, dict):
        errors.append("gpu_running requires watchdog object")
        return
    if watchdog.get("state") != "active":
        errors.append("live gpu_running watchdog.state must be active")
    if not nonempty_string(watchdog.get("automation_id")):
        errors.append("gpu_running.watchdog.automation_id must be non-empty")
    due = parse_utc(
        watchdog.get("next_check_due_at_utc"),
        "gpu_running.watchdog.next_check_due_at_utc",
        errors,
    )
    if strict:
        bindings = {
            "task_id": gpu.get("task_id"),
            "execution_id": gpu.get("execution_id"),
            "target_thread_id": gpu.get("owner_thread_id"),
            "terminal_event_id": gpu.get("terminal_event_id"),
            "wake_owner_thread_id": gpu.get("owner_thread_id"),
            "controller_thread_id": controller,
        }
        for key, expected in bindings.items():
            if watchdog.get(key) != expected:
                errors.append(f"gpu_running.watchdog.{key} must match the live job")
    if observed_at is not None and due is not None and observed_at >= due:
        handling = watchdog.get("due_handling")
        if not isinstance(handling, dict):
            errors.append("overdue gpu watchdog requires task-bound due_handling")
            return
        if handling.get("state") not in WATCHDOG_DUE_STATES:
            errors.append("gpu watchdog due_handling.state is invalid")
        for key in ("task_id", "execution_id", "terminal_event_id"):
            if handling.get(key) != gpu.get(key):
                errors.append(f"gpu watchdog due_handling.{key} must match the live job")
        if not nonempty_string(handling.get("recovery_receipt")):
            errors.append("gpu watchdog due_handling.recovery_receipt must be non-empty")


def validate_gpu(
    record: dict[str, Any],
    *,
    registry: dict[str, dict[str, Any]],
    controller: str,
    observed_at: datetime | None,
    strict: bool,
    errors: list[str],
) -> None:
    running = record.get("gpu_running")
    if running is not None:
        if not isinstance(running, dict):
            errors.append("gpu_running must be null or an object")
        else:
            for key in ("task_id", "owner_thread_id", "execution_id", "terminal_event_id"):
                if not nonempty_string(running.get(key)):
                    errors.append(f"gpu_running.{key} must be non-empty")
            if running.get("observed_state") not in GPU_RUNNING_STATES:
                errors.append(f"gpu_running.observed_state must be one of {sorted(GPU_RUNNING_STATES)}")
            if strict and nonempty_string(running.get("task_id")) and nonempty_string(
                running.get("owner_thread_id")
            ):
                validate_bound_lease(
                    running.get("lease"),
                    field="gpu_running.lease",
                    registry=registry,
                    expected_task=str(running["task_id"]),
                    expected_owner=str(running["owner_thread_id"]),
                    errors=errors,
                )
            validate_watchdog(
                running.get("watchdog"),
                gpu=running,
                controller=controller,
                observed_at=observed_at,
                strict=strict,
                errors=errors,
            )

    queue = record.get("gpu_queue")
    if queue is None and not strict:
        queue = []
    if not isinstance(queue, list):
        errors.append("gpu_queue must be a list")
        return
    launch_ready: list[dict[str, Any]] = []
    seen_tasks: set[str] = set()
    for index, item in enumerate(queue):
        prefix = f"gpu_queue[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        task = item.get("task_id")
        if not nonempty_string(task):
            errors.append(f"{prefix}.task_id must be non-empty")
        elif task in seen_tasks:
            errors.append(f"gpu_queue has duplicate task_id: {task}")
        else:
            seen_tasks.add(str(task))
        if not nonempty_string(item.get("owner_thread_id")):
            errors.append(f"{prefix}.owner_thread_id must be non-empty")
        state = item.get("queue_state")
        if state not in GPU_QUEUE_STATES:
            errors.append(f"{prefix}.queue_state must be one of {sorted(GPU_QUEUE_STATES)}")
        if state == "blocked" and not nonempty_string(item.get("blocking_fact")):
            errors.append(f"{prefix} blocked item requires blocking_fact")
        if state == "launch_ready":
            launch_ready.append(item)
        authority = item.get("latest_authority")
        if not isinstance(authority, dict):
            errors.append(f"{prefix}.latest_authority must be an object")
        else:
            if authority.get("checked_against_latest_terminal") is not True:
                errors.append(f"{prefix} authority must check the latest terminal")
            if authority.get("source_kind") not in QUEUE_AUTHORITY_KINDS:
                errors.append(f"{prefix} has non-authoritative queue source")
            for key in ("authority_id", "evidence_path"):
                if not nonempty_string(authority.get(key)):
                    errors.append(f"{prefix}.latest_authority.{key} must be non-empty")
            if authority.get("queue_disposition") != "queue_gpu":
                errors.append(f"{prefix}.latest_authority.queue_disposition must be queue_gpu")

    launch = record.get("gpu_launch_in_progress")
    if launch_ready:
        if len(launch_ready) != 1:
            errors.append("at most one gpu_queue item may be launch_ready")
        if running is not None:
            errors.append("launch_ready GPU item requires gpu_running=null")
        if not isinstance(launch, dict):
            errors.append("launch_ready GPU item requires gpu_launch_in_progress")
        else:
            item = launch_ready[0]
            binding = validate_bound_lease(
                launch,
                field="gpu_launch_in_progress",
                registry=registry,
                expected_task=str(item.get("task_id")),
                expected_owner=str(item.get("owner_thread_id")),
                errors=errors,
            )
            if binding is not None and not nonempty_string(launch.get("dispatch_receipt")):
                errors.append("gpu_launch_in_progress.dispatch_receipt must be non-empty")
    elif launch is not None:
        errors.append("gpu_launch_in_progress requires exactly one launch_ready queue item")


def validate_result_analysis_queue(value: Any, *, required: bool, errors: list[str]) -> None:
    if value is None and not required:
        return
    if not isinstance(value, list):
        errors.append("result_analysis_queue must be a list")
        return
    seen: set[str] = set()
    for index, item in enumerate(value):
        prefix = f"result_analysis_queue[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        task = item.get("task_id")
        if not nonempty_string(task):
            errors.append(f"{prefix}.task_id must be non-empty")
        elif task in seen:
            errors.append(f"result_analysis_queue has duplicate task_id: {task}")
        else:
            seen.add(str(task))
        if item.get("status") not in RESULT_ANALYSIS_STATES:
            errors.append(f"{prefix}.status must be one of {sorted(RESULT_ANALYSIS_STATES)}")
        authority = item.get("terminal_authority")
        if not isinstance(authority, dict):
            errors.append(f"{prefix}.terminal_authority must be an object")
        else:
            for key in ("terminal_id", "evidence_path"):
                if not nonempty_string(authority.get(key)):
                    errors.append(f"{prefix}.terminal_authority.{key} must be non-empty")


def history_fingerprints(history: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in history:
        if isinstance(item, dict) and nonempty_string(item.get("terminal_event_id")):
            result[str(item["terminal_event_id"])] = canonical_sha256(item)
    return result


def validate_terminal_transaction(
    value: Any,
    *,
    history: list[dict[str, Any]],
    registry: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append("terminal_transaction must be an object")
        return
    state = value.get("callback_state")
    if state in {None, "none", "pending"}:
        return
    if state not in CALLBACK_STATES:
        errors.append("terminal_transaction.callback_state is invalid")
        return
    if state in {"delivered", "acknowledged"}:
        callback = value.get("delivered_callback")
        binding = callback_tuple(callback)
        if binding is None:
            errors.append("delivered terminal_transaction requires exact delivered_callback")
        else:
            matches = [
                item
                for item in history
                if callback_tuple(item) == binding
                and item.get("callback_receipt") == callback.get("callback_receipt")
                and item.get("callback_delivery_state") in {"delivered", "acknowledged"}
            ]
            if len(matches) != 1:
                errors.append(
                    "delivered_callback must match exactly one durable terminal history record"
                )
        if value.get("watchdog_state") not in {"paused", "not_required"}:
            errors.append("delivered terminal requires watchdog_state paused or not_required")
    if state == "acknowledged":
        action = value.get("controller_action")
        if not isinstance(action, dict):
            errors.append("acknowledged shared commit requires controller_action")
            return
        for key in ("transaction_id", "disposition"):
            if not nonempty_string(action.get(key)):
                errors.append(f"controller_action.{key} must be non-empty")
        parse_utc(action.get("decided_at"), "controller_action.decided_at", errors)
        next_action = action.get("next_action")
        if next_action not in CONTROLLER_ACTIONS:
            errors.append(f"controller_action.next_action must be one of {sorted(CONTROLLER_ACTIONS)}")
        if next_action == "dispatch_next":
            next_lease = action.get("next_lease")
            validate_bound_lease(
                next_lease,
                field="controller_action.next_lease",
                registry=registry,
                errors=errors,
            )
            if not nonempty_string(action.get("dispatch_receipt")):
                errors.append("controller_action dispatch_next requires dispatch_receipt")
        if next_action == "explicit_hold":
            for key in (
                "blocking_fact",
                "reopening_fact",
                "observer_thread_id",
                "reopen_trigger_ref",
                "next_evidence_action",
            ):
                if not nonempty_string(action.get(key)):
                    errors.append(f"controller_action explicit_hold requires {key}")


def validate_snapshot(record: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    version = record.get("schema_version")
    strict = version == SNAPSHOT_SCHEMA_VERSION
    if version not in {None, 1, SNAPSHOT_SCHEMA_VERSION}:
        errors.append(f"schema_version must be {SNAPSHOT_SCHEMA_VERSION} for new snapshots")
    controller = record.get("controller_thread_id")
    if not nonempty_string(controller):
        errors.append("controller_thread_id must be non-empty")
        controller = ""
    observed_at = parse_utc(record.get("observed_at_utc"), "observed_at_utc", errors)
    registry = validate_worker_registry(
        record.get("worker_registry"), required=strict, errors=errors
    )
    validate_lease_transitions(record.get("lease_transitions"), errors)
    history = validate_terminal_history(
        record.get("terminal_idempotency_history"), required=strict, errors=errors
    )
    validate_gpu(
        record,
        registry=registry,
        controller=str(controller),
        observed_at=observed_at,
        strict=strict,
        errors=errors,
    )
    validate_result_analysis_queue(
        record.get("result_analysis_queue"), required=strict, errors=errors
    )
    validate_terminal_transaction(
        record.get("terminal_transaction"),
        history=history,
        registry=registry,
        errors=errors,
    )
    ignored = sorted(LEGACY_NONAUTHORITY_KEYS.intersection(record))
    return errors, ignored


def empty_watermark(controller_thread_id: Any) -> dict[str, Any]:
    return {
        "schema_version": WATERMARK_SCHEMA_VERSION,
        "controller_thread_id": controller_thread_id,
        "generation": 0,
        "owner_registry": {},
        "terminal_history": [],
        "transition_fingerprints": [],
        "last_core_sha256": None,
    }


def load_watermark(path: Path, controller_thread_id: Any) -> dict[str, Any]:
    if not path.exists():
        return empty_watermark(controller_thread_id)
    value = load_json(path)
    if value.get("schema_version") not in {1, WATERMARK_SCHEMA_VERSION}:
        raise ValueError("durable shared-resource watermark schema_version is unsupported")
    if value.get("controller_thread_id") != controller_thread_id:
        raise ValueError("durable shared-resource watermark controller_thread_id mismatch")
    if not isinstance(value.get("owner_registry"), dict):
        raise ValueError("durable watermark owner_registry must be an object")
    if not isinstance(value.get("terminal_history"), list):
        raise ValueError("durable watermark terminal_history must be a list")
    if not isinstance(value.get("transition_fingerprints"), list):
        raise ValueError("durable watermark transition_fingerprints must be a list")
    return value


def transition_to_epoch(
    transitions: list[dict[str, Any]], owner: str, epoch: int
) -> bool:
    return any(
        item.get("owner_thread_id") == owner
        and item.get("kind") in {"activate", "transfer"}
        and item.get("to_epoch") == epoch
        and nonempty_string(item.get("transition_receipt"))
        for item in transitions
    )


def validate_durable_chronology(
    record: dict[str, Any], watermark: dict[str, Any], errors: list[str]
) -> None:
    current_registry = registry_map(record)
    prior_registry = watermark.get("owner_registry", {})
    transitions = record.get("lease_transitions")
    transitions = transitions if isinstance(transitions, list) else []
    strict = record.get("schema_version") == SNAPSHOT_SCHEMA_VERSION

    if current_registry:
        for owner, prior in prior_registry.items():
            if owner not in current_registry and strict:
                errors.append(
                    f"worker_registry must retain durable owner {owner} and its max epoch"
                )
                continue
            current = current_registry.get(owner)
            if not isinstance(current, dict) or not isinstance(prior, dict):
                continue
            prior_max = prior.get("max_lease_epoch", 0)
            current_max = current.get("max_lease_epoch", 0)
            if positive_int(prior_max) and (
                not positive_int(current_max) or int(current_max) < int(prior_max)
            ):
                errors.append(f"worker_registry owner {owner} regresses durable max_lease_epoch")
        for owner, current in current_registry.items():
            prior = prior_registry.get(owner)
            prior_max = prior.get("max_lease_epoch", 0) if isinstance(prior, dict) else 0
            current_max = current.get("max_lease_epoch", 0)
            if (
                watermark.get("generation", 0) > 0
                and positive_int(current_max)
                and int(current_max) > int(prior_max or 0)
                and not transition_to_epoch(transitions, owner, int(current_max))
            ):
                errors.append(
                    f"worker_registry owner {owner} advances epoch without a durable transition receipt"
                )

    prior_history = history_fingerprints(
        [item for item in watermark.get("terminal_history", []) if isinstance(item, dict)]
    )
    current_history = record.get("terminal_idempotency_history")
    if isinstance(current_history, list):
        for item in current_history:
            if not isinstance(item, dict) or not nonempty_string(item.get("terminal_event_id")):
                continue
            event = str(item["terminal_event_id"])
            fingerprint = canonical_sha256(item)
            if event in prior_history and prior_history[event] != fingerprint:
                errors.append(f"terminal_event_id {event} conflicts with durable history")
            binding = callback_tuple(item)
            if binding is not None:
                owner_record = current_registry.get(binding[1]) or prior_registry.get(binding[1])
                if isinstance(owner_record, dict):
                    durable_epoch = owner_record.get("max_lease_epoch")
                    if positive_int(durable_epoch) and binding[3] < int(durable_epoch):
                        errors.append(f"terminal_event_id {event} uses a stale lease epoch")


def merged_terminal_history(
    prior: list[Any], current: list[Any]
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in [*prior, *current]:
        if isinstance(item, dict) and nonempty_string(item.get("terminal_event_id")):
            merged[str(item["terminal_event_id"])] = copy.deepcopy(item)
    return [merged[key] for key in sorted(merged)]


def advance_watermark(record: dict[str, Any], watermark: dict[str, Any]) -> dict[str, Any]:
    next_value = copy.deepcopy(watermark)
    changed = False
    if "worker_registry" in record:
        current_registry = registry_map(record)
        if current_registry != next_value.get("owner_registry"):
            next_value["owner_registry"] = copy.deepcopy(current_registry)
            changed = True
    if "terminal_idempotency_history" in record:
        merged = merged_terminal_history(
            next_value.get("terminal_history", []),
            record.get("terminal_idempotency_history", []),
        )
        if merged != next_value.get("terminal_history"):
            next_value["terminal_history"] = merged
            changed = True
    if "lease_transitions" in record:
        fingerprints = sorted(
            set(next_value.get("transition_fingerprints", []))
            | {
                canonical_sha256(item)
                for item in record.get("lease_transitions", [])
                if isinstance(item, dict)
            }
        )
        if fingerprints != next_value.get("transition_fingerprints"):
            next_value["transition_fingerprints"] = fingerprints
            changed = True
    if not changed:
        return watermark
    core = {
        "owner_registry": next_value.get("owner_registry"),
        "terminal_history": next_value.get("terminal_history"),
        "transition_fingerprints": next_value.get("transition_fingerprints"),
    }
    next_value["last_core_sha256"] = canonical_sha256(core)
    next_value["generation"] = int(watermark.get("generation", 0)) + 1
    return next_value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Managed GPU, result-analysis, worker-lease, and terminal "
            "idempotency state without scheduling zero-GPU, Pro, or idle lanes."
        )
    )
    parser.add_argument("record", type=Path)
    parser.add_argument(
        "--state",
        type=Path,
        required=True,
        help="durable cross-snapshot lease and terminal-idempotency watermark",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate against the watermark without advancing it",
    )
    args = parser.parse_args()

    try:
        record = load_json(args.record)
    except ValueError as exc:
        print(f"FAIL_RESEARCH_LANES: {exc}")
        return 2

    lock_path = args.state.with_name(f".{args.state.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            watermark = load_watermark(args.state, record.get("controller_thread_id"))
        except ValueError as exc:
            print(f"FAIL_RESEARCH_LANES: {exc}")
            return 2

        errors, ignored = validate_snapshot(record)
        validate_durable_chronology(record, watermark, errors)
        if errors:
            print("FAIL_RESEARCH_LANES")
            for error in errors:
                print(f"- {error}")
            return 1

        if not args.check_only:
            next_watermark = advance_watermark(record, watermark)
            if next_watermark is not watermark:
                atomic_write_json(args.state, next_watermark)

    print("PASS_RESEARCH_LANES")
    if ignored:
        print("IGNORED_LEGACY_NONAUTHORITY=" + ",".join(ignored))
    return 0


if __name__ == "__main__":
    sys.exit(main())
