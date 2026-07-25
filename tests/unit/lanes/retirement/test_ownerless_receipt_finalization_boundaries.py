"""Fail-closed receipt reservation and completed-finalization boundaries."""

from __future__ import annotations

from contextlib import ExitStack
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.closeout.ownerless.receipt.completion as completion
import ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core as receipt
from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError

if TYPE_CHECKING:
    from pathlib import Path

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000222"
_EXECUTOR = "agent:codex:thread:executor"
_COMPETING = "lane_resolution_ownerless_reservation_competing"
_STALE = "lane_resolution_ownerless_decision_stale"


class _RaisingContext:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def __enter__(self) -> object:
        raise self.error

    def __exit__(self, *_args: object) -> bool:
        return False


def _token(path: Path, raw: bytes) -> receipt.OwnerlessReceiptReservationToken:
    return receipt.OwnerlessReceiptReservationToken(
        path=path,
        raw=raw,
        identity=(1, 2, 3, 4, 5, 6),
    )


def _recover(
    *,
    tmp_path: Path,
    report: dict[str, object],
) -> None:
    completion.recover_ownerless_resolution(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision_path=tmp_path / "records" / "decisions" / "decision.json",
        decision={"decision_id": _DECISION_ID},
        observation=SimpleNamespace(),
        reservation={},
        report=report,
        prepare_resolution=lambda **_kwargs: ({}, {}, "retired", ()),
        write_receipt=lambda **_kwargs: "receipts/ownerless.json",
    )


def _current_decision() -> SimpleNamespace:
    return SimpleNamespace(raw=b"decision", require_current=lambda: None)


def test_effect_receipt_claim_preserves_the_first_claim_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        receipt,
        "claim_receipt_reservation",
        lambda *_args, **_kwargs: (False, None, "lane_resolution_receipt_path_exists"),
    )

    with ExitStack() as stack:
        assert receipt.claim_effect_receipt_reservation(
            stack,
            tmp_path,
            tmp_path / "records",
            _DECISION_ID,
            mode="create",
            admission=None,
        ) == (None, None, None, "lane_resolution_receipt_path_exists")


def test_receipt_token_rejects_changed_bytes_and_descriptor_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = f"{_DECISION_ID}\n".encode()
    cases = (
        (b"replacement\n", [(1, 2, 3, 4, 5, 6)]),
        (expected, [(1, 2, 3, 4, 5, 6), (1, 3, 3, 4, 5, 6)]),
    )
    for raw, identities in cases:
        with monkeypatch.context() as scoped:
            identity_values = iter(identities)
            scoped.setattr(
                receipt,
                "require_locked_record_identity",
                lambda *_args, **_kwargs: None,
            )
            scoped.setattr(receipt.os, "fstat", lambda _descriptor: object())
            scoped.setattr(
                receipt.posix,
                "file_identity",
                lambda _metadata, values=identity_values: next(values),
            )
            scoped.setattr(receipt, "read_descriptor_bytes", lambda _descriptor, raw=raw: raw)
            scoped.setattr(
                receipt,
                "require_ownerless_receipt_reservation_token",
                lambda **_kwargs: None,
            )
            with pytest.raises(ValueError, match=f"^{_COMPETING}$"):
                receipt.ownerless_receipt_reservation_token(
                    control_root=tmp_path,
                    artifact_root=tmp_path / "records",
                    decision_id=_DECISION_ID,
                    descriptor=7,
                )


def test_receipt_context_guard_revalidates_the_held_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = _token(tmp_path / "exact-sidecar", b"exact\n")
    monkeypatch.setattr(
        receipt,
        "ownerless_receipt_reservation_token",
        lambda **_kwargs: token,
    )
    context = receipt.ownerless_receipt_reservation_context(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision_id=_DECISION_ID,
        descriptor=7,
    )
    calls: list[str] = []
    monkeypatch.setattr(
        receipt,
        "require_locked_record_identity",
        lambda *_args, **_kwargs: calls.append("identity"),
    )
    monkeypatch.setattr(
        receipt,
        "require_ownerless_receipt_reservation_token",
        lambda **_kwargs: calls.append("token"),
    )

    with receipt.ownerless_receipt_reservation_guard(context):
        calls.append("body")

    assert calls == [
        "identity",
        "token",
        "identity",
        "body",
        "identity",
        "token",
        "identity",
    ]


