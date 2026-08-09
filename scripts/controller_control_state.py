#!/usr/bin/env python3
"""Validate and atomically update the rebuildable Controller control snapshot."""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = 5
LIFECYCLES = {"DELEGATED", "BLOCKED", "DONE"}
CANDIDATE_STATES = {"OPEN", "BLOCKED", "CLOSED"}
BLOCKER_KINDS = {"EXTERNAL_FACT", "UNAVAILABLE_AUTHORITY"}
EXECUTOR_CONTINUATION_KINDS = {"CARRIER", "ZERO_UTILITY_IMPLEMENTATION"}
CLOSURE_BASES = {
    "VALID_SCIENTIFIC_NEGATIVE",
    "PROSPECTIVE_SCOPED_MPE_FAILURE",
    "EXTERNAL_IMPOSSIBILITY",
}
EXTERNAL_IMPOSSIBILITY_REASONS = {
    "DATA_UNAVAILABLE",
    "HARDWARE_UNAVAILABLE",
    "IRRETRIEVABLE_REQUIRED_EVIDENCE",
    "LEGAL_OR_LICENSE_PROHIBITION",
    "REQUIRED_AUTHORITY_UNAVAILABLE",
    "SERVICE_OR_API_UNAVAILABLE",
}
ROLE_STATES = {
    "ACTIVE",
    "WAITING_EXTERNAL",
    "HOLD",
    "BLOCKED",
    "TERMINAL_PENDING_ABSORPTION",
}
MANAGED_ROLE_KINDS = {"Explorer", "Audit", "Executor"}
WAKE_STATES = {"NONE", "CLAIMED", "SENT"}
PENDING_VERIFICATION_STATES = {"IDENTITY_VERIFIED", "CONTROLLER_VERIFIED"}
ADVISORY_MONITOR_STATES = {"AWAITING_RESPONSE", "RESPONSE_OBSERVED"}
ADVISORY_READER_ROLES = {"Explorer", "Audit"}
ADVISORY_BATCH_MODES = {"NON_BLOCKING", "BLOCKING_HIGH_RISK"}
ADVISORY_GATE_TRANSITIONS = {"ACTIVATE_SUCCESSOR", "CLOSE_OBJECTIVE"}
FRESH_THREAD_REASONS = {
    "PROTECTED_RESULT_INDEPENDENCE",
    "STRICT_BLIND_EXPOSURE_REPLACEMENT",
    "INDEPENDENT_VERIFICATION_OR_ADJUDICATION",
    "WRITE_OWNERSHIP_TRANSFER",
    "INDEPENDENT_REPRODUCTION_OR_ANTI_ANCHORING",
    "VERIFIED_CONTEXT_ISOLATION_REQUIRED",
    "OWNER_THREAD_UNAVAILABLE_AFTER_RECOVERY_PROOF",
}
SAME_ROLE_FRESH_THREAD_REASONS = {
    "STRICT_BLIND_EXPOSURE_REPLACEMENT",
    "INDEPENDENT_REPRODUCTION_OR_ANTI_ANCHORING",
    "VERIFIED_CONTEXT_ISOLATION_REQUIRED",
    "OWNER_THREAD_UNAVAILABLE_AFTER_RECOVERY_PROOF",
}
AUDIT_FRESH_THREAD_REASONS = {
    "PROTECTED_RESULT_INDEPENDENCE",
    "INDEPENDENT_VERIFICATION_OR_ADJUDICATION",
}
CURSOR_OBSERVATION_KINDS = {"NON_TERMINAL", "TERMINAL"}
CURSOR_SOURCE_TURN_STATES = {"IN_PROGRESS", "FINAL"}
TITLE_RE = re.compile(
    r"^(Controller|Explorer|Audit|Executor) · .+ · "
    r"(ACTIVE|WAITING_EXTERNAL|HOLD|BLOCKED|TERMINAL_PENDING_ABSORPTION)$"
)
UNIT_RE = re.compile(r"^[A-Za-z0-9_.@:-]+\.service$")
REMOTE_HOSTS = {"dual5090", "ecnuhpc"}
REMOTE_OUTPUT_ROOTS = (PurePosixPath("/home/xiaowen/runs"), PurePosixPath("/home/xiaowen/projects"))
TERMINAL_ROOTS = (
    PurePosixPath("/private/tmp"),
    PurePosixPath("/tmp"),
    PurePosixPath(tempfile.gettempdir()),
    PurePosixPath("/Users/xiaowen/Documents/Obsidian Vault/003_科研/experiments"),
)
STARTUP_CHAIN_PROJECTION_KEYS = (
    "scientific_identity",
    "estimand",
    "metric",
    "baseline",
    "seeds",
    "exposure",
    "authority",
    "budget",
    "stop",
    "claim",
)
_STARTUP_AUTHORITY_UNSPECIFIED = object()
LEGACY_EXECUTOR_TERMINAL_SCHEMA = "V4_EXECUTOR_NO_STARTUP_AUTHORITY_MIRROR"
LEGACY_TERMINAL_COMPLETION_BINDING_PROJECTIONS = {
    "/private/tmp/TERM-SMI-E1-OPTSTATE-RETURN-GAP4-V4-R1-ATTEMPT006-SOURCE-SEAL-ROUTE-AUDIT-20260808-001.json": {
        "bytes": 131795,
        "sha256": "a89560212fa263b5e890bb3625bdfacde0803b6a58af2ed3e26f532c0a1713a1",
        "missing_from_binding": frozenset(),
        "allow_missing_startup_authority_mirror": False,
    },
    "/private/tmp/TERM-P59-RANK-RELEASE-CLEAN-ROOM-R2-V5-SCORING-ELIGIBILITY-SCOUT-EXECUTOR-ATTEMPT-003-20260808-001.json": {
        "bytes": 14432,
        "sha256": "70bb814182f566459a644b461b218c091cf0e24db4355d2a199edee5849be6e0",
        "missing_from_binding": frozenset({"terminal_event_id", "terminal_path"}),
        "allow_missing_startup_authority_mirror": True,
    },
    "/private/tmp/TERM-SMI-E1-OPTSTATE-RETURN-GAP4-V4-R1-ATTEMPT007-ROOT-CONTRACT-AUTHORIZED-IMPLEMENTATION-PROFILE-EXECUTOR-20260808-001.json": {
        "bytes": 15581,
        "sha256": "b0262f0302d7c126d73c63b4fe11d46885bd92cb257a26f31a2eb213963f1acb",
        "missing_from_binding": frozenset(),
        "allow_missing_startup_authority_mirror": True,
    },
    "/private/tmp/TERM-SMI-E1-OPTSTATE-RETURN-GAP4-V4-R1-ATTEMPT008-AUTHORITY-RECEIVER-LOCAL-ORCHESTRATION-BOUNDARY-AUDIT-20260808-001.json": {
        "bytes": 159707,
        "sha256": "f4ab04e70a452fb3ffe83b3f6a90cfb6fdbd8a7cf7cd6a174112722449635bd5",
        "missing_from_binding": frozenset(),
        "allow_missing_startup_authority_mirror": False,
        "allow_unbound_startup_authority_mirror": True,
    },
    "/private/tmp/TERM-SMI-E1-OPTSTATE-RETURN-GAP4-V4-CONFIRMATION-CONTRACT-IMPLEMENTATION-20260809-001.json": {
        "bytes": 11548,
        "sha256": "104fed10aa4758532ffa7473914dc9c54e09639bb3f861220a9c3b9aa6478440",
        "missing_from_binding": frozenset(),
        "allow_missing_startup_authority_mirror": True,
        "missing_startup_authority_requires_unbound_objective": True,
    },
    "/private/tmp/TERM-FPA-DP1-INTERNAL-PRESERVING-WITNESS-R1-EXECUTOR-20260809-001.json": {
        "bytes": 5088,
        "sha256": "6ece649999d5fde20df870e062723f68866abacfc0773cd4dea95bac9c1aefe7",
        "missing_from_binding": frozenset(),
        "allow_missing_startup_authority_mirror": True,
        "missing_startup_authority_requires_unbound_objective": True,
    },
}


class StateError(ValueError):
    pass


