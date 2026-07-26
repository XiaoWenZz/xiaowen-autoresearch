#!/usr/bin/env python3
"""Initialize a xiaowen-autoresearch task without overwriting existing content."""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "1.2"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:40] or "research-task"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument(
        "--task-type",
        choices=("literature", "experiment", "engineering", "mixed"),
        default="mixed",
    )
    parser.add_argument(
        "--governance-track",
        choices=("scout", "confirmatory"),
        default="scout",
        help="initialize durable Managed Scout state or full Confirmatory state",
    )
    parser.add_argument("--program-id")
    parser.add_argument("--epoch-id")
    parser.add_argument("--max-iterations", type=int, default=8)
    parser.add_argument("--max-cost-usd", type=float)
    parser.add_argument("--max-runtime-hours", type=float)
    parser.add_argument("--owner", default="user")
    parser.add_argument(
        "--adopt-existing",
        action="store_true",
        help=(
            "add durable state to an existing governed repository without "
            "overwriting AGENTS.md or existing project artifacts"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_iterations < 1:
        print("error: --max-iterations must be positive", file=sys.stderr)
        return 2
    if args.max_cost_usd is not None and args.max_cost_usd < 0:
        print("error: --max-cost-usd cannot be negative", file=sys.stderr)
        return 2
    if args.max_runtime_hours is not None and args.max_runtime_hours <= 0:
        print("error: --max-runtime-hours must be positive", file=sys.stderr)
        return 2

    root = args.task_dir.expanduser().resolve()
    root_is_nonempty = root.exists() and root.is_dir() and any(root.iterdir())
    if root.exists() and not root.is_dir():
        print(f"error: task path is not a directory: {root}", file=sys.stderr)
        return 2
    if root_is_nonempty and not args.adopt_existing:
        print(f"error: task directory must be absent or empty: {root}", file=sys.stderr)
        return 2
    if args.adopt_existing:
        if not root_is_nonempty:
            print("error: --adopt-existing requires a non-empty repository", file=sys.stderr)
            return 2
        if not (root / "AGENTS.md").is_file():
            print("error: --adopt-existing requires an existing AGENTS.md", file=sys.stderr)
            return 2
        collisions = [name for name in ("state", "runs", "logs", "reports") if (root / name).exists()]
        if collisions:
            print(
                "error: --adopt-existing refuses managed-state collisions: " + ", ".join(collisions),
                file=sys.stderr,
            )
            return 2
    root.mkdir(parents=True, exist_ok=True)

    created_at = utc_now()
    task_id = f"{slugify(args.title)}-{uuid.uuid4().hex[:8]}"
    program_id = args.program_id or task_id
    epoch_id = args.epoch_id or f"{program_id}-E1"
    operating_weight = "managed" if args.governance_track == "scout" else "full"

    agents_text = f"""# Research Task Rules

## Identity

- Task ID: `{task_id}`
- Program ID: `{program_id}`
- Epoch ID: `{epoch_id}`
- Task type: `{args.task_type}`
- Governance track: `{args.governance_track}`
- Operating weight: `{operating_weight}`
- Owner: `{args.owner}`

## Required practice

- Read `state/charter.json` before acting and do not run evidentiary work until it is frozen and validates with `--ready`.
- Keep Scout conclusions at `SCOUT_SIGNAL` or a scoped carrier-level stop. Promote to Confirmatory before public-test access, publication-facing comparison, or method-validation claims.
- Preserve JSONL state as append-only; append a superseding record instead of rewriting history.
- Create a run manifest before each experiment and preserve raw artifacts, failed runs, anomalies, and negative results.
- Do not change the research question, protocol, data split, primary metric, seed policy, budget, or claim boundary without a recorded approval.
- Separate facts, inferences, and hypotheses. Never let the evidence-producing worker accept its own claim.
- Record exact validation commands and pass/fail outcomes.
- Never store credentials or secrets in this task.
"""
    # AGENTS.md is intentionally the first task file for new tasks. An adopted
    # repository must already have its governing AGENTS.md and is never
    # overwritten here.
    if not args.adopt_existing:
        (root / "AGENTS.md").write_text(agents_text, encoding="utf-8")

    for directory in ("state", "runs", "artifacts", "logs", "reports"):
        (root / directory).mkdir(exist_ok=args.adopt_existing)

    charter = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "program_id": program_id,
        "epoch_id": epoch_id,
        "task_type": args.task_type,
        "governance_track": args.governance_track,
        "operating_weight": operating_weight,
        "governance_admission_proof": "",
        "title": args.title,
        "owner": args.owner,
        "objective": args.objective,
        "research_question": "",
        "hypotheses": [],
        "scope": {"in": [], "out": []},
        "success_criteria": [],
        "failure_criteria": [],
        "primary_metrics": [],
        "strongest_baseline": "",
        "claim_boundary": "",
        "governance": {
            "pre_evidence_iteration_budget": 2 if args.governance_track == "scout" else None,
            "promotion_trigger": "",
        },
        "protocol": {
            "frozen": False,
            "frozen_at": None,
            "code_version": "",
            "data_version": "",
            "data_split": "",
            "data_boundary": "",
            "seed_policy": "",
            "analysis_plan": "",
        },
        "budget": {
            "max_iterations": args.max_iterations,
            "max_cost_usd": args.max_cost_usd,
            "max_runtime_hours": args.max_runtime_hours,
        },
        "authorization": {
            "allowed": [
                "read_public_sources",
                "read_task_workspace",
                "write_task_workspace",
                "run_local_validation",
            ],
            "approval_required": [
                "change_charter",
                "increase_budget",
                "submit_compute_job",
                "external_write",
                "use_credentials_for_new_purpose",
                "publish_or_merge",
                "destructive_action",
            ],
            "forbidden": [
                "fabricate_evidence",
                "hide_negative_results",
                "store_secrets",
                "change_protocol_without_record",
            ],
        },
        "stop_conditions": [
            "success_criteria_met",
            "max_iterations_reached",
            "budget_exhausted",
            "same_structural_blocker_repeats_three_times",
            "required_approval_denied",
        ],
        "created_at": created_at,
        "updated_at": created_at,
    }
    progress = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "governance_track": args.governance_track,
        "operating_weight": operating_weight,
        "status": "draft",
        "phase": "charter",
        "iteration": 0,
        "active_run_id": None,
        "last_engineering_progress_at": None,
        "last_scientific_progress_at": None,
        "stale_count": 0,
        "next_action": "Complete, freeze, and validate the charter.",
        "blockers": [],
        "updated_at": created_at,
    }
    heartbeat = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "runner_id": None,
        "status": "idle",
        "last_seen_at": None,
        "lease_expires_at": None,
    }

    write_json(root / "state" / "charter.json", charter)
    write_json(root / "state" / "progress.json", progress)
    write_json(root / "state" / "heartbeat.json", heartbeat)
    for name in ("directions", "evidence", "claims", "iterations", "approvals", "workers"):
        (root / "state" / f"{name}.jsonl").touch()
    (root / "logs" / "events.jsonl").touch()

    print(f"initialized task: {task_id}")
    print(f"task directory: {root}")
    print(f"governance track: {args.governance_track}")
    print(f"operating weight: {operating_weight}")
    if args.adopt_existing:
        print("adopted existing repository without overwriting AGENTS.md or artifacts")
    print("next: complete state/charter.json, freeze it, then run validate_task.py --ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
