"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.repo.runtime.authority as runtime_authority
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import runtime_build

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_self_hosted_expectation_uses_the_accepted_ref_and_linked_checkout(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "ethos"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    (repo / ".ethos").mkdir()
    (repo / ".ethos/profile.toml").write_text('profile_id = "ethos"\n', encoding="utf-8")
    (repo / ".ethos/workspace.toml").write_text(
        '[branch_roles]\naccepted_branch = "dev"\n',
        encoding="utf-8",
    )
    (repo / "VERSION").write_text("0.2.0-alpha.1\n", encoding="ascii")
    (repo / "tracked.txt").write_text("accepted\n", encoding="utf-8")
    assert git_process(repo, "add", ".").returncode == 0
    accepted = git_process(
        repo,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "accepted",
    )
    assert accepted.returncode == 0
    accepted_commit = git_process(repo, "rev-parse", "dev").stdout.strip()
    accepted_tree = git_process(repo, "rev-parse", "dev^{tree}").stdout.strip()
    lane = tmp_path / "lane"
    assert git_process(repo, "worktree", "add", "-q", "-b", "work/runtime", lane).returncode == 0
    (lane / "tracked.txt").write_text("candidate\n", encoding="utf-8")
    assert git_process(lane, "add", "tracked.txt").returncode == 0
    candidate = git_process(
        lane,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "candidate",
    )
    assert candidate.returncode == 0

    identity, source_root = expected_runtime_build(lane)

    assert identity == runtime_build(accepted_commit, accepted_tree, accepted=True)
    assert source_root == repo.resolve()


def test_self_hosted_version_migration_bootstraps_from_the_exact_invoking_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "ethos"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    (repo / ".ethos").mkdir()
    (repo / ".ethos/profile.toml").write_text('profile_id = "ethos"\n', encoding="utf-8")
    (repo / ".ethos/workspace.toml").write_text(
        '[branch_roles]\naccepted_branch = "dev"\n',
        encoding="utf-8",
    )
    (repo / "tracked.txt").write_text("accepted\n", encoding="utf-8")
    assert git_process(repo, "add", ".").returncode == 0
    assert (
        git_process(
            repo,
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "accepted without VERSION",
        ).returncode
        == 0
    )
    lane = tmp_path / "lane"
    assert git_process(repo, "worktree", "add", "-q", "-b", "work/runtime", lane).returncode == 0
    (lane / "VERSION").write_text("0.2.0-alpha.1\n", encoding="ascii")
    (lane / "pyproject.toml").write_text("[project]\nname='ethos'\n", encoding="utf-8")
    invoking_module = lane / "src/ethos/adapters/repo/runtime/authority.py"
    invoking_module.parent.mkdir(parents=True)
    invoking_module.touch()
    monkeypatch.setattr(runtime_authority, "__file__", invoking_module.as_posix())

    identity, source_root = expected_runtime_build(lane)

    assert identity.source_commit == git_process(lane, "rev-parse", "HEAD").stdout.strip()
    assert identity.source_tree != git_process(lane, "rev-parse", "HEAD^{tree}").stdout.strip()
    assert identity.channel == "development"
    assert identity.acceptance_state == "unaccepted"
    assert source_root == lane.resolve()
