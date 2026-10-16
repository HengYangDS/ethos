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
    ("workspace", "expected"),
    [
        (LEGACY, BranchRolePolicy()),
        (
            '[branch_roles]\nrelease_mirror = "accepted_ff"\n',
            BranchRolePolicy(release_mirror="accepted_ff"),
        ),
        ("[commit_policy]\nsigning_required = true\n", BranchRolePolicy()),
    ],
    ids=["legacy-names", "settings-only", "no-table"],
)
def test_closeout_reads_the_settings_and_the_paradigm_names(
    tmp_path: Path, workspace: str, expected: BranchRolePolicy
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = commit_fixture_file(repo, ".ethos/workspace.toml", workspace, "record branch roles")

    assert accepted_transition_policy(repo, head) == expected


def test_closeout_rejects_an_invalid_incumbent(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    table = LEGACY.replace('release_branch = "main"', "release_branch = 1")
    head = commit_fixture_file(repo, ".ethos/workspace.toml", table, "record invalid roles")

    with pytest.raises(ValueError, match="canonical strings"):
        accepted_transition_policy(repo, head)
