from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.effects as effects
import ethos.adapters.mutation.lane_retirement.linked as linked
import ethos.adapters.mutation.lane_retirement.linked_admission as linked_admission
from ethos.adapters.mutation.lane_retirement.linked import LinkedRetirementRequest
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path


SOURCE = "work/source"
SUCCESSOR = "work/successor"
SOURCE_HEAD = "a" * 40
ACCEPTED = "b" * 40
SUCCESSOR_HEAD = "c" * 40


def _worktree(branch: str = SOURCE, head: str = SOURCE_HEAD) -> dict[str, object]:
    return {"role": "work_lane", "branch": branch, "head": head, "path": f"/{branch}"}


def _lane(
    *,
    branch: str = SOURCE,
    head: str = SOURCE_HEAD,
    gaps: list[str] | None = None,
    lease_state: str = "valid",
    holder: str = "agent:test:holder",
) -> dict[str, object]:
    return {
        "branch": branch,
        "head": head,
        "path": f"/{branch}",
        "required_gaps": gaps or [],
        "lease_state": lease_state,
        "lease": {"holder_ref": holder},
    }


def _stub_retirement(
    monkeypatch: pytest.MonkeyPatch,
    *,
    worktrees: list[dict[str, object]],
    lanes: dict[str, dict[str, object]] | None = None,
    accepted: str = ACCEPTED,
    current_branch: str = "",
    verified_refs: set[str] | None = None,
    stub_holder_gaps: bool = True,
) -> None:
    lane_map = lanes or {}
    refs = verified_refs if verified_refs is not None else {str(row["branch"]) for row in worktrees}
    monkeypatch.setattr(linked, "repository_root", lambda root: root)
    monkeypatch.setattr(linked, "workspace_status", lambda _repo: {"worktrees": worktrees})
    monkeypatch.setattr(linked, "load_branch_role_policy", lambda _repo: BranchRolePolicy())
    monkeypatch.setattr(linked, "leases_by_branch", lambda _repo: {})
    monkeypatch.setattr(effects, "control_root", lambda *_args: None)
    monkeypatch.setattr(effects, "actor_ref", lambda: "agent:test:holder")
    if stub_holder_gaps:
        monkeypatch.setattr(effects, "holder_gaps", lambda _lane: [])
    monkeypatch.setattr(effects, "archived_carrier_absorption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        effects,
        "lane",
        lambda _repo, row, *_args, **_kwargs: lane_map.get(
            str(row["branch"]), _lane(branch=str(row["branch"]), head=str(row["head"]))
        ),
    )

    def output(_repo: Path, *args: str) -> str | None:
        if args == ("rev-parse", "dev"):
            return accepted
        if args[:2] == ("rev-parse", "--verify"):
            return args[2] if args[2] in refs else None
        if args == ("symbolic-ref", "--short", "HEAD"):
            return current_branch
        return None

    monkeypatch.setattr(linked, "output", output)
    monkeypatch.setattr(linked_admission, "output", output)


@pytest.mark.parametrize(
    ("worktrees", "retirement_request", "expected"),
    [
        ([], LinkedRetirementRequest(apply=True, authorize=True), "retire_branch_required"),
        (
            [],
            LinkedRetirementRequest(branch="work/missing"),
            "retire_branch_not_found",
        ),
        (
            [_worktree()],
            LinkedRetirementRequest(branch=SOURCE, apply=True),
            "authorization_required",
        ),
        (
            [_worktree()],
            LinkedRetirementRequest(branch=SOURCE, apply=True, authorize=True),
            "expect_head_required",
        ),
    ],
)
def test_landed_public_pre_effect_matrix_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worktrees: list[dict[str, object]],
    retirement_request: LinkedRetirementRequest,
    expected: str,
) -> None:
    _stub_retirement(monkeypatch, worktrees=worktrees)

    report = retire_linked_work_lane(root=tmp_path, mode="landed", request=retirement_request)

    assert expected in report["required_gaps"]
    assert report["mutation"]["decision"]["verdict"] == report["verdict"]


def test_landed_public_preserves_lane_and_head_gaps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lane = _lane(gaps=["work_lane_dirty"])
    _stub_retirement(monkeypatch, worktrees=[_worktree()], lanes={SOURCE: lane})

    report = retire_linked_work_lane(
        root=tmp_path,
        mode="landed",
        request=LinkedRetirementRequest(
            branch=SOURCE,
            expect_head="d" * 40,
            apply=True,
            authorize=True,
        ),
    )

    assert {"work_lane_dirty", "expect_head_mismatch"} <= set(report["required_gaps"])


