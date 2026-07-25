"""Optional invalid-state explanations over an open-world gap vocabulary.

ETHOS is a repository trust-transition system: a transition is trustworthy iff every
node of the chain (Authority -> Subject -> Commitment -> Change -> Evidence -> Claim
-> Chronicle) is satisfied. Every gap ETHOS emits is therefore a FAILED PRECONDITION
of exactly one node or boundary precondition. This module loads the SSOT taxonomy
(system/invalid_states.toml) and classifies any gap string into its category, so
known gap strings may be grouped for readers without constraining new signals.

Pure kernel: TOML read only, no IO/subprocess/network. Derive-don't-store — the
categories live in the contract, this module is the projection.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ethos._resources import declaration_text

# The seven chain-node failures plus carrier/substrate boundary failures, in order.
# A gap that classifies to none of these remains an explicit unknown signal.
NODE_ORDER: tuple[str, ...] = (
    "authority_gap",
    "subject_ambiguous",
    "commitment_missing",
    "change_unbounded",
    "carrier_invalid",
    "evidence_missing_or_stale",
    "claim_unbound_or_overreaching",
    "chronicle_missing",
    "substrate_untrusted",
)

UNCLASSIFIED = "unclassified_invalid_state"
_TAXONOMY_RESOURCE = "data/invalid_states.toml"


@dataclass(frozen=True, slots=True)
class InvalidStateCategory:
    """One node-derived failure class. chain_term names the node whose precondition
    failed; match_prefixes are the gap-string prefixes that reduce to it."""

    id: str
    node: str
    question: str
    summary: str
    match_prefixes: tuple[str, ...]


def _taxonomy_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "system" / "invalid_states.toml"
        if candidate.exists():
            return candidate
    return Path("system/invalid_states.toml")


def _taxonomy_text() -> str:
    """Read the invalid-state taxonomy from source checkout or packaged resource.

    Source checkouts keep the governance contract in `system/invalid_states.toml`.
    Installed wheels run outside that checkout, so they need the release resource
    mirror packaged inside `ethos`.
    """
    taxonomy_path = _taxonomy_path()
    if taxonomy_path.exists():
        return taxonomy_path.read_text(encoding="utf-8")
    return declaration_text(
        taxonomy_path,
        resource=_TAXONOMY_RESOURCE,
        canonical=Path("system/invalid_states.toml"),
    )


@lru_cache(maxsize=1)
def invalid_state_categories() -> tuple[InvalidStateCategory, ...]:
    """Load the taxonomy in chain order (NODE_ORDER). Cached: the contract is static."""
    payload = tomllib.loads(_taxonomy_text())
    by_id = {
        str(entry["id"]): InvalidStateCategory(
            id=str(entry["id"]),
            node=str(entry["node"]),
            question=str(entry["question"]),
            summary=str(entry["summary"]),
            match_prefixes=tuple(str(prefix) for prefix in entry.get("match_prefixes", ())),
        )
        for entry in payload.get("category", ())
    }
    return tuple(by_id[node] for node in NODE_ORDER if node in by_id)


def classify(gap: str) -> str:
    """Return the invalid-state category id a gap string reduces to.

    Longest-prefix wins so specific prefixes beat generic ones; chain order breaks
    ties (an earlier node's precondition is the more fundamental failure). Returns
    UNCLASSIFIED when a gap matches no category. Unknown signals are preserved rather
    than forced into an unsuitable existing category.
    """
    best_id = UNCLASSIFIED
    best_len = -1
    segments = (gap, *gap.split(":"))
    for category in invalid_state_categories():
        for prefix in category.match_prefixes:
            if any(segment.startswith(prefix) for segment in segments) and len(prefix) > best_len:
                best_id, best_len = category.id, len(prefix)
    return best_id


def classify_all(gaps: tuple[str, ...]) -> dict[str, list[str]]:
    """Group gaps by their node-derived category (chain order preserved)."""
    grouped: dict[str, list[str]] = {category.id: [] for category in invalid_state_categories()}
    grouped[UNCLASSIFIED] = []
    for gap in gaps:
        grouped[classify(gap)].append(gap)
    return {key: value for key, value in grouped.items() if value}


def invalid_state_projection(gaps: tuple[str, ...] | list[str]) -> dict[str, object]:
    """Project a gap collection into grouped invalid-state categories."""
    grouped = classify_all(tuple(str(gap) for gap in gaps))
    return {
        "categories": grouped,
        "category_count": len(grouped),
        "gap_count": sum(len(items) for items in grouped.values()),
    }


def explain_gap(gap: str) -> dict[str, object]:
    """Project one gap into taxonomy metadata for read-only command surfaces."""
    category_id = classify(gap)
    categories = {category.id: category for category in invalid_state_categories()}
    category = categories.get(category_id)
    invalid_state = (
        {
            "id": category.id,
            "node": category.node,
            "question": category.question,
            "summary": category.summary,
        }
        if category is not None
        else {
            "id": UNCLASSIFIED,
            "node": "boundary:taxonomy",
            "question": "Does an existing explanation category fit this signal?",
            "summary": "No current category fits; the original signal remains authoritative.",
        }
    )
    return {
        "gap": gap,
        "signal": gap,
        "kind": "invalid_state_projection",
        "meaning": (
            "A governance gap or advisory signal names a failed or weakened "
            "precondition in the ETHOS trust-transition chain."
        ),
        "invalid_state": invalid_state,
        "taxonomy": {
            "source": "system/invalid_states.toml",
            "schema": "system/schemas/contracts/invalid_states.schema.json",
            "projection_only": True,
            "lifecycle_command": False,
        },
        "next_action": "Inspect the original signal and its owning verifier.",
    }