@pytest.mark.parametrize("binding", ["control_root", "artifact_root", "decision_id"])
def test_receipt_context_must_match_the_admission_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, binding: str
) -> None:
    record_root = tmp_path / "records"
    context_fields: dict[str, object] = {
        "control_root": tmp_path.absolute(),
        "artifact_root": record_root.absolute(),
        "decision_id": _DECISION_ID,
        "descriptor": 7,
        "token": _token(tmp_path / "exact-sidecar", b"exact\n"),
    }
    context_fields[binding] = (
        "lane-decision:00000000-0000-4000-8000-000000000223"
        if binding == "decision_id"
        else (tmp_path / f"other-{binding}").absolute()
    )
    context = receipt.OwnerlessReceiptReservationContext(**context_fields)
    monkeypatch.setattr(
        receipt, "require_ownerless_receipt_reservation_context", lambda _context: None
    )
    monkeypatch.setattr(
        receipt.inventory,
        "ownerless_closeout_reservation_admission",
        lambda **_kwargs: pytest.fail("a mismatched context must not reach inventory"),
    )

    reservation, gap = receipt.ownerless_reservation_admission_or_gap(
        root=tmp_path,
        record_root=record_root,
        decision_path=record_root / "decisions" / "decision.json",
        decision_sha256="a" * 64,
        expected=SimpleNamespace(decision_id=_DECISION_ID),
        receipt_reservation=context,
    )

    assert (reservation, gap) == (None, _COMPETING)


