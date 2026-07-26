#!/usr/bin/env python3
"""Append immutable task records or atomically refresh a worker heartbeat."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


STREAMS = {
    "directions": ("state/directions.jsonl", "direction_id"),
    "evidence": ("state/evidence.jsonl", "evidence_id"),
    "claims": ("state/claims.jsonl", "claim_id"),
    "iterations": ("state/iterations.jsonl", "iteration_id"),
    "approvals": ("state/approvals.jsonl", "approval_id"),
    "workers": ("state/workers.jsonl", "worker_record_id"),
    "events": ("logs/events.jsonl", "event_id"),
}


def utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def format_dt(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def load_record(args: argparse.Namespace) -> dict:
    if args.record_json is not None:
        raw = args.record_json
    else:
        raw = args.record_file.read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("record must be a JSON object")
    return value


def append_record(root: Path, stream: str, record: dict) -> None:
    relative_path, id_field = STREAMS[stream]
    path = root / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"missing stream: {path}")
    if id_field not in record and stream == "events":
        record[id_field] = f"EV-{uuid.uuid4().hex[:12]}"
    if not isinstance(record.get(id_field), str) or not record[id_field].strip():
        raise ValueError(f"record requires non-empty {id_field}")
    record.setdefault("recorded_at", format_dt(utc_now_dt()))

    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid existing JSON at {path}:{line_number}: {exc}") from exc
            if existing.get(id_field) == record[id_field]:
                raise ValueError(f"duplicate {id_field}: {record[id_field]}")
        handle.seek(0, os.SEEK_END)
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def update_heartbeat(root: Path, runner_id: str, status: str, lease_minutes: int) -> None:
    path = root / "state" / "heartbeat.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing heartbeat: {path}")
    current = json.loads(path.read_text(encoding="utf-8"))
    now = utc_now_dt()
    lease_expires = None if status in {"idle", "stopped"} else format_dt(now + timedelta(minutes=lease_minutes))
    current.update(
        {
            "runner_id": runner_id,
            "status": status,
            "last_seen_at": format_dt(now),
            "lease_expires_at": lease_expires,
        }
    )
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=".heartbeat-", delete=False
    ) as handle:
        json.dump(current, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    os.replace(temp_name, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    append_parser = subparsers.add_parser("append", help="append one immutable JSONL record")
    append_parser.add_argument("task_dir", type=Path)
    append_parser.add_argument("stream", choices=tuple(STREAMS))
    source = append_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--record-json")
    source.add_argument("--record-file", type=Path)

    heartbeat_parser = subparsers.add_parser("heartbeat", help="atomically refresh the liveness lease")
    heartbeat_parser.add_argument("task_dir", type=Path)
    heartbeat_parser.add_argument("--runner-id", required=True)
    heartbeat_parser.add_argument(
        "--status", choices=("alive", "idle", "waiting_external", "stopped"), default="alive"
    )
    heartbeat_parser.add_argument("--lease-minutes", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.task_dir.expanduser().resolve()
    try:
        if args.command == "append":
            append_record(root, args.stream, load_record(args))
            print(f"appended {args.stream} record")
        else:
            if args.lease_minutes < 1:
                raise ValueError("--lease-minutes must be positive")
            update_heartbeat(root, args.runner_id, args.status, args.lease_minutes)
            print(f"heartbeat updated: runner={args.runner_id} status={args.status}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
