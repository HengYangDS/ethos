"""Quality subjects bind committed roles and one valid committed tree."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.gate_policy import observe_quality_subjects
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_quality_observation_retains_committed_roles_and_explicit_test_identity(
    tmp_path: Path,
) -> None:
    """Policy compilation and native observation share the same committed roles."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "test_entry.js").write_text("export const answer = 42;\n")
    (repo / ".gitattributes").write_text("test_entry.js ethos-role=code\n")
    head = commit_fixture(repo, "declare production subject")
    tree, (subject,) = observe_quality_subjects(repo, language="javascript")
    assert tree == git(repo, "rev-parse", f"{head}^{{tree}}")
    assert subject.role == "code"
    assert not subject.is_test
    assert subject.requires_behavior
    (repo / ".gitattributes").write_text("test_entry.js ethos-role=test\n")
    assert observe_quality_subjects(repo)[1] == (subject,)


@pytest.mark.parametrize("fault", ["profile", "tree"])
def test_quality_subjects_bind_one_valid_committed_tree(tmp_path: Path, fault: str) -> None:
    """An invalid committed profile or another expected tree never yields quality subjects."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "answer.py").write_text("VALUE = 42\n")
    if fault == "profile":
        (repo / ".ethos").mkdir()
        (repo / ".ethos/profile.toml").write_text("profile_id = 1\n")
    commit_fixture(repo, "record source")
    message = "repository_profile_invalid" if fault == "profile" else "code_source_changed"
    with pytest.raises(ValueError, match=message):
        observe_quality_subjects(repo, expected_tree="0" * 40 if fault == "tree" else "")
