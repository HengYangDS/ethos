"""Bind acceptance purpose to unchanged quality floors and native audit evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import tomli_w

from ethos.adapters.repo.dependency_acceptance import dependency_acceptance_gaps
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.proof.plan import proof_acceptance_purpose
from ethos.repository.policy.gates import ResolvedGatePolicy
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import RepositoryProfileDeclaration

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.proof.plan import AcceptancePurpose


_MISSING_QUALITY = (
    "quality_obligation_unproven:behavior",
    "quality_obligation_unproven:static-analysis",
)


@pytest.mark.parametrize("owner_kind", ["packaged", "registry"])
def test_source_acceptance_preserves_floors_and_binds_native_audit(
    tmp_path: Path, owner_kind: str
) -> None:
    """One explicit purpose changes the audit command, never the required gate set."""
    declaration = load_gate_registry_declaration()
    profile = (
        RepositoryProfile(
            root=tmp_path,
            exists=True,
            declaration=RepositoryProfileDeclaration(
                profile_id="ethos", proof=ProofPolicy(gate_registry="system/gates.toml")
            ),
        )
        if owner_kind == "registry"
        else None
    )

    def compiled(purpose: AcceptancePurpose) -> ResolvedGatePolicy:
        return compile_gate_policy(
            profile=profile,
            gate_registry_source=tomli_w.dumps(
                declaration.model_dump(mode="json", exclude_defaults=True)
            ).encode(),
            repository_python="python",
            repository_paths=("src/ethos/cli.py",),
            full=True,
            acceptance_purpose=purpose,
        )

    strict = compiled("repository")
    source = compiled("local-source")
    assert source.projection["owner"] == strict.projection["owner"]
    assert not set(_MISSING_QUALITY).intersection(source.gaps)
    assert source.declaration == strict.declaration
    assert source.gate_ids == strict.gate_ids
    assert source.digest != strict.digest
    assert source.projection["acceptance_purpose"] == "local-source"
    for gate in strict.gates:
        selected = source.registry[gate.id]
        if gate.tool_adapter == "vulnerabilities":
            assert selected.command == (*gate.command, "--", "--scope", "local-development")
            assert source.nodes[source.gate_ids.index(gate.id)].command != (
                strict.nodes[strict.gate_ids.index(gate.id)].command
            )
        else:
            assert selected == gate
    with pytest.raises(ValueError, match="proof_acceptance_purpose_invalid"):
        proof_acceptance_purpose({"acceptance_purpose": "publishing"})


def test_partial_product_source_floor_still_requires_its_native_audit(tmp_path: Path) -> None:
    """A product gate subset cannot acquire a native-profile applicability exemption."""
    selected = compile_gate_policy(acceptance_purpose="local-source")
    assert "proof_dependency_acceptance_audit_missing" in selected.gaps
    assert dependency_acceptance_gaps(
        tmp_path, "a" * 40, selected.projection, (), acceptance_purpose="local-source"
    ) == ["proof_dependency_acceptance_audit_missing"]


@pytest.mark.parametrize(
    "gates",
    [
        "unparsed",
        (
            {
                "id": "audit",
                "command": ("{python}", "-m", "nox", "-s", "vulnerabilities"),
                "tool_adapter": "vulnerabilities",
            },
        ),
    ],
    ids=["malformed", "unexecuted"],
)
def test_release_acceptance_requires_each_selected_audit_attempt(tmp_path: Path, gates) -> None:
    """A malformed selection or an unexecuted audit is never read as accepted risk."""
    assert dependency_acceptance_gaps(
        tmp_path, "a" * 40, {"gates": gates}, (), acceptance_purpose="repository"
    ) == ["proof_dependency_acceptance_audit_missing"]
