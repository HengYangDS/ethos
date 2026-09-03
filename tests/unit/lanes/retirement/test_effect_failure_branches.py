from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path

_ARCHIVE_LISTING = """openspec/changes/archive/2026-08-29-change
openspec/changes/archive/2026-08-29-other
"""


@pytest.mark.parametrize(
    ("state", "holder", "actor", "expected"),
    [
        (
            "unknown",
            "",
            "agent:test:case:cleanup",
            ["work_lane_lease_unknown:work/source"],
        ),
        ("valid", "agent:test:case:owner", "agent:test:case:owner", []),
        (
            "valid",
            "agent:test:case:owner",
            "",
            ["invocation_actor_missing:work/source"],
        ),
        (
            "valid",
            "agent:test:case:owner",
            "agent:test:case:other",
            ["foreign_work_lane_retire_authority_required"],
        ),
        ("expired", "agent:test:case:owner", "agent:test:case:cleanup", []),
        ("missing", "", "agent:test:case:cleanup", []),
        ("missing", "", "", ["invocation_actor_missing:work/source"]),
    ],
)
def test_holder_gaps_follow_observed_lease_state(
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    holder: str,
    actor: str,
    expected: list[str],
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    lane = {
        "branch": "work/source",
        "lease_state": state,
        "lease": {"holder_ref": holder},
    }
    assert effects.holder_gaps(lane) == expected


@pytest.mark.parametrize(
    ("results", "expected"),
    [
        ({"rev-parse": (1, "")}, "retirement_ref_unavailable"),
        ({"rev-parse": (0, "b" * 40)}, "retirement_ref_stale"),
        ({"status": (0, " M dirty")}, "work_lane_dirty"),
    ],
)
def test_reobservation_reports_unavailable_stale_and_dirty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    results: dict[str, tuple[int, str]],
    expected: str,
) -> None:
    lane = tmp_path / "lane"
    lane.mkdir()

    def run(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        key = "status" if args[0] == "status" else args[0]
        code, stdout = results.get(
            key, (0, "work/example" if args[0] == "symbolic-ref" else "a" * 40)
        )
        return subprocess.CompletedProcess(args, code, stdout, "")

    monkeypatch.setattr(effects, "run_git", run)
    assert expected in effects.reobservation_gaps("work/example", str(lane), "a" * 40)


def test_blocked_trims_stderr_and_effect_gaps_detects_stale_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert effects.blocked(["gap"], " failure \n")["stderr"] == "failure"
    policy = type("Policy", (), {"accepted_branch": "dev"})()
    monkeypatch.setattr(effects, "output", lambda *_args: "other")
    gaps = effects.effect_gaps(
        tmp_path,
        tmp_path,
        mode="landed",
        policy=policy,
        lane={"branch": "work/example"},
        authority_lane={"branch": "work/example"},
        accepted_head="a" * 40,
    )
    assert gaps == ["retirement_control_root_stale"]


def _lane(branch: str = "work/source") -> dict[str, object]:
    return {
        "branch": branch,
        "path": f"/{branch}",
        "head": "a" * 40,
        "lease": {
            "holder_ref": "agent:test:case:holder",
            "generation": 1,
            "expires_at": "2026-08-30T00:00:00Z",
        },
    }


def test_archive_absorption_and_effect_admission_cover_terminal_git_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = "openspec/changes/change/proposal.md"
    archive = "openspec/changes/archive/2026-08-29-change"
    monkeypatch.setattr(effects, "is_ancestor", lambda *_args: True)
    monkeypatch.setattr(effects, "_carrier_delta_paths", lambda *_args: (source,))
    monkeypatch.setattr(effects, "_archive_roots", lambda *_args: (archive,))
    monkeypatch.setattr(effects, "output", lambda *_args: "blob")

    mapping = effects.archived_carrier_absorption(tmp_path, head="a" * 40, accepted_head="b" * 40)
    assert mapping["paths"][source] == {"target": f"{archive}/proposal.md", "blob": "blob"}

    lane = _lane()
    authority = _lane("work/successor")
    authority["path"] = (tmp_path / "successor").as_posix()
    monkeypatch.setattr(
        effects,
        "output",
        lambda root, command, *_args: (
            "dev"
            if root == tmp_path and command == "symbolic-ref"
            else "b" * 40
            if root == tmp_path
            else "work/successor"
            if command == "symbolic-ref"
            else authority["head"]
        ),
    )
    monkeypatch.setattr(effects, "reobservation_gaps", lambda *_args: [])
    monkeypatch.setattr(effects, "actor_ref", lambda: "agent:test:case:holder")
    monkeypatch.setattr(effects, "archive_absorption_gaps", lambda *_args: [])
    monkeypatch.setattr(
        effects,
        "linked_retirement_plan",
        lambda *_args, **_kwargs: (tmp_path, object()),
    )
    monkeypatch.setattr(
        effects,
        "admit_git_effect",
        lambda *_args: (_ for _ in ()).throw(ValueError("git_effect_plan_invalid: stale")),
    )

    assert effects.effect_gaps(
        tmp_path / "successor",
        tmp_path,
        mode="superseded",
        policy=BranchRolePolicy(),
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    ) == ["git_effect_plan_invalid"]


@pytest.mark.parametrize(
    ("mode", "merged", "dirty", "lease_state", "expected"),
    [
        ("landed", True, False, "valid", set()),
        ("landed", True, False, "expired", set()),
        ("landed", True, False, "missing", set()),
        ("landed", True, False, "unknown", {"work_lane_lease_unknown:work/source"}),
        ("landed", False, True, "missing", {"work_lane_not_merged", "work_lane_dirty"}),
        (
            "superseded",
            True,
            False,
            "expired",
            {
                "work_lane_already_merged_use_retire_landed",
                "work_lane_lease_expired:work/source",
            },
        ),
    ],
)
def test_lane_projection_reports_native_retirement_readiness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    merged: object,
    dirty: object,
    lease_state: str,
    expected: set[str],
) -> None:
    lane_path = tmp_path / "lane"
    lane_path.mkdir()
    monkeypatch.setattr(effects, "is_ancestor", lambda *_args: bool(merged))
    monkeypatch.setattr(effects, "has_changed_paths", lambda _path: bool(dirty))
    lease = (
        {
            "lease_state": "valid",
            "holder_ref": "agent:test:case:holder",
            "generation": 1,
            "expires_at": "2026-08-30T00:00:00Z",
        }
        if lease_state == "valid"
        else {"lease_state": lease_state}
    )

    report = effects.lane(
        tmp_path,
        {"branch": "work/source", "path": lane_path, "head": "a" * 40},
        {"work/source": lease},
        accepted_head="b" * 40,
        mode=mode,
    )

    gaps = set(report["required_gaps"])
    assert gaps == expected
    assert report["retire_ready"] is not bool(gaps)


