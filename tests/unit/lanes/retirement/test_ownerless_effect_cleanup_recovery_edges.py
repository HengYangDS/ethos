from __future__ import annotations

import hashlib
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution._effects as effects
import ethos.adapters.mutation.resolution.closeout.cleanup.core as cleanup
import ethos.adapters.mutation.resolution.closeout.effect as closeout_effect
import ethos.adapters.mutation.resolution.closeout.recovery as recovery
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.fence import (
    OwnerlessCloseoutAdmissionError,
)
from ethos.contracts.resolution.lane import LaneObservation

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


def _decision(observation: LaneObservation) -> dict[str, object]:
    return {
        "decision_id": _DECISION_ID,
        "chronicle_digest": "d" * 64,
        "observation": observation.model_dump(mode="json"),
    }


def _binding() -> dict[str, object]:
    return {
        "executor_ref": _EXECUTOR,
        "decision_sha256": "e" * 64,
        "accepted_branch": "dev",
        "accepted_head": "f" * 40,
        "target_digest": "0" * 64,
        "target_binding_digest": "1" * 64,
        "postcondition_digest": "2" * 64,
    }


def _reservation(observation: LaneObservation) -> dict[str, object]:
    return {
        "schema_version": 2,
        "decision_id": _DECISION_ID,
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        **_binding(),
        "phase": "receipt",
        "recovery_state": "effect_complete_receipt_missing",
    }


@pytest.mark.parametrize("stage", ["worktree_remove", "update_ref"])
def test_ownerless_cas_classifies_subprocess_transition_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stage: str,
) -> None:
    observation = _observation(tmp_path)
    expected = effects.OwnerlessCloseoutError(
        "lane_resolution_ownerless_transition_unknown",
        phase="unknown",
        recovery_state="transition_unknown",
    )

    def run(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if stage == "worktree_remove":
            raise OSError
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 0, "", "")
        raise subprocess.SubprocessError

    monkeypatch.setattr(effects, "run_git", run)
    monkeypatch.setattr(effects, "_classified_transition", lambda *_args, **_kwargs: expected)
    monkeypatch.setattr(effects, "ref_head", lambda *_args: "f" * 40)

    with pytest.raises(effects.OwnerlessCloseoutError) as raised:
        effects.retire_clean_ownerless_cas(
            root=tmp_path,
            observation=observation,
            accepted_branch="dev",
            accepted_head="f" * 40,
        )

    assert raised.value is expected


def test_ownerless_effect_probes_fail_closed_on_invalid_and_unreadable_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    responses = iter(
        (
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 0, "not-an-oid\n", ""),
        )
    )
    monkeypatch.setattr(effects, "run_git", lambda *_args, **_kwargs: next(responses))

    assert effects.probe_ownerless_ref(tmp_path, "work/orphan") == ("unverifiable", "")

    malformed = (
        "",
        "worktree /target\0\0\0",
        "unknown value\0\0",
        "worktree\0HEAD " + "a" * 40 + "\0branch refs/heads/dev\0\0",
        "worktree /target\0HEAD " + "a" * 40 + "\0detached unexpected\0\0",
    )
    assert all(effects._strict_worktree_records(output) is None for output in malformed)  # noqa: SLF001, RUF100
    detached = "worktree /target\0HEAD " + "a" * 40 + "\0detached\0\0"
    assert effects._strict_worktree_records(detached) is not None  # noqa: SLF001, RUF100

    monkeypatch.setattr(
        effects.os.path,
        "lexists",
        lambda _path: (_ for _ in ()).throw(OSError("path unavailable")),
    )
    assert effects.probe_ownerless_path((tmp_path / "orphan").as_posix()) == "unverifiable"
    assert effects._path_digest(tmp_path / "missing") == ""  # noqa: SLF001, RUF100


