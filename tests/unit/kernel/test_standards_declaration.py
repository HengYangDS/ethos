from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos_core.contracts.registry.declarations import StandardsDeclaration
from ethos_core.contracts.registry.declarations import load_standards_declaration

ROOT = Path(__file__).resolve().parents[3]


def test_standards_declaration_is_frozen_and_projects_adapter_registry() -> None:
    declaration = load_standards_declaration(ROOT / "system/standards.toml")

    assert declaration.adapters[0].id == "slsa"
    assert declaration.registry()["mcp"]["mode"] == "agent-projection"

    with pytest.raises(ValidationError):
        declaration.adapters[0].mode = "mutable"  # type: ignore[misc]


def test_standards_declaration_rejects_duplicate_or_incomplete_adapter_records() -> None:
    payload = load_standards_declaration(ROOT / "system/standards.toml").model_dump()
    payload["adapters"] = [*payload["adapters"], payload["adapters"][0]]
    with pytest.raises(ValidationError, match="duplicate standards adapter id"):
        StandardsDeclaration.model_validate(payload)

    payload = load_standards_declaration(ROOT / "system/standards.toml").model_dump()
    payload["adapters"][0].pop("fallback")
    with pytest.raises(ValidationError):
        StandardsDeclaration.model_validate(payload)
