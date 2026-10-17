"""Accepted closeout reads the incumbent's committed branch-role settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.mutation.accepted.admission import accepted_transition_policy
from ethos.contracts.branch.roles import BranchRolePolicy
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

LEGACY = """[branch_roles]
release_branch = "main"
accepted_branch = "accepted/train"
candidate_branch = "candidate/train"
work_branch_prefix = "work/"
proposal_branch_prefix = "submit/"
"""


@pytest.mark.parametrize(
    ("path", "text", "expected"),
    [
        (".ethos/workspace.toml", LEGACY, BranchRolePolicy()),
        (
            ".ethos/workspace.toml",
            '[branch_roles]\nrelease_mirror = "accepted_ff"\n',
            BranchRolePolicy(),
        ),
        (
            ".ethos/release.toml",
            '[release]\nmirror = "accepted_ff"\n',
            BranchRolePolicy(release_mirror="accepted_ff"),
        ),
        (".ethos/release.toml", '[protected_refs]\ntags = ["v*"]\n', BranchRolePolicy()),
    ],
    ids=["legacy-names", "retired-mirror", "release-mirror", "no-mirror"],
)
def test_closeout_reads_the_release_mirror_and_the_paradigm_names(
    tmp_path: Path, path: str, text: str, expected: BranchRolePolicy
) -> None:
    """The incumbent's release binding decides the mirror; a workspace table decides nothing."""
    repo = init_git_repo(tmp_path / "repo")
    head = commit_fixture_file(repo, path, text, "record branch roles")

    assert accepted_transition_policy(repo, head) == expected


def test_closeout_rejects_an_invalid_incumbent(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    release = '[release]\nmirror = "mirror"\n'
    head = commit_fixture_file(repo, ".ethos/release.toml", release, "record an invalid mirror")

    with pytest.raises(ValueError, match="mirror is invalid"):
        accepted_transition_policy(repo, head)
