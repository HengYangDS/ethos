"""Reject worktree collisions, stale refs and ambiguous native observations."""

from __future__ import annotations

from functools import partial
from types import SimpleNamespace

import pytest

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.adapters.repo.worktree_effects import attach_worktree
from ethos.adapters.repo.worktree_effects import remove_worktree
from ethos.adapters.repo.worktree_effects import sync_worktree
from ethos.adapters.repo.worktree_effects import worktree_record
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def _repository(tmp_path):
    repo = init_git_repo(tmp_path / "repo")
    return repo, adopt_and_commit(repo)


def test_add_worktree_rejects_path_collision_before_git_effect(tmp_path) -> None:
    repo, head = _repository(tmp_path)
    target = tmp_path / "linked"
    target.mkdir()
    git(repo, "branch", "linked", head)

    with pytest.raises(ValueError, match=r"^worktree_effect_path_collision$"):
        add_worktree(repo, target, head=head, branch="linked")

    assert git(repo, "worktree", "list", "--porcelain").count(target.as_posix()) == 0


def test_add_worktree_rejects_stale_ref_before_git_effect(tmp_path) -> None:
    repo, head = _repository(tmp_path)
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)

    with pytest.raises(ValueError, match=r"^worktree_effect_ref_stale$"):
        add_worktree(repo, target, head="0" * len(head), branch="linked")

    assert not target.exists()


def test_remove_worktree_rejects_unowned_existing_path(tmp_path) -> None:
    repo, head = _repository(tmp_path)
    target = tmp_path / "linked"
    target.mkdir()

    with pytest.raises(ValueError, match=r"^worktree_effect_path_ownership_unknown$"):
        remove_worktree(repo, target, head=head, branch="linked")

    assert target.is_dir()


@pytest.mark.parametrize("operation", ["add", "remove", "sync", "attach"])
def test_worktree_effect_surfaces_git_failure_without_terminal_claim(
    tmp_path, operation: str
) -> None:
    stderr = f"{operation} denied"
    repo, head = _repository(tmp_path)
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    previous = head
    if operation in {"remove", "sync"}:
        git(repo, "worktree", "add", target.as_posix(), "linked")
        if operation == "sync":
            (repo / "SYNC.md").write_text("sync\n", encoding="utf-8")
            git(repo, "add", "SYNC.md")
            git(repo, "commit", "-m", "advance sync target")
            head = git(repo, "rev-parse", "HEAD")
            git(repo, "update-ref", "refs/heads/linked", head, previous)
    elif operation == "attach":
        git(repo, "worktree", "add", "--detach", target.as_posix(), head)

    def runner(root, *arguments, **kwargs):
        mutating = arguments[:2] in {
            ("worktree", "add"),
            ("worktree", "remove"),
        } or arguments[:1] in {("read-tree",), ("switch",)}
        if mutating:
            return SimpleNamespace(returncode=1, stdout="", stderr=stderr)
        return run_git(root, *arguments, **kwargs)

    effect = (
        partial(sync_worktree, previous=previous)
        if operation == "sync"
        else {"add": add_worktree, "remove": remove_worktree, "attach": attach_worktree}[operation]
    )
    with pytest.raises(ValueError, match=rf"^{stderr}$"):
        effect(repo, target, head=head, branch="linked", runner=runner)

    assert target.exists() is (operation != "add")


def test_worktree_record_fails_closed_on_observation_error(tmp_path) -> None:
    def runner(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="observation failed")

    with pytest.raises(ValueError, match=r"^worktree_effect_observation_failed$"):
        worktree_record(tmp_path, tmp_path / "linked", runner=runner)


def test_worktree_record_rejects_duplicate_path_records(tmp_path) -> None:
    target = tmp_path / "linked"
    target.mkdir()
    block = f"worktree {target}\nHEAD {'a' * 40}\ndetached\n"

    def runner(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout=f"{block}\n{block}", stderr="")

    with pytest.raises(ValueError, match=r"^worktree_effect_observation_ambiguous$"):
        worktree_record(tmp_path, target, runner=runner)
