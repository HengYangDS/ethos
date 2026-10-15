"""Retirement deletes refs that predate an accepted rename without adopting their identity."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.git_effect_observation import observe_git_effect
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from tests.support.git_effect import fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path

ZERO_OID = "0" * 40


@pytest.mark.parametrize("kind", ["inherited", "introduced", "unrelated"])
def test_deleted_ref_identity_must_be_inherited_from_accepted_history(
    tmp_path: Path, kind: str
) -> None:
    """Retirement may delete a ref that predates an accepted rename, never adopt its identity."""
    case = fixture(tmp_path, "repository:former")
    former = (case.repo / ".ethos/profile.toml").read_text(encoding="utf-8")
    topic = case.old
    if kind == "introduced":
        git(case.repo, "checkout", "-q", "-b", "topic")
        topic = commit_fixture_file(
            case.repo,
            ".ethos/profile.toml",
            former.replace("former", "introduced"),
            "introduce identity",
        )
        git(case.repo, "checkout", "-q", "dev")
    elif kind == "unrelated":
        git(case.repo, "checkout", "-q", "--orphan", "unrelated")
        topic = commit_fixture_file(
            case.repo, "unrelated.txt", "no shared history\n", "start unrelated history"
        )
        git(case.repo, "checkout", "-q", "dev")
    git(case.repo, "update-ref", "refs/heads/topic", topic)
    renamed = commit_fixture_file(
        case.repo, ".ethos/profile.toml", former.replace("former", "renamed"), "rename identity"
    )
    value = GitEffect(
        updates={"refs/heads/topic": GitRefUpdate(expected=topic, desired=ZERO_OID)},
        assertions={"refs/heads/dev": renamed},
    )
    before = observe_git_effect(case.repo, value)
    if kind == "inherited":
        assert (
            resolve_git_effect_repository(case.repo, value, before, allow_absent_prestate=True)
            == "repository:renamed"
        )
        return
    with pytest.raises(ValueError, match="git_effect_repository_identity_mismatch"):
        resolve_git_effect_repository(case.repo, value, before, allow_absent_prestate=True)
