"""Bind gate identities to selected source, runtime and profile semantics."""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.repo.gate_policy as gate_policy
from ethos.adapters.repo.dependency_acceptance import dependency_acceptance_gaps
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.gate_policy import resolve_proof_policies
from ethos.contracts.gates import Gate
from ethos.repository.policy.gates import canonical_gate_command
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.policy.quality.obligations import quality_obligation_gaps
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


def test_source_acceptance_preserves_floors_and_binds_native_audit() -> None:
    """One explicit purpose changes the audit command, never the required gate set."""
    strict = compile_gate_policy(full=True)
    source = compile_gate_policy(full=True, acceptance_purpose="local-source")
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


@pytest.mark.parametrize(
    ("entry", "package_source"),
    [
        ("tools/check.py", ""),
        ("src/tools/check.py", "raise RuntimeError()\n"),
        ("src/tools/check/__main__.py", "raise RuntimeError()\n"),
    ],
)
def test_python_module_policy_binds_committed_entry_and_parent_packages(
    tmp_path: Path,
    entry: str,
    package_source: str,
) -> None:
    """Module resolution consumes observed Git paths, never imports mutable candidate code."""
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo)
    registry = repo / "system/gates.toml"
    registry.write_text(
        registry.read_text().replace(
            '["tools/check.sh"]',
            '["{python}", "-B", "-m", "tools.check"]',
        )
    )
    source = repo / entry
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("raise RuntimeError('must not execute')\n")
    prefix = "src/" if entry.startswith("src/") else ""
    package = repo / f"{prefix}tools/__init__.py"
    package.write_text(package_source)
    missing = commit_fixture(repo, "module without runtime")
    assert (
        "gate_runtime_missing:repository-python" in resolve_gate_policy(repo, tree_ref=missing).gaps
    )
    interpreter = repo / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("")
    bound = resolve_gate_policy(repo, tree_ref=missing)
    assert bound.gaps == _MISSING_QUALITY
    assert {path for path, _digest in bound.sources[0][1]} == {entry, f"{prefix}tools/__init__.py"}
    source.write_text("uncommitted mutable replacement\n")
    assert resolve_gate_policy(repo, tree_ref=missing).digest == bound.digest
    changed = resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "module changed"))
    assert changed.digest != bound.digest
    source.unlink()
    deleted = commit_fixture(repo, "module deleted")
    source.write_text("untracked replacement\n")
    assert any(
        gap.startswith("gate_policy_source_missing:check:")
        for gap in resolve_gate_policy(repo, tree_ref=deleted).gaps
    )


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
    shared_gate = resolve_gate_policy(repo, tree_ref=commit_fixture(repo, "share gate"))
    assert shared_gate.digest != changed.digest
    owner = shared_gate.projection["owner"]
    assert isinstance(owner, dict)
    assert owner["code_correctness_map"] == {
        "behavior": "sample-tests",
        "static-analysis": "sample-tests",
    }

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


def test_quality_observation_retains_committed_roles_and_explicit_test_identity(
    tmp_path: Path,
) -> None:
    """Policy compilation and native observation share the same committed roles."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "test_entry.js").write_text("export const answer = 42;\n")
    (repo / ".gitattributes").write_text("test_entry.js ethos-role=code\n")
    head = commit_fixture(repo, "declare production subject")
    tree, (subject,) = observe_quality_subjects(repo, language="javascript")
    assert tree == git(repo, "rev-parse", f"{head}^{{tree}}")
    assert subject.role == "code"
    assert not subject.is_test
    assert subject.requires_behavior
    (repo / ".gitattributes").write_text("test_entry.js ethos-role=test\n")
    assert observe_quality_subjects(repo)[1] == (subject,)


def test_rootless_policy_compiles_only_the_product_declaration() -> None:
    """Without a repository, the product registry compiles without observing materials."""
    assert resolve_gate_policy(full=True) == compile_gate_policy(full=True)


@pytest.mark.parametrize("fault", ["profile", "tree"])
def test_quality_subjects_bind_one_valid_committed_tree(tmp_path: Path, fault: str) -> None:
    """An invalid committed profile or another expected tree never yields quality subjects."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "answer.py").write_text("VALUE = 42\n")
    if fault == "profile":
        (repo / ".ethos").mkdir()
        (repo / ".ethos/profile.toml").write_text("profile_id = 1\n")
    commit_fixture(repo, "record source")
    message = "repository_profile_invalid" if fault == "profile" else "code_source_changed"
    with pytest.raises(ValueError, match=message):
        observe_quality_subjects(repo, expected_tree="0" * 40 if fault == "tree" else "")
