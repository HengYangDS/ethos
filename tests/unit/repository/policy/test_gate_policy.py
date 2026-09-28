"""Bind gate identities to selected source, runtime and profile semantics."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import tomli_w

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.gate_policy import resolve_proof_policies
from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import ResolvedGatePolicy
from ethos.repository.policy.gates import canonical_gate_command
from ethos.repository.policy.gates import quality_obligation_gaps
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import RepositoryProfileDeclaration
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import declare_fixture_code_correctness
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import initialize_adopted_fixture
from tests.support.governed_repository import write_script_gate_policy

if TYPE_CHECKING:
    from pathlib import Path

_MISSING_QUALITY = (
    "quality_obligation_unproven:behavior",
    "quality_obligation_unproven:static-analysis",
)


def test_quality_axis_conjoins_scoped_evidence_from_distinct_gates() -> None:
    """Neither one green check nor an out-of-scope report covers every subject."""
    tree = "a" * 40
    reference = "ethos.adapters.gates.code_quality:behavior_report"
    subjects = ["src/app.py", "tools/utility.py"]
    policy = {
        "owner": {
            "quality_floor_version": 2,
            "code_correctness_map": {"behavior": "primary"},
            "quality_subjects": {"behavior": subjects},
        },
        "gates": [
            {
                "id": name,
                "execution_identity": ["provider", reference],
                "execution_mode": "provider",
                "tool_adapter": "ethos",
                "dimensions": ["behavior"],
            }
            for name in ("primary", "additional")
        ],
    }

    def check(name: str, path: str) -> dict[str, object]:
        report = {
            "verdict": "pass",
            "quality_evidence": {
                "axis": "behavior",
                "source_tree": tree,
                "selected_paths": [path],
            },
        }
        return {
            "action_id": name,
            "stdout": json.dumps(
                {"gate": name, "providers": [{"provider": reference, "report": report}]}
            ),
        }

    primary = check("primary", subjects[0])
    additional = check("additional", subjects[1])
    gap = ("quality_obligation_unproven:behavior",)
    assert quality_obligation_gaps(policy, (primary, additional), source_tree=tree) == ()
    assert quality_obligation_gaps(policy, (primary,), source_tree=tree) == gap
    assert quality_obligation_gaps(policy, (additional,), source_tree=tree) == gap
    assert (
        quality_obligation_gaps(
            policy, (primary, check("additional", "other.py")), source_tree=tree
        )
        == gap
    )


def test_quality_axis_rejects_unverified_additional_gate_before_execution(tmp_path: Path) -> None:
    """A claimed supplemental scope cannot become a costly false-green command."""
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="native-quality",
            proof=ProofPolicy(
                code_correctness_gates=("behavior", "additional", "static"),
                code_correctness_map={"behavior": "behavior", "static-analysis": "static"},
                gates=(
                    Gate(
                        id="behavior",
                        kind="test",
                        providers=("ethos.adapters.gates.code_quality:behavior_report",),
                    ),
                    Gate(
                        id="additional",
                        kind="test",
                        command=("python", "-c", "pass"),
                        dimensions=("behavior",),
                    ),
                    Gate(
                        id="static",
                        kind="lint",
                        providers=("ethos.adapters.gates.code_quality:static_report",),
                    ),
                ),
            ),
        ),
    )

    policy = compile_gate_policy(profile=profile, repository_paths=("src/app.py",), full=True)

    assert "quality_gate_verifier_missing:behavior:additional" in policy.gaps


def test_scheduler_hint_does_not_reclassify_product_quality_owner(tmp_path: Path) -> None:
    """Capacity changes bind execution but do not invent an adopter quality floor."""
    packaged = load_gate_registry_declaration()
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="ethos", proof=ProofPolicy(gate_registry="system/gates.toml")
        ),
    )

    def compiled(declaration: GateRegistryDeclaration) -> ResolvedGatePolicy:
        return compile_gate_policy(
            profile=profile,
            gate_registry_source=tomli_w.dumps(
                declaration.model_dump(mode="json", exclude_defaults=True)
            ).encode(),
            repository_python="python",
            repository_paths=("src/example.py",),
            full=True,
        )

    base = compiled(packaged)
    varied = packaged.model_copy(
        update={
            "gates": tuple(
                gate.model_copy(update={"cpu_reservation": 1 if gate.cpu_reservation == 2 else 2})
                if gate.id == "unit-architecture"
                else gate
                for gate in packaged.gates
            )
        }
    )
    capacity = compiled(varied)
    assert capacity.projection["owner"] == base.projection["owner"]
    assert capacity.digest != base.digest

    substantive = packaged.model_copy(
        update={
            "gates": tuple(
                gate.model_copy(update={"command": (*gate.command, "--changed")})
                if gate.id == "unit-architecture"
                else gate
                for gate in packaged.gates
            )
        }
    )
    owner = compiled(substantive).projection["owner"]
    assert isinstance(owner, dict)
    assert owner.get("quality_floor_version") == 2


@pytest.mark.parametrize("floor", ["full", "default"])
def test_gate_policy_binds_committed_sources_and_reports_missing_source(tmp_path, floor) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo, full=True)
    first = dict(resolve_proof_policies(repo, tree_ref=commit_fixture(repo, "policy")))[floor]
    assert first.gate_ids == (("check", "publish") if floor == "full" else ("check",))
    assert first.gaps == _MISSING_QUALITY

    registry = repo / "system/gates.toml"
    registry.write_text(registry.read_text().replace("tools/check.sh", "tools/check-v2.sh"))
    (repo / "tools/check-v2.sh").write_text("#!/bin/sh\nexit 0\n")
    changed = dict(resolve_proof_policies(repo, tree_ref=commit_fixture(repo, "command")))[floor]
    assert changed.digest != first.digest

    (repo / "tools/check-v2.sh").unlink()
    missing = commit_fixture(repo, "missing")
    (repo / "tools/check-v2.sh").write_text("#!/bin/sh\nexit 0\n")
    selected = dict(resolve_proof_policies(repo, tree_ref=missing))[floor]
    assert selected == resolve_gate_policy(repo, tree_ref=missing, full=floor == "full")
    assert selected.gaps == (
        "gate_policy_source_missing:check:tools/check-v2.sh",
        *_MISSING_QUALITY,
    )


def test_nox_gate_binds_repository_sources_and_requires_runtime(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo)
    registry = repo / "system/gates.toml"
    registry.write_text(
        registry.read_text().replace(
            '["tools/check.sh"]',
            '["{python}", "-m", "nox", "-s", "check"]',
        )
    )
    for relative, text in (
        ("noxfile.py", "def check(): pass\n"),
        ("pyproject.toml", "[project]\nname='x'\nversion='0'\n"),
        ("uv.lock", "version=1\n"),
    ):
        (repo / relative).write_text(text)

    missing = commit_fixture(repo, "nox without runtime")
    assert resolve_gate_policy(repo, tree_ref=missing).gaps == (
        "gate_runtime_missing:repository-python",
        *_MISSING_QUALITY,
    )

    runtime = repo / ".venv/bin/python"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("")
    bound = resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "bind nox runtime"))
    assert bound.gaps == _MISSING_QUALITY
    assert {path for path, _digest in bound.sources[0][1]} == {
        "noxfile.py",
        "pyproject.toml",
        "uv.lock",
    }


def test_gate_policy_identity_binds_profile_semantics_and_python_command(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    initialize_adopted_fixture(repo)
    declare_fixture_code_correctness(repo)
    commit_fixture(repo, "declare native quality policy")
    profile = repo / ".ethos/profile.toml"
    head = git(repo, "rev-parse", "HEAD")
    selected = resolve_gate_policy(repo, tree_ref=head, full=True)
    first = selected.digest
    assert first == resolve_gate_policy(repo, tree_ref=head, gate_ids=selected.gate_ids).digest

    profile.write_text(
        profile.read_text().replace(
            'dimensions = ["test", "coverage"]',
            'dimensions = ["test", "coverage", "property"]',
        )
    )
    changed = resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "change dimensions"))
    assert changed.digest != first

    profile.write_text(
        profile.read_text().replace(
            'static-analysis = "sample-static"',
            'static-analysis = "sample-tests"',
        )
    )
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "invalidate map"))

    assert canonical_gate_command(("/one/bin/python3.14", "-m", "tool")) == (
        "python",
        "-m",
        "tool",
    )
    assert canonical_gate_command(("python3.12", "-m", "tool")) != canonical_gate_command(
        ("python3.13", "-m", "tool")
    )


def test_script_discovery_reads_selected_git_object_not_mutable_checkout(tmp_path: Path) -> None:
    """Script role follows Git content at the selected tree or index."""
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo)
    (repo / "notes.txt").write_text("example\n#!/bin/sh\n", encoding="utf-8")
    head = commit_fixture(repo, "declare scripts")
    committed = resolve_gate_policy(repo, tree_ref=head)
    assert "tools/check.sh" in committed.script_paths
    assert "notes.txt" not in committed.script_paths

    script = repo / "tools/check.sh"
    script.write_text("echo changed\n", encoding="utf-8")
    assert resolve_gate_policy(repo, tree_ref=head).script_paths == committed.script_paths
    assert "tools/check.sh" in resolve_gate_policy(repo).script_paths

    git(repo, "add", "tools/check.sh")
    assert "tools/check.sh" not in resolve_gate_policy(repo).script_paths
    assert resolve_gate_policy(repo, tree_ref=head).script_paths == committed.script_paths


def test_carrier_role_projection_reads_selected_git_tree(tmp_path: Path) -> None:
    """A mutable attribute file cannot reinterpret committed carrier roles."""
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo)
    (repo / "main.ts").write_text("export const answer = 42;\n", encoding="utf-8")
    attributes = repo / ".gitattributes"
    attributes.write_text("*.ts ethos-role=code\n", encoding="utf-8")
    head = commit_fixture(repo, "declare carrier role")
    committed = resolve_gate_policy(repo, tree_ref=head)
    assert ("main.ts", "code") in committed.carrier_roles

    attributes.write_text("*.ts ethos-role=docs\n", encoding="utf-8")
    assert resolve_gate_policy(repo, tree_ref=head).carrier_roles == committed.carrier_roles
    assert ("main.ts", "code") in resolve_gate_policy(repo).carrier_roles

    git(repo, "add", ".gitattributes")
    assert ("main.ts", "docs") in resolve_gate_policy(repo).carrier_roles
    assert resolve_gate_policy(repo, tree_ref=head).carrier_roles == committed.carrier_roles

    attributes.write_text("*.ts ethos-role=unknown-value\n", encoding="utf-8")
    git(repo, "add", ".gitattributes")
    with pytest.raises(ValueError, match=r"quality_carrier_role_invalid:main\.ts"):
        resolve_gate_policy(repo)