@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"),
    [
        (1, "", ()),
        (
            0,
            _ARCHIVE_LISTING,
            ("openspec/changes/archive/2026-08-29-change",),
        ),
    ],
)
def test_archive_absorption_uses_only_the_exact_archived_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    expected: tuple[str, ...],
) -> None:
    source = "openspec/changes/change/proposal.md"
    monkeypatch.setattr(effects, "is_ancestor", lambda *_args: True)
    monkeypatch.setattr(effects, "_carrier_delta_paths", lambda *_args: (source,))
    monkeypatch.setattr(effects, "output", lambda *_args: "blob")
    monkeypatch.setattr(
        effects,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], returncode, stdout, ""),
    )

    report = effects.archived_carrier_absorption(tmp_path, head="a" * 40, accepted_head="b" * 40)
    roots = {str(item["target"]).rsplit("/", 1)[0] for item in report.get("paths", {}).values()}
    assert tuple(roots) == expected


def test_retirement_drift_checks_stop_at_the_first_fresh_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = BranchRolePolicy()
    lane = _lane()
    authority = _lane("work/successor")
    authority["path"] = (tmp_path / "successor").as_posix()

    monkeypatch.setattr(
        effects,
        "output",
        lambda _root, command, *_args: "dev" if command == "symbolic-ref" else "stale",
    )
    assert effects.effect_gaps(
        tmp_path,
        tmp_path,
        mode="landed",
        policy=policy,
        lane=lane,
        authority_lane=lane,
        accepted_head="b" * 40,
    ) == ["accepted_ref_stale"]

    monkeypatch.setattr(
        effects,
        "output",
        lambda root, command, *_args: (
            "dev"
            if root == tmp_path and command == "symbolic-ref"
            else "b" * 40
            if root == tmp_path
            else "work/successor"
            if command == "symbolic-ref"
            else authority["head"]
        ),
    )
    monkeypatch.setattr(effects, "reobservation_gaps", lambda *_args: ["retirement_ref_stale"])
    assert effects.effect_gaps(
        tmp_path / "successor",
        tmp_path,
        mode="superseded",
        policy=policy,
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    ) == ["retirement_ref_stale"]

    monkeypatch.setattr(effects, "reobservation_gaps", lambda *_args: [])
    monkeypatch.setattr(effects, "actor_ref", lambda: "agent:test:other")
    assert effects.effect_gaps(
        tmp_path / "successor",
        tmp_path,
        mode="superseded",
        policy=policy,
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    ) == ["foreign_work_lane_retire_authority_required"]


def test_missing_retirement_path_and_carrier_delta_are_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert effects.reobservation_gaps("work/source", "", "a" * 40) == [
        "retirement_worktree_path_unavailable"
    ]
    monkeypatch.setattr(
        effects,
        "output",
        lambda _repo, command, *_args: (
            "openspec/changes/change/proposal.md\0src/product.py\0" if command == "diff" else "blob"
        ),
    )
    monkeypatch.setattr(effects, "is_ancestor", lambda *_args: True)
    monkeypatch.setattr(
        effects,
        "_archive_roots",
        lambda *_args: ("openspec/changes/archive/2026-08-29-change",),
    )
    assert (
        effects.archived_carrier_absorption(tmp_path, head="a" * 40, accepted_head="b" * 40) == {}
    )
