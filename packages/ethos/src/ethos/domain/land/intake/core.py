"""Intake-ledger projection reducer for adopted repositories."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def intake_projection_report(repo: Path) -> dict[str, object]:
    """Project the intake-ledger configuration state (a non-truth projection)."""
    config_path = repo / ".ethos" / "intake.toml"
    gaps: list[str] = []
    provider = "unconfigured"
    configured = False
    if config_path.exists():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            provider = "invalid"
            gaps.append("intake_config_invalid:.ethos/intake.toml")
        else:
            configured_provider = str(config.get("provider") or "").strip()
            if configured_provider:
                provider = configured_provider
                configured = True
            else:
                provider = "invalid"
                gaps.append("intake_provider_missing:.ethos/intake.toml")
    state = "configured" if configured else "invalid" if gaps else "unconfigured"
    return {
        "kind": "intake_projection",
        "state": state,
        "truth_boundary": "projection-evidence",
        "repository_truth": False,
        "provider": provider,
        "configured": configured,
        "expected_config": ".ethos/intake.toml",
        "adapters": ["backlog", "github", "gitlab"],
        "blocking": False,
        "required_gaps": gaps,
    }
