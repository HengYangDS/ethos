"""Profile repair is admitted through one exact owned public mutation boundary."""

from __future__ import annotations

import json
from difflib import unified_diff
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.patch_admission import patch_admission
from ethos.adapters.admission.patch_admission import staged_artifact_admission
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import render_repository_profile
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane

if TYPE_CHECKING:
    import subprocess
    from pathlib import Path


def _profile_prewrite(
    root: Path, *, patch: Path | None, paths: tuple[str, ...] = (".ethos/profile.toml",)
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    """Use the original public CLI executor with an explicit governed repository."""
    arguments = ["lane", "prewrite", *paths]
    arguments.extend(
        ("--root", root.as_posix(), "--editor-root", root.as_posix(), "--require-editor-root")
    )
    if patch is not None:
        arguments.extend(("--patch", patch.as_posix()))
    arguments.append("--json")
    completed = run_ethos_raw(*arguments, cwd=root)
    assert completed.stdout, completed.stderr
    return completed, json.loads(completed.stdout)


@pytest.mark.parametrize("rejection", [None, "scope", "strict-spec", "supporting-template"])
@pytest.mark.parametrize("placement", ["capability", "specs_root", "both"])
def test_exact_metadata_profile_repair_preserves_other_policy(
    tmp_path: Path, placement: str, rejection: str | None
) -> None:
    """Resolve only native metadata bindings, never unrelated source or proof obligations."""
    fixture = prepared_work_lane(tmp_path)
    root = fixture.worktree
    profile = root / ".ethos/profile.toml"
    original = profile.read_text()
    parsed = load_repository_profile(root).declaration.model_dump(mode="json")
    metadata_paths = []
    if placement in {"capability", "both"}:
        metadata_paths.append(root / "openspec/specs/contracts/capability.toml")
        parsed["openspec"]["capability_metadata"] = [
            {"file_name": "capability.toml", "authority_ref": "openspec/specs/contracts/spec.md"}
        ]
    if placement in {"specs_root", "both"}:
        metadata_paths.append(root / "openspec/specs/families.toml")
        parsed["openspec"]["specs_root_metadata"] = [
            {"file_name": "families.toml", "authority_ref": "openspec/specs/contracts/spec.md"}
        ]
    for metadata in metadata_paths:
        metadata.write_text('family = "contracts"\n')
    if rejection == "scope":
        parsed["openspec"]["material_paths"] = [".ethos/**"]
    if rejection == "strict-spec":
        spec = root / "openspec/specs/contracts/spec.md"
        spec.write_text(spec.read_text().replace("SHALL", "can"))
    if rejection == "supporting-template":
        (root / "openspec/specs/template.md").write_text("# Supporting template\n")
    replacement = render_repository_profile(RepositoryProfileDeclaration.model_validate(parsed))
    patch = tmp_path / "metadata-binding.patch"
    patch.write_text(
        "diff --git a/.ethos/profile.toml b/.ethos/profile.toml\n"
        + "".join(
            unified_diff(
                original.splitlines(keepends=True),
                replacement.splitlines(keepends=True),
                fromfile="a/.ethos/profile.toml",
                tofile="b/.ethos/profile.toml",
            )
        )
    )

    completed, report = _profile_prewrite(root, patch=patch)

    accepted = rejection != "scope"
    assert (report["verdict"] == "pass") is accepted, json.dumps(report, indent=2)
    assert (completed.returncode == 0) is accepted, report
    assert profile.read_text() == original
    assert all(metadata.read_text() == 'family = "contracts"\n' for metadata in metadata_paths)
    if rejection in {"strict-spec", "supporting-template"}:
        profile.write_text(replacement)
        completed, remaining = _profile_prewrite(root, patch=None)
        assert completed.returncode != 0, remaining
        assert remaining["verdict"] == "block", remaining
        prefix = (
            "openspec_validation_failed:spec:"
            if rejection == "strict-spec"
            else "openspec_specs_root_entry_unexpected:"
        )
        assert remaining["data"]["openspec"]["verdict"] == "block", remaining
        assert any(
            gap.startswith(prefix) for gap in remaining["data"]["openspec"]["required_gaps"]
        ), remaining


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
        "delete_profile",
        "identity_unavailable",
    ],
)
def test_invalid_profile_repair_cannot_bypass_exact_owned_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    fixture = prepared_work_lane(tmp_path)
    root = fixture.repository if case == "accepted_root" else fixture.worktree
    profile = root / ".ethos/profile.toml"
    valid = profile.read_text(encoding="utf-8")
    invalid = "schema_version = 1\n" + (
        "".join(
            line for line in valid.splitlines(keepends=True) if not line.startswith("profile_id = ")
        )
        if case == "identity_unavailable"
        else valid
    )
    profile.write_text(invalid, encoding="utf-8")
    commit_fixture(root, "record former profile envelope")
    candidate = (
        "schema_version = 2\n" + valid
        if case == "invalid_postimage"
        else valid.replace('profile_id = "', 'profile_id = "switched-', 1)
        if case == "changed_identity"
        else valid
    )
    if case == "delete_profile":
        profile.unlink()
    else:
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
            "delete_profile": "profile_repair_valid_postimage_required",
            "identity_unavailable": "profile_repair_identity_unavailable",
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
