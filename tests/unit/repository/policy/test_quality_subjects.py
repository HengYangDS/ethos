"""Quality subjects bind committed roles and one valid committed tree."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.gate_policy as owner
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


def test_quality_observation_names_no_subject_on_its_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host bounds the length of a command line, so no subject rides on one."""
    repo = init_git_repo(tmp_path / "repo")
    for name in ("answer.py", "other.py", "notes.md"):
        (repo / name).write_text("VALUE = 42\n")
    commit_fixture(repo, "record sources")
    commands: list[tuple[str, ...]] = []
    run = owner.run_git

    def recorded(root: Path, *args: str, **options: object) -> object:
        commands.append(args)
        return run(root, *args, **options)

    monkeypatch.setattr(owner, "run_git", recorded)
    (repo / "notes.md").write_text("no code subject\n")
    assert len(observe_quality_subjects(repo, language="python")[1]) == 2
    compared = [args for args in commands if args[0] == "diff"]
    assert compared
    assert not any(name in args for args in compared for name in ("answer.py", "other.py"))
    (repo / "other.py").write_text("VALUE = 43\n")
    with pytest.raises(ValueError, match="code_source_changed"):
        observe_quality_subjects(repo, language="python")


def test_quality_observation_compares_subject_names_as_bytes(tmp_path: Path) -> None:
    """A text read rewrites a carriage return in a name, and the subject's change goes unseen."""
    repo = init_git_repo(tmp_path / "repo")
    name = "odd\rname.py"
    (repo / name).write_text("VALUE = 42\n")
    commit_fixture(repo, "record a source")
    subjects = observe_quality_subjects(repo, language="python")[1]
    assert [subject.path for subject in subjects] == [name]
    (repo / name).write_text("VALUE = 43\n")
    with pytest.raises(ValueError, match="code_source_changed"):
        observe_quality_subjects(repo, language="python")
