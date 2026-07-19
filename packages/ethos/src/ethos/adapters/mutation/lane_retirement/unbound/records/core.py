"""Durable local record mechanics for exceptional unbound Work Lane retirement."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import cast

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation

ATTEMPT_KIND = "exceptional_unbound_retirement_attempt"
RECEIPT_KIND = "exceptional_unbound_retirement_receipt"
MAX_STABLE_ERROR_LENGTH = 240


def operation_id(
    *,
    branch: str,
    expect_head: str,
    accepted_head: str,
    protected_refs: dict[str, str],
    claim_id: str,
    chronicle: dict[str, object],
    reason: str,
    observation_sha256: str,
) -> str:
    """Bind a deterministic identity to one irreversible ref transition."""
    digest = sha256(
        {
            "branch": branch,
            "expect_head": expect_head,
            "accepted_head": accepted_head,
            "protected_refs": protected_refs,
            "claim_id": claim_id,
            "chronicle": chronicle,
            "reason": reason,
            "before_observation_sha256": observation_sha256,
        }
    )
    return f"exceptional-unbound-retirement:{digest}"


def sha256(value: object) -> str:
    """Return a stable digest for a structured record payload."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def attempt_payload(
    *,
    operation_id: str,
    branch: str,
    expect_head: str,
    reason: str,
    observation: dict[str, object],
) -> dict[str, object]:
    """Build the no-clobber pre-effect record for an admitted operation."""
    chronicle = cast("dict[str, object]", observation["chronicle"])
    return {
        "schema_version": 1,
        "kind": ATTEMPT_KIND,
        "operation_id": operation_id,
        "branch": branch,
        "expected_head": expect_head,
        "accepted_head": observation["accepted_head"],
        "protected_refs": observation["protected_refs"],
        "claim_id": observation["claim_id"],
        "chronicle_ref": chronicle["ref"],
        "chronicle_sha256": chronicle["sha256"],
        "chronicle_claim_id": chronicle["target_claim"],
        "chronicle_claim_sha256": chronicle["claim_sha256"],
        "reason": reason,
        "before_observation_sha256": observation["observation_sha256"],
        "effect": "git_update_ref_compare_and_delete",
        "mints_authority": False,
        "recheck_required": True,
    }


def receipt_payload(
    *,
    operation_id: str,
    branch: str,
    expect_head: str,
    reason: str,
    before: dict[str, object],
    after: dict[str, object],
    effect: dict[str, object],
    chronicle_unchanged: bool,
) -> dict[str, object]:
    """Build the postcondition-bound receipt for a verified ref retirement."""
    chronicle = cast("dict[str, object]", before["chronicle"])
    return {
        "schema_version": 1,
        "kind": RECEIPT_KIND,
        "operation_id": operation_id,
        "branch": branch,
        "expected_head": expect_head,
        "accepted_head": before["accepted_head"],
        "protected_refs_before": before["protected_refs"],
        "protected_refs_after": after["protected_refs"],
        "claim_id": before["claim_id"],
        "chronicle_ref": chronicle["ref"],
        "chronicle_sha256": chronicle["sha256"],
        "chronicle_claim_id": chronicle["target_claim"],
        "chronicle_claim_sha256": chronicle["claim_sha256"],
        "reason": reason,
        "before_observation_sha256": before["observation_sha256"],
        "after_observation_sha256": after["observation_sha256"],
        "effect": effect,
        "postconditions": {
            "ref_absent": not bool(after["head"]),
            "unbound_absent": not bool(after["status_unbound"]),
            "active_lease_absent": not bool(after[observation.ACTIVE_LEASE_PRESENT]),
            "protected_refs_unchanged": before["protected_refs"] == after["protected_refs"],
            "chronicle_unchanged": chronicle_unchanged,
        },
        "mints_authority": False,
        "recheck_required": True,
    }


def attempt_path(records_root: Path, operation_id: str) -> Path:
    """Return the durable attempt path for one operation identity."""
    return (
        records_root
        / "recovery"
        / "unbound-retirement"
        / "attempts"
        / f"{suffix(operation_id)}.json"
    )


def receipt_path(records_root: Path, operation_id: str) -> Path:
    """Return the durable receipt path for one operation identity."""
    return (
        records_root
        / "recovery"
        / "unbound-retirement"
        / "receipts"
        / f"{suffix(operation_id)}.json"
    )


