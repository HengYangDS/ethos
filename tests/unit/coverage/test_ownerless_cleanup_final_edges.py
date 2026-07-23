from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.mutation.resolution.closeout.cleanup.core as cleanup
from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution.closeout.recovery import ResolutionRuntime
from ethos_core.contracts.resolution.lane import LaneObservation

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


def _decision() -> dict[str, Any]:
    return {
        "decision_id": _DECISION_ID,
        "observation": _observation().model_dump(mode="json"),
    }


def _binding() -> dict[str, object]:
    return {
        "executor_ref": "agent:codex:thread:executor",
        "wcp_schema_version": "workstation.repo-family-governance.v1",
        "wcp_decision_sha256": "d" * 64,
        "accepted_branch": "dev",
        "accepted_head": "e" * 40,
        "wcp_binding_digest": "f" * 64,
        "target_digest": "1" * 64,
        "target_binding_digest": "2" * 64,
        "postcondition_digest": "3" * 64,
    }


def _reservation() -> dict[str, object]:
    return {
        "schema_version": 1,
        "decision_id": _DECISION_ID,
        "lane_ref": "work/orphan",
        "head": "a" * 40,
        **_binding(),
        "phase": "receipt",
        "recovery_state": "effect_complete_receipt_missing",
    }


def _receipt() -> dict[str, object]:
    return {
        "decision_id": _DECISION_ID,
        "state": "retired",
        "ownerless_closeout_binding": _binding(),
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

    def reserve(**_kwargs: object) -> Path:
        return Path("receipt.reservation")

    defaults: dict[str, Any] = {
        "accepted_control_root": lambda root: root,
        "records_artifact_root": lambda root: root / "records",
        "observe_lane": lambda _root, _lane_ref: (_observation(), []),
        "prepare_resolution_effect": prepare,
        "reserve_resolution_receipt": reserve,
        "release_resolution_receipt_reservation": lambda **_kwargs: None,
        "retire_clean_ownerless_lane": lambda **_kwargs: _binding(),
        "write_resolution_receipt": lambda **_kwargs: "receipt.json",
        "release_closeout_fence": lambda *_args, **_kwargs: None,
        "block_resolution_report": _block,
        "ownerless_closeout_candidate": lambda _disposition, _observation: False,
    }
    defaults.update(overrides)
    return ResolutionRuntime(**defaults)


def _recover_existing(
    *,
    tmp_path: Path,
    runtime: ResolutionRuntime | None = None,
) -> tuple[bool, dict[str, object]]:
    report: dict[str, object] = {"required_gaps": []}
    recovered = cleanup.recover_existing_ownerless_receipt(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision_path=tmp_path / "decision.json",
        decision=_decision(),
        observation=_observation(),
        reservation=_reservation(),
        report=report,
        runtime=runtime or _runtime(),
        chronicle_event=lambda decision, receipt: {
            "decision_id": decision["decision_id"],
            "has_receipt": receipt is not None,
        },
    )
    return recovered, report


def test_receipt_recovery_context_reconstructs_exact_completed_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _receipt()
    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (receipt, tmp_path / "receipt.json"),
    )
    monkeypatch.setattr(cleanup, "exact_ownerless_resolution_receipt", lambda **_kwargs: True)

    reservation, gap = cleanup.ownerless_receipt_recovery_context(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=_decision(),
        observation=_observation(),
    )

    assert gap == ""
    assert reservation == _reservation()


def test_existing_receipt_recovery_blocks_unreadable_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = ValueError("lane_resolution_receipt_schema_invalid")

    def unreadable(**_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(cleanup, "read_resolution_receipt", unreadable)

    recovered, report = _recover_existing(tmp_path=tmp_path)

    assert recovered is True
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_receipt_schema_invalid"]


def test_existing_receipt_recovery_blocks_receipt_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (_receipt(), tmp_path / "receipt.json"),
    )
    monkeypatch.setattr(cleanup, "exact_ownerless_resolution_receipt", lambda **_kwargs: False)

    recovered, report = _recover_existing(tmp_path=tmp_path)

    assert recovered is True
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_ownerless_receipt_mismatch"]


def test_existing_receipt_recovery_requires_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (_receipt(), tmp_path / "receipt.json"),
    )
    monkeypatch.setattr(cleanup, "exact_ownerless_resolution_receipt", lambda **_kwargs: True)

    recovered, report = _recover_existing(tmp_path=tmp_path)

    assert recovered is True
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_ownerless_executor_required"]


def test_existing_receipt_recovery_blocks_unfinalizable_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = OwnerlessCloseoutError(
        "lane_resolution_ownerless_fence_stale",
        fence_acquired=True,
    )

    def reject_recovery(**_kwargs: object) -> dict[str, object]:
        raise error

    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (_receipt(), tmp_path / "receipt.json"),
    )
    monkeypatch.setattr(cleanup, "exact_ownerless_resolution_receipt", lambda **_kwargs: True)
    monkeypatch.setattr(cleanup, "recover_completed_ownerless_closeout", reject_recovery)

    recovered, report = _recover_existing(tmp_path=tmp_path)

    assert recovered is True
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_ownerless_fence_stale"]


