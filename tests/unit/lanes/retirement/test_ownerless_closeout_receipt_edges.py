from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.mutation.resolution.receipts import exact_ownerless_resolution_receipt
from ethos.adapters.mutation.resolution.receipts import read_resolution_receipt
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from ethos.adapters.mutation.resolution.records.core import receipt_path
from ethos.adapters.mutation.resolution.records.core import target_digest
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionReceipt

if TYPE_CHECKING:
    from pathlib import Path

_FIRST_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"
_SECOND_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000002"


def _receipt(*, decision_id: str = _FIRST_DECISION_ID) -> dict[str, object]:
    return {
        "schema_version": 2,
        "receipt_id": "lane-resolution-receipt:ownerless-edge",
        "decision_id": decision_id,
        "completed": True,
        "state": "retired",
        "observation_digest": "d" * 64,
        "reconciliation_required": False,
        "lane_ref": "work/20260722-ownerless",
        "head": "a" * 40,
        "preservation_package": "",
        "preservation_manifest_sha256": "",
        "mints_authority": False,
    }


def _stored_receipt_path(root: Path, record_root: Path, decision_id: str) -> Path:
    destination = receipt_path(root, decision_id, artifact_root=record_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def _exact_receipt() -> tuple[
    dict[str, object], dict[str, object], LaneObservation, dict[str, object]
]:
    observation = LaneObservation(
        lane_ref="work/20260722-ownerless",
        head="a" * 40,
        lane_incarnation_id="lane-incarnation:20260722-ownerless",
        path="/tmp/20260722-ownerless",
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )
    decision = {"decision_id": _FIRST_DECISION_ID, "break_glass": False}
    binding: dict[str, object] = {
        "executor_ref": "agent:codex:thread:executor",
        "wcp_schema_version": "workstation.repo-family-governance.v1",
        "wcp_decision_sha256": "d" * 64,
        "accepted_branch": "dev",
        "accepted_head": "e" * 40,
        "wcp_binding_digest": "f" * 64,
        "target_digest": target_digest(observation.lane_ref, observation.head),
        "target_binding_digest": "2" * 64,
        "postcondition_digest": "3" * 64,
    }
    receipt = LaneResolutionReceipt(
        receipt_id="lane-resolution-receipt:ownerless-exact",
        decision_id=_FIRST_DECISION_ID,
        completed=True,
        state="retired",
        observation_digest=observation.digest(),
        reconciliation_required=False,
        lane_ref=observation.lane_ref,
        head=observation.head,
        preservation_package="",
        preservation_manifest_sha256="",
        ownerless_closeout_binding=binding,
        mints_authority=False,
    ).to_payload()
    return receipt, decision, observation, binding


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("schema_version", 999, id="schema-version"),
        pytest.param("receipt_id", "", id="receipt-id"),
        pytest.param("completed", False, id="completed"),
        pytest.param("mints_authority", True, id="mints-authority"),
    ],
)
def test_exact_ownerless_receipt_rejects_an_invalid_receipt_envelope(
    field: str, value: object
) -> None:
    receipt, decision, observation, binding = _exact_receipt()
    receipt[field] = value

    assert not exact_ownerless_resolution_receipt(
        receipt=receipt,
        decision=decision,
        observation=observation,
        expected_binding=binding,
    )


def test_exact_ownerless_receipt_rejects_a_defaulted_noncanonical_envelope() -> None:
    receipt, decision, observation, binding = _exact_receipt()
    receipt.pop("schema_version")

    assert not exact_ownerless_resolution_receipt(
        receipt=receipt,
        decision=decision,
        observation=observation,
        expected_binding=binding,
    )


def test_receipt_reader_rejects_a_symlinked_immutable_record(tmp_path: Path) -> None:
    record_root = tmp_path / "records"
    destination = _stored_receipt_path(tmp_path, record_root, _FIRST_DECISION_ID)
    outside = tmp_path / "outside-receipt.json"
    outside.write_text(json.dumps(_receipt()), encoding="utf-8")
    destination.symlink_to(outside)

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        read_resolution_receipt(
            root=tmp_path,
            decision_id=_FIRST_DECISION_ID,
            artifact_root=record_root,
        )


def test_receipt_reader_rejects_invalid_json(tmp_path: Path) -> None:
    record_root = tmp_path / "records"
    destination = _stored_receipt_path(tmp_path, record_root, _FIRST_DECISION_ID)
    destination.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        read_resolution_receipt(
            root=tmp_path,
            decision_id=_FIRST_DECISION_ID,
            artifact_root=record_root,
        )


def test_receipt_reader_rejects_a_non_object_payload(tmp_path: Path) -> None:
    record_root = tmp_path / "records"
    destination = _stored_receipt_path(tmp_path, record_root, _FIRST_DECISION_ID)
    destination.write_text("[]", encoding="utf-8")

    with pytest.raises(TypeError, match="lane_resolution_receipt_invalid"):
        read_resolution_receipt(
            root=tmp_path,
            decision_id=_FIRST_DECISION_ID,
            artifact_root=record_root,
        )


@pytest.mark.parametrize("field", ["schema_version", "preservation_package"])
def test_ownerless_receipt_reader_rejects_a_defaulted_noncanonical_record(
    tmp_path: Path, field: str
) -> None:
    record_root = tmp_path / "records"
    destination = _stored_receipt_path(tmp_path, record_root, _FIRST_DECISION_ID)
    receipt, _decision, _observation, _binding = _exact_receipt()
    receipt.pop(field)
    destination.write_text(json.dumps(receipt) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        read_resolution_receipt(
            root=tmp_path,
            decision_id=_FIRST_DECISION_ID,
            artifact_root=record_root,
            require_ownerless_closeout_binding=True,
        )


def test_receipt_reader_rejects_a_record_stored_under_another_decision_id(
    tmp_path: Path,
) -> None:
    record_root = tmp_path / "records"
    destination = _stored_receipt_path(tmp_path, record_root, _SECOND_DECISION_ID)
    destination.write_text(json.dumps(_receipt()) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        read_resolution_receipt(
            root=tmp_path,
            decision_id=_SECOND_DECISION_ID,
            artifact_root=record_root,
        )


def test_ownerless_receipt_reader_requires_the_closeout_binding_when_requested(
    tmp_path: Path,
) -> None:
    record_root = tmp_path / "records"
    write_resolution_receipt(
        root=tmp_path,
        receipt=_receipt(),
        artifact_root=record_root,
    )

    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        read_resolution_receipt(
            root=tmp_path,
            decision_id=_FIRST_DECISION_ID,
            artifact_root=record_root,
            require_ownerless_closeout_binding=True,
        )
