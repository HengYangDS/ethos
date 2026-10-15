"""Accepted closeout reads a committed predecessor branch-role incumbent."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.mutation.accepted.admission import accepted_transition_policy
from ethos.contracts.branch.roles import BranchRolePolicy
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

OLDEST = """[branch_roles]
release_branch = "main"
accepted_branch = "accepted/train"
candidate_branch = "candidate/train"
work_branch_prefix = "work/"
proposal_branch_prefix = "submit/"
"""


def test_closeout_reads_a_five_field_incumbent_with_predecessor_defaults(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = commit_fixture_file(repo, ".ethos/workspace.toml", OLDEST, "record predecessor roles")

    assert accepted_transition_policy(repo, head) == BranchRolePolicy(
        accepted_branch="accepted/train",
        candidate_branch="candidate/train",
        proposal_branch_prefix="submit/",
    )


@pytest.mark.parametrize("field", ["release_branch", "work_branch_prefix"])
def test_closeout_rejects_any_other_incomplete_incumbent(tmp_path: Path, field: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    table = "".join(line for line in OLDEST.splitlines(keepends=True) if not line.startswith(field))
    head = commit_fixture_file(repo, ".ethos/workspace.toml", table, "record incomplete roles")

    with pytest.raises(ValueError, match="complete and exact"):
        accepted_transition_policy(repo, head)
