"""Bind acceptance purpose to unchanged quality floors and native audit evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import tomli_w

from ethos.adapters.repo.dependency_acceptance import dependency_acceptance_gaps
from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.proof.plan import proof_acceptance_purpose
from ethos.repository.policy.gates import ResolvedGatePolicy
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import RepositoryProfileDeclaration
from tests.support.registries import repository_registry
from tests.support.registries import repository_registry_path

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.proof.plan import AcceptancePurpose


_MISSING_QUALITY = (
    "quality_obligation_unproven:behavior",
    "quality_obligation_unproven:static-analysis",
)


@pytest.mark.parametrize("full", [False, True])
@pytest.mark.parametrize("owner_kind", ["packaged", "registry"])
def test_source_acceptance_preserves_floors_and_binds_native_audit(
    tmp_path: Path, owner_kind: str, *, full: bool
) -> None:
    """One explicit purpose changes the audit command, never the required gate set."""
    declaration = repository_registry()
    profile = (
        RepositoryProfile(
            root=tmp_path,
            exists=True,
            declaration=RepositoryProfileDeclaration(
                profile_id="ethos", proof=ProofPolicy(gate_registry="system/repository-gates.toml")
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
            full=full,
            acceptance_purpose=purpose,
        )

    strict = compiled("repository")
    source = compiled("local-source")
    assert source.projection["owner"] == strict.projection["owner"]
    assert not set(_MISSING_QUALITY).intersection(source.gaps)
    # The shared obligations declare no audit; ETHOS's own registry declares one in full only.
    missing = not full and profile is not None
    missing_audit = ("proof_dependency_acceptance_audit_missing",) if missing else ()
    assert source.gaps == (*strict.gaps, *missing_audit)
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
    with pytest.raises(ValueError, match="proof_acceptance_purpose_invalid"):
        compile_gate_policy(full=True, acceptance_purpose="publishing")


def test_a_default_floor_still_requires_its_declared_native_audit(tmp_path: Path) -> None:
    """A proof subset cannot acquire an applicability exemption from the audit it declares."""
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="ethos", proof=ProofPolicy(gate_registry="system/repository-gates.toml")
        ),
    )
    selected = compile_gate_policy(
        profile=profile,
        gate_registry_source=repository_registry_path().read_bytes(),
        acceptance_purpose="local-source",
    )
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


def test_native_audit_honors_source_purpose_without_changing_target_floor(
    tmp_path: Path,
) -> None:
    """Purpose interpretation follows the selected closure, including a native audit command."""
    native = Gate(id="native", kind="check", command=("target-check",))
    audit = Gate(
        id="audit",
        kind="check",
        command=("{python}", "-m", "nox", "-s", "vulnerabilities"),
        tool_adapter="vulnerabilities",
    )
    registry = load_gate_registry_declaration().model_copy(
        update={
            "gates": (native, audit),
            "proof_sets": GateProofSets(default=("native",), full=("native", "audit")),
        }
    )
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="target", proof=ProofPolicy(gate_registry="system/gates.toml")
        ),
    )

    def compiled(purpose: AcceptancePurpose) -> ResolvedGatePolicy:
        return compile_gate_policy(
            profile=profile,
            gate_registry_source=tomli_w.dumps(
                registry.model_dump(mode="json", exclude_none=True)
            ).encode(),
            gate_ids=("native", "audit"),
            repository_python="python",
            acceptance_purpose=purpose,
        )

    strict = compiled("repository")
    source = compiled("local-source")
    assert strict.profile is source.profile is profile
    assert source.declaration.proof_sets == strict.declaration.proof_sets
    assert source.gate_ids == strict.gate_ids
    assert source.registry["native"] == strict.registry["native"]
    assert source.registry["audit"].command == (
        *strict.registry["audit"].command,
        "--",
        "--scope",
        "local-development",
    )
    assert source.digest != strict.digest
