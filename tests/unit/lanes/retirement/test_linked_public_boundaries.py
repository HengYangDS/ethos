from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.effects as effects
import ethos.adapters.mutation.lane_retirement.linked as linked
from ethos.adapters.mutation.lane_retirement.linked import LinkedRetirementRequest
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.contracts.branch.roles import BranchRolePolicy


def _lane(
    *,
    branch: str = "work/source",
    head: str = "a" * 40,
    path: str = "/lane",
    gaps: list[str] | None = None,
    lease_state: str = "valid",
    holder: str = "agent:test:holder",
) -> dict[str, object]:
    return {
        "branch": branch,
        "head": head,
        "path": path,
        "required_gaps": gaps or [],
        "lease_state": lease_state,
        "lease": {"holder_ref": holder},
    }


@pytest.mark.parametrize(
    ("branch", "lanes", "retirement_request", "gaps"),
    [
        ("", [], LinkedRetirementRequest(apply=True, authorize=True), {"retire_branch_required"}),
        (
            "work/missing",
            [],
            LinkedRetirementRequest(branch="work/missing"),
            {"retire_branch_not_found"},
        ),
        (
            "work/source",
            [_lane()],
            LinkedRetirementRequest(branch="work/source", apply=True),
            {"authorization_required", "expect_head_required"},
        ),
        (
            "work/source",
            [_lane(gaps=["work_lane_dirty"])],
            LinkedRetirementRequest(
                branch="work/source", expect_head="b" * 40, apply=True, authorize=True
            ),
            {"work_lane_dirty", "expect_head_mismatch"},
        ),
    ],
)
def test_landed_pre_effect_matrix_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    branch: str,
    lanes: list[dict[str, object]],
    retirement_request: LinkedRetirementRequest,
    gaps: set[str],
) -> None:
    monkeypatch.setattr(effects, "actor_ref", lambda: "agent:test:holder")

    assert gaps <= set(
        linked._landed_gaps(  # noqa: SLF001
            branch=branch, request=retirement_request, lanes=lanes
        )
    )


@pytest.mark.parametrize(
    ("branch", "linked_lane", "gap"),
    [
        ("", {}, "superseded_retire_branch_required"),
        ("work/missing", {}, "superseded_retire_branch_not_found"),
        ("dev", {}, "superseded_retire_not_work_lane"),
        ("work/source", {}, "superseded_retire_worktree_not_linked"),
    ],
)
def test_superseded_target_resolution_rejects_invalid_subjects(
    monkeypatch: pytest.MonkeyPatch,
    branch: str,
    linked_lane: dict[str, object],
    gap: str,
) -> None:
    policy = BranchRolePolicy()
    monkeypatch.setattr(
        linked,
        "output",
        lambda _repo, *args: (
            None
            if branch == "work/missing" and args == ("rev-parse", "--verify", branch)
            else branch
        ),
    )
    assert linked._superseded_target_gaps(  # noqa: SLF001
        Path("/repo"), policy, branch, linked_lane
    ) == [gap]


def test_source_lane_successor_authority_filters_only_missing_source_lease() -> None:
    lane = _lane(
        gaps=["work_lane_missing_lease:work/source", "work_lane_dirty"],
        lease_state="valid",
    )

    assert linked._source_lane_gaps(  # noqa: SLF001
        lane, branch="work/source", successor=_lane()
    ) == [
        "work_lane_dirty",
        "successor_retire_target_lease_present",
    ]


@pytest.mark.parametrize(
    ("source", "absorbed", "accepted", "successor", "lane", "ancestor", "gap"),
    [
        ("", "a", "a", {}, {}, True, ""),
        ("a", "", "a", {}, {}, True, ""),
        ("a", "b", "b", {}, {}, False, "superseded_lane_not_absorbed_by_accepted"),
        ("a", "b", "b", {}, {"archive_absorption": {"change": "x"}}, False, ""),
        ("a", "c", "b", _lane(head="c"), {}, False, "superseded_lane_not_absorbed_by_successor"),
    ],
)
def test_absorption_authority_matrix(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    absorbed: str,
    accepted: str,
    successor: dict[str, object],
    lane: dict[str, object],
    ancestor: int,
    gap: str,
) -> None:
    monkeypatch.setattr(effects, "absorbed", lambda *_args: False)
    monkeypatch.setattr(linked, "is_ancestor", lambda *_args: ancestor)

    assert (
        linked._absorption_gap(  # noqa: SLF001
            Path("/repo"),
            source_head=source,
            absorbed_by=absorbed,
            accepted_head=accepted,
            successor=successor,
            lane=lane,
        )
        == gap
    )


def test_linked_apply_rejects_missing_control_root_before_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    worktree = {"role": "work_lane", "branch": "work/source", "head": head, "path": "/lane"}
    monkeypatch.setattr(linked, "repository_root", lambda root: root)
    monkeypatch.setattr(linked, "workspace_status", lambda _repo: {"worktrees": [worktree]})
    monkeypatch.setattr(linked, "load_branch_role_policy", lambda _repo: BranchRolePolicy())
    monkeypatch.setattr(linked, "output", lambda *_args: "b" * 40)
    monkeypatch.setattr(linked, "leases_by_branch", lambda _repo: {})
    monkeypatch.setattr(effects, "control_root", lambda *_args: None)
    monkeypatch.setattr(effects, "lane", lambda *_args, **_kwargs: _lane(head=head))
    monkeypatch.setattr(linked, "_with_archive_absorption", lambda _repo, lane, _head: lane)
    monkeypatch.setattr(effects, "holder_gaps", lambda _lane: [])
    applied: list[bool] = []
    monkeypatch.setattr(effects, "apply_retirement", lambda *_args, **_kwargs: applied.append(True))

    report = retire_linked_work_lane(
        root=Path("/repo"),
        mode="landed",
        request=LinkedRetirementRequest(
            branch="work/source", expect_head=head, authorize=True, apply=True
        ),
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["retirement_control_root_unavailable"]
    assert applied == []


def test_linked_effect_failure_is_projected_as_a_fresh_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    control = Path("/control")
    worktree = {"role": "work_lane", "branch": "work/source", "head": head, "path": "/lane"}
    monkeypatch.setattr(linked, "repository_root", lambda root: root)
    monkeypatch.setattr(linked, "workspace_status", lambda _repo: {"worktrees": [worktree]})
    monkeypatch.setattr(linked, "load_branch_role_policy", lambda _repo: BranchRolePolicy())
    monkeypatch.setattr(linked, "output", lambda *_args: "b" * 40)
    monkeypatch.setattr(linked, "leases_by_branch", lambda _repo: {})
    monkeypatch.setattr(effects, "control_root", lambda *_args: control)
    monkeypatch.setattr(effects, "lane", lambda *_args, **_kwargs: _lane(head=head))
    monkeypatch.setattr(linked, "_with_archive_absorption", lambda _repo, lane, _head: lane)
    monkeypatch.setattr(effects, "holder_gaps", lambda _lane: [])
    monkeypatch.setattr(
        effects,
        "apply_retirement",
        lambda *_args, **_kwargs: {
            "required_gaps": ["branch_delete_failed_after_worktree_removed"],
            "stderr": "git effect rejected",
            "observed": {"ref_state": "expected"},
        },
    )

    report = retire_linked_work_lane(
        root=Path("/repo"),
        mode="landed",
        request=LinkedRetirementRequest(
            branch="work/source", expect_head=head, authorize=True, apply=True
        ),
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["branch_delete_failed_after_worktree_removed"]
    assert report["observed"] == {"ref_state": "expected"}
    assert report["mutation"]["decision"]["verdict"] == "block"
