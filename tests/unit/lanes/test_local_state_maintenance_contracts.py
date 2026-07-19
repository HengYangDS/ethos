from __future__ import annotations

import tarfile
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.store.state.maintenance as maintenance
from ethos.surface.cli.root import inspection as inspection_cli
from tests.support.contract_helpers import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

OBSERVED_AT = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)


def _repo(tmp_path: Path) -> Path:
    return init_git_repo(tmp_path / "repo")


def test_archive_extraction_rejects_invalid_and_mismatched_payloads(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.tar"
    invalid.write_text("not a tar\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="maintenance_archive_extraction_failed"):
        maintenance._verify_archive_extraction(
            invalid,
            {"entries": []},
            repository_root=tmp_path,
        )

    payload = tmp_path / "payload" / "local-state"
    payload.mkdir(parents=True)
    (payload / "state.txt").write_text("state\n", encoding="utf-8")
    archive = tmp_path / "mismatched.tar"
    with tarfile.open(archive, "w") as stream:
        stream.add(payload, arcname="local-state")
    with pytest.raises(RuntimeError, match="maintenance_archive_entry_verification_failed"):
        maintenance._verify_archive_extraction(
            archive,
            {"entries": []},
            repository_root=tmp_path,
        )


def test_replay_validation_rejects_drift_and_malformed_receipts(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    archive_root.mkdir()
    digest = "0" * 64
    maintenance._receipt_path(archive_root, digest).write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="maintenance_existing_receipt_invalid"):
        maintenance._verified_existing_receipt(archive_root, digest, repo)

    maintenance._receipt_path(archive_root, digest).write_text("{}", encoding="utf-8")
    maintenance._manifest_path(archive_root, digest).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="maintenance_existing_receipt_invalid"):
        maintenance._verified_existing_receipt(archive_root, digest, repo)

    for receipt in ({"deleted": []}, {"deleted": {"proof_paths": ["../escape"]}}):
        with pytest.raises(ValueError, match="maintenance_existing_receipt_invalid"):
            maintenance._verify_receipt_postconditions(repo, receipt)
    (repo / ".ethos" / "state" / "residue-snapshots").mkdir(parents=True)
    with pytest.raises(ValueError, match="maintenance_existing_receipt_postcondition_failed"):
        maintenance._verify_receipt_postconditions(
            repo,
            {"deleted": {"proof_paths": [], "recovery_snapshot": True}},
        )


def test_doctor_default_is_read_only_and_explicit_maintenance_emits_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    snapshots = repo / ".ethos" / "state" / "residue-snapshots"
    snapshots.mkdir(parents=True)
    source = snapshots / "dirty.patch"
    source.write_text("patch\n", encoding="utf-8")
    emitted = []
    monkeypatch.setattr(inspection_cli, "emit", lambda result, **_kwargs: emitted.append(result))

    inspection_cli.doctor(root=repo, json_output=True)
    assert emitted[-1].data["maintenance"] == {}
    assert source.exists()

    inspection_cli.doctor(
        root=repo,
        maintenance=True,
        archive_root=archive_root,
        observed_at=OBSERVED_AT.isoformat(),
        json_output=True,
    )
    report = emitted[-1].data["maintenance"]
    assert report["inventory_digest"]
    assert report["recovery"]["source_exists"] is True
    assert source.exists()
    assert not archive_root.exists()


def test_doctor_maintenance_reports_stable_boundary_gaps(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    emitted = []
    monkeypatch.setattr(inspection_cli, "emit", lambda result, **_kwargs: emitted.append(result))

    inspection_cli.doctor(root=repo, maintenance=True, json_output=True)
    assert emitted[-1].required_gaps == (
        "maintenance_archive_root_required",
        "maintenance_observed_at_required",
    )

    for error, gap in (
        (
            RuntimeError("maintenance_archive_extraction_failed"),
            "maintenance_archive_extraction_failed",
        ),
        (ValueError("invalid"), "maintenance_operation_failed"),
        (OSError(), "maintenance_operation_failed"),
    ):

        def fail_inventory(*_args: object, _error: Exception = error) -> dict[str, object]:
            raise _error

        monkeypatch.setattr(inspection_cli, "local_state_maintenance_inventory", fail_inventory)
        inspection_cli.doctor(
            root=repo,
            maintenance=True,
            archive_root=tmp_path / "archive",
            observed_at=OBSERVED_AT.isoformat(),
            json_output=True,
        )
        assert emitted[-1].required_gaps == (gap,)

    archive_root = tmp_path / "archive"

    def apply(*args: object, **kwargs: object) -> dict[str, object]:
        assert args == (repo, archive_root, OBSERVED_AT.isoformat())
        assert kwargs == {
            "expect_inventory_digest": "digest",
            "confirm_irreversible": True,
        }
        return {"state": "applied"}

    monkeypatch.setattr(inspection_cli, "apply_local_state_maintenance", apply)
    inspection_cli.doctor(
        root=repo,
        apply_maintenance=True,
        archive_root=archive_root,
        observed_at=OBSERVED_AT.isoformat(),
        expect_inventory_digest="digest",
        confirm_irreversible=True,
        json_output=True,
    )

    assert emitted[-1].summary["maintenance_state"] == "applied"
