#!/usr/bin/env python3
"""Read-only shadow detectors for workflow cost, trace defects, and conformance."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import statistics
import stat
from pathlib import Path
from typing import Any, Iterable


WORKSPACE_ROOT = Path("/Users/xiaowen/Documents/Obsidian Vault/003_科研")
SKILL_ROOT = Path(__file__).resolve().parents[1]
STATE_DB = Path("/Users/xiaowen/.codex/state_5.sqlite")
ARIS_THREAD_ID = "019fdaac-ce48-74d1-8fa0-94bab9ee2f3e"
SOFT_TOKEN_THRESHOLD = 25_000_000
HARD_TOKEN_THRESHOLD = 75_000_000
MIN_SOFT_TOKEN_TURNS = 2
MIN_RELATIVE_WINDOWS = 8
CONTEXT_WINDOW_SIZE = 20
CONTEXT_MIN_ROLLOVER_SAMPLES = 8
CONTEXT_MEDIAN_TARGET = 64_000
CONTEXT_P95_TARGET = 96_000
CONTEXT_MEDIAN_ROLLOVER = 96_000
CONTEXT_TAIL_LIMIT = 128_000
ISSUE_FIELDS = (
    "source_type",
    "detector",
    "observed_fact",
    "affected_stage",
    "impact",
    "recurrence_clue",
    "evidence_pointer",
    "protected_boundary_flag",
    "suggested_next_check",
    "fingerprint",
    "rule_ref",
    "mode",
)


class GateError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise GateError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(*parts: Any) -> str:
    return hashlib.sha256(_canonical(list(parts))).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_json_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object
        )
    except UnicodeDecodeError as exc:
        raise GateError("terminal_json is not strict UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise GateError("terminal_json is not valid JSON") from exc
    if not isinstance(value, dict):
        raise GateError("terminal_json must contain one object")
    return value


def _checked_rule_path(path: Path, workspace_root: Path, skill_root: Path) -> Path:
    if not path.is_absolute():
        raise GateError("rule-chain path must be absolute")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise GateError(f"rule-chain path is unavailable: {path}") from exc
    if resolved != path:
        raise GateError(f"rule-chain path uses traversal or a symlink: {path}")
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise GateError(f"rule-chain path is not a regular file: {path}")
    in_skill = _is_within(path, skill_root)
    workspace_agent = _is_within(path, workspace_root) and path.name == "AGENTS.md"
    if not in_skill and not workspace_agent:
        raise GateError(f"rule-chain path is outside allowed rule roots: {path}")
    return path


def _reported_sha256(value: Any, where: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise GateError(f"{where} must be one lowercase SHA-256")
    return value


def _rule_chain_assertions(
    rule_chain: Any,
    *,
    workspace_root: Path,
    skill_root: Path,
) -> list[tuple[Path, str]]:
    if not isinstance(rule_chain, dict):
        raise GateError("terminal.rule_chain must be an object")
    assertions: list[tuple[Path, str]] = []

    def walk(value: Any, where: str) -> None:
        if isinstance(value, dict):
            has_path = "path" in value
            has_sha = "sha256" in value
            if has_path != has_sha:
                raise GateError(f"{where} has an incomplete path/SHA-256 assertion")
            if has_path:
                raw_path = value["path"]
                if not isinstance(raw_path, str) or not raw_path:
                    raise GateError(f"{where}.path must be a non-empty string")
                path = _checked_rule_path(Path(raw_path), workspace_root, skill_root)
                assertions.append(
                    (path, _reported_sha256(value["sha256"], f"{where}.sha256"))
                )
                return
            for key, item in value.items():
                if key == "routed_references":
                    if not isinstance(item, dict) or not item:
                        raise GateError(
                            f"{where}.routed_references must be a non-empty object"
                        )
                    for name, digest in item.items():
                        if (
                            not isinstance(name, str)
                            or Path(name).name != name
                            or not name.endswith(".md")
                        ):
                            raise GateError("routed reference name must be one Markdown basename")
                        path = _checked_rule_path(
                            skill_root / "references" / name,
                            workspace_root,
                            skill_root,
                        )
                        assertions.append(
                            (
                                path,
                                _reported_sha256(
                                    digest,
                                    f"{where}.routed_references.{name}",
                                ),
                            )
                        )
                else:
                    walk(item, f"{where}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{where}[{index}]")

    walk(rule_chain, "terminal.rule_chain")
    if not assertions:
        raise GateError("terminal.rule_chain contains no file hash assertions")
    paths = [path for path, _ in assertions]
    if len(paths) != len(set(paths)):
        raise GateError("terminal.rule_chain contains duplicate file assertions")
    return assertions


def validate_rule_chain_terminal(
    terminal_path: Path,
    *,
    workspace_root: Path = WORKSPACE_ROOT,
    skill_root: Path = SKILL_ROOT,
) -> dict[str, Any]:
    terminal = _strict_json_file(terminal_path)
    assertions = _rule_chain_assertions(
        terminal.get("rule_chain"),
        workspace_root=workspace_root.resolve(strict=True),
        skill_root=skill_root.resolve(strict=True),
    )
    entries: list[dict[str, str]] = []
    mismatches: list[dict[str, str]] = []
    for path, reported in assertions:
        observed = _sha256_file(path)
        entry = {
            "path": str(path),
            "reported_sha256": reported,
            "observed_sha256": observed,
        }
        entries.append(entry)
        if reported != observed:
            mismatches.append(entry)
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "mode": "PRE_SEAL_READ_ONLY",
        "checked": len(entries),
        "entries": entries,
        "mismatches": mismatches,
    }


def _thread_record(db_path: Path, thread_id: str) -> tuple[Path, Path]:
    if thread_id == ARIS_THREAD_ID:
        raise GateError("ARIS thread is outside xiaowen-autoresearch workflow auditing")
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT rollout_path, cwd FROM threads WHERE id = ?", (thread_id,)
        ).fetchall()
    finally:
        connection.close()
    if len(rows) != 1:
        raise GateError("thread identity is missing or ambiguous")
    return Path(rows[0][0]), Path(rows[0][1])


def _canonical_dispatch_marker(event: dict[str, Any], dispatch_id: str) -> bool:
    """Match only the Controller-to-owner activation message, never later echoes."""

    if event.get("type") != "response_item":
        return False
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return False
    if payload.get("type") != "message" or payload.get("role") != "user":
        return False
    content = payload.get("content")
    if not isinstance(content, list):
        return False
    text = "\n".join(
        item["text"]
        for item in content
        if isinstance(item, dict)
        and item.get("type") in {"input_text", "text"}
        and isinstance(item.get("text"), str)
    )
    if not isinstance(dispatch_id, str) or not dispatch_id:
        return False
    if "LUNA_ROUTE_DISPATCH_ID" in text:
        return False
    marker_prefix = "MODEL_ROUTE_DISPATCH_ID="
    if text.count(marker_prefix) != 1:
        return False
    marker = rf"{re.escape(marker_prefix + dispatch_id)}"
    exact_marker = re.search(rf"(?m)^(?:[ \t]*{marker}|[ \t]*<input>{marker})$", text)
    return (
        exact_marker is not None
        and "PASS_MODEL_ROUTE:" in text
        and "await-successor-activation" in text
    )


def _token_usage(event: dict[str, Any]) -> int | None:
    if event.get("type") != "event_msg":
        return None
    payload = event.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "token_count":
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    last = info.get("last_token_usage")
    if not isinstance(last, dict):
        return None
    total = last.get("total_tokens")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise GateError("token_count last_token_usage.total_tokens is invalid")
    return total


def _context_input_tokens(event: dict[str, Any], line_number: int) -> int:
    payload = event.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "token_count":
        raise GateError(f"token_count event at line {line_number} is malformed")
    info = payload.get("info")
    if not isinstance(info, dict):
        raise GateError(f"token_count info at line {line_number} is malformed")
    last = info.get("last_token_usage")
    if not isinstance(last, dict):
        raise GateError(
            f"token_count last_token_usage at line {line_number} is malformed"
        )
    value = last.get("input_tokens")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GateError(
            f"token_count last_token_usage.input_tokens at line {line_number} is invalid"
        )
    return value


def scan_controller_context_window(
    rollout_path: Path,
    thread_id: str,
) -> tuple[str, int | None, list[int]]:
    """Read one rollout's session identity and the latest post-epoch input window."""

    session_id: str | None = None
    epoch_marker_line: int | None = None
    post_epoch_tokens: list[int] = []
    with rollout_path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw, object_pairs_hook=_strict_object)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise GateError(f"invalid rollout JSON at line {line_number}") from exc
            if not isinstance(event, dict):
                raise GateError(f"rollout event at line {line_number} must be an object")

            event_type = event.get("type")
            if event_type == "session_meta":
                if session_id is not None:
                    raise GateError("rollout contains multiple session_meta records")
                payload = event.get("payload")
                if not isinstance(payload, dict):
                    raise GateError("session_meta payload is missing or malformed")
                identity = payload.get("id")
                if not isinstance(identity, str) or not identity:
                    raise GateError("session_meta.id is missing")
                session_identity = payload.get("session_id")
                if session_identity is not None and (
                    not isinstance(session_identity, str)
                    or session_identity != identity
                ):
                    raise GateError("session_meta session identity is contradictory")
                if identity != thread_id:
                    raise GateError("session_meta.id does not match requested thread")
                session_id = identity
                continue

            if event_type == "compacted":
                epoch_marker_line = line_number
                post_epoch_tokens.clear()
                continue

            if event_type != "event_msg":
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            payload_type = payload.get("type")
            if payload_type == "context_compacted":
                epoch_marker_line = line_number
                post_epoch_tokens.clear()
            elif payload_type == "token_count":
                post_epoch_tokens.append(_context_input_tokens(event, line_number))

    if session_id is None:
        raise GateError("rollout is missing session_meta identity")
    return session_id, epoch_marker_line, post_epoch_tokens[-CONTEXT_WINDOW_SIZE:]


