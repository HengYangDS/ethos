"""Shared fixtures for the Work Lane test suites.

The lane coverage is split across sibling `test_lanes*.py` modules by theme
(status, lifecycle, lease projection); these helpers — git plumbing, sample-repo
and candidate-worktree scaffolding, branch-role policy authoring, and the
no-UI-projection assertion — are the setup every split imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo as init_repo

if TYPE_CHECKING:
    from pathlib import Path

__all__ = (
    "add_candidate_worktree",
    "assert_no_ui_projection",
    "git",
    "init_repo",
    "write_role_policy",
)


def add_candidate_worktree(repo: Path, path: Path) -> Path:
    git(repo, "worktree", "add", "-b", "candidate/dev", path.as_posix(), "dev")
    return path


def write_role_policy(
    repo: Path,
    *,
    candidate_branch: str = "stage/dev",
    work_branch_prefix: str = "lane/",
    submit_branch_prefix: str = "review/",
) -> None:
    (repo / ".ethos" / "workspace.toml").write_text(
        "\n".join(
            [
                "[branch_roles]",
                'release_branch = "main"',
                'accepted_branch = "dev"',
                f'candidate_branch = "{candidate_branch}"',
                f'work_branch_prefix = "{work_branch_prefix}"',
                f'submit_branch_prefix = "{submit_branch_prefix}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/workspace.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "configure branch roles",
    )


def assert_no_ui_projection(value: object) -> None:
    if isinstance(value, dict):
        forbidden = {"open_action", "open_label", "action", "label"}
        assert not (forbidden & set(value))
        for child in value.values():
            assert_no_ui_projection(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_ui_projection(child)
