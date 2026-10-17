"""Only the product source owns its gate registry without the adopter quality floor."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.repo.gate_policy as gate_policy
from ethos.adapters.repo.gate_policy import resolve_proof_policies
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import ResolvedGatePolicy
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import RepositoryProfileDeclaration
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_script_gate_policy

if TYPE_CHECKING:
    from pathlib import Path

_MISSING_QUALITY = (
    "quality_obligation_unproven:behavior",
    "quality_obligation_unproven:static-analysis",
)


def _without_gate(declaration: GateRegistryDeclaration, gate_id: str) -> GateRegistryDeclaration:
    return declaration.model_copy(
        update={
            "proof_sets": declaration.proof_sets.model_copy(
                update={
                    floor: tuple(
                        item for item in getattr(declaration.proof_sets, floor) if item != gate_id
                    )
                    for floor in ("default", "full")
                }
            ),
            "gates": tuple(
                gate.model_copy(
                    update={
                        "depends_on": tuple(item for item in gate.depends_on if item != gate_id)
                    }
                )
                for gate in declaration.gates
                if gate.id != gate_id
            ),
        }
    )


@pytest.mark.parametrize("source", ["product", "foreign"])
def test_only_the_product_source_owns_its_registry_without_the_quality_floor(
    tmp_path: Path, source: str
) -> None:
    """Shared product history, never equality with a running copy, decides the quality owner."""
    packaged = load_gate_registry_declaration()
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="ethos", proof=ProofPolicy(gate_registry="system/gates.toml")
        ),
    )

    def compiled(
        declaration: GateRegistryDeclaration, *, local_source: bool = False
    ) -> ResolvedGatePolicy:
        return compile_gate_policy(
            profile=profile,
            gate_registry_source=tomli_w.dumps(
                declaration.model_dump(mode="json", exclude_defaults=True)
            ).encode(),
            repository_python="python",
            repository_paths=("src/example.py",),
            full=True,
            acceptance_purpose="local-source" if local_source else "repository",
            product_source=source == "product",
        )

    def changed(field: str, value: object) -> GateRegistryDeclaration:
        return packaged.model_copy(
            update={
                "gates": tuple(
                    gate.model_copy(update={field: value})
                    if gate.id == "unit-architecture"
                    else gate
                    for gate in packaged.gates
                )
            }
        )

    base = compiled(packaged)
    scoped = compiled(packaged, local_source=True)
    assert scoped.projection["owner"] == base.projection["owner"]
    assert scoped.digest != base.digest
    assert scoped.gaps == base.gaps
    owner = base.projection["owner"]
    assert isinstance(owner, dict)
    if source == "product":
        assert sorted(owner) == ["id", "kind", "path", "schema_version", "source_refs"]
    else:
        assert owner.get("quality_floor_version") == 2
    unit = packaged.registry()["unit-architecture"]
    for candidate in (
        changed("cpu_reservation", 1 if unit.cpu_reservation == 2 else 2),
        changed("command", (*unit.command, "--changed")),
        _without_gate(packaged, "python-size"),
    ):
        policy = compiled(candidate)
        assert policy.projection["owner"] == owner
        assert policy.digest != base.digest


def _floor_owned(repo: Path, ref: str) -> bool:
    policy = dict(resolve_proof_policies(repo, tree_ref=ref))["full"]
    owner = policy.projection["owner"]
    assert isinstance(owner, dict)
    return owner.get("quality_floor_version") == 2 and set(_MISSING_QUALITY) <= set(policy.gaps)


def test_product_registry_is_recognized_by_history_shared_with_the_running_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rewritten or edited product keeps its owner; foreign history and paths keep the floor."""
    repo = init_git_repo(tmp_path / "repo")
    root = git(repo, "rev-parse", "HEAD")
    write_script_gate_policy(repo, full=True)
    build = commit_fixture(repo, "declare the product registry")
    registry = repo / "system/gates.toml"
    registry.write_text(
        registry.read_text().replace('command = ["publish"]', 'command = ["publish", "--all"]')
    )
    edited = commit_fixture(repo, "edit the product registry")
    git(repo, "checkout", "-q", "-b", "rewritten", root)
    write_script_gate_policy(repo, full=True)
    rewritten = commit_fixture(repo, "rewrite the history after the root")
    git(repo, "checkout", "-q", "--orphan", "unrelated")
    unrelated = commit_fixture(repo, "start an unrelated history")
    git(repo, "checkout", "-q", "-b", "moved", rewritten)
    profile = repo / ".ethos/profile.toml"
    profile.write_text(profile.read_text().replace("system/gates.toml", ".ethos/gates.toml"))
    git(repo, "mv", "system/gates.toml", ".ethos/gates.toml")
    moved = commit_fixture(repo, "declare the registry elsewhere")
    monkeypatch.setattr(gate_policy, "invoking_source_commit", lambda: build)

    assert {
        ref: _floor_owned(repo, ref) for ref in (build, edited, rewritten, unrelated, moved)
    } == {
        build: False,
        edited: False,
        rewritten: False,
        unrelated: True,
        moved: True,
    }
    monkeypatch.setattr(gate_policy, "invoking_source_commit", lambda: "0" * 40)
    assert _floor_owned(repo, build)