# Keep a short importable alias for callers that use the existing token-window naming.
scan_context_window = scan_controller_context_window


def _nearest_rank_p95(values: list[int]) -> int | None:
    if not values:
        return None
    rank = max(1, math.ceil(0.95 * len(values)))
    return sorted(values)[rank - 1]


def _integer_median(values: list[int]) -> int | float | None:
    if not values:
        return None
    median = statistics.median(values)
    if isinstance(median, float) and median.is_integer():
        return int(median)
    return median


def controller_context_decision(
    values: list[int],
    *,
    thread_id: str,
    session_id: str,
    epoch_marker_line: int | None,
) -> dict[str, Any]:
    count = len(values)
    median = _integer_median(values)
    p95 = _nearest_rank_p95(values)
    tail = 0
    for value in reversed(values):
        if value <= CONTEXT_TAIL_LIMIT:
            break
        tail += 1
    if tail >= CONTEXT_WINDOW_SIZE:
        decision = "PAUSE_NEW_OBJECTIVE_ADMISSION"
    elif (
        count >= CONTEXT_MIN_ROLLOVER_SAMPLES
        and median is not None
        and median > CONTEXT_MEDIAN_ROLLOVER
    ):
        decision = "REQUIRE_ROLLOVER"
    else:
        decision = "ALLOW"
    return {
        "status": "PASS",
        "mode": "CONTROLLER_CONTEXT_WINDOW",
        "thread_id": thread_id,
        "session_id": session_id,
        "count": count,
        "median": median,
        "p95": p95,
        "tail_consecutive_over_128000": tail,
        "epoch_marker_line": epoch_marker_line,
        "minimum_rollover_samples": CONTEXT_MIN_ROLLOVER_SAMPLES,
        "median_target": CONTEXT_MEDIAN_TARGET,
        "p95_target": CONTEXT_P95_TARGET,
        "decision": decision,
    }


