from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from ethos_governance.history import history_identity_report


def _ledger_path(root: Path) -> Path:
    return root / "docs" / "governance" / "self-evolution-ledger.toml"


def evolution_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    if not path.exists():
        return {"hypotheses": []}
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    return {"hypotheses": payload.get("hypothesis", [])}


def evolution_report(root: Path) -> dict[str, object]:
    ledger = evolution_ledger(root)
    hypotheses = ledger["hypotheses"]
    gaps = [
        f"hypothesis_missing_field:{index}"
        for index, item in enumerate(hypotheses)
        if not item.get("id") or not item.get("campaign") or not item.get("state")
    ]
    active = [item for item in hypotheses if item.get("state") in {"active", "experimenting"}]
    return {
        "ok": not gaps,
        "active_count": len(active),
        "required_gaps": gaps,
        "ledger": ledger,
    }


def evolution_candidates(root: Path) -> dict[str, object]:
    candidates: list[dict[str, str]] = []
    history = history_identity_report(root)
    if history["raw_mismatches"] or history["unsigned_commits"] or history["subject_mismatches"]:
        candidates.append(
            {
                "id": "history-identity-normalization",
                "campaign": "ethos-release-hardening",
                "state": "ready",
                "claim": "Raw commit identity and signatures should be normalized.",
                "challenge": "GitLab-visible history remains inconsistent until rewritten.",
            }
        )
    if not candidates:
        candidates.append(
            {
                "id": "release-readiness-ratchet",
                "campaign": "ethos-release-hardening",
                "state": "ready",
                "claim": "Release readiness should keep gaining deterministic checks.",
                "challenge": "A clean report can still hide unmodeled ecosystem drift.",
            }
        )
    return {"ok": True, "candidates": candidates}
