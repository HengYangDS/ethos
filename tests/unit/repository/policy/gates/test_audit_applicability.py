"""Bind native audit applicability to committed declarations and execution purpose."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.repo.gate_policy as gate_policy
from ethos.adapters.repo.dependency_acceptance import dependency_acceptance_gaps
from ethos.contracts.gates import Gate
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import RepositoryProfileDeclaration
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_script_gate_policy

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("registry_owned", [False, True])
def test_source_acceptance_preserves_floors_and_binds_native_audit(
    tmp_path: Path, *, registry_owned: bool
) -> None:
    """Execution purpose never reclassifies the original declaration's quality owner."""
    declaration = load_gate_registry_declaration()
    profile = (
        RepositoryProfile(
            root=tmp_path,
            exists=True,
            declaration=RepositoryProfileDeclaration(
                profile_id="product",
                proof=ProofPolicy(gate_registry="system/gates.toml"),
            ),
        )
        if registry_owned
        else None
    )
    registry_source = tomli_w.dumps(declaration.model_dump(mode="json", exclude_none=True)).encode()
    strict = compile_gate_policy(
        full=True,
        profile=profile,
        gate_registry_source=registry_source,
        repository_python="python",
        repository_paths=("src/main.py",),
    )
    source = compile_gate_policy(
        full=True,
        profile=profile,
        gate_registry_source=registry_source,
        repository_python="python",
        repository_paths=("src/main.py",),
        acceptance_purpose="local-source",
    )
    assert source.declaration == strict.declaration
    assert source.projection["owner"] == strict.projection["owner"]
    assert source.gaps == strict.gaps
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
        compile_gate_policy(full=True, acceptance_purpose="publishing")


def test_imported_native_audit_honors_source_purpose_without_changing_target_floor(
    tmp_path: Path,
) -> None:
    """Purpose interpretation follows selected closure, including newly imported commands."""
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="target",
            proof=ProofPolicy(
                code_correctness_gates=("native",),
                code_correctness_map={"behavior": "native", "static-analysis": "native"},
                gates=(Gate(id="native", kind="check", command=("target-check",)),),
            ),
        ),
    )
    requested = ("native", "dependency-vulnerabilities")
    strict = compile_gate_policy(
        profile=profile,
        gate_ids=requested,
        product_gate_ids=("dependency-vulnerabilities",),
        repository_python="python",
    )
    source = compile_gate_policy(
        profile=profile,
        gate_ids=requested,
        product_gate_ids=("dependency-vulnerabilities",),
        repository_python="python",
        acceptance_purpose="local-source",
    )
    assert strict.profile is source.profile is profile
    assert source.declaration.proof_sets == strict.declaration.proof_sets
    assert source.gate_ids == strict.gate_ids
    assert source.registry["native"] == strict.registry["native"]
    source_gate = next(gate for gate in source.gates if gate.id == "dependency-vulnerabilities")
    strict_gate = next(gate for gate in strict.gates if gate.id == "dependency-vulnerabilities")
    assert source_gate.command == (
        *strict_gate.command,
        "--",
        "--scope",
        "local-development",
    )
    assert source.digest != strict.digest


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


@pytest.mark.parametrize("canonical", [False, True], ids=["native", "canonical"])
@pytest.mark.parametrize("carrier", ["registry", "profile"])
def test_audit_applicability_reads_only_the_committed_declaration(
    tmp_path: Path, monkeypatch, carrier: str, *, canonical: bool
) -> None:
    """A partial proof keeps the full audit obligation without expanding source bindings."""
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo, full=True)
    registry = repo / "system/gates.toml"
    declaration = tomllib.loads(registry.read_text())
    declaration["proof_sets"]["full"].append("audit")
    declaration["gates"].append(
        {
            "id": "audit",
            "kind": "lint",
            "command": ["{python}", "-m", "nox", "-s", "vulnerabilities"],
            "tool_adapter": "vulnerabilities" if canonical else "repository-native",
            "depends_on": ["check"],
        }
    )
    registry.write_text(tomli_w.dumps(declaration))
    if carrier == "profile":
        registry = repo / ".ethos/profile.toml"
        registry.write_text(
            tomli_w.dumps(
                {
                    "profile_id": "policy-test",
                    "proof": {
                        "code_correctness_gates": [gate["id"] for gate in declaration["gates"]],
                        "code_correctness_map": {"behavior": "check", "static-analysis": "audit"},
                        "gates": declaration["gates"],
                    },
                }
            )
        )
    head = commit_fixture(repo, "declare audit ownership")

    def source_binding_forbidden(*_args, **_options):
        pytest.fail("audit applicability must not expand the repository source binding")

    monkeypatch.setattr(gate_policy, "_repository_paths", source_binding_forbidden)
    monkeypatch.setattr(gate_policy, "source_paths_for_gates", source_binding_forbidden)
    monkeypatch.setattr(gate_policy, "compile_gate_policy", source_binding_forbidden)
    policy = {"gates": ({"id": "check", "command": ("tools/check.sh",)},)}
    expected = (
        ["proof_dependency_acceptance_audit_missing"] if canonical and carrier == "registry" else []
    )
    assert (
        dependency_acceptance_gaps(repo, head, policy, (), acceptance_purpose="local-source")
        == expected
    )

    registry.write_text("uncommitted invalid registry")
    assert (
        dependency_acceptance_gaps(repo, head, policy, (), acceptance_purpose="local-source")
        == expected
    )
    invalid = commit_fixture(repo, "invalidate audit declaration")
    assert dependency_acceptance_gaps(
        repo, invalid, policy, (), acceptance_purpose="local-source"
    ) == ["proof_dependency_acceptance_audit_missing"]


@pytest.mark.parametrize("profile", ["", "invalid profile"], ids=["absent", "invalid"])
def test_audit_applicability_never_exempts_an_absent_or_invalid_profile(
    tmp_path: Path, profile: str
) -> None:
    """Only a valid committed native declaration can select its own audit owner."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "README.md").write_text("Audit applicability fixture\n")
    if profile:
        path = repo / ".ethos/profile.toml"
        path.parent.mkdir()
        path.write_text(profile)
    head = commit_fixture(repo, "capture profile state")
    assert dependency_acceptance_gaps(
        repo, head, {"gates": ()}, (), acceptance_purpose="local-source"
    ) == ["proof_dependency_acceptance_audit_missing"]
