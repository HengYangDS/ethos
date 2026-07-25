from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.resolution.records.clear.core as clear_core
import ethos.adapters.mutation.resolution.records.clear.quarantine as clear_quarantine
import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.inventory as record_inventory
import ethos.adapters.mutation.resolution.records.io.posix as record_posix
import ethos.adapters.mutation.resolution.records.reservations as reservation_store
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutReservation

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000201"


def _expected_ownerless_reservation() -> OwnerlessCloseoutReservation:
    return OwnerlessCloseoutReservation(
        schema_version=2,
        decision_id=_DECISION_ID,
        lane_ref="work/example",
        head="a" * 40,
        executor_ref="agent:codex:thread:executor",
        decision_sha256="b" * 64,
        accepted_branch="dev",
        accepted_head="c" * 40,
        target_digest=reservation_store.target_digest("work/example", "a" * 40),
        target_binding_digest="d" * 64,
        phase="reserved",
        recovery_state="reserved_no_effect",
        postcondition_digest="",
    )


def test_ownerless_reservation_admission_rejects_stale_foreign_and_competing_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _expected_ownerless_reservation()
    decision_path = tmp_path / "decisions" / "decision.json"
    matching_current = {
        "content_sha256": expected.decision_sha256,
        "physical_path": decision_path.absolute(),
    }

    def records_for(
        *,
        decision: dict[str, object] | None = matching_current,
        reservations: dict[str, dict[str, object]] | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            invalid_count=0,
            conflicts=set(),
            decisions={expected.decision_id: decision} if decision is not None else {},
            receipt_reservations={},
            reservations=reservations or {},
        )

    monkeypatch.setattr(
        record_inventory,
        "read_current_lane_resolution_records",
        lambda **_kwargs: records_for(decision={"content_sha256": "stale"}),
    )
    with pytest.raises(ValueError, match="lane_resolution_ownerless_decision_stale"):
        record_inventory.ownerless_closeout_reservation_admission(
            root=tmp_path,
            record_root=tmp_path / "records",
            decision_path=decision_path,
            decision_sha256=expected.decision_sha256,
            expected=expected,
        )

    foreign = expected.model_dump()
    foreign["lane_ref"] = "work/other"
    foreign["target_digest"] = reservation_store.target_digest("work/other", expected.head)
    monkeypatch.setattr(
        record_inventory,
        "read_current_lane_resolution_records",
        lambda **_kwargs: records_for(reservations={"foreign": foreign}),
    )
    assert (
        record_inventory.ownerless_closeout_reservation_admission(
            root=tmp_path,
            record_root=tmp_path / "records",
            decision_path=decision_path,
            decision_sha256=expected.decision_sha256,
            expected=expected,
        )
        is None
    )

    first = expected.model_dump()
    competing = expected.model_dump()
    competing["executor_ref"] = "agent:codex:thread:competing"
    monkeypatch.setattr(
        record_inventory,
        "read_current_lane_resolution_records",
        lambda **_kwargs: records_for(reservations={"first": first, "competing": competing}),
    )
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_competing"):
        record_inventory.ownerless_closeout_reservation_admission(
            root=tmp_path,
            record_root=tmp_path / "records",
            decision_path=decision_path,
            decision_sha256=expected.decision_sha256,
            expected=expected,
        )


