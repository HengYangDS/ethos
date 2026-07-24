from __future__ import annotations

import subprocess
from contextlib import contextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.mutation.resolution.closeout.receipt as receipt_claim
import ethos.adapters.mutation.resolution.closeout.recovery as recovery
from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution.closeout.recovery import ResolutionRuntime
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000004"


def _observation() -> LaneObservation:
    return LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="lane-incarnation:test",
        path="/tmp/work-orphan",
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def _decision(observation: LaneObservation | None = None) -> dict[str, Any]:
    current = observation or _observation()
    return {
        "decision_id": _DECISION_ID,
        "observation": current.model_dump(mode="json"),
    }


def _binding() -> dict[str, object]:
    return {
        "executor_ref": "agent:codex:thread:executor",
        "decision_sha256": "d" * 64,
        "accepted_branch": "dev",
        "accepted_head": "e" * 40,
        "target_digest": "1" * 64,
        "target_binding_digest": "2" * 64,
        "postcondition_digest": "3" * 64,
    }


def _block(report: dict[str, object], *gaps: str, state: str = "blocked") -> None:
    report.update(
        ok=False,
        state=state,
        required_gaps=list(dict.fromkeys(gap for gap in gaps if gap)),
    )


def _runtime(**overrides: Any) -> ResolutionRuntime:
    def prepare(**_kwargs: object) -> tuple[dict[str, object], dict[str, object], str, str]:
        return {}, {}, "retired", ""

    defaults: dict[str, Any] = {
        "accepted_control_root": lambda root: root,
        "current_record_root": lambda root: root / "records",
        "observe_lane": lambda _root, _lane_ref: (_observation(), []),
        "prepare_resolution_effect": prepare,
        "release_resolution_receipt_reservation": lambda **_kwargs: None,
        "retire_clean_ownerless_lane": lambda **_kwargs: _binding(),
        "write_resolution_receipt": lambda **_kwargs: "receipt.json",
        "release_closeout_fence": lambda *_args, **_kwargs: None,
        "block_resolution_report": _block,
        "ownerless_closeout_candidate": lambda _disposition, _observation: False,
    }
    defaults.update(overrides)
    return ResolutionRuntime(**defaults)


def _chronicle(decision: dict[str, Any], receipt: dict[str, object] | None) -> dict[str, object]:
    return {"decision_id": decision["decision_id"], "has_receipt": receipt is not None}


def _recover(
    *,
    tmp_path: Path,
    runtime: ResolutionRuntime,
    report: dict[str, object] | None = None,
) -> dict[str, object]:
    current_report = report or {"required_gaps": []}
    recovery.recover_ownerless_resolution(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision_path=tmp_path / "decision.json",
        decision=_decision(),
        observation=_observation(),
        reservation={"recovery_state": "effect_complete_receipt_missing"},
        report=current_report,
        runtime=runtime,
        chronicle_event=_chronicle,
    )
    return current_report


def test_ownerless_recovery_context_returns_root_binding_gap(tmp_path: Path) -> None:
    error = ValueError("lane_resolution_control_root_mismatch")

    def reject_root(_root: Path) -> Path:
        raise error

    reservation, control_root, artifact_root, gap = recovery.ownerless_recovery_context(
        root=tmp_path,
        decision=_decision(),
        disposition="retire",
        runtime=_runtime(accepted_control_root=reject_root),
    )

    assert reservation == {}
    assert control_root is None
    assert artifact_root is None
    assert gap == "lane_resolution_control_root_mismatch"


def test_ownerless_recovery_context_ignores_incomplete_target(tmp_path: Path) -> None:
    decision = _decision()
    decision["observation"] = {
        "lane_ref": "",
        "head": "a" * 40,
        "dirty": False,
        "orphan": True,
        "holder_ref": "",
    }

    reservation, control_root, artifact_root, gap = recovery.ownerless_recovery_context(
        root=tmp_path,
        decision=decision,
        disposition="retire",
        runtime=_runtime(),
    )

    assert reservation == {}
    assert control_root == tmp_path
    assert artifact_root == tmp_path / "records"
    assert gap == ""