def scan_token_window(rollout_path: Path, dispatch_id: str) -> tuple[int, int, int]:
    activation_lines: list[int] = []
    token_events: list[tuple[int, int]] = []
    with rollout_path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if dispatch_id not in raw and '"token_count"' not in raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise GateError(f"invalid rollout JSON at line {line_number}") from exc
            if dispatch_id in raw and _canonical_dispatch_marker(event, dispatch_id):
                activation_lines.append(line_number)
            token_usage = _token_usage(event)
            if token_usage is not None:
                token_events.append((line_number, token_usage))
    if len(activation_lines) != 1:
        raise GateError("dispatch activation point is missing or ambiguous")
    activation_line = activation_lines[0]
    usages = [usage for line, usage in token_events if line > activation_line and usage > 0]
    return sum(usages), len(usages), activation_line


def relative_soft_threshold(healthy_windows: Iterable[int]) -> int | None:
    windows = list(healthy_windows)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in windows):
        raise GateError("healthy comparable windows must be non-negative integers")
    if len(windows) < MIN_RELATIVE_WINDOWS:
        return None
    median = statistics.median(windows)
    mad = statistics.median(abs(value - median) for value in windows)
    return int(max(2 * median, median + 3 * mad))


def token_decision(
    *,
    thread_id: str,
    dispatch_id: str,
    token_total: int,
    token_turns: int,
    decision_output_count: int,
    healthy_windows: Iterable[int],
) -> dict[str, Any]:
    if decision_output_count < 0:
        raise GateError("decision_output_count must be non-negative")
    relative = relative_soft_threshold(healthy_windows)
    effective_soft = SOFT_TOKEN_THRESHOLD
    if relative is not None:
        effective_soft = min(HARD_TOKEN_THRESHOLD, max(effective_soft, relative))
    band = "NONE"
    if decision_output_count == 0:
        if token_total >= HARD_TOKEN_THRESHOLD:
            band = "HARD"
        elif token_turns >= MIN_SOFT_TOKEN_TURNS and token_total >= effective_soft:
            band = "SOFT"
    return {
        "status": "PASS",
        "mode": "SHADOW",
        "detector": "BACKWARD_OUTCOME_COST",
        "thread_id": thread_id,
        "dispatch_id": dispatch_id,
        "token_total": token_total,
        "token_turns": token_turns,
        "decision_output_count": decision_output_count,
        "soft_threshold": effective_soft,
        "hard_threshold": HARD_TOKEN_THRESHOLD,
        "relative_threshold": relative,
        "trigger": band,
        "fingerprint": None
        if band == "NONE"
        else _fingerprint("BACKWARD_OUTCOME_COST", thread_id, dispatch_id, band),
    }