@pytest.mark.parametrize(
    ("lease_state", "holder", "actor", "expected"),
    [
        ("valid", "agent:test:holder", "agent:test:holder", set()),
        (
            "valid",
            "agent:test:holder",
            "",
            {f"invocation_actor_missing:{SOURCE}"},
        ),
        (
            "valid",
            "agent:test:holder",
            "agent:test:other",
            {"foreign_work_lane_retire_authority_required"},
        ),
        ("expired", "agent:test:former", "agent:test:cleanup", set()),
        (
            "expired",
            "agent:test:former",
            "",
            {f"invocation_actor_missing:{SOURCE}"},
        ),
        ("missing", "", "agent:test:cleanup", set()),
        ("missing", "", "", {f"invocation_actor_missing:{SOURCE}"}),
        ("unknown", "", "agent:test:cleanup", {f"work_lane_lease_unknown:{SOURCE}"}),
        ("unknown", "", "", {f"work_lane_lease_unknown:{SOURCE}"}),
    ],
)
def test_landed_public_actor_and_lease_state_matrix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    lease_state: str,
    holder: str,
    actor: str,
    expected: set[str],
) -> None:
    lane = _lane(lease_state=lease_state, holder=holder)
    _stub_retirement(
        monkeypatch,
        worktrees=[_worktree()],
        lanes={SOURCE: lane},
        stub_holder_gaps=False,
    )
    monkeypatch.setattr(effects, "actor_ref", lambda: actor)

    report = retire_linked_work_lane(
        root=tmp_path,
        mode="landed",
        request=LinkedRetirementRequest(branch=SOURCE, expect_head=SOURCE_HEAD),
    )

    assert set(report["required_gaps"]) == expected
    expected_verdict = (
        "unknown" if lease_state == "unknown" else "pass" if not expected else "block"
    )
    assert report["verdict"] == expected_verdict


def test_landed_public_decision_names_repository_policy_not_commitment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lane = _lane(lease_state="missing", holder="")
    _stub_retirement(
        monkeypatch,
        worktrees=[_worktree()],
        lanes={SOURCE: lane},
        stub_holder_gaps=False,
    )
    monkeypatch.setattr(effects, "actor_ref", lambda: "agent:test:cleanup")

    report = retire_linked_work_lane(
        root=tmp_path,
        mode="landed",
        request=LinkedRetirementRequest(branch=SOURCE, expect_head=SOURCE_HEAD),
    )

    assert report["verdict"] == "pass"
    assert report["mutation"]["decision"]["policy_refs"] == [
        (
            "openspec/specs/repository-governance/spec.md"
            "#linked-work-lane-retirement-has-one-exact-effect"
        )
    ]


@pytest.mark.parametrize(
    ("branch", "worktrees", "verified", "gap"),
    [
        ("", [], set(), "superseded_retire_branch_required"),
        ("work/missing", [], set(), "superseded_retire_branch_not_found"),
        ("dev", [], {"dev"}, "superseded_retire_not_work_lane"),
        (SOURCE, [], {SOURCE}, "superseded_retire_worktree_not_linked"),
    ],
)
def test_superseded_public_target_resolution_rejects_invalid_subjects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    branch: str,
    worktrees: list[dict[str, object]],
    verified: set[str],
    gap: str,
) -> None:
    _stub_retirement(monkeypatch, worktrees=worktrees, verified_refs=verified)

    report = retire_linked_work_lane(
        root=tmp_path,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch=branch,
            expect_head=SOURCE_HEAD,
            absorbed_by=ACCEPTED,
            reason="absorbed",
        ),
    )

    assert gap in report["required_gaps"]


def test_superseded_public_successor_filters_only_missing_source_lease(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _lane(
        gaps=[f"work_lane_missing_lease:{SOURCE}", "work_lane_dirty"],
        lease_state="valid",
    )
    successor = _lane(branch=SUCCESSOR, head=SUCCESSOR_HEAD)
    _stub_retirement(
        monkeypatch,
        worktrees=[_worktree(), _worktree(SUCCESSOR, SUCCESSOR_HEAD)],
        lanes={SOURCE: source, SUCCESSOR: successor},
        current_branch=SUCCESSOR,
    )

    report = retire_linked_work_lane(
        root=tmp_path,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch=SOURCE,
            expect_head=SOURCE_HEAD,
            absorbed_by=SUCCESSOR_HEAD,
            reason="absorbed by successor",
        ),
    )

    gaps = set(report["required_gaps"])
    assert f"work_lane_missing_lease:{SOURCE}" not in gaps
    assert {"work_lane_dirty", "retirement_source_lease_present"} <= gaps


