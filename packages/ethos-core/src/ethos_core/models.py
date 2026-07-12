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


ASSURANCE_CLASSES = frozenset(
    {
        "digest_only",
        "semantic_attested",
        "independently_reviewed",
        "independently_reexecuted",
        "formally_proven",
    }
)
"""The complete claim-assurance vocabulary.

Each class says what the supplied evidence *actually establishes*.  The value
is deliberately about evidence depth rather than a tool, provider, or actor so
adopters may choose independent proof without inheriting this repository's
reference provider.
"""

PARSER_ASSURANCE_ALIASES = {"semantic": "semantic_attested"}
"""Temporary parser-only migration mapping for tracked legacy claims.

The alias is not an assurance class.  It keeps existing claims readable while
they are migrated; serializers always emit the canonical class.
"""

ASSURANCE_FORBIDDEN_PHRASES = {
    "digest_only": ("semantic", "verified", "validates", "enforces", "guarantees", "proves"),
    "semantic_attested": ("verified", "validates", "enforces", "guarantees"),
    "independently_reviewed": ("verified", "semantic correctness", "guarantees"),
    "independently_reexecuted": ("semantic correctness", "verified", "guarantees"),
    "formally_proven": (),
}
"""Conclusion vocabulary that each assurance class must reject.

The policy is intentionally conservative: an independent execution proves
only that exact bound floor ran elsewhere, not the semantic correctness of the
change.  A named formal proof is the only class that may make a proof claim,
and even then callers must bind it to its stated theorem.
"""

# Compatibility name used by a small number of direct contract tests.  It is
# intentionally core-only and never encodes repository/adopter policy.
CLAIM_OVERCLAIM_PHRASES = ASSURANCE_FORBIDDEN_PHRASES["digest_only"]


def canonical_assurance_class(value: str) -> str:
    """Return the canonical assurance class for one declared verifier token."""
    return PARSER_ASSURANCE_ALIASES.get(value, value)


@dataclass(frozen=True)
class Authority:
    id: str
    order_ref: str
    derived_views: tuple[str, ...] = ()
    policy_refs: tuple[str, ...] = ()
    chain_term: str = field(default="authority", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_text(self.id, "id"))
        object.__setattr__(self, "order_ref", _require_text(self.order_ref, "order_ref"))
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
            "order_ref": self.order_ref,
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
        declared_verifier = _require_text(self.verifier, "verifier")
        verifier = canonical_assurance_class(declared_verifier)
        object.__setattr__(self, "verifier", verifier)
        if verifier not in ASSURANCE_CLASSES:
            msg = "verifier must name a supported assurance class"
            raise ValueError(msg)
        binding = self.binding.lower()
        for phrase in ASSURANCE_FORBIDDEN_PHRASES[verifier]:
            if phrase in binding:
                msg = f"assurance class {verifier} does not permit {phrase}"
                raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "change_id": self.change_id,
            "evidence_ids": list(self.evidence_ids),
            "binding": self.binding,
            "verifier": self.verifier,
        }
