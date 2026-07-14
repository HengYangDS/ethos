from __future__ import annotations

import pytest
from pydantic import ValidationError

import ethos_core.contracts.openspec.models as openspec_contract
from ethos_core.contracts.openspec.models import AdopterOpenSpecPolicy
from ethos_core.contracts.openspec.models import ChangeScopeDeclaration


def test_openspec_scope_companion_contract_is_strict() -> None:
    """Scope companions use a stable ETHOS contract, not OpenSpec schema."""
    declaration = ChangeScopeDeclaration.model_validate({"schema_version": 1, "paths": ["docs/**"]})

    assert openspec_contract.__all__ == [
        "AdopterOpenSpecPolicy",
        "ChangeScopeDeclaration",
    ]
    assert declaration.paths == ("docs/**",)
    with pytest.raises(ValidationError):
        ChangeScopeDeclaration.model_validate({"schema_version": 1, "paths": []})
    with pytest.raises(ValidationError, match="scope paths must be unique"):
        ChangeScopeDeclaration.model_validate(
            {"schema_version": 1, "paths": ["docs/**", "docs/**"]}
        )
    with pytest.raises(ValidationError, match="dot segments"):
        ChangeScopeDeclaration.model_validate({"schema_version": 1, "paths": ["docs/../secret"]})


def test_adopter_openspec_policy_rejects_missing_or_empty_material_paths() -> None:
    """A profile cannot silently opt out of material-path admission."""
    with pytest.raises(ValidationError):
        AdopterOpenSpecPolicy.model_validate({})
    with pytest.raises(ValidationError):
        AdopterOpenSpecPolicy.model_validate({"material_paths": []})
    with pytest.raises(ValidationError, match="material paths must be unique"):
        AdopterOpenSpecPolicy.model_validate({"material_paths": ["guidelines.md", "guidelines.md"]})