def test_ownerless_recovery_context_rejects_unreadable_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservation_path = tmp_path / "reservation.json"
    reservation_path.touch()

    error = ValueError("not a reservation")

    def unreadable_reservation(**_kwargs: object) -> dict[str, object]:
        raise error

    monkeypatch.setattr(
        recovery.cleanup,
        "ownerless_receipt_recovery_context",
        lambda **_kwargs: ({}, ""),
    )
    monkeypatch.setattr(
        recovery,
        "ownerless_closeout_reservation_path",
        lambda *_args, **_kwargs: reservation_path,
    )
    monkeypatch.setattr(recovery, "read_ownerless_closeout_reservation", unreadable_reservation)

    reservation, _control_root, _artifact_root, gap = recovery.ownerless_recovery_context(
        root=tmp_path,
        decision=_decision(),
        disposition="retire",
        runtime=_runtime(),
    )

    assert reservation == {}
    assert gap == "lane_resolution_ownerless_reservation_invalid"


def test_ownerless_recovery_context_rejects_different_reservation_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservation_path = tmp_path / "reservation.json"
    reservation_path.touch()
    mismatched = {
        "decision_id": "lane-decision:00000000-0000-4000-8000-000000000099",
        "lane_ref": "work/orphan",
        "head": "a" * 40,
        "recovery_state": "reserved_no_effect",
    }
    monkeypatch.setattr(
        recovery.cleanup,
        "ownerless_receipt_recovery_context",
        lambda **_kwargs: ({}, ""),
    )
    monkeypatch.setattr(
        recovery,
        "ownerless_closeout_reservation_path",
        lambda *_args, **_kwargs: reservation_path,
    )
    monkeypatch.setattr(
        recovery,
        "read_ownerless_closeout_reservation",
        lambda **_kwargs: mismatched,
    )

    reservation, _control_root, _artifact_root, gap = recovery.ownerless_recovery_context(
        root=tmp_path,
        decision=_decision(),
        disposition="retire",
        runtime=_runtime(),
    )

    assert reservation == mismatched
    assert gap == "lane_resolution_ownerless_recovery_binding_mismatch"


def test_recover_ownerless_resolution_blocks_receipt_reservation_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def collide(**_kwargs: object) -> Iterator[int]:
        raise FileExistsError
        yield -1

    monkeypatch.setattr(receipt_claim, "claim_resolution_receipt_reservation", collide)

    report = _recover(tmp_path=tmp_path, runtime=_runtime())

    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_receipt_path_exists"]


def test_recover_ownerless_resolution_requires_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    monkeypatch.setattr(
        recovery.cleanup,
        "recover_existing_ownerless_receipt",
        lambda **_kwargs: False,
    )

    report = _recover(tmp_path=tmp_path, runtime=_runtime())

    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_ownerless_executor_required"]


def test_recover_ownerless_resolution_blocks_unfinalizable_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = OwnerlessCloseoutError(
        "lane_resolution_ownerless_postcondition_failed",
        fence_acquired=True,
    )

    def reject_recovery(**_kwargs: object) -> dict[str, object]:
        raise error

    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        recovery.cleanup,
        "recover_existing_ownerless_receipt",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(recovery, "recover_completed_ownerless_closeout", reject_recovery)

    report = _recover(tmp_path=tmp_path, runtime=_runtime())

    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_ownerless_postcondition_failed"]


def test_recover_ownerless_resolution_blocks_effect_preparation_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def prepare(**_kwargs: object) -> tuple[dict[str, object], dict[str, object], str, str]:
        return {}, {}, "retired", "lane_resolution_preservation_missing"

    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        recovery.cleanup,
        "recover_existing_ownerless_receipt",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        recovery,
        "recover_completed_ownerless_closeout",
        lambda **_kwargs: _binding(),
    )

    report = _recover(tmp_path=tmp_path, runtime=_runtime(prepare_resolution_effect=prepare))

    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_preservation_missing"]


