"""The plan an apply executes and the receipt each apply run leaves, both content-addressed."""

from __future__ import annotations

import hashlib
from contextlib import suppress
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StringConstraints

from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.contracts.digest import is_sha256_hex
from ethos.contracts.semantic import canonical_json_bytes

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

# Nanosecond times exceed JSON's exact integers, so records keep them as decimal strings.
_Nanoseconds = Annotated[str, StringConstraints(pattern=r"^[0-9]+$")]
_PLANS = ("requests", "record-retirement")
_RECEIPTS = ("receipts", "record-retirement")


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PlannedFile(_Record):
    """One planned file, by its store-relative path, size and modification time."""

    path: str
    size: int
    mtime_ns: _Nanoseconds


class PlannedItem(_Record):
    """One planned item: its kind, its state and every file it owns."""

    kind: str
    state: str
    files: tuple[PlannedFile, ...]


class Cutoffs(_Record):
    """The frozen floors: an older artifact or record may retire."""

    artifact: _Nanoseconds
    record: _Nanoseconds


class RetirementPlan(_Record):
    """The write-ahead plan that a preview leaves and an apply reads."""

    schema_version: Literal[2]
    kind: Literal["record-retirement-plan"]
    accepted_commit: str
    cutoffs: Cutoffs
    items: tuple[PlannedItem, ...]


class KindTally(BaseModel):
    """What one apply run did to one kind: deleted, already absent, kept and deferred."""

    model_config = ConfigDict(extra="forbid")

    deleted: int = 0
    deleted_bytes: int = 0
    absent: int = 0
    kept: dict[str, int] = Field(default_factory=dict)
    deferred: dict[str, int] = Field(default_factory=dict)

    def add(self, outcome: Literal["kept", "deferred"], reason: str) -> None:
        """Count one item that stays, by why it stays."""
        counts = self.kept if outcome == "kept" else self.deferred
        counts[reason] = counts.get(reason, 0) + 1


class RetirementReceipt(_Record):
    """One apply run's outcome for its plan, read after its last batch."""

    schema_version: Literal[1] = 1
    kind: Literal["record-retirement-receipt"] = "record-retirement-receipt"
    plan: str
    runtime_build: dict[str, str | int]
    cutoffs: Cutoffs
    kinds: dict[str, KindTally]
    live_members_clear: bool


def write_plan(store: Path, document: Mapping[str, object]) -> dict[str, object]:
    """Persist one plan; an unchanged store's preview writes the same plan."""
    return _write(store.joinpath(*_PLANS), document, "record_retirement_plan_collision")


def read_plan(store: Path, digest: str) -> RetirementPlan:
    """Read the plan a digest names, refusing a missing, altered or older plan."""
    path = store.joinpath(*_PLANS, f"{digest}.json")
    if not is_sha256_hex(digest) or not path.is_file():
        message = "record_retirement_plan_missing"
        raise ValueError(message)
    payload = path.read_bytes()
    plan = None
    if hashlib.sha256(payload).hexdigest() == digest:
        with suppress(ValueError):
            plan = RetirementPlan.model_validate_json(payload)
    if plan is None:
        message = "record_retirement_plan_mismatch"
        raise ValueError(message)
    return plan


def write_receipt(store: Path, receipt: RetirementReceipt) -> dict[str, object]:
    """Persist one run's receipt."""
    document = receipt.model_dump(mode="json")
    return _write(store.joinpath(*_RECEIPTS), document, "record_retirement_receipt_collision")


def applied_receipt(store: Path, digest: str) -> dict[str, object] | None:
    """Return the receipt that binds a plan without a deferral, when one does."""
    directory = store.joinpath(*_RECEIPTS)
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else ():
        payload = path.read_bytes()
        try:
            receipt = RetirementReceipt.model_validate_json(payload)
        except ValueError:
            continue
        deferred = any(tally.deferred for tally in receipt.kinds.values())
        bound = hashlib.sha256(payload).hexdigest() == path.stem and receipt.plan == digest
        if bound and not deferred:
            return {"path": path.as_posix(), "sha256": path.stem, "size_bytes": len(payload)}
    return None


def _write(directory: Path, document: Mapping[str, object], collision: str) -> dict[str, object]:
    payload = canonical_json_bytes(document)
    digest = hashlib.sha256(payload).hexdigest()
    path = write_content_addressed(directory / f"{digest}.json", payload, collision=collision)
    return {"path": path.as_posix(), "sha256": digest, "size_bytes": len(payload)}
