from __future__ import annotations

import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution._effects as effects
import ethos.adapters.mutation.resolution.closeout.effect as closeout_effect
import ethos.adapters.mutation.resolution.closeout.recovery as recovery
import ethos.adapters.mutation.resolution.lane as lane
from ethos.adapters.mutation.resolution.records.reservations import target_digest
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from pathlib import Path


def _observation(tmp_path: Path) -> LaneObservation:
    return LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="git-worktree-registration:v1:fixture",
        path=(tmp_path / "orphan").as_posix(),
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def test_ownerless_effect_has_no_runtime_or_external_adapter_bags() -> None:
    assert not hasattr(closeout_effect, "OwnerlessCloseout" + "Runtime")
    assert not hasattr(recovery, "Resolution" + "Runtime")
    assert not hasattr(effects, "_ownerless" + "_runtime")
    assert not hasattr(lane, "_resolution" + "_runtime")


def test_ownerless_error_uses_explicit_phase_and_recovery_state() -> None:
    unreserved = closeout_effect.OwnerlessCloseoutError("gap")
    reserved = closeout_effect.OwnerlessCloseoutError(
        "gap", phase="reserved", recovery_state="reserved_no_effect"
    )
    assert unreserved.reservation_visible is False
    assert reserved.reservation_visible is True
    assert (reserved.phase, reserved.recovery_state) == ("reserved", "reserved_no_effect")
    with pytest.raises(ValueError, match="state must be complete"):
        closeout_effect.OwnerlessCloseoutError("gap", phase="reserved")


def test_new_reservation_uses_fresh_fence_binding_digest(tmp_path: Path) -> None:
    observation = _observation(tmp_path)
    admission = SimpleNamespace(
        decision=SimpleNamespace(decision_id="lane-decision:00000000-0000-4000-8000-000000000001"),
        observation=observation,
        executor_ref="agent:codex:thread:executor",
        decision_sha256="d" * 64,
        accepted_branch="dev",
        accepted_head="e" * 40,
        target_digest=target_digest(observation.lane_ref, observation.head),
        target_binding_digest="0" * 64,
    )
    reservation = closeout_effect._reservation(  # noqa: SLF001, RUF100
        admission, {"target_binding_digest": "1" * 64}
    )
    assert reservation["target_binding_digest"] == "1" * 64
    assert reservation["target_binding_digest"] != admission.target_binding_digest


def test_ownerless_cas_removes_then_verifies_then_exact_deletes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observation = _observation(tmp_path)
    events: list[tuple[str, ...]] = []

    def run(_root: Path, *args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        events.append(args)
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 0, "", "")
        assert args == ("update-ref", "--stdin")
        stdin = str(kwargs["stdin"])
        assert f"update refs/heads/dev {'e' * 40} {'e' * 40}" in stdin
        assert f"delete refs/heads/work/orphan {'a' * 40}" in stdin
        return subprocess.CompletedProcess(args, 0, "start: ok\nprepare: ok\ncommit: ok\n", "")

    monkeypatch.setattr(effects, "run_git", run)
    monkeypatch.setattr(
        effects,
        "probe_ownerless_ref",
        lambda _root, branch: ("oid", "e" * 40) if branch == "dev" else ("absent", ""),
    )
    effects.retire_clean_ownerless_cas(
        root=tmp_path,
        observation=observation,
        accepted_branch="dev",
        accepted_head="e" * 40,
    )
    assert events == [("worktree", "remove", observation.path), ("update-ref", "--stdin")]


def test_dangling_path_remains_present_for_safety(tmp_path: Path) -> None:
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "missing", target_is_directory=True)
    assert effects.probe_ownerless_path(dangling.as_posix()) == "present"
