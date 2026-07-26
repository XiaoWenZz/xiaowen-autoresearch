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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("entries"), list):
        raise ValidationError("manifest must be an object with an entries array")
    return value


def load_ledger(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"cannot read exposure ledger {path}: {exc}") from exc
    records: list[dict[str, Any]] = []
    event_ids: set[str] = set()
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
        parse_time(record["observed_at"], f"ledger line {line_number}")
        records.append(record)
    return records


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
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    ledger = load_ledger(ledger_path)
    freeze_at = parse_time(freeze_at_raw, "freeze_at")
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
    return {
        "schema_version": "prospective-frame-validation-v1",
        "status": "PASS_FRESHNESS_LEDGER" if not mismatches else "INVALID_FRESHNESS_LEDGER",
        "freeze_at": freeze_at_raw,
        "manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
            "entry_count": len(entries),
        },
        "exposure_ledger": {
            "path": str(ledger_path),
            "sha256": sha256_file(ledger_path),
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
