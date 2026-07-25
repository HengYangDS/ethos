from __future__ import annotations

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
