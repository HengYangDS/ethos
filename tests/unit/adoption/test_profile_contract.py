"""Validate immutable adopter profiles without fallback from invalid selected state."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.adapters.admission.patch_admission import patch_admission
from ethos.adapters.admission.patch_admission import staged_artifact_admission
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.repository.adoption.fleet import inspect_adopter
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_root
from ethos.repository.profile import render_repository_profile
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import declare_fixture_code_correctness
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane
from tests.support.literal_cases import literal_case


def _write_profile(root: Path, text: str) -> Path:
    profile = root / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(text, encoding="utf-8")
    return profile


def _assert_invalid_profile(root: Path, text: str) -> None:
    _write_profile(root, text)
    assert load_repository_profile(root).state == "invalid"


def _profile_prewrite(
    root: Path, *, patch: Path | None, paths: tuple[str, ...] = (".ethos/profile.toml",)
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    arguments = [sys.executable, "-B", "-m", "ethos.cli", "lane", "prewrite", *paths]
    arguments.extend(
        ("--root", root.as_posix(), "--editor-root", root.as_posix(), "--require-editor-root")
    )
    if patch is not None:
        arguments.extend(("--patch", patch.as_posix()))
    arguments.append("--json")
    completed = subprocess.run(
        arguments,
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")},
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.stdout, completed.stderr
    return completed, json.loads(completed.stdout)


def test_profile_contract_is_strict_frozen_and_deterministic(tmp_path: Path) -> None:
    declaration = RepositoryProfileDeclaration.bootstrap('sample<repo&"')

    rendered = render_repository_profile(declaration)

    assert rendered == 'profile_id = "sample<repo&\\""\n'
    assert declaration.openspec is None
    with pytest.raises(ValidationError):
        declaration.profile_id = "mutable"
    with pytest.raises(TypeError):
        declaration.proof.code_correctness_map["behavior"] = "mutable"
    with pytest.raises(ValidationError):
        RepositoryProfileDeclaration.model_validate(
            {
                "profile_id": "sample",
                "extra": True,
            }
        )

    _write_profile(tmp_path, rendered)
    loaded = load_repository_profile(tmp_path)

    assert loaded.state == "valid"
    assert loaded.declaration is not None
    assert loaded.declaration.profile_id == 'sample<repo&"'
    assert loaded.declaration.openspec is None


@pytest.mark.parametrize(
    "fields",
    [
        {"roots": {"durable_evidence": "evidence"}},
        {"evidence": {"durable_roots": ["evidence"]}},
    ],
)
def test_profile_cannot_select_current_proof_by_directory(fields) -> None:
    """Retired directory declarations cannot become a parallel proof selector."""
    with pytest.raises(ValidationError):
        RepositoryProfileDeclaration.model_validate({"profile_id": "sample", **fields})


@pytest.mark.parametrize(
    "proof",
    literal_case(
        "adoption.test_profile_contract:parametrize:test_profile_rejects_retired_or_incomplete_proof_owners:0"
    ),
)
def test_profile_rejects_retired_or_incomplete_proof_owners(tmp_path: Path, proof: str) -> None:
    _assert_invalid_profile(tmp_path, 'profile_id = "sample"\n\n[proof]\n' + proof)


def test_adopter_profile_is_identical_from_worktree_and_commit(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    _write_profile(tmp_path, 'profile_id = "native-check-adopter"\n')
    declare_fixture_code_correctness(tmp_path)
    git(tmp_path, "add", ".ethos/profile.toml")
    git(tmp_path, "commit", "-q", "-m", "profile")
    head = git(tmp_path, "rev-parse", "HEAD")

    worktree = resolve_gate_policy(tmp_path)
    committed = resolve_gate_policy(tmp_path, tree_ref=head)

    assert worktree.profile is not None
    assert worktree.profile.state == "valid"
    assert worktree.digest == committed.digest
    assert set(worktree.gate_ids) == {"sample-tests", "sample-static"}


def test_profile_gate_rejects_retired_registry_projection_field(tmp_path: Path) -> None:
    _assert_invalid_profile(
        tmp_path,
        'profile_id = "sample"\n\n'
        "[proof]\n"
        'code_correctness_gates = ["tests"]\n\n'
        "[[proof.gates]]\n"
        'id = "tests"\n'
        'kind = "test"\n'
        'command = ["pytest"]\n'
        'registries = ["quality"]\n',
    )


@pytest.mark.parametrize(
    "text",
    literal_case(
        "adoption.test_profile_contract:parametrize:test_profile_contract_rejects_incomplete_or_undeclared_shape:1"
    ),
)
def test_profile_contract_rejects_incomplete_or_undeclared_shape(tmp_path: Path, text: str) -> None:
    _assert_invalid_profile(tmp_path, text)


def test_profile_contract_rejects_non_string_paths() -> None:
    with pytest.raises(TypeError, match="repository path must be a string"):
        RepositoryProfileDeclaration.model_validate(
            {
                "profile_id": "sample",
                "openspec": {"material_paths": ["openspec/**"]},
                "roots": {"docs": 1},
            }
        )


def test_profile_contract_rejects_complete_former_envelope(tmp_path: Path) -> None:
    _assert_invalid_profile(
        tmp_path,
        "schema_version = 1\n"
        'profile_id = "sample"\n'
        'profile_version = "1"\n'
        'ethos_contract_version = "1"\n\n'
        "[repository]\n"
        'kind = "documentation"\n'
        'root_subject = "sample"\n\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n',
    )


def test_current_profile_rejects_root_rules_workaround(tmp_path: Path) -> None:
    _assert_invalid_profile(
        tmp_path,
        'profile_id = "sample"\n\n'
        "[roots]\n"
        'rules = "."\n\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n',
    )


def test_profile_rejects_open_spec_root_relocation(tmp_path: Path) -> None:
    """The native OpenSpec CLI cannot consume a renamed repository root."""
    _assert_invalid_profile(
        tmp_path,
        'profile_id = "sample"\n\n[roots]\nopenspec = "contracts"\n',
    )


def test_adopter_inspection_does_not_accept_a_relocated_open_spec_root(
    tmp_path: Path,
) -> None:
    """Capability discovery must agree with the native OpenSpec reader."""
    relocated = tmp_path / "contracts"
    (relocated / "specs").mkdir(parents=True)
    (relocated / "config.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    _write_profile(
        tmp_path,
        'profile_id = "sample"\n\n[roots]\nopenspec = "contracts"\n',
    )

    report = inspect_adopter(tmp_path)

    assert report["verdict"] == "block"
    assert report["adopter"]["capabilities"]["openspec"] is False


def test_profile_includes_declared_normative_sources_without_root_escape(tmp_path: Path) -> None:
    _write_profile(tmp_path, 'profile_id = "sample"\n\nnormative_sources = ["guidelines.md"]\n')

    profile = load_repository_profile(tmp_path)
    assert profile.declaration is not None
    assert profile.declaration.normative_sources == ("guidelines.md",)
    assert profile_root(tmp_path, "docs") == tmp_path / "docs"


def test_profile_loader_rejects_unreadable_profile(tmp_path: Path, monkeypatch) -> None:
    profile = _write_profile(tmp_path, "profile_id = 'sample'\n")
    original = Path.read_text

    def unreadable(path: Path, *args, **kwargs) -> str:
        if path == profile.resolve():
            raise OSError
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)

    assert load_repository_profile(tmp_path).state == "invalid"


def test_invalid_profile_never_falls_back_to_default_roots(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "profile_id = 'sample'\n[roots]\ndocs = '../docs'\n",
    )

    loaded = load_repository_profile(tmp_path)

    assert loaded.state == "invalid"
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        profile_root(tmp_path, "docs")


def test_profile_loader_never_falls_back_from_an_invalid_tree_ref(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    _write_profile(tmp_path, "profile_id = 'working-tree'\n")

    with pytest.raises(ValueError, match="repository_tree_ref_invalid"):
        load_committed_repository_profile(tmp_path, "deadbeef" * 5)


def test_owned_lane_can_admit_exact_legacy_profile_repair_without_applying_it(
    tmp_path: Path,
) -> None:
    """A strict repair path must exist without accepting the former profile as authority."""
    fixture = prepared_work_lane(tmp_path)
    root = fixture.worktree
    profile = root / ".ethos/profile.toml"
    valid = profile.read_text(encoding="utf-8")
    invalid = "schema_version = 1\n" + valid
    profile.write_text(invalid, encoding="utf-8")
    commit_fixture(root, "record former profile envelope")
    profile.write_text(valid, encoding="utf-8")
    patch = tmp_path / "profile-repair.patch"
    patch.write_text(git(root, "diff", "--no-ext-diff") + "\n", encoding="utf-8")
    profile.write_text(invalid, encoding="utf-8")
    patch_report = patch_admission(
        root=root,
        requested_paths=(".ethos/profile.toml",),
        baseline_head=git(root, "rev-parse", "HEAD"),
        patch=patch.read_text(encoding="utf-8"),
    )
    assert patch_report["verdict"] == "pass", patch_report

    completed, report = _profile_prewrite(root, patch=patch)

    assert completed.returncode == 0, report
    assert report["verdict"] == "pass", report
    data = report["data"]
    assert isinstance(data, dict)
    patch_result = data["patch_admission"]
    assert isinstance(patch_result, dict)
    assert patch_result["paths"] == [".ethos/profile.toml"]
    official = data["openspec"]
    assert isinstance(official, dict)
    assert official["verdict"] == "unknown"
    assert profile.read_text(encoding="utf-8") == invalid


@pytest.mark.parametrize(
    "case",
    [
        "no_patch",
        "invalid_postimage",
        "changed_identity",
        "extra_path",
        "accepted_root",
        "missing_actor",
    ],
)
def test_invalid_profile_repair_cannot_bypass_exact_owned_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    fixture = prepared_work_lane(tmp_path)
    root = fixture.repository if case == "accepted_root" else fixture.worktree
    profile = root / ".ethos/profile.toml"
    valid = profile.read_text(encoding="utf-8")
    invalid = "schema_version = 1\n" + valid
    profile.write_text(invalid, encoding="utf-8")
    commit_fixture(root, "record former profile envelope")
    candidate = (
        "schema_version = 2\n" + valid
        if case == "invalid_postimage"
        else valid.replace('profile_id = "', 'profile_id = "switched-', 1)
        if case == "changed_identity"
        else valid
    )
    profile.write_text(candidate, encoding="utf-8")
    paths = [".ethos/profile.toml"]
    other = root / "README.md"
    original = other.read_text(encoding="utf-8")
    if case == "extra_path":
        other.write_text(original + "\nExtra content.\n", encoding="utf-8")
        paths.append("README.md")
    patch = tmp_path / "profile-repair.patch"
    patch.write_text(git(root, "diff", "--no-ext-diff") + "\n", encoding="utf-8")
    profile.write_text(invalid, encoding="utf-8")
    other.write_text(original, encoding="utf-8")
    if case == "missing_actor":
        monkeypatch.delenv("ETHOS_ACTOR")

    completed, report = _profile_prewrite(
        root, patch=None if case == "no_patch" else patch, paths=tuple(paths)
    )

    assert completed.returncode != 0, report
    assert report["verdict"] == "block", report
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert "repository_profile_invalid:.ethos/profile.toml" in gaps
    if case == "missing_actor":
        data = report["data"]
        assert isinstance(data, dict)
        authority = data["mutation_authority"]
        assert isinstance(authority, dict)
        assert authority["verdict"] == "block", report
    else:
        reason = {
            "no_patch": "profile_repair_exact_patch_required",
            "invalid_postimage": "repository_profile_invalid:.ethos/profile.toml",
            "changed_identity": "profile_repair_identity_changed",
            "extra_path": "profile_repair_requires_single_profile_path",
            "accepted_root": "profile_repair_requires_work_lane",
        }[case]
        assert reason in gaps, report
    assert profile.read_text(encoding="utf-8") == invalid


def test_staged_invalid_profile_cannot_hide_behind_valid_working_bytes(tmp_path: Path) -> None:
    fixture = prepared_work_lane(tmp_path)
    root = fixture.worktree
    profile = root / ".ethos/profile.toml"
    valid = profile.read_text(encoding="utf-8")
    profile.write_text("schema_version = 1\n" + valid, encoding="utf-8")
    git(root, "add", ".ethos/profile.toml")
    profile.write_text(valid, encoding="utf-8")

    report = staged_artifact_admission(root, git(root, "rev-parse", "HEAD"))

    assert report["verdict"] == "block", report
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert "repository_profile_invalid:.ethos/profile.toml" in gaps
    admission = prewrite_guard(root=root, paths=[profile], editor_root=root, staged=True)
    assert admission["verdict"] == "block", admission
    admission_gaps = admission["required_gaps"]
    assert isinstance(admission_gaps, list)
    assert "repository_profile_invalid:.ethos/profile.toml" in admission_gaps


def test_valid_profile_cannot_stage_an_invalid_replacement(tmp_path: Path) -> None:
    fixture = prepared_work_lane(tmp_path)
    root = fixture.worktree
    profile = root / ".ethos/profile.toml"
    valid = profile.read_text(encoding="utf-8")
    profile.write_text("schema_version = 1\n" + valid, encoding="utf-8")
    patch = tmp_path / "invalid-profile.patch"
    patch.write_text(git(root, "diff", "--no-ext-diff") + "\n", encoding="utf-8")
    profile.write_text(valid, encoding="utf-8")

    completed, report = _profile_prewrite(root, patch=patch)

    assert completed.returncode != 0, report
    assert report["verdict"] == "block", report
    data = report["data"]
    assert isinstance(data, dict)
    patch_result = data["patch_admission"]
    assert isinstance(patch_result, dict)
    assert patch_result["reason"] == "repository_profile_invalid:.ethos/profile.toml"
