"""Construct Work Lane lifecycle scenarios for contract tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from tests.support.governed_repository import commit_active_commitment
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_role_policy

if TYPE_CHECKING:
    from pathlib import Path


def add_candidate_worktree(repo: Path, path: Path) -> Path:
    git(repo, "worktree", "add", "-b", "candidate/dev", path.as_posix(), "dev")
    install_hook_launchers(path)
    return path


def leased_worktree(repo: Path, path: Path, *, holder_ref: str = "agent:test:case:agent-a") -> Path:
    """Create one owned worktree with a matching lease for admission tests."""
    carrier = ".ethos/commitment.toml"
    change_id = None
    if not (repo / carrier).exists():
        commit_active_commitment(repo)
        carrier = "openspec/changes/fixture-change/commitment.toml"
        change_id = "fixture-change"
    git(repo, "worktree", "add", "-b", "work/feature", path.as_posix(), "dev")
    head = git(path, "rev-parse", "HEAD")
    acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        lease=exact_lease(
            repo=repo,
            branch="work/feature",
            holder_ref=holder_ref,
            expected_head=head,
            carrier=carrier,
            change_id=change_id,
        ),
    )
    return path


def absorb_obsolete_delta_in_accepted(repo: Path) -> str:
    """Commit a fixture change directly on the accepted branch."""
    (repo / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
    git(repo, "add", "obsolete.txt")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "absorb obsolete lane delta",
    )
    return git(repo, "rev-parse", "dev")


def orphan_work_lane(tmp_path: Path) -> tuple[Path, Path]:
    """Create an unleased Work Lane for exceptional-resolution tests."""
    repo = init_git_repo(tmp_path / "repo")
    lane = tmp_path / "repo-work-orphan"
    git(repo, "worktree", "add", "-b", "work/orphan", lane.as_posix(), "dev")
    return repo, lane


def superseded_work_lane(
    tmp_path: Path,
    *,
    absorbed: bool = True,
    holder_ref: str = "agent:test:case:agent-a",
) -> tuple[Path, Path, str, str, Path]:
    """Create an owned obsolete lane and optionally absorb its change on dev."""
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(
        repo,
        candidate_branch="candidate/dev",
        work_branch_prefix="work/",
        proposal_branch_prefix="proposal/",
    )
    commit_active_commitment(repo)
    carrier = "openspec/changes/fixture-change/commitment.toml"
    change_id = "fixture-change"
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    lane = tmp_path / "repo-work-superseded"
    git(repo, "worktree", "add", "-b", "work/superseded", lane.as_posix(), "dev")
    (lane / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
    git(lane, "add", "obsolete.txt")
    git(
        lane,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "obsolete lane delta",
    )
    head = git(lane, "rev-parse", "HEAD")
    accepted = (
        absorb_obsolete_delta_in_accepted(repo) if absorbed else git(repo, "rev-parse", "dev")
    )
    database = repo / ".ethos" / "state" / "state.sqlite"
    acquire_lease(
        database,
        lease=exact_lease(
            repo=repo,
            branch="work/superseded",
            holder_ref=holder_ref,
            expected_head=head,
            carrier=carrier,
            change_id=change_id,
            ttl_seconds=3600,
        ),
    )
    return repo, lane, head, accepted, database


def assert_no_ui_projection(value: object) -> None:
    if isinstance(value, dict):
        forbidden = {"open_action", "open_label", "action", "label"}
        assert not (forbidden & set(value))
        for child in value.values():
            assert_no_ui_projection(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_ui_projection(child)
