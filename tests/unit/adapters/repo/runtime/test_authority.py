"""Tests for runtime build-authority selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.authority as authority
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import runtime_build

if TYPE_CHECKING:
    from pathlib import Path


def _git(root: Path, *args: str) -> str:
    result = git_process(root, *args)
    assert result.returncode == 0
    return result.stdout.strip()


def _commit(root: Path, message: str) -> None:
    _git(root, "add", ".")
    _git(root, "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-m", message)


def _repository(tmp_path: Path, *, version: bool) -> tuple[Path, Path]:
    repo, lane = tmp_path / "ethos", tmp_path / "lane"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch=dev")
    (repo / ".ethos").mkdir()
    (repo / ".ethos/profile.toml").write_text('profile_id = "ethos"\n')
    (repo / ".ethos/workspace.toml").write_text('[branch_roles]\naccepted_branch = "dev"\n')
    (repo / "tracked.txt").write_text("accepted\n")
    if version:
        (repo / "VERSION").write_text("0.2.0-alpha.1\n")
    _commit(repo, "accepted")
    _git(repo, "worktree", "add", "-q", "-b", "work/runtime", str(lane))
    return repo, lane


def test_self_hosted_expectation_uses_accepted_checkout_and_rejects_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = _repository(tmp_path, version=True)
    expected = runtime_build(
        _git(repo, "rev-parse", "dev"), _git(repo, "rev-parse", "dev^{tree}"), accepted=True
    )
    (lane / "tracked.txt").write_text("candidate\n")
    _commit(lane, "candidate")
    identity, source_root = authority.expected_runtime_build(lane)
    assert (identity, source_root) == (expected, repo.resolve())
    monkeypatch.setattr(
        authority, "source_build_identity", lambda *_a, **_k: runtime_build("a" * 40, "b" * 40)
    )
    with pytest.raises(ValueError, match="accepted_build_identity_unavailable"):
        authority.expected_runtime_build(lane)


def test_version_migration_uses_exact_invoking_lane_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo, lane = _repository(tmp_path, version=False)
    (lane / "VERSION").write_text("0.2.0-alpha.1\n")
    (lane / "pyproject.toml").write_text("[project]\nname='ethos'\n")
    module = lane / "src/ethos/adapters/repo/runtime/authority.py"
    module.parent.mkdir(parents=True)
    module.touch()
    monkeypatch.setattr(authority, "__file__", str(module))
    _commit(lane, "version migration")
    (lane / "tracked.txt").write_text("staged postimage\n")
    _git(lane, "add", "tracked.txt")
    identity, source_root = authority.expected_runtime_build(lane)
    assert identity.source_commit == _git(lane, "rev-parse", "HEAD")
    assert identity.source_tree == _git(lane, "rev-parse", "HEAD^{tree}")
    assert authority.expected_runtime_source(lane) == (
        identity.source_commit,
        identity.source_tree,
    )
    assert (identity.channel, identity.acceptance_state, source_root) == (
        "development",
        "unaccepted",
        lane.resolve(),
    )


def test_runtime_authority_fallback_matrix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    packaged = runtime_build("a" * 40, "b" * 40)
    monkeypatch.setattr(authority, "packaged_build_identity", lambda: packaged)
    assert authority.runtime_build_identity(tmp_path) == packaged
    monkeypatch.setattr(
        authority, "repository_root", lambda _root: (_ for _ in ()).throw(ValueError())
    )
    monkeypatch.setattr(authority, "runtime_build_identity", lambda _root: packaged)
    assert authority.expected_runtime_build(tmp_path)[0] == packaged
    assert authority.expected_runtime_source(tmp_path) == (
        packaged.source_commit,
        packaged.source_tree,
    )
