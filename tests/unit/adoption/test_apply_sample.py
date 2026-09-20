"""Apply native adoption bindings with idempotence and failed-write cleanup."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

import pytest
import tomli_w

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.domain.adoption import adopt_repository
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.profile import load_repository_profile
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ROOT = Path(__file__).resolve().parents[3]


def test_adopt_apply_writes_profile_and_official_openspec_config(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, apply=True)

    profile = load_repository_profile(tmp_path)
    assert result["applied"] is True
    assert result["planned_files"] == [
        ".ethos/profile.toml",
        "openspec/config.yaml",
    ]
    assert profile.exists
    assert profile.state == "valid"
    assert profile.declaration is not None
    assert profile.declaration.profile_id == tmp_path.name
    assert profile.declaration.openspec.material_paths == ("**",)
    assert resolve_gate_policy(tmp_path).gate_ids == ()
    assert resolve_gate_policy(tmp_path).registry == {}
    assert sorted(path.as_posix() for path in tmp_path.rglob("*") if path.is_file()) == [
        (tmp_path / ".ethos/profile.toml").as_posix(),
        (tmp_path / "openspec/config.yaml").as_posix(),
    ]
    assert result["repository_id"] == f"repository:{tmp_path.name}"


def test_declared_local_gate_registry_preserves_self_governance_floor() -> None:
    profile = load_repository_profile(ROOT)

    assert profile.state == "valid"
    assert profile.declaration is not None
    assert profile.declaration.proof.gate_registry == "system/gates.toml"
    assert "unit-architecture" in resolve_gate_policy(ROOT).gate_ids


def test_profile_native_gate_owner_replaces_packaged_gates(tmp_path: Path) -> None:
    adoption_plan(tmp_path, apply=True)
    profile = tmp_path / ".ethos" / "profile.toml"
    cases = (
        ("sample-tests", "test", "tests", "behavior", "proof"),
        ("sample-static", "typing", "types", "static-analysis", "contract"),
    )
    gates = [
        {
            "id": name,
            "kind": kind,
            "command": ["custom", command],
            "dimensions": [dimension],
            "evidence_class": evidence,
            "trust_bearing": True,
        }
        for name, kind, command, dimension, evidence in cases
    ]
    profile.write_text(
        profile.read_text()
        + tomli_w.dumps(
            {
                "proof": {
                    "code_correctness_gates": [row[0] for row in cases],
                    "code_correctness_map": {row[3]: row[0] for row in cases},
                    "gates": gates,
                }
            }
        )
    )

    assert set(resolve_gate_policy(tmp_path).registry) == {"sample-tests", "sample-static"}


def test_adoption_repository_identity_does_not_depend_on_checkout_path(tmp_path: Path) -> None:
    first = init_git_repo(tmp_path / "first")
    adoption_plan(first, apply=True)
    git(first, "add", ".")
    git(first, "commit", "-m", "adopt")
    second = tmp_path / "second"
    git(first, "worktree", "add", "--detach", second.as_posix(), "HEAD")

    first_profile = (first / ".ethos" / "profile.toml").read_text(encoding="utf-8")
    second_plan = adoption_plan(second)

    assert second_plan["required_gaps"] == []
    assert {item["action"] for item in second_plan["write_plan"]} == {"keep_existing"}
    assert (second / ".ethos" / "profile.toml").read_text(encoding="utf-8") == first_profile
    assert adoption_plan(first)["repository_id"] == adoption_plan(second)["repository_id"]


def test_apply_is_idempotent_and_replaces_an_empty_binding(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text("", encoding="utf-8")

    first = adoption_plan(tmp_path, apply=True)
    second = adoption_plan(tmp_path, apply=True)

    assert first["write_plan"][0]["action"] == "write_empty"
    assert second["write_plan"][0]["action"] == "keep_existing"
    assert profile.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("relative", "content"),
    [
        (".ethos/profile.toml", "profile_id = 'foreign'\n"),
        ("AGENTS.md", "# Existing\n"),
        (".gitlab-ci.yml", "stages: [test]\n"),
        (
            "openspec/config.yaml",
            (
                "schema: intent-to-proof\ncontext: preserve the adopter workflow\n"
                "rules:\n  verification: [bind exact evidence]\n"
            ),
        ),
    ],
)
def test_adoption_preserves_existing_authored_surfaces(tmp_path, relative, content):
    """Neither bootstrap bindings nor unrelated authored surfaces are overwritten."""
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    result = adoption_plan(tmp_path, apply=True)
    assert result["applied"] is True
    assert result["required_gaps"] == []
    assert target.read_text() == content
    if relative == "openspec/config.yaml":
        assert (
            next(row["action"] for row in result["write_plan"] if row["path"] == relative)
            == "keep_existing"
        )


@pytest.mark.parametrize("parent_link", [False, True])
def test_adopt_rejects_symlinked_binding_without_touching_target(tmp_path, parent_link):
    external = tmp_path / "external"
    external.mkdir()
    target = external / "profile.toml"
    target.write_text("")
    profile = tmp_path / ".ethos" / "profile.toml"
    if parent_link:
        profile.parent.symlink_to(external, target_is_directory=True)
    else:
        profile.parent.mkdir()
        profile.symlink_to(target)
    result = adoption_plan(tmp_path, apply=True)
    assert result["applied"] is False
    assert result["required_gaps"] == ["adoption_conflict:.ethos/profile.toml"]
    assert target.read_text() == ""
    assert (profile.parent if parent_link else profile).is_symlink()


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


@pytest.mark.parametrize("condition", ["valid", "denied", "stale", "digest", "conflict", "preview"])
def test_application_adoption_preserves_admission_and_direct_result(tmp_path, capsys, condition):
    repo = init_git_repo(tmp_path / "repo with spaces")
    head = git(repo, "rev-parse", "HEAD")
    if condition == "conflict":
        (repo / ".ethos").mkdir()
        (repo / ".ethos/profile.toml").write_text("[invalid")
    preview = adopt_repository(repo)
    assert preview.data["applied"] is False
    result = adopt_repository(
        repo,
        apply=condition != "preview",
        authorize=condition != "denied",
        expect_head="0" * 40 if condition == "stale" else head,
        expect_plan_digest="0" * 64 if condition == "digest" else preview.data["plan_digest"],
    )
    assert result.verdict == ("pass" if condition in {"valid", "preview"} else "block")
    assert result.data["applied"] is (condition == "valid")
    if condition == "valid":
        assert result.data["repository_id"] == preview.data["repository_id"]
        assert result.data["plan_digest"] == preview.data["plan_digest"]
        assert load_repository_profile(repo).declaration.profile_id == repo.name
    if condition == "digest":
        assert result.required_gaps == ("adoption_plan_digest_mismatch",)
        assert not (repo / ".ethos").exists()
    assert (repo / "openspec/config.yaml").exists() is (condition == "valid")
    action = shlex.split(result.next_action)
    if condition != "conflict":
        assert action[:2] == ["ethos", "status" if condition == "valid" else "adopt"]
        assert action[action.index("--root") + 1] == str(repo.resolve())
    if condition == "preview":
        assert {"--apply", "--authorize"} <= set(action)
        assert action[action.index("--expect-head") + 1] == head
        assert action[action.index("--expect-plan-digest") + 1] == preview.data["plan_digest"]
    assert result.user_decision_required is (condition in {"preview", "denied", "conflict"})
    assert "next_action" not in result.data
    assert not capsys.readouterr().out
