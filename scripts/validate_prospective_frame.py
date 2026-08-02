#!/usr/bin/env python3
"""Validate a prospective artifact frame against a cross-task exposure ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
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
        "status": "NOT_EVALUATED",
        "reason": "no trusted append-only access ledger was supplied",
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
    status = "PASS_FRESHNESS_LEDGER"
    if mismatches:
        status = "INVALID_FRESHNESS_LEDGER"
    elif chronology_invalid:
        status = "INVALID_ACCESS_CHRONOLOGY"
    return {
        "schema_version": "prospective-frame-validation-v1",
        "status": status,
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
        "--trusted-access-ledger",
        type=Path,
        help="trusted append-only exposure ledger used only for plan/access chronology",
    )
    parser.add_argument(
        "--plan-frozen-at",
        help="RFC3339 prospective plan freeze time; required with --trusted-access-ledger",
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
