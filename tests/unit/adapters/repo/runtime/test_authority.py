"""Tests for runtime build-authority selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.authority as authority
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import runtime_build

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path, *, version: bool) -> tuple[Path, Path]:
    repo, lane = init_git_repo(tmp_path / "ethos"), tmp_path / "lane"
    (repo / ".ethos").mkdir()
    (repo / ".ethos/profile.toml").write_text('profile_id = "ethos"\n')
    (repo / ".ethos/workspace.toml").write_text('[branch_roles]\naccepted_branch = "dev"\n')
    if version:
        (repo / "VERSION").write_text("0.2.0-alpha.2\n")
    commit_fixture(repo, "accepted")
    git(repo, "worktree", "add", "-q", "-b", "work/runtime", str(lane))
    return repo, lane


@pytest.mark.parametrize(
    "mode", ["lane", "untracked", "staged", "detached", "advanced", "invalid", "crlf"]
)
def test_self_hosted_expectation_binds_accepted_objects_not_checkout_overlay(tmp_path, mode):
    repo, lane = _repository(tmp_path, version=True)
    (lane / "README.md").write_text("candidate\n")
    commit_fixture(lane, "candidate")
    if mode == "untracked":
        (repo / "observation.log").write_text("foreign observation\n")
    elif mode in {"staged", "invalid", "crlf"}:
        (repo / "VERSION").write_bytes(
            b"0.2.0-alpha.2\r\n" if mode == "crlf" else b"invalid version\n"
        )
        git(repo, "config", "core.autocrlf", "false")
        git(repo, "add", "VERSION")
        if mode != "staged":
            commit_fixture(repo, "invalid version")
    elif mode == "detached":
        git(repo, "checkout", "--detach")
    elif mode == "advanced":
        (repo / "README.md").write_text("new accepted\n")
        commit_fixture(repo, "advance accepted")
    expected = runtime_build(git(repo, "rev-parse", "dev"), git(repo, "rev-parse", "dev^{tree}"))
    before = git(repo, "status", "--porcelain"), (repo / ".git/index").read_bytes()
    if mode in {"invalid", "crlf"}:
        with pytest.raises(ValueError, match="product_version_invalid"):
            authority.expected_runtime_build(lane)
        return
    identity, source_root = authority.expected_runtime_build(lane)
    assert (identity, source_root) == (expected, (lane if mode == "detached" else repo).resolve())
    assert before == (git(repo, "status", "--porcelain"), (repo / ".git/index").read_bytes())


def test_version_migration_uses_exact_invoking_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo, lane = _repository(tmp_path, version=False)
    (lane / "VERSION").write_text("0.2.0-alpha.2\n")
    (lane / "pyproject.toml").write_text("[project]\nname='ethos'\n")
    module = lane / "src/ethos/adapters/repo/runtime/authority.py"
    module.parent.mkdir(parents=True)
    module.touch()
    monkeypatch.setattr(authority, "__file__", str(module))
    commit_fixture(lane, "version migration")
    (lane / "README.md").write_text("staged postimage\n")
    git(lane, "add", "README.md")
    identity, source_root = authority.expected_runtime_build(lane)
    assert authority.expected_runtime_source(lane) == identity[2:4]
    assert (identity, source_root) == (
        runtime_build(git(lane, "rev-parse", "HEAD"), git(lane, "rev-parse", "HEAD^{tree}")),
        lane.resolve(),
    )


def test_runtime_authority_fallback_matrix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    packaged = runtime_build("a" * 40, "b" * 40)
    monkeypatch.setattr(authority, "packaged_build_identity", lambda: packaged)
    assert authority.runtime_build_identity(tmp_path) == packaged
    assert authority.runtime_build_identity(tmp_path, include_overlay=False) == packaged
    monkeypatch.setattr(
        authority, "repository_root", lambda _root: (_ for _ in ()).throw(ValueError())
    )
    monkeypatch.setattr(authority, "runtime_build_identity", lambda _root: packaged)
    assert authority.expected_runtime_build(tmp_path)[0] == packaged
    assert authority.expected_runtime_source(tmp_path) == (
        packaged.source_commit,
        packaged.source_tree,
    )
