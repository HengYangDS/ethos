"""Restore the shared floor applicability that the stage-1 packaged registry withholds."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.repository.policy.gates as gate_policy
from ethos.contracts.gates import load_gate_registry_declaration

if TYPE_CHECKING:
    import pytest

    from ethos.contracts.gates import GateRegistryDeclaration

_DOCUMENTS = ("*.md",)
_CONFIGURATION = ("*.toml", "*.yaml", "*.yml", "*.json")
_FORMATTED = ("*.py", "*.pyi", *_DOCUMENTS, *_CONFIGURATION, "*.js", "*.mjs", "*.cjs")
FLOOR_APPLICABILITY = {
    "docs-registry": _DOCUMENTS,
    "openspec": ("openspec/config.yaml", "openspec/specs/*.md", "openspec/changes/*.md"),
    "markdown-links": _DOCUMENTS,
    "config-quality": (*_CONFIGURATION, "*.ini", "*.cfg"),
    "markdown-lint": _DOCUMENTS,
    "source-format": (*_FORMATTED, "*.sh", "*.bash", "*.svg"),
    "prose": _DOCUMENTS,
}


def restore_packaged_floors(monkeypatch: pytest.MonkeyPatch) -> GateRegistryDeclaration:
    """Patch the packaged registry with the shared floors' required paths for one test."""
    shipped = load_gate_registry_declaration()
    gates = tuple(
        gate.model_copy(update={"required_for_paths": FLOOR_APPLICABILITY.get(gate.id, ())})
        for gate in shipped.gates
    )
    packaged = shipped.model_copy(update={"gates": gates})
    monkeypatch.setattr(gate_policy, "_PACKAGED_GATE_DECLARATION", packaged)
    return packaged
