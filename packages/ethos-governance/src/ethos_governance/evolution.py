from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


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