class ActivationWaitTimeout(StateError):
    """The Controller CAS is still absent after the bounded activation wait."""


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require(mapping: dict[str, Any], keys: tuple[str, ...], where: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise StateError(f"{where} missing keys: {', '.join(missing)}")


def _reject_unicode_surrogates(value: Any, where: str) -> Any:
    """Reject non-scalar Unicode recursively in JSON keys and values."""
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise StateError(f"{where} contains a Unicode surrogate")
    elif isinstance(value, list):
        for item in value:
            _reject_unicode_surrogates(item, where)
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_unicode_surrogates(key, where)
            _reject_unicode_surrogates(item, where)
    return value


def _timestamp(value: Any, where: str) -> datetime:
    if not _nonempty(value):
        raise StateError(f"{where} must be a non-empty timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StateError(f"{where} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise StateError(f"{where} must include a timezone")
    return parsed


def _sha256(value: Any, where: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise StateError(f"{where} must be a lowercase SHA-256")
    return value


def _validate_blocker_attestation(
    blocker: dict[str, Any],
    where: str,
) -> tuple[str, str] | None:
    """Validate the optional v5 external blocker attestation shape.

    Existing BLOCKED snapshots may omit both attestation fields.  Once either
    field is present, however, both are required and the reason/path/digest
    tuple is closed to the external-impossibility allowlist and immutable-path
    grammar.  Reading and digest verification are deliberately performed by
    the cold absorption command after the pending terminal is bound.
    """
    has_reason = "reason_code" in blocker
    has_evidence = "evidence_ref" in blocker
    if has_reason != has_evidence:
        raise StateError(
            f"{where}.reason_code and evidence_ref must be provided together"
        )
    if not has_reason:
        return None
    reason_code = blocker["reason_code"]
    if not isinstance(reason_code, str) or reason_code not in EXTERNAL_IMPOSSIBILITY_REASONS:
        raise StateError(
            f"{where}.reason_code must be one of {sorted(EXTERNAL_IMPOSSIBILITY_REASONS)}"
        )
    evidence_ref = blocker["evidence_ref"]
    if not isinstance(evidence_ref, str):
        raise StateError(f"{where}.evidence_ref must be an immutable path#sha256 reference")
    match = re.fullmatch(r"(.+)#sha256=([0-9a-f]{64})", evidence_ref)
    if match is None:
        raise StateError(
            f"{where}.evidence_ref must match <absolute-path>#sha256=<64 lowercase hex>"
        )
    normalized_path = _terminal_path(match.group(1), f"{where}.evidence_ref path")
    return str(normalized_path), match.group(2)


def _verify_blocker_attestation(
    blocker: dict[str, Any],
    *,
    pending_terminal_path: str,
    where: str,
) -> None:
    """Read and hash a new external blocker witness before the absorption CAS."""
    parsed = _validate_blocker_attestation(blocker, where)
    if parsed is None:
        raise StateError(f"{where} requires reason_code and evidence_ref")
    evidence_path, expected_digest = parsed
    pending_path = str(_terminal_path(pending_terminal_path, "pending terminal_path"))
    if evidence_path == pending_path:
        raise StateError(
            f"{where}.evidence_ref must not reference the absorbed worker terminal"
        )
    data = _read_immutable_terminal(Path(evidence_path))
    actual_digest = hashlib.sha256(data).hexdigest()
    if actual_digest != expected_digest:
        raise StateError(f"{where}.evidence_ref digest does not match immutable evidence")


def _terminal_path(value: Any, where: str) -> PurePosixPath:
    if not _nonempty(value):
        raise StateError(f"{where} must be a non-empty absolute path")
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts:
        raise StateError(f"{where} must be a normalized absolute path")
    if not any(path.is_relative_to(root) for root in TERMINAL_ROOTS):
        raise StateError(f"{where} is outside allowlisted immutable terminal roots")
    return path


def _validate_completion_binding(binding: Any, where: str) -> dict[str, Any]:
    if not isinstance(binding, dict):
        raise StateError(f"{where} must be an object")
    required = (
        "task_id",
        "dispatch_id",
        "lease_epoch",
        "contract_revision",
        "terminal_event_id",
        "terminal_path",
    )
    _require(binding, required, where)
    if set(binding) != set(required):
        raise StateError(f"{where} contains unsupported fields")
    for key in ("task_id", "dispatch_id", "terminal_event_id"):
        if not _nonempty(binding[key]):
            raise StateError(f"{where}.{key} must be non-empty")
    contract_revision = binding["contract_revision"]
    if not (
        _nonempty(contract_revision)
        or (
            isinstance(contract_revision, int)
            and not isinstance(contract_revision, bool)
            and contract_revision >= 1
        )
    ):
        raise StateError(
            f"{where}.contract_revision must be a non-empty string or positive integer"
        )
    if (
        isinstance(binding["lease_epoch"], bool)
        or not isinstance(binding["lease_epoch"], int)
        or binding["lease_epoch"] < 1
    ):
        raise StateError(f"{where}.lease_epoch must be a positive integer")
    _terminal_path(binding["terminal_path"], f"{where}.terminal_path")
    return binding


def completion_binding_sha256(binding: dict[str, Any]) -> str:
    _validate_completion_binding(binding, "completion_binding")
    return hashlib.sha256(canonical_bytes(binding)).hexdigest()


def derive_startup_chain_id(
    scientific_projection: dict[str, Any],
    production_entrypoint: str,
    zero_utility_barrier: str,
) -> str:
    """Derive, never accept, the repair identity from canonical hard inputs."""
    if not isinstance(scientific_projection, dict) or set(scientific_projection) != set(
        STARTUP_CHAIN_PROJECTION_KEYS
    ):
        raise StateError("scientific_projection must contain exactly the hard projection keys")
    for key in STARTUP_CHAIN_PROJECTION_KEYS:
        value = scientific_projection[key]
        if value is None or (_nonempty(value) is False and isinstance(value, str)):
            raise StateError(f"scientific_projection.{key} must be bound")
    if not _nonempty(production_entrypoint):
        raise StateError("production_entrypoint must be non-empty")
    if not _nonempty(zero_utility_barrier):
        raise StateError("zero_utility_barrier must be non-empty")
    payload = {
        "scientific_projection": scientific_projection,
        "production_entrypoint": production_entrypoint,
        "zero_utility_barrier": zero_utility_barrier,
    }
    return "startup-chain-sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def require_startup_chain_id(
    declared: Any,
    scientific_projection: dict[str, Any],
    production_entrypoint: str,
    zero_utility_barrier: str,
) -> str:
    derived = derive_startup_chain_id(
        scientific_projection,
        production_entrypoint,
        zero_utility_barrier,
    )
    if declared != derived:
        raise StateError("startup_chain_id is not the canonical derivation")
    return derived


def _startup_chain_id(value: Any, where: str) -> str:
    if not isinstance(value, str) or re.fullmatch(
        r"startup-chain-sha256:[0-9a-f]{64}", value
    ) is None:
        raise StateError(f"{where} must be a canonical startup-chain SHA-256")
    return value


def _validate_startup_chain_authority(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StateError(f"{where} must be an object")
    required = {
        "startup_chain_id",
        "contract_path",
        "contract_sha256",
        "prior_attempt_records",
    }
    if set(value) != required:
        raise StateError(f"{where} must contain exactly the authority fields")
    _startup_chain_id(value["startup_chain_id"], f"{where}.startup_chain_id")
    _terminal_path(value["contract_path"], f"{where}.contract_path")
    _sha256(value["contract_sha256"], f"{where}.contract_sha256")
    records = value["prior_attempt_records"]
    if not isinstance(records, list) or len(records) > 2:
        raise StateError(f"{where}.prior_attempt_records must contain zero to two records")
    paths: set[str] = set()
    for index, record in enumerate(records):
        record_where = f"{where}.prior_attempt_records[{index}]"
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            raise StateError(f"{record_where} must contain exactly path and sha256")
        _terminal_path(record["path"], f"{record_where}.path")
        _sha256(record["sha256"], f"{record_where}.sha256")
        if record["path"] in paths:
            raise StateError(f"{where}.prior_attempt_records contains a duplicate path")
        if record["path"] == value["contract_path"]:
            raise StateError(f"{where} contract and attempt paths must differ")
        paths.add(record["path"])
    return value


def _startup_chain_binding_from_contract(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise StateError("startup contract must be a JSON object")
    binding = contract.get("startup_chain_binding")
    if not isinstance(binding, dict):
        raise StateError("startup contract must contain startup_chain_binding")
    required = {
        "scientific_projection",
        "production_entrypoint",
        "zero_utility_barrier",
    }
    if set(binding) != required:
        raise StateError("startup_chain_binding must contain exactly the canonical inputs")
    derive_startup_chain_id(
        binding["scientific_projection"],
        binding["production_entrypoint"],
        binding["zero_utility_barrier"],
    )
    return binding


def _startup_attempt_round(record: Any, expected_chain_id: str) -> tuple[str, int]:
    if not isinstance(record, dict):
        raise StateError("startup attempt record must be a JSON object")
    attempt = record.get("startup_chain_attempt")
    if not isinstance(attempt, dict):
        raise StateError("attempt record must contain startup_chain_attempt")
    required = {
        "attempt_id",
        "startup_chain_id",
        "repair_round",
        "boundary",
        "utility_observed",
        "protected_access",
    }
    if set(attempt) != required:
        raise StateError("startup_chain_attempt must contain exactly the canonical fields")
    if not _nonempty(attempt["attempt_id"]):
        raise StateError("startup_chain_attempt.attempt_id must be non-empty")
    if attempt["startup_chain_id"] != expected_chain_id:
        raise StateError("attempt startup_chain_id does not match the immutable contract")
    repair_round = attempt["repair_round"]
    if (
        not isinstance(repair_round, int)
        or isinstance(repair_round, bool)
        or repair_round not in {1, 2}
    ):
        raise StateError("startup_chain_attempt.repair_round must be 1 or 2")
    if attempt["boundary"] != "PRE_UTILITY_FAILURE":
        raise StateError("only pre-utility failures consume startup repair rounds")
    if attempt["utility_observed"] is not False or attempt["protected_access"] is not False:
        raise StateError("startup repair history must remain outcome-blind")
    return attempt["attempt_id"], repair_round


def _open_terminal_no_symlinks(path: Path) -> int:
    """Open an allowlisted absolute path without following any path component."""
    normalized = _terminal_path(str(path), "terminal_path")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise StateError("platform lacks no-symlink terminal traversal support")
    components = normalized.parts[1:]
    if not components:
        raise StateError("terminal path must name a file beneath an allowlisted root")
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    directory_fd = os.open("/", directory_flags)
    try:
        for component in components[:-1]:
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        return os.open(components[-1], file_flags, dir_fd=directory_fd)
    except OSError as exc:
        raise StateError(f"terminal path has an unavailable or symlinked component: {path}") from exc
    finally:
        os.close(directory_fd)


def _read_immutable_terminal(path: Path) -> bytes:
    """Read one sealed terminal, rejecting symlink traversal and read-time mutation."""
    try:
        fd = _open_terminal_no_symlinks(path)
    except StateError:
        raise
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise StateError("terminal must be a regular non-symlink file")
        if before.st_nlink != 1:
            raise StateError("terminal link count must be one")
        if before.st_mode & 0o222:
            raise StateError("terminal must be immutable to ordinary writes")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    stable_fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise StateError("terminal changed while being read")
    try:
        verification_fd = _open_terminal_no_symlinks(path)
        directory_entry = os.fstat(verification_fd)
    except StateError as exc:
        raise StateError("terminal path changed while being read") from exc
    finally:
        if "verification_fd" in locals():
            os.close(verification_fd)
    if any(getattr(after, field) != getattr(directory_entry, field) for field in stable_fields):
        raise StateError("terminal path changed while being read")
    data = b"".join(chunks)
    if len(data) != after.st_size:
        raise StateError("terminal byte count changed while being read")
    if not data:
        raise StateError("terminal must be non-empty")
    return data


def _strict_json_document(data: bytes, where: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise StateError(f"{where} contains duplicate JSON key {key}")
            output[key] = value
        return output

    def reject_constant(value: str) -> Any:
        raise StateError(f"{where} contains non-standard JSON constant {value}")

    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise StateError(f"{where} contains non-finite JSON number {value}")
        return parsed

    try:
        document = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
            parse_float=finite_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateError(f"{where} must be valid UTF-8 JSON") from exc
    return _reject_unicode_surrogates(document, where)


def _legacy_terminal_completion_binding_projection(
    path: Path,
    data: bytes,
    terminal_body: dict[str, Any],
) -> dict[str, Any] | None:
    """Project two digest-pinned legacy envelopes onto the six-field identity."""
    path_text = str(path)
    projection = LEGACY_TERMINAL_COMPLETION_BINDING_PROJECTIONS.get(path_text)
    if projection is None:
        return None
    if (
        len(data) != projection["bytes"]
        or hashlib.sha256(data).hexdigest() != projection["sha256"]
    ):
        raise StateError("legacy terminal compatibility identity mismatch")
    raw_binding = terminal_body.get("completion_binding")
    if not isinstance(raw_binding, dict):
        raise StateError("terminal.completion_binding must be an object")
    required = (
        "task_id",
        "dispatch_id",
        "lease_epoch",
        "contract_revision",
        "terminal_event_id",
        "terminal_path",
    )
    missing = set(required) - set(raw_binding)
    if missing != projection["missing_from_binding"]:
        raise StateError("legacy terminal completion binding shape mismatch")
    projected = {key: raw_binding[key] for key in required if key in raw_binding}
    if "terminal_event_id" in missing:
        projected["terminal_event_id"] = terminal_body.get("terminal_event_id")
    if "terminal_path" in missing:
        projected["terminal_path"] = path_text
    return _validate_completion_binding(
        projected, "projected_legacy_terminal.completion_binding"
    )


def _read_bound_terminal(
    path: Path,
    expected_binding: dict[str, Any],
    expected_startup_authority: Any = _STARTUP_AUTHORITY_UNSPECIFIED,
    *,
    require_startup_authority_mirror: bool = False,
) -> tuple[bytes, dict[str, Any]]:
    _validate_completion_binding(expected_binding, "expected_completion_binding")
    data = _read_immutable_terminal(path)
    terminal_body = _strict_json_document(data, "terminal body")
    if not isinstance(terminal_body, dict):
        raise StateError("terminal body must be a JSON object")
    body_binding = _legacy_terminal_completion_binding_projection(
        path, data, terminal_body
    )
    compatibility_projection = (
        LEGACY_TERMINAL_COMPLETION_BINDING_PROJECTIONS.get(str(path))
        if body_binding is not None
        else {}
    )
    if body_binding is None:
        body_binding = _validate_completion_binding(
            terminal_body.get("completion_binding"), "terminal.completion_binding"
        )
    if body_binding != expected_binding:
        raise StateError("terminal completion binding does not match current dispatch/lease registry")
    for mirror in ("terminal_event_id", "terminal_path"):
        if mirror in terminal_body and terminal_body[mirror] != expected_binding[mirror]:
            raise StateError(f"terminal top-level {mirror} mirror does not match completion binding")
    if expected_startup_authority is not _STARTUP_AUTHORITY_UNSPECIFIED:
        body_has_authority = "startup_chain_authority" in terminal_body
        body_authority = terminal_body.get("startup_chain_authority")
        if (
            not body_has_authority
            and compatibility_projection.get(
                "missing_startup_authority_requires_unbound_objective", False
            )
            and expected_startup_authority is not None
        ):
            raise StateError(
                "legacy terminal missing startup_chain_authority is compatible only with an unbound objective"
            )
        if expected_startup_authority is None:
            if (
                require_startup_authority_mirror
                and not body_has_authority
                and not compatibility_projection.get(
                    "allow_missing_startup_authority_mirror", False
                )
            ):
                raise StateError(
                    "Executor terminal must explicitly bind startup_chain_authority"
                )
            if body_has_authority and body_authority is not None:
                if not compatibility_projection.get(
                    "allow_unbound_startup_authority_mirror", False
                ):
                    raise StateError(
                        "terminal startup_chain_authority mirror is not bound by the objective"
                    )
                body_authority = _validate_startup_chain_authority(
                    body_authority,
                    "terminal.startup_chain_authority",
                )
                _resolve_startup_chain_authority(body_authority)
        else:
            expected_startup_authority = _validate_startup_chain_authority(
                expected_startup_authority,
                "expected_startup_chain_authority",
            )
            _resolve_startup_chain_authority(expected_startup_authority)
            if (
                not body_has_authority
                and not compatibility_projection.get(
                    "allow_missing_startup_authority_mirror", False
                )
            ):
                raise StateError("terminal is missing the bound startup_chain_authority mirror")
            if body_has_authority:
                body_authority = _validate_startup_chain_authority(
                    body_authority,
                    "terminal.startup_chain_authority",
                )
                if body_authority != expected_startup_authority:
                    raise StateError(
                        "terminal startup_chain_authority does not match current objective authority"
                    )
    return data, terminal_body


def _resolve_startup_chain_authority(
    authority: dict[str, Any],
) -> tuple[str, set[int]]:
    """Resolve only the complete immutable history prebound by objective authority."""
    contract_data = _read_immutable_terminal(Path(authority["contract_path"]))
    if hashlib.sha256(contract_data).hexdigest() != authority["contract_sha256"]:
        raise StateError("startup contract digest does not match objective authority")
    contract = _strict_json_document(contract_data, "startup contract")
    binding = _startup_chain_binding_from_contract(contract)
    chain_id = derive_startup_chain_id(
        binding["scientific_projection"],
        binding["production_entrypoint"],
        binding["zero_utility_barrier"],
    )
    if chain_id != authority["startup_chain_id"]:
        raise StateError("startup contract identity does not match objective authority")

    attempt_ids: set[str] = set()
    rounds: set[int] = set()
    for index, record_ref in enumerate(authority["prior_attempt_records"]):
        record_path = record_ref["path"]
        record_data = _read_immutable_terminal(Path(record_path))
        if hashlib.sha256(record_data).hexdigest() != record_ref["sha256"]:
            raise StateError("startup attempt digest does not match objective authority")
        record = _strict_json_document(
            record_data,
            f"startup attempt record {record_path}",
        )
        attempt_id, repair_round = _startup_attempt_round(record, chain_id)
        if attempt_id in attempt_ids:
            raise StateError("startup attempt history contains a duplicate attempt_id")
        if repair_round in rounds:
            raise StateError("startup attempt history contains a duplicate repair round")
        if repair_round != index + 1:
            raise StateError("startup attempt repair rounds must be consecutive from round 1")
        attempt_ids.add(attempt_id)
        rounds.add(repair_round)
    expected_rounds = set(range(1, len(rounds) + 1))
    if rounds != expected_rounds:
        raise StateError("startup attempt repair rounds must be consecutive from round 1")
    return chain_id, rounds


def _transition_startup_chain_authority(
    previous: Any,
    requested: Any,
    *,
    new_owner_role: str,
) -> dict[str, Any] | None:
    """Preserve one repair budget monotonically across explicit transitions."""
    if previous is None:
        if requested is None:
            return None
        if new_owner_role != "Executor":
            raise StateError("startup-chain authority may be bound only to an Executor")
        requested = _validate_startup_chain_authority(
            requested, "new_startup_chain_authority"
        )
        _resolve_startup_chain_authority(requested)
        return requested

    previous = _validate_startup_chain_authority(
        previous, "existing_startup_chain_authority"
    )
    _resolve_startup_chain_authority(previous)
    if new_owner_role != "Executor":
        if requested is not None:
            raise StateError("an Audit boundary must not bind replacement startup authority")
        if new_owner_role != "Audit":
            raise StateError("leaving an active startup chain requires an Audit successor")
        return None

    if requested is None:
        return copy.deepcopy(previous)
    requested = _validate_startup_chain_authority(
        requested, "new_startup_chain_authority"
    )
    immutable_identity = (
        "startup_chain_id",
        "contract_path",
        "contract_sha256",
    )
    if any(previous[key] != requested[key] for key in immutable_identity):
        raise StateError("replacing an active startup chain requires an Audit boundary")
    old_records = previous["prior_attempt_records"]
    new_records = requested["prior_attempt_records"]
    if len(new_records) < len(old_records):
        raise StateError("startup-chain authority cannot shrink prior attempt history")
    if new_records[: len(old_records)] != old_records:
        raise StateError("startup-chain authority must preserve prior records monotonically")
    if len(new_records) > len(old_records) + 1:
        raise StateError("startup-chain authority may append only the next attempt record")
    _resolve_startup_chain_authority(requested)
    return requested


def _startup_chain_decision(rounds: set[int]) -> dict[str, Any]:
    """Map recorded failures to the one next startup action without off-by-one."""
    failures = len(rounds)
    if failures == 0:
        authorized_repair_round = None
        disposition = "RUN_INITIAL_STARTUP_WITNESS"
        on_failure = "RECORD_STARTUP_ATTEMPT"
    elif failures == 1:
        authorized_repair_round = 1
        disposition = "MINIMAL_REPAIR_IN_SAME_EXECUTOR"
        on_failure = "RECORD_STARTUP_ATTEMPT"
    elif failures == 2:
        authorized_repair_round = 2
        disposition = "CLEAN_CHAIN_REIMPLEMENTATION_IN_SAME_EXECUTOR"
        on_failure = "BOUNDED_ROOT_CAUSE_INVENTORY"
    else:
        raise StateError("startup-chain failure history exceeds the two-repair bound")
    return {
        "pre_utility_failures_recorded": failures,
        "authorized_repair_round": authorized_repair_round,
        "disposition": disposition,
        "on_full_witness_failure": on_failure,
    }


def _bound_terminal_envelope(
    path: Path,
    expected_binding: dict[str, Any],
    expected_startup_authority: Any = _STARTUP_AUTHORITY_UNSPECIFIED,
    *,
    require_startup_authority_mirror: bool = False,
) -> tuple[int, str]:
    data, _ = _read_bound_terminal(
        path,
        expected_binding,
        expected_startup_authority,
        require_startup_authority_mirror=require_startup_authority_mirror,
    )
    return len(data), hashlib.sha256(data).hexdigest()


def _requires_startup_authority_mirror(objective: dict[str, Any]) -> bool:
    return (
        objective.get("owner_role") == "Executor"
        and objective.get("legacy_terminal_schema")
        != LEGACY_EXECUTOR_TERMINAL_SCHEMA
    )


def _validate_owner_transition(
    *,
    old_thread_id: str,
    old_role: str,
    new_thread_id: str,
    new_role: str,
    fresh_thread_reason: Any,
    fresh_thread_evidence_ref: Any,
    controller_thread_id: str,
) -> None:
    if new_thread_id == controller_thread_id:
        raise StateError("Controller thread cannot be a managed owner")
    uses_fresh_thread = new_thread_id != old_thread_id
    if not uses_fresh_thread:
        if fresh_thread_reason is not None or fresh_thread_evidence_ref is not None:
            raise StateError("same-thread successor cannot record fresh-thread reason or evidence")
        if new_role != old_role:
            raise StateError("same-thread successor must preserve the canonical role")
        return
    if fresh_thread_reason not in FRESH_THREAD_REASONS:
        raise StateError("a different successor thread requires an allowlisted fresh_thread_reason")
    if not _nonempty(fresh_thread_evidence_ref):
        raise StateError("a different successor thread requires immutable fresh_thread_evidence_ref")
    if fresh_thread_reason in SAME_ROLE_FRESH_THREAD_REASONS and new_role != old_role:
        raise StateError(f"{fresh_thread_reason} must preserve the canonical role")
    if fresh_thread_reason in AUDIT_FRESH_THREAD_REASONS and new_role != "Audit":
        raise StateError(f"{fresh_thread_reason} requires an Audit successor")
    if fresh_thread_reason == "WRITE_OWNERSHIP_TRANSFER" and new_role == old_role:
        raise StateError("WRITE_OWNERSHIP_TRANSFER requires a canonical role change")


def _validate_executor_continuation(
    *,
    continuation_kind: Any,
    old_owner_thread_id: str,
    new_owner_thread_id: str,
    old_owner_role: str,
    new_owner_role: str,
    new_candidate_state: str,
    new_scientific_outcome: str,
    new_remote_job: dict[str, Any] | None,
    previous_startup_authority: Any,
    resulting_startup_authority: dict[str, Any] | None,
) -> None:
    """Enforce the non-persistent Executor successor continuation gate."""
    if new_owner_role != "Executor":
        if continuation_kind is not None:
            raise StateError(
                "executor-continuation-kind is allowed only for an Executor successor"
            )
        return
    if continuation_kind not in EXECUTOR_CONTINUATION_KINDS:
        raise StateError(
            "Executor successor requires --executor-continuation-kind CARRIER or "
            "ZERO_UTILITY_IMPLEMENTATION"
        )
    if continuation_kind == "CARRIER":
        if resulting_startup_authority is None:
            raise StateError("CARRIER Executor successor requires startup_chain_authority")
        return

    if (
        new_owner_thread_id != old_owner_thread_id
        or old_owner_role != "Executor"
        or new_owner_role != "Executor"
    ):
        raise StateError(
            "ZERO_UTILITY_IMPLEMENTATION requires the same Executor owner thread and role"
        )
    if new_candidate_state != "OPEN":
        raise StateError(
            "ZERO_UTILITY_IMPLEMENTATION requires candidate_state OPEN"
        )
    if new_scientific_outcome != "UNOBSERVED":
        raise StateError(
            "ZERO_UTILITY_IMPLEMENTATION requires scientific_outcome UNOBSERVED"
        )
    if new_remote_job is not None:
        raise StateError(
            "ZERO_UTILITY_IMPLEMENTATION cannot bind a new remote job"
        )
    if previous_startup_authority is None:
        if resulting_startup_authority is not None:
            raise StateError(
                "ZERO_UTILITY_IMPLEMENTATION cannot introduce startup_chain_authority"
            )
    elif resulting_startup_authority != previous_startup_authority:
        raise StateError(
            "ZERO_UTILITY_IMPLEMENTATION may only retain the existing startup_chain_authority"
        )


def validate_state(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise StateError("state must be a JSON object")
    _require(
        state,
        (
            "schema_version",
            "revision",
            "updated_at",
            "controller",
            "objectives",
            "managed_roles",
            "remote_jobs",
            "advisory_reads",
            "pending_absorptions",
            "absorbed_terminal_event_ids",
        ),
        "state",
    )
    if state["schema_version"] != SCHEMA_VERSION:
        raise StateError(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(state["revision"], int) or state["revision"] < 0:
        raise StateError("revision must be a non-negative integer")
    if not _nonempty(state["updated_at"]):
        raise StateError("updated_at must be non-empty")

    controller = state["controller"]
    if not isinstance(controller, dict):
        raise StateError("controller must be an object")
    _require(controller, ("thread_id", "project_id", "cwd", "title", "pin_required"), "controller")
    for key in ("thread_id", "project_id", "cwd", "title"):
        if not _nonempty(controller[key]):
            raise StateError(f"controller.{key} must be non-empty")
    if controller["pin_required"] is not True:
        raise StateError("controller.pin_required must be true")
    if not TITLE_RE.fullmatch(controller["title"]):
        raise StateError("controller.title is not canonical")

    objectives = state["objectives"]
    if not isinstance(objectives, list):
        raise StateError("objectives must be a list")
    objective_ids: set[str] = set()
    objective_gate_ids: set[str] = set()
    delegated_owner_threads: set[str] = set()
    completion_dispatches: set[tuple[str, str, int]] = set()
    completion_terminal_ids: set[str] = set()
    completion_terminal_paths: set[str] = set()
    for index, objective in enumerate(objectives):
        where = f"objectives[{index}]"
        if not isinstance(objective, dict):
            raise StateError(f"{where} must be an object")
        _require(
            objective,
            (
                "objective_id",
                "candidate_id",
                "candidate_state",
                "stage",
                "scientific_outcome",
                "lifecycle",
                "next_action",
            ),
            where,
        )
        for key in (
            "objective_id",
            "candidate_id",
            "candidate_state",
            "stage",
            "scientific_outcome",
            "next_action",
        ):
            if not _nonempty(objective[key]):
                raise StateError(f"{where}.{key} must be non-empty")
        if objective["objective_id"] in objective_ids:
            raise StateError(f"duplicate objective_id {objective['objective_id']}")
        objective_ids.add(objective["objective_id"])
        lifecycle = objective["lifecycle"]
        if lifecycle not in LIFECYCLES:
            raise StateError(f"{where}.lifecycle must be one of {sorted(LIFECYCLES)}")
        candidate_state = objective["candidate_state"]
        if candidate_state not in CANDIDATE_STATES:
            raise StateError(f"{where}.candidate_state must be one of {sorted(CANDIDATE_STATES)}")
        fresh_thread_reason = objective.get("fresh_thread_reason")
        if fresh_thread_reason is not None and fresh_thread_reason not in FRESH_THREAD_REASONS:
            raise StateError(f"{where}.fresh_thread_reason is not allowlisted")
        fresh_thread_evidence_ref = objective.get("fresh_thread_evidence_ref")
        if (fresh_thread_reason is None) != (fresh_thread_evidence_ref is None):
            raise StateError(f"{where} fresh-thread reason and evidence must appear together")
        if fresh_thread_evidence_ref is not None and not _nonempty(fresh_thread_evidence_ref):
            raise StateError(f"{where}.fresh_thread_evidence_ref must be non-empty")
        owner_recovery_evidence_ref = objective.get("owner_recovery_evidence_ref")
        if owner_recovery_evidence_ref is not None and not _nonempty(owner_recovery_evidence_ref):
            raise StateError(f"{where}.owner_recovery_evidence_ref must be non-empty")
        if lifecycle == "DELEGATED":
            if candidate_state != "OPEN":
                raise StateError(f"{where} delegated candidate must be OPEN")
            _require(objective, ("owner_thread_id", "owner_role", "owner_state"), where)
            if not all(_nonempty(objective[key]) for key in ("owner_thread_id", "owner_role", "owner_state")):
                raise StateError(f"{where} delegated owner fields must be non-empty")
            if objective["owner_state"] not in ROLE_STATES:
                raise StateError(f"{where}.owner_state must be canonical")
            owner_thread_id = objective["owner_thread_id"]
            if owner_thread_id in delegated_owner_threads:
                raise StateError(f"duplicate delegated owner_thread_id {owner_thread_id}")
            delegated_owner_threads.add(owner_thread_id)
            binding = _validate_completion_binding(
                objective.get("completion_binding"), f"{where}.completion_binding"
            )
            dispatch_key = (
                binding["task_id"],
                binding["dispatch_id"],
                binding["lease_epoch"],
            )
            if dispatch_key in completion_dispatches:
                raise StateError(f"{where}.completion_binding duplicates a dispatch/lease")
            completion_dispatches.add(dispatch_key)
            if binding["terminal_event_id"] in completion_terminal_ids:
                raise StateError(f"{where}.completion_binding terminal_event_id is not unique")
            completion_terminal_ids.add(binding["terminal_event_id"])
            if binding["terminal_path"] in completion_terminal_paths:
                raise StateError(f"{where}.completion_binding terminal_path is not unique")
            completion_terminal_paths.add(binding["terminal_path"])
            if fresh_thread_reason in AUDIT_FRESH_THREAD_REASONS and objective["owner_role"] != "Audit":
                raise StateError(f"{where}.{fresh_thread_reason} requires an Audit owner")
        elif lifecycle == "BLOCKED":
            if "completion_binding" in objective:
                raise StateError(f"{where} blocked objective cannot retain completion_binding")
            if fresh_thread_reason is not None or owner_recovery_evidence_ref is not None:
                raise StateError(f"{where} blocked objective cannot retain owner-transition metadata")
            if candidate_state != "BLOCKED":
                raise StateError(f"{where} blocked lifecycle requires candidate_state BLOCKED")
            blocker = objective.get("blocker")
            if not isinstance(blocker, dict):
                raise StateError(f"{where}.blocker must be an object")
            _require(
                blocker,
                ("kind", "reopening_fact", "observer", "trigger", "next_check_at", "resolution_deadline"),
                f"{where}.blocker",
            )
            if blocker["kind"] not in BLOCKER_KINDS:
                raise StateError(f"{where}.blocker.kind must be one of {sorted(BLOCKER_KINDS)}")
            if not _nonempty(blocker["reopening_fact"]) or not _nonempty(blocker["observer"]):
                raise StateError(f"{where}.blocker reopening_fact and observer must be non-empty")
            has_trigger = _nonempty(blocker["trigger"])
            has_check = _nonempty(blocker["next_check_at"])
            if not has_trigger and not has_check:
                raise StateError(f"{where}.blocker requires trigger or next_check_at")
            if blocker["trigger"] is not None and not has_trigger:
                raise StateError(f"{where}.blocker.trigger must be null or non-empty")
            if blocker["next_check_at"] is not None and not has_check:
                raise StateError(f"{where}.blocker.next_check_at must be null or non-empty")
            deadline = _timestamp(blocker["resolution_deadline"], f"{where}.blocker.resolution_deadline")
            if has_check and _timestamp(blocker["next_check_at"], f"{where}.blocker.next_check_at") > deadline:
                raise StateError(f"{where}.blocker.next_check_at must not exceed resolution_deadline")
            _validate_blocker_attestation(blocker, f"{where}.blocker")
        else:
            if "completion_binding" in objective:
                raise StateError(f"{where} completed objective cannot retain completion_binding")
            if fresh_thread_reason is not None or owner_recovery_evidence_ref is not None:
                raise StateError(f"{where} completed objective cannot retain owner-transition metadata")
            if candidate_state != "CLOSED":
                raise StateError(f"{where} DONE requires candidate_state CLOSED; OPEN/DONE is invalid")

        startup_authority = objective.get("startup_chain_authority")
        if startup_authority is not None:
            delegated_executor = (
                lifecycle == "DELEGATED" and objective.get("owner_role") == "Executor"
            )
            if not delegated_executor and lifecycle != "BLOCKED":
                raise StateError(
                    f"{where}.startup_chain_authority requires a delegated Executor or finite BLOCKED lifecycle"
                )
            _validate_startup_chain_authority(
                startup_authority,
                f"{where}.startup_chain_authority",
            )
        legacy_terminal_schema = objective.get("legacy_terminal_schema")
        if legacy_terminal_schema is not None:
            if legacy_terminal_schema != LEGACY_EXECUTOR_TERMINAL_SCHEMA:
                raise StateError(f"{where}.legacy_terminal_schema is invalid")
            if (
                lifecycle != "DELEGATED"
                or objective.get("owner_role") != "Executor"
                or startup_authority is not None
            ):
                raise StateError(
                    f"{where}.legacy_terminal_schema applies only to one migrated v4 Executor without startup authority"
                )

        gate = objective.get("advisory_blocking_gate")
        if gate is not None:
            if lifecycle != "DELEGATED":
                raise StateError(f"{where}.advisory_blocking_gate requires a delegated objective")
            if not isinstance(gate, dict):
                raise StateError(f"{where}.advisory_blocking_gate must be an object")
            _require(
                gate,
                ("blocking_gate_id", "transition", "target_stage", "authority_ref"),
                f"{where}.advisory_blocking_gate",
            )
            if gate["transition"] not in ADVISORY_GATE_TRANSITIONS:
                raise StateError(f"{where}.advisory_blocking_gate.transition is invalid")
            if not all(_nonempty(gate[key]) for key in ("blocking_gate_id", "target_stage", "authority_ref")):
                raise StateError(f"{where}.advisory_blocking_gate fields must be non-empty")
            if gate["blocking_gate_id"] in objective_gate_ids:
                raise StateError(f"{where}.advisory_blocking_gate is not globally unique")
            objective_gate_ids.add(gate["blocking_gate_id"])

        closure = objective.get("idea_closure")
        if candidate_state != "CLOSED":
            if closure is not None:
                raise StateError(f"{where}.idea_closure is only valid for closed candidates")
            continue
        if lifecycle != "DONE":
            raise StateError(f"{where} closed candidate must have lifecycle DONE")
        if not isinstance(closure, dict):
            raise StateError(f"{where}.idea_closure must be an object for closed candidate")
        _require(
            closure,
            ("basis", "scope", "evidence_ref", "reopening_fact"),
            f"{where}.idea_closure",
        )
        if closure["basis"] not in CLOSURE_BASES:
            raise StateError(f"{where}.idea_closure.basis must be one of {sorted(CLOSURE_BASES)}")
        if not all(_nonempty(closure[key]) for key in ("scope", "evidence_ref", "reopening_fact")):
            raise StateError(f"{where}.idea_closure required fields must be non-empty")
        if closure["basis"] in {"VALID_SCIENTIFIC_NEGATIVE", "PROSPECTIVE_SCOPED_MPE_FAILURE"}:
            _require(
                closure,
                (
                    "independent_audit_terminal_id",
                    "evidence_eligible",
                    "prospective_action_table_pass",
                ),
                f"{where}.idea_closure",
            )
            if not _nonempty(closure["independent_audit_terminal_id"]):
                raise StateError(f"{where}.idea_closure independent Audit must be bound")
            for key in ("evidence_eligible", "prospective_action_table_pass"):
                if closure[key] is not True:
                    raise StateError(f"{where}.idea_closure.{key} must be true")
            if closure["basis"] == "VALID_SCIENTIFIC_NEGATIVE":
                _require(closure, ("power_or_futility_pass",), f"{where}.idea_closure")
                if closure["power_or_futility_pass"] is not True:
                    raise StateError(f"{where}.idea_closure.power_or_futility_pass must be true")
            else:
                _require(
                    closure,
                    (
                        "finite_cell_complete",
                        "preregistered_mpe_failure",
                        "scope_boundary_preserved",
                        "adversarial_review_pass",
                        "powered_negative_claimed",
                    ),
                    f"{where}.idea_closure",
                )
                for key in (
                    "finite_cell_complete",
                    "preregistered_mpe_failure",
                    "scope_boundary_preserved",
                    "adversarial_review_pass",
                ):
                    if closure[key] is not True:
                        raise StateError(f"{where}.idea_closure.{key} must be true")
                if closure["powered_negative_claimed"] is not False:
                    raise StateError(f"{where}.idea_closure.powered_negative_claimed must be false")
        else:
            _require(
                closure,
                ("reason_code", "observer", "trigger", "unavoidable"),
                f"{where}.idea_closure",
            )
            if closure["reason_code"] not in EXTERNAL_IMPOSSIBILITY_REASONS:
                raise StateError(f"{where}.idea_closure.reason_code is not an allowed external impossibility")
            if not _nonempty(closure["observer"]) or not _nonempty(closure["trigger"]):
                raise StateError(f"{where}.idea_closure external observer/trigger must be non-empty")
            if closure["unavoidable"] is not True:
                raise StateError(f"{where}.idea_closure.unavoidable must be true")

    roles = state["managed_roles"]
    if not isinstance(roles, list):
        raise StateError("managed_roles must be a list")
    role_threads: set[str] = set()
    for index, role in enumerate(roles):
        where = f"managed_roles[{index}]"
        if not isinstance(role, dict):
            raise StateError(f"{where} must be an object")
        _require(role, ("thread_id", "role", "title", "state", "pin_required", "cursor"), where)
        if role["thread_id"] in role_threads:
            raise StateError(f"duplicate managed role thread_id {role['thread_id']}")
        role_threads.add(role["thread_id"])
        if not all(_nonempty(role[key]) for key in ("thread_id", "role", "title", "state")):
            raise StateError(f"{where} identity fields must be non-empty")
        if role["role"] not in MANAGED_ROLE_KINDS:
            raise StateError(f"{where}.role must be canonical")
        if role["state"] not in ROLE_STATES:
            raise StateError(f"{where}.state must be canonical")
        if role["pin_required"] is not True:
            raise StateError(f"{where}.pin_required must be true")
        if not TITLE_RE.fullmatch(role["title"]):
            raise StateError(f"{where}.title is not canonical")
        if not role["title"].startswith(f"{role['role']} · "):
            raise StateError(f"{where}.title role does not match role")
        if role["cursor"] is not None and not _nonempty(role["cursor"]):
            raise StateError(f"{where}.cursor must be null or non-empty")

    role_by_thread = {role["thread_id"]: role for role in roles}
    if controller["thread_id"] in role_by_thread:
        raise StateError("Controller thread cannot also be a managed role")
    for index, objective in enumerate(objectives):
        if objective["lifecycle"] != "DELEGATED":
            continue
        where = f"objectives[{index}]"
        role = role_by_thread.get(objective["owner_thread_id"])
        if role is None:
            raise StateError(f"{where}.owner_thread_id is not an active managed role")
        if role["role"] != objective["owner_role"] or role["state"] != objective["owner_state"]:
            raise StateError(f"{where} owner identity/state does not match managed role")

    jobs = state["remote_jobs"]
    if not isinstance(jobs, list):
        raise StateError("remote_jobs must be a list")
    job_ids: set[str] = set()
    for index, job in enumerate(jobs):
        where = f"remote_jobs[{index}]"
        if not isinstance(job, dict):
            raise StateError(f"{where} must be an object")
        _require(
            job,
            (
                "job_id",
                "objective_id",
                "owner_thread_id",
                "host",
                "unit",
                "output_path",
                "expected_files",
                "eta",
                "late_threshold",
                "monitor_state",
                "wake_delivery",
            ),
            where,
        )
        for key in ("job_id", "objective_id", "owner_thread_id", "host", "unit", "output_path", "eta", "late_threshold", "monitor_state"):
            if not _nonempty(job[key]):
                raise StateError(f"{where}.{key} must be non-empty")
        if job["job_id"] in job_ids:
            raise StateError(f"duplicate job_id {job['job_id']}")
        job_ids.add(job["job_id"])
        if job["objective_id"] not in objective_ids:
            raise StateError(f"{where}.objective_id is unknown")
        if job["owner_thread_id"] not in role_threads:
            raise StateError(f"{where}.owner_thread_id is not an active managed role")
        if job["host"] not in REMOTE_HOSTS:
            raise StateError(f"{where}.host is not allowlisted")
        if not UNIT_RE.fullmatch(job["unit"]):
            raise StateError(f"{where}.unit is unsafe")
        output_path = PurePosixPath(job["output_path"])
        if not output_path.is_absolute() or not any(output_path.is_relative_to(root) for root in REMOTE_OUTPUT_ROOTS):
            raise StateError(f"{where}.output_path is outside allowlisted roots")
        if not isinstance(job["expected_files"], list) or not all(_nonempty(item) for item in job["expected_files"]):
            raise StateError(f"{where}.expected_files must contain non-empty names")
        if any(PurePosixPath(item).name != item or item in {".", ".."} for item in job["expected_files"]):
            raise StateError(f"{where}.expected_files must be basenames")
        if job["monitor_state"] not in {"ACTIVE", "TERMINAL_OBSERVED"}:
            raise StateError(f"{where}.monitor_state is invalid")
        wake = job["wake_delivery"]
        if not isinstance(wake, dict):
            raise StateError(f"{where}.wake_delivery must be an object")
        _require(wake, ("state", "claim_token", "observation_id"), f"{where}.wake_delivery")
        if wake["state"] not in WAKE_STATES:
            raise StateError(f"{where}.wake_delivery.state is invalid")
        if wake["state"] == "NONE":
            if wake["claim_token"] is not None or wake["observation_id"] is not None:
                raise StateError(f"{where}.wake_delivery NONE must have null identifiers")
        elif not _nonempty(wake["claim_token"]) or not _nonempty(wake["observation_id"]):
            raise StateError(f"{where}.wake_delivery claimed identifiers must be non-empty")

    events = state["absorbed_terminal_event_ids"]
    if not isinstance(events, list) or not all(_nonempty(item) for item in events):
        raise StateError("absorbed_terminal_event_ids must be a list of non-empty strings")
    if len(events) != len(set(events)):
        raise StateError("absorbed_terminal_event_ids contains duplicates")
    reused_completion_ids = completion_terminal_ids.intersection(events)
    if reused_completion_ids:
        raise StateError(
            "delegated completion terminal_event_id is already absorbed: "
            + ", ".join(sorted(reused_completion_ids))
        )

    pending = state["pending_absorptions"]
    if not isinstance(pending, list):
        raise StateError("pending_absorptions must be a list")
    pending_event_ids: set[str] = set()
    pending_objective_ids: set[str] = set()
    pending_owner_threads: set[str] = set()
    objective_by_id = {objective["objective_id"]: objective for objective in objectives}
    for index, item in enumerate(pending):
        where = f"pending_absorptions[{index}]"
        if not isinstance(item, dict):
            raise StateError(f"{where} must be an object")
        _require(
            item,
            (
                "terminal_event_id",
                "objective_id",
                "owner_thread_id",
                "owner_role",
                "completion_binding_sha256",
                "terminal_path",
                "terminal_bytes",
                "terminal_sha256",
                "terminal_cursor",
                "source_final_turn_id",
                "observation_id",
                "observed_at",
                "verification_state",
                "controller_verification_ref",
            ),
            where,
        )
        for key in (
            "terminal_event_id",
            "objective_id",
            "owner_thread_id",
            "owner_role",
            "observation_id",
        ):
            if not _nonempty(item[key]):
                raise StateError(f"{where}.{key} must be non-empty")
        _sha256(item["completion_binding_sha256"], f"{where}.completion_binding_sha256")
        _terminal_path(item["terminal_path"], f"{where}.terminal_path")
        if not isinstance(item["terminal_bytes"], int) or item["terminal_bytes"] < 1:
            raise StateError(f"{where}.terminal_bytes must be a positive integer")
        _sha256(item["terminal_sha256"], f"{where}.terminal_sha256")
        if item["terminal_cursor"] is not None and not _nonempty(item["terminal_cursor"]):
            raise StateError(f"{where}.terminal_cursor must be null or non-empty")
        if item["source_final_turn_id"] is not None and not _nonempty(item["source_final_turn_id"]):
            raise StateError(f"{where}.source_final_turn_id must be null or non-empty")
        _timestamp(item["observed_at"], f"{where}.observed_at")
        if item["verification_state"] not in PENDING_VERIFICATION_STATES:
            raise StateError(f"{where}.verification_state is invalid")
        if item["verification_state"] == "IDENTITY_VERIFIED":
            if item["controller_verification_ref"] is not None:
                raise StateError(f"{where} identity-only record cannot claim Controller verification")
        elif not _nonempty(item["controller_verification_ref"]):
            raise StateError(f"{where}.controller_verification_ref must be non-empty")
        if item["terminal_event_id"] in events:
            raise StateError(f"{where}.terminal_event_id is already absorbed")
        if item["terminal_event_id"] in pending_event_ids:
            raise StateError(f"duplicate pending terminal_event_id {item['terminal_event_id']}")
        if item["objective_id"] in pending_objective_ids:
            raise StateError(f"duplicate pending objective_id {item['objective_id']}")
        if item["owner_thread_id"] in pending_owner_threads:
            raise StateError(f"duplicate pending owner_thread_id {item['owner_thread_id']}")
        pending_event_ids.add(item["terminal_event_id"])
        pending_objective_ids.add(item["objective_id"])
        pending_owner_threads.add(item["owner_thread_id"])
        objective = objective_by_id.get(item["objective_id"])
        if objective is None or objective["lifecycle"] != "DELEGATED":
            raise StateError(f"{where}.objective_id is not delegated")
        if objective["owner_thread_id"] != item["owner_thread_id"]:
            raise StateError(f"{where}.owner_thread_id does not match objective")
        if objective["owner_role"] != item["owner_role"]:
            raise StateError(f"{where}.owner_role does not match objective")
        if objective["owner_state"] != "TERMINAL_PENDING_ABSORPTION":
            raise StateError(f"{where} objective is not terminal-pending")
        binding = objective["completion_binding"]
        if item["terminal_event_id"] != binding["terminal_event_id"]:
            raise StateError(f"{where}.terminal_event_id does not match completion_binding")
        if item["terminal_path"] != binding["terminal_path"]:
            raise StateError(f"{where}.terminal_path does not match completion_binding")
        if item["completion_binding_sha256"] != completion_binding_sha256(binding):
            raise StateError(f"{where}.completion_binding_sha256 does not match")
        role = role_by_thread.get(item["owner_thread_id"])
        if role is None or role["state"] != "TERMINAL_PENDING_ABSORPTION":
            raise StateError(f"{where} managed role is not terminal-pending")

    for objective in objectives:
        if objective["lifecycle"] != "DELEGATED":
            continue
        is_terminal_pending = objective["owner_state"] == "TERMINAL_PENDING_ABSORPTION"
        has_pending = objective["objective_id"] in pending_objective_ids
        if is_terminal_pending != has_pending:
            raise StateError(
                f"objective {objective['objective_id']} terminal-pending state must match one pending absorption"
            )

    consumed_advisory_scopes = state.get("absorbed_advisory_scopes", [])
    if not isinstance(consumed_advisory_scopes, list):
        raise StateError("absorbed_advisory_scopes must be a list")
    consumed_scope_keys: set[tuple[str, str]] = set()
    for index, consumed in enumerate(consumed_advisory_scopes):
        where = f"absorbed_advisory_scopes[{index}]"
        if not isinstance(consumed, dict):
            raise StateError(f"{where} must be an object")
        _require(consumed, ("candidate_id", "scope_sha256", "local_validation_terminal_event_id"), where)
        if not _nonempty(consumed["candidate_id"]):
            raise StateError(f"{where}.candidate_id must be non-empty")
        if not isinstance(consumed["scope_sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", consumed["scope_sha256"]) is None:
            raise StateError(f"{where}.scope_sha256 must be a lowercase SHA-256")
        if consumed["local_validation_terminal_event_id"] not in events:
            raise StateError(f"{where}.local_validation_terminal_event_id is not absorbed")
        consumed_key = (consumed["candidate_id"], consumed["scope_sha256"])
        if consumed_key in consumed_scope_keys:
            raise StateError(f"{where} duplicates an absorbed advisory scope")
        consumed_scope_keys.add(consumed_key)

    advisories = state["advisory_reads"]
    if not isinstance(advisories, list):
        raise StateError("advisory_reads must be a list")
    advisory_ids: set[str] = set()
    advisory_conversations: set[str] = set()
    advisory_scopes: set[tuple[str, str]] = set()
    advisory_blocking_gates: set[str] = set()
    objective_by_id = {objective["objective_id"]: objective for objective in objectives}
    for index, advisory in enumerate(advisories):
        where = f"advisory_reads[{index}]"
        if not isinstance(advisory, dict):
            raise StateError(f"{where} must be an object")
        _require(
            advisory,
            (
                "advisory_id",
                "objective_id",
                "conversation_thread_id",
                "reader_thread_id",
                "reader_role",
                "submitted_at",
                "submitted_thread_updated_at",
                "not_before",
                "scope_revision",
                "scope_sha256",
                "batch_mode",
                "decision_gate",
                "blocking_gate_id",
                "monitor_state",
                "observed_thread_updated_at",
                "wake_delivery",
            ),
            where,
        )
        for key in (
            "advisory_id",
            "objective_id",
            "conversation_thread_id",
            "reader_thread_id",
            "reader_role",
            "not_before",
            "decision_gate",
            "monitor_state",
        ):
            if not _nonempty(advisory[key]):
                raise StateError(f"{where}.{key} must be non-empty")
        if advisory["advisory_id"] in advisory_ids:
            raise StateError(f"duplicate advisory_id {advisory['advisory_id']}")
        advisory_ids.add(advisory["advisory_id"])
        if advisory["conversation_thread_id"] in advisory_conversations:
            raise StateError(f"{where}.conversation_thread_id already has an in-flight advisory batch")
        advisory_conversations.add(advisory["conversation_thread_id"])
        if advisory["objective_id"] not in objective_ids:
            raise StateError(f"{where}.objective_id is unknown")
        if advisory["reader_role"] not in ADVISORY_READER_ROLES:
            raise StateError(f"{where}.reader_role must be Explorer or Audit")
        if advisory["reader_thread_id"] == controller["thread_id"]:
            raise StateError(f"{where}.reader_thread_id cannot be the Controller")
        if advisory["conversation_thread_id"] == advisory["reader_thread_id"]:
            raise StateError(f"{where} conversation and reader threads must differ")
        batch_mode = advisory["batch_mode"]
        if batch_mode not in ADVISORY_BATCH_MODES:
            raise StateError(f"{where}.batch_mode must be one of {sorted(ADVISORY_BATCH_MODES)}")
        scope_revision = advisory["scope_revision"]
        if isinstance(scope_revision, bool) or not isinstance(scope_revision, int) or scope_revision < 1:
            raise StateError(f"{where}.scope_revision must be a positive integer")
        scope_sha256 = advisory["scope_sha256"]
        if not isinstance(scope_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", scope_sha256) is None:
            raise StateError(f"{where}.scope_sha256 must be a lowercase SHA-256")
        scope_key = (objective_by_id[advisory["objective_id"]]["candidate_id"], scope_sha256)
        if scope_key in advisory_scopes:
            raise StateError(f"{where} duplicates an in-flight advisory scope")
        if scope_key in consumed_scope_keys:
            raise StateError(f"{where} repeats an absorbed advisory scope")
        advisory_scopes.add(scope_key)
        if batch_mode == "NON_BLOCKING":
            if advisory["decision_gate"] != "NON_BLOCKING":
                raise StateError(f"{where}.decision_gate must be NON_BLOCKING")
            if advisory["blocking_gate_id"] is not None:
                raise StateError(f"{where}.blocking_gate_id must be null for NON_BLOCKING")
        else:
            if advisory["decision_gate"] != "BLOCKING_HIGH_RISK":
                raise StateError(f"{where}.decision_gate must be BLOCKING_HIGH_RISK")
            if not _nonempty(advisory["blocking_gate_id"]):
                raise StateError(f"{where}.blocking_gate_id is required for BLOCKING_HIGH_RISK")
            gate_key = advisory["blocking_gate_id"]
            if gate_key in advisory_blocking_gates:
                raise StateError(f"{where} duplicates an active blocking gate")
            advisory_blocking_gates.add(gate_key)
            gate = objective_by_id[advisory["objective_id"]].get("advisory_blocking_gate")
            if not isinstance(gate, dict) or gate.get("blocking_gate_id") != advisory["blocking_gate_id"]:
                raise StateError(f"{where}.blocking_gate_id is not prospectively bound on the objective")
            objective = objective_by_id[advisory["objective_id"]]
            if (
                advisory["reader_thread_id"] != objective.get("owner_thread_id")
                or advisory["reader_role"] != objective.get("owner_role")
            ):
                raise StateError(f"{where} blocking reader must be the current scientific owner")
        if advisory["monitor_state"] not in ADVISORY_MONITOR_STATES:
            raise StateError(f"{where}.monitor_state is invalid")
        baseline = advisory["submitted_thread_updated_at"]
        observed = advisory["observed_thread_updated_at"]
        if advisory["monitor_state"] == "AWAITING_RESPONSE":
            if not _nonempty(advisory["submitted_at"]):
                raise StateError(f"{where}.submitted_at must be non-empty while awaiting response")
            if isinstance(baseline, bool) or not isinstance(baseline, (int, float)) or not math.isfinite(baseline) or baseline < 0:
                raise StateError(f"{where}.submitted_thread_updated_at must be a non-negative finite number")
            if observed is not None:
                raise StateError(f"{where} awaiting response must have null observed_thread_updated_at")
        else:
            if advisory["submitted_at"] is not None and not _nonempty(advisory["submitted_at"]):
                raise StateError(f"{where}.submitted_at must be null or non-empty")
            if baseline is not None and (
                isinstance(baseline, bool)
                or not isinstance(baseline, (int, float))
                or not math.isfinite(baseline)
                or baseline < 0
            ):
                raise StateError(f"{where}.submitted_thread_updated_at must be null or a non-negative finite number")
            if isinstance(observed, bool) or not isinstance(observed, (int, float)) or not math.isfinite(observed):
                raise StateError(f"{where}.observed_thread_updated_at must be a finite number")
            if baseline is not None and observed <= baseline:
                raise StateError(f"{where}.observed_thread_updated_at must exceed submission baseline")
        wake = advisory["wake_delivery"]
        if not isinstance(wake, dict):
            raise StateError(f"{where}.wake_delivery must be an object")
        _require(wake, ("state", "claim_token", "observation_id"), f"{where}.wake_delivery")
        if wake["state"] not in WAKE_STATES:
            raise StateError(f"{where}.wake_delivery.state is invalid")
        if advisory["monitor_state"] == "AWAITING_RESPONSE" and wake["state"] != "NONE":
            raise StateError(f"{where} cannot wake before response observation")
        if wake["state"] == "NONE":
            if wake["claim_token"] is not None or wake["observation_id"] is not None:
                raise StateError(f"{where}.wake_delivery NONE must have null identifiers")
        elif not _nonempty(wake["claim_token"]) or not _nonempty(wake["observation_id"]):
            raise StateError(f"{where}.wake_delivery claimed identifiers must be non-empty")

    return state


def canonical_bytes(state: dict[str, Any]) -> bytes:
    _reject_unicode_surrogates(state, "canonical JSON")
    try:
        document = json.dumps(
            state,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return (document + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise StateError("canonical JSON contains an unsupported or non-finite value") from exc


def checksum_path(state_path: Path) -> Path:
    return state_path.with_name(state_path.name + ".sha256")


@contextmanager
def _state_lock(path: Path, *, exclusive: bool):
    """Serialize one state/checksum pair on its stable parent directory inode."""
    if exclusive:
        path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    directory_fd = os.open(path.parent, flags)
    try:
        fcntl.flock(
            directory_fd,
            fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH,
        )
        yield
    finally:
        fcntl.flock(directory_fd, fcntl.LOCK_UN)
        os.close(directory_fd)


def _read_state_unlocked(path: Path, *, verify_checksum: bool = True) -> dict[str, Any]:
    data = path.read_bytes()
    state = validate_state(json.loads(data))
    if verify_checksum:
        sidecar = checksum_path(path)
        if not sidecar.is_file():
            raise StateError(f"missing checksum sidecar {sidecar}")
        expected = sidecar.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(data).hexdigest()
        if expected != actual:
            raise StateError("state checksum mismatch")
    return state


def read_state(path: Path, *, verify_checksum: bool = True) -> dict[str, Any]:
    with _state_lock(path, exclusive=False):
        return _read_state_unlocked(path, verify_checksum=verify_checksum)


def _atomic_write(path: Path, data: bytes, mode: int = 0o640) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _commit_state_files_unlocked(path: Path, state: dict[str, Any]) -> None:
    """Commit one already-validated state/checksum pair under `_state_lock`."""
    data = canonical_bytes(state)
    digest = hashlib.sha256(data).hexdigest()
    _atomic_write(path, data)
    _atomic_write(
        checksum_path(path),
        f"{digest}  {path.name}\n".encode("utf-8"),
    )


def _objective_guard_signature(objective: dict[str, Any]) -> tuple[Any, ...]:
    return (
        objective.get("candidate_id"),
        objective.get("candidate_state"),
        objective.get("lifecycle"),
        objective.get("owner_thread_id"),
        objective.get("owner_role"),
        objective.get("fresh_thread_reason"),
        objective.get("fresh_thread_evidence_ref"),
        objective.get("owner_recovery_evidence_ref"),
        objective.get("completion_binding"),
        objective.get("startup_chain_authority"),
        objective.get("legacy_terminal_schema"),
        hashlib.sha256(canonical_bytes(objective.get("blocker"))).hexdigest(),
    )


def _validate_advisory_transition(
    previous: dict[str, Any] | None,
    updated: dict[str, Any],
    *,
    operation: str,
) -> None:
    previous_advisories = {} if previous is None else {
        item["advisory_id"]: item for item in previous["advisory_reads"]
    }
    updated_advisories = {item["advisory_id"]: item for item in updated["advisory_reads"]}
    previous_objectives = {} if previous is None else {
        item["objective_id"]: item for item in previous["objectives"]
    }
    immutable_keys = (
        "advisory_id",
        "objective_id",
        "conversation_thread_id",
        "reader_thread_id",
        "reader_role",
        "submitted_at",
        "submitted_thread_updated_at",
        "not_before",
        "scope_revision",
        "scope_sha256",
        "batch_mode",
        "decision_gate",
        "blocking_gate_id",
    )
    for advisory_id, advisory in updated_advisories.items():
        old = previous_advisories.get(advisory_id)
        if old is None:
            if (
                advisory["monitor_state"] != "AWAITING_RESPONSE"
                or advisory["wake_delivery"]["state"] != "NONE"
            ):
                raise StateError("new advisory must start AWAITING_RESPONSE with NONE delivery")
            if advisory["batch_mode"] == "BLOCKING_HIGH_RISK":
                old_objective = previous_objectives.get(advisory["objective_id"])
                gate = None if old_objective is None else old_objective.get("advisory_blocking_gate")
                if not isinstance(gate, dict) or gate.get("blocking_gate_id") != advisory["blocking_gate_id"]:
                    raise StateError("BLOCKING_HIGH_RISK advisory requires a gate bound in the previous state")
            continue
        if any(old.get(key) != advisory.get(key) for key in immutable_keys):
            raise StateError(f"advisory {advisory_id} immutable identity or scope changed")
        old_monitor = old["monitor_state"]
        new_monitor = advisory["monitor_state"]
        old_wake = old["wake_delivery"]["state"]
        new_wake = advisory["wake_delivery"]["state"]
        if old == advisory:
            continue
        if old_monitor == "AWAITING_RESPONSE" and old_wake == "NONE":
            if new_monitor != "RESPONSE_OBSERVED" or new_wake != "CLAIMED":
                raise StateError(f"advisory {advisory_id} response transition is not monotonic")
            if operation != "CLAIM_ADVISORY_WAKE":
                raise StateError(
                    f"advisory {advisory_id} response may be claimed only by claim-advisory-wake"
                )
        elif old_monitor == "RESPONSE_OBSERVED" and old_wake == "CLAIMED":
            if new_monitor != "RESPONSE_OBSERVED" or new_wake != "SENT":
                raise StateError(f"advisory {advisory_id} delivery transition is not monotonic")
            if operation != "COMPLETE_ADVISORY_WAKE":
                raise StateError(
                    f"advisory {advisory_id} delivery may complete only by complete-advisory-wake"
                )
        else:
            raise StateError(f"advisory {advisory_id} cannot be modified after {old_monitor}/{old_wake}")

    removed_ids = set(previous_advisories) - set(updated_advisories)
    if removed_ids and operation not in {
        "ACTIVATE_SUCCESSOR",
        "CLOSE_OBJECTIVE",
        "ABSORB_NONBLOCKING_ADVISORY",
    }:
        raise StateError("advisory entries may be removed only during terminal absorption")

    previous_consumed = [] if previous is None else previous.get("absorbed_advisory_scopes", [])
    updated_consumed = updated.get("absorbed_advisory_scopes", [])
    if updated_consumed[: len(previous_consumed)] != previous_consumed:
        raise StateError("absorbed_advisory_scopes is append-only")
    new_consumed = updated_consumed[len(previous_consumed) :]
    consumed_by_scope = {
        (item["candidate_id"], item["scope_sha256"]): item for item in new_consumed
    }
    if len(consumed_by_scope) != len(new_consumed):
        raise StateError("new absorbed advisory scopes must be unique")
    for advisory_id in removed_ids:
        old = previous_advisories[advisory_id]
        if old["monitor_state"] != "RESPONSE_OBSERVED" or old["wake_delivery"]["state"] != "SENT":
            raise StateError(f"advisory {advisory_id} cannot be removed before observed SENT delivery")
        old_objective = previous_objectives[old["objective_id"]]
        scope_key = (old_objective["candidate_id"], old["scope_sha256"])
        if scope_key not in consumed_by_scope:
            raise StateError(f"advisory {advisory_id} removal lacks local validation absorption")
    if len(new_consumed) != len(removed_ids):
        raise StateError("absorbed advisory scope records must match removed advisories exactly")


def _validate_state_transition(
    previous: dict[str, Any] | None,
    updated: dict[str, Any],
    *,
    operation: str,
) -> None:
    _validate_advisory_transition(previous, updated, operation=operation)
    if previous is None:
        if updated["pending_absorptions"]:
            raise StateError("initial state cannot seed pending absorptions")
        if any(
            objective.get("legacy_terminal_schema") is not None
            for objective in updated["objectives"]
        ):
            raise StateError("initial state cannot seed v4 legacy terminal applicability")
        return
    if previous["controller"] != updated["controller"]:
        raise StateError("Controller identity cannot change through a state data replacement")

    previous_objectives = {item["objective_id"]: item for item in previous["objectives"]}
    updated_objectives = {item["objective_id"]: item for item in updated["objectives"]}
    if operation == "GENERIC":
        if set(previous_objectives) != set(updated_objectives):
            raise StateError("generic replacement cannot add, remove, or rename objectives")
        for objective_id, old in previous_objectives.items():
            new = updated_objectives[objective_id]
            if _objective_guard_signature(old) != _objective_guard_signature(new):
                raise StateError(f"generic replacement cannot change owner/lifecycle for {objective_id}")
            old_gate = old.get("advisory_blocking_gate")
            new_gate = new.get("advisory_blocking_gate")
            if old_gate is not None and old_gate != new_gate:
                raise StateError(f"generic replacement cannot change or remove blocking gate for {objective_id}")
            if old_gate is None and new_gate is not None:
                if any(
                    advisory["objective_id"] == objective_id
                    and advisory["batch_mode"] == "BLOCKING_HIGH_RISK"
                    for advisory in updated["advisory_reads"]
                ):
                    raise StateError("blocking gate and advisory must be created in separate revisions")
        previous_roles = {(item["thread_id"], item["role"]) for item in previous["managed_roles"]}
        updated_roles = {(item["thread_id"], item["role"]) for item in updated["managed_roles"]}
        if previous_roles != updated_roles:
            raise StateError("generic replacement cannot change managed owner identities")
        if previous["absorbed_terminal_event_ids"] != updated["absorbed_terminal_event_ids"]:
            raise StateError("generic replacement cannot absorb terminal events")
    elif operation == "RECORD_STARTUP_ATTEMPT":
        if set(previous_objectives) != set(updated_objectives):
            raise StateError(
                "record-startup-attempt cannot add, remove, or rename objectives"
            )
        changed_ids = [
            objective_id
            for objective_id in previous_objectives
            if previous_objectives[objective_id] != updated_objectives[objective_id]
        ]
        if len(changed_ids) != 1:
            raise StateError(
                "record-startup-attempt must change exactly one objective authority"
            )
        objective_id = changed_ids[0]
        old = previous_objectives[objective_id]
        new = updated_objectives[objective_id]
        old_without_authority = {
            key: value for key, value in old.items() if key != "startup_chain_authority"
        }
        new_without_authority = {
            key: value for key, value in new.items() if key != "startup_chain_authority"
        }
        if old_without_authority != new_without_authority:
            raise StateError(
                "record-startup-attempt may change only startup_chain_authority"
            )
        if (
            old.get("lifecycle") != "DELEGATED"
            or old.get("candidate_state") != "OPEN"
            or old.get("owner_role") != "Executor"
            or old.get("owner_state") not in {"ACTIVE", "WAITING_EXTERNAL"}
            or old.get("scientific_outcome") != "UNOBSERVED"
        ):
            raise StateError(
                "record-startup-attempt requires one outcome-blind delegated Executor"
            )
        previous_authority = _validate_startup_chain_authority(
            old.get("startup_chain_authority"),
            "existing_startup_chain_authority",
        )
        updated_authority = _validate_startup_chain_authority(
            new.get("startup_chain_authority"),
            "updated_startup_chain_authority",
        )
        expected = _transition_startup_chain_authority(
            previous_authority,
            updated_authority,
            new_owner_role="Executor",
        )
        if expected != updated_authority:
            raise StateError("record-startup-attempt authority transition is invalid")
        old_records = previous_authority["prior_attempt_records"]
        new_records = updated_authority["prior_attempt_records"]
        if len(new_records) != len(old_records) + 1:
            raise StateError(
                "record-startup-attempt must append exactly one consecutive record"
            )
        if new_records[:-1] != old_records:
            raise StateError(
                "record-startup-attempt must preserve the existing record prefix"
            )
        for other_id, previous_objective in previous_objectives.items():
            if other_id != objective_id and updated_objectives[other_id] != previous_objective:
                raise StateError(
                    f"record-startup-attempt cannot modify objective {other_id}"
                )
        for key in (
            "managed_roles",
            "remote_jobs",
            "advisory_reads",
            "absorbed_advisory_scopes",
            "pending_absorptions",
            "absorbed_terminal_event_ids",
        ):
            if previous.get(key, []) != updated.get(key, []):
                raise StateError(f"record-startup-attempt cannot change {key}")
    elif operation == "REBUILD_ADD_OBJECTIVE":
        previous_ids = set(previous_objectives)
        updated_ids = set(updated_objectives)
        added_ids = updated_ids - previous_ids
        if previous_ids - updated_ids or len(added_ids) != 1:
            raise StateError(
                "rebuild-add-objective must preserve every existing objective and add exactly one"
            )
        for objective_id, old in previous_objectives.items():
            if updated_objectives[objective_id] != old:
                raise StateError(
                    f"rebuild-add-objective cannot modify existing objective {objective_id}"
                )
        added_objective = updated_objectives[next(iter(added_ids))]
        if (
            added_objective["lifecycle"] != "DELEGATED"
            or added_objective["candidate_state"] != "OPEN"
            or added_objective["owner_state"] != "ACTIVE"
            or not _nonempty(added_objective.get("owner_recovery_evidence_ref"))
        ):
            raise StateError(
                "rebuild-add-objective may add only one ACTIVE DELEGATED objective with recovery evidence"
            )

        previous_roles = {item["thread_id"]: item for item in previous["managed_roles"]}
        updated_roles = {item["thread_id"]: item for item in updated["managed_roles"]}
        added_role_threads = set(updated_roles) - set(previous_roles)
        if set(previous_roles) - set(updated_roles) or len(added_role_threads) != 1:
            raise StateError(
                "rebuild-add-objective must preserve every existing role and add exactly one"
            )
        for thread_id, old in previous_roles.items():
            if updated_roles[thread_id] != old:
                raise StateError(
                    f"rebuild-add-objective cannot modify existing managed role {thread_id}"
                )
        added_role = updated_roles[next(iter(added_role_threads))]
        if (
            added_role["thread_id"] != added_objective["owner_thread_id"]
            or added_role["role"] != added_objective["owner_role"]
            or added_role["state"] != "ACTIVE"
        ):
            raise StateError("rebuild-add-objective role does not match the added objective")

        for key in (
            "remote_jobs",
            "advisory_reads",
            "absorbed_advisory_scopes",
            "pending_absorptions",
            "absorbed_terminal_event_ids",
        ):
            if previous.get(key, []) != updated.get(key, []):
                raise StateError(f"rebuild-add-objective cannot change {key}")
    pending_operations = {
        "OBSERVE_TERMINAL",
        "VERIFY_PENDING_TERMINAL",
        "ACTIVATE_SUCCESSOR",
        "CLOSE_OBJECTIVE",
        "ABSORB_AND_BLOCK",
    }
    if previous["pending_absorptions"] != updated["pending_absorptions"]:
        if operation not in pending_operations:
            raise StateError("pending_absorptions may change only through dedicated terminal transactions")
def write_state(
    path: Path,
    state: dict[str, Any],
    expected_revision: int,
    *,
    operation: str = "GENERIC",
) -> dict[str, Any]:
    with _state_lock(path, exclusive=True):
        current_revision = -1
        current_state: dict[str, Any] | None = None
        if path.exists():
            current_state = _read_state_unlocked(path)
            current_revision = current_state["revision"]
        if current_revision != expected_revision:
            raise StateError(
                f"revision conflict: expected {expected_revision}, found {current_revision}"
            )
        updated = copy.deepcopy(state)
        updated["schema_version"] = SCHEMA_VERSION
        updated["revision"] = expected_revision + 1
        updated["updated_at"] = datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        validate_state(updated)
        _validate_state_transition(current_state, updated, operation=operation)
        _commit_state_files_unlocked(path, updated)
        return updated


def _read_legacy_unlocked(path: Path, version: int) -> dict[str, Any]:
    data = path.read_bytes()
    sidecar = checksum_path(path)
    if not sidecar.is_file():
        raise StateError(f"missing checksum sidecar {sidecar}")
    expected = sidecar.read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(data).hexdigest() != expected:
        raise StateError("state checksum mismatch")
    legacy = json.loads(data)
    if not isinstance(legacy, dict) or legacy.get("schema_version") != version:
        raise StateError(f"legacy state must use schema_version {version}")
    if version == 2 and "advisory_reads" in legacy:
        raise StateError("legacy state must not contain advisory_reads")
    return legacy


def _read_legacy(path: Path, version: int) -> dict[str, Any]:
    with _state_lock(path, exclusive=False):
        return _read_legacy_unlocked(path, version)


def find_job(state: dict[str, Any], job_id: str) -> dict[str, Any]:
    for job in state["remote_jobs"]:
        if job["job_id"] == job_id:
            return job
    raise StateError(f"unknown job_id {job_id}")


def find_advisory(state: dict[str, Any], advisory_id: str) -> dict[str, Any]:
    for advisory in state["advisory_reads"]:
        if advisory["advisory_id"] == advisory_id:
            return advisory
    raise StateError(f"unknown advisory_id {advisory_id}")


def find_objective(state: dict[str, Any], objective_id: str) -> dict[str, Any]:
    for objective in state["objectives"]:
        if objective["objective_id"] == objective_id:
            return objective
    raise StateError(f"unknown objective_id {objective_id}")


def find_pending_terminal(state: dict[str, Any], terminal_event_id: str) -> dict[str, Any]:
    for pending in state["pending_absorptions"]:
        if pending["terminal_event_id"] == terminal_event_id:
            return pending
    raise StateError(f"unknown pending terminal_event_id {terminal_event_id}")


def _terminal_pending_title(title: str) -> str:
    parts = title.rsplit(" · ", 1)
    if len(parts) != 2:
        raise StateError("managed role title is not canonical")
    return f"{parts[0]} · TERMINAL_PENDING_ABSORPTION"


def _require_absorbable_pending(
    state: dict[str, Any],
    *,
    objective: dict[str, Any],
    terminal_event_id: str,
    old_owner_thread_id: str,
) -> dict[str, Any]:
    pending = find_pending_terminal(state, terminal_event_id)
    if pending["objective_id"] != objective["objective_id"]:
        raise StateError("pending terminal objective does not match")
    if pending["owner_thread_id"] != old_owner_thread_id:
        raise StateError("pending terminal owner does not match")
    if pending["verification_state"] != "CONTROLLER_VERIFIED":
        raise StateError("pending terminal is not Controller-verified")
    if pending["completion_binding_sha256"] != completion_binding_sha256(
        objective["completion_binding"]
    ):
        raise StateError("pending terminal completion binding does not match")
    size, digest = _bound_terminal_envelope(
        Path(pending["terminal_path"]),
        objective["completion_binding"],
        objective.get("startup_chain_authority"),
        require_startup_authority_mirror=_requires_startup_authority_mirror(objective),
    )
    if size != pending["terminal_bytes"] or digest != pending["terminal_sha256"]:
        raise StateError("pending terminal immutable envelope changed")
    return pending


def cmd_replace(args: argparse.Namespace) -> None:
    candidate = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = write_state(Path(args.state), candidate, args.expected_revision)
    print(json.dumps({"status": "PASS", "revision": result["revision"]}, sort_keys=True))


def cmd_rebuild_add_objective(args: argparse.Namespace) -> None:
    """CAS-add one omitted prebound objective from immutable runtime facts."""
    path = Path(args.state)
    state = read_state(path)
    if state["revision"] != args.expected_revision:
        raise StateError(
            f"revision conflict: expected {args.expected_revision}, found {state['revision']}"
        )
    if args.owner_role not in MANAGED_ROLE_KINDS:
        raise StateError("owner_role is invalid")
    if not TITLE_RE.fullmatch(args.owner_title):
        raise StateError("owner_title is not canonical")
    if not args.owner_title.startswith(f"{args.owner_role} · "):
        raise StateError("owner_title role mismatch")
    if not args.owner_title.endswith(" · ACTIVE"):
        raise StateError("reconstructed owner_title must be ACTIVE")
    for key in (
        "objective_id",
        "candidate_id",
        "stage",
        "scientific_outcome",
        "next_action",
        "owner_thread_id",
        "recovery_evidence_ref",
    ):
        if not _nonempty(getattr(args, key)):
            raise StateError(f"{key} must be non-empty")
    if args.owner_thread_id == state["controller"]["thread_id"]:
        raise StateError("Controller thread cannot be a managed owner")
    if args.cursor is not None and not _nonempty(args.cursor):
        raise StateError("cursor must be null or non-empty")
    if not isinstance(args.terminal_bytes, int) or args.terminal_bytes < 1:
        raise StateError("terminal_bytes must be a positive integer")
    expected_terminal_sha256 = _sha256(args.terminal_sha256, "terminal_sha256")

    completion_binding = json.loads(args.completion_binding_json)
    _validate_completion_binding(completion_binding, "completion_binding")
    if completion_binding["terminal_event_id"] in state["absorbed_terminal_event_ids"]:
        raise StateError("terminal_event_id is already absorbed")
    if any(
        pending["terminal_event_id"] == completion_binding["terminal_event_id"]
        for pending in state["pending_absorptions"]
    ):
        raise StateError("terminal_event_id is already pending absorption")
    terminal_data, terminal_body = _read_bound_terminal(
        Path(completion_binding["terminal_path"]), completion_binding
    )
    terminal_bytes = len(terminal_data)
    terminal_sha256 = hashlib.sha256(terminal_data).hexdigest()
    if (
        terminal_bytes != args.terminal_bytes
        or terminal_sha256 != expected_terminal_sha256
    ):
        raise StateError("immutable terminal envelope does not match reconstruction facts")

    objective = {
        "objective_id": args.objective_id,
        "candidate_id": args.candidate_id,
        "candidate_state": "OPEN",
        "stage": args.stage,
        "scientific_outcome": args.scientific_outcome,
        "lifecycle": "DELEGATED",
        "next_action": args.next_action,
        "owner_thread_id": args.owner_thread_id,
        "owner_role": args.owner_role,
        "owner_state": "ACTIVE",
        "owner_recovery_evidence_ref": args.recovery_evidence_ref,
        "completion_binding": completion_binding,
    }
    terminal_has_startup_authority = "startup_chain_authority" in terminal_body
    recovered_startup_authority = terminal_body.get("startup_chain_authority")
    if args.owner_role == "Executor":
        if not terminal_has_startup_authority:
            raise StateError(
                "reconstructed Executor terminal must explicitly bind startup_chain_authority"
            )
        if recovered_startup_authority is not None:
            recovered_startup_authority = _validate_startup_chain_authority(
                recovered_startup_authority,
                "terminal.startup_chain_authority",
            )
            _resolve_startup_chain_authority(recovered_startup_authority)
            objective["startup_chain_authority"] = copy.deepcopy(
                recovered_startup_authority
            )
    elif terminal_has_startup_authority and recovered_startup_authority is not None:
        raise StateError(
            "only a reconstructed Executor may bind startup_chain_authority"
        )
    role = {
        "thread_id": args.owner_thread_id,
        "role": args.owner_role,
        "title": args.owner_title,
        "state": "ACTIVE",
        "pin_required": True,
        "cursor": args.cursor,
    }

    existing = next(
        (item for item in state["objectives"] if item["objective_id"] == args.objective_id),
        None,
    )
    if existing is not None:
        existing_role = next(
            (
                item
                for item in state["managed_roles"]
                if item["thread_id"] == args.owner_thread_id
            ),
            None,
        )
        if existing == objective and existing_role == role:
            print(
                json.dumps(
                    {
                        "status": "ALREADY_APPLIED",
                        "revision": state["revision"],
                        "objective_id": args.objective_id,
                        "terminal_event_id": completion_binding["terminal_event_id"],
                    },
                    sort_keys=True,
                )
            )
            return
        raise StateError("objective_id already exists with different reconstruction facts")

    state["objectives"].append(objective)
    state["managed_roles"].append(role)
    result = write_state(
        path,
        state,
        args.expected_revision,
        operation="REBUILD_ADD_OBJECTIVE",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "revision": result["revision"],
                "objective_id": args.objective_id,
                "terminal_event_id": completion_binding["terminal_event_id"],
            },
            sort_keys=True,
        )
    )


def _validate_migration_candidate(legacy: dict[str, Any], updated: dict[str, Any], *, version: int) -> None:
    if legacy["controller"] != updated["controller"]:
        raise StateError("migration cannot change Controller identity")
    legacy_objectives = {item["objective_id"]: item for item in legacy["objectives"]}
    updated_objectives = {item["objective_id"]: item for item in updated["objectives"]}
    if set(legacy_objectives) != set(updated_objectives):
        raise StateError("migration cannot add, remove, or rename objectives")
    for objective_id, old in legacy_objectives.items():
        if _objective_guard_signature(old) != _objective_guard_signature(updated_objectives[objective_id]):
            raise StateError(f"migration cannot change owner/lifecycle for {objective_id}")
    legacy_roles = {(item["thread_id"], item["role"]) for item in legacy["managed_roles"]}
    updated_roles = {(item["thread_id"], item["role"]) for item in updated["managed_roles"]}
    if legacy_roles != updated_roles:
        raise StateError("migration cannot change managed owner identities")
    legacy_advisories = [] if version == 2 else legacy.get("advisory_reads", [])
    if legacy_advisories:
        raise StateError("legacy advisory obligations cannot be migrated into explicit batch authority")
    updated_advisories = updated["advisory_reads"]
    if {item["advisory_id"] for item in legacy_advisories} != {
        item["advisory_id"] for item in updated_advisories
    }:
        raise StateError("migration cannot add or remove advisory obligations")
    immutable_keys = (
        "advisory_id",
        "objective_id",
        "conversation_thread_id",
        "reader_thread_id",
        "reader_role",
        "submitted_at",
        "submitted_thread_updated_at",
        "not_before",
        "monitor_state",
        "observed_thread_updated_at",
        "wake_delivery",
    )
    updated_by_id = {item["advisory_id"]: item for item in updated_advisories}
    for old in legacy_advisories:
        new = updated_by_id[old["advisory_id"]]
        if any(old.get(key) != new.get(key) for key in immutable_keys):
            raise StateError(f"migration changed advisory identity {old['advisory_id']}")


def cmd_migrate_v2(args: argparse.Namespace) -> None:
    path = Path(args.state)
    legacy = _read_legacy(path, 2)
    if legacy["revision"] != args.expected_revision:
        raise StateError(f"revision conflict: expected {args.expected_revision}, found {legacy['revision']}")
    candidate = json.loads(Path(args.input).read_text(encoding="utf-8"))
    updated = copy.deepcopy(candidate)
    updated["schema_version"] = SCHEMA_VERSION
    updated["revision"] = args.expected_revision + 1
    updated["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    validate_state(updated)
    _validate_migration_candidate(legacy, updated, version=2)
    with _state_lock(path, exclusive=True):
        locked_legacy = _read_legacy_unlocked(path, 2)
        if locked_legacy["revision"] != args.expected_revision:
            raise StateError(
                f"revision conflict: expected {args.expected_revision}, found {locked_legacy['revision']}"
            )
        _validate_migration_candidate(locked_legacy, updated, version=2)
        _commit_state_files_unlocked(path, updated)
    print(json.dumps({"status": "PASS", "revision": updated["revision"], "migrated_from": 2}, sort_keys=True))


def cmd_migrate_v3(args: argparse.Namespace) -> None:
    path = Path(args.state)
    legacy = _read_legacy(path, 3)
    if legacy["revision"] != args.expected_revision:
        raise StateError(f"revision conflict: expected {args.expected_revision}, found {legacy['revision']}")
    candidate = json.loads(Path(args.input).read_text(encoding="utf-8"))
    updated = copy.deepcopy(candidate)
    updated["schema_version"] = SCHEMA_VERSION
    updated["revision"] = args.expected_revision + 1
    updated["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    validate_state(updated)
    _validate_migration_candidate(legacy, updated, version=3)
    with _state_lock(path, exclusive=True):
        locked_legacy = _read_legacy_unlocked(path, 3)
        if locked_legacy["revision"] != args.expected_revision:
            raise StateError(
                f"revision conflict: expected {args.expected_revision}, found {locked_legacy['revision']}"
            )
        _validate_migration_candidate(locked_legacy, updated, version=3)
        _commit_state_files_unlocked(path, updated)
    print(json.dumps({"status": "PASS", "revision": updated["revision"], "migrated_from": 3}, sort_keys=True))


def cmd_migrate_v4_native_heartbeat(args: argparse.Namespace) -> None:
    """One-shot v4 to v5 migration for native Controller-heartbeat recovery."""
    path = Path(args.state)
    legacy = _read_legacy(path, 4)
    if legacy["revision"] != args.expected_revision:
        raise StateError(
            f"revision conflict: expected {args.expected_revision}, found {legacy['revision']}"
        )
    supplied = json.loads(Path(args.bindings_json).read_text(encoding="utf-8"))
    if not isinstance(supplied, list):
        raise StateError("bindings_json must be a list")
    by_objective: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(supplied):
        where = f"bindings[{index}]"
        if not isinstance(record, dict):
            raise StateError(f"{where} must be an object")
        _require(record, ("objective_id", "completion_binding", "terminal_observation"), where)
        if not _nonempty(record["objective_id"]) or record["objective_id"] in by_objective:
            raise StateError(f"{where}.objective_id is invalid or duplicate")
        _validate_completion_binding(record["completion_binding"], f"{where}.completion_binding")
        observation = record["terminal_observation"]
        if observation is not None:
            if not isinstance(observation, dict):
                raise StateError(f"{where}.terminal_observation must be null or an object")
            _require(
                observation,
                ("terminal_cursor", "source_final_turn_id", "observation_id"),
                f"{where}.terminal_observation",
            )
            if observation["terminal_cursor"] is not None and not _nonempty(
                observation["terminal_cursor"]
            ):
                raise StateError(f"{where}.terminal_observation.terminal_cursor is invalid")
            if observation["source_final_turn_id"] is not None and not _nonempty(
                observation["source_final_turn_id"]
            ):
                raise StateError(f"{where}.terminal_observation.source_final_turn_id is invalid")
            if not _nonempty(observation["observation_id"]):
                raise StateError(f"{where}.terminal_observation.observation_id must be non-empty")
        by_objective[record["objective_id"]] = record

    updated = copy.deepcopy(legacy)
    delegated = {
        objective["objective_id"]: objective
        for objective in updated["objectives"]
        if objective["lifecycle"] == "DELEGATED"
    }
    if set(by_objective) != set(delegated):
        raise StateError("bindings_json must bind every and only delegated objective")
    roles_by_thread = {role["thread_id"]: role for role in updated["managed_roles"]}
    pending: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for objective_id, objective in delegated.items():
        record = by_objective[objective_id]
        binding = copy.deepcopy(record["completion_binding"])
        objective["completion_binding"] = binding
        if (
            objective.get("owner_role") == "Executor"
            and objective.get("startup_chain_authority") is None
        ):
            objective["legacy_terminal_schema"] = LEGACY_EXECUTOR_TERMINAL_SCHEMA
        observation = record["terminal_observation"]
        if observation is None:
            continue
        terminal_data, _ = _read_bound_terminal(
            Path(binding["terminal_path"]),
            binding,
            objective.get("startup_chain_authority"),
        )
        size = len(terminal_data)
        digest = hashlib.sha256(terminal_data).hexdigest()
        objective["owner_state"] = "TERMINAL_PENDING_ABSORPTION"
        role = roles_by_thread.get(objective["owner_thread_id"])
        if role is None:
            raise StateError(f"migration objective {objective_id} owner role is missing")
        role["state"] = "TERMINAL_PENDING_ABSORPTION"
        role["title"] = _terminal_pending_title(role["title"])
        pending.append(
            {
                "terminal_event_id": binding["terminal_event_id"],
                "objective_id": objective_id,
                "owner_thread_id": objective["owner_thread_id"],
                "owner_role": objective["owner_role"],
                "completion_binding_sha256": completion_binding_sha256(binding),
                "terminal_path": binding["terminal_path"],
                "terminal_bytes": size,
                "terminal_sha256": digest,
                "terminal_cursor": observation["terminal_cursor"],
                "source_final_turn_id": observation["source_final_turn_id"],
                "observation_id": observation["observation_id"],
                "observed_at": now,
                "verification_state": "IDENTITY_VERIFIED",
                "controller_verification_ref": None,
            }
        )
    updated["pending_absorptions"] = pending
    updated["schema_version"] = SCHEMA_VERSION
    updated["revision"] = args.expected_revision + 1
    updated["updated_at"] = now
    validate_state(updated)
    if updated["controller"] != legacy["controller"]:
        raise StateError("migration cannot change Controller identity")
    for key in (
        "remote_jobs",
        "advisory_reads",
        "absorbed_terminal_event_ids",
        "absorbed_advisory_scopes",
    ):
        if updated.get(key, []) != legacy.get(key, []):
            raise StateError(f"migration cannot change {key}")
    with _state_lock(path, exclusive=True):
        locked_legacy = _read_legacy_unlocked(path, 4)
        if locked_legacy["revision"] != args.expected_revision:
            raise StateError(
                f"revision conflict: expected {args.expected_revision}, found {locked_legacy['revision']}"
            )
        if locked_legacy != legacy:
            raise StateError("legacy state changed before v4 migration commit")
        _commit_state_files_unlocked(path, updated)
    print(
        json.dumps(
            {
                "status": "PASS",
                "revision": updated["revision"],
                "migrated_from": 4,
                "pending_absorptions": len(pending),
            },
            sort_keys=True,
        )
    )


def cmd_reconcile_open(args: argparse.Namespace) -> None:
    """Atomically reopen finite BLOCKED objectives and bind their activated owners."""
    path = Path(args.state)
    legacy_preimage: dict[str, Any] | None = None
    try:
        state = read_state(path)
        migrated_from = None
    except StateError as exc:
        if "schema_version must be 5" not in str(exc):
            raise
        state = _read_legacy(path, 3)
        legacy_preimage = copy.deepcopy(state)
        migrated_from = 3
    if state["revision"] != args.expected_revision:
        raise StateError(f"revision conflict: expected {args.expected_revision}, found {state['revision']}")

    transitions = json.loads(args.transitions_json)
    if not isinstance(transitions, list) or not transitions:
        raise StateError("transitions must be a non-empty list")
    seen_objectives: set[str] = set()
    seen_threads: set[str] = set()
    roles_by_thread = {role["thread_id"]: role for role in state["managed_roles"]}
    for index, transition in enumerate(transitions):
        where = f"transitions[{index}]"
        if not isinstance(transition, dict):
            raise StateError(f"{where} must be an object")
        _require(
            transition,
            (
                "objective_id",
                "new_objective_id",
                "stage",
                "scientific_outcome",
                "next_action",
                "owner_thread_id",
                "owner_role",
                "owner_state",
                "owner_title",
                "cursor",
                "recovery_evidence_ref",
                "completion_binding",
            ),
            where,
        )
        if transition["objective_id"] in seen_objectives:
            raise StateError(f"{where}.objective_id is duplicate")
        if transition["owner_thread_id"] in seen_threads:
            raise StateError(f"{where}.owner_thread_id is duplicate")
        seen_objectives.add(transition["objective_id"])
        seen_threads.add(transition["owner_thread_id"])
        objective = find_objective(state, transition["objective_id"])
        if objective["candidate_state"] == "CLOSED":
            raise StateError(f"{where} cannot reactivate a CLOSED candidate")
        if objective["lifecycle"] != "BLOCKED":
            raise StateError(f"{where} reconcile-open may only reopen a BLOCKED objective")
        startup_authority = objective.get("startup_chain_authority")
        if startup_authority is not None:
            if transition["owner_role"] != "Executor":
                raise StateError(
                    f"{where} startup-chain recovery must reopen to an Executor"
                )
            _resolve_startup_chain_authority(
                _validate_startup_chain_authority(
                    startup_authority,
                    f"{where}.startup_chain_authority",
                )
            )
        if transition["owner_role"] not in MANAGED_ROLE_KINDS:
            raise StateError(f"{where}.owner_role is invalid")
        if transition["owner_state"] not in ROLE_STATES:
            raise StateError(f"{where}.owner_state is invalid")
        if not TITLE_RE.fullmatch(transition["owner_title"]):
            raise StateError(f"{where}.owner_title is not canonical")
        if not transition["owner_title"].startswith(f"{transition['owner_role']} · "):
            raise StateError(f"{where}.owner_title role mismatch")
        for key in (
            "new_objective_id",
            "stage",
            "scientific_outcome",
            "next_action",
            "owner_thread_id",
            "recovery_evidence_ref",
        ):
            if not _nonempty(transition[key]):
                raise StateError(f"{where}.{key} must be non-empty")
        if transition["cursor"] is not None and not _nonempty(transition["cursor"]):
            raise StateError(f"{where}.cursor must be null or non-empty")
        _validate_completion_binding(
            transition["completion_binding"], f"{where}.completion_binding"
        )
        if transition["new_objective_id"] != transition["objective_id"] and any(
            other is not objective and other["objective_id"] == transition["new_objective_id"]
            for other in state["objectives"]
        ):
            raise StateError(f"{where}.new_objective_id already exists")
        objective.update(
            {
                "objective_id": transition["new_objective_id"],
                "candidate_state": "OPEN",
                "stage": transition["stage"],
                "scientific_outcome": transition["scientific_outcome"],
                "lifecycle": "DELEGATED",
                "next_action": transition["next_action"],
                "owner_thread_id": transition["owner_thread_id"],
                "owner_role": transition["owner_role"],
                "owner_state": transition["owner_state"],
                "owner_recovery_evidence_ref": transition["recovery_evidence_ref"],
                "completion_binding": copy.deepcopy(transition["completion_binding"]),
            }
        )
        for stale_key in (
            "blocker",
            "reopening_fact",
            "idea_closure",
            "fresh_thread_reason",
            "fresh_thread_evidence_ref",
            "advisory_blocking_gate",
        ):
            objective.pop(stale_key, None)
        if transition["owner_thread_id"] == state["controller"]["thread_id"]:
            raise StateError(f"{where}.owner_thread_id cannot be the Controller")
        roles_by_thread[transition["owner_thread_id"]] = {
            "thread_id": transition["owner_thread_id"],
            "role": transition["owner_role"],
            "title": transition["owner_title"],
            "state": transition["owner_state"],
            "pin_required": True,
            "cursor": transition["cursor"],
        }

    delegated_threads = {
        objective["owner_thread_id"]
        for objective in state["objectives"]
        if objective["lifecycle"] == "DELEGATED"
    }
    state["managed_roles"] = [roles_by_thread[thread_id] for thread_id in sorted(delegated_threads)]

    remote_jobs = json.loads(args.remote_jobs_json)
    if not isinstance(remote_jobs, list):
        raise StateError("remote_jobs_json must be a list")
    state["remote_jobs"] = remote_jobs
    if migrated_from is None:
        state = write_state(path, state, args.expected_revision, operation="RECONCILE_OPEN")
    else:
        if state.get("advisory_reads"):
            raise StateError("v3 reconcile-open requires advisory obligations to be cleared or explicitly migrated first")
        state["schema_version"] = SCHEMA_VERSION
        state["pending_absorptions"] = []
        state["revision"] = args.expected_revision + 1
        state["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        validate_state(state)
        with _state_lock(path, exclusive=True):
            locked_legacy = _read_legacy_unlocked(path, 3)
            if locked_legacy["revision"] != args.expected_revision:
                raise StateError(
                    f"revision conflict: expected {args.expected_revision}, found {locked_legacy['revision']}"
                )
            if locked_legacy != legacy_preimage:
                raise StateError("legacy state changed before reconcile-open commit")
            _commit_state_files_unlocked(path, state)
    print(
        json.dumps(
            {
                "status": "PASS",
                "revision": state["revision"],
                "reactivated": len(transitions),
                "migrated_from": migrated_from,
            },
            sort_keys=True,
        )
    )


def cmd_validate(args: argparse.Namespace) -> None:
    state = read_state(Path(args.state))
    print(json.dumps({"status": "PASS", "revision": state["revision"]}, sort_keys=True))


def active_state_projection(state: dict[str, Any]) -> dict[str, Any]:
    """Return the routine Controller view without replay-only history bodies."""
    active_objectives = [
        copy.deepcopy(item)
        for item in state["objectives"]
        if item["lifecycle"] != "DONE"
    ]
    closed_objective_ids = [
        item["objective_id"]
        for item in state["objectives"]
        if item["lifecycle"] == "DONE"
    ]
    absorbed_events = state["absorbed_terminal_event_ids"]
    absorbed_advisories = state["absorbed_advisory_scopes"]
    return {
        "projection": "active",
        "schema_version": state["schema_version"],
        "revision": state["revision"],
        "updated_at": state["updated_at"],
        "canonical_state_sha256": hashlib.sha256(canonical_bytes(state)).hexdigest(),
        "controller": copy.deepcopy(state["controller"]),
        "objectives": active_objectives,
        "managed_roles": copy.deepcopy(state["managed_roles"]),
        "remote_jobs": copy.deepcopy(state["remote_jobs"]),
        "advisory_reads": copy.deepcopy(state["advisory_reads"]),
        "pending_absorptions": copy.deepcopy(state["pending_absorptions"]),
        "history_summary": {
            "closed_objectives": {
                "count": len(closed_objective_ids),
                "ids_sha256": hashlib.sha256(
                    canonical_bytes(closed_objective_ids)
                ).hexdigest(),
            },
            "absorbed_terminal_event_ids": {
                "count": len(absorbed_events),
                "sha256": hashlib.sha256(canonical_bytes(absorbed_events)).hexdigest(),
            },
            "absorbed_advisory_scopes": {
                "count": len(absorbed_advisories),
                "sha256": hashlib.sha256(
                    canonical_bytes(absorbed_advisories)
                ).hexdigest(),
            },
        },
    }


def cmd_show(args: argparse.Namespace) -> None:
    state = read_state(Path(args.state))
    output = state if args.projection == "full" else active_state_projection(state)
    print(canonical_bytes(output).decode("utf-8"), end="")


def _validate_committed_successor(
    state: dict[str, Any],
    *,
    minimum_revision: int,
    objective_id: str,
    owner_thread_id: str,
    owner_role: str,
    completion_binding: dict[str, Any],
    absorbed_terminal_event_id: str,
    expected_remote_job: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return the activated objective, or None while the Controller CAS is pending."""
    if state["revision"] < minimum_revision:
        return None

    objective = find_objective(state, objective_id)
    if objective.get("lifecycle") != "DELEGATED":
        raise StateError("committed successor objective is not DELEGATED")
    if objective.get("owner_thread_id") != owner_thread_id:
        raise StateError("committed successor owner_thread_id mismatch")
    if objective.get("owner_role") != owner_role:
        raise StateError("committed successor owner_role mismatch")
    if objective.get("completion_binding") != completion_binding:
        raise StateError("committed successor completion_binding mismatch")
    if absorbed_terminal_event_id not in state["absorbed_terminal_event_ids"]:
        raise StateError("predecessor terminal_event_id is not absorbed")
    if any(
        pending.get("terminal_event_id") == absorbed_terminal_event_id
        for pending in state["pending_absorptions"]
    ):
        raise StateError("absorbed predecessor terminal remains pending")

    roles = [
        role for role in state["managed_roles"]
        if role.get("thread_id") == owner_thread_id
    ]
    if len(roles) != 1:
        raise StateError("committed successor must have exactly one managed role")
    role = roles[0]
    if role.get("role") != owner_role:
        raise StateError("committed successor managed role mismatch")
    if role.get("state") != objective.get("owner_state"):
        raise StateError("committed successor managed-role state mismatch")
    successor_jobs = [
        job
        for job in state["remote_jobs"]
        if job.get("objective_id") == objective_id
        or job.get("owner_thread_id") == owner_thread_id
    ]
    if expected_remote_job is None:
        if successor_jobs:
            raise StateError("committed successor has unexpected remote job binding")
    elif successor_jobs != [expected_remote_job]:
        raise StateError("committed successor remote job binding mismatch")
    return objective


def cmd_await_successor_activation(args: argparse.Namespace) -> None:
    """Wait read-only for one exact Controller successor-activation CAS."""
    if args.minimum_revision < 0:
        raise StateError("minimum_revision must be non-negative")
    if not 0 <= args.timeout_ms <= 30_000:
        raise StateError("timeout_ms must be between 0 and 30000")
    if not 1 <= args.poll_ms <= 1_000:
        raise StateError("poll_ms must be between 1 and 1000")
    if args.owner_role not in MANAGED_ROLE_KINDS:
        raise StateError("owner_role must be a canonical managed role")
    completion_binding = _strict_json_document(
        args.completion_binding_json.encode("utf-8"),
        "completion_binding_json",
    )
    _validate_completion_binding(completion_binding, "completion_binding")
    if not _nonempty(args.absorbed_terminal_event_id):
        raise StateError("absorbed_terminal_event_id must be non-empty")
    expected_remote_job = None
    if args.remote_job_json is not None:
        expected_remote_job = _strict_json_document(
            args.remote_job_json.encode("utf-8"),
            "remote_job_json",
        )
        if not isinstance(expected_remote_job, dict):
            raise StateError("remote_job_json must be an object")
        if args.owner_role != "Executor":
            raise StateError("only an Executor successor may bind a remote job")

    deadline = time.monotonic() + args.timeout_ms / 1000
    while True:
        state = read_state(Path(args.state))
        objective = _validate_committed_successor(
            state,
            minimum_revision=args.minimum_revision,
            objective_id=args.objective_id,
            owner_thread_id=args.owner_thread_id,
            owner_role=args.owner_role,
            completion_binding=completion_binding,
            absorbed_terminal_event_id=args.absorbed_terminal_event_id,
            expected_remote_job=expected_remote_job,
        )
        if objective is not None:
            terminal_identity_projection = {
                "completion_binding": copy.deepcopy(completion_binding),
            }
            if args.owner_role == "Executor":
                terminal_identity_projection["startup_chain_authority"] = copy.deepcopy(
                    objective.get("startup_chain_authority")
                )
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "revision": state["revision"],
                        "objective_id": objective["objective_id"],
                        "owner_thread_id": args.owner_thread_id,
                        "completion_binding_sha256": completion_binding_sha256(
                            completion_binding
                        ),
                        "terminal_identity_projection": terminal_identity_projection,
                        "remote_job_id": None
                        if expected_remote_job is None
                        else expected_remote_job.get("job_id"),
                    },
                    sort_keys=True,
                )
            )
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ActivationWaitTimeout(
                "successor activation CAS did not reach minimum_revision before timeout"
            )
        time.sleep(min(args.poll_ms / 1000, remaining))


def cmd_record_startup_attempt(args: argparse.Namespace) -> None:
    """CAS-append one sealed pre-utility failure inside the current Executor."""
    path = Path(args.state)
    state = read_state(path)
    objective = find_objective(state, args.objective_id)
    if (
        objective.get("lifecycle") != "DELEGATED"
        or objective.get("candidate_state") != "OPEN"
        or objective.get("owner_role") != "Executor"
        or objective.get("owner_state") not in {"ACTIVE", "WAITING_EXTERNAL"}
        or objective.get("scientific_outcome") != "UNOBSERVED"
    ):
        raise StateError(
            "record-startup-attempt requires one outcome-blind delegated Executor"
        )
    if objective.get("owner_thread_id") != args.owner_thread_id:
        raise StateError("record-startup-attempt owner does not match the objective")
    authority = _validate_startup_chain_authority(
        objective.get("startup_chain_authority"),
        "objective.startup_chain_authority",
    )
    _resolve_startup_chain_authority(authority)
    record_path = str(
        _terminal_path(args.attempt_record_path, "attempt_record_path")
    )
    record_sha256 = _sha256(args.attempt_record_sha256, "attempt_record_sha256")
    record_ref = {"path": record_path, "sha256": record_sha256}
    existing_records = authority["prior_attempt_records"]
    if record_ref in existing_records:
        record_data = _read_immutable_terminal(Path(record_path))
        if hashlib.sha256(record_data).hexdigest() != record_sha256:
            raise StateError("startup attempt digest changed after the CAS")
        _, rounds = _resolve_startup_chain_authority(authority)
        decision = _startup_chain_decision(rounds)
        print(
            json.dumps(
                {
                    "status": "ALREADY_APPLIED",
                    "revision": state["revision"],
                    "objective_id": args.objective_id,
                    **decision,
                },
                sort_keys=True,
            )
        )
        return
    if any(record["path"] == record_path for record in existing_records):
        raise StateError("startup attempt path is already bound with a different digest")
    if (
        isinstance(args.expected_revision, bool)
        or not isinstance(args.expected_revision, int)
        or state["revision"] != args.expected_revision
    ):
        raise StateError(
            f"revision conflict: expected {args.expected_revision}, found {state['revision']}"
        )
    record_data = _read_immutable_terminal(Path(record_path))
    if hashlib.sha256(record_data).hexdigest() != record_sha256:
        raise StateError("startup attempt digest does not match the sealed record")
    updated_authority = copy.deepcopy(authority)
    updated_authority["prior_attempt_records"].append(record_ref)
    _, rounds = _resolve_startup_chain_authority(updated_authority)
    objective["startup_chain_authority"] = updated_authority
    result = write_state(
        path,
        state,
        args.expected_revision,
        operation="RECORD_STARTUP_ATTEMPT",
    )
    decision = _startup_chain_decision(rounds)
    print(
        json.dumps(
            {
                "status": "PASS",
                "revision": result["revision"],
                "objective_id": args.objective_id,
                **decision,
            },
            sort_keys=True,
        )
    )


def cmd_derive_startup_chain_id(args: argparse.Namespace) -> None:
    state = read_state(Path(args.state))
    objective = find_objective(state, args.objective_id)
    if objective["lifecycle"] != "DELEGATED" or objective.get("owner_role") != "Executor":
        raise StateError("startup-chain admission requires a delegated Executor objective")
    authority = _validate_startup_chain_authority(
        objective.get("startup_chain_authority"),
        "objective.startup_chain_authority",
    )
    chain_id, rounds = _resolve_startup_chain_authority(authority)
    decision = _startup_chain_decision(rounds)
    print(
        json.dumps(
            {
                "status": "PASS",
                "startup_chain_id": chain_id,
                **decision,
            },
            sort_keys=True,
        )
    )


def cmd_prepare_terminal_callback(args: argparse.Namespace) -> None:
    """Render the existing callback from one sealed, prebound terminal."""
    state = read_state(Path(args.state))
    objective = find_objective(state, args.objective_id)
    if objective["lifecycle"] != "DELEGATED":
        raise StateError("callback preparation requires a delegated objective")
    binding = objective["completion_binding"]
    if binding["terminal_event_id"] != args.terminal_event_id:
        raise StateError("callback terminal_event_id does not match current completion binding")
    data, terminal_body = _read_bound_terminal(
        Path(binding["terminal_path"]),
        binding,
        objective.get("startup_chain_authority"),
        require_startup_authority_mirror=_requires_startup_authority_mirror(objective),
    )

    def compact_text(field: str) -> str | None:
        value = terminal_body.get(field)
        if value is None:
            return None
        if not isinstance(value, str):
            raise StateError(f"terminal.{field} must be null or a string")
        if len(value.encode("utf-8")) > 2048:
            raise StateError(f"terminal.{field} exceeds 2048 UTF-8 bytes")
        return value

    fresh_thread_reason = terminal_body.get("fresh_thread_reason")
    if fresh_thread_reason is not None:
        if (
            not isinstance(fresh_thread_reason, str)
            or fresh_thread_reason not in FRESH_THREAD_REASONS
        ):
            raise StateError("terminal.fresh_thread_reason is not allowlisted")

    payload = {
        "terminal_event_id": binding["terminal_event_id"],
        "objective_id": objective["objective_id"],
        "owner_thread_id": objective["owner_thread_id"],
        "terminal_path": binding["terminal_path"],
        "final_bytes": len(data),
        "final_sha256": hashlib.sha256(data).hexdigest(),
        "disposition": compact_text("disposition"),
        "next_action": compact_text("next_action"),
        "fresh_thread_reason": fresh_thread_reason,
    }
    print(canonical_bytes(payload).decode("utf-8"), end="")


def cmd_observe_terminal(args: argparse.Namespace) -> None:
    """Register a prebound terminal only after shared structural parsing."""
    path = Path(args.state)
    state = read_state(path)
    objective = find_objective(state, args.objective_id)
    if objective["lifecycle"] != "DELEGATED":
        raise StateError("terminal observation requires a delegated objective")
    if objective["owner_thread_id"] != args.owner_thread_id:
        raise StateError("terminal observation owner does not match")
    binding = objective["completion_binding"]
    event_id = binding["terminal_event_id"]
    if event_id in state["absorbed_terminal_event_ids"]:
        print(json.dumps({"status": "NOOP", "terminal_event_id": event_id}, sort_keys=True))
        return
    size, digest = _bound_terminal_envelope(
        Path(binding["terminal_path"]),
        binding,
        objective.get("startup_chain_authority"),
        require_startup_authority_mirror=_requires_startup_authority_mirror(objective),
    )
    expected_digest = _sha256(
        args.expected_terminal_sha256,
        "expected_terminal_sha256",
    )
    if (
        not isinstance(args.expected_terminal_bytes, int)
        or isinstance(args.expected_terminal_bytes, bool)
        or args.expected_terminal_bytes < 1
    ):
        raise StateError("expected_terminal_bytes must be a positive integer")
    if (size, digest) != (args.expected_terminal_bytes, expected_digest):
        raise StateError("terminal does not match the delivered callback envelope")
    existing = [
        item
        for item in state["pending_absorptions"]
        if item["objective_id"] == args.objective_id or item["terminal_event_id"] == event_id
    ]
    if existing:
        if len(existing) != 1:
            raise StateError("terminal observation collides with multiple pending records")
        pending = existing[0]
        expected = (
            event_id,
            binding["terminal_path"],
            completion_binding_sha256(binding),
            size,
            digest,
        )
        actual = (
            pending["terminal_event_id"],
            pending["terminal_path"],
            pending["completion_binding_sha256"],
            pending["terminal_bytes"],
            pending["terminal_sha256"],
        )
        if actual != expected:
            raise StateError("duplicate terminal observation conflicts with pending identity")
        print(json.dumps({"status": "NOOP", "terminal_event_id": event_id}, sort_keys=True))
        return
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    state["pending_absorptions"].append(
        {
            "terminal_event_id": event_id,
            "objective_id": objective["objective_id"],
            "owner_thread_id": objective["owner_thread_id"],
            "owner_role": objective["owner_role"],
            "completion_binding_sha256": completion_binding_sha256(binding),
            "terminal_path": binding["terminal_path"],
            "terminal_bytes": size,
            "terminal_sha256": digest,
            "terminal_cursor": args.terminal_cursor,
            "source_final_turn_id": args.source_final_turn_id,
            "observation_id": args.observation_id,
            "observed_at": now,
            "verification_state": "IDENTITY_VERIFIED",
            "controller_verification_ref": None,
        }
    )
    objective["owner_state"] = "TERMINAL_PENDING_ABSORPTION"
    roles = [
        role for role in state["managed_roles"] if role["thread_id"] == objective["owner_thread_id"]
    ]
    if len(roles) != 1:
        raise StateError("terminal observation owner must match one managed role")
    roles[0]["state"] = "TERMINAL_PENDING_ABSORPTION"
    roles[0]["title"] = _terminal_pending_title(roles[0]["title"])
    result = write_state(
        path,
        state,
        args.expected_revision,
        operation="OBSERVE_TERMINAL",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "revision": result["revision"],
                "terminal_event_id": event_id,
                "terminal_bytes": size,
                "terminal_sha256": digest,
            },
            sort_keys=True,
        )
    )


def cmd_verify_pending_terminal(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = read_state(path)
    pending = find_pending_terminal(state, args.terminal_event_id)
    if pending["completion_binding_sha256"] != args.completion_binding_sha256:
        raise StateError("pending completion binding does not match verification request")
    objective = find_objective(state, pending["objective_id"])
    if pending["completion_binding_sha256"] != completion_binding_sha256(
        objective["completion_binding"]
    ):
        raise StateError("pending terminal completion binding does not match objective")
    size, digest = _bound_terminal_envelope(
        Path(pending["terminal_path"]),
        objective["completion_binding"],
        objective.get("startup_chain_authority"),
        require_startup_authority_mirror=_requires_startup_authority_mirror(objective),
    )
    if size != pending["terminal_bytes"] or digest != pending["terminal_sha256"]:
        raise StateError("pending terminal immutable envelope changed before verification")
    if pending["verification_state"] == "CONTROLLER_VERIFIED":
        if pending["controller_verification_ref"] != args.controller_verification_ref:
            raise StateError("pending terminal was verified by a different Controller reference")
        print(json.dumps({"status": "NOOP", "terminal_event_id": args.terminal_event_id}, sort_keys=True))
        return
    pending["verification_state"] = "CONTROLLER_VERIFIED"
    pending["controller_verification_ref"] = args.controller_verification_ref
    result = write_state(
        path,
        state,
        args.expected_revision,
        operation="VERIFY_PENDING_TERMINAL",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "revision": result["revision"],
                "terminal_event_id": args.terminal_event_id,
                "verification_state": "CONTROLLER_VERIFIED",
            },
            sort_keys=True,
        )
    )


def cmd_claim(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = read_state(path)
    job = find_job(state, args.job_id)
    wake = job["wake_delivery"]
    if wake["state"] != "NONE":
        raise StateError(f"job wake already {wake['state']}")
    job["monitor_state"] = "TERMINAL_OBSERVED"
    job["wake_delivery"] = {
        "state": "CLAIMED",
        "claim_token": args.claim_token,
        "observation_id": args.observation_id,
    }
    result = write_state(path, state, args.expected_revision)
    print(json.dumps({"status": "PASS", "revision": result["revision"], "delivery": "CLAIMED"}, sort_keys=True))


def cmd_complete(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = read_state(path)
    job = find_job(state, args.job_id)
    wake = job["wake_delivery"]
    if wake["state"] != "CLAIMED" or wake["claim_token"] != args.claim_token:
        raise StateError("job wake claim does not match")
    wake["state"] = "SENT"
    result = write_state(path, state, args.expected_revision)
    print(json.dumps({"status": "PASS", "revision": result["revision"], "delivery": "SENT"}, sort_keys=True))


def cmd_claim_advisory(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = read_state(path)
    advisory = find_advisory(state, args.advisory_id)
    if advisory["monitor_state"] != "AWAITING_RESPONSE":
        raise StateError(f"advisory response already {advisory['monitor_state']}")
    wake = advisory["wake_delivery"]
    if wake["state"] != "NONE":
        raise StateError(f"advisory wake already {wake['state']}")
    if args.observed_thread_updated_at <= advisory["submitted_thread_updated_at"]:
        raise StateError("observed thread update does not exceed submission baseline")
    advisory["monitor_state"] = "RESPONSE_OBSERVED"
    advisory["observed_thread_updated_at"] = args.observed_thread_updated_at
    advisory["wake_delivery"] = {
        "state": "CLAIMED",
        "claim_token": args.claim_token,
        "observation_id": args.observation_id,
    }
    result = write_state(
        path,
        state,
        args.expected_revision,
        operation="CLAIM_ADVISORY_WAKE",
    )
    print(json.dumps({"status": "PASS", "revision": result["revision"], "delivery": "CLAIMED"}, sort_keys=True))


def cmd_complete_advisory(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = read_state(path)
    advisory = find_advisory(state, args.advisory_id)
    wake = advisory["wake_delivery"]
    if advisory["monitor_state"] != "RESPONSE_OBSERVED":
        raise StateError("advisory response is not observed")
    if wake["state"] != "CLAIMED" or wake["claim_token"] != args.claim_token:
        raise StateError("advisory wake claim does not match")
    wake["state"] = "SENT"
    result = write_state(
        path,
        state,
        args.expected_revision,
        operation="COMPLETE_ADVISORY_WAKE",
    )
    print(json.dumps({"status": "PASS", "revision": result["revision"], "delivery": "SENT"}, sort_keys=True))


def cmd_absorb_nonblocking_advisory(args: argparse.Namespace) -> None:
    """Absorb one locally verified NON_BLOCKING Pro batch without changing objective lifecycle."""
    path = Path(args.state)
    state = read_state(path)
    advisory = find_advisory(state, args.advisory_id)
    if advisory["batch_mode"] != "NON_BLOCKING":
        raise StateError("only NON_BLOCKING advisory may use standalone absorption")
    if advisory["monitor_state"] != "RESPONSE_OBSERVED" or advisory["wake_delivery"]["state"] != "SENT":
        raise StateError("NON_BLOCKING advisory is not observed with SENT delivery")
    if args.local_validation_terminal_event_id in state["absorbed_terminal_event_ids"]:
        raise StateError("local validation terminal is already absorbed")
    objective = find_objective(state, advisory["objective_id"])
    state.setdefault("absorbed_advisory_scopes", []).append(
        {
            "candidate_id": objective["candidate_id"],
            "scope_sha256": advisory["scope_sha256"],
            "local_validation_terminal_event_id": args.local_validation_terminal_event_id,
        }
    )
    state["absorbed_terminal_event_ids"].append(args.local_validation_terminal_event_id)
    state["advisory_reads"] = [
        item for item in state["advisory_reads"] if item["advisory_id"] != args.advisory_id
    ]
    result = write_state(
        path,
        state,
        args.expected_revision,
        operation="ABSORB_NONBLOCKING_ADVISORY",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "revision": result["revision"],
                "absorbed_advisory_id": args.advisory_id,
                "local_validation_terminal_event_id": args.local_validation_terminal_event_id,
            },
            sort_keys=True,
        )
    )


def cmd_advance_cursors(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = read_state(path)
    updates = json.loads(args.updates_json)
    if not isinstance(updates, list) or not updates:
        raise StateError("cursor updates must be a non-empty list")
    roles = {role["thread_id"]: role for role in state["managed_roles"]}
    seen: set[str] = set()
    for index, update in enumerate(updates):
        where = f"cursor_updates[{index}]"
        if not isinstance(update, dict):
            raise StateError(f"{where} must be an object")
        _require(
            update,
            (
                "thread_id",
                "expected_cursor",
                "new_cursor",
                "observation_kind",
                "source_turn_state",
            ),
            where,
        )
        thread_id = update["thread_id"]
        if not _nonempty(thread_id) or thread_id in seen:
            raise StateError(f"{where}.thread_id is invalid or duplicate")
        seen.add(thread_id)
        role = roles.get(thread_id)
        if role is None:
            raise StateError(f"{where}.thread_id is not an active managed role")
        if update["expected_cursor"] != role["cursor"]:
            raise StateError(f"{where}.expected_cursor does not match")
        if not _nonempty(update["new_cursor"]):
            raise StateError(f"{where}.new_cursor must be non-empty")
        observation_kind = update["observation_kind"]
        if observation_kind not in CURSOR_OBSERVATION_KINDS:
            raise StateError(f"{where}.observation_kind is invalid")
        source_turn_state = update["source_turn_state"]
        if source_turn_state not in CURSOR_SOURCE_TURN_STATES:
            raise StateError(f"{where}.source_turn_state is invalid")
        terminal_event_id = update.get("terminal_event_id")
        if observation_kind == "TERMINAL":
            if not _nonempty(terminal_event_id):
                raise StateError(f"{where}.terminal_event_id is required for TERMINAL")
            if terminal_event_id not in state["absorbed_terminal_event_ids"]:
                raise StateError(f"{where}.terminal_event_id is not absorbed; cursor must not cross terminal")
        elif terminal_event_id is not None:
            raise StateError(f"{where}.terminal_event_id is only valid for TERMINAL")
        if (
            source_turn_state == "FINAL"
            and observation_kind == "NON_TERMINAL"
            and role["role"] == "Executor"
        ):
            owned_objectives = [
                objective
                for objective in state["objectives"]
                if objective.get("lifecycle") == "DELEGATED"
                and objective.get("owner_thread_id") == thread_id
            ]
            if len(owned_objectives) != 1:
                raise StateError(
                    f"{where} FINAL NON_TERMINAL Executor lacks one delegated objective"
                )
            objective = owned_objectives[0]
            active_jobs = [
                job
                for job in state["remote_jobs"]
                if job.get("objective_id") == objective["objective_id"]
                and job.get("owner_thread_id") == thread_id
                and job.get("monitor_state") == "ACTIVE"
                and job.get("wake_delivery")
                == {"state": "NONE", "claim_token": None, "observation_id": None}
            ]
            if len(active_jobs) != 1:
                raise StateError(
                    f"{where} FINAL NON_TERMINAL Executor requires exactly one active registered remote job"
                )
        role["cursor"] = update["new_cursor"]
    result = write_state(path, state, args.expected_revision)
    print(json.dumps({"status": "PASS", "revision": result["revision"], "advanced": len(updates)}, sort_keys=True))


def _clear_advisories_for_absorption(
    state: dict[str, Any],
    *,
    advisory_ids: list[str],
    objective: dict[str, Any],
    owner_thread_id: str,
    terminal_event_id: str,
    transition: str,
    target_stage: str,
) -> None:
    clear_ids = set(advisory_ids)
    if len(clear_ids) != len(advisory_ids):
        raise StateError("clear_advisory_id contains duplicates")
    known = {advisory["advisory_id"]: advisory for advisory in state["advisory_reads"]}
    missing = clear_ids - set(known)
    if missing:
        raise StateError(f"unknown clear_advisory_id: {', '.join(sorted(missing))}")

    gate = objective.get("advisory_blocking_gate")
    gate_is_target = bool(
        isinstance(gate, dict)
        and gate["transition"] == transition
        and gate["target_stage"] == target_stage
    )
    matching_gate_ids: list[str] = []
    consumed = state.setdefault("absorbed_advisory_scopes", [])
    for advisory_id in clear_ids:
        advisory = known[advisory_id]
        if advisory["objective_id"] != objective["objective_id"]:
            raise StateError(f"advisory {advisory_id} does not belong to the absorbed objective")
        if advisory["reader_thread_id"] != owner_thread_id:
            raise StateError(f"advisory {advisory_id} reader is not the absorbed owner")
        if advisory["monitor_state"] != "RESPONSE_OBSERVED" or advisory["wake_delivery"]["state"] != "SENT":
            raise StateError(f"advisory {advisory_id} is not observed with SENT delivery")
        if advisory["batch_mode"] == "BLOCKING_HIGH_RISK":
            if not gate_is_target or advisory["blocking_gate_id"] != gate["blocking_gate_id"]:
                raise StateError(f"advisory {advisory_id} does not authorize this exact transition")
            matching_gate_ids.append(advisory_id)
        consumed.append(
            {
                "candidate_id": objective["candidate_id"],
                "scope_sha256": advisory["scope_sha256"],
                "local_validation_terminal_event_id": terminal_event_id,
            }
        )

    if gate_is_target:
        if len(matching_gate_ids) != 1:
            raise StateError("exact blocking gate requires one observed locally validated advisory")
        objective.pop("advisory_blocking_gate", None)
    state["advisory_reads"] = [
        advisory for advisory in state["advisory_reads"] if advisory["advisory_id"] not in clear_ids
    ]


def cmd_activate_successor(args: argparse.Namespace) -> None:
    """Atomically absorb one terminal and transfer a delegated objective to its activated successor."""
    path = Path(args.state)
    state = read_state(path)
    objective = find_objective(state, args.objective_id)
    if objective["lifecycle"] != "DELEGATED":
        raise StateError("objective must be DELEGATED before successor activation")
    if objective.get("owner_thread_id") != args.old_owner_thread_id:
        raise StateError("old owner does not match delegated objective")
    if args.terminal_event_id in state["absorbed_terminal_event_ids"]:
        raise StateError("terminal_event_id is already absorbed")
    pending = _require_absorbable_pending(
        state,
        objective=objective,
        terminal_event_id=args.terminal_event_id,
        old_owner_thread_id=args.old_owner_thread_id,
    )
    new_completion_binding = json.loads(args.new_completion_binding_json)
    _validate_completion_binding(new_completion_binding, "new_completion_binding")
    reserved_terminal_event_ids = set(state["absorbed_terminal_event_ids"])
    reserved_terminal_event_ids.update(
        item["terminal_event_id"] for item in state["pending_absorptions"]
    )
    if new_completion_binding["terminal_event_id"] in reserved_terminal_event_ids:
        raise StateError(
            "new completion terminal_event_id is already pending or absorbed"
        )
    executor_continuation_kind = getattr(args, "executor_continuation_kind", None)
    if args.new_owner_role != "Executor" and executor_continuation_kind is not None:
        raise StateError(
            "executor-continuation-kind is allowed only for an Executor successor"
        )
    startup_authority_json = getattr(args, "new_startup_chain_authority_json", None)
    requested_startup_authority = None
    if startup_authority_json is not None:
        requested_startup_authority = _strict_json_document(
            startup_authority_json.encode("utf-8"),
            "new_startup_chain_authority_json",
        )
    startup_authority = _transition_startup_chain_authority(
        objective.get("startup_chain_authority"),
        requested_startup_authority,
        new_owner_role=args.new_owner_role,
    )
    new_remote_job_json = getattr(args, "new_remote_job_json", None)
    new_remote_job = None
    if new_remote_job_json is not None:
        new_remote_job = _strict_json_document(
            new_remote_job_json.encode("utf-8"),
            "new_remote_job_json",
        )
        if not isinstance(new_remote_job, dict):
            raise StateError("new_remote_job_json must be an object")
        if args.new_owner_role != "Executor":
            raise StateError("only an Executor successor may bind a remote job")

    clear_job_ids = set(args.clear_remote_job_id)
    if len(clear_job_ids) != len(args.clear_remote_job_id):
        raise StateError("clear_remote_job_id contains duplicates")
    known_job_ids = {job["job_id"] for job in state["remote_jobs"]}
    missing_job_ids = clear_job_ids - known_job_ids
    if missing_job_ids:
        raise StateError(f"unknown clear_remote_job_id: {', '.join(sorted(missing_job_ids))}")
    for job in state["remote_jobs"]:
        if job["job_id"] in clear_job_ids:
            if job["objective_id"] != args.objective_id or job["owner_thread_id"] != args.old_owner_thread_id:
                raise StateError(f"remote job {job['job_id']} does not belong to the absorbed objective/owner")
    state["remote_jobs"] = [job for job in state["remote_jobs"] if job["job_id"] not in clear_job_ids]

    _clear_advisories_for_absorption(
        state,
        advisory_ids=args.clear_advisory_id,
        objective=objective,
        owner_thread_id=args.old_owner_thread_id,
        terminal_event_id=args.terminal_event_id,
        transition="ACTIVATE_SUCCESSOR",
        target_stage=args.new_stage,
    )

    for other in state["objectives"]:
        if other is objective or other["lifecycle"] != "DELEGATED":
            continue
        if other.get("owner_thread_id") == args.old_owner_thread_id:
            raise StateError("old owner still owns another delegated objective")
    if any(job["owner_thread_id"] == args.old_owner_thread_id for job in state["remote_jobs"]):
        raise StateError("old owner still owns an uncleared remote job")
    roles = state["managed_roles"]
    old_roles = [role for role in roles if role["thread_id"] == args.old_owner_thread_id]
    if len(old_roles) != 1:
        raise StateError("old owner must match exactly one managed role")
    fresh_thread_reason = getattr(args, "fresh_thread_reason", None)
    fresh_thread_evidence_ref = getattr(args, "fresh_thread_evidence_ref", None)
    uses_fresh_thread = args.new_owner_thread_id != args.old_owner_thread_id
    _validate_owner_transition(
        old_thread_id=args.old_owner_thread_id,
        old_role=old_roles[0]["role"],
        new_thread_id=args.new_owner_thread_id,
        new_role=args.new_owner_role,
        fresh_thread_reason=fresh_thread_reason,
        fresh_thread_evidence_ref=fresh_thread_evidence_ref,
        controller_thread_id=state["controller"]["thread_id"],
    )
    _validate_executor_continuation(
        continuation_kind=executor_continuation_kind,
        old_owner_thread_id=args.old_owner_thread_id,
        new_owner_thread_id=args.new_owner_thread_id,
        old_owner_role=old_roles[0]["role"],
        new_owner_role=args.new_owner_role,
        new_candidate_state=args.new_candidate_state,
        new_scientific_outcome=args.new_scientific_outcome,
        new_remote_job=new_remote_job,
        previous_startup_authority=objective.get("startup_chain_authority"),
        resulting_startup_authority=startup_authority,
    )
    if uses_fresh_thread and any(
        role["thread_id"] == args.new_owner_thread_id for role in roles
    ):
        raise StateError("new owner is already a managed role")

    new_objective_id = args.new_objective_id or args.objective_id
    if new_objective_id != args.objective_id and any(
        item is not objective and item["objective_id"] == new_objective_id for item in state["objectives"]
    ):
        raise StateError("new objective_id already exists")
    objective.update(
        {
            "objective_id": new_objective_id,
            "candidate_state": args.new_candidate_state,
            "stage": args.new_stage,
            "scientific_outcome": args.new_scientific_outcome,
            "lifecycle": "DELEGATED",
            "next_action": args.new_next_action,
            "owner_thread_id": args.new_owner_thread_id,
            "owner_role": args.new_owner_role,
            "owner_state": args.new_owner_state,
            "completion_binding": new_completion_binding,
        }
    )
    if startup_authority is None:
        objective.pop("startup_chain_authority", None)
    else:
        objective["startup_chain_authority"] = startup_authority
    for stale_key in (
        "blocker",
        "reopening_fact",
        "idea_closure",
        "legacy_terminal_schema",
    ):
        objective.pop(stale_key, None)
    if uses_fresh_thread:
        objective["fresh_thread_reason"] = fresh_thread_reason
        objective["fresh_thread_evidence_ref"] = fresh_thread_evidence_ref
    else:
        objective.pop("fresh_thread_reason", None)
        objective.pop("fresh_thread_evidence_ref", None)
    objective.pop("owner_recovery_evidence_ref", None)

    new_role = {
        "thread_id": args.new_owner_thread_id,
        "role": args.new_owner_role,
        "title": args.new_owner_title,
        "state": args.new_owner_state,
        "pin_required": True,
        "cursor": args.new_cursor,
    }
    state["managed_roles"] = [
        new_role if role["thread_id"] == args.old_owner_thread_id else role for role in roles
    ]
    if new_remote_job is not None:
        if new_remote_job.get("objective_id") != new_objective_id:
            raise StateError("remote job objective_id mismatch")
        if new_remote_job.get("owner_thread_id") != args.new_owner_thread_id:
            raise StateError("remote job owner_thread_id mismatch")
        if new_remote_job.get("monitor_state") != "ACTIVE":
            raise StateError("new remote job must start ACTIVE")
        if new_remote_job.get("wake_delivery") != {
            "state": "NONE",
            "claim_token": None,
            "observation_id": None,
        }:
            raise StateError("new remote job must start with NONE wake delivery")
        if any(job.get("job_id") == new_remote_job.get("job_id") for job in state["remote_jobs"]):
            raise StateError("new remote job_id is already registered")
        state["remote_jobs"].append(new_remote_job)
    state["pending_absorptions"] = [
        item for item in state["pending_absorptions"] if item is not pending
    ]
    state["absorbed_terminal_event_ids"].append(args.terminal_event_id)
    result = write_state(path, state, args.expected_revision, operation="ACTIVATE_SUCCESSOR")
    print(
        json.dumps(
            {
                "status": "PASS",
                "revision": result["revision"],
                "absorbed_terminal_event_id": args.terminal_event_id,
                "objective_id": new_objective_id,
                "owner_thread_id": args.new_owner_thread_id,
                "fresh_thread_reason": fresh_thread_reason,
                "fresh_thread_evidence_ref": fresh_thread_evidence_ref,
            },
            sort_keys=True,
        )
    )


def _clear_owned_jobs(
    state: dict[str, Any],
    *,
    clear_job_ids: list[str],
    objective_id: str,
    owner_thread_id: str,
) -> None:
    clear_ids = set(clear_job_ids)
    if len(clear_ids) != len(clear_job_ids):
        raise StateError("clear_remote_job_id contains duplicates")
    known = {job["job_id"] for job in state["remote_jobs"]}
    missing = clear_ids - known
    if missing:
        raise StateError(f"unknown clear_remote_job_id: {', '.join(sorted(missing))}")
    for job in state["remote_jobs"]:
        if job["job_id"] in clear_ids and (
            job["objective_id"] != objective_id or job["owner_thread_id"] != owner_thread_id
        ):
            raise StateError(f"remote job {job['job_id']} does not belong to absorbed owner")
    state["remote_jobs"] = [job for job in state["remote_jobs"] if job["job_id"] not in clear_ids]


def _require_releasable_owner(
    state: dict[str, Any], objective: dict[str, Any], owner_thread_id: str
) -> list[dict[str, Any]]:
    if any(
        other is not objective
        and other["lifecycle"] == "DELEGATED"
        and other.get("owner_thread_id") == owner_thread_id
        for other in state["objectives"]
    ):
        raise StateError("old owner still owns another delegated objective")
    if any(job["owner_thread_id"] == owner_thread_id for job in state["remote_jobs"]):
        raise StateError("old owner still owns an uncleared remote job")
    roles = state["managed_roles"]
    if sum(role["thread_id"] == owner_thread_id for role in roles) != 1:
        raise StateError("old owner must match exactly one managed role")
    return roles


def cmd_close_objective(args: argparse.Namespace) -> None:
    """Atomically absorb one terminal and close one scientifically supported scope."""
    path = Path(args.state)
    state = read_state(path)
    objective = find_objective(state, args.objective_id)
    if objective["lifecycle"] != "DELEGATED":
        raise StateError("objective must be DELEGATED before scoped close")
    if objective.get("owner_thread_id") != args.old_owner_thread_id:
        raise StateError("old owner does not match delegated objective")
    if args.terminal_event_id in state["absorbed_terminal_event_ids"]:
        raise StateError("terminal_event_id is already absorbed")
    pending = _require_absorbable_pending(
        state,
        objective=objective,
        terminal_event_id=args.terminal_event_id,
        old_owner_thread_id=args.old_owner_thread_id,
    )
    closure = json.loads(args.closure_json)
    if not isinstance(closure, dict):
        raise StateError("closure_json must be an object")
    _clear_owned_jobs(
        state,
        clear_job_ids=args.clear_remote_job_id,
        objective_id=args.objective_id,
        owner_thread_id=args.old_owner_thread_id,
    )
    _clear_advisories_for_absorption(
        state,
        advisory_ids=args.clear_advisory_id,
        objective=objective,
        owner_thread_id=args.old_owner_thread_id,
        terminal_event_id=args.terminal_event_id,
        transition="CLOSE_OBJECTIVE",
        target_stage=args.new_stage,
    )
    roles = _require_releasable_owner(state, objective, args.old_owner_thread_id)
    objective.update(
        {
            "candidate_state": "CLOSED",
            "stage": args.new_stage,
            "scientific_outcome": args.new_scientific_outcome,
            "lifecycle": "DONE",
            "next_action": args.new_next_action,
            "idea_closure": closure,
        }
    )
    for stale_key in (
        "owner_thread_id",
        "owner_role",
        "owner_state",
        "blocker",
        "reopening_fact",
        "fresh_thread_reason",
        "fresh_thread_evidence_ref",
        "owner_recovery_evidence_ref",
        "advisory_blocking_gate",
        "completion_binding",
        "startup_chain_authority",
        "legacy_terminal_schema",
    ):
        objective.pop(stale_key, None)
    state["managed_roles"] = [role for role in roles if role["thread_id"] != args.old_owner_thread_id]
    state["pending_absorptions"] = [item for item in state["pending_absorptions"] if item is not pending]
    state["absorbed_terminal_event_ids"].append(args.terminal_event_id)
    result = write_state(path, state, args.expected_revision, operation="CLOSE_OBJECTIVE")
    print(json.dumps({"status": "PASS", "revision": result["revision"], "absorbed_terminal_event_id": args.terminal_event_id, "objective_id": args.objective_id, "lifecycle": "DONE"}, sort_keys=True))


def cmd_absorb_and_block(args: argparse.Namespace) -> None:
    """Absorb a verified terminal into one finite external/authority blocker."""
    path = Path(args.state)
    state = read_state(path)
    objective = find_objective(state, args.objective_id)
    if objective["lifecycle"] != "DELEGATED":
        raise StateError("objective must be DELEGATED before external blocking")
    if objective.get("owner_thread_id") != args.old_owner_thread_id:
        raise StateError("old owner does not match delegated objective")
    if args.terminal_event_id in state["absorbed_terminal_event_ids"]:
        raise StateError("terminal_event_id is already absorbed")
    blocker = json.loads(args.blocker_json)
    if not isinstance(blocker, dict):
        raise StateError("blocker_json must be an object")
    if _validate_blocker_attestation(blocker, "blocker") is None:
        raise StateError("blocker requires reason_code and evidence_ref")
    pending = _require_absorbable_pending(
        state,
        objective=objective,
        terminal_event_id=args.terminal_event_id,
        old_owner_thread_id=args.old_owner_thread_id,
    )
    _verify_blocker_attestation(
        blocker,
        pending_terminal_path=pending["terminal_path"],
        where="blocker",
    )
    if objective.get("advisory_blocking_gate") is not None:
        raise StateError("external blocking cannot bypass a high-risk advisory gate")
    _clear_owned_jobs(
        state,
        clear_job_ids=args.clear_remote_job_id,
        objective_id=args.objective_id,
        owner_thread_id=args.old_owner_thread_id,
    )
    _clear_advisories_for_absorption(
        state,
        advisory_ids=args.clear_advisory_id,
        objective=objective,
        owner_thread_id=args.old_owner_thread_id,
        terminal_event_id=args.terminal_event_id,
        transition="ACTIVATE_SUCCESSOR",
        target_stage=args.new_stage,
    )
    roles = _require_releasable_owner(state, objective, args.old_owner_thread_id)
    objective.update(
        {
            "candidate_state": "BLOCKED",
            "stage": args.new_stage,
            "scientific_outcome": args.new_scientific_outcome,
            "lifecycle": "BLOCKED",
            "next_action": args.new_next_action,
            "blocker": blocker,
        }
    )
    for stale_key in (
        "owner_thread_id",
        "owner_role",
        "owner_state",
        "idea_closure",
        "reopening_fact",
        "fresh_thread_reason",
        "fresh_thread_evidence_ref",
        "owner_recovery_evidence_ref",
        "advisory_blocking_gate",
        "completion_binding",
        "legacy_terminal_schema",
    ):
        objective.pop(stale_key, None)
    state["managed_roles"] = [role for role in roles if role["thread_id"] != args.old_owner_thread_id]
    state["pending_absorptions"] = [item for item in state["pending_absorptions"] if item is not pending]
    state["absorbed_terminal_event_ids"].append(args.terminal_event_id)
    result = write_state(path, state, args.expected_revision, operation="ABSORB_AND_BLOCK")
    print(json.dumps({"status": "PASS", "revision": result["revision"], "absorbed_terminal_event_id": args.terminal_event_id, "objective_id": args.objective_id, "lifecycle": "BLOCKED"}, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--state", required=True)
    validate.set_defaults(handler=cmd_validate)
    show = subparsers.add_parser("show")
    show.add_argument("--state", required=True)
    show.add_argument(
        "--projection", choices=("active", "full"), default="active"
    )
    show.set_defaults(handler=cmd_show)
    await_activation = subparsers.add_parser("await-successor-activation")
    await_activation.add_argument("--state", required=True)
    await_activation.add_argument("--minimum-revision", type=int, required=True)
    await_activation.add_argument("--objective-id", required=True)
    await_activation.add_argument("--owner-thread-id", required=True)
    await_activation.add_argument(
        "--owner-role", choices=sorted(MANAGED_ROLE_KINDS), required=True
    )
    await_activation.add_argument("--completion-binding-json", required=True)
    await_activation.add_argument("--absorbed-terminal-event-id", required=True)
    remote_job_expectation = await_activation.add_mutually_exclusive_group(required=True)
    remote_job_expectation.add_argument("--remote-job-json")
    remote_job_expectation.add_argument("--no-remote-job", action="store_true")
    await_activation.add_argument("--timeout-ms", type=int, default=30_000)
    await_activation.add_argument("--poll-ms", type=int, default=100)
    await_activation.set_defaults(handler=cmd_await_successor_activation)
    derive_chain = subparsers.add_parser("derive-startup-chain-id")
    derive_chain.add_argument("--state", required=True)
    derive_chain.add_argument("--objective-id", required=True)
    derive_chain.set_defaults(handler=cmd_derive_startup_chain_id)
    record_startup = subparsers.add_parser("record-startup-attempt")
    record_startup.add_argument("--state", required=True)
    record_startup.add_argument("--expected-revision", type=int, required=True)
    record_startup.add_argument("--objective-id", required=True)
    record_startup.add_argument("--owner-thread-id", required=True)
    record_startup.add_argument("--attempt-record-path", required=True)
    record_startup.add_argument("--attempt-record-sha256", required=True)
    record_startup.set_defaults(handler=cmd_record_startup_attempt)
    replace = subparsers.add_parser("replace")
    replace.add_argument("--state", required=True)
    replace.add_argument("--input", required=True)
    replace.add_argument("--expected-revision", type=int, required=True)
    replace.set_defaults(handler=cmd_replace)
    rebuild = subparsers.add_parser("rebuild-add-objective")
    rebuild.add_argument("--state", required=True)
    rebuild.add_argument("--expected-revision", type=int, required=True)
    rebuild.add_argument("--objective-id", required=True)
    rebuild.add_argument("--candidate-id", required=True)
    rebuild.add_argument("--stage", required=True)
    rebuild.add_argument("--scientific-outcome", required=True)
    rebuild.add_argument("--next-action", required=True)
    rebuild.add_argument("--owner-thread-id", required=True)
    rebuild.add_argument("--owner-role", choices=sorted(MANAGED_ROLE_KINDS), required=True)
    rebuild.add_argument("--owner-title", required=True)
    rebuild.add_argument("--cursor")
    rebuild.add_argument("--recovery-evidence-ref", required=True)
    rebuild.add_argument("--completion-binding-json", required=True)
    rebuild.add_argument("--terminal-bytes", type=int, required=True)
    rebuild.add_argument("--terminal-sha256", required=True)
    rebuild.set_defaults(handler=cmd_rebuild_add_objective)
    migrate = subparsers.add_parser("migrate-v2")
    migrate.add_argument("--state", required=True)
    migrate.add_argument("--input", required=True)
    migrate.add_argument("--expected-revision", type=int, required=True)
    migrate.set_defaults(handler=cmd_migrate_v2)
    migrate_v3 = subparsers.add_parser("migrate-v3")
    migrate_v3.add_argument("--state", required=True)
    migrate_v3.add_argument("--input", required=True)
    migrate_v3.add_argument("--expected-revision", type=int, required=True)
    migrate_v3.set_defaults(handler=cmd_migrate_v3)
    migrate_v4 = subparsers.add_parser("migrate-v4-native-heartbeat")
    migrate_v4.add_argument("--state", required=True)
    migrate_v4.add_argument("--expected-revision", type=int, required=True)
    migrate_v4.add_argument("--bindings-json", required=True)
    migrate_v4.set_defaults(handler=cmd_migrate_v4_native_heartbeat)
    reconcile = subparsers.add_parser("reconcile-open")
    reconcile.add_argument("--state", required=True)
    reconcile.add_argument("--expected-revision", type=int, required=True)
    reconcile.add_argument("--transitions-json", required=True)
    reconcile.add_argument("--remote-jobs-json", required=True)
    reconcile.set_defaults(handler=cmd_reconcile_open)
    claim = subparsers.add_parser("claim-job-wake")
    claim.add_argument("--state", required=True)
    claim.add_argument("--job-id", required=True)
    claim.add_argument("--expected-revision", type=int, required=True)
    claim.add_argument("--claim-token", required=True)
    claim.add_argument("--observation-id", required=True)
    claim.set_defaults(handler=cmd_claim)
    complete = subparsers.add_parser("complete-job-wake")
    complete.add_argument("--state", required=True)
    complete.add_argument("--job-id", required=True)
    complete.add_argument("--expected-revision", type=int, required=True)
    complete.add_argument("--claim-token", required=True)
    complete.set_defaults(handler=cmd_complete)
    claim_advisory = subparsers.add_parser("claim-advisory-wake")
    claim_advisory.add_argument("--state", required=True)
    claim_advisory.add_argument("--advisory-id", required=True)
    claim_advisory.add_argument("--expected-revision", type=int, required=True)
    claim_advisory.add_argument("--claim-token", required=True)
    claim_advisory.add_argument("--observation-id", required=True)
    claim_advisory.add_argument("--observed-thread-updated-at", type=float, required=True)
    claim_advisory.set_defaults(handler=cmd_claim_advisory)
    complete_advisory = subparsers.add_parser("complete-advisory-wake")
    complete_advisory.add_argument("--state", required=True)
    complete_advisory.add_argument("--advisory-id", required=True)
    complete_advisory.add_argument("--expected-revision", type=int, required=True)
    complete_advisory.add_argument("--claim-token", required=True)
    complete_advisory.set_defaults(handler=cmd_complete_advisory)
    absorb_advisory = subparsers.add_parser("absorb-nonblocking-advisory")
    absorb_advisory.add_argument("--state", required=True)
    absorb_advisory.add_argument("--advisory-id", required=True)
    absorb_advisory.add_argument("--expected-revision", type=int, required=True)
    absorb_advisory.add_argument("--local-validation-terminal-event-id", required=True)
    absorb_advisory.set_defaults(handler=cmd_absorb_nonblocking_advisory)
    callback = subparsers.add_parser("prepare-terminal-callback")
    callback.add_argument("--state", required=True)
    callback.add_argument("--objective-id", required=True)
    callback.add_argument("--terminal-event-id", required=True)
    callback.set_defaults(handler=cmd_prepare_terminal_callback)
    observe = subparsers.add_parser("observe-terminal")
    observe.add_argument("--state", required=True)
    observe.add_argument("--expected-revision", type=int, required=True)
    observe.add_argument("--objective-id", required=True)
    observe.add_argument("--owner-thread-id", required=True)
    observe.add_argument("--observation-id", required=True)
    observe.add_argument("--expected-terminal-bytes", type=int, required=True)
    observe.add_argument("--expected-terminal-sha256", required=True)
    observe.add_argument("--terminal-cursor")
    observe.add_argument("--source-final-turn-id")
    observe.set_defaults(handler=cmd_observe_terminal)
    verify_pending = subparsers.add_parser("verify-pending-terminal")
    verify_pending.add_argument("--state", required=True)
    verify_pending.add_argument("--expected-revision", type=int, required=True)
    verify_pending.add_argument("--terminal-event-id", required=True)
    verify_pending.add_argument("--completion-binding-sha256", required=True)
    verify_pending.add_argument("--controller-verification-ref", required=True)
    verify_pending.set_defaults(handler=cmd_verify_pending_terminal)
    advance = subparsers.add_parser("advance-cursors")
    advance.add_argument("--state", required=True)
    advance.add_argument("--expected-revision", type=int, required=True)
    advance.add_argument("--updates-json", required=True)
    advance.set_defaults(handler=cmd_advance_cursors)
    activate = subparsers.add_parser("activate-successor")
    activate.add_argument("--state", required=True)
    activate.add_argument("--expected-revision", type=int, required=True)
    activate.add_argument("--objective-id", required=True)
    activate.add_argument("--new-objective-id")
    activate.add_argument("--terminal-event-id", required=True)
    activate.add_argument("--old-owner-thread-id", required=True)
    activate.add_argument("--new-owner-thread-id", required=True)
    activate.add_argument("--fresh-thread-reason", choices=sorted(FRESH_THREAD_REASONS))
    activate.add_argument("--fresh-thread-evidence-ref")
    activate.add_argument("--new-owner-role", choices=sorted(MANAGED_ROLE_KINDS), required=True)
    activate.add_argument(
        "--executor-continuation-kind",
        choices=sorted(EXECUTOR_CONTINUATION_KINDS),
    )
    activate.add_argument("--new-owner-state", choices=sorted(ROLE_STATES), required=True)
    activate.add_argument("--new-owner-title", required=True)
    activate.add_argument("--new-cursor")
    activate.add_argument("--new-candidate-state", choices=sorted(CANDIDATE_STATES), required=True)
    activate.add_argument("--new-stage", required=True)
    activate.add_argument("--new-scientific-outcome", required=True)
    activate.add_argument("--new-next-action", required=True)
    activate.add_argument("--new-completion-binding-json", required=True)
    activate.add_argument("--new-startup-chain-authority-json")
    activate.add_argument("--new-remote-job-json")
    activate.add_argument("--clear-remote-job-id", action="append", default=[])
    activate.add_argument("--clear-advisory-id", action="append", default=[])
    activate.set_defaults(handler=cmd_activate_successor)
    close = subparsers.add_parser("close-objective")
    close.add_argument("--state", required=True)
    close.add_argument("--expected-revision", type=int, required=True)
    close.add_argument("--objective-id", required=True)
    close.add_argument("--terminal-event-id", required=True)
    close.add_argument("--old-owner-thread-id", required=True)
    close.add_argument("--new-stage", required=True)
    close.add_argument("--new-scientific-outcome", required=True)
    close.add_argument("--new-next-action", required=True)
    close.add_argument("--closure-json", required=True)
    close.add_argument("--clear-remote-job-id", action="append", default=[])
    close.add_argument("--clear-advisory-id", action="append", default=[])
    close.set_defaults(handler=cmd_close_objective)
    block = subparsers.add_parser("absorb-and-block")
    block.add_argument("--state", required=True)
    block.add_argument("--expected-revision", type=int, required=True)
    block.add_argument("--objective-id", required=True)
    block.add_argument("--terminal-event-id", required=True)
    block.add_argument("--old-owner-thread-id", required=True)
    block.add_argument("--new-stage", required=True)
    block.add_argument("--new-scientific-outcome", required=True)
    block.add_argument("--new-next-action", required=True)
    block.add_argument("--blocker-json", required=True)
    block.add_argument("--clear-remote-job-id", action="append", default=[])
    block.add_argument("--clear-advisory-id", action="append", default=[])
    block.set_defaults(handler=cmd_absorb_and_block)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except ActivationWaitTimeout as exc:
        print(
            json.dumps(
                {"status": "WAIT_ACTIVATION_COMMIT", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 75
    except (OSError, json.JSONDecodeError, StateError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
