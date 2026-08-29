from __future__ import annotations

import sqlite3
import subprocess
from contextlib import closing
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path

_ARCHIVE_LISTING = """openspec/changes/archive/2026-08-29-change
openspec/changes/archive/2026-08-29-other
"""


def test_retirement_result_distinguishes_terminal_and_unrecovered_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed = {"ref_state": "absent"}
    monkeypatch.setattr(effects, "retirement_observation", lambda *_args: observed)
    monkeypatch.setattr(effects, "retirement_terminal", lambda _value: True)
    terminal = effects.retirement_result(
        tmp_path, tmp_path, {}, result={}, error=OSError("late fs error")
    )
    monkeypatch.setattr(effects, "retirement_terminal", lambda _value: False)
    failed = effects.retirement_result(
        tmp_path, tmp_path, {}, result={}, error=OSError("late fs error")
    )
    assert terminal == {"observed": observed}
    assert failed["required_gaps"] == ["lease_cleanup_failed"]
    assert failed["stderr"] == "late fs error"


def test_holder_unknown_does_not_invent_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    assert effects.holder_gaps({"lease_state": "unknown"}) == []
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    lane = {"lease_state": "valid", "lease": {"holder_ref": "agent:test:case:owner"}}
    assert effects.holder_gaps(lane) == ["foreign_work_lane_retire_authority_required"]


def test_require_missing_lease_and_restore_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        effects,
        "observe_lease_from_connection",
        lambda *_args: type("Lease", (), {"state": "valid"})(),
    )
    with (
        closing(sqlite3.connect(":memory:")) as connection,
        pytest.raises(ValueError, match="successor_retire_target_lease_present"),
    ):
        effects.require_missing_lease(connection, "work/example")
    assert effects.restore_worktree(tmp_path, {"path": "", "branch": ""}) == {
        "state": "blocked",
        "error": "worktree_restore_coordinates_missing",
    }
    monkeypatch.setattr(
        effects,
        "add_worktree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("occupied")),
    )
    assert effects.restore_worktree(
        tmp_path,
        {"path": str(tmp_path / "lane"), "branch": "work/example", "head": "a" * 40},
    ) == {"state": "blocked", "error": "occupied"}


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


def _raise(error: Exception) -> None:
    raise error


@pytest.mark.parametrize(
    ("failure", "gap"),
    [
        ("reobserve", "retirement_ref_stale"),
        ("plan", "git_effect_plan_invalid"),
        ("worktree", "worktree_remove_failed"),
        ("effect", "branch_delete_failed_after_worktree_removed"),
    ],
)
def test_remove_linked_lane_failures_preserve_one_exact_recovery_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    gap: str,
) -> None:
    lane = _lane()
    monkeypatch.setattr(
        effects,
        "reobservation_gaps",
        lambda *_args: ["retirement_ref_stale"] if failure == "reobserve" else [],
    )

    def plan(*_args: object, **_kwargs: object) -> tuple[Path, object]:
        if failure == "plan":
            _raise(ValueError("git_effect_plan_invalid: malformed"))
        return tmp_path, object()

    monkeypatch.setattr(effects, "linked_retirement_plan", plan)
    monkeypatch.setattr(effects, "admit_git_effect", lambda *_args: None)

    def remove(*_args: object, **_kwargs: object) -> None:
        if failure == "worktree":
            _raise(ValueError("occupied"))

    monkeypatch.setattr(effects, "remove_worktree", remove)

    def execute(*_args: object, **_kwargs: object) -> None:
        if failure == "effect":
            _raise(ValueError("CAS rejected"))

    monkeypatch.setattr(effects, "execute_git_effect", execute)
    monkeypatch.setattr(
        effects,
        "failed_ref_transition",
        lambda *_args, **_kwargs: effects.blocked(["branch_delete_failed_after_worktree_removed"]),
    )

    report = effects.remove_linked_lane(
        tmp_path,
        lane,
        accepted=("dev", "b" * 40),
        authority=lane,
    )

    assert report["required_gaps"] == [gap]