def classify_conformance(event: dict[str, Any]) -> str:
    if event.get("authority_conflict") is True:
        return "AUTHORITY_CONFLICT"
    applicable = event.get("rule_applicable")
    feasible = event.get("rule_feasible")
    if applicable is not True or feasible is not True:
        return "NOT_ESTIMABLE"
    if event.get("shared_tooling_drift") is True:
        return "RULE_TOOLING_DRIFT"
    recurrence = event.get("independent_recurrence_count", 0)
    if isinstance(recurrence, bool) or not isinstance(recurrence, int) or recurrence < 0:
        raise GateError("independent_recurrence_count must be a non-negative integer")
    if event.get("compliant_zero_output") is True or recurrence >= 2:
        return "RULE_DESIGN_DEFECT"
    if event.get("isolated_deviation") is True:
        return "EXECUTION_NONCONFORMANCE"
    return "NOT_ESTIMABLE"


def _route_sample_int(event: dict[str, Any], field: str) -> int:
    value = event.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GateError(f"MODEL_ROUTE_SAMPLE.{field} must be a non-negative integer")
    return value


def _route_sample_bool(event: dict[str, Any], field: str) -> bool:
    value = event.get(field)
    if not isinstance(value, bool):
        raise GateError(f"MODEL_ROUTE_SAMPLE.{field} must be boolean")
    return value


def _route_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    def rate(field: str) -> float:
        return sum(_route_sample_bool(sample, field) for sample in samples) / len(samples)

    return {
        "sample_count": len(samples),
        "total_tokens_median": statistics.median(
            _route_sample_int(sample, "total_tokens") for sample in samples
        ),
        "wall_time_ms_median": statistics.median(
            _route_sample_int(sample, "wall_time_ms") for sample in samples
        ),
        "first_pass_acceptance_rate": rate("first_pass_acceptance"),
        "retry_count_median": statistics.median(
            _route_sample_int(sample, "retry_count") for sample in samples
        ),
        "decision_complete_output_rate": rate("decision_complete_output"),
        "reliability_pass_rate": rate("reliability_pass"),
    }


