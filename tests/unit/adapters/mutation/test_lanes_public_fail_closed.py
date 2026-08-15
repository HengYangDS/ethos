from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.mutation.lanes as lanes

if TYPE_CHECKING:
    import pytest


def test_candidate_lane_start_missing_and_drift_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert lanes.candidate_lane_start_gap(
        tmp_path, {"exists": False, "worktree_exists": False}
    ) == (
        "candidate_branch_missing",
        {},
    )
    assert lanes.candidate_lane_start_gap(tmp_path, {"exists": True, "worktree_exists": False}) == (
        "candidate_worktree_missing",
        {},
    )
    candidate = {
        "exists": True,
        "worktree_exists": True,
        "worktree_path": tmp_path,
        "branch": "candidate/dev",
        "head": "a" * 40,
    }
    monkeypatch.setattr(lanes, "changed_paths", lambda _path: ("dirty",))
    assert lanes.candidate_lane_start_gap(tmp_path, candidate)[0] == "candidate_worktree_dirty"


def test_lane_start_target_collision_prefers_existing_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "lane"
    target.symlink_to(tmp_path / "missing")
    monkeypatch.setattr(lanes, "ref_head", lambda *_args: "existing")

    assert lanes.lane_start_carrier_gap(tmp_path, target=target, branch="work/test") == (
        "lane_start_target_path_exists"
    )


def test_source_lane_start_invalid_root_and_repository_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    monkeypatch.setattr(
        lanes,
        "repository_root",
        lambda _root: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "git")),
    )
    _source, blocked = lanes.source_lane_start_commitment(
        tmp_path,
        branch="work/test",
        target=target,
        holder_ref="agent:test:case:owner",
        source_root=tmp_path / "source",
    )
    assert blocked is not None
    assert blocked["required_gaps"] == ["source_work_lane_invalid"]

    monkeypatch.setattr(lanes, "repository_root", Path)
    monkeypatch.setattr(lanes, "same_git_repository", lambda *_args: False)
    _source, blocked = lanes.source_lane_start_commitment(
        tmp_path,
        branch="work/test",
        target=target,
        holder_ref="agent:test:case:owner",
        source_root=tmp_path / "foreign",
    )
    assert blocked is not None
    assert blocked["required_gaps"] == ["source_work_lane_invalid"]


def test_start_work_lane_projects_state_recovery_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = SimpleNamespace(
        canonical_sibling_worktrees=False, work_branch=lambda name: f"work/{name}"
    )
    monkeypatch.setattr(lanes, "repository_root", Path)
    monkeypatch.setattr(lanes, "load_branch_role_policy", lambda _repo: policy)
    monkeypatch.setattr(
        lanes,
        "lane_start_target",
        lambda *_args, **_kwargs: ("work/test", tmp_path / "target", None),
    )
    monkeypatch.setattr(
        lanes, "admit_lane_start", lambda *_args, **_kwargs: ({"head": "abc"}, None)
    )
    monkeypatch.setattr(
        lanes,
        "lane_start_commitment",
        lambda *_args, **_kwargs: ((tmp_path, "change", "carrier", "digest", "", ""), None),
    )
    monkeypatch.setattr(
        lanes,
        "local_state_mutation_guard",
        lambda _repo: {
            "required_gaps": ["local_state_migration_required"],
            "next_action": "ethos migrate-local-state --apply",
        },
    )

    report = lanes.start_work_lane(
        root=tmp_path,
        name="test",
        commitment_path=tmp_path / "commitment.toml",
        holder_ref="agent:test:case:owner",
        apply=True,
    )

    assert report["required_gaps"] == ["local_state_migration_required"]
    assert report["next_action"] == "ethos migrate-local-state --apply"


def test_admit_lane_start_reports_carrier_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    monkeypatch.setattr(
        lanes,
        "workspace_status",
        lambda _repo: {
            "role": lanes.ROLE_ACCEPTED_ROOT,
            "dirty": False,
            "candidate": {"head": "abc"},
        },
    )
    monkeypatch.setattr(lanes, "candidate_lane_start_gap", lambda *_args: ("", {}))
    monkeypatch.setattr(lanes, "lane_start_carrier_gap", lambda *_args, **_kwargs: "collision")

    _candidate, blocked = lanes.admit_lane_start(tmp_path, branch="work/test", target=target)

    assert blocked is not None
    assert blocked["required_gaps"] == ["collision"]


def test_source_lane_start_maps_commitment_binding_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    lease = {
        "lease_state": "valid",
        "holder_ref": "agent:test:case:owner",
        "expected_head": "head",
    }
    monkeypatch.setattr(lanes, "repository_root", Path)
    monkeypatch.setattr(lanes, "same_git_repository", lambda *_args: True)
    monkeypatch.setattr(
        lanes,
        "run_git",
        lambda _root, *args, **_kwargs: SimpleNamespace(
            stdout="work/source" if args[0] == "symbolic-ref" else "head"
        ),
    )
    monkeypatch.setattr(
        lanes, "observe_lease", lambda *_args: SimpleNamespace(record=lambda: lease)
    )
    monkeypatch.setattr(lanes, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(lanes, "changed_paths", lambda _root: ())
    monkeypatch.setattr(
        lanes,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(role_for_branch=lambda _branch: lanes.ROLE_WORK_LANE),
    )
    monkeypatch.setattr(
        lanes,
        "load_lease_bound_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("lease_binding_invalid")),
    )

    _source, blocked = lanes.source_lane_start_commitment(
        tmp_path,
        branch="work/test",
        target=target,
        holder_ref="agent:test:case:owner",
        source_root=source,
    )

    assert blocked is not None
    assert blocked["required_gaps"] == ["lease_binding_invalid"]