def test_ownerless_postconditions_treat_lease_probe_failure_as_coordination_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path)
    decision_bytes = b"exact decision"
    monkeypatch.setattr(effects, "probe_ownerless_ref", lambda *_args: ("absent", ""))
    monkeypatch.setattr(
        effects,
        "probe_ownerless_worktree_registration",
        lambda *_args: "absent",
    )
    monkeypatch.setattr(effects, "probe_ownerless_path", lambda *_args: "absent")
    monkeypatch.setattr(effects, "probe_closeout_fence", lambda *_args, **_kwargs: ("absent", None))
    monkeypatch.setattr(effects, "ref_head", lambda *_args: "f" * 40)
    monkeypatch.setattr(
        effects,
        "leases_by_branch",
        lambda _root: (_ for _ in ()).throw(RuntimeError("lease probe unavailable")),
    )

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="postcondition_failed:coordination_absent",
    ):
        effects.verify_ownerless_postconditions(
            root=tmp_path,
            database=tmp_path / "state.sqlite",
            decision_path=tmp_path / "decision.json",
            decision_sha256=hashlib.sha256(decision_bytes).hexdigest(),
            observation=observation,
            accepted_branch="dev",
            accepted_head="f" * 40,
            fence=None,
            decision_bytes=decision_bytes,
        )


def test_ownerless_effect_preparation_returns_explicit_package_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path)
    decision = _decision(observation)
    original_prepare = effects.prepare_preservation_package
    monkeypatch.setattr(
        effects,
        "prepare_preservation_package",
        lambda **_kwargs: ({"partial": "package"}, "lane_resolution_preservation_failed"),
    )

    assert effects.prepare_resolution_effect(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=decision,
        observation=observation,
        disposition="retire",
    ) == ({}, {}, "retired", "lane_resolution_preservation_failed")

    monkeypatch.setattr(effects, "prepare_preservation_package", original_prepare)
    monkeypatch.setattr(effects, "canonical_package_path", lambda *_args: None)
    assert effects.prepare_preservation_package(
        root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=decision,
        observation=observation,
        disposition="preserve",
    ) == ({}, "lane_resolution_preservation_path_outside_root")

    package = tmp_path / "records" / "already-present"
    package.mkdir(parents=True)
    monkeypatch.setattr(effects, "canonical_package_path", lambda *_args: package)
    assert effects.prepare_preservation_package(
        root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=decision,
        observation=observation,
        disposition="preserve-retire",
    ) == ({}, "lane_resolution_preservation_package_exists")


def test_ownerless_effect_releases_unreserved_fence_after_reobservation_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fence = {"target_binding_digest": "1" * 64}
    admission = SimpleNamespace(root=tmp_path, existing_reservation=None)
    released: list[object] = []
    monkeypatch.setattr(closeout_effect, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(closeout_effect, "_acquire_fresh_fence", lambda *_args: fence)
    monkeypatch.setattr(
        closeout_effect,
        "reobserve_ownerless_closeout_under_fence",
        lambda **_kwargs: (_ for _ in ()).throw(
            OwnerlessCloseoutAdmissionError("lane_resolution_ownerless_decision_stale")
        ),
    )
    monkeypatch.setattr(
        closeout_effect,
        "_release_unreserved_fence",
        lambda *_args: released.append("released"),
    )

    with pytest.raises(
        closeout_effect.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_decision_stale",
    ):
        closeout_effect.retire_clean_ownerless_lane(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision={},
            executor_ref=_EXECUTOR,
            artifact_root=tmp_path / "records",
            admission=admission,
        )

    assert released == ["released"]


def test_ownerless_effect_fence_release_failure_is_explicit_transition_unknown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path)
    admission = SimpleNamespace(
        observation=observation,
        decision=SimpleNamespace(decision_id=_DECISION_ID),
    )
    monkeypatch.setattr(
        closeout_effect,
        "release_closeout_fence",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("fence unavailable")),
    )

    with pytest.raises(closeout_effect.OwnerlessCloseoutError, match="transition_unknown"):
        closeout_effect._release_unreserved_fence(  # noqa: SLF001, RUF100
            admission,
            tmp_path / "state.sqlite",
            {"target_binding_digest": "1" * 64},
        )