def model_route_scorecard(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare supplied existing process facts; never launch a benchmark task."""

    groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for event in events:
        if event.get("kind") != "MODEL_ROUTE_SAMPLE":
            continue
        comparison_key = event.get("comparison_key")
        route = event.get("route")
        if not isinstance(comparison_key, str) or not comparison_key:
            raise GateError("MODEL_ROUTE_SAMPLE.comparison_key must be a non-empty string")
        if route not in {"LUNA", "SOL"}:
            raise GateError("MODEL_ROUTE_SAMPLE.route must be LUNA or SOL")
        groups.setdefault(comparison_key, {"LUNA": [], "SOL": []})[route].append(event)

    scorecards: list[dict[str, Any]] = []
    for comparison_key in sorted(groups):
        routes = groups[comparison_key]
        if not routes["LUNA"] or not routes["SOL"]:
            scorecards.append(
                {
                    "comparison_key": comparison_key,
                    "mode": "SHADOW",
                    "disposition": "NOT_ESTIMABLE",
                    "reason": "both comparable Luna and Sol samples are required",
                    "sample_count": {
                        "LUNA": len(routes["LUNA"]),
                        "SOL": len(routes["SOL"]),
                    },
                }
            )
            continue

        luna = _route_summary(routes["LUNA"])
        sol = _route_summary(routes["SOL"])
        reliability_noninferior = (
            luna["reliability_pass_rate"] == 1.0
            and luna["reliability_pass_rate"] >= sol["reliability_pass_rate"]
        )
        quality_noninferior = (
            luna["first_pass_acceptance_rate"] >= sol["first_pass_acceptance_rate"]
            and luna["decision_complete_output_rate"]
            >= sol["decision_complete_output_rate"]
            and luna["retry_count_median"] <= sol["retry_count_median"]
        )
        cost_improved = (
            luna["total_tokens_median"] < sol["total_tokens_median"]
            and luna["wall_time_ms_median"] < sol["wall_time_ms_median"]
        )
        if not reliability_noninferior or not quality_noninferior:
            disposition = "ROLLBACK_REQUIRED"
        elif cost_improved:
            disposition = "RETAIN_ELIGIBLE"
        else:
            disposition = "NO_CHANGE"
        scorecards.append(
            {
                "comparison_key": comparison_key,
                "mode": "SHADOW",
                "disposition": disposition,
                "reliability_noninferior": reliability_noninferior,
                "quality_noninferior": quality_noninferior,
                "cost_improved": cost_improved,
                "LUNA": luna,
                "SOL": sol,
            }
        )
    return scorecards


def _issue(detector: str, event: dict[str, Any], observed_fact: str) -> dict[str, Any]:
    fingerprint = _fingerprint(
        detector,
        event.get("failure_fingerprint"),
        event.get("affected_stage"),
        observed_fact,
    )
    issue = {
        "source_type": event.get("source_type", "AUDITOR_DISCOVERY"),
        "detector": detector,
        "observed_fact": observed_fact,
        "affected_stage": event.get("affected_stage", "UNVERIFIED"),
        "impact": event.get("impact", "UNVERIFIED"),
        "recurrence_clue": event.get("recurrence_clue", "UNVERIFIED"),
        "evidence_pointer": event.get("evidence_pointer", "UNVERIFIED"),
        "protected_boundary_flag": bool(event.get("protected_boundary_flag", False)),
        "suggested_next_check": event.get("suggested_next_check", "VERIFY_TRACE"),
        "fingerprint": fingerprint,
        "rule_ref": event.get("rule_ref"),
        "mode": "SHADOW",
    }
    if set(issue) != set(ISSUE_FIELDS):
        raise AssertionError("issue envelope drift")
    return issue


def evaluate_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
        raise GateError("events input must be a list of objects")
    issues: list[dict[str, Any]] = []
    conformance: list[dict[str, Any]] = []
    fingerprint_counts: dict[str, int] = {}
    controller_wakes: dict[str, int] = {}
    forward_kinds = {
        "ACCESS_SELF_LOCK",
        "WHOLE_CHAIN_GAP",
        "USER_RESCUE",
        "MODEL_ROUTE_MISMATCH",
        "CREATE_NEW_ESCALATION",
        "ACTIVATION_READ_BEFORE_CAS",
    }
    for event in events:
        if event.get("detector") == "RULE_CONFORMANCE":
            conformance.append(
                {
                    "evidence_pointer": event.get("evidence_pointer", "UNVERIFIED"),
                    "classification": classify_conformance(event),
                }
            )
        kind = event.get("kind")
        fingerprint = event.get("failure_fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            fingerprint_counts[fingerprint] = fingerprint_counts.get(fingerprint, 0) + 1
        if kind == "CONTROLLER_WAKE":
            key = str(event.get("objective_id", "UNVERIFIED"))
            controller_wakes[key] = controller_wakes.get(key, 0) + 1
        elif kind in forward_kinds:
            issues.append(_issue("FORWARD_TRACE", event, str(kind)))

    for fingerprint, count in sorted(fingerprint_counts.items()):
        if count >= 2:
            event = next(item for item in events if item.get("failure_fingerprint") == fingerprint)
            issues.append(
                _issue(
                    "FORWARD_TRACE",
                    event,
                    f"REPEATED_FAILURE_FINGERPRINT:{fingerprint}:count={count}",
                )
            )
    for objective_id, count in sorted(controller_wakes.items()):
        if count > 1:
            event = next(
                item
                for item in events
                if item.get("kind") == "CONTROLLER_WAKE"
                and str(item.get("objective_id", "UNVERIFIED")) == objective_id
            )
            issues.append(
                _issue(
                    "FORWARD_TRACE",
                    event,
                    f"REPEATED_CONTROLLER_WAKE:{objective_id}:count={count}",
                )
            )

    deduped = {issue["fingerprint"]: issue for issue in issues}
    return {
        "status": "PASS",
        "mode": "SHADOW",
        "issues": [deduped[key] for key in sorted(deduped)],
        "rule_conformance": conformance,
        "model_route_scorecard": model_route_scorecard(events),
    }


def _load_json_value(raw: str, where: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GateError(f"{where} is not valid JSON") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    token = subparsers.add_parser("token-window")
    token.add_argument("--state-db", default=str(STATE_DB))
    token.add_argument("--workspace-root", default=str(WORKSPACE_ROOT))
    token.add_argument("--thread-id", required=True)
    token.add_argument("--dispatch-id", required=True)
    token.add_argument("--decision-output-count", type=int, required=True)
    token.add_argument("--healthy-windows-json", default="[]")
    context = subparsers.add_parser("controller-context-window")
    context.add_argument("--state-db", default=str(STATE_DB))
    context.add_argument("--workspace-root", default=str(WORKSPACE_ROOT))
    context.add_argument("--thread-id", required=True)
    events = subparsers.add_parser("evaluate-events")
    events.add_argument("--events-json", required=True)
    rule_chain = subparsers.add_parser("validate-rule-chain")
    rule_chain.add_argument("--terminal-json", required=True)
    rule_chain.add_argument("--workspace-root", default=str(WORKSPACE_ROOT))
    rule_chain.add_argument("--skill-root", default=str(SKILL_ROOT))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "token-window":
            rollout_path, cwd = _thread_record(Path(args.state_db), args.thread_id)
            workspace_root = Path(args.workspace_root)
            if not _is_within(cwd, workspace_root):
                raise GateError("thread cwd is outside the configured workspace")
            if not rollout_path.is_file():
                raise GateError("thread rollout_path is unavailable")
            healthy = _load_json_value(args.healthy_windows_json, "healthy_windows_json")
            if not isinstance(healthy, list):
                raise GateError("healthy_windows_json must be a list")
            token_total, token_turns, activation_line = scan_token_window(
                rollout_path, args.dispatch_id
            )
            result = token_decision(
                thread_id=args.thread_id,
                dispatch_id=args.dispatch_id,
                token_total=token_total,
                token_turns=token_turns,
                decision_output_count=args.decision_output_count,
                healthy_windows=healthy,
            )
            result["activation_line"] = activation_line
        elif args.command == "controller-context-window":
            rollout_path, cwd = _thread_record(Path(args.state_db), args.thread_id)
            workspace_root = Path(args.workspace_root)
            if not _is_within(cwd, workspace_root):
                raise GateError("thread cwd is outside the configured workspace")
            if not rollout_path.is_file():
                raise GateError("thread rollout_path is unavailable")
            session_id, epoch_marker_line, values = scan_controller_context_window(
                rollout_path,
                args.thread_id,
            )
            result = controller_context_decision(
                values,
                thread_id=args.thread_id,
                session_id=session_id,
                epoch_marker_line=epoch_marker_line,
            )
        elif args.command == "evaluate-events":
            events = _load_json_value(args.events_json, "events_json")
            result = evaluate_events(events)
        else:
            result = validate_rule_chain_terminal(
                Path(args.terminal_json),
                workspace_root=Path(args.workspace_root),
                skill_root=Path(args.skill_root),
            )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if args.command == "controller-context-window" and result["decision"] in {
            "PAUSE_NEW_OBJECTIVE_ADMISSION",
            "REQUIRE_ROLLOVER",
        }:
            return 2
        return 0 if result["status"] == "PASS" else 2
    except (GateError, OSError, UnicodeError, sqlite3.Error) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
