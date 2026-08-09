from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.admission.ref_move_policy import resolve_ref_move_policy
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import canonical_json_digest
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_role_policy
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from pathlib import Path

_ZERO = "0" * 40


def test_ref_policy_uses_valid_profile_only_for_schema_bootstrap(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    head = commit_fixture(repo, "profile-only governance")

    policy = resolve_ref_move_policy(repo, "refs/heads/work/feature", head, _ZERO)

    assert policy == BranchRolePolicy()


def test_ref_policy_rejects_transition_without_strict_or_profile_authority(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    with pytest.raises(ValueError, match="ref_move_policy_unavailable"):
        resolve_ref_move_policy(repo, "refs/heads/arbitrary", head, head)


def test_release_ref_uses_current_accepted_fast_forward_policy(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    base = git(repo, "rev-parse", "HEAD")
    write_role_policy(repo, release_mirror="accepted_ff")
    accepted = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-b", "legacy-policy", base)
    write_role_policy(repo, release_mirror="independent")
    incumbent = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "dev")
    assert git(repo, "rev-parse", "HEAD") == accepted

    policy = resolve_ref_move_policy(repo, "refs/heads/main", incumbent, _ZERO)

    assert policy.release_mirror == "accepted_ff"


@pytest.mark.parametrize("operation", ["lane.retire", "lane.retire.compensate"])
def test_absorbed_legacy_ref_requires_exact_current_policy_intent(
    tmp_path: Path, operation: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = git(repo, "rev-parse", "HEAD")
    write_role_policy(repo)
    accepted = git(repo, "rev-parse", "HEAD")
    ref_name = "refs/heads/lane/legacy"
    old, new = (legacy, _ZERO) if operation == "lane.retire" else (_ZERO, legacy)
    write_ref_intent(
        root=repo,
        ref_name=ref_name,
        update=GitRefUpdate(expected=old, desired=new),
        operation=operation,
        plan_digest=canonical_json_digest({"operation": operation}),
    )

    policy = resolve_ref_move_policy(repo, ref_name, old, new)

    assert git(repo, "rev-parse", "HEAD") == accepted
    assert policy.role_for_branch("lane/legacy") == "work_lane"


@pytest.mark.parametrize("case", ["missing-intent", "wrong-role", "head-drift"])
def test_absorbed_legacy_ref_fails_closed_without_exact_current_authority(
    tmp_path: Path, case: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = git(repo, "rev-parse", "HEAD")
    write_role_policy(repo)
    ref_name = "refs/heads/lane/legacy"
    if case != "missing-intent":
        write_ref_intent(
            root=repo,
            ref_name=ref_name,
            update=GitRefUpdate(expected=legacy, desired=_ZERO),
            operation="lane.retire",
            plan_digest=canonical_json_digest({"operation": "lane.retire"}),
        )
    if case == "wrong-role":
        ref_name = "refs/heads/dev"
    elif case == "head-drift":
        git(repo, "checkout", "-b", "other")
        (repo / "drift").write_text("drift\n", encoding="utf-8")
        commit_fixture(repo, "drift from accepted")

    with pytest.raises(ValueError, match="ref_move_policy_unavailable"):
        resolve_ref_move_policy(repo, ref_name, legacy, _ZERO)
