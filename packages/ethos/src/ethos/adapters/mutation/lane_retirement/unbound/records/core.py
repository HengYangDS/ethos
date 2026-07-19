"""Durable local record mechanics for exceptional unbound Work Lane retirement."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import cast

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as unbound_observation

ATTEMPT_KIND = "exceptional_unbound_retirement_attempt"
RECEIPT_KIND = "exceptional_unbound_retirement_receipt"
MAX_STABLE_ERROR_LENGTH = 240
_GIT_SHA_LENGTH = 40
_RECORD_COLLISION = "unbound_retire_record_collision"
_RECORD_UNSAFE = "unbound_retire_record_unsafe"
_RECORD_INVALID = "unbound_retire_record_invalid"


def operation_id(  # noqa: PLR0913, RUF100 - exact record identity preserves bound state dimensions
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
        "lease_relinquish_binding": unbound_observation.lease_relinquish_binding(observation),
        "reason": reason,
        "before_observation_sha256": observation["observation_sha256"],
        "effect": "git_update_ref_compare_and_delete",
        "mints_authority": False,
        "recheck_required": True,
    }


def receipt_payload(  # noqa: PLR0913, RUF100 - exact receipt preserves bound state dimensions
    *,
    operation_id: str,
    branch: str,
    expect_head: str,
    reason: str,
    before: dict[str, object],
    after: dict[str, object],
    effect: dict[str, object],
    chronicle_unchanged: bool,
    lease_relinquished: dict[str, object],
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
        "lease_relinquish_binding": unbound_observation.lease_relinquish_binding(before),
        "lease_relinquished": lease_relinquished,
        "reason": reason,
        "before_observation_sha256": before["observation_sha256"],
        "after_observation_sha256": after["observation_sha256"],
        "effect": effect,
        "postconditions": {
            "ref_absent": not bool(after["head"]),
            "unbound_absent": not bool(after["status_unbound"]),
            "active_lease_absent": not bool(after[unbound_observation.HAS_ACTIVE_LEASE]),
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
            raise ValueError(_RECORD_COLLISION)
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
                raise ValueError(_RECORD_COLLISION) from exc
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
        raise ValueError(_RECORD_UNSAFE)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(_RECORD_INVALID) from exc
    if not isinstance(payload, dict):
        raise TypeError(_RECORD_INVALID)
    validate_record(payload, kind=kind)
    return payload


def validate_record(payload: dict[str, object], *, kind: str) -> None:
    """Reject malformed durable records before they can guide a retry."""
    required = _required_fields(kind)
    if (
        set(payload) != required
        or payload.get("kind") != kind
        or payload.get("schema_version") != 1
    ):
        raise ValueError(_RECORD_INVALID)
    _validate_common_fields(payload, kind=kind)
    if kind == RECEIPT_KIND:
        _validate_receipt_fields(payload)


def _required_fields(kind: str) -> set[str]:
    """Return the exact durable field set for one record kind."""
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
        "lease_relinquish_binding",
        "reason",
        "before_observation_sha256",
        "effect",
        "mints_authority",
        "recheck_required",
    }
    return (
        common
        | {
            "protected_refs_before",
            "protected_refs_after",
            "after_observation_sha256",
            "lease_relinquished",
            "postconditions",
        }
        if kind == RECEIPT_KIND
        else common | {"protected_refs"}
    )


def _validate_common_fields(payload: dict[str, object], *, kind: str) -> None:
    """Validate fields shared by attempts and receipts."""
    if not str(payload.get("operation_id") or "").startswith("exceptional-unbound-retirement:"):
        raise ValueError(_RECORD_INVALID)
    if not str(payload.get("branch") or "").startswith("work/"):
        raise ValueError(_RECORD_INVALID)
    if not sha256_text_fields(
        payload,
        "expected_head",
        "accepted_head",
        "chronicle_sha256",
        "chronicle_claim_sha256",
    ):
        raise ValueError(_RECORD_INVALID)
    if not valid_lease_relinquish_binding(payload.get("lease_relinquish_binding")):
        raise ValueError(_RECORD_INVALID)
    if payload.get("mints_authority") is not False or payload.get("recheck_required") is not True:
        raise ValueError(_RECORD_INVALID)
    protected_key = "protected_refs" if kind == ATTEMPT_KIND else "protected_refs_before"
    protected = payload.get(protected_key)
    if not isinstance(protected, dict) or not protected or not all(protected.values()):
        raise ValueError(_RECORD_INVALID)


def _validate_receipt_fields(payload: dict[str, object]) -> None:
    """Validate receipt-only postconditions and lease CAS evidence."""
    protected = payload["protected_refs_before"]
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
        raise ValueError(_RECORD_INVALID)
    if not valid_lease_relinquishment(
        payload.get("lease_relinquish_binding"),
        payload.get("lease_relinquished"),
        subject=str(payload.get("branch") or ""),
    ):
        raise ValueError(_RECORD_INVALID)


def sha256_text_fields(payload: dict[str, object], *keys: str) -> bool:
    """Accept only SHA-1/SHA-256 textual record fields."""
    return all(
        isinstance(payload.get(key), str) and len(str(payload[key])) in {40, 64} for key in keys
    )


def valid_lease_relinquish_binding(value: object) -> bool:
    """Accept a durable exact lease binding, or the explicit no-lease shape."""
    if not isinstance(value, dict) or set(value) != {
        "active",
        "lease_id",
        "holder_ref",
        "epoch",
        "expected_head",
    }:
        return False
    binding = cast("dict[str, object]", value)
    active = binding.get("active")
    if not isinstance(active, bool):
        return False
    fields = ("lease_id", "holder_ref", "expected_head")
    if not active:
        return binding.get("epoch") == 0 and all(binding.get(field) == "" for field in fields)
    lease_id = binding.get("lease_id")
    holder_ref = binding.get("holder_ref")
    epoch = binding.get("epoch")
    expected_head = binding.get("expected_head")
    return (
        isinstance(lease_id, str)
        and bool(lease_id)
        and isinstance(holder_ref, str)
        and bool(holder_ref)
        and isinstance(epoch, int)
        and not isinstance(epoch, bool)
        and epoch > 0
        and isinstance(expected_head, str)
        and len(expected_head) == _GIT_SHA_LENGTH
    )


def valid_lease_relinquishment(binding: object, relinquished: object, *, subject: str) -> bool:
    """Require a successful receipt to retain the exact native CAS result."""
    if not isinstance(binding, dict):
        return False
    lease_binding = cast("dict[str, object]", binding)
    active = lease_binding.get("active")
    if active is False:
        return relinquished == {}
    if active is not True:
        return False
    return relinquished == {
        "revoked": True,
        "subject": subject,
        "lease_id": lease_binding.get("lease_id"),
        "holder_ref": lease_binding.get("holder_ref"),
        "epoch": lease_binding.get("epoch"),
        "expected_head": lease_binding.get("expected_head"),
    }


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
