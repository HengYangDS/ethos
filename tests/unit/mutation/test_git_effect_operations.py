from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_effects as git_effects
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _cas_plan(repo: Path, old: str, new: str):
    effect = GitEffect(updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)})
    facts = Facts(
        repository=f"repository:{repo.name}",
        head=old,
        tree=git(repo, "rev-parse", f"{old}^{{tree}}"),
        observed_at=datetime(2026, 8, 10, tzinfo=UTC),
        values={"refs": {"refs/heads/dev": old}, "assertions": {}},
    )
    authority = Commitment(
        id="authority:test:git-effect",
        intent="Apply exact ref CAS.",
        subjects=(facts.repository,),
    )
    return effect, compile_git_effect_plan(
        authority,
        facts,
        prior_attestations={},
        policy={"operation": "git.ref.compare-and-swap", "effect_digest": effect.digest()},
        effect=effect,
    )


def test_stage_effects_reject_missing_paths_stale_heads_and_git_failures(
    tmp_path: Path,
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

    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="git_effect_move_path_outside_root"):
        git_effects.move_tracked_tree(repo, "source", "../outside/moved")
    unsafe = repo / "unsafe"
    unsafe.write_text("file\n", encoding="utf-8")
    with pytest.raises(ValueError, match="git_effect_compensation_path_unsafe"):
        git_effects.remove_untracked_tree(repo, "unsafe")


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


def test_exact_ref_cas_compensates_a_failed_postcondition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    repository = repo / ".ethos/commitment.toml"
    repository.parent.mkdir(parents=True, exist_ok=True)
    repository.write_text(
        'schema_version = 1\nid = "repository:repo"\nintent = "Govern."\n'
        'subjects = ["repository:repo"]\n',
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/commitment.toml")
    git(repo, "commit", "-m", "declare repository identity")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect, plan = _cas_plan(repo, old, new)
    observe = git_effects.observe_git_effect
    injected = False

    def stale_once(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal injected
        observed = observe(*args, **kwargs)
        if not injected and observed["refs"] == {"refs/heads/dev": new}:
            injected = True
            return {**observed, "refs": {"refs/heads/dev": old}}
        return observed

    monkeypatch.setattr(git_effects, "observe_git_effect", stale_once)

    with pytest.raises(ValueError, match="git_effect_postcondition_failed"):
        git_effects.execute_git_effect(repo, plan, issuer="agent:test:case:one")

    assert git(repo, "rev-parse", "dev") == old
    assert effect.updates["refs/heads/dev"].desired == new
