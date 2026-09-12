"""Exact Git effects preserve preimages and reject unsafe recovery operations."""

from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from collections.abc import Mapping


def _cas_plan(repo: Path, old: str, new: str):
    effect = GitEffect(updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)})
    facts = Facts(
        repository=f"repository:{repo.name}",
        head=old,
        tree=git(repo, "rev-parse", f"{old}^{{tree}}"),
        observed_at=datetime(2026, 8, 10, tzinfo=UTC),
        values={"refs": {"refs/heads/dev": old}, "assertions": {}},
    )
    authority = commitment_fixture(
        id="authority:test:git-effect", acceptance=("acceptance:fixture",)
    )
    return effect, compile_git_effect_plan(
        authority,
        facts,
        prior_attestations={},
        policy={"operation": "git.ref.compare-and-swap", "effect_digest": effect.digest()},
        effect=effect,
    )


def test_stage_effects_reject_missing_paths_stale_heads_and_git_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="git_effect_stage_paths_missing"):
        git_effects.stage_git_paths(repo, ())

    def rejected(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(("git", "add"), 1, "", "index rejected")

    with pytest.raises(ValueError, match="index rejected"):
        git_effects.stage_git_paths(repo, ("README.md",), runner=rejected)

    commit_fixture_file(repo, "next.txt", "next\n", "advance")
    with pytest.raises(ValueError, match="git_effect_head_stale"):
        git_effects.stage_git_worktree(repo, previous=head)
    monkeypatch.setattr(git_effects, "current_tracked_head", lambda _root: "observed")
    monkeypatch.setattr(
        git_effects,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess((), 1, "", ""),
    )
    with pytest.raises(ValueError, match="git_effect_stage_failed"):
        git_effects.stage_git_worktree(repo, previous="observed")


def test_worktree_postimage_is_exact_and_does_not_mutate_the_real_index(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    index_tree = git(repo, "write-tree")
    readme = repo / "README.md"
    readme.write_text("changed\n", encoding="utf-8")
    created = repo / "created.txt"
    created.write_text("created\n", encoding="utf-8")
    status = git(repo, "status", "--short")

    with observe_worktree_postimage(repo, previous=head) as observed:
        temporary_index = Path(observed.environment["GIT_INDEX_FILE"])
        temporary_objects = Path(observed.environment["GIT_OBJECT_DIRECTORY"])
        assert observed.tree != index_tree
        assert observed.changed_paths == ("README.md", "created.txt")
        assert git(repo, "write-tree") == index_tree
        assert git(repo, "status", "--short") == status
        assert readme.read_text(encoding="utf-8") == "changed\n"
        assert created.read_text(encoding="utf-8") == "created\n"
        assert temporary_index.is_file()
        assert temporary_objects.is_dir()

    assert not temporary_index.exists()
    assert not temporary_objects.exists()
    assert git(repo, "write-tree") == index_tree
    assert git(repo, "status", "--short") == status


def test_move_and_compensation_refuse_unsafe_paths_and_restore_exact_tree(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    source = repo / "source"
    source.mkdir()
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    git(repo, "add", "source/tracked.txt")
    git(repo, "commit", "-m", "add source")
    head = git(repo, "rev-parse", "HEAD")

    git_effects.move_tracked_tree(repo, "source", "archive/source")
    git_effects.stage_git_worktree(repo, previous=head)
    assert (repo / "archive/source/tracked.txt").is_file()
    git_effects.compensate_git_worktree(repo, head=head, untracked_path="archive")
    assert (repo / "source/tracked.txt").is_file()
    assert not (repo / "archive").exists()
    with pytest.raises(ValueError, match="git_effect_compensation_path_tracked"):
        git_effects.remove_untracked_tree(repo, "source")
    assert (repo / "source/tracked.txt").read_text() == "tracked\n"

    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="git_effect_move_path_outside_root"):
        git_effects.move_tracked_tree(repo, "source", "../outside/moved")
    with pytest.raises(ValueError, match="git_effect_move_binding_stale"):
        git_effects.move_tracked_tree(repo, "missing", "target")
    (repo / "target").mkdir()
    with pytest.raises(ValueError, match="git_effect_move_binding_stale"):
        git_effects.move_tracked_tree(repo, "source", "target")
    unsafe = repo / "unsafe"
    unsafe.write_text("file\n", encoding="utf-8")
    with pytest.raises(ValueError, match="git_effect_compensation_path_unsafe"):
        git_effects.remove_untracked_tree(repo, "unsafe")
    with pytest.raises(ValueError, match="git_effect_compensation_path_outside_root"):
        git_effects.remove_untracked_tree(repo, "../outside")


@pytest.mark.parametrize("path", ["", ".", "owned/..", "alias", "alias/child", "dangling"])
def test_compensation_never_removes_the_repository_or_follows_path_links(tmp_path, path):
    repo = tmp_path / "repo"
    marker = repo / "owned/child/keep.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("not owned by this effect\n")
    (repo / "alias").symlink_to(repo / "owned", target_is_directory=True)
    (repo / "dangling").symlink_to(repo / "missing", target_is_directory=True)

    with pytest.raises(ValueError, match="git_effect_compensation_path_unsafe"):
        git_effects.remove_untracked_tree(repo, path)

    assert marker.read_text() == "not owned by this effect\n"
    assert (repo / "alias").is_symlink()
    assert (repo / "dangling").is_symlink()


def test_compensation_reports_unowned_residue_without_removing_it(tmp_path):
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    original = (repo / "README.md").read_bytes()
    (repo / "README.md").write_text("failed mutation\n")
    residue = repo / "unowned/keep.txt"
    residue.parent.mkdir()
    residue.write_text("preserve\n")

    with pytest.raises(ValueError, match="git_effect_compensation_residue"):
        git_effects.compensate_git_worktree(repo, head=head)

    assert (repo / "README.md").read_bytes() == original
    assert residue.read_text() == "preserve\n"
    assert git(repo, "rev-parse", "HEAD") == head


def test_created_path_compensation_reports_restore_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    monkeypatch.setattr(
        git_effects,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ("git", "restore"), 1, "", "restore rejected"
        ),
    )

    with pytest.raises(ValueError, match="restore rejected"):
        git_effects.compensate_created_paths(
            repo,
            head="a" * 40,
            paths=("new/path",),
            untracked_root="new",
        )
    with pytest.raises(ValueError, match="restore rejected"):
        git_effects.compensate_git_worktree(repo, head="a" * 40)


def test_index_restore_preserves_working_bytes_and_rejects_an_unreadable_tree(
    tmp_path: Path,
) -> None:
    """Native index recovery is exact and never claims success after Git rejects it."""
    repo = init_git_repo(tmp_path / "repo")
    original = git(repo, "write-tree")
    readme = repo / "README.md"
    readme.write_text("unstaged content survives index recovery\n")
    git(repo, "add", "README.md")

    git_effects.restore_git_index(repo, tree=original)

    assert git(repo, "write-tree") == original
    assert readme.read_text() == "unstaged content survives index recovery\n"
    with pytest.raises(ValueError, match="failed to unpack tree object"):
        git_effects.restore_git_index(repo, tree="f" * 40)
    assert git(repo, "write-tree") == original
    assert readme.read_text() == "unstaged content survives index recovery\n"


def test_created_path_compensation_preserves_prior_index_and_unstaged_overlay(
    tmp_path: Path,
) -> None:
    """Remove only newly owned paths while retaining both kinds of prior edits."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    readme = repo / "README.md"
    readme.write_text("prior staged edit\n")
    git(repo, "add", "README.md")
    readme.write_text("prior unstaged edit\n")
    index = git(repo, "write-tree")
    created = repo / "new/artifact"
    created.parent.mkdir()
    created.write_text("failed effect output\n")
    git_effects.stage_git_paths(repo, ("new/artifact",))

    git_effects.compensate_created_paths(
        repo, head=head, paths=("new/artifact",), untracked_root="new"
    )

    assert git(repo, "write-tree") == index
    assert readme.read_text() == "prior unstaged edit\n"
    assert git(repo, "show", ":README.md") == "prior staged edit"
    assert not created.parent.exists()
    git_effects.remove_untracked_tree(repo, "new")
    assert git(repo, "rev-parse", "HEAD") == head


def test_compensation_refuses_deletion_when_native_index_observation_fails(
    tmp_path: Path,
) -> None:
    """An unreadable index is unknown ownership, not proof that content is untracked."""
    repo = init_git_repo(tmp_path / "repo")
    owned = repo / "owned/keep.txt"
    owned.parent.mkdir()
    owned.write_text("preserve on failed observation\n")
    index = repo / ".git/index"
    original = index.read_bytes()
    index.write_bytes(b"invalid native index\n")

    with pytest.raises(ValueError, match=r"fatal:.*index"):
        git_effects.remove_untracked_tree(repo, "owned")

    assert owned.read_text() == "preserve on failed observation\n"
    assert index.read_bytes() == b"invalid native index\n"
    index.write_bytes(original)
    git_effects.remove_untracked_tree(repo, "owned")
    assert not owned.parent.exists()


@pytest.mark.parametrize("missing_candidate", [False, True])
def test_accepted_effect_rejects_missing_candidate_or_unbound_runtime_before_cas(
    tmp_path: Path, *, missing_candidate: bool
) -> None:
    """A carried plan cannot replace fresh candidate and hook binding checks."""
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    git(repo, "add", ".ethos/profile.toml")
    git(repo, "commit", "-m", "test: declare repository")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "test: candidate")
    candidate = tmp_path / "candidate"
    git(repo, "worktree", "add", "-b", "candidate/dev", str(candidate), new)
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)},
        assertions={"refs/heads/candidate/dev": new},
    )
    facts = Facts(
        repository=f"repository:{repo.name}",
        head=old,
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        observed_at=datetime.now(UTC),
        values={
            "refs": {"refs/heads/dev": old},
            "assertions": {"refs/heads/candidate/dev": new},
            "candidate_worktree_path": str(
                tmp_path / "missing" if missing_candidate else candidate
            ),
        },
    )
    plan = compile_git_effect_plan(
        None,
        facts,
        prior_attestations={},
        policy={
            "operation": "git.ref.compare-and-swap",
            "transition": "candidate.accept",
            "candidate_branch": "candidate/dev",
            "effect_digest": effect.digest(),
        },
        effect=effect,
    )
    expected = "binding_stale" if missing_candidate else "hook_invalid"

    with pytest.raises(ValueError, match=f"git_effect_candidate_{expected}"):
        git_effects.execute_git_effect(repo, plan, issuer="agent:test:case:agent-test")

    assert git(repo, "rev-parse", "HEAD") == old
    assert git(candidate, "rev-parse", "HEAD") == new
    assert git(repo, "status", "--short") == ""


def test_exact_ref_cas_compensates_a_failed_postcondition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    git(repo, "add", ".ethos/profile.toml")
    git(repo, "commit", "-m", "declare repository identity")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect, plan = _cas_plan(repo, old, new)
    observe = git_effects.observe_git_effect
    injected = False

    def stale_once(
        root: Path, effect: GitEffect, *, environment: Mapping[str, str] | None = None
    ) -> dict[str, object]:
        nonlocal injected
        observed = observe(root, effect, environment=environment)
        if not injected and observed["refs"] == {"refs/heads/dev": new}:
            injected = True
            return {**observed, "refs": {"refs/heads/dev": old}}
        return observed

    monkeypatch.setattr(git_effects, "observe_git_effect", stale_once)

    with pytest.raises(ValueError, match="git_effect_postcondition_failed"):
        git_effects.execute_git_effect(repo, plan, issuer="agent:test:case:one")

    assert git(repo, "rev-parse", "dev") == old
    assert effect.updates["refs/heads/dev"].desired == new