def test_completed_ownerless_closeout_reports_stale_decision_and_accepted_head(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path)
    reservation = _reservation(observation)

    with pytest.raises(closeout_effect.OwnerlessCloseoutError, match="decision_stale"):
        closeout_effect.recover_completed_ownerless_closeout(
            root=tmp_path,
            decision_path=tmp_path / "missing.json",
            decision=_decision(observation),
            executor_ref=_EXECUTOR,
            reservation=reservation,
        )

    decision = _decision(observation)
    monkeypatch.setattr(
        closeout_effect,
        "canonical_resolution_decision_snapshot",
        lambda **_kwargs: (decision, ""),
    )
    monkeypatch.setattr(closeout_effect, "current_chronicle_matches", lambda *_args: True)
    monkeypatch.setattr(closeout_effect, "_verify_completed_binding", lambda **_kwargs: None)
    monkeypatch.setattr(closeout_effect, "ref_head", lambda *_args: "not-the-accepted-head")

    with pytest.raises(closeout_effect.OwnerlessCloseoutError, match="accepted_head_stale"):
        closeout_effect.recover_completed_ownerless_closeout(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision=decision,
            executor_ref=_EXECUTOR,
            reservation=reservation,
            decision_bytes=b"exact decision",
        )


def test_completed_ownerless_closeout_maps_binding_and_postcondition_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path)
    decision = _decision(observation)
    reservation = _reservation(observation)

    with pytest.raises(closeout_effect.OwnerlessCloseoutError, match="decision_stale"):
        closeout_effect._verify_completed_binding(  # noqa: SLF001, RUF100
            decision=decision,
            decision_sha256="e" * 64,
            observation=observation,
            executor_ref=_EXECUTOR,
            reservation=dict(reservation, decision_id="lane-decision:other"),
        )
    with pytest.raises(
        closeout_effect.OwnerlessCloseoutError,
        match="recovery_binding_mismatch:executor_ref",
    ):
        closeout_effect._verify_completed_binding(  # noqa: SLF001, RUF100
            decision=decision,
            decision_sha256="e" * 64,
            observation=observation,
            executor_ref=_EXECUTOR,
            reservation=dict(reservation, executor_ref="agent:codex:thread:other"),
        )

    monkeypatch.setattr(
        closeout_effect,
        "canonical_resolution_decision_snapshot",
        lambda **_kwargs: (decision, ""),
    )
    monkeypatch.setattr(closeout_effect, "current_chronicle_matches", lambda *_args: True)
    monkeypatch.setattr(closeout_effect, "_verify_completed_binding", lambda **_kwargs: None)
    monkeypatch.setattr(closeout_effect, "ref_head", lambda *_args: "f" * 40)
    monkeypatch.setattr(closeout_effect, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(
        closeout_effect,
        "probe_closeout_fence",
        lambda *_args, **_kwargs: ("absent", None),
    )
    monkeypatch.setattr(
        closeout_effect,
        "exact_ownerless_resolution_receipt",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(closeout_effect, "verify_ownerless_postconditions", lambda **_kwargs: {})
    monkeypatch.setattr(
        closeout_effect,
        "canonical_resolution_payload_digest",
        lambda _payload: "mismatch",
    )

    with pytest.raises(closeout_effect.OwnerlessCloseoutError, match="postcondition_digest"):
        closeout_effect.recover_completed_ownerless_closeout(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision=decision,
            executor_ref=_EXECUTOR,
            reservation=reservation,
            receipt={},
            decision_bytes=b"exact decision",
        )


def test_ownerless_partial_recording_leaves_unbound_errors_alone_and_maps_write_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    reservation = {"phase": "reserved", "recovery_state": "reserved_no_effect"}
    monkeypatch.setattr(
        closeout_effect,
        "transition_ownerless_closeout_reservation",
        lambda **_kwargs: pytest.fail("unbound errors must not create partial records"),
    )
    closeout_effect._record_ownerless_partial(  # noqa: SLF001, RUF100
        root=tmp_path,
        artifact_root=tmp_path / "records",
        reservation=reservation,
        error=closeout_effect.OwnerlessCloseoutError("lane_resolution_ownerless_decision_stale"),
    )

    monkeypatch.setattr(
        closeout_effect,
        "transition_ownerless_closeout_reservation",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("record unavailable")),
    )
    with pytest.raises(closeout_effect.OwnerlessCloseoutError, match="reservation_update_failed"):
        closeout_effect._record_ownerless_partial(  # noqa: SLF001, RUF100
            root=tmp_path,
            artifact_root=tmp_path / "records",
            reservation=reservation,
            error=closeout_effect.OwnerlessCloseoutError(
                "lane_resolution_ownerless_worktree_removed_ref_present",
                phase="effect",
                recovery_state="worktree_removed_ref_present",
            ),
        )


def test_cleanup_recovery_contexts_reject_unreadable_and_mismatched_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path)
    decision = _decision(observation)
    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("bad receipt")),
    )
    assert (
        cleanup.ownerless_receipt_recovery_context(
            control_root=tmp_path,
            artifact_root=tmp_path / "records",
            decision=decision,
            observation=observation,
        )[1]
        == "lane_resolution_receipt_invalid"
    )

    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: ({"ownerless_closeout_binding": []}, tmp_path / "receipt.json"),
    )
    assert cleanup.ownerless_receipt_recovery_context(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=decision,
        observation=observation,
    ) == ({}, "lane_resolution_ownerless_receipt_mismatch")

    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: ({"ownerless_closeout_binding": _binding()}, tmp_path / "receipt.json"),
    )
    monkeypatch.setattr(cleanup, "exact_ownerless_resolution_receipt", lambda **_kwargs: False)
    assert cleanup.ownerless_receipt_recovery_context(
        control_root=tmp_path,
        artifact_root=tmp_path / "records",
        decision=decision,
        observation=observation,
    ) == ({}, "lane_resolution_ownerless_receipt_mismatch")

    reservation_path = tmp_path / "reservation.json"
    reservation_path.touch()
    monkeypatch.setattr(
        cleanup,
        "ownerless_closeout_reservation_path",
        lambda *_args, **_kwargs: reservation_path,
    )
    monkeypatch.setattr(
        cleanup,
        "read_ownerless_closeout_reservation",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("bad reservation")),
    )
    assert (
        cleanup.ownerless_reservation_recovery_context(
            control_root=tmp_path,
            artifact_root=tmp_path / "records",
            decision=decision,
            observation=observation,
            receipt_recovery={},
        )[1]
        == "lane_resolution_ownerless_reservation_invalid"
    )

    monkeypatch.setattr(
        cleanup,
        "read_ownerless_closeout_reservation",
        lambda **_kwargs: {"decision_id": "lane-decision:other"},
    )
    assert (
        cleanup.ownerless_reservation_recovery_context(
            control_root=tmp_path,
            artifact_root=tmp_path / "records",
            decision=decision,
            observation=observation,
            receipt_recovery={},
        )[1]
        == "lane_resolution_ownerless_recovery_binding_mismatch"
    )


