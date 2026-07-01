from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def _ledger_path(root: Path) -> Path:
    return root / "docs" / "governance" / "evolution-ledger.toml"


def evolution_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    if not path.exists():
        return {"hypotheses": []}
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {"hypotheses": [], "parse_error": str(exc)}
    return {"hypotheses": payload.get("hypothesis", [])}


def evolution_report(root: Path) -> dict[str, object]:
    ledger = evolution_ledger(root)
    hypotheses = ledger["hypotheses"]
    gaps = [
        f"hypothesis_missing_field:{index}"
        for index, item in enumerate(hypotheses)
        if not item.get("id")
        or not item.get("campaign")
        or not item.get("state")
        or not item.get("owner")
        or not item.get("claim")
        or not item.get("challenge")
        or not item.get("transition")
        or not item.get("proof_refs")
        or not item.get("review_refs")
        or not item.get("decision_refs")
        or not item.get("retirement_conditions")
    ]
    if ledger.get("parse_error"):
        gaps.append("evolution_ledger_invalid_toml")
    active = [item for item in hypotheses if item.get("state") in {"active", "experimenting"}]
    return {
        "ok": not gaps,
        "active_count": len(active),
        "required_gaps": gaps,
        "ledger": ledger,
    }


def evolution_candidates(root: Path) -> dict[str, object]:
    candidates = [
        {
            "id": "release-readiness-ratchet",
            "campaign": "ethos-release-hardening",
            "state": "ready",
            "owner": "ethos-maintainers",
            "claim": "Release readiness should keep gaining deterministic checks.",
            "challenge": "A clean report can still hide unmodeled ecosystem drift.",
            "transition": "observe -> shape",
            "proof_refs": ["ethos quality release-policy --json"],
            "review_refs": ["tests/unit/test_release_policy_and_attestation.py"],
            "decision_refs": ["docs/governance/release-governance.md"],
            "retirement_conditions": ["release policy emits no advisory gaps"],
        },
        {
            "id": "asset-quality-kernel",
            "campaign": "ethos-asset-quality-kernel",
            "state": "ready",
            "owner": "ethos-maintainers",
            "claim": "Quality and determinism require a first-class product package.",
            "challenge": "CLI quality commands without a semantic home create low-cohesion design.",
            "transition": "shape -> canonize",
            "proof_refs": ["ethos quality asset-policy --json"],
            "review_refs": ["tests/unit/test_quality_kernel.py"],
            "decision_refs": ["docs/architecture/package-ontology.md"],
            "retirement_conditions": [
                "ethos-quality owns quality semantics and repository consumes them"
            ],
        }
    ]
    return {"ok": True, "candidates": candidates}