def test_apply_retirement_projects_transaction_and_storage_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = _lane()
    policy = BranchRolePolicy()
    monkeypatch.setattr(effects, "state_database", lambda _repo: tmp_path / "state.sqlite")
    monkeypatch.setattr(
        effects,
        "retirement_result",
        lambda *_args, result, error, **_kwargs: {
            "result": result,
            "error": str(error) if error is not None else "",
        },
    )
    monkeypatch.setattr(
        effects,
        "require_missing_lease",
        lambda *_args: (_ for _ in ()).throw(ValueError("successor_retire_target_lease_present")),
    )

    value_error = effects.apply_retirement(
        tmp_path,
        tmp_path,
        policy=policy,
        lane=lane,
        authority_lane=_lane("work/successor"),
        accepted_head="b" * 40,
    )
    assert value_error["result"]["required_gaps"] == ["successor_retire_target_lease_present"]

    monkeypatch.setattr(
        effects.sqlite3,
        "connect",
        lambda *_args: (_ for _ in ()).throw(sqlite3.OperationalError("database unavailable")),
    )
    storage_error = effects.apply_retirement(
        tmp_path,
        tmp_path,
        policy=policy,
        lane=lane,
        authority_lane=lane,
        accepted_head="b" * 40,
    )
    assert storage_error["error"] == "database unavailable"


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
        policy=BranchRolePolicy(),
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    ) == ["git_effect_plan_invalid"]


def test_restore_worktree_projects_applied_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attestation = SimpleNamespace(
        id="attestation:restore",
        payload=SimpleNamespace(body={"result": {"state": "applied"}}),
    )
    monkeypatch.setattr(effects, "add_worktree", lambda *_args, **_kwargs: attestation)

    assert effects.restore_worktree(tmp_path, _lane()) == {
        "state": "applied",
        "attestation_id": "attestation:restore",
    }


@pytest.mark.parametrize(
    ("mode", "merged", "dirty", "lease_state", "expected"),
    [
        ("landed", True, False, "valid", set()),
        ("landed", False, True, "missing", {"work_lane_not_merged", "work_lane_dirty"}),
        ("superseded", True, False, "expired", {"work_lane_already_merged_use_retire_landed"}),
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
    assert expected <= gaps
    if lease_state != "valid":
        assert any(gap.startswith("work_lane_") and "lease" in gap for gap in gaps)
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


class _Connection:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def execute(self, *_args: object) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        return None


@pytest.mark.parametrize("effect_gaps", [[], ["retirement_ref_stale"]])
def test_successor_retirement_commits_only_the_terminal_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effect_gaps: list[str],
) -> None:
    connection = _Connection()
    lane = _lane()
    authority = _lane("work/successor")
    monkeypatch.setattr(effects.sqlite3, "connect", lambda *_args: connection)
    monkeypatch.setattr(effects, "state_database", lambda _repo: tmp_path / "state.sqlite")
    monkeypatch.setattr(effects, "require_missing_lease", lambda *_args: None)
    observed: list[str] = []
    monkeypatch.setattr(
        effects,
        "expected_current_lease",
        lambda *_args, **_kwargs: observed.append("lease"),
    )
    monkeypatch.setattr(effects, "effect_gaps", lambda *_args, **_kwargs: effect_gaps)
    monkeypatch.setattr(effects, "remove_linked_lane", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        effects,
        "retirement_result",
        lambda *_args, result, error, **_kwargs: {"result": result, "error": error},
    )

    result = effects.apply_retirement(
        tmp_path,
        tmp_path,
        policy=BranchRolePolicy(),
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    )

    assert observed == ["lease"]
    assert connection.committed is (not effect_gaps)
    assert connection.rolled_back is bool(effect_gaps)
    assert result["result"].get("required_gaps", []) == effect_gaps


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
