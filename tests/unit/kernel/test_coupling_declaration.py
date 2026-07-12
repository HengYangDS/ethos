from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos_core.contracts.registry.declarations import CouplingDeclaration
from ethos_core.contracts.registry.declarations import load_coupling_declaration

ROOT = Path(__file__).resolve().parents[3]


def test_coupling_declaration_is_frozen_and_projects_declared_bindings() -> None:
    declaration = load_coupling_declaration(ROOT / "system/coupling.toml")

    assert declaration.layers["product_semantic_hard_binding"]
    assert declaration.binding("branch_role_policy").config_source == ".ethos/workspace.toml"
    assert declaration.binding("openspec_workspace").not_product_substrate is True
    assert declaration.binding_projection()[0]["id"] == "git_repository_substrate"

    with pytest.raises(ValidationError):
        declaration.bindings[0].id = "mutable"  # type: ignore[misc]


def test_coupling_declaration_rejects_duplicate_ids_and_invalid_adapter_admission() -> None:
    payload = load_coupling_declaration(ROOT / "system/coupling.toml").model_dump()
    payload["bindings"] = [*payload["bindings"], payload["bindings"][0]]
    with pytest.raises(ValidationError, match="duplicate coupling binding id"):
        CouplingDeclaration.model_validate(payload)

    payload = load_coupling_declaration(ROOT / "system/coupling.toml").model_dump()
    adapter = next(
        item for item in payload["bindings"] if item["id"] == "mcp_acp_protocol_adapters"
    )
    adapter["admission"] = {"authority_ref": "docs/governance/product-design-contract.md"}
    with pytest.raises(ValidationError, match="admission"):
        CouplingDeclaration.model_validate(payload)


@pytest.mark.parametrize(
    ("binding_id", "field", "value", "match"),
    [
        ("mcp_acp_protocol_adapters", "admission", None, "admission missing"),
        (
            "branch_role_policy",
            "admission",
            {
                "authority_ref": "docs/governance/product-design-contract.md",
                "truth_boundary": "profile_or_adapter",
                "decision_state": "admitted",
            },
            "admission outside",
        ),
        ("git_repository_substrate", "layer", "undeclared", "unknown coupling binding layer"),
    ],
)
def test_coupling_declaration_rejects_invalid_declared_boundaries(
    binding_id: str, field: str, value: object, match: str
) -> None:
    payload = load_coupling_declaration(ROOT / "system/coupling.toml").model_dump()
    binding = next(item for item in payload["bindings"] if item["id"] == binding_id)
    binding[field] = value

    with pytest.raises(ValidationError, match=match):
        CouplingDeclaration.model_validate(payload)