def suffix(operation_id: str) -> str:
    """Return the digest suffix from an operation identity."""
    return operation_id.rpartition(":")[2]


def write_record(path: Path, payload: dict[str, object], *, kind: str) -> str:
    """Publish one deterministic local record without clobbering another writer."""
    validate_record(payload, kind=kind)
    existing = read_record(path, kind=kind)
    if existing:
        if existing != payload:
            raise ValueError("unbound_retire_record_collision")
        return path.as_posix()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            if read_record(path, kind=kind) != payload:
                raise ValueError("unbound_retire_record_collision") from exc
    finally:
        temporary.unlink(missing_ok=True)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return path.as_posix()


def read_record(path: Path, *, kind: str) -> dict[str, object]:
    """Read and validate an existing record or return an empty mapping if absent."""
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return {}
    if not stat.S_ISREG(mode):
        raise ValueError("unbound_retire_record_unsafe")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("unbound_retire_record_invalid") from exc
    if not isinstance(payload, dict):
        raise TypeError("unbound_retire_record_invalid")
    validate_record(payload, kind=kind)
    return payload


def validate_record(payload: dict[str, object], *, kind: str) -> None:
    """Reject malformed durable records before they can guide a retry."""
    common = {
        "schema_version",
        "kind",
        "operation_id",
        "branch",
        "expected_head",
        "accepted_head",
        "claim_id",
        "chronicle_ref",
        "chronicle_sha256",
        "chronicle_claim_id",
        "chronicle_claim_sha256",
        "reason",
        "before_observation_sha256",
        "effect",
        "mints_authority",
        "recheck_required",
    }
    required = common | {"protected_refs"}
    if kind == RECEIPT_KIND:
        required = common | {
            "protected_refs_before",
            "protected_refs_after",
            "after_observation_sha256",
            "postconditions",
        }
    if (
        set(payload) != required
        or payload.get("kind") != kind
        or payload.get("schema_version") != 1
    ):
        raise ValueError("unbound_retire_record_invalid")
    if not str(payload.get("operation_id") or "").startswith("exceptional-unbound-retirement:"):
        raise ValueError("unbound_retire_record_invalid")
    if not str(payload.get("branch") or "").startswith("work/"):
        raise ValueError("unbound_retire_record_invalid")
    if not sha256_text_fields(
        payload, "expected_head", "accepted_head", "chronicle_sha256", "chronicle_claim_sha256"
    ):
        raise ValueError("unbound_retire_record_invalid")
    if payload.get("mints_authority") is not False or payload.get("recheck_required") is not True:
        raise ValueError("unbound_retire_record_invalid")
    protected_key = "protected_refs" if kind == ATTEMPT_KIND else "protected_refs_before"
    protected = payload.get(protected_key)
    if not isinstance(protected, dict) or not protected or not all(protected.values()):
        raise ValueError("unbound_retire_record_invalid")
    if kind == RECEIPT_KIND:
        expected = {
            "ref_absent",
            "unbound_absent",
            "active_lease_absent",
            "protected_refs_unchanged",
            "chronicle_unchanged",
        }
        postconditions = payload.get("postconditions")
        if (
            payload.get("protected_refs_after") != protected
            or not isinstance(postconditions, dict)
            or set(postconditions) != expected
            or not all(value is True for value in postconditions.values())
        ):
            raise ValueError("unbound_retire_record_invalid")


def sha256_text_fields(payload: dict[str, object], *keys: str) -> bool:
    """Accept only SHA-1/SHA-256 textual record fields."""
    return all(
        isinstance(payload.get(key), str) and len(str(payload[key])) in {40, 64} for key in keys
    )


def effect_summary(completed: object) -> dict[str, object]:
    """Project the sole Git effect without carrying its raw output into evidence."""
    return {
        "command": "git update-ref -d",
        "returncode": int(getattr(completed, "returncode", 1)),
        "stderr_sha256": hashlib.sha256(str(getattr(completed, "stderr", "")).encode()).hexdigest(),
    }


def stable_gap(exc: BaseException) -> str:
    """Return only a compact known exception string as a machine-readable gap."""
    message = str(exc).strip()
    return (
        message
        if message and "\n" not in message and len(message) <= MAX_STABLE_ERROR_LENGTH
        else "unbound_retire_effect_failed"
    )
