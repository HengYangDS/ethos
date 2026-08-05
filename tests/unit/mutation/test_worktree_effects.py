from __future__ import annotations

import pytest

from ethos.adapters.repo.config_effects import set_local_config
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.adapters.repo.worktree_effects import attach_worktree
from ethos.adapters.repo.worktree_effects import remove_worktree
from ethos.adapters.repo.worktree_effects import sync_worktree
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def test_add_worktree_recognizes_exact_terminal_state(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)

    applied = add_worktree(repo, target, head=head, branch="linked")
    recognized = add_worktree(repo, target, head=head, branch="linked")

    assert applied.statement["result"]["state"] == "applied"
    assert recognized.statement["result"]["state"] == "recognized"
    assert recognized.statement["output"]["head"] == head
    assert recognized.statement["output"]["branch"] == "linked"
    assert recognized.predicate == "effect:git-worktree"
    assert recognized.statement["command"] == ("git", "worktree", "add")
    assert recognized.effect_digest


def test_add_worktree_rejects_path_bound_to_other_head(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    add_worktree(repo, target, head=head, branch="linked")

    with pytest.raises(ValueError, match="worktree_effect_binding_stale"):
        add_worktree(repo, target, head="0" * len(head), branch="linked")


def test_remove_worktree_recognizes_absent_terminal_state(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    add_worktree(repo, target, head=head, branch="linked")

    applied = remove_worktree(repo, target, head=head, branch="linked")
    recognized = remove_worktree(repo, target, head=head, branch="linked")

    assert applied.statement["result"]["state"] == "applied"
    assert recognized.statement["result"]["state"] == "recognized"
    assert recognized.predicate == "effect:git-worktree"
    assert recognized.statement["command"] == ("git", "worktree", "remove")
    assert not target.exists()


def test_remove_worktree_rejects_inexact_binding(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    add_worktree(repo, target, head=head, branch="linked")

    with pytest.raises(ValueError, match="worktree_effect_binding_stale"):
        remove_worktree(repo, target, head=head, branch="other")


def test_sync_worktree_attests_exact_index_and_terminal_recognition(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    previous = git(repo, "rev-parse", "HEAD")
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "change")
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "worktree", "add", "-b", "linked", target.as_posix(), previous)
    git(repo, "update-ref", "refs/heads/linked", head, previous)

    applied = sync_worktree(repo, target, branch="linked", previous=previous, head=head)
    recognized = sync_worktree(repo, target, branch="linked", previous=previous, head=head)

    assert applied.statement["result"]["state"] == "applied"
    assert recognized.statement["result"]["state"] == "recognized"
    assert recognized.predicate == "effect:git-worktree-index"
    assert recognized.statement["command"] == ("git", "read-tree", "-u", "-m")
    assert recognized.statement["output"]["head"] == head
    assert recognized.statement["freshness"]["head"] == head


def test_attach_worktree_attests_switch_and_terminal_recognition(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    git(repo, "worktree", "add", "--detach", target.as_posix(), head)

    applied = attach_worktree(repo, target, branch="linked", head=head)
    recognized = attach_worktree(repo, target, branch="linked", head=head)

    assert applied.statement["result"]["state"] == "applied"
    assert recognized.statement["result"]["state"] == "recognized"
    assert recognized.predicate == "effect:git-worktree"
    assert recognized.statement["command"] == ("git", "switch")
    assert git(target, "branch", "--show-current") == "linked"


def test_local_config_attests_apply_and_terminal_recognition(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    values = {"core.hooksPath": ".githooks", "gc.packRefs": "false"}

    applied = set_local_config(repo, values)
    recognized = set_local_config(repo, values)

    assert applied.statement["result"]["state"] == "applied"
    assert recognized.statement["result"]["state"] == "recognized"
    assert recognized.statement["output"] == values
    assert recognized.predicate == "effect:git-config"
    assert git(repo, "config", "--local", "--get", "core.hooksPath") == ".githooks"
