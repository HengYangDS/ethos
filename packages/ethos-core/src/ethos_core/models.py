from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any


def _require_text(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        msg = f"{field_name} must be non-empty"
        raise ValueError(msg)
    return stripped


def _tuple_text(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    return tuple(_require_text(value, field_name) for value in values)


SEMANTIC_VERIFIERS = {"semantic"}
DIGEST_ONLY_VERIFIERS = {"digest_only"}
CLAIM_OVERCLAIM_PHRASES = (
    "semantic",
)
CHRONICLE_EVENT_TYPES = ("decision", "evidence", "state_change", "supersession")


@dataclass(frozen=True)
class JudgmentSource:
    id: str
    authority: str
    derived_views: tuple[str, ...] = ()
    policy_refs: tuple[str, ...] = ()
    chain_term: str = field(default="judgment_source", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "authority", _require_text(self.authority, "authority"))
        object.__setattr__(
            self,
            "derived_views",
            _tuple_text(self.derived_views, "derived_views"),
        )
        object.__setattr__(
            self,
            "policy_refs",
            _tuple_text(self.policy_refs, "policy_refs"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "authority": self.authority,
            "derived_views": list(self.derived_views),
            "policy_refs": list(self.policy_refs),
        }


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
class EvidenceClaim:
    id: str
    change_id: str
    evidence_ids: tuple[str, ...]
    binding: str
    verifier: str = "digest_only"
    chain_term: str = field(default="claim", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "change_id", _require_text(self.change_id, "change_id"))
        object.__setattr__(
            self,
            "evidence_ids",
            _tuple_text(self.evidence_ids, "evidence_ids"),
        )
        object.__setattr__(self, "binding", _require_text(self.binding, "binding"))
        object.__setattr__(self, "verifier", _require_text(self.verifier, "verifier"))
        if self.verifier not in DIGEST_ONLY_VERIFIERS | SEMANTIC_VERIFIERS:
            msg = "verifier must be one of digest_only or semantic"
            raise ValueError(msg)
        binding = self.binding.lower()
        if (
            self.verifier not in SEMANTIC_VERIFIERS
            and any(phrase in binding for phrase in CLAIM_OVERCLAIM_PHRASES)
        ):
            msg = "semantic claims require semantic verifier"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "change_id": self.change_id,
            "evidence_ids": list(self.evidence_ids),
            "binding": self.binding,
            "verifier": self.verifier,
        }


@dataclass(frozen=True)
class ChronicleEvent:
    id: str
    subject_id: str
    event_type: str
    evidence_ids: tuple[str, ...] = ()
    decision: str = ""
    supersedes: tuple[str, ...] = ()
    current_state_delta: str = ""
    chain_term: str = field(default="chronicle", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "subject_id", _require_text(self.subject_id, "subject_id"))
        object.__setattr__(self, "event_type", _require_text(self.event_type, "event_type"))
        if self.event_type not in CHRONICLE_EVENT_TYPES:
            msg = f"event_type must be one of {', '.join(CHRONICLE_EVENT_TYPES)}"
            raise ValueError(msg)
        object.__setattr__(self, "evidence_ids", _tuple_text(self.evidence_ids, "evidence_ids"))
        object.__setattr__(self, "supersedes", _tuple_text(self.supersedes, "supersedes"))
        if self.event_type == "decision":
            if not self.evidence_ids:
                msg = "decision events require evidence"
                raise ValueError(msg)
            if not self.decision.strip():
                msg = "decision is required for decision events"
                raise ValueError(msg)
            if not self.current_state_delta.strip():
                msg = "current_state_delta is required for decision events"
                raise ValueError(msg)
        if self.event_type == "evidence" and not self.evidence_ids:
            msg = "evidence events require evidence"
            raise ValueError(msg)
        if self.event_type == "state_change" and not self.current_state_delta.strip():
            msg = "state_change events require current_state_delta"
            raise ValueError(msg)
        if self.event_type == "supersession":
            if not self.supersedes:
                msg = "supersession events require supersedes"
                raise ValueError(msg)
            if not self.evidence_ids:
                msg = "supersession events require evidence"
                raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "event_type": self.event_type,
            "evidence_ids": list(self.evidence_ids),
            "decision": self.decision,
            "supersedes": list(self.supersedes),
            "current_state_delta": self.current_state_delta,
        }
