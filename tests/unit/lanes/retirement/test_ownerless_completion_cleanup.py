"""Fail-closed completion and cleanup boundaries for ownerless closeout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.closeout.cleanup.core as cleanup_adapter
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt import (
    completion as completion_adapter,
)
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from pathlib import Path


class _CompletionDecision:
    def __init__(self, gaps: tuple[str, ...]) -> None:
        self._gaps = iter(gaps)

    def current_gap(self) -> str:
        return next(self._gaps)


@dataclass(frozen=True)
class _CompletedReceiptCase:
    effect_gaps: tuple[str, ...]
    decision_gaps: tuple[str, ...]
    write_fails: bool
    cleanup_gap: str
    expected_result: bool
    expected_calls: list[str]
    expected_gaps: list[str]


def _completion_binding() -> dict[str, object]:
    return {
        "executor_ref": "agent:codex:thread:executor",
        "decision_sha256": "a" * 64,
        "accepted_branch": "dev",
        "accepted_head": "b" * 40,
        "target_digest": "c" * 64,
        "target_binding_digest": "d" * 64,
        "postcondition_digest": "e" * 64,
    }


def _completion_observation(tmp_path: Path) -> LaneObservation:
    return LaneObservation(
        lane_ref="work/orphan",
        head="f" * 40,
        lane_incarnation_id="lane:completion",
        path=(tmp_path / "orphan").as_posix(),
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="0" * 64,
        untracked_digest="1" * 64,
    )


@pytest.mark.parametrize(
    "case",
    [
        _CompletedReceiptCase(
            effect_gaps=("lane_resolution_effect_failed",),
            decision_gaps=(),
            write_fails=False,
            cleanup_gap="",
            expected_result=False,
            expected_calls=[],
            expected_gaps=["lane_resolution_effect_failed"],
        ),
        _CompletedReceiptCase(
            effect_gaps=(),
            decision_gaps=("lane_resolution_ownerless_decision_stale",),
            write_fails=False,
            cleanup_gap="",
            expected_result=False,
            expected_calls=[],
            expected_gaps=["lane_resolution_ownerless_decision_stale"],
        ),
        _CompletedReceiptCase(
            effect_gaps=(),
            decision_gaps=("",),
            write_fails=True,
            cleanup_gap="",
            expected_result=False,
            expected_calls=["write"],
            expected_gaps=["lane_resolution_receipt_write_failed_after_effect"],
        ),
        _CompletedReceiptCase(
            effect_gaps=(),
            decision_gaps=("", "lane_resolution_ownerless_decision_stale"),
            write_fails=False,
            cleanup_gap="",
            expected_result=True,
            expected_calls=["write"],
            expected_gaps=["lane_resolution_ownerless_decision_stale"],
        ),
        _CompletedReceiptCase(
            effect_gaps=(),
            decision_gaps=("", ""),
            write_fails=False,
            cleanup_gap="lane_resolution_ownerless_cleanup_failed",
            expected_result=True,
            expected_calls=["write", "cleanup"],
            expected_gaps=["lane_resolution_ownerless_cleanup_failed"],
        ),
    ],
)
def test_completed_receipt_finalization_fails_closed_at_each_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: _CompletedReceiptCase,
) -> None:
    calls: list[str] = []
    report: dict[str, object] = {"ok": True, "state": "effect", "required_gaps": []}
    decision = {"decision_id": "lane-decision:00000000-0000-4000-8000-000000000031"}

    def prepare_resolution(
        **_kwargs: object,
    ) -> tuple[dict[str, object], dict[str, object], str, tuple[str, ...]]:
        return {"package": "exact"}, {"state": "retired"}, "retired", case.effect_gaps

    def write_receipt(**_kwargs: object) -> str:
        calls.append("write")
        if case.write_fails:
            raise OSError
        return "receipts/ownerless.json"

    monkeypatch.setattr(completion_adapter, "chronicle_event", lambda *_args: {"event": "exact"})
    monkeypatch.setattr(
        completion_adapter.cleanup,
        "release_ownerless_closeout_resources",
        lambda **_kwargs: calls.append("cleanup") or case.cleanup_gap,
    )

    outcome = completion_adapter._write_completed_receipt(  # noqa: SLF001, RUF100
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=decision,
        observation=_completion_observation(tmp_path),
        report=report,
        binding=_completion_binding(),
        current_decision=_CompletionDecision(case.decision_gaps),
        prepare_resolution=prepare_resolution,
        write_receipt=write_receipt,
    )

    assert outcome is case.expected_result
    assert calls == case.expected_calls
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == case.expected_gaps


@pytest.mark.parametrize(
    ("fence_state", "expected"),
    [
        ("absent", ""),
        ("present", "lane_resolution_ownerless_cleanup_failed"),
        ("unverifiable", "lane_resolution_ownerless_cleanup_failed"),
    ],
)
def test_cleanup_tolerates_only_a_proven_absent_stale_fence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fence_state: str,
    expected: str,
) -> None:
    monkeypatch.setattr(cleanup_adapter, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(
        cleanup_adapter,
        "release_closeout_fence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("lane_closeout_fence_release_stale:replacement")
        ),
    )
    monkeypatch.setattr(
        cleanup_adapter,
        "probe_closeout_fence",
        lambda *_args, **_kwargs: (fence_state, None),
    )
    monkeypatch.setattr(
        cleanup_adapter,
        "ownerless_closeout_reservation_path",
        lambda *_args, **_kwargs: tmp_path / "missing-reservation.json",
    )

    assert (
        cleanup_adapter.release_ownerless_closeout_resources(
            control_root=tmp_path,
            artifact_root=tmp_path / "records",
            decision={"decision_id": "lane-decision:00000000-0000-4000-8000-000000000032"},
            observation=_completion_observation(tmp_path),
            binding=_completion_binding(),
        )
        == expected
    )
