"""Short-lived exact authorization for one local Git ref transaction."""

from __future__ import annotations

import os
import time
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Literal

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.adapters.repo.git import git_stdout
from ethos.contracts.semantic import canonical_json_digest

if TYPE_CHECKING:
    from ethos.contracts.plan import GitRefUpdate

_INTENT_TTL = timedelta(minutes=1)
_INTENT_SUBDIR = Path("ethos") / "ref-intent"
_LOCK_ATTEMPTS = 1_000
_LOCK_DELAY_SECONDS = 0.001
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Oid = Annotated[str, Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")]


class _RefIntent(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: Literal[2] = 2
    operation: str = Field(pattern=r"^[a-z0-9-]+(?:\.[a-z0-9-]+)*$")
    ref_name: str = Field(pattern=r"^refs/[^\s]+$")
    old_value: Oid
    new_value: Oid
    plan_digest: Digest
    nonce: Digest
    phase: Literal["issued", "prepared", "committed"]
    created_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def validate_nonce(self) -> _RefIntent:
        if self.nonce != _intent_key(self):
            raise ValueError("ref_intent_nonce_invalid")
        return self


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
    plan_digest: str,
) -> dict[str, object]:
    """Write one exact plan-bound intent immediately before its Git CAS."""
    now = datetime.now(UTC)
    identity = {
        "schema_version": 2,
        "operation": operation,
        "ref_name": ref_name,
        "old_value": update.expected,
        "new_value": update.desired,
        "plan_digest": plan_digest,
    }
    intent = _RefIntent(
        **identity,
        nonce=canonical_json_digest(identity),
        phase="issued",
        created_at=now,
        expires_at=now + _INTENT_TTL,
    )
    directory = ref_intent_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{intent.nonce}.json"
    with _IntentLock(path.with_suffix(".lock")):
        existing = _read(path)
        if existing:
            if existing.nonce == intent.nonce:
                return existing.model_dump(mode="json")
            raise ValueError("ref_intent_collision")
        path.unlink(missing_ok=True)
        _store(path, intent)
    return intent.model_dump(mode="json")


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
                time.sleep(_LOCK_DELAY_SECONDS)
                continue
            return self
        raise ValueError("ref_intent_lock_timeout")

    def __exit__(self, *_args: object) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
        self.path.unlink(missing_ok=True)


def claim_ref_intent(
    *,
    root: Path,
    ref_name: str,
    update: GitRefUpdate,
    operation: str,
    phase: Literal["prepared", "committed", "aborted", "recover"],
    plan_digest: str | None = None,
) -> dict[str, object]:
    """Advance, abort, or observe one exact intent transaction."""
    directory = ref_intent_dir(root)
    if not directory.is_dir():
        return _claim(present=False, gap="ref_intent_missing")
    match, mismatch, terminal = _select_intent(
        directory,
        ref_name=ref_name,
        update=update,
        operation=operation,
        phase=phase,
        plan_digest=plan_digest,
    )
    if terminal or not match:
        return terminal or _claim(present=bool(mismatch), gap=mismatch or "ref_intent_missing")
    path, intent = match
    with _IntentLock(path.with_suffix(".lock")):
        current = _read(path)
        if current is None:
            return _claim(present=False, gap="ref_intent_missing")
        if current.nonce != intent.nonce:
            return _claim(present=True, gap="ref_intent_changed", intent=current)
        if gap := _identity_gap(
            current,
            update=update,
            operation=operation,
            plan_digest=plan_digest,
        ):
            return _claim(present=True, gap=gap, intent=current)
        gap, result = _advance(path, current, phase)
        return _claim(present=True, gap=gap, intent=result)


def _select_intent(
    directory: Path,
    *,
    ref_name: str,
    update: GitRefUpdate,
    operation: str,
    phase: str,
    plan_digest: str | None,
) -> tuple[tuple[Path, _RefIntent] | None, str, dict[str, object] | None]:
    match = None
    mismatch = ""
    now = datetime.now(UTC)
    for path in sorted(directory.glob("*.json")):
        intent = _read(path)
        if intent is None:
            _remove_invalid(path)
            return match, mismatch, _claim(present=True, gap="ref_intent_payload_invalid")
        if intent.ref_name != ref_name:
            continue
        if gap := _identity_gap(
            intent, update=update, operation=operation, plan_digest=plan_digest
        ):
            mismatch = gap
            continue
        if now >= intent.expires_at and not (
            phase == "recover" and intent.phase in {"prepared", "committed"}
        ):
            return match, mismatch, _reclaim_expired(path, intent)
        if match:
            return match, mismatch, _claim(present=True, gap="ref_intent_ambiguous")
        match = path, intent
    return match, mismatch, None


def _identity_gap(
    intent: _RefIntent,
    *,
    update: GitRefUpdate,
    operation: str,
    plan_digest: str | None,
) -> str:
    checks = (
        (
            intent.old_value != update.expected or intent.new_value != update.desired,
            "ref_intent_mismatch",
        ),
        (intent.operation != operation, "ref_intent_operation_mismatch"),
        (bool(plan_digest and intent.plan_digest != plan_digest), "ref_intent_plan_mismatch"),
    )
    return next((gap for failed, gap in checks if failed), "")


def committed_ref_intent(
    *,
    root: Path,
    operation: str,
    desired: str,
    ref_name: str = "",
) -> dict[str, object]:
    """Return the sole committed plan-bound intent for one desired ref state."""
    matches = []
    for path in sorted(ref_intent_dir(root).glob("*.json")):
        intent = _read(path)
        if intent is None:
            _remove_invalid(path)
        elif (
            (not ref_name or intent.ref_name == ref_name)
            and intent.operation == operation
            and intent.new_value == desired
            and intent.phase == "committed"
        ):
            matches.append(intent)
    return (
        _claim(present=True, gap="", intent=matches[0])
        if len(matches) == 1
        else _claim(
            present=bool(matches), gap="ref_intent_ambiguous" if matches else "ref_intent_missing"
        )
    )


def clear_ref_intent(root: Path, nonce: str) -> None:
    """Remove one exact local intent idempotently."""
    (ref_intent_dir(root) / f"{nonce}.json").unlink(missing_ok=True)


def sweep_stale_ref_intents(root: Path, *, now: datetime | None = None) -> list[str]:
    """Remove expired or malformed intents and return their nonces."""
    directory = ref_intent_dir(root)
    if not directory.is_dir():
        return []
    moment = now or datetime.now(UTC)
    swept = []
    for path in sorted(directory.glob("*.json")):
        with _IntentLock(path.with_suffix(".lock")):
            intent = _read(path)
            if intent is None or (moment >= intent.expires_at and intent.phase == "issued"):
                path.unlink(missing_ok=True)
                swept.append(path.stem)
    return swept


def _advance(
    path: Path,
    intent: _RefIntent,
    phase: Literal["prepared", "committed", "aborted", "recover"],
) -> tuple[str, _RefIntent]:
    if phase in {"committed", "recover"}:
        return _set_phase(path, intent, source="prepared", target="committed")
    if phase == "prepared":
        return _set_phase(path, intent, source="issued", target="prepared")
    if intent.phase == "committed":
        return "", intent
    if intent.phase not in {"issued", "prepared"}:
        return "ref_intent_not_prepared", intent
    path.unlink(missing_ok=True)
    return "", intent


def _set_phase(
    path: Path,
    intent: _RefIntent,
    *,
    source: Literal["issued", "prepared"],
    target: Literal["prepared", "committed"],
) -> tuple[str, _RefIntent]:
    if intent.phase == target:
        return "", intent
    if intent.phase != source:
        return ("ref_intent_reused" if target == "prepared" else "ref_intent_not_prepared"), intent
    updated = intent.model_copy(update={"phase": target})
    _store(path, updated)
    return "", updated


def _reclaim_expired(path: Path, intent: _RefIntent) -> dict[str, object]:
    with _IntentLock(path.with_suffix(".lock")):
        current = _read(path)
        if current is None or current.nonce != intent.nonce:
            return _claim(present=True, gap="ref_intent_changed", intent=current)
        path.unlink(missing_ok=True)
    return _claim(present=True, gap="ref_intent_stale", intent=intent)


def _remove_invalid(path: Path) -> None:
    with _IntentLock(path.with_suffix(".lock")):
        if _read(path) is None:
            path.unlink(missing_ok=True)


def _read(path: Path) -> _RefIntent | None:
    try:
        return _RefIntent.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _intent_key(intent: _RefIntent) -> str:
    return canonical_json_digest(
        intent.model_dump(mode="json", exclude={"nonce", "phase", "created_at", "expires_at"})
    )


def _store(path: Path, intent: _RefIntent) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(intent.model_dump_json())
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _claim(
    *,
    present: bool,
    gap: str,
    intent: _RefIntent | None = None,
) -> dict[str, object]:
    empty = dict.fromkeys(_RefIntent.model_fields, "")
    return {"present": present, "gap": gap, **(intent.model_dump(mode="json") if intent else empty)}
