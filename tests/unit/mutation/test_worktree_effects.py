"""Recognize and attest exact worktree effects without repeating completed changes."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from threading import Event

import pytest

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.adapters.repo.worktree_effects import attach_worktree
from ethos.adapters.repo.worktree_effects import hold_worktree_refs
from ethos.adapters.repo.worktree_effects import remove_worktree
from ethos.adapters.repo.worktree_effects import sync_worktree
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime


@pytest.mark.parametrize("interrupted", [False, True])
def test_worktree_ref_assertions_hold_all_inputs_and_release_on_failure(
    tmp_path: Path, *, interrupted: bool
) -> None:
    """Original governed hooks admit held assertions, not ref movements or deletions."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    previous = git(repo, "rev-parse", "HEAD")
    head = commit_fixture_file(repo, "next.md", "Next input\n", "fix: next input")
    refs = {
        "refs/heads/dev": head,
        "refs/heads/candidate/dev": head,
        "refs/heads/work/retained": previous,
    }
    for ref, value in refs.items():
        git(repo, "update-ref", ref, value)
    install_fixture_hook_runtime(repo)
    reflog = git(repo, "reflog", "--all")
    before = git(repo, "show-ref"), git(repo, "status", "--porcelain")
    common = repo / git(repo, "rev-parse", "--git-common-dir")
    locks = set(common.rglob("*.lock"))

    def compete() -> None:
        with hold_worktree_refs(repo, refs):
            for ref, value in refs.items():
                other = previous if value == head else head
                result = run_git(
                    repo,
                    "-c",
                    "core.filesRefLockTimeout=0",
                    "update-ref",
                    ref,
                    other,
                    value,
                    check=False,
                )
                assert result.returncode != 0
                assert git(repo, "rev-parse", ref) == value
            if interrupted:
                message = "Interrupted materialization"
                raise OSError(message)

    if interrupted:
        with pytest.raises(OSError, match="Interrupted materialization"):
            compete()
    else:
        compete()
    assert git(repo, "reflog", "--all") == reflog
    assert (git(repo, "show-ref"), git(repo, "status", "--porcelain")) == before
    assert set(common.rglob("*.lock")) == locks
    with hold_worktree_refs(repo, refs):
        assert all(git(repo, "rev-parse", ref) == value for ref, value in refs.items())
    refused = run_git(repo, "update-ref", "-d", "refs/heads/candidate/dev", head, check=False)
    assert refused.returncode != 0
    assert "candidate_ref_move_no_ref_intent" in refused.stderr
    assert git(repo, "rev-parse", "refs/heads/candidate/dev") == head
    with (
        pytest.raises(ProcessExecutionError) as failed,
        hold_worktree_refs(repo, {"refs/heads/candidate/dev": previous}),
    ):
        pytest.fail("A stale assertion must not enter the effect")
    assert failed.value.code == "worktree_effect_ref_preparation_failed"
    assert "cannot lock ref" in failed.value.cause
    assert failed.value.observation["returncode"] != 0
    assert set(common.rglob("*.lock")) == locks
    assert git(repo, "reflog", "--all") == reflog


def test_worktree_ref_holder_timeout_releases_owned_git_process(tmp_path: Path) -> None:
    """A caller deadline ends the held transaction without an operator killing it."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    refs = {"refs/heads/dev": head}
    install_fixture_hook_runtime(repo)
    common = repo / git(repo, "rev-parse", "--git-common-dir")
    locks = set(common.rglob("*.lock"))
    entered = Event()

    def expire() -> None:
        # The deadline starts before the transaction is prepared, which can take seconds under
        # proof load; a hold that outlasts the whole deadline from entry always expires it.
        with hold_worktree_refs(repo, refs, timeout_seconds=5):
            entered.set()
            Event().wait(5.1)

    with pytest.raises(ValueError, match="worktree_effect_ref_lock_timeout"):
        expire()
    assert entered.is_set()
    assert set(common.rglob("*.lock")) == locks
    with hold_worktree_refs(repo, refs):
        assert git(repo, "rev-parse", "HEAD") == head


def test_worktree_preimage_uses_content_not_index_stat_cache(tmp_path: Path) -> None:
    """Restored bytes are clean even when cached stat data differs; readers keep the index."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    path = repo / "README.md"
    original = path.read_bytes()
    os.utime(path, (1, 1))
    git(repo, "add", "README.md")
    path.write_text("temporary user change\n")
    git(repo, "status", "--porcelain")
    path.write_bytes(original)
    index = repo / git(repo, "rev-parse", "--git-path", "index")
    before = index.read_bytes()
    assert run_git(repo, "diff-files", "--quiet", check=False).returncode == 1
    assert worktree_sync_gap(repo, (repo,), "dev", head, head, head) == ""
    assert index.read_bytes() == before
    path.write_text("real user change\n")
    assert worktree_sync_gap(repo, (repo,), "dev", head, head, head) == "worktree_dirty"
    assert index.read_bytes() == before


