"""Durable local records for exceptional unbound Work Lane retirement."""

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any
from typing import cast

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation

ATTEMPT_KIND = "exceptional_unbound_retirement_attempt"
RECEIPT_KIND = "exceptional_unbound_retirement_receipt"
MAX_STABLE_ERROR_LENGTH = 240
_GIT_SHA_LENGTH = 40
_RECORD_COLLISION = "unbound_retire_record_collision"
_RECORD_UNSAFE = "unbound_retire_record_unsafe"
_RECORD_INVALID = "unbound_retire_record_invalid"


def _keys(value: str) -> set[str]:
    return set(value.split())


def _data(**values: Any) -> dict[str, Any]:
    return values


_COMMON_KEYS = _keys(
    "schema_version kind operation_id branch expected_head accepted_head claim_id chronicle_ref "
    "chronicle_sha256 chronicle_claim_id chronicle_claim_sha256 reason before_observation_sha256 "
    "lease_relinquish_binding effect mints_authority recheck_required"
)
_POSTCONDITIONS = _keys(
    "ref_absent unbound_absent active_lease_absent protected_refs_unchanged chronicle_unchanged"
)


def sha256(value: object) -> str:
    """Return a stable digest for a structured record payload."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


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
    payload = _data(branch=branch, expect_head=expect_head, accepted_head=accepted_head)
    payload |= _data(protected_refs=protected_refs, claim_id=claim_id, chronicle=chronicle)
    payload |= _data(reason=reason, before_observation_sha256=observation_sha256)
    return f"exceptional-unbound-retirement:{sha256(payload)}"


def _payload(
    kind: str,
    operation_id: str,
    branch: str,
    expect_head: str,
    reason: str,
    observed: dict[str, Any],
) -> dict[str, object]:
    chronicle = observed["chronicle"]
    result = _data(schema_version=1, kind=kind, operation_id=operation_id, branch=branch)
    result |= _data(expected_head=expect_head, accepted_head=observed["accepted_head"])
    result |= _data(claim_id=observed["claim_id"], chronicle_ref=chronicle["ref"])
    result |= _data(
        chronicle_sha256=chronicle["sha256"], chronicle_claim_id=chronicle["target_claim"]
    )
    result |= _data(chronicle_claim_sha256=chronicle["claim_sha256"], reason=reason)
    result |= _data(before_observation_sha256=observed["observation_sha256"])
    result |= _data(lease_relinquish_binding=observation.lease_relinquish_binding(observed))
    result |= _data(mints_authority=False, recheck_required=True)
    return result


def attempt_payload(
    *,
    operation_id: str,
    branch: str,
    expect_head: str,
    reason: str,
    observation: dict[str, object],
) -> dict[str, object]:
    """Build the no-clobber pre-effect record."""
    return _payload(ATTEMPT_KIND, operation_id, branch, expect_head, reason, observation) | _data(
        protected_refs=observation["protected_refs"], effect="git_update_ref_compare_and_delete"
    )


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
    """Build the postcondition-bound retirement receipt."""
    protected = before["protected_refs"]
    result = _payload(RECEIPT_KIND, operation_id, branch, expect_head, reason, before)
    result |= _data(protected_refs_before=protected, protected_refs_after=after["protected_refs"])
    result |= _data(after_observation_sha256=after["observation_sha256"], effect=effect)
    result["lease_relinquished"] = lease_relinquished
    result["postconditions"] = _data(
        ref_absent=not bool(after["head"]),
        unbound_absent=not bool(after["status_unbound"]),
        active_lease_absent=not bool(after[observation.HAS_ACTIVE_LEASE]),
        protected_refs_unchanged=protected == after["protected_refs"],
        chronicle_unchanged=chronicle_unchanged,
    )
    return result


def _record_path(records_root: Path, operation_id: str, category: str) -> Path:
    return records_root / "recovery/unbound-retirement" / category / f"{suffix(operation_id)}.json"


def attempt_path(records_root: Path, operation_id: str) -> Path:
    """Return the durable attempt path for one operation identity."""
    return _record_path(records_root, operation_id, "attempts")


def receipt_path(records_root: Path, operation_id: str) -> Path:
    """Return the durable receipt path for one operation identity."""
    return _record_path(records_root, operation_id, "receipts")


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
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
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


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) in {40, 64}


def validate_record(payload: dict[str, object], *, kind: str) -> None:
    """Reject malformed durable records before they can guide a retry."""
    receipt = kind == RECEIPT_KIND
    receipt_keys = _keys(
        "protected_refs_before protected_refs_after after_observation_sha256 "
        "lease_relinquished postconditions"
    )
    required = _COMMON_KEYS | (receipt_keys if receipt else {"protected_refs"})
    protected = payload.get("protected_refs_before" if receipt else "protected_refs")
    invalid = (
        set(payload) != required
        or payload.get("kind") != kind
        or payload.get("schema_version") != 1
        or not str(payload.get("operation_id") or "").startswith("exceptional-unbound-retirement:")
        or not str(payload.get("branch") or "").startswith("work/")
        or not sha256_text_fields(
            payload,
            "expected_head",
            "accepted_head",
            "chronicle_sha256",
            "chronicle_claim_sha256",
        )
        or payload.get("mints_authority") is not False
        or payload.get("recheck_required") is not True
        or not valid_lease_relinquish_binding(payload.get("lease_relinquish_binding"))
        or not isinstance(protected, dict)
        or not protected
        or not all(protected.values())
    )
    postconditions = payload.get("postconditions")
    invalid |= receipt and (
        payload.get("protected_refs_after") != protected
        or not isinstance(postconditions, dict)
        or set(postconditions) != _POSTCONDITIONS
        or not all(value is True for value in postconditions.values())
        or not valid_lease_relinquishment(
            payload.get("lease_relinquish_binding"),
            payload.get("lease_relinquished"),
            subject=str(payload.get("branch") or ""),
        )
    )
    if invalid:
        raise ValueError(_RECORD_INVALID)


def valid_lease_relinquish_binding(value: object) -> bool:
    """Accept an exact lease binding or the explicit no-lease shape."""
    fields = {"active", "lease_id", "holder_ref", "epoch", "expected_head"}
    if not isinstance(value, dict) or set(value) != fields:
        return False
    binding = cast("dict[str, object]", value)
    active, epoch = binding.get("active"), binding.get("epoch")
    if not isinstance(active, bool):
        return False
    texts = tuple(binding.get(key) for key in ("lease_id", "holder_ref", "expected_head"))
    if not active:
        return epoch == 0 and texts == ("", "", "")
    return (
        all(isinstance(item, str) and item for item in texts)
        and isinstance(epoch, int)
        and not isinstance(epoch, bool)
        and epoch > 0
        and len(cast("str", texts[2])) == _GIT_SHA_LENGTH
    )


def valid_lease_relinquishment(binding: object, relinquished: object, *, subject: str) -> bool:
    """Require a receipt to retain the exact native lease CAS result."""
    if not isinstance(binding, dict):
        return False
    lease = cast("dict[str, object]", binding)
    if lease.get("active") is False:
        return relinquished == {}
    if lease.get("active") is not True:
        return False
    return relinquished == {
        "revoked": True,
        "subject": subject,
        "lease_id": lease.get("lease_id"),
        "holder_ref": lease.get("holder_ref"),
        "epoch": lease.get("epoch"),
        "expected_head": lease.get("expected_head"),
    }


def sha256_text_fields(payload: dict[str, object], *keys: str) -> bool:
    """Accept only SHA-1/SHA-256 textual record fields."""
    return all(_valid_digest(payload.get(key)) for key in keys)


def effect_summary(completed: object) -> dict[str, object]:
    """Project the sole Git effect without carrying raw output into evidence."""
    return {
        "command": "git update-ref --stdin",
        "transaction": "verify_protected_refs_delete_target",
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
