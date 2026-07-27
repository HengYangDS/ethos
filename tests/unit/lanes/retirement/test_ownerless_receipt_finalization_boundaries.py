from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.closeout.ownerless.receipt.completion as completion
import ethos.adapters.mutation.resolution.records.reservations as reservations
from ethos.adapters.mutation.resolution.closeout.ownerless.effect import (
    OwnerlessCloseoutEffectContext,
)

if TYPE_CHECKING:
    from pathlib import Path


_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000222"


def test_ownerless_transition_is_exact_compare_and_replace(tmp_path: Path) -> None:
    record_root = tmp_path / "records"
    reservation = {
        "schema_version": 2,
        "decision_id": _DECISION_ID,
        "lane_ref": "work/orphan",
        "head": "a" * 40,
        "executor_ref": "agent:codex:thread:receipt-boundaries",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": reservations.target_digest("work/orphan", "a" * 40),
        "target_binding_digest": "d" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }
    path = reservations.reserve_ownerless_closeout_target(
        root=tmp_path,
        reservation=reservation,
        artifact_root=record_root,
    )
    transitioned = reservations.transition_ownerless_closeout_reservation(
        root=tmp_path,
        expected=reservation,
        phase="unknown",
        recovery_state="transition_unknown",
        artifact_root=record_root,
    )

    with pytest.raises(ValueError, match=r"^lane_resolution_ownerless_reservation_mismatch$"):
        reservations.transition_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            phase="effect",
            recovery_state="worktree_removed_ref_present",
            artifact_root=record_root,
        )

    assert transitioned["recovery_state"] == "transition_unknown"
    assert json.loads(path.read_text(encoding="utf-8")) == transitioned


@pytest.mark.parametrize(
    ("descriptor", "actor", "gap"),
    [
        (None, "agent:codex:thread:executor", "lane_resolution_ownerless_receipt_mismatch"),
        (7, "", "lane_resolution_ownerless_executor_required"),
    ],
)
def test_completed_recovery_requires_receipt_descriptor_and_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    descriptor: int | None,
    actor: str,
    gap: str,
) -> None:
    report: dict[str, object] = {"required_gaps": []}
    monkeypatch.setattr(
        completion,
        "claim_receipt_reservation",
        lambda *_args, **_kwargs: (True, descriptor, ""),
    )
    monkeypatch.setattr(
        completion,
        "enter_completed_decision",
        lambda *_args, **_kwargs: (
            SimpleNamespace(raw=b"decision", require_current=lambda: None),
            "",
        ),
    )
    monkeypatch.setattr(
        completion.cleanup, "recover_existing_ownerless_receipt", lambda **_kwargs: False
    )
    monkeypatch.setattr(completion.cleanup, "release_receipt_reservation", lambda **_kwargs: "")
    if actor:
        monkeypatch.setenv("ETHOS_ACTOR", actor)
    else:
        monkeypatch.delenv("ETHOS_ACTOR", raising=False)

    completion.recover_ownerless_resolution(
        context=OwnerlessCloseoutEffectContext(
            control_root=tmp_path,
            artifact_root=tmp_path / "records",
            decision_path=tmp_path / "records" / "decisions" / "decision.json",
            decision={"decision_id": _DECISION_ID},
            observation=SimpleNamespace(),
            disposition="retire",
            recover_receipt_reservation=True,
            admission=None,
            receipt_reservation=None,
            reservation={},
        ),
        report=report,
        prepare_resolution=lambda **_kwargs: ({}, {}, "retired", ()),
        write_receipt=lambda **_kwargs: "receipts/ownerless.json",
    )

    assert report == {"ok": False, "state": "partial_transition", "required_gaps": [gap]}