def test_record_claim_coordination_and_liveness_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    with (
        pytest.raises(ValueError, match="lane_resolution_receipt_invalid"),
        record_store.claim_resolution_receipt_reservation(
            root=tmp_path,
            decision_id="invalid",
            artifact_root=record_root,
            mode="create",
        ),
    ):
        pass

    @contextmanager
    def unlocked(*_args: object, **_kwargs: object):
        yield

    @contextmanager
    def rejected_claim(*_args: object, **_kwargs: object):
        raise ValueError("rejected")
        yield None

    with monkeypatch.context() as scoped:
        scoped.setattr(record_store, "_receipt_coordination_lock", unlocked)
        scoped.setattr(record_store, "claim_record_sidecar", rejected_claim)
        with (
            pytest.raises(ValueError, match="lane_resolution_receipt_invalid"),
            record_store.claim_resolution_receipt_reservation(
                root=tmp_path,
                decision_id=_DECISION_ID,
                artifact_root=record_root,
                mode="create",
            ),
        ):
            pass

    monkeypatch.setattr(record_store, "git_common_dir", lambda _root: "")
    root = tmp_path / "root"
    root.mkdir()
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "is_relative_to", lambda *_args: False)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_store._receipt_coordination_root(root, tmp_path / "outside")  # noqa: SLF001, RUF100
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store._receipt_coordination_root(tmp_path, tmp_path)  # noqa: SLF001, RUF100

    monkeypatch.setattr(
        record_posix,
        "open_directory_path",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )
    with (
        pytest.raises(OSError, match="lane_resolution_record_path_unsafe"),
        record_store._receipt_coordination_lock(  # noqa: SLF001, RUF100
            tmp_path,
            record_root,
            record_root / ".reservation",
        ),
    ):
        pass

    monkeypatch.setattr(record_posix, "directory_descriptor_is_live", lambda *_args: False)
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store._require_coordination_live(  # noqa: SLF001, RUF100
            tmp_path,
            0,
            (0, 0, 0),
        )


def test_clear_postcondition_and_quarantine_binding_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_receipt = {"clear_receipt_id": "receipt"}
    plan = SimpleNamespace(
        observation=SimpleNamespace(record_root=tmp_path / "records"),
        clear_receipt=clear_receipt,
    )
    mismatch = SimpleNamespace(
        clears={_DECISION_ID: {}},
        invalid_count=0,
        conflicts=set(),
        manifests={},
        clear_quarantines={},
    )
    monkeypatch.setattr(
        clear_core,
        "read_current_lane_resolution_records",
        lambda **_kwargs: mismatch,
    )
    assert (
        clear_core._postcondition_gap(tmp_path, _DECISION_ID, plan)  # noqa: SLF001, RUF100
        == "lane_resolution_clear_receipt_mismatch"
    )

    failed = SimpleNamespace(
        clears={_DECISION_ID: clear_receipt},
        invalid_count=1,
        conflicts=set(),
        manifests={},
        clear_quarantines={},
    )
    monkeypatch.setattr(
        clear_core,
        "read_current_lane_resolution_records",
        lambda **_kwargs: failed,
    )
    monkeypatch.setattr(clear_core, "exact_clear_receipt", lambda *_args: True)
    assert (
        clear_core._postcondition_gap(tmp_path, _DECISION_ID, plan)  # noqa: SLF001, RUF100
        == "lane_resolution_clear_remove_failed"
    )

    v1_manifest = {
        "decision_id": _DECISION_ID,
        "lane_ref": "work/example",
        "head": "a" * 40,
        "observation_digest": "b" * 64,
        "bundle_sha256": "c" * 64,
        "patch_sha256": "d" * 64,
        "untracked_archive_sha256": "",
        "source_lease_transferred": False,
    }
    assert clear_quarantine.validated_manifest(v1_manifest) == v1_manifest

    valid_identity = (1, 2, 3, 4, 5, 6)
    assert (
        clear_quarantine.exact_package_binding(
            {
                "package_names": {"payload"},
                "payload_sha256": {"payload": 7},
                "payload_identities": {"payload": valid_identity},
            }
        )
        is None
    )
    assert (
        clear_quarantine.exact_package_binding(
            {
                "package_names": {"payload"},
                "payload_sha256": {"payload": "a" * 64},
                "payload_identities": {"payload": (1, 2)},
            }
        )
        is None
    )

    identity = (1, 2, 0o40700)
    name = record_store.clear_quarantine_name(_DECISION_ID, identity)
    malformed = clear_quarantine.ClearQuarantineCandidate(
        path=tmp_path / name,
        payload_sha256=None,
        package_names=set(),
        payload_identities={},
        entry_identity=identity,
    )
    records, invalid = clear_quarantine.clear_quarantines(
        tmp_path,
        (malformed,),
        {_DECISION_ID: {"manifest_sha256": "e" * 64}},
        {},
    )
    assert records == {}
    assert invalid == [malformed.path]
