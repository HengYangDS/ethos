"""Optional invalid-state explanations over terminal-kernel concepts.

ETHOS evaluates an immutable ChangeContract against fresh RepositoryFacts,
transient PlanIR, and verifier-bounded Attestations. This module reads the
contract taxonomy and groups gap strings for readers without constraining new
signals. It does not create lifecycle state or replace the original verifier.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ethos._resources import declaration_text

CATEGORY_ORDER: tuple[str, ...] = (
    "change_contract_invalid",
    "repository_facts_invalid",
    "plan_invalid",
    "attestation_invalid",
    "execution_substrate_invalid",
)
UNCLASSIFIED = "unclassified_invalid_state"
_TAXONOMY_RESOURCE = "data/invalid_states.toml"


@dataclass(frozen=True, slots=True)
class InvalidStateCategory:
    """One terminal-kernel failure class and its recognized gap prefixes."""

    id: str
    concept: str
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
    """Read the taxonomy from the checkout or its packaged declaration resource."""
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
    """Load terminal categories in deterministic declaration order."""
    payload = tomllib.loads(_taxonomy_text())
    by_id = {
        str(entry["id"]): InvalidStateCategory(
            id=str(entry["id"]),
            concept=str(entry["concept"]),
            question=str(entry["question"]),
            summary=str(entry["summary"]),
            match_prefixes=tuple(str(prefix) for prefix in entry.get("match_prefixes", ())),
        )
        for entry in payload.get("category", ())
    }
    return tuple(by_id[category_id] for category_id in CATEGORY_ORDER if category_id in by_id)


def classify(gap: str) -> str:
    """Return the narrowest terminal-kernel category for one verifier signal."""
    best_id = UNCLASSIFIED
    best_len = -1
    segments = (gap, *gap.split(":"))
    for category in invalid_state_categories():
        for prefix in category.match_prefixes:
            if any(segment.startswith(prefix) for segment in segments) and len(prefix) > best_len:
                best_id, best_len = category.id, len(prefix)
    return best_id


def classify_all(gaps: tuple[str, ...]) -> dict[str, list[str]]:
    """Group verifier signals by terminal-kernel category in declaration order."""
    grouped: dict[str, list[str]] = {category.id: [] for category in invalid_state_categories()}
    grouped[UNCLASSIFIED] = []
    for gap in gaps:
        grouped[classify(gap)].append(gap)
    return {key: value for key, value in grouped.items() if value}


def invalid_state_projection(gaps: tuple[str, ...] | list[str]) -> dict[str, object]:
    """Project a verifier gap collection without changing its authority."""
    grouped = classify_all(tuple(str(gap) for gap in gaps))
    return {
        "categories": grouped,
        "category_count": len(grouped),
        "gap_count": sum(len(items) for items in grouped.values()),
    }


def explain_gap(gap: str) -> dict[str, object]:
    """Project one gap into taxonomy metadata for read-only surfaces."""
    category_id = classify(gap)
    categories = {category.id: category for category in invalid_state_categories()}
    category = categories.get(category_id)
    invalid_state = (
        {
            "id": category.id,
            "concept": category.concept,
            "question": category.question,
            "summary": category.summary,
        }
        if category is not None
        else {
            "id": UNCLASSIFIED,
            "concept": "taxonomy",
            "question": "Does a terminal-kernel category fit this signal?",
            "summary": (
                "No current category fits; the original verifier signal remains authoritative."
            ),
        }
    )
    return {
        "gap": gap,
        "signal": gap,
        "kind": "invalid_state_projection",
        "meaning": "A verifier reports a missing or invalid terminal-kernel precondition.",
        "invalid_state": invalid_state,
        "taxonomy": {
            "source": "system/invalid_states.toml",
            "schema": "system/schemas/contracts/invalid_states.schema.json",
            "projection_only": True,
            "lifecycle_command": False,
        },
        "next_action": "Inspect the original signal and its owning verifier.",
    }
