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


def test_start_projects_selected_package_runtime_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-feature"
    selected_command = "/runtime/python -B -I -m ethos.cli"
    monkeypatch.setattr(
        lane_start,
        "runtime_command",
        lambda _root, *arguments: " ".join((selected_command, *arguments)),
    )

    report = lane_start.start_work_lane(
        root=repo,
        name="feature",
        path=target,
        holder_ref=HOLDER,
    )

    bootstrap = report["runner_bootstrap"]
    assert bootstrap["command"] == selected_command
    assert bootstrap["environment_scope"] == "git_common_package_runtime"
    assert bootstrap["next_action"] == (
        f"{selected_command} status --root {target.as_posix()} --json"
    )
    assert "uv run" not in bootstrap["next_action"]


def _lightweight_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lane_start, "require_runtime_wheel_provenance", lambda: None)
    monkeypatch.setattr(
        lane_start,
        "runtime_command",
        lambda _root, *arguments: " ".join(
            ("/runtime/python", "-B", "-I", "-m", "ethos.cli", *arguments)
        ),
    )
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


def test_start_projects_candidate_while_observing_the_current_accepted_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-feature"
    candidate_head = git(candidate, "rev-parse", "HEAD")
    accepted_head = commit_fixture_file(
        repo,
        "accepted-only.txt",
        "accepted advanced after candidate projection\n",
        "advance accepted independently",
    )
    assert accepted_head != candidate_head
    _lightweight_runtime(monkeypatch)

    report = lane_start.start_work_lane(
        root=repo,
        name="feature",
        path=target,
        holder_ref=HOLDER,
        apply=True,
    )

    assert report["verdict"] == "pass"
    assert report["base_head"] == candidate_head
    assert git(target, "rev-parse", "HEAD") == candidate_head
    effect_evidence = report["ref_attestation"]["payload"]["body"]
    assert effect_evidence["plan"]["facts"]["head"] == accepted_head
    assert effect_evidence["input"]["head"] == accepted_head


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
    _lightweight_runtime(monkeypatch)

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


def test_start_uses_the_owned_worktree_removal_effect_for_compensation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-feature"
    _lightweight_runtime(monkeypatch)
    removed: list[tuple[Path, str, str, bool]] = []
    real_remove = lane_start.remove_worktree

    def remove(root: Path, path: Path, *, branch: str, head: str, force: bool):
        removed.append((path, branch, head, force))
        return real_remove(root, path, branch=branch, head=head, force=force)

    monkeypatch.setattr(lane_start, "remove_worktree", remove)
    monkeypatch.setattr(
        lane_start,
        "install_hook_launchers",
        lambda _root: (_ for _ in ()).throw(ValueError("hook_runtime_failed")),
    )

    report = lane_start.start_work_lane(
        root=repo,
        name="feature",
        path=target,
        holder_ref=HOLDER,
        apply=True,
    )

    assert report["required_gaps"] == ["hook_runtime_failed"]
    assert [(path, branch, force) for path, branch, _head, force in removed] == [
        (target, "work/feature", True)
    ]
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()
    assert "work/feature" not in leases_by_branch(repo)


def test_start_honors_canonical_sibling_profile_without_a_parallel_source_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    commit_fixture_file(
        repo,
        workspace.relative_to(repo).as_posix(),
        "[branch_roles]\ncanonical_sibling_worktrees = true\n",
        "configure canonical Work Lanes",
    )
    _lightweight_runtime(monkeypatch)

    report = lane_start.start_work_lane(
        root=repo,
        name="semantic lane",
        holder_ref=HOLDER,
    )

    lane_id = str(report["branch"]).removeprefix("work/")
    assert lane_id.endswith("-semantic-lane")
    assert report["path"] == (repo.parent / f"{repo.name}-worktrees" / lane_id).as_posix()


def test_start_blocks_before_effects_when_selected_runtime_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-feature"
    monkeypatch.setattr(
        lane_start,
        "runtime_command",
        lambda *_args: (_ for _ in ()).throw(ValueError("hook_runtime_current_missing")),
    )

    report = lane_start.start_work_lane(
        root=repo,
        name="feature",
        path=target,
        holder_ref=HOLDER,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["hook_runtime_current_missing"]
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()
    assert "work/feature" not in leases_by_branch(repo)


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
