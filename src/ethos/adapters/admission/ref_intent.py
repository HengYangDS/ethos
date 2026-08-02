"""Short-lived exact authorization for one local Git ref transaction."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal

from ethos.adapters.repo.git import git_stdout

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ethos.contracts.plan import GitRefUpdate

_INTENT_TTL = timedelta(minutes=1)
_INTENT_SUBDIR = Path("ethos") / "ref-intent"
_SCHEMA_VERSION = 1
_ATOMIC_READ_ATTEMPTS = 100
_ATOMIC_READ_DELAY_SECONDS = 0.001
_LOCK_ATTEMPTS = 1_000
_OPERATION_PARTS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789.-")


def _git_path(root: Path, relative: str) -> Path:
    resolved = git_stdout(root, "rev-parse", "--git-path", relative)
    if not resolved:
        return root / ".git" / relative
    path = Path(resolved)
    return path if path.is_absolute() else root / path


def ref_intent_dir(root: Path) -> Path:
    """Return the linked-worktree-safe local intent directory."""
    return _git_path(root, _INTENT_SUBDIR.as_posix())


def write_ref_intent(
    *,
    root: Path,
    ref_name: str,
    update: GitRefUpdate,
    operation: str,
    recoverable: bool = False,
) -> dict[str, object]:
    """Write one exact issued intent immediately before its Git CAS."""
    _require_operation(operation)
    now = datetime.now(UTC)
    nonce = _intent_key(
        ref_name=ref_name,
        update=update,
        operation=operation,
        recoverable=recoverable,
    )
    intent: dict[str, object] = {
        "schema_version": _SCHEMA_VERSION,
        "operation": operation,
        "ref_name": ref_name,
        "old_value": update.expected,
        "new_value": update.desired,
        "recoverable": recoverable,
        "nonce": nonce,
        "phase": "issued",
        "created_at": now.isoformat(),
        "expires_at": (now + _INTENT_TTL).isoformat(),
    }
    directory = ref_intent_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / f"{nonce}.lock"
    with _IntentLock(lock):
        path = directory / f"{nonce}.json"
        existing = _read_atomic(path) if path.exists() else None
        if existing is not None:
            if _exact_identity(existing) == _exact_identity(intent):
                return existing
            message = "ref_intent_collision"
            raise ValueError(message)
        path.unlink(missing_ok=True)
        _store(path, intent)
        return intent


class _IntentLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.descriptor = -1

    def __enter__(self) -> _IntentLock:
        for _ in range(_LOCK_ATTEMPTS):
            try:
                self.descriptor = os.open(
                    self.path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                time.sleep(_ATOMIC_READ_DELAY_SECONDS)
            else:
                return self
        message = "ref_intent_lock_timeout"
        raise ValueError(message)

    def __exit__(self, *_args: object) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
        self.path.unlink(missing_ok=True)


def _read_atomic(path: Path) -> dict[str, object] | None:
    for _ in range(_ATOMIC_READ_ATTEMPTS):
        if intent := _read(path):
            return intent
        time.sleep(_ATOMIC_READ_DELAY_SECONDS)
    return None


def _intent_key(
    *,
    ref_name: str,
    update: GitRefUpdate,
    operation: str,
    recoverable: bool,
) -> str:
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "operation": operation,
        "ref_name": ref_name,
        "old_value": update.expected,
        "new_value": update.desired,
        "recoverable": recoverable,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _exact_identity(intent: Mapping[str, object]) -> dict[str, object]:
    return {
        name: intent.get(name)
        for name in (
            "schema_version",
            "operation",
            "ref_name",
            "old_value",
            "new_value",
            "recoverable",
            "nonce",
        )
    }


def claim_ref_intent(
    *,
    root: Path,
    ref_name: str,
    update: GitRefUpdate,
    operation: str,
    phase: Literal["issued", "prepared", "committed", "aborted", "recover", "retry"],
) -> dict[str, object]:
    """Advance, abort, or observe one exact intent transaction."""
    _require_operation(operation)
    directory = ref_intent_dir(root)
    if not directory.is_dir():
        return _claim(present=False, gap="ref_intent_missing")
    mismatch = ""
    match: tuple[Path, dict[str, object], dict[str, object]] | None = None
    now = datetime.now(UTC)
    for path in sorted(directory.glob("*.json")):
        intent = _read(path)
        if intent is None or intent.get("ref_name") != ref_name:
            continue
        intent = dict(intent or {})
        if gap := _identity_gap(intent, update=update, operation=operation):
            mismatch = gap
            continue
        retrying = phase == "retry" and intent.get("phase") == "issued"
        recovering = phase in {"recover", "retry"} and _retained_prepared(intent)
        if _expired(intent, now=now) and not (retrying or recovering):
            stale = _reclaim_expired(path, intent, requested_phase=phase)
            if stale is not None:
                return stale
            continue
        if not isinstance(intent.get("recoverable"), bool):
            return _claim(present=True, gap="ref_intent_payload_invalid", intent=intent)
        if match is not None:
            return _claim(present=True, gap="ref_intent_ambiguous")
        match = path, intent, {}
    if match:
        path, intent, _ = match
        return _advance_locked(
            path,
            intent,
            phase=phase,
            update=update,
            operation=operation,
        )
    return _claim(present=bool(mismatch), gap=mismatch or "ref_intent_missing")


def _advance_locked(
    path: Path,
    observed: dict[str, object],
    *,
    phase: Literal["issued", "prepared", "committed", "aborted", "recover", "retry"],
    update: GitRefUpdate,
    operation: str,
) -> dict[str, object]:
    with _IntentLock(path.with_suffix(".lock")):
        current = _read(path)
        if current is None:
            return _claim(present=False, gap="ref_intent_missing")
        if _exact_identity(current) != _exact_identity(observed):
            return _claim(present=True, gap="ref_intent_changed", intent=current)
        if gap := _identity_gap(current, update=update, operation=operation):
            return _claim(present=True, gap=gap, intent=current)
        if not isinstance(current.get("recoverable"), bool):
            return _claim(present=True, gap="ref_intent_payload_invalid", intent=current)
        gap = _advance_intent(
            path,
            current,
            phase=phase,
            retain=current["recoverable"] is True,
        )
        return _claim(present=True, gap=gap, intent=current)


def _reclaim_expired(
    path: Path,
    intent: Mapping[str, object],
    *,
    requested_phase: str,
) -> dict[str, object] | None:
    with _IntentLock(path.with_suffix(".lock")):
        current = _read(path)
        if current != intent:
            return _claim(present=True, gap="ref_intent_changed", intent=current)
        path.unlink(missing_ok=True)
    return (
        None
        if intent.get("phase") == "issued" and requested_phase == "issued"
        else _claim(present=True, gap="ref_intent_stale", intent=intent)
    )


def _identity_gap(
    intent: Mapping[str, object],
    *,
    update: GitRefUpdate,
    operation: str,
) -> str:
    if intent.get("old_value") != update.expected or intent.get("new_value") != update.desired:
        return "ref_intent_mismatch"
    return "ref_intent_operation_mismatch" if intent.get("operation") != operation else ""


def clear_ref_intent(root: Path, nonce: str) -> None:
    """Remove one exact local intent idempotently."""
    (ref_intent_dir(root) / f"{nonce}.json").unlink(missing_ok=True)


def sweep_stale_ref_intents(root: Path, *, now: datetime | None = None) -> list[str]:
    """Remove expired or malformed intents and return their nonces."""
    directory = ref_intent_dir(root)
    if not directory.is_dir():
        return []
    moment = now or datetime.now(UTC)
    swept: list[str] = []
    for path in sorted(directory.glob("*.json")):
        with _IntentLock(path.with_suffix(".lock")):
            intent = _read(path)
            if intent is None or (_expired(intent, now=moment) and not _retained_prepared(intent)):
                path.unlink(missing_ok=True)
                swept.append(path.stem)
    return swept


def _require_operation(operation: str) -> None:
    if (
        not operation
        or operation != operation.strip()
        or operation.startswith(".")
        or operation.endswith(".")
        or ".." in operation
        or set(operation) - _OPERATION_PARTS
    ):
        message = f"ref_intent_operation_unknown:{operation}"
        raise ValueError(message)


def _advance_intent(
    path: Path,
    intent: dict[str, object],
    *,
    phase: Literal["issued", "prepared", "committed", "aborted", "recover", "retry"],
    retain: bool,
) -> str:
    current = intent.get("phase")
    if phase in {"issued", "prepared"}:
        return _advance_initial(path, intent, phase=phase)
    if phase == "retry":
        return _retry_intent(path, intent)
    if phase == "aborted":
        return _abort_intent(path, current=current, retain=retain)
    if phase == "recover":
        if current == "prepared" and retain:
            intent["phase"] = "committed"
            _store(path, intent)
        elif current != "committed":
            return "ref_intent_not_committed"
    elif current == "committed" and retain:
        return ""
    elif current != "prepared":
        return "ref_intent_not_prepared"
    elif retain:
        intent["phase"] = "committed"
        _store(path, intent)
    else:
        path.unlink(missing_ok=True)
    return ""


def _abort_intent(path: Path, *, current: object, retain: bool) -> str:
    if current == "committed":
        return "" if retain else "ref_intent_not_prepared"
    if current not in {"issued", "prepared"}:
        return "ref_intent_not_prepared"
    path.unlink(missing_ok=True)
    return ""


def _retry_intent(path: Path, intent: dict[str, object]) -> str:
    if intent.get("phase") == "issued":
        return ""
    if not _retained_prepared(intent):
        return "ref_intent_not_prepared"
    now = datetime.now(UTC)
    intent.update(
        phase="issued",
        created_at=now.isoformat(),
        expires_at=(now + _INTENT_TTL).isoformat(),
    )
    _store(path, intent)
    return ""


def _advance_initial(
    path: Path,
    intent: dict[str, object],
    *,
    phase: Literal["issued", "prepared"],
) -> str:
    current = intent.get("phase")
    if phase == "issued":
        return "" if current == "issued" else "ref_intent_not_issued"
    if current in {"prepared", "committed"}:
        return ""
    if current != "issued":
        return "ref_intent_reused"
    if phase == "prepared":
        intent["phase"] = "prepared"
        _store(path, intent)
    return ""


def _read(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _expired(intent: Mapping[str, object], *, now: datetime) -> bool:
    if intent.get("phase") == "committed":
        return False
    try:
        expires = datetime.fromisoformat(str(intent["expires_at"]))
    except (KeyError, TypeError, ValueError):
        return True
    return expires.tzinfo is None or now >= expires


def _retained_prepared(intent: Mapping[str, object]) -> bool:
    return intent.get("phase") == "prepared" and intent.get("recoverable") is True


def _store(path: Path, intent: Mapping[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(intent, stream, sort_keys=True, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _claim(
    *,
    present: bool,
    gap: str,
    intent: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload = intent or {}
    return {
        "present": present,
        "gap": gap,
        "schema_version": payload.get("schema_version"),
        "operation": str(payload.get("operation") or ""),
        "ref_name": str(payload.get("ref_name") or ""),
        "old_value": str(payload.get("old_value") or ""),
        "new_value": str(payload.get("new_value") or ""),
        "nonce": str(payload.get("nonce") or ""),
        "phase": str(payload.get("phase") or ""),
        "recoverable": payload.get("recoverable") is True,
    }
