"""The gate provider catalog resolves an ID and a legacy name to one callable."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import pytest

from ethos.contracts.gate_providers import provider_catalog
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import compile_gate_policy
from ethos.repository.profile import repository_profile_from_text
from tests.support.registries import repository_registry

if TYPE_CHECKING:
    from pathlib import Path

_DOCS = "ethos.application.docs_registry:docs_registry_report"
_SCHEMAS = "ethos.repository.policy.schema:schema_validation_report"
# Each `ethos.<module>:<callable>` name that gate declarations used before the catalog and that
# named a callable then: the 21 of the shipped registries, and two more that adopters declare.
_LEGACY_NAMES = {
    "ethos.adapters.gates.code_quality:behavior_report",
    "ethos.adapters.gates.code_quality:static_report",
    "ethos.adapters.gates.commit_ranges:commit_ranges_report",
    "ethos.adapters.gates.configuration:configuration_report",
    "ethos.adapters.gates.formatting:source_format_report",
    "ethos.adapters.gates.generated_artifacts:generated_artifact_gate_report",
    "ethos.adapters.gates.provenance.observation:integrity_report",
    "ethos.adapters.gates.python_quality:behavior_report",
    "ethos.adapters.gates.python_quality:static_report",
    "ethos.adapters.gates.tool:external_links_report",
    "ethos.adapters.gates.tool:markdown_links_report",
    "ethos.adapters.gates.tool:markdown_lint_report",
    "ethos.adapters.gates.tool:module_layout_gate_report",
    "ethos.adapters.gates.tool:prose_report",
    "ethos.adapters.gates.ty:ty_gate_report",
    "ethos.adapters.openspec.governance:openspec_validation_report",
    "ethos.assistants.skills.portfolio:skill_portfolio_report",
    "ethos.domain.source_budget.measurement:source_budget_report",
    "ethos.domain.status:audit_for_root",
    "ethos.domain.status:product_audit",
    "ethos.repository.policy.boundary.product:product_boundary_report",
    _DOCS,
    _SCHEMAS,
}
# A name that one adopter declares and that named no callable before the catalog either.
_UNMAPPED = "ethos.domain.prove:code_size_report"
_DOCS_SOURCE = "gate_policy_source_missing:docs-registry:@ethos/application/docs_registry.py"


def test_catalog_maps_every_legacy_name_to_an_id_with_its_own_importable_callable() -> None:
    """The table is the only map: no alias module stands in for a provider.

    TOML refuses a repeated key, so reading the table proves each ID and legacy name unique.
    """
    providers, legacy = provider_catalog()
    assert set(legacy) == _LEGACY_NAMES
    assert set(legacy.values()) <= set(providers)
    assert len(set(providers.values())) == len(providers)
    for target in providers.values():
        module, _, name = target.partition(":")
        assert callable(getattr(importlib.import_module(module), name)), target


@pytest.mark.parametrize(
    ("gate", "reference", "gap"),
    [
        ("docs-registry", "provider.docs-registry", _DOCS_SOURCE),
        ("docs-registry", _DOCS, _DOCS_SOURCE),
        ("check", "provider.unknown", "gate_provider_unresolved:check:provider.unknown"),
        ("check", _UNMAPPED, f"gate_provider_unresolved:check:{_UNMAPPED}"),
    ],
)
def test_shared_gate_composes_under_either_spelling_and_an_unresolved_name_refuses(
    tmp_path: Path, gate: str, reference: str, gap: str
) -> None:
    """A legacy name composes with the shared gate's ID; an unresolved name is the policy's gap.

    No material is supplied, so a resolved provider leaves one gap, which names its bound source.
    """
    profile = repository_profile_from_text(
        tmp_path,
        exists=True,
        text=f'profile_id = "target"\n[proof]\ncode_correctness_gates = ["{gate}"]\n'
        f'[[proof.gates]]\nid = "{gate}"\nkind = "docs"\nproviders = ["{reference}"]\n',
    )
    policy = compile_gate_policy(profile=profile, gate_ids=(gate,), repository_paths=("a.md",))
    assert policy.gaps == (gap,)


def test_shipped_registries_declare_every_provider_by_its_id() -> None:
    gates = (*load_gate_registry_declaration().gates, *repository_registry().gates)
    declared = {name for gate in gates for name in (*gate.providers, *gate.verification_providers)}
    assert declared
    assert declared <= set(provider_catalog()[0])
