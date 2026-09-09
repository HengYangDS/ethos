from __future__ import annotations

import shutil
from pathlib import Path

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

    assert applied.payload.body["result"]["state"] == "applied"
    assert recognized.payload.body["result"]["state"] == "recognized"
    assert recognized.payload.body["output"]["head"] == head
    assert recognized.payload.body["output"]["branch"] == "linked"
    assert recognized.predicate == "effect:git-worktree"
    assert recognized.payload.body["command"] == ("git", "worktree", "add")
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


@pytest.mark.parametrize("content_absent", [False, True])
def test_remove_worktree_recognizes_absent_terminal_state(tmp_path, content_absent) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    add_worktree(repo, target, head=head, branch="linked")
    admin = Path(git(target, "rev-parse", "--absolute-git-dir"))
    if content_absent:
        shutil.rmtree(target)
        assert admin.is_dir()
        assert "prunable" in git(repo, "worktree", "list", "--porcelain")

    applied = remove_worktree(repo, target, head=head, branch="linked")
    recognized = remove_worktree(repo, target, head=head, branch="linked")

    assert applied.payload.body["result"]["state"] == "applied"
    assert recognized.payload.body["result"]["state"] == "recognized"
    assert recognized.predicate == "effect:git-worktree"
    assert recognized.payload.body["command"] == ("git", "worktree", "remove")
    assert not target.exists()
    assert not admin.exists()
    assert git(repo, "rev-parse", "linked") == head


@pytest.mark.parametrize(
    ("drift", "after_admission"),
    [("content", True), ("locked", False), ("head", False), ("head", True), ("branch", True)],
)
def test_absent_worktree_deregistration_rejects_drift(tmp_path, drift, after_admission):
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "worktree", "add", "-b", "linked", str(target), head)
    admin = Path(git(target, "rev-parse", "--absolute-git-dir"))

    def change_binding():
        if drift == "content":
            target.mkdir()
            (target / "new.txt").write_text("not reviewed\n")
        elif drift == "locked":
            git(repo, "worktree", "lock", str(target))
        elif drift == "head":
            git(repo, "update-ref", "refs/heads/linked", f"{head}^", head)
        else:
            git(repo, "branch", "other", head)
            git(repo, f"--git-dir={admin}", "symbolic-ref", "HEAD", "refs/heads/other")

    if not after_admission:
        change_binding()
    shutil.rmtree(target)

    with pytest.raises(ValueError, match="worktree_effect_binding_stale"):
        remove_worktree(
            repo,
            target,
            head=head,
            branch="linked",
            admit=change_binding if after_admission else None,
        )
    assert admin.is_dir()
    if drift == "content":
        assert (target / "new.txt").read_text() == "not reviewed\n"


def test_remove_historical_worktree_uses_control_repository_identity(tmp_path) -> None:
    """A subject predating adoption cannot own the control repository's identity."""
    repo = init_git_repo(tmp_path / "repo")
    historical = git(repo, "rev-parse", "HEAD")
    adopt_and_commit(repo)
    target = tmp_path / "historical"
    git(repo, "worktree", "add", "-b", "topic/old", target.as_posix(), historical)

    applied = remove_worktree(repo, target, head=historical, branch="topic/old")
    recognized = remove_worktree(repo, target, head=historical, branch="topic/old")

    assert applied.payload.body["repository"] == "repository:repo"
    assert applied.payload.body["input"]["head"] == historical
    assert recognized.payload.body["result"]["state"] == "recognized"
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


@pytest.mark.parametrize("dangling", [False, True])
def test_remove_worktree_rejects_link_root_before_resolving(tmp_path, dangling) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "worktree", "add", "-b", "linked", target.as_posix(), head)
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path / "missing" if dangling else target, target_is_directory=True)
    before = git(repo, "worktree", "list", "--porcelain")

    with pytest.raises(ValueError, match="worktree_effect_binding_stale"):
        remove_worktree(repo, alias, head=head, branch="linked")

    assert alias.is_symlink()
    assert target.is_dir()
    assert git(repo, "worktree", "list", "--porcelain") == before
    assert git(target, "rev-parse", "HEAD") == head


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

    assert applied.payload.body["result"]["state"] == "applied"
    assert recognized.payload.body["result"]["state"] == "recognized"
    assert recognized.predicate == "effect:git-worktree-index"
    assert recognized.payload.body["command"] == ("git", "read-tree", "-u", "-m")
    assert recognized.payload.body["output"]["head"] == head
    assert recognized.payload.body["freshness"]["head"] == head


def test_attach_worktree_attests_switch_and_terminal_recognition(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    git(repo, "worktree", "add", "--detach", target.as_posix(), head)

    applied = attach_worktree(repo, target, branch="linked", head=head)
    recognized = attach_worktree(repo, target, branch="linked", head=head)

    assert applied.payload.body["result"]["state"] == "applied"
    assert recognized.payload.body["result"]["state"] == "recognized"
    assert recognized.predicate == "effect:git-worktree"
    assert recognized.payload.body["command"] == ("git", "switch")
    assert git(target, "branch", "--show-current") == "linked"


def test_local_config_attests_apply_and_terminal_recognition(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    values = {"core.hooksPath": ".githooks", "gc.packRefs": "false"}

    applied = set_local_config(repo, values)
    recognized = set_local_config(repo, values)

    assert applied.payload.body["result"]["state"] == "applied"
    assert recognized.payload.body["result"]["state"] == "recognized"
    assert recognized.payload.body["output"] == values
    assert recognized.predicate == "effect:git-config"
    assert recognized.commitment_digest is None
    assert recognized.payload.body["repository"] == "repository:repo"
    assert git(repo, "config", "--local", "--get", "core.hooksPath") == ".githooks"
