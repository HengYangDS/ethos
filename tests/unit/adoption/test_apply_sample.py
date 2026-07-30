from __future__ import annotations

import os
from pathlib import Path

import pytest

from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.gates import resolve_gate_policy
from ethos.repository.profile import load_repository_profile
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

ROOT = Path(__file__).resolve().parents[3]


def test_adopt_apply_writes_profile_and_repository_commitment(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, apply=True)

    profile = load_repository_profile(tmp_path)
    assert result["applied"] is True
    assert result["planned_files"] == [".ethos/profile.toml", ".ethos/commitment.toml"]
    assert profile.exists
    assert profile.state == "valid"
    assert profile.declaration is not None
    assert profile.declaration.profile_id == tmp_path.name
    assert profile.declaration.commitment == ".ethos/commitment.toml"
    assert profile.declaration.openspec is None
    assert resolve_gate_policy(tmp_path).gate_ids == ()
    assert resolve_gate_policy(tmp_path).registry == {}
    assert sorted(path.as_posix() for path in tmp_path.rglob("*") if path.is_file()) == [
        (tmp_path / ".ethos/commitment.toml").as_posix(),
        (tmp_path / ".ethos/profile.toml").as_posix(),
    ]
    assert 'id = "repository:' in (tmp_path / ".ethos/commitment.toml").read_text()


def test_declared_local_gate_registry_preserves_self_governance_floor() -> None:
    profile = load_repository_profile(ROOT)

    assert profile.state == "valid"
    assert profile.declaration is not None
    assert profile.declaration.proof.gate_registry == "system/gates.toml"
    assert "unit-architecture" in resolve_gate_policy(ROOT).gate_ids


def test_profile_native_gate_owner_replaces_packaged_gates(tmp_path: Path) -> None:
    adoption_plan(tmp_path, apply=True)
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.write_text(
        profile.read_text(encoding="utf-8")
        + """

[proof]
required_gates = ["sample-tests", "sample-static"]

[proof.code_axes]
behavior = "sample-tests"
static-analysis = "sample-static"

[[proof.gates]]
id = "sample-tests"
kind = "test"
command = ["custom", "tests"]
dimensions = ["behavior"]
evidence_class = "proof"
trust_bearing = true

[[proof.gates]]
id = "sample-static"
kind = "typing"
command = ["custom", "types"]
dimensions = ["static-analysis"]
evidence_class = "contract"
trust_bearing = true
""",
        encoding="utf-8",
    )

    assert set(resolve_gate_policy(tmp_path).registry) == {"sample-tests", "sample-static"}


def test_dry_run_plan_can_be_applied_without_changing_identity(tmp_path: Path) -> None:
    plan = adoption_plan(tmp_path)
    result = adoption_plan(
        tmp_path,
        apply=True,
        repository_id=plan["repository_id"],
        expect_plan_digest=plan["plan_digest"],
    )

    assert result["repository_id"] == plan["repository_id"]
    assert result["plan_digest"] == plan["plan_digest"]
    assert load_repository_commitment(tmp_path).id == plan["repository_id"]


def test_apply_rejects_a_plan_digest_that_was_not_reviewed(tmp_path: Path) -> None:
    result = adoption_plan(
        tmp_path,
        apply=True,
        repository_id="repository:reviewed",
        expect_plan_digest="0" * 64,
    )

    assert result["applied"] is False
    assert result["required_gaps"] == ["adoption_plan_digest_mismatch"]
    assert not (tmp_path / ".ethos").exists()


def test_adoption_repository_identity_does_not_depend_on_checkout_path(tmp_path: Path) -> None:
    first = init_git_repo(tmp_path / "first")
    adoption_plan(first, apply=True)
    git(first, "add", ".")
    git(first, "commit", "-m", "adopt")
    second = tmp_path / "second"
    git(first, "worktree", "add", "--detach", second.as_posix(), "HEAD")

    first_contract = (first / ".ethos" / "commitment.toml").read_text(encoding="utf-8")
    second_plan = adoption_plan(second)

    assert second_plan["required_gaps"] == []
    assert {item["action"] for item in second_plan["write_plan"]} == {"keep_existing"}
    assert (second / ".ethos" / "commitment.toml").read_text(encoding="utf-8") == first_contract
    assert load_repository_commitment(first).id == load_repository_commitment(second).id