def test_existing_receipt_recovery_blocks_recomputed_binding_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mismatched = dict(_binding(), accepted_head="9" * 40)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (_receipt(), tmp_path / "receipt.json"),
    )
    monkeypatch.setattr(cleanup, "exact_ownerless_resolution_receipt", lambda **_kwargs: True)
    monkeypatch.setattr(
        cleanup,
        "recover_completed_ownerless_closeout",
        lambda **_kwargs: mismatched,
    )

    recovered, report = _recover_existing(tmp_path=tmp_path)

    assert recovered is True
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_ownerless_receipt_mismatch"]


@pytest.mark.parametrize(
    ("cleanup_gap", "sidecar_gap", "expected_gaps"),
    [
        (
            "lane_resolution_ownerless_cleanup_failed",
            "",
            ["lane_resolution_ownerless_cleanup_failed"],
        ),
        (
            "",
            "lane_resolution_receipt_reservation_release_failed",
            ["lane_resolution_receipt_reservation_release_failed"],
        ),
    ],
)
def test_existing_receipt_recovery_retains_cleanup_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_gap: str,
    sidecar_gap: str,
    expected_gaps: list[str],
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (_receipt(), tmp_path / "receipt.json"),
    )
    monkeypatch.setattr(cleanup, "exact_ownerless_resolution_receipt", lambda **_kwargs: True)
    monkeypatch.setattr(
        cleanup,
        "recover_completed_ownerless_closeout",
        lambda **_kwargs: _binding(),
    )
    monkeypatch.setattr(
        cleanup,
        "release_ownerless_closeout_resources",
        lambda **_kwargs: cleanup_gap,
    )
    monkeypatch.setattr(
        cleanup,
        "release_receipt_reservation",
        lambda **_kwargs: sidecar_gap,
    )

    recovered, report = _recover_existing(tmp_path=tmp_path)

    assert recovered is True
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == expected_gaps


def test_cleanup_tolerates_exact_fence_already_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = ValueError("lane_closeout_fence_release_stale:work/orphan")

    def stale_release(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(cleanup, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(cleanup, "probe_closeout_fence", lambda *_args, **_kwargs: ("absent", None))
    monkeypatch.setattr(
        cleanup,
        "ownerless_closeout_reservation_path",
        lambda *_args, **_kwargs: tmp_path / "missing-reservation.json",
    )

    gap = cleanup.release_ownerless_closeout_resources(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=_decision(),
        observation=_observation(),
        binding=_binding(),
        runtime=_runtime(release_closeout_fence=stale_release),
    )

    assert gap == ""


@pytest.mark.parametrize(
    ("binding", "case"),
    [
        ("not-a-binding", "binding_wrong"),
        (_binding(), "exact_wrong"),
    ],
)
def test_receipt_recovery_context_rejects_nonexact_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binding: object,
    case: str,
) -> None:
    receipt = {"ownerless_closeout_binding": binding}
    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (receipt, tmp_path / "receipt.json"),
    )
    monkeypatch.setattr(
        cleanup,
        "exact_ownerless_resolution_receipt",
        lambda **_kwargs: case != "exact_wrong",
    )

    reservation, gap = cleanup.ownerless_receipt_recovery_context(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=_decision(),
        observation=_observation(),
    )

    assert reservation == {}
    assert gap == "lane_resolution_ownerless_receipt_mismatch"


def test_cleanup_rejects_nonstale_fence_release_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = ValueError("different fence")

    def invalid_release(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(cleanup, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(cleanup, "probe_closeout_fence", lambda *_args, **_kwargs: ("absent", None))

    gap = cleanup.release_ownerless_closeout_resources(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=_decision(),
        observation=_observation(),
        binding=_binding(),
        runtime=_runtime(release_closeout_fence=invalid_release),
    )

    assert gap == "lane_resolution_ownerless_cleanup_failed"


def test_cleanup_releases_exact_visible_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservation_path = tmp_path / "reservation.json"
    reservation_path.touch()
    released: list[dict[str, object]] = []
    monkeypatch.setattr(cleanup, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(
        cleanup,
        "ownerless_closeout_reservation_path",
        lambda *_args, **_kwargs: reservation_path,
    )
    monkeypatch.setattr(
        cleanup,
        "release_ownerless_closeout_reservation",
        lambda **kwargs: released.append(kwargs),
    )

    gap = cleanup.release_ownerless_closeout_resources(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=_decision(),
        observation=_observation(),
        binding=_binding(),
        runtime=_runtime(),
    )

    assert gap == ""
    assert released[0]["expected"]["decision_id"] == _DECISION_ID
