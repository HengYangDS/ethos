from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.records.reservations as reservation_store
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.ethos_cli_runner import run_ethos
from tests.support.lane_helpers import init_repo

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"


def _ownerless_reservation() -> dict[str, object]:
    lane_ref, head = "work/20260722-ownerless", "a" * 40
    return {
        "schema_version": 2,
        "decision_id": _DECISION_ID,
        "lane_ref": lane_ref,
        "head": head,
        "executor_ref": "agent:Codex:thread:Executor+1",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": reservation_store.target_digest(lane_ref, head),
        "target_binding_digest": "e" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }


def _receipt(*, decision_id: str = _DECISION_ID) -> dict[str, object]:
    return {
        "schema_version": 3,
        "receipt_id": "lane-resolution-receipt:one",
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


def _ownerless_binding(*, executor_ref: str) -> dict[str, object]:
    return {
        "executor_ref": executor_ref,
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": reservation_store.target_digest("work/20260722-ownerless", "a" * 40),
        "target_binding_digest": "e" * 64,
        "postcondition_digest": "f" * 64,
    }


def test_lane_resolution_inventory_exposes_empty_local_artifact_view(tmp_path) -> None:
    repo = init_repo(tmp_path / "repo")

    payload = run_ethos(
        "lane",
        "resolution",
        "inventory",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["command"] == "lane resolution inventory"
    assert payload["state"] == "ready"
    assert payload["summary"] == {
        "package_count": 0,
        "receipt_count": 0,
        "clear_count": 0,
        "inflight_count": 0,
        "partial_count": 0,
        "decision_count": 0,
        "pending_decision_count": 0,
        "invalid_current_record_count": 0,
    }
    assert payload["data"]["entries"] == []


def test_lane_resolution_clear_exposes_bounded_refusal_contract(tmp_path) -> None:
    repo = init_repo(tmp_path / "repo")

    payload = run_ethos(
        "lane",
        "resolution",
        "clear",
        "--decision-id",
        "lane-decision:missing",
        "--expect-manifest-sha256",
        "a" * 64,
        "--chronicle-ref",
        "evidence/chronicle/missing.md",
        "--reason",
        "A retained package must be selected exactly.",
        "--break-glass",
        "--confirm-irreversible",
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["command"] == "lane resolution clear"
    assert "lane_resolution_clear_package_missing" in payload["required_gaps"]


def test_inventory_ignores_historical_ownerless_reservation_state_drift(tmp_path) -> None:
    repo = init_repo(tmp_path / "repo")
    canonical = _ownerless_reservation()
    reservation_store.reserve_ownerless_closeout_target(root=repo, reservation=canonical)
    legacy = {
        **canonical,
        "phase": "receipt",
        "recovery_state": "effect_complete_receipt_missing",
        "postcondition_digest": "f" * 64,
    }
    legacy_path = (
        repo / "build/artifacts/lane-resolution/reservations" / f"{canonical['target_digest']}.json"
    )
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(json.dumps(legacy), encoding="utf-8")

    payload = run_ethos(
        "lane",
        "resolution",
        "inventory",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["data"]["conflicting_decision_ids"] == []
    assert payload["required_gaps"] == ["lane_resolution_inflight_reservation_present"]


def test_inventory_maps_non_object_ownerless_reservation_to_current_record_gap(
    tmp_path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = _ownerless_reservation()
    path = current_record_root(repo) / "reservations" / f"{reservation['target_digest']}.json"
    path.parent.mkdir(parents=True)
    path.write_text("[]\n", encoding="utf-8")

    payload = run_ethos(
        "lane",
        "resolution",
        "inventory",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert payload["summary"]["invalid_current_record_count"] == 1


def test_inventory_preserves_current_record_blocker_through_cli_projection(tmp_path) -> None:
    repo = init_repo(tmp_path / "repo")
    receipt = _receipt()
    receipt["unexpected"] = "field"
    path = current_record_root(repo) / "receipts" / "invalid-extra-field.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    payload = run_ethos(
        "lane",
        "resolution",
        "inventory",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert payload["data"]["summary"]["invalid_current_record_count"] == 1


def test_receipt_writer_rejects_an_unversioned_current_record(
    tmp_path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    unversioned = _receipt()
    unversioned.pop("schema_version")

    assert (
        validate_schema_instance("lane-resolution-receipt.schema.json", unversioned, root=repo)[
            "ok"
        ]
        is False
    )
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        write_resolution_receipt(root=repo, receipt=unversioned)


def test_receipt_contract_requires_preservation_package(tmp_path) -> None:
    repo = init_repo(tmp_path / "repo")
    payload = _receipt()
    payload.pop("preservation_package")

    assert not validate_schema_instance("lane-resolution-receipt.schema.json", payload, root=repo)[
        "ok"
    ]
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        write_resolution_receipt(root=repo, receipt=payload)


@pytest.mark.parametrize("version", [1, 2, 4, "3"])
def test_receipt_contract_rejects_explicit_non_v3_versions(tmp_path, version: object) -> None:
    repo = init_repo(tmp_path / "repo")
    payload = {**_receipt(), "schema_version": version}

    assert (
        validate_schema_instance("lane-resolution-receipt.schema.json", payload, root=repo)["ok"]
        is False
    )
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        write_resolution_receipt(root=repo, receipt=payload)


def test_ownerless_receipt_executor_uses_canonical_holder_ref_contract(tmp_path) -> None:
    repo = init_repo(tmp_path / "repo")
    valid = _receipt()
    valid["ownerless_closeout_binding"] = _ownerless_binding(
        executor_ref="agent:Codex:thread:Executor+1"
    )

    written = Path(
        write_resolution_receipt(
            root=repo,
            receipt=valid,
            require_ownerless_closeout_binding=True,
        )
    )

    assert (
        json.loads(written.read_text(encoding="utf-8"))["ownerless_closeout_binding"][
            "executor_ref"
        ]
        == "agent:Codex:thread:Executor+1"
    )
    invalid = _receipt(decision_id="lane-decision:00000000-0000-4000-8000-000000000002")
    invalid["ownerless_closeout_binding"] = _ownerless_binding(executor_ref="agent:codex:thread")
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        write_resolution_receipt(
            root=repo,
            receipt=invalid,
            require_ownerless_closeout_binding=True,
        )
