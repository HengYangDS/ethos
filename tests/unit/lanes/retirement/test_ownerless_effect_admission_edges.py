"""Public ownerless-effect admission boundaries."""

from __future__ import annotations

from contextlib import ExitStack
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.closeout.effect as closeout_effect
import ethos.adapters.mutation.resolution.closeout.ownerless.effect as ownerless_effect
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.fence import (
    OwnerlessCloseoutAdmissionError,
)
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from pathlib import Path


_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000051"
_EXECUTOR = "agent:codex:thread:executor"


def _observation(tmp_path: Path) -> LaneObservation:
    return LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="lane:effect-cleanup-recovery",
        path=(tmp_path / "orphan").as_posix(),
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def test_ownerless_effect_receipt_admission_maps_unverifiable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    receipt_reservation = SimpleNamespace()
    observed: list[dict[str, object]] = []
    admission_unavailable = "admission unavailable"

    def admit(**kwargs: object) -> None:
        observed.append(kwargs)
        raise RuntimeError(admission_unavailable)

    monkeypatch.setattr(closeout_effect, "admit_ownerless_closeout_facts", admit)
    with pytest.raises(
        closeout_effect.OwnerlessCloseoutError,
        match=r"^lane_resolution_ownerless_admission_unverifiable$",
    ):
        closeout_effect.retire_clean_ownerless_lane(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision={"decision_id": _DECISION_ID},
            executor_ref=_EXECUTOR,
            receipt_reservation=receipt_reservation,
        )
    assert observed == [
        {
            "root": tmp_path,
            "decision_path": tmp_path / "decision.json",
            "decision": {"decision_id": _DECISION_ID},
            "executor_ref": _EXECUTOR,
            "receipt_reservation": receipt_reservation,
        }
    ]


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            (
                None,
                "admit_ownerless_closeout",
                OwnerlessCloseoutAdmissionError("lane_resolution_ownerless_decision_stale"),
                "lane_resolution_ownerless_decision_stale",
            ),
            id="unreserved-decision-stale",
        ),
        pytest.param(
            (
                object(),
                "admit_ownerless_closeout_facts",
                OwnerlessCloseoutAdmissionError("lane_resolution_ownerless_reservation_competing"),
                "lane_resolution_ownerless_reservation_competing",
            ),
            id="reserved-competing",
        ),
        pytest.param(
            (
                object(),
                "admit_ownerless_closeout_facts",
                RuntimeError(),
                "lane_resolution_ownerless_admission_unverifiable",
            ),
            id="reserved-unverifiable",
        ),
    ],
)
def test_ownerless_effect_admission_translates_public_collaborator_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: tuple[object | None, str, Exception, str],
) -> None:
    receipt_reservation, collaborator, failure, expected = case

    def fail(**_kwargs: object) -> object:
        raise failure

    monkeypatch.setattr(ownerless_effect, collaborator, fail)

    with pytest.raises(ownerless_effect.OwnerlessCloseoutError, match=rf"^{expected}$"):
        ownerless_effect.admit_ownerless_effect_target(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision={"decision_id": _DECISION_ID},
            executor_ref=_EXECUTOR,
            receipt_reservation=receipt_reservation,
        )


def test_recover_claim_skips_ownerless_context_for_non_ownerless_candidate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path).model_copy(update={"orphan": False})

    def unexpected_context(**_kwargs: object) -> object:
        pytest.fail("non-ownerless recovery must not build an ownerless context")

    monkeypatch.setattr(
        ownerless_effect,
        "claim_receipt_reservation",
        lambda *_args, **_kwargs: (True, 7, ""),
    )
    monkeypatch.setattr(
        ownerless_effect,
        "ownerless_receipt_reservation_context",
        unexpected_context,
    )

    with ExitStack() as stack:
        assert ownerless_effect.claim_resolution_effect_attempt(
            stack=stack,
            control_root=tmp_path,
            artifact_root=tmp_path / "records",
            decision_path=tmp_path / "decision.json",
            decision={"decision_id": _DECISION_ID},
            observation=observation,
            disposition="retire",
            recover=True,
        ) == (None, 7, None, ())


def test_ownerless_effect_releases_unreserved_fence_after_unexpected_reobservation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fence = {"target_binding_digest": "1" * 64}
    observation = _observation(tmp_path)
    admission = SimpleNamespace(
        root=tmp_path,
        existing_reservation=None,
        observation=observation,
        decision=SimpleNamespace(decision_id=_DECISION_ID, chronicle_digest="d" * 64),
        executor_ref=_EXECUTOR,
        accepted_branch="dev",
        accepted_head="f" * 40,
        decision_sha256="e" * 64,
        target_digest="0" * 64,
    )
    released: list[dict[str, object]] = []
    reobserve_unavailable = "reobserve unavailable"
    monkeypatch.setattr(closeout_effect, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(closeout_effect, "acquire_closeout_fence", lambda *_args, **_kwargs: fence)
    monkeypatch.setattr(
        closeout_effect,
        "reobserve_ownerless_closeout_under_fence",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError(reobserve_unavailable)),
    )
    monkeypatch.setattr(
        closeout_effect,
        "release_closeout_fence",
        lambda _database, **kwargs: released.append(kwargs),
    )

    with pytest.raises(
        closeout_effect.OwnerlessCloseoutError,
        match=r"^lane_resolution_ownerless_admission_unverifiable$",
    ):
        closeout_effect.retire_clean_ownerless_lane(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision={},
            executor_ref=_EXECUTOR,
            artifact_root=tmp_path / "records",
            admission=admission,
        )

    assert released == [
        {
            "subject": observation.lane_ref,
            "decision_id": _DECISION_ID,
            "target_binding_digest": "1" * 64,
        }
    ]