def test_cleanup_existing_receipt_retains_partial_state_for_all_nonfinalizable_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path)
    decision = _decision(observation)
    reservation = _reservation(observation)
    inputs = {
        "control_root": tmp_path,
        "artifact_root": tmp_path / "records",
        "decision_path": tmp_path / "decision.json",
        "decision": decision,
        "observation": observation,
        "reservation": reservation,
        "decision_bytes": b"exact decision",
        "require_decision_current": lambda: None,
    }

    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("receipt unavailable")),
    )
    report: dict[str, object] = {}
    assert cleanup.recover_existing_ownerless_receipt(report=report, **inputs) is True
    assert report["required_gaps"] == ["lane_resolution_receipt_invalid"]

    receipt = {"state": "retired", "ownerless_closeout_binding": _binding()}
    monkeypatch.setattr(
        cleanup,
        "read_resolution_receipt",
        lambda **_kwargs: (receipt, tmp_path / "receipt.json"),
    )
    monkeypatch.setattr(cleanup, "exact_ownerless_resolution_receipt", lambda **_kwargs: False)
    report = {}
    assert cleanup.recover_existing_ownerless_receipt(report=report, **inputs) is True
    assert report["required_gaps"] == ["lane_resolution_ownerless_receipt_mismatch"]

    monkeypatch.setattr(cleanup, "exact_ownerless_resolution_receipt", lambda **_kwargs: True)
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    report = {}
    assert cleanup.recover_existing_ownerless_receipt(report=report, **inputs) is True
    assert report["required_gaps"] == ["lane_resolution_ownerless_executor_required"]

    monkeypatch.setenv("ETHOS_ACTOR", _EXECUTOR)
    monkeypatch.setattr(
        cleanup,
        "recover_completed_ownerless_closeout",
        lambda **_kwargs: {"wrong": "binding"},
    )
    report = {}
    assert cleanup.recover_existing_ownerless_receipt(report=report, **inputs) is True
    assert report["required_gaps"] == ["lane_resolution_ownerless_receipt_mismatch"]

    expected_binding = {field: reservation[field] for field in cleanup._OWNERLESS_RECEIPT_FIELDS}  # noqa: SLF001, RUF100
    monkeypatch.setattr(
        cleanup,
        "recover_completed_ownerless_closeout",
        lambda **_kwargs: expected_binding,
    )
    monkeypatch.setattr(cleanup, "chronicle_event", lambda *_args: {"event": "retired"})
    monkeypatch.setattr(
        cleanup,
        "release_ownerless_closeout_resources",
        lambda **_kwargs: "lane_resolution_ownerless_cleanup_failed",
    )
    report = {}
    assert cleanup.recover_existing_ownerless_receipt(report=report, **inputs) is True
    assert report["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]


def test_recovery_preserve_retire_guards_receipt_and_chronicle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path)
    chronicle = b"fresh"
    decision = {
        "decision_id": _DECISION_ID,
        "chronicle_ref": "evidence/chronicle/preserve-retire.md",
        "chronicle_digest": hashlib.sha256(chronicle).hexdigest(),
    }

    with monkeypatch.context() as patch:
        patch.setattr(recovery, "accepted_control_root", lambda _root: tmp_path)
        patch.setattr(recovery, "current_record_root", lambda _root: tmp_path / "records")
        patch.setattr(
            recovery,
            "accepted_preserve_retire_chronicle",
            lambda *_args, **_kwargs: (chronicle, ""),
        )
        report: dict[str, object] = {}
        recovery.apply_resolution(
            root=tmp_path,
            decision={**decision, "chronicle_digest": "stale"},
            decision_path=tmp_path / "decision.json",
            observation=observation,
            disposition="preserve-retire",
            report=report,
        )
        assert report == {
            "ok": False,
            "state": "blocked",
            "required_gaps": ["lane_resolution_chronicle_stale"],
        }

    with monkeypatch.context() as patch:
        patch.setattr(recovery, "accepted_control_root", lambda _root: tmp_path)
        patch.setattr(recovery, "current_record_root", lambda _root: tmp_path / "records")
        patch.setattr(
            recovery,
            "accepted_preserve_retire_chronicle",
            lambda *_args, **_kwargs: (chronicle, ""),
        )
        patch.setattr(
            recovery,
            "claim_resolution_effect_attempt",
            lambda **_kwargs: (None, 1, None, ()),
        )
        patch.setattr(
            recovery,
            "prepare_resolution_effect",
            lambda **_kwargs: ({"package": "retained"}, {"state": "ready"}, "preserved", ""),
        )
        patch.setattr(recovery, "observe_lane", lambda *_args: (observation, []))
        patch.setattr(
            recovery,
            "retire_lane",
            lambda **_kwargs: (_ for _ in ()).throw(ValueError("lane_resolution_chronicle_stale")),
        )
        patch.setattr(
            recovery,
            "write_resolution_receipt",
            lambda **_kwargs: (_ for _ in ()).throw(OSError("receipt unavailable")),
        )
        patch.setattr(recovery.cleanup, "release_receipt_reservation", lambda **_kwargs: "")
        report = {}
        recovery.apply_resolution(
            root=tmp_path,
            decision=decision,
            decision_path=tmp_path / "decision.json",
            observation=observation.model_copy(update={"orphan": False}),
            disposition="preserve-retire",
            report=report,
        )
        assert report == {
            "ok": False,
            "state": "partial_transition",
            "required_gaps": ["lane_resolution_receipt_write_failed"],
            "preservation_package": {"package": "retained"},
        }

    with monkeypatch.context() as patch:
        patch.setattr(recovery, "accepted_control_root", lambda _root: tmp_path)
        patch.setattr(recovery, "current_record_root", lambda _root: tmp_path / "records")
        patch.setattr(
            recovery,
            "accepted_preserve_retire_chronicle",
            lambda *_args, **_kwargs: (None, ""),
        )
        report = {}
        recovery.apply_resolution(
            root=tmp_path,
            decision=decision,
            decision_path=tmp_path / "decision.json",
            observation=observation,
            disposition="preserve-retire",
            report=report,
        )
        assert report == {
            "ok": False,
            "state": "blocked",
            "required_gaps": ["lane_resolution_chronicle_invalid"],
        }


