from __future__ import annotations

import sqlite3
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.effects as effects

if TYPE_CHECKING:
    from pathlib import Path


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
        sqlite3.connect(":memory:") as connection,
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