def test_receipt_token_validation_rejects_wrong_or_unverifiable_sidecars(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    with pytest.raises(ValueError, match=f"^{_COMPETING}$"):
        receipt.require_ownerless_receipt_reservation_token(
            token=_token(tmp_path / "wrong", b"wrong"),
            control_root=tmp_path,
            artifact_root=tmp_path / "records",
            decision_id=_DECISION_ID,
        )

    sidecar = tmp_path / "exact-sidecar"
    monkeypatch.setattr(receipt, "_reservation_path", lambda *_args: sidecar)
    monkeypatch.setattr(receipt, "_reservation_bytes", lambda _decision_id: b"exact\n")
    monkeypatch.setattr(
        receipt,
        "open_current_record_snapshot",
        lambda _artifact_root: (None, "invalid"),
    )
    with pytest.raises(ValueError, match=f"^{_COMPETING}$"):
        receipt.require_ownerless_receipt_reservation_token(
            token=_token(sidecar, b"exact\n"),
            control_root=tmp_path,
            artifact_root=tmp_path / "records",
            decision_id=_DECISION_ID,
        )


def test_completed_decision_binding_detects_changed_held_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binding = completion.CompletedDecisionBinding(
        path=tmp_path / "decision.json",
        record_root=tmp_path / "records",
        raw=b"original",
        descriptor=7,
    )
    monkeypatch.setattr(
        completion,
        "require_locked_record_identity",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(completion, "read_descriptor_bytes", lambda _descriptor: b"replacement")

    with pytest.raises(OwnerlessCloseoutError, match=f"^{_STALE}$"):
        binding.require_current()


@pytest.mark.parametrize(
    ("error", "gap"),
    [
        (
            OwnerlessCloseoutError("lane_resolution_ownerless_exact"),
            "lane_resolution_ownerless_exact",
        ),
        (OSError("lock unavailable"), _STALE),
    ],
)
def test_completed_decision_binding_preserves_classified_and_translated_lock_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
    gap: str,
) -> None:
    monkeypatch.setattr(
        completion,
        "lock_record",
        lambda *_args, **_kwargs: _RaisingContext(error),
    )

    with (
        pytest.raises(OwnerlessCloseoutError, match=f"^{gap}$"),
        completion.bind_completed_decision(
            decision_path=tmp_path / "decision.json",
            record_root=tmp_path / "records",
        ),
    ):
        raise AssertionError


def test_enter_completed_decision_returns_a_classified_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = OwnerlessCloseoutError("lane_resolution_ownerless_exact")
    monkeypatch.setattr(
        completion,
        "bind_completed_decision",
        lambda **_kwargs: _RaisingContext(error),
    )

    with ExitStack() as stack:
        assert completion.enter_completed_decision(
            stack,
            decision_path=tmp_path / "decision.json",
            record_root=tmp_path / "records",
        ) == (None, "lane_resolution_ownerless_exact")


def test_completed_recovery_stops_before_decision_binding_and_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report: dict[str, object] = {"required_gaps": []}
    monkeypatch.setattr(
        completion,
        "claim_receipt_reservation",
        lambda *_args, **_kwargs: (False, None, "lane_resolution_receipt_path_exists"),
    )
    _recover(tmp_path=tmp_path, report=report)
    assert report == {
        "ok": False,
        "state": "partial_transition",
        "required_gaps": ["lane_resolution_receipt_path_exists"],
    }

    report = {"required_gaps": []}
    monkeypatch.setattr(
        completion,
        "claim_receipt_reservation",
        lambda *_args, **_kwargs: (True, 7, ""),
    )
    monkeypatch.setattr(
        completion,
        "enter_completed_decision",
        lambda *_args, **_kwargs: (None, _STALE),
    )
    _recover(tmp_path=tmp_path, report=report)
    assert report == {
        "ok": False,
        "state": "partial_transition",
        "required_gaps": [_STALE],
    }


@pytest.mark.parametrize(
    ("descriptor", "actor", "gap"),
    [
        (None, _EXECUTOR, "lane_resolution_ownerless_receipt_mismatch"),
        (7, "", "lane_resolution_ownerless_executor_required"),
    ],
)
def test_completed_recovery_requires_a_receipt_descriptor_and_executor(
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
        lambda *_args, **_kwargs: (_current_decision(), ""),
    )
    monkeypatch.setattr(
        completion.cleanup,
        "recover_existing_ownerless_receipt",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        completion.cleanup,
        "release_receipt_reservation",
        lambda **_kwargs: "",
    )
    if actor:
        monkeypatch.setenv("ETHOS_ACTOR", actor)
    else:
        monkeypatch.delenv("ETHOS_ACTOR", raising=False)

    _recover(tmp_path=tmp_path, report=report)

    assert report == {
        "ok": False,
        "state": "partial_transition",
        "required_gaps": [gap],
    }


def test_completed_recovery_reports_a_cleanup_gap_after_an_existing_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report: dict[str, object] = {"ok": True, "state": "effect", "required_gaps": []}
    released: list[int | None] = []
    monkeypatch.setattr(
        completion,
        "claim_receipt_reservation",
        lambda *_args, **_kwargs: (True, 7, ""),
    )
    monkeypatch.setattr(
        completion,
        "enter_completed_decision",
        lambda *_args, **_kwargs: (_current_decision(), ""),
    )

    def recovered(**_kwargs: object) -> bool:
        report["receipt"] = {"receipt_id": "exact"}
        return True

    def release(**kwargs: object) -> str:
        released.append(kwargs["locked_descriptor"])
        return "lane_resolution_receipt_reservation_release_failed"

    monkeypatch.setattr(completion.cleanup, "recover_existing_ownerless_receipt", recovered)
    monkeypatch.setattr(completion.cleanup, "release_receipt_reservation", release)

    _recover(tmp_path=tmp_path, report=report)

    assert released == [7]
    assert report["ok"] is False
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_receipt_reservation_release_failed"]