def test_recovery_context_and_retirement_effects_preserve_fail_closed_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observation = _observation(tmp_path)
    decision = _decision(observation)
    monkeypatch.setattr(recovery, "_resolution_roots", lambda _root: (None, None, "root gap"))
    assert recovery.ownerless_recovery_context(
        root=tmp_path,
        decision=decision,
        disposition="retire",
    ) == ({}, None, None, "root gap")

    missing_lane = _decision(observation)
    missing_lane["observation"] = {
        "lane_ref": "",
        "head": "",
        "dirty": False,
        "orphan": True,
    }
    monkeypatch.setattr(
        recovery,
        "_resolution_roots",
        lambda _root: (tmp_path, tmp_path / "records", ""),
    )
    assert recovery.ownerless_recovery_context(
        root=tmp_path,
        decision=missing_lane,
        disposition="retire",
    ) == ({}, tmp_path, tmp_path / "records", "")

    monkeypatch.setattr(
        recovery.cleanup,
        "ownerless_receipt_recovery_context",
        lambda **_kwargs: ({}, "lane_resolution_ownerless_receipt_invalid"),
    )
    assert recovery.ownerless_recovery_context(
        root=tmp_path,
        decision=decision,
        disposition="retire",
    ) == ({}, tmp_path, tmp_path / "records", "lane_resolution_ownerless_receipt_invalid")

    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    assert recovery._retire_resolution(  # noqa: SLF001, RUF100
        root=tmp_path,
        control_root=tmp_path,
        decision_path=tmp_path / "decision.json",
        decision=decision,
        observation=observation,
        disposition="retire",
        artifact_root=tmp_path / "records",
    ) == (False, "lane_resolution_ownerless_executor_required", {})

    non_ownerless = observation.model_copy(update={"orphan": False})
    monkeypatch.setattr(
        recovery,
        "retire_lane",
        lambda **_kwargs: (_ for _ in ()).throw(
            ValueError("lane_resolution_branch_delete_failed_after_worktree_removed")
        ),
    )
    assert recovery._retire_resolution(  # noqa: SLF001, RUF100
        root=tmp_path,
        control_root=tmp_path,
        decision_path=tmp_path / "decision.json",
        decision=decision,
        observation=non_ownerless,
        disposition="retire",
        artifact_root=tmp_path / "records",
    ) == (True, "lane_resolution_branch_delete_failed_after_worktree_removed", {})
    monkeypatch.setattr(
        recovery,
        "retire_lane",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("ordinary failure")),
    )
    assert recovery._retire_resolution(  # noqa: SLF001, RUF100
        root=tmp_path,
        control_root=tmp_path,
        decision_path=tmp_path / "decision.json",
        decision=decision,
        observation=non_ownerless,
        disposition="retire",
        artifact_root=tmp_path / "records",
    ) == (False, "lane_resolution_branch_delete_failed", {})
