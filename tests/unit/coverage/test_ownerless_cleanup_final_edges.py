from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.closeout.cleanup.core as cleanup
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _observation(tmp_path: Path) -> LaneObservation:
    return LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="lane:cleanup",
        path=(tmp_path / "orphan").as_posix(),
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def _binding() -> dict[str, object]:
    return {
        "executor_ref": "agent:codex:thread:executor",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": "d" * 64,
        "target_binding_digest": "e" * 64,
        "postcondition_digest": "f" * 64,
    }


def test_cleanup_releases_fence_before_visible_reservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []
    reservation = tmp_path / "reservation.json"
    reservation.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cleanup, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(
        cleanup,
        "ownerless_closeout_reservation_path",
        lambda *_a, **_k: reservation,
    )
    monkeypatch.setattr(cleanup, "release_closeout_fence", lambda *_a, **_k: events.append("fence"))
    monkeypatch.setattr(
        cleanup,
        "release_ownerless_closeout_reservation",
        lambda **_kwargs: events.append("reservation"),
    )
    gap = cleanup.release_ownerless_closeout_resources(
        control_root=tmp_path,
        artifact_root=tmp_path,
        decision={"decision_id": "lane-decision:00000000-0000-4000-8000-000000000001"},
        observation=_observation(tmp_path),
        binding=_binding(),
    )
    assert gap == ""
    assert events == ["fence", "reservation"]


def test_failed_fence_release_retains_visible_reservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []
    monkeypatch.setattr(cleanup, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(
        cleanup,
        "release_closeout_fence",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("different fence")),
    )
    monkeypatch.setattr(cleanup, "probe_closeout_fence", lambda *_a, **_k: ("present", {}))
    monkeypatch.setattr(
        cleanup,
        "release_ownerless_closeout_reservation",
        lambda **_kwargs: events.append("reservation"),
    )
    gap = cleanup.release_ownerless_closeout_resources(
        control_root=tmp_path,
        artifact_root=tmp_path,
        decision={"decision_id": "lane-decision:00000000-0000-4000-8000-000000000001"},
        observation=_observation(tmp_path),
        binding=_binding(),
    )
    assert gap == "lane_resolution_ownerless_cleanup_failed"
    assert events == []