def test_apply_is_idempotent_and_replaces_an_empty_binding(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text("", encoding="utf-8")

    first = adoption_plan(tmp_path, apply=True)
    second = adoption_plan(tmp_path, apply=True)

    assert first["write_plan"][0]["action"] == "write_empty"
    assert second["write_plan"][0]["action"] == "keep_existing"
    assert profile.read_text(encoding="utf-8")


def test_existing_valid_minimal_profile_is_preserved(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text("profile_id = 'foreign'\n", encoding="utf-8")

    result = adoption_plan(tmp_path, apply=True)

    assert result["applied"] is True
    assert result["required_gaps"] == []
    assert profile.read_text(encoding="utf-8") == "profile_id = 'foreign'\n"


def test_existing_repository_surfaces_are_outside_bootstrap_scope(tmp_path: Path) -> None:
    agent = tmp_path / "AGENTS.md"
    provider = tmp_path / ".gitlab-ci.yml"
    agent.write_text("# Existing\n", encoding="utf-8")
    provider.write_text("stages: [test]\n", encoding="utf-8")

    result = adoption_plan(tmp_path, apply=True)

    assert result["applied"] is True
    assert agent.read_text(encoding="utf-8") == "# Existing\n"
    assert provider.read_text(encoding="utf-8") == "stages: [test]\n"


def test_adopt_rejects_profile_symlink_without_touching_its_target(tmp_path: Path) -> None:
    external = tmp_path / "external.toml"
    external.write_text("", encoding="utf-8")
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.symlink_to(external)

    result = adoption_plan(tmp_path, apply=True)

    assert result["applied"] is False
    assert result["required_gaps"] == ["adoption_conflict:.ethos/profile.toml"]
    assert external.read_text(encoding="utf-8") == ""
    assert profile.is_symlink()


def test_adopt_rejects_symlinked_profile_parent(tmp_path: Path) -> None:
    external = tmp_path / "external"
    external.mkdir()
    (tmp_path / ".ethos").symlink_to(external, target_is_directory=True)

    result = adoption_plan(tmp_path, apply=True)

    assert result["applied"] is False
    assert result["required_gaps"] == [
        "adoption_conflict:.ethos/profile.toml",
        "adoption_conflict:.ethos/commitment.toml",
    ]
    assert list(external.iterdir()) == []


def test_adopt_rejects_non_regular_profile_targets(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.mkdir(parents=True)

    directory_result = adoption_plan(tmp_path, apply=True)

    assert directory_result["applied"] is False
    assert directory_result["required_gaps"] == ["adoption_conflict:.ethos/profile.toml"]

    profile.rmdir()
    os.mkfifo(profile)
    special_result = adoption_plan(tmp_path, apply=True)

    assert special_result["applied"] is False
    assert special_result["required_gaps"] == ["adoption_conflict:.ethos/profile.toml"]


def test_adopt_rejects_unreadable_parent_or_profile(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / ".ethos" / "profile.toml"
    target.parent.mkdir()
    target.write_text("", encoding="utf-8")
    original_resolve = Path.resolve
    original_lstat = Path.lstat

    def broken_resolve(path: Path, *args, **kwargs) -> Path:
        if path == target.parent:
            raise OSError
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", broken_resolve)
    assert adoption_plan(tmp_path, apply=True)["applied"] is False
    monkeypatch.setattr(Path, "resolve", original_resolve)

    def broken_lstat(path: Path):
        if path == target:
            raise OSError
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", broken_lstat)
    assert adoption_plan(tmp_path, apply=True)["applied"] is False


def test_atomic_profile_write_cleans_temporary_file_on_failure(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / ".ethos" / "profile.toml"
    target.parent.mkdir()
    original_replace = Path.replace
    message = "replace failed"

    def fail_replace(path: Path, destination: Path) -> Path:
        if destination == target:
            raise OSError(message)
        return original_replace(path, destination)

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        adoption_plan(tmp_path, apply=True)

    assert list(target.parent.glob(".profile-*")) == []


def test_adopt_rolls_back_profile_when_commitment_write_fails(tmp_path: Path, monkeypatch) -> None:
    commitment = tmp_path / ".ethos" / "commitment.toml"
    original_replace = Path.replace
    message = "commitment replace failed"

    def fail_commitment(path: Path, destination: Path) -> Path:
        if destination == commitment:
            raise OSError(message)
        return original_replace(path, destination)

    monkeypatch.setattr(Path, "replace", fail_commitment)

    with pytest.raises(OSError, match="commitment replace failed"):
        adoption_plan(tmp_path, apply=True)

    assert not (tmp_path / ".ethos" / "profile.toml").exists()
    assert not commitment.exists()
