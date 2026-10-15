"""Formed-repository acceptance binds observations to the installed effect."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from tools.ci.delivery.acceptance.adopter import verify_formed

if TYPE_CHECKING:
    from pathlib import Path


def test_installed_formation_observation_binds_the_effect_head(tmp_path: Path) -> None:
    """A formation plan is not the result; the applied effect owns the commit OID."""
    target = tmp_path / "formed"
    target.mkdir()
    entry = target / "AGENTS.md"
    entry.write_text("Run ethos status --root . --json\n", encoding="utf-8")
    guide = tmp_path / "SKILL.md"
    guide.write_text("Use the installed product.\n", encoding="utf-8")
    digest = hashlib.sha256(guide.read_bytes()).hexdigest()
    head = "a" * 40
    plan: dict[str, object] = {
        "write_plan": [
            {"path": "AGENTS.md", "content_sha256": hashlib.sha256(entry.read_bytes()).hexdigest()}
        ]
    }
    status: dict[str, object] = {
        "verdict": "pass",
        "data": {
            "head": head,
            "dirty": False,
            "hook_runtime": {"current": True},
            "candidate": {"worktree_exists": True},
        },
        "governance_context": {"agent_guidance": {"sha256": digest, "path": str(guide)}},
    }

    assert verify_formed(target, plan, {"effect": {"head": head}}, (0, status, ""), digest) == head
    with pytest.raises(RuntimeError, match="installed_formation_status_invalid"):
        verify_formed(target, plan, {"head": head}, (0, status, ""), digest)
