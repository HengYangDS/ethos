"""Apply native adoption bindings with idempotence and failed-write cleanup."""

import os
import shlex
from hashlib import sha256
from pathlib import Path

import pytest

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.domain.adoption import adopt_repository
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.profile import load_repository_profile
from tests.support.governed_repository import declare_fixture_code_correctness
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("empty", [False, True])
def test_adopt_apply_writes_profile_and_official_openspec_config(
    tmp_path: Path, monkeypatch, newline, empty
) -> None:
    """Declared byte identities survive native newline policy and repeated adoption."""
    native_open = os.fdopen

    def open_native(descriptor, mode="r", **options):
        if "b" not in mode:
            options.setdefault("newline", newline)
        return native_open(descriptor, mode, **options)

    monkeypatch.setattr(os, "fdopen", open_native)
    if empty:
        (tmp_path / ".ethos").mkdir()
        (tmp_path / ".ethos/profile.toml").touch()
    result = adoption_plan(tmp_path, apply=True)
    assert result["write_plan"][0]["action"] == ("write_empty" if empty else "create")
    for row in result["write_plan"]:
        assert sha256((tmp_path / row["path"]).read_bytes()).hexdigest() == row["content_sha256"]
    assert {row["action"] for row in adoption_plan(tmp_path, apply=True)["write_plan"]} == {
        "keep_existing"
    }
    profile = load_repository_profile(tmp_path)
    assert result["planned_files"] == [".ethos/profile.toml", "openspec/config.yaml"]
    assert profile.state == "valid"
    assert profile.declaration.profile_id == tmp_path.name
    assert profile.declaration.openspec.material_paths == ("**",)
    assert resolve_gate_policy(tmp_path).gate_ids == ()
    assert resolve_gate_policy(tmp_path).registry == {}
    files = [p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()]
    assert sorted(files) == result["planned_files"]
    assert result["repository_id"] == f"repository:{tmp_path.name}"


def test_repository_declared_gate_owners_remain_distinct(tmp_path: Path) -> None:
    """The product retains its floor while an adopter selects only its own gates."""
    assert "unit-architecture" in resolve_gate_policy(ROOT).gate_ids
    adoption_plan(tmp_path, apply=True)
    declare_fixture_code_correctness(tmp_path)

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
    assert adoption_plan(first)["repository_id"] == second_plan["repository_id"]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("apply", [False, True])
@pytest.mark.parametrize(
    ("relative", "content", "valid"),
    [
        (".ethos/profile.toml", "profile_id = 'foreign'\n", True),
        ("AGENTS.md", "# Existing\n", True),
        (".gitlab-ci.yml", "stages: [test]\n", True),
        (
            "openspec/config.yaml",
            (
                "schema: intent-to-proof\ncontext: preserve the adopter workflow\n"
                "rules:\n  verification: [bind exact evidence]\n"
            ),
            True,
        ),
        ("openspec/config.yaml", "schema: [", False),
        ("openspec/config.yaml", "", False),
        ("openspec/config.yaml", "schema: spec-driven\ndefaultStore: foreign\n", False),
    ],
)
def test_adoption_preserves_existing_authored_surfaces(
    tmp_path, relative, content, valid, newline, apply
):
    """Preserve authored bytes without mistaking rejected config for valid adoption."""
    repo = init_git_repo(tmp_path / "repo")
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    content = content.replace("\n", newline).encode()
    target.write_bytes(content)
    report = adopt_repository(
        repo, apply=apply, authorize=True, expect_head=git(repo, "rev-parse", "HEAD")
    )
    result = report.data
    assert (report.verdict, result["applied"]) == ("pass" if valid else "block", apply and valid)
    assert target.read_bytes() == content
    if not valid:
        assert "adoption_conflict:openspec/config.yaml" in report.required_gaps
        assert any(gap.startswith("openspec_config_") for gap in report.required_gaps)
        assert report.user_decision_required
        assert "Resolve" in report.next_action
        assert not (repo / ".ethos").exists()
    elif relative in result["planned_files"]:
        row = next(row for row in result["write_plan"] if row["path"] == relative)
        assert row["action"] == "keep_existing"
        assert row["content_sha256"] == sha256(content).hexdigest()


@pytest.mark.parametrize(
    "kind", ["parent_link", "file_link", "directory", "fifo", "resolve", "lstat"]
)
def test_adopt_rejects_unsafe_binding_without_touching_target(tmp_path, monkeypatch, kind):
    observe = Path.lstat
    target = tmp_path / "profile.toml"
    target.write_text("")
    profile = tmp_path / ".ethos" / "profile.toml"
    if kind == "parent_link":
        profile.parent.symlink_to(tmp_path, target_is_directory=True)
    else:
        profile.parent.mkdir()
        if kind == "file_link":
            profile.symlink_to(target)
        elif kind == "directory":
            profile.mkdir()
        elif kind == "fifo":
            os.mkfifo(profile)
        else:
            profile.touch()
            native = getattr(Path, kind)

            def unreadable(path: Path, *args, **kwargs):
                if path == (profile.parent if kind == "resolve" else profile):
                    raise OSError
                return native(path, *args, **kwargs)

            monkeypatch.setattr(Path, kind, unreadable)
    before = observe(profile)
    result = adoption_plan(tmp_path, apply=True)
    assert result["applied"] is False
    assert result["required_gaps"] == ["adoption_conflict:.ethos/profile.toml"]
    assert target.read_text() == ""
    if kind in {"parent_link", "file_link"}:
        assert (profile.parent if kind == "parent_link" else profile).is_symlink()
    after = observe(profile)
    assert (after.st_mode, after.st_ino) == (before.st_mode, before.st_ino)
    if profile.is_file():
        assert profile.read_bytes() == b""


@pytest.mark.parametrize("second", [False, True])
@pytest.mark.parametrize("empty", [False, True])
def test_atomic_profile_write_cleans_temporary_file_on_failure(
    tmp_path, monkeypatch, second, empty
):
    target = tmp_path / ".ethos" / "profile.toml"
    target.parent.mkdir()
    if empty:
        target.touch()
    original_replace = Path.replace
    message = "replace failed"

    def fail_replace(path: Path, destination: Path) -> Path:
        if destination == (tmp_path / "openspec/config.yaml" if second else target):
            raise OSError(message)
        return original_replace(path, destination)

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        adoption_plan(tmp_path, apply=True)

    assert not list(tmp_path.rglob(".profile-*"))
    assert target.read_bytes() == b"" if empty else not target.exists()


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
