"""Exact Git effects preserve preimages and reject unsafe recovery operations."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git as git_adapter
import ethos.adapters.repo.git_effects as git_effects
import ethos.adapters.repo.worktree_postimage as postimage
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from tests.support.git_effect import fixture
from tests.support.git_effect import plan as effect_plan
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from collections.abc import Mapping


def test_stage_effects_reject_stale_heads_and_git_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
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


@pytest.mark.parametrize("state", ["clean", "unstaged", "staged", "mixed"])
def test_execution_source_reads_only_its_consumed_native_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """Tree-only consumers retain fresh content and index checks without a path scan."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    readme = repo / "README.md"
    if state != "clean":
        readme.write_text("selected source\n")
    if state in {"staged", "mixed"}:
        git(repo, "add", "README.md")
    if state == "mixed":
        readme.write_text("unstaged overlay\n")
    index_tree = git(repo, "write-tree")
    status = git(repo, "status", "--short")
    index = repo / ".git/index"
    index_bytes = index.read_bytes()
    with observe_worktree_postimage(repo, previous=head) as observed:
        expected_tree = observed.tree
        assert observed.changed_paths == (() if state == "clean" else ("README.md",))
    observed_git = postimage.run_git
    commands: list[tuple[str, ...]] = []
    scratch: set[Path] = set()

    def observe(root: Path, *args: str, **kwargs):
        commands.append(args)
        environment = kwargs.get("env") or {}
        scratch.update(
            Path(environment[name])
            for name in ("GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY")
            if name in environment
        )
        return observed_git(root, *args, **kwargs)

    monkeypatch.setattr(postimage, "run_git", observe)
    monkeypatch.setattr(git_adapter, "run_git", observe)
    expected_index = "" if state in {"staged", "mixed"} else index_tree

    assert postimage.observe_execution_source(repo, head, index_tree) == {
        "worktree": expected_tree,
        "index": expected_index,
    }
    assert len(commands) == 5
    assert ("add", "--all") in commands
    assert ("write-tree",) in commands
    assert not any("--name-only" in args for args in commands)
    assert scratch
    assert all(not path.exists() for path in scratch)
    assert index.read_bytes() == index_bytes
    assert git(repo, "status", "--short") == status

    commands.clear()
    readme.write_text("later observed source\n")
    refreshed = postimage.observe_execution_source(repo, head, index_tree)
    assert refreshed["worktree"] != expected_tree
    assert refreshed["index"] == expected_index
    assert len(commands) == 5
    assert all(not path.exists() for path in scratch)
    assert index.read_bytes() == index_bytes


@pytest.mark.parametrize("failure", ["index", "stage"])
def test_execution_source_failure_preserves_index_and_releases_owned_scratch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """A narrower result projection retains native refusal and quarantine cleanup."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "write-tree")
    index = repo / ".git/index"
    if failure == "index":
        index.write_bytes(b"invalid native index\n")
    original = index.read_bytes()
    observed_git = postimage.run_git
    scratch: set[Path] = set()

    def observe(root: Path, *args: str, **kwargs):
        environment = kwargs.get("env") or {}
        scratch.update(
            Path(environment[name])
            for name in ("GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY")
            if name in environment
        )
        if failure == "stage" and args == ("add", "--all"):
            return subprocess.CompletedProcess(args, 1, "", "native stage rejected")
        return observed_git(root, *args, **kwargs)

    monkeypatch.setattr(postimage, "run_git", observe)
    with pytest.raises(ValueError, match="proof_execution_source_unavailable"):
        postimage.observe_execution_source(repo, head, tree)

    assert scratch
    assert all(not path.exists() for path in scratch)
    assert index.read_bytes() == original


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


def test_compensation_reports_restore_failure(
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
    case = fixture(tmp_path)
    repo, old, new = case.repo, case.old, case.new
    candidate = tmp_path / "candidate"
    git(repo, "worktree", "add", "-b", "candidate/dev", str(candidate), new)
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)},
        assertions={"refs/heads/candidate/dev": new},
    )
    plan = compile_observed_git_effect(
        repo,
        None,
        effect,
        head=old,
        policy={"operation": "candidate.accept", "candidate_branch": "candidate/dev"},
        values={
            "candidate_worktree_path": str(tmp_path / "missing" if missing_candidate else candidate)
        },
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
    case = fixture(tmp_path)
    repo, old, new, effect = case.repo, case.old, case.new, case.effect
    plan = effect_plan(repo, effect)
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
