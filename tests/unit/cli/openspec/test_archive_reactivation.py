"""Accepted archive reactivation generation contract."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.openspec.start_effect import current_generation_scope
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_exact_accepted_archive_reactivation_defines_one_current_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, candidate = start_adopted_candidate(tmp_path)
    archive = candidate / "openspec/changes/archive/2026-08-08-restored-change"
    archive.mkdir(parents=True)
    (archive / ".openspec.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    (archive / "commitment.toml").write_text(
        "schema_version = 1\n"
        'id = "change:restored-change"\n'
        'intent = "Restore one exact accepted archive."\n'
        'subjects = ["repository:self"]\n'
        'scope = ["README.md", "openspec/changes/restored-change/**"]\n'
        'permissions = ["repository.read", "work-lane.write"]\n',
        encoding="utf-8",
    )
    git(candidate, "add", archive.relative_to(candidate).as_posix())
    git(candidate, "commit", "-m", "archive restored change")
    accepted = git(candidate, "rev-parse", "HEAD")
    worktree = tmp_path / "repo-work-restored-change"
    branch = "work/restored-change"
    git(candidate, "worktree", "add", "-b", branch, worktree.as_posix(), accepted)
    active = worktree / "openspec/changes/restored-change"
    active.parent.mkdir(parents=True, exist_ok=True)
    (worktree / archive.relative_to(candidate)).rename(active)
    git(worktree, "add", "-A")
    git(worktree, "commit", "-m", "reactivate exact accepted archive")
    restored = git(worktree, "rev-parse", "HEAD")
    acquire_lease(
        state_database(repository),
        lease=exact_lease(
            repo=repository,
            branch=branch,
            holder_ref="agent:test:case:reactivation",
            expected_head=restored,
            carrier="openspec/changes/restored-change/commitment.toml",
            change_id="restored-change",
        ),
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:reactivation")
    readme = worktree / "README.md"
    readme.write_text("# restored generation\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    git(worktree, "commit", "-m", "implement restored generation")
    implemented = git(worktree, "rev-parse", "HEAD")
    advanced = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{branch}",
        old_value=restored,
        new_value=implemented,
    )
    assert advanced["state"] == "lease_ref_advanced"

    lease = leases_by_branch(worktree)[branch]
    scope = current_generation_scope(
        worktree,
        head=implemented,
        repository_id=load_repository_commitment(worktree).id,
        commitment=load_commitment(
            worktree,
            carrier=str(lease["base_commitment_path"]),
            change_id="restored-change",
            tree_ref=implemented,
        ),
        lease=lease,
        fallback_paths=(
            "README.md",
            "openspec/changes/restored-change/.openspec.yaml",
            "openspec/changes/restored-change/commitment.toml",
        ),
    )

    assert scope.gaps == ()
    assert scope.paths == (
        "README.md",
        "openspec/changes/restored-change/.openspec.yaml",
        "openspec/changes/restored-change/commitment.toml",
    )
    assert scope.start_authority["predicate"] == "effect:openspec-archive-reactivation"
    assert {item.source for item in scope.attributions if item.state == "authorized"} == {
        "archive_reactivation"
    }