@pytest.mark.parametrize(
    ("absorbed_by", "archive_absorption", "ancestor", "gap"),
    [
        (ACCEPTED, False, False, "superseded_lane_not_absorbed_by_accepted"),
        (ACCEPTED, True, False, ""),
        (SUCCESSOR_HEAD, False, False, "superseded_lane_not_absorbed_by_successor"),
        (SUCCESSOR_HEAD, False, True, ""),
    ],
)
def test_superseded_public_absorption_authority_matrix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    absorbed_by: str,
    archive_absorption: object,
    ancestor: object,
    gap: str,
) -> None:
    successor_rows = [_worktree(SUCCESSOR, SUCCESSOR_HEAD)] if absorbed_by == SUCCESSOR_HEAD else []
    lanes = {SOURCE: _lane()}
    if successor_rows:
        lanes[SUCCESSOR] = _lane(branch=SUCCESSOR, head=SUCCESSOR_HEAD)
    _stub_retirement(
        monkeypatch,
        worktrees=[_worktree(), *successor_rows],
        lanes=lanes,
        current_branch=SUCCESSOR if successor_rows else "",
    )
    monkeypatch.setattr(effects, "absorbed", lambda *_args: ancestor)
    monkeypatch.setattr(linked_admission, "is_ancestor", lambda *_args: ancestor)
    if archive_absorption:
        monkeypatch.setattr(
            effects,
            "archived_carrier_absorption",
            lambda *_args, **_kwargs: {"change": "archived"},
        )

    report = retire_linked_work_lane(
        root=tmp_path,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch=SOURCE,
            expect_head=SOURCE_HEAD,
            absorbed_by=absorbed_by,
            reason="absorbed",
        ),
    )

    if gap:
        assert gap in report["required_gaps"]
    else:
        assert not any(
            str(item).startswith("superseded_lane_not_absorbed") for item in report["required_gaps"]
        )


def test_linked_apply_rejects_missing_control_root_before_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_retirement(monkeypatch, worktrees=[_worktree()])
    applied: list[bool] = []
    monkeypatch.setattr(
        linked,
        "compile_retirement_operation",
        lambda *_args, **_kwargs: applied.append(True),
    )

    report = retire_linked_work_lane(
        root=tmp_path,
        mode="landed",
        request=LinkedRetirementRequest(
            branch=SOURCE,
            expect_head=SOURCE_HEAD,
            authorize=True,
            apply=True,
        ),
    )

    assert report["required_gaps"] == ["retirement_control_root_unavailable"]
    assert applied == []


def test_linked_effect_failure_is_projected_as_a_fresh_block(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lane = _lane()
    _stub_retirement(monkeypatch, worktrees=[_worktree()], lanes={SOURCE: lane})
    monkeypatch.setattr(effects, "control_root", lambda *_args: tmp_path)
    monkeypatch.setattr(linked, "effect_readiness_gaps", lambda *_args, **_kwargs: [])
    compiled = object()
    receipt = {"path": "/receipt", "sha256": "sha256:" + "d" * 64}
    monkeypatch.setattr(
        linked,
        "compile_retirement_operation",
        lambda *_args, **_kwargs: compiled,
    )
    monkeypatch.setattr(linked, "persist_operation", lambda *_args, **_kwargs: receipt)
    monkeypatch.setattr(
        linked,
        "apply_operation",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "state": "partial_transition",
            "required_gaps": ["branch_delete_failed_after_worktree_removed"],
            "stderr": "git effect rejected",
            "observed": {"ref_state": "expected"},
        },
    )

    report = retire_linked_work_lane(
        root=tmp_path,
        mode="landed",
        request=LinkedRetirementRequest(
            branch=SOURCE,
            expect_head=SOURCE_HEAD,
            authorize=True,
            apply=True,
        ),
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["branch_delete_failed_after_worktree_removed"]
    assert report["observed"] == {"ref_state": "expected"}
    assert report["receipt"] == receipt
    assert report["mutation"]["decision"]["verdict"] == "block"


def test_linked_apply_persists_and_executes_the_common_retirement_operation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lane = _lane()
    _stub_retirement(monkeypatch, worktrees=[_worktree()], lanes={SOURCE: lane})
    monkeypatch.setattr(effects, "control_root", lambda *_args: tmp_path)
    monkeypatch.setattr(linked, "effect_readiness_gaps", lambda *_args, **_kwargs: [])
    compiled = object()
    receipt = {"path": "/receipt", "sha256": "sha256:" + "d" * 64}
    calls: list[str] = []
    monkeypatch.setattr(
        linked,
        "compile_retirement_operation",
        lambda *_args, **_kwargs: calls.append("compile") or compiled,
    )
    monkeypatch.setattr(
        linked,
        "persist_operation",
        lambda *_args, **_kwargs: calls.append("persist") or receipt,
    )
    monkeypatch.setattr(
        linked,
        "apply_operation",
        lambda *_args, **_kwargs: (
            calls.append("apply")
            or {
                "verdict": "pass",
                "state": "retired",
                "observed": {
                    "worktree_state": "absent",
                    "ref_state": "absent",
                    "lease_state": "absent",
                    "accepted_state": "expected",
                },
                "completed_effects": ["remove_worktree", "delete_ref", "revoke_lease"],
                "remaining_effects": [],
                "required_gaps": [],
                "next_action": "ethos status",
                "user_decision_required": False,
            }
        ),
    )
    report = retire_linked_work_lane(
        root=tmp_path,
        mode="landed",
        request=LinkedRetirementRequest(
            branch=SOURCE,
            expect_head=SOURCE_HEAD,
            authorize=True,
            apply=True,
        ),
    )

    assert calls == ["compile", "persist", "apply"]
    assert report["state"] == "retired"
    assert report["receipt"] == receipt