@pytest.mark.parametrize("attach", [False, True], ids=["created", "attached"])
def test_worktree_creation_and_attachment_recognize_exact_terminal_state(tmp_path, attach) -> None:
    """Both native creation paths preserve one exact, replayable worktree binding."""
    repo = init_git_repo(tmp_path / "repo")
    head = adopt_and_commit(repo)
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    if attach:
        git(repo, "worktree", "add", "--detach", target.as_posix(), head)
    operation = attach_worktree if attach else add_worktree
    applied = operation(repo, target, head=head, branch="linked")
    recognized = operation(repo, target, head=head, branch="linked")
    assert applied.payload.body["result"]["state"] == "applied"
    assert recognized.payload.body["result"]["state"] == "recognized"
    assert recognized.payload.body["output"]["head"] == head
    assert recognized.payload.body["output"]["branch"] == "linked"
    assert recognized.predicate == "effect:git-worktree"
    assert recognized.payload.body["command"] == (
        ("git", "switch") if attach else ("git", "worktree", "add")
    )
    assert recognized.effect_digest
    assert git(target, "branch", "--show-current") == "linked"


def test_add_worktree_rejects_path_bound_to_other_head(tmp_path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = adopt_and_commit(repo)
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    add_worktree(repo, target, head=head, branch="linked")

    with pytest.raises(ValueError, match="worktree_effect_binding_stale"):
        add_worktree(repo, target, head="0" * len(head), branch="linked")


@pytest.mark.parametrize("content_absent", [False, True])
def test_remove_worktree_recognizes_absent_terminal_state(tmp_path, content_absent) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = adopt_and_commit(repo)
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
    head = adopt_and_commit(repo)
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
    head = adopt_and_commit(repo)
    target = tmp_path / "linked"
    git(repo, "branch", "linked", head)
    add_worktree(repo, target, head=head, branch="linked")

    with pytest.raises(ValueError, match="worktree_effect_binding_stale"):
        remove_worktree(repo, target, head=head, branch="other")


@pytest.mark.parametrize("dangling", [False, True])
def test_remove_worktree_rejects_link_root_before_resolving(tmp_path, dangling) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = adopt_and_commit(repo)
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
    previous = adopt_and_commit(repo)
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


@pytest.mark.parametrize("dirty", [False, True], ids=["restored", "changed"])
def test_sync_worktree_refreshes_only_native_index_stat_cache(tmp_path, dirty) -> None:
    """A clean byte preimage must sync despite stale stats; real edits must survive."""
    repo = init_git_repo(tmp_path / "repo")
    previous = adopt_and_commit(repo)
    material = repo / "README.md"
    original = material.read_bytes()
    material.write_text("# accepted replacement\n", encoding="utf-8")
    git(repo, "add", "README.md")
    head = git(repo, "commit-tree", git(repo, "write-tree"), "-p", previous, "-m", "fix: sync")
    git(repo, "read-tree", previous)
    material.write_bytes(b"unaccepted user content\n" if dirty else original)
    index_before = git(repo, "write-tree")
    assert index_before == git(repo, "rev-parse", f"{previous}^{{tree}}")
    assert run_git(repo, "diff-files", "--quiet", check=False).returncode == 1
    assert worktree_sync_gap(repo, (repo,), "dev", previous, previous, head) == (
        "worktree_dirty" if dirty else ""
    )
    git(repo, "update-ref", "refs/heads/dev", head, previous)

    if dirty:
        with pytest.raises(ValueError, match=r"not uptodate|worktree_effect_preimage_dirty"):
            sync_worktree(repo, repo, branch="dev", previous=previous, head=head)
        assert material.read_bytes() == b"unaccepted user content\n"
        assert git(repo, "write-tree") == index_before
    else:
        applied = sync_worktree(repo, repo, branch="dev", previous=previous, head=head)
        assert applied.payload.body["result"]["state"] == "applied"
        assert material.read_text() == "# accepted replacement\n"
        assert git(repo, "write-tree") == git(repo, "rev-parse", f"{head}^{{tree}}")
