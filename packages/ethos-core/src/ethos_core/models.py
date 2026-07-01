from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _require_text(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        msg = f"{field_name} must be non-empty"
        raise ValueError(msg)
    return stripped


def _tuple_text(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    return tuple(_require_text(value, field_name) for value in values)


@dataclass(frozen=True)
class Subject:
    id: str
    kind: str
    name: str
    owner: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chain_term: str = field(default="subject", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "kind", _require_text(self.kind, "kind"))
        object.__setattr__(self, "name", _require_text(self.name, "name"))
        object.__setattr__(self, "owner", _require_text(self.owner, "owner"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "owner": self.owner,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Commitment:
    id: str
    subject_id: str
    kind: str
    statement: str
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    chain_term: str = field(default="commitment", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "subject_id", _require_text(self.subject_id, "subject_id"))
        object.__setattr__(self, "kind", _require_text(self.kind, "kind"))
        object.__setattr__(self, "statement", _require_text(self.statement, "statement"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "kind": self.kind,
            "statement": self.statement,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Change:
    id: str
    subject_ids: tuple[str, ...]
    commitment_ids: tuple[str, ...]
    transition: str
    inscriptions: tuple[str, ...] = ()
    ir: dict[str, Any] = field(default_factory=dict)
    chain_term: str = field(default="change", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "subject_ids", _tuple_text(self.subject_ids, "subject_ids"))
        object.__setattr__(
            self,
            "commitment_ids",
            _tuple_text(self.commitment_ids, "commitment_ids"),
        )
        object.__setattr__(self, "transition", _require_text(self.transition, "transition"))
        object.__setattr__(self, "inscriptions", _tuple_text(self.inscriptions, "inscriptions"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject_ids": list(self.subject_ids),
            "commitment_ids": list(self.commitment_ids),
            "transition": self.transition,
            "inscriptions": list(self.inscriptions),
            "ir": dict(self.ir),
        }


@dataclass(frozen=True)
class Evidence:
    id: str
    change_id: str
    kind: str
    refs: tuple[str, ...]
    head: str | None = None
    digest: str | None = None
    chain_term: str = field(default="evidence", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "change_id", _require_text(self.change_id, "change_id"))
        object.__setattr__(self, "kind", _require_text(self.kind, "kind"))
        object.__setattr__(self, "refs", _tuple_text(self.refs, "refs"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "change_id": self.change_id,
            "kind": self.kind,
            "refs": list(self.refs),
            "head": self.head,
            "digest": self.digest,
        }


@dataclass(frozen=True)
class ChronicleEvent:
    id: str
    subject_id: str
    event_type: str
    evidence_ids: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    chain_term: str = field(default="chronicle", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "subject_id", _require_text(self.subject_id, "subject_id"))
        object.__setattr__(self, "event_type", _require_text(self.event_type, "event_type"))
        object.__setattr__(self, "evidence_ids", _tuple_text(self.evidence_ids, "evidence_ids"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "event_type": self.event_type,
            "evidence_ids": list(self.evidence_ids),
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class Evolution:
    id: str
    subject_id: str
    hypothesis: str
    state: str
    evidence_ids: tuple[str, ...] = ()
    chain_term: str = field(default="evolution", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "subject_id", _require_text(self.subject_id, "subject_id"))
        object.__setattr__(self, "hypothesis", _require_text(self.hypothesis, "hypothesis"))
        object.__setattr__(self, "state", _require_text(self.state, "state"))
        object.__setattr__(self, "evidence_ids", _tuple_text(self.evidence_ids, "evidence_ids"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "hypothesis": self.hypothesis,
            "state": self.state,
            "evidence_ids": list(self.evidence_ids),
        }