def test_recover_ownerless_resolution_blocks_receipt_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_write(**_kwargs: object) -> str:
        raise OSError

    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        recovery.cleanup,
        "recover_existing_ownerless_receipt",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        recovery,
        "recover_completed_ownerless_closeout",
        lambda **_kwargs: _binding(),
    )

    report = _recover(tmp_path=tmp_path, runtime=_runtime(write_resolution_receipt=fail_write))

    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_receipt_write_failed_after_effect"]


@pytest.mark.parametrize(
    "release_error",
    [OSError(), ValueError("lane_resolution_current_record_changed")],
)
def test_recover_ownerless_resolution_retains_cleanup_and_sidecar_gaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    release_error: Exception,
) -> None:
    def fail_sidecar_release(**_kwargs: object) -> None:
        raise release_error

    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        recovery.cleanup,
        "recover_existing_ownerless_receipt",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        recovery,
        "recover_completed_ownerless_closeout",
        lambda **_kwargs: _binding(),
    )
    monkeypatch.setattr(
        recovery.cleanup,
        "release_ownerless_closeout_resources",
        lambda **_kwargs: "lane_resolution_ownerless_cleanup_failed",
    )

    report = _recover(
        tmp_path=tmp_path,
        runtime=_runtime(
            release_resolution_receipt_reservation=fail_sidecar_release,
        ),
    )

    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == [
        "lane_resolution_ownerless_cleanup_failed",
        "lane_resolution_receipt_reservation_release_failed",
    ]


def test_apply_ownerless_resolution_requires_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    report: dict[str, object] = {"required_gaps": []}

    recovery.apply_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        decision=_decision(),
        observation=_observation(),
        disposition="retire",
        report=report,
        runtime=_runtime(ownerless_closeout_candidate=lambda _disposition, _observation: True),
        chronicle_event=_chronicle,
    )

    assert report["state"] == "ownerless_executor_required"
    assert report["required_gaps"] == ["lane_resolution_ownerless_executor_required"]


def test_apply_ownerless_resolution_requires_accepted_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        recovery,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(accepted_branch="dev"),
    )
    monkeypatch.setattr(
        recovery,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, stdout="", stderr=""),
    )
    report: dict[str, object] = {"required_gaps": []}

    recovery.apply_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        decision=_decision(),
        observation=_observation(),
        disposition="retire",
        report=report,
        runtime=_runtime(ownerless_closeout_candidate=lambda _disposition, _observation: True),
        chronicle_event=_chronicle,
    )

    assert report["state"] == "ownerless_accepted_head_unavailable"
    assert report["required_gaps"] == ["lane_resolution_ownerless_accepted_head_unavailable"]


@pytest.mark.parametrize(
    ("error_message", "expected_releases"),
    [
        (
            "lane_resolution_branch_delete_failed_after_worktree_removed",
            0,
        ),
        ("git refused branch deletion", 1),
    ],
)
def test_apply_resolution_classifies_branch_delete_failure_side_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_message: str,
    expected_releases: int,
) -> None:
    def fail_retire(**_kwargs: object) -> None:
        raise ValueError(error_message)

    released: list[str] = []

    def release_sidecar(**_kwargs: object) -> None:
        released.append("released")

    monkeypatch.setattr(recovery, "retire_lane", fail_retire)
    report: dict[str, object] = {"required_gaps": []}

    recovery.apply_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        decision=_decision(),
        observation=_observation(),
        disposition="retire",
        report=report,
        runtime=_runtime(
            release_resolution_receipt_reservation=release_sidecar,
        ),
        chronicle_event=_chronicle,
    )

    expected_gap = (
        error_message
        if error_message.startswith("lane_resolution_")
        else "lane_resolution_branch_delete_failed"
    )
    assert report["required_gaps"] == [expected_gap]
    assert len(released) == expected_releases
