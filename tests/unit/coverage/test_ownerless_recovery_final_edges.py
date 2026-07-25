from __future__ import annotations

from contextlib import ExitStack
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.closeout.recovery as recovery
from ethos.adapters.mutation.resolution.closeout.effect import OwnerlessCloseoutError
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _observation(tmp_path: Path) -> LaneObservation:
    return LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="lane:coverage",
        path=(tmp_path / "orphan").as_posix(),
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def test_resolution_roots_maps_direct_root_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        recovery,
        "accepted_control_root",
        lambda _root: (_ for _ in ()).throw(ValueError("root failed")),
    )
    control, artifact, gap = recovery._resolution_roots(tmp_path)  # noqa: SLF001, RUF100
    assert (control, artifact) == (None, None)
    assert gap == "lane_resolution_control_root_unavailable"


def test_ownerless_retire_uses_explicit_reservation_visibility(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observation = _observation(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        recovery,
        "retire_clean_ownerless_lane",
        lambda **_kwargs: (_ for _ in ()).throw(
            OwnerlessCloseoutError(
                "lane_resolution_ownerless_worktree_removed_ref_present",
                phase="effect",
                recovery_state="worktree_removed_ref_present",
            )
        ),
    )
    retained, gap, binding = recovery._retire_resolution(  # noqa: SLF001, RUF100
        root=tmp_path,
        control_root=tmp_path,
        decision_path=tmp_path / "decision.json",
        decision={},
        observation=observation,
        disposition="retire",
        artifact_root=tmp_path / "records",
    )
    assert retained is True
    assert gap == "lane_resolution_ownerless_worktree_removed_ref_present"
    assert binding == {}


def test_ownerless_retire_pre_admission_failure_does_not_claim_reservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observation = _observation(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        recovery,
        "retire_clean_ownerless_lane",
        lambda **_kwargs: (_ for _ in ()).throw(
            OwnerlessCloseoutError("lane_resolution_ownerless_decision_stale")
        ),
    )
    retained, gap, _binding = recovery._retire_resolution(  # noqa: SLF001, RUF100
        root=tmp_path,
        control_root=tmp_path,
        decision_path=tmp_path / "decision.json",
        decision={},
        observation=observation,
        disposition="retire",
        artifact_root=tmp_path / "records",
    )
    assert retained is False
    assert gap == "lane_resolution_ownerless_decision_stale"


def test_prepare_resolution_preserves_effect_and_observation_boundaries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observation = _observation(tmp_path)
    inputs = {
        "control_root": tmp_path,
        "artifact_root": tmp_path / "records",
        "decision": {"decision_id": "lane-decision:00000000-0000-4000-8000-000000000041"},
        "observation": observation,
    }
    with monkeypatch.context() as patch:
        patch.setattr(
            recovery,
            "prepare_resolution_effect",
            lambda **_kwargs: (_ for _ in ()).throw(ValueError("lane_resolution_effect_exact")),
        )
        assert recovery._prepare_resolution(  # noqa: SLF001, RUF100
            **inputs, disposition="retire"
        ) == ({}, {}, "blocked", ("lane_resolution_effect_exact",))

    for disposition, current, current_gaps, expected_gaps in (
        ("retire", observation, (), ()),
        ("preserve-retire", observation, (), ()),
        (
            "preserve-retire",
            observation,
            ("lane_resolution_observe_failed",),
            ("lane_resolution_observe_failed", "lane_resolution_observation_stale"),
        ),
        (
            "preserve-retire",
            observation.model_copy(update={"head": "d" * 40}),
            (),
            ("lane_resolution_observation_stale",),
        ),
    ):
        calls: list[str] = []
        with monkeypatch.context() as patch:
            patch.setattr(
                recovery,
                "prepare_resolution_effect",
                lambda **_kwargs: ({"package": "exact"}, {"receipt": "exact"}, "ready", ""),
            )

            def observe(
                *_args: object,
                observed: LaneObservation = current,
                observed_gaps: tuple[str, ...] = current_gaps,
                events: list[str] = calls,
                **_kwargs: object,
            ) -> tuple[LaneObservation, tuple[str, ...]]:
                events.append("observe")
                return observed, observed_gaps

            patch.setattr(recovery, "observe_lane", observe)
            package, receipt, state, gaps = recovery._prepare_resolution(  # noqa: SLF001, RUF100
                **inputs, disposition=disposition
            )
        assert (package, receipt, state, gaps) == (
            {"package": "exact"},
            {"receipt": "exact"},
            "ready",
            expected_gaps,
        )
        assert calls == ([] if disposition == "retire" else ["observe"])


def test_claim_effect_attempt_preserves_every_fail_closed_claim_gap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observation = _observation(tmp_path)
    inputs = {
        "control_root": tmp_path,
        "artifact_root": tmp_path / "records",
        "decision_path": tmp_path / "decision.json",
        "decision": {"decision_id": "lane-decision:00000000-0000-4000-8000-000000000042"},
        "observation": observation,
        "disposition": "retire",
    }
    with monkeypatch.context() as patch, ExitStack() as stack:
        patch.setattr(
            recovery,
            "claim_receipt_reservation",
            lambda *_args, **_kwargs: (False, None, "lane_resolution_receipt_path_exists"),
        )
        assert recovery._claim_effect_attempt(  # noqa: SLF001, RUF100
            stack=stack, **inputs, recover=True
        ) == (None, None, ("lane_resolution_receipt_path_exists",))

    with monkeypatch.context() as patch, ExitStack() as stack:
        patch.setattr(
            recovery, "claim_receipt_reservation", lambda *_args, **_kwargs: (True, 7, "")
        )
        patch.setattr(
            recovery,
            "ownerless_receipt_reservation_token",
            lambda **_kwargs: (_ for _ in ()).throw(ValueError("lane_resolution_receipt_invalid")),
        )
        assert recovery._claim_effect_attempt(  # noqa: SLF001, RUF100
            stack=stack, **inputs, recover=True
        ) == (None, 7, ("lane_resolution_receipt_invalid",))

    with monkeypatch.context() as patch, ExitStack() as stack:
        patch.setattr(
            recovery,
            "pre_admit_ownerless_lane",
            lambda **_kwargs: (None, "lane_resolution_ownerless_executor_required"),
        )
        assert recovery._claim_effect_attempt(  # noqa: SLF001, RUF100
            stack=stack, **inputs, recover=False
        ) == (None, None, ("lane_resolution_ownerless_executor_required",))

    with monkeypatch.context() as patch, ExitStack() as stack:
        patch.setattr(recovery, "pre_admit_ownerless_lane", lambda **_kwargs: (object(), ""))
        patch.setattr(
            recovery,
            "claim_effect_receipt_reservation",
            lambda *_args, **_kwargs: (None, 7, "lane_resolution_receipt_invalid"),
        )
        patch.setattr(
            recovery.cleanup,
            "release_receipt_reservation",
            lambda **_kwargs: "lane_resolution_receipt_reservation_release_failed",
        )
        assert recovery._claim_effect_attempt(  # noqa: SLF001, RUF100
            stack=stack, **inputs, recover=False
        ) == (
            None,
            7,
            (
                "lane_resolution_receipt_invalid",
                "lane_resolution_receipt_reservation_release_failed",
            ),
        )
