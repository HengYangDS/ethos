"""Pre-state revisions keep their historical identity; produced revisions meet today's schema."""

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

RETIRED_SCHEMA = '\n[retired]\nformat = "ruff-json"\n'


@pytest.mark.parametrize(
    ("retired_role", "retired_identity", "expected"),
    [
        ("expected", "repo", "repository:repo"),
        ("asserted", "repo", "repository:repo"),
        ("desired", "repo", "repository_profile_invalid"),
        ("expected", "other", "git_effect_repository_identity_mismatch"),
    ],
)
def test_prestate_identity_survives_a_retired_profile_schema(
    tmp_path: Path, retired_role: str, retired_identity: str, expected: str
) -> None:
    """A retired accepted schema keeps its identity; the produced revision stays strict."""
    case = fixture(tmp_path)
    profile = (case.repo / ".ethos/profile.toml").read_text(encoding="utf-8")
    retired = commit_fixture_file(
        case.repo,
        ".ethos/profile.toml",
        profile.replace('"repo"', f'"{retired_identity}"') + RETIRED_SCHEMA,
        "accepted with a retired profile schema",
    )
    migrated = commit_fixture_file(
        case.repo, ".ethos/profile.toml", profile, "migrate the profile schema"
    )
    git(case.repo, "update-ref", "refs/heads/candidate", retired)
    git(case.repo, "update-ref", "refs/heads/topic", case.old)
    git(case.repo, "checkout", "-q", "--detach", case.old)
    value = {
        "expected": GitEffect(
            updates={"refs/heads/candidate": GitRefUpdate(expected=retired, desired=migrated)}
        ),
        "asserted": GitEffect(
            updates={"refs/heads/topic": GitRefUpdate(expected=case.old, desired=migrated)},
            assertions={"refs/heads/candidate": retired},
        ),
        "desired": GitEffect(
            updates={"refs/heads/topic": GitRefUpdate(expected=case.old, desired=retired)}
        ),
    }[retired_role]
    before = observe_git_effect(case.repo, value)
    if expected.startswith("repository:"):
        assert resolve_git_effect_repository(case.repo, value, before) == expected
        return
    with pytest.raises(ValueError, match=expected):
        resolve_git_effect_repository(case.repo, value, before)
