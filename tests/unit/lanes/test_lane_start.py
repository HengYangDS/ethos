"""Public Work Lane start behavior without a duplicate intent carrier."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.mutation.lane_lifecycle.start as lane_start
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


HOLDER = "agent:test:case:lane-start"


def _lightweight_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lane_start, "require_runtime_wheel_provenance", lambda: None)
    monkeypatch.setattr(
        lane_start,
        "install_hook_launchers",
        lambda _root: {"state": "current", "required_gaps": []},
    )


def test_start_projects_exact_candidate_and_minimal_lease_without_commitment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-feature"
    head = git(candidate, "rev-parse", "HEAD")
    _lightweight_runtime(monkeypatch)

    report = lane_start.start_work_lane(
        root=repo,
        name="feature",
        path=target,
        holder_ref=HOLDER,
        apply=True,
    )

    assert report["verdict"] == "pass"
    assert report["head"] == report["base_head"] == head
    assert git(target, "rev-parse", "HEAD") == head
    assert git(target, "status", "--short") == ""
    assert tuple(repo.parent.rglob("commitment.toml")) == ()
    lease = leases_by_branch(repo)["work/feature"]
    assert set(lease) == {
        "subject",
        "lease_state",
        "lane_ref",
        "holder_ref",
        "generation",
        "expires_at",
    }
    assert {name: lease[name] for name in ("lane_ref", "holder_ref", "generation")} == {
        "lane_ref": "work/feature",
        "holder_ref": HOLDER,
        "generation": 1,
    }
    assert report["ref_attestation"]["commitment_digest"] is None


def test_start_dry_run_is_side_effect_free_and_apply_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-feature"
    head = git(candidate, "rev-parse", "HEAD")
    _lightweight_runtime(monkeypatch)

    planned = lane_start.start_work_lane(
        root=repo,
        name="feature",
        path=target,
        holder_ref=HOLDER,
    )

    assert planned["state"] == "planned"
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()
    assert "work/feature" not in leases_by_branch(repo)

    first = lane_start.start_work_lane(
        root=repo,
        name="feature",
        path=target,
        holder_ref=HOLDER,
        apply=True,
    )
    second = lane_start.start_work_lane(
        root=repo,
        name="feature",
        path=target,
        holder_ref=HOLDER,
        apply=True,
    )

    assert first["verdict"] == second["verdict"] == "pass"
    assert first["head"] == second["head"] == head
    assert leases_by_branch(repo)["work/feature"]["generation"] == 1


def test_start_compensates_ref_worktree_and_lease_when_hook_binding_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-feature"
    monkeypatch.setattr(lane_start, "require_runtime_wheel_provenance", lambda: None)

    def fail_hook(_root: Path) -> dict[str, object]:
        msg = "hook_runtime_failed"
        raise ValueError(msg)

    monkeypatch.setattr(lane_start, "install_hook_launchers", fail_hook)

    report = lane_start.start_work_lane(
        root=repo,
        name="feature",
        path=target,
        holder_ref=HOLDER,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["hook_runtime_failed"]
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()
    assert "work/feature" not in leases_by_branch(repo)


def test_start_honors_canonical_sibling_profile_without_a_parallel_source_lane(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    commit_fixture_file(
        repo,
        workspace.relative_to(repo).as_posix(),
        "[branch_roles]\ncanonical_sibling_worktrees = true\n",
        "configure canonical Work Lanes",
    )

    report = lane_start.start_work_lane(
        root=repo,
        name="semantic lane",
        holder_ref=HOLDER,
    )

    lane_id = str(report["branch"]).removeprefix("work/")
    assert lane_id.endswith("-semantic-lane")
    assert report["path"] == (repo.parent / f"{repo.name}-worktrees" / lane_id).as_posix()


def test_start_rejects_noncanonical_path_before_effects(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    commit_fixture_file(
        repo,
        workspace.relative_to(repo).as_posix(),
        "[branch_roles]\ncanonical_sibling_worktrees = true\n",
        "configure canonical Work Lanes",
    )

    report = lane_start.start_work_lane(
        root=repo,
        name="semantic lane",
        path=tmp_path / "outside",
        holder_ref=HOLDER,
    )

    assert report["required_gaps"] == ["work_lane_path_not_canonical"]
    assert not (tmp_path / "outside").exists()
