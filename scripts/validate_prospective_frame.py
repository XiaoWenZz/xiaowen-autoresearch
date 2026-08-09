#!/usr/bin/env python3
"""Validate a prospective artifact frame against a cross-task exposure ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPOSURE_SEVERITY = {
    "metadata": 0,
    "claim": 1,
    "source": 2,
    "data": 2,
    "result": 2,
    "model": 2,
    "design": 2,
    "execution": 2,
    "protected": 2,
}
ACCESS_EXPOSURE_TYPES = {"result", "data", "model", "design", "execution", "protected"}
ACCESS_MODES = {"public_source", "protected", "confirmatory", "strict_result_blind"}
RISK_ACCESS_MODES = {"protected", "confirmatory", "strict_result_blind"}
SAFE_TEXT_EXTENSIONS = {
    ".bib",
    ".cfg",
    ".csv",
    ".ini",
    ".ipynb",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".mjs",
    ".py",
    ".rst",
    ".sh",
    ".tex",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}
OPERATIONAL_ACCESS_KEY = "operational_access"
SHELL_META_RE = re.compile(r"[\x00\r\n;&|<>$`\\*?]")
SENSITIVE_CODEX_DIRECTORIES = {
    "archived_sessions",
    "memories",
    "rollout_history",
    "rollout_summaries",
    "sessions",
}


class ValidationError(ValueError):
    """Raised when an input cannot support a fail-closed freshness decision."""


def parse_time(value: Any, context: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{context} requires a non-empty RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{context} has invalid RFC3339 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{context} timestamp must include a timezone: {value}")
    return parsed.astimezone(timezone.utc)


def load_manifest(path: Path) -> tuple[dict[str, Any], str]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("entries"), list):
        raise ValidationError("manifest must be an object with an entries array")
    return value, hashlib.sha256(payload).hexdigest()


def load_ledger(
    path: Path, *, require_append_only_chronology: bool = False
) -> tuple[list[dict[str, Any]], str]:
    try:
        payload = path.read_bytes()
        lines = payload.decode("utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValidationError(f"cannot read exposure ledger {path}: {exc}") from exc
    records: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    previous_time: datetime | None = None
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"invalid JSONL at ledger line {line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValidationError(f"ledger line {line_number} must be an object")
        for key in ("event_id", "artifact_id", "exposure_type", "observed_at", "source"):
            if not isinstance(record.get(key), str) or not record[key]:
                raise ValidationError(f"ledger line {line_number} requires non-empty {key}")
        event_id = record["event_id"]
        if event_id in event_ids:
            raise ValidationError(f"duplicate ledger event_id: {event_id}")
        event_ids.add(event_id)
        exposure_type = record["exposure_type"]
        if exposure_type not in EXPOSURE_SEVERITY:
            raise ValidationError(
                f"ledger line {line_number} has unsupported exposure_type: {exposure_type}"
            )
        observed_at = parse_time(record["observed_at"], f"ledger line {line_number}")
        if (
            require_append_only_chronology
            and previous_time is not None
            and observed_at < previous_time
        ):
            raise ValidationError(
                f"trusted access ledger line {line_number} regresses append-only chronology"
            )
        previous_time = observed_at
        records.append(record)
    return records, hashlib.sha256(payload).hexdigest()


def derive_tier(
    events: list[dict[str, Any]],
    freeze_at: datetime,
    fresh_tier: str,
    claim_tier: str,
    design_tier: str,
) -> tuple[str, list[dict[str, str]]]:
    effective: list[dict[str, str]] = []
    severity = 0
    for event in events:
        observed_at = parse_time(event["observed_at"], f"event {event['event_id']}")
        if observed_at > freeze_at:
            continue
        event_severity = EXPOSURE_SEVERITY[event["exposure_type"]]
        severity = max(severity, event_severity)
        effective.append(
            {
                "event_id": event["event_id"],
                "exposure_type": event["exposure_type"],
                "observed_at": event["observed_at"],
                "source": event["source"],
            }
        )
    if severity >= 2:
        tier = design_tier
    elif severity == 1:
        tier = claim_tier
    else:
        tier = fresh_tier
    return tier, sorted(effective, key=lambda item: (item["observed_at"], item["event_id"]))


def validate_safe_source_tree(
    root: Path,
    entries: list[dict[str, Any]],
    forbidden_text: list[str],
) -> dict[str, Any]:
    """Validate an exact, text-only safe tree without returning file contents."""
    try:
        unresolved_mode = root.lstat().st_mode
    except OSError as exc:
        raise ValidationError(f"cannot inspect safe source root {root}: {exc}") from exc
    if stat.S_ISLNK(unresolved_mode) or not stat.S_ISDIR(unresolved_mode):
        raise ValidationError("safe source root must be a real directory, not a symlink")
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise ValidationError(f"cannot resolve safe source root {root}: {exc}") from exc

    declared: dict[str, str] = {}
    for position, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValidationError(f"manifest entry {position} must be an object")
        raw_path = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(raw_path, str) or not raw_path:
            raise ValidationError(
                f"strict-result-blind manifest entry {position} requires non-empty path"
            )
        relative = Path(raw_path)
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() in {"", "."}:
            raise ValidationError(
                f"strict-result-blind manifest path must be canonical and relative: {raw_path}"
            )
        canonical = relative.as_posix()
        if canonical in declared:
            raise ValidationError(f"duplicate strict-result-blind manifest path: {canonical}")
        if not isinstance(digest, str) or not re_full_sha256(digest):
            raise ValidationError(
                f"strict-result-blind manifest path {canonical} requires canonical sha256"
            )
        declared[canonical] = digest.lower()

    actual: dict[str, Path] = {}
    try:
        descendants = sorted(root.rglob("*"), key=lambda path: path.as_posix())
    except OSError as exc:
        raise ValidationError(f"cannot enumerate safe source root {root}: {exc}") from exc
    for path in descendants:
        relative = path.relative_to(root).as_posix()
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            raise ValidationError(f"cannot inspect safe source path {relative}: {exc}") from exc
        if stat.S_ISLNK(mode):
            raise ValidationError(f"safe source tree contains symlink: {relative}")
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValidationError(f"safe source tree contains special file: {relative}")
        if path.suffix.casefold() not in SAFE_TEXT_EXTENSIONS:
            raise ValidationError(f"safe source tree contains opaque file type: {relative}")
        actual[relative] = path

    if set(actual) != set(declared):
        missing = sorted(set(declared) - set(actual))
        undeclared = sorted(set(actual) - set(declared))
        raise ValidationError(
            "safe source manifest/file set mismatch "
            f"(missing={missing}, undeclared={undeclared})"
        )

    forbidden_bytes: list[bytes] = []
    for position, value in enumerate(forbidden_text, start=1):
        if not isinstance(value, str) or not value:
            raise ValidationError(f"forbidden byte sequence {position} must be non-empty")
        forbidden_bytes.append(value.encode("utf-8"))

    for relative, path in actual.items():
        try:
            payload = path.read_bytes()
            payload.decode("utf-8", errors="strict")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValidationError(f"safe source file is not readable UTF-8 text: {relative}: {exc}") from exc
        digest = hashlib.sha256(payload).hexdigest()
        if digest != declared[relative]:
            raise ValidationError(f"safe source sha256 mismatch: {relative}")
        if any(marker in payload for marker in forbidden_bytes):
            raise ValidationError(
                f"safe source file contains a forbidden byte sequence: {relative}"
            )

    return {
        "status": "PASS_SAFE_SOURCE_TREE",
        "root": str(root),
        "file_count": len(actual),
        "forbidden_sequence_count": len(forbidden_bytes),
    }


def re_full_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdefABCDEF" for character in value)


def _canonical_absolute_path(raw_path: Any, context: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValidationError(f"{context} requires a non-empty absolute path")
    path = Path(raw_path)
    if (
        not path.is_absolute()
        or path.as_posix() != raw_path
        or "." in path.parts
        or ".." in path.parts
    ):
        raise ValidationError(f"{context} must be canonical and absolute: {raw_path}")
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ValidationError(f"{context} cannot inspect path {raw_path}: {exc}") from exc
    if stat.S_ISLNK(mode):
        raise ValidationError(f"{context} must be a regular non-symlink file: {raw_path}")
    if not stat.S_ISREG(mode):
        raise ValidationError(f"{context} must be a regular file, not a directory or special file: {raw_path}")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValidationError(f"{context} cannot resolve path {raw_path}: {exc}") from exc
    if resolved.as_posix() != raw_path:
        raise ValidationError(f"{context} must be canonical and absolute: {raw_path}")
    parts = tuple(part.casefold() for part in path.parts)
    if ".codex" in parts:
        codex_index = parts.index(".codex")
        if any(part in SENSITIVE_CODEX_DIRECTORIES for part in parts[codex_index + 1 :]):
            raise ValidationError(f"{context} targets a sensitive .codex history/state path: {raw_path}")
        filename = parts[-1]
        if (
            filename in {"state.sqlite", "state.sqlite3", "state.db"}
            or (filename.startswith("state_") and filename.endswith((".sqlite", ".sqlite3", ".db")))
        ):
            raise ValidationError(f"{context} targets a sensitive .codex history/state path: {raw_path}")
    return path


def _canonical_locator_path(raw_path: Any, context: str) -> str:
    """Validate a locator identity without touching the referenced path."""
    if not isinstance(raw_path, str) or not raw_path:
        raise ValidationError(f"{context} requires a non-empty absolute path")
    path = Path(raw_path)
    if (
        not path.is_absolute()
        or path.as_posix() != raw_path
        or "." in path.parts
        or ".." in path.parts
    ):
        raise ValidationError(f"{context} must be canonical and absolute: {raw_path}")
    return raw_path


def validate_operational_access(
    frame: Any,
    safe_source_root: Path,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate exact pre-bound files and activation argv for strict blindness."""
    if not isinstance(frame, dict):
        raise ValidationError(
            f"strict_result_blind requires top-level {OPERATIONAL_ACCESS_KEY} object"
        )
    expected_keys = {
        "authority_readable_paths",
        "helper_paths",
        "locator_only_paths",
        "activation_argv",
    }
    if set(frame) != expected_keys:
        raise ValidationError(
            f"{OPERATIONAL_ACCESS_KEY} must contain exactly authority_readable_paths, helper_paths, locator_only_paths, activation_argv"
        )

    def path_list(
        key: str,
        *,
        allow_empty: bool = False,
        locator_only: bool = False,
    ) -> tuple[list[str], set[str]]:
        raw_values = frame.get(key)
        if not isinstance(raw_values, list) or (not allow_empty and not raw_values):
            qualifier = "array" if allow_empty else "non-empty array"
            raise ValidationError(f"{OPERATIONAL_ACCESS_KEY}.{key} requires an {qualifier}")
        values: list[str] = []
        seen: set[str] = set()
        for position, raw_value in enumerate(raw_values, start=1):
            context = f"{OPERATIONAL_ACCESS_KEY}.{key}[{position}]"
            value = (
                _canonical_locator_path(raw_value, context)
                if locator_only
                else _canonical_absolute_path(raw_value, context).as_posix()
            )
            if value in seen:
                raise ValidationError(f"{context} duplicates path: {value}")
            seen.add(value)
            values.append(value)
        return values, seen

    authority_paths, authority_set = path_list("authority_readable_paths")
    raw_helpers = frame.get("helper_paths")
    if not isinstance(raw_helpers, list) or not raw_helpers:
        raise ValidationError(
            f"{OPERATIONAL_ACCESS_KEY}.helper_paths requires a non-empty array"
        )
    helper_paths: list[str] = []
    helper_set: set[str] = set()
    for position, raw_helper in enumerate(raw_helpers, start=1):
        context = f"{OPERATIONAL_ACCESS_KEY}.helper_paths[{position}]"
        if not isinstance(raw_helper, dict) or set(raw_helper) != {"path", "sha256"}:
            raise ValidationError(f"{context} must be an object with path and sha256")
        helper_path = _canonical_absolute_path(raw_helper["path"], f"{context}.path")
        helper_value = helper_path.as_posix()
        if helper_value in helper_set:
            raise ValidationError(f"{context}.path duplicates path: {helper_value}")
        digest = raw_helper["sha256"]
        if not isinstance(digest, str) or not re_full_sha256(digest):
            raise ValidationError(f"{context}.sha256 requires canonical sha256")
        try:
            helper_digest = hashlib.sha256(helper_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise ValidationError(f"{context}.path cannot read helper: {helper_value}: {exc}") from exc
        if helper_digest != digest.lower():
            raise ValidationError(f"{context}.sha256 mismatch: {helper_value}")
        helper_set.add(helper_value)
        helper_paths.append(helper_value)
    locator_paths, locator_set = path_list("locator_only_paths", allow_empty=True, locator_only=True)
    overlap = sorted(authority_set & locator_set)
    if overlap:
        raise ValidationError(
            "locator_only_paths must be disjoint from authority_readable_paths: "
            + ", ".join(overlap)
        )
    if not helper_set <= authority_set:
        missing = sorted(helper_set - authority_set)
        raise ValidationError(
            "operational helper path is not in authority_readable_paths: "
            + ", ".join(missing)
        )

    activation_argv = frame.get("activation_argv")
    if (
        not isinstance(activation_argv, list)
        or not activation_argv
        or any(not isinstance(value, str) or not value for value in activation_argv)
    ):
        raise ValidationError(
            f"{OPERATIONAL_ACCESS_KEY}.activation_argv must be a non-empty JSON string array"
        )
    executable = activation_argv[0]
    if not Path(executable).is_absolute() or executable not in authority_set:
        raise ValidationError(
            f"{OPERATIONAL_ACCESS_KEY}.activation_argv[1] executable must be a canonical absolute authority_readable_path"
        )
    for position, value in enumerate(activation_argv, start=1):
        if SHELL_META_RE.search(value):
            raise ValidationError(
                f"{OPERATIONAL_ACCESS_KEY}.activation_argv[{position}] contains shell metacharacters"
            )
        if Path(value).is_absolute():
            _canonical_locator_path(
                value, f"{OPERATIONAL_ACCESS_KEY}.activation_argv[{position}]"
            )
            if value not in authority_set | locator_set:
                raise ValidationError(
                    f"{OPERATIONAL_ACCESS_KEY}.activation_argv[{position}] absolute path is not in the bound readable/locator set: {value}"
                )
    referenced_helpers = helper_set.intersection(activation_argv)
    if not referenced_helpers:
        raise ValidationError(
            f"{OPERATIONAL_ACCESS_KEY}.activation_argv must reference a bound helper path"
        )

    try:
        safe_root = safe_source_root.resolve(strict=True)
    except OSError as exc:
        raise ValidationError(f"cannot resolve safe source root for operational access: {exc}") from exc
    if not safe_root.is_dir():
        raise ValidationError("safe source root for operational access must be a directory")
    for position, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValidationError(f"manifest entry {position} requires a safe-tree path")
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValidationError(f"manifest entry {position} safe-tree path is not canonical")
        try:
            safe_file = (safe_root / relative).resolve(strict=True)
        except OSError as exc:
            raise ValidationError(
                f"manifest entry {position} safe-tree path cannot resolve: {entry['path']}"
            ) from exc
        if safe_file.as_posix() not in authority_set:
            raise ValidationError(
                "safe-tree file is not in authority_readable_paths: " + safe_file.as_posix()
            )

    return {
        "status": "PASS_OPERATIONAL_ACCESS_FRAME",
        "authority_readable_path_count": len(authority_paths),
        "helper_path_count": len(helper_paths),
        "locator_only_path_count": len(locator_paths),
        "activation_argv_length": len(activation_argv),
    }


def validate(
    manifest_path: Path,
    ledger_path: Path,
    freeze_at_raw: str,
    id_field: str,
    tier_field: str,
    fresh_tier: str,
    claim_tier: str,
    design_tier: str,
    trusted_access_ledger_path: Path | None = None,
    plan_frozen_at_raw: str | None = None,
    access_mode: str | None = None,
    safe_source_root: Path | None = None,
    forbidden_text: list[str] | None = None,
) -> dict[str, Any]:
    manifest, manifest_sha256 = load_manifest(manifest_path)
    trusted_is_exposure_ledger = (
        trusted_access_ledger_path is not None
        and trusted_access_ledger_path.resolve() == ledger_path.resolve()
    )
    ledger, ledger_sha256 = load_ledger(
        ledger_path,
        require_append_only_chronology=trusted_is_exposure_ledger,
    )
    freeze_at = parse_time(freeze_at_raw, "freeze_at")
    effective_access_events = [
        event
        for event in ledger
        if event["exposure_type"] in ACCESS_EXPOSURE_TYPES
        and parse_time(event["observed_at"], f"event {event['event_id']}") <= freeze_at
    ]
    if access_mode is not None and access_mode not in ACCESS_MODES:
        raise ValidationError(f"unsupported access mode: {access_mode}")
    mode_was_inferred = access_mode is None and not effective_access_events
    effective_access_mode = access_mode or (
        "public_source" if not effective_access_events else "unspecified"
    )
    mode_invalid = False
    mode_reason: str | None = None
    if effective_access_mode == "unspecified":
        mode_invalid = True
        mode_reason = "protected/design/execution exposure exists; --access-mode is required"
    elif effective_access_mode == "public_source" and effective_access_events:
        mode_invalid = True
        mode_reason = "public_source cannot contain protected/design/execution exposure"
    elif effective_access_mode in RISK_ACCESS_MODES and (
        trusted_access_ledger_path is None or plan_frozen_at_raw is None
    ):
        mode_invalid = True
        mode_reason = (
            f"{effective_access_mode} requires --trusted-access-ledger and --plan-frozen-at"
        )
    if (trusted_access_ledger_path is None) != (plan_frozen_at_raw is None):
        raise ValidationError(
            "trusted access chronology requires both trusted_access_ledger and plan_frozen_at"
        )
    entries = manifest["entries"]
    artifact_ids: set[str] = set()
    events_by_artifact: dict[str, list[dict[str, Any]]] = {}
    for event in ledger:
        events_by_artifact.setdefault(event["artifact_id"], []).append(event)

    derived_entries: list[dict[str, Any]] = []
    mismatches: list[dict[str, str]] = []
    declared_counts = {fresh_tier: 0, claim_tier: 0, design_tier: 0}
    derived_counts = {fresh_tier: 0, claim_tier: 0, design_tier: 0}

    for position, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValidationError(f"manifest entry {position} must be an object")
        artifact_id = entry.get(id_field)
        declared_tier = entry.get(tier_field)
        if not isinstance(artifact_id, str) or not artifact_id:
            raise ValidationError(f"manifest entry {position} requires non-empty {id_field}")
        if artifact_id in artifact_ids:
            raise ValidationError(f"duplicate manifest artifact ID: {artifact_id}")
        artifact_ids.add(artifact_id)
        if declared_tier not in declared_counts:
            raise ValidationError(
                f"manifest artifact {artifact_id} has unsupported {tier_field}: {declared_tier}"
            )
        derived_tier, effective_events = derive_tier(
            events_by_artifact.get(artifact_id, []),
            freeze_at,
            fresh_tier,
            claim_tier,
            design_tier,
        )
        declared_counts[declared_tier] += 1
        derived_counts[derived_tier] += 1
        derived_entries.append(
            {
                "artifact_id": artifact_id,
                "declared_tier": declared_tier,
                "derived_tier": derived_tier,
                "effective_exposures": effective_events,
            }
        )
        if declared_tier != derived_tier:
            mismatches.append(
                {
                    "artifact_id": artifact_id,
                    "declared_tier": declared_tier,
                    "derived_tier": derived_tier,
                }
            )

    unknown_ledger_artifacts = sorted(set(events_by_artifact) - artifact_ids)
    access_chronology: dict[str, Any] = {
        "status": "NOT_APPLICABLE_PUBLIC_SOURCE",
        "reason": "public-source work has no protected result-access chronology",
    }
    if effective_access_mode in RISK_ACCESS_MODES:
        access_chronology = {
            "status": "NOT_EVALUATED",
            "reason": "no trusted append-only access ledger and prospective plan were supplied",
        }
    chronology_invalid = False
    if trusted_access_ledger_path is not None and plan_frozen_at_raw is not None:
        if trusted_is_exposure_ledger:
            access_events = ledger
            access_ledger_sha256 = ledger_sha256
        else:
            access_events, access_ledger_sha256 = load_ledger(
                trusted_access_ledger_path,
                require_append_only_chronology=True,
            )
        plan_frozen_at = parse_time(plan_frozen_at_raw, "plan_frozen_at")
        protected_accesses = [
            event
            for event in access_events
            if event["exposure_type"] in ACCESS_EXPOSURE_TYPES
        ]
        protected_accesses.sort(
            key=lambda event: (
                parse_time(event["observed_at"], f"event {event['event_id']}"),
                event["event_id"],
            )
        )
        first_access = protected_accesses[0] if protected_accesses else None
        first_access_at = (
            parse_time(
                first_access["observed_at"],
                f"event {first_access['event_id']}",
            )
            if first_access is not None
            else None
        )
        chronology_invalid = (
            first_access_at is not None and plan_frozen_at >= first_access_at
        )
        access_chronology = {
            "status": (
                "INVALID_PLAN_ACCESS_CHRONOLOGY"
                if chronology_invalid
                else "PASS_PLAN_BEFORE_ACCESS"
            ),
            "plan_frozen_at": plan_frozen_at_raw,
            "first_protected_access": (
                {
                    "event_id": first_access["event_id"],
                    "exposure_type": first_access["exposure_type"],
                    "observed_at": first_access["observed_at"],
                    "source": first_access["source"],
                }
                if first_access is not None
                else None
            ),
            "path": str(trusted_access_ledger_path),
            "sha256": access_ledger_sha256,
            "event_count": len(access_events),
        }
    safe_source_validation: dict[str, Any] = {
        "status": "NOT_APPLICABLE",
        "reason": "strict_result_blind mode was not selected",
    }
    operational_access_validation: dict[str, Any] = {
        "status": "NOT_APPLICABLE",
        "reason": "strict_result_blind mode was not selected",
    }
    safe_source_invalid = False
    if effective_access_mode == "strict_result_blind":
        if safe_source_root is None:
            safe_source_invalid = True
            safe_source_validation = {
                "status": "BLOCK_PRE_DISPATCH_ACCESS",
                "reason": "strict_result_blind requires --safe-source-root",
            }
        else:
            try:
                safe_source_validation = validate_safe_source_tree(
                    safe_source_root,
                    entries,
                    forbidden_text or [],
                )
            except ValidationError as exc:
                safe_source_invalid = True
                safe_source_validation = {
                    "status": "BLOCK_PRE_DISPATCH_ACCESS",
                    "reason": str(exc),
                }
            if not safe_source_invalid:
                try:
                    operational_access_validation = validate_operational_access(
                        manifest.get(OPERATIONAL_ACCESS_KEY),
                        safe_source_root,
                        entries,
                    )
                except ValidationError as exc:
                    safe_source_invalid = True
                    operational_access_validation = {
                        "status": "BLOCK_PRE_DISPATCH_ACCESS",
                        "reason": str(exc),
                    }

    status = "PASS_FRESHNESS_LEDGER"
    if mode_invalid:
        status = "INVALID_ACCESS_MODE"
    elif effective_access_mode in RISK_ACCESS_MODES and unknown_ledger_artifacts:
        status = "INVALID_UNKNOWN_LEDGER_ARTIFACT"
    elif safe_source_invalid:
        status = "BLOCK_PRE_DISPATCH_ACCESS"
    elif mismatches:
        status = "INVALID_FRESHNESS_LEDGER"
    elif chronology_invalid:
        status = "INVALID_ACCESS_CHRONOLOGY"
    return {
        "schema_version": "prospective-frame-validation-v1",
        "status": status,
        "access_mode": {
            "value": effective_access_mode,
            "inferred": mode_was_inferred,
            "reason": mode_reason,
            "effective_protected_event_count": len(effective_access_events),
        },
        "freeze_at": freeze_at_raw,
        "manifest": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
            "entry_count": len(entries),
        },
        "exposure_ledger": {
            "path": str(ledger_path),
            "sha256": ledger_sha256,
            "event_count": len(ledger),
            "unknown_artifact_count": len(unknown_ledger_artifacts),
            "unknown_artifacts": unknown_ledger_artifacts,
        },
        "tiers": {
            "fresh": fresh_tier,
            "claim_exposed": claim_tier,
            "design_or_execution_exposed": design_tier,
            "declared_counts": declared_counts,
            "derived_counts": derived_counts,
        },
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "access_chronology": access_chronology,
        "safe_source_validation": safe_source_validation,
        "operational_access_validation": operational_access_validation,
        "entries": sorted(derived_entries, key=lambda item: item["artifact_id"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--exposure-ledger", type=Path, required=True)
    parser.add_argument("--freeze-at", required=True, help="RFC3339 freeze time")
    parser.add_argument("--id-field", default="paper_id")
    parser.add_argument("--tier-field", default="confirmation_tier")
    parser.add_argument("--fresh-tier", default="P")
    parser.add_argument("--claim-tier", default="E")
    parser.add_argument("--design-tier", default="D")
    parser.add_argument(
        "--access-mode",
        choices=tuple(sorted(ACCESS_MODES)),
        help=(
            "public_source, protected, confirmatory, or strict_result_blind; "
            "omit only when the ledger has no protected/design/execution exposure"
        ),
    )
    parser.add_argument(
        "--trusted-access-ledger",
        type=Path,
        help="trusted append-only exposure ledger used only for plan/access chronology",
    )
    parser.add_argument(
        "--plan-frozen-at",
        help="RFC3339 prospective plan freeze time; required with --trusted-access-ledger",
    )
    parser.add_argument(
        "--safe-source-root",
        type=Path,
        help="exact text-only source tree required for strict_result_blind",
    )
    parser.add_argument(
        "--forbidden-text",
        action="append",
        default=[],
        help="non-empty UTF-8 sequence forbidden from the strict safe tree; repeatable",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = validate(
            args.manifest,
            args.exposure_ledger,
            args.freeze_at,
            args.id_field,
            args.tier_field,
            args.fresh_tier,
            args.claim_tier,
            args.design_tier,
            args.trusted_access_ledger,
            args.plan_frozen_at,
            args.access_mode,
            args.safe_source_root,
            args.forbidden_text,
        )
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        try:
            args.output.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: cannot write output {args.output}: {exc}", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(rendered)
    return 0 if result["status"] == "PASS_FRESHNESS_LEDGER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
