from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.receipts as receipt_adapter
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.receipts import LaneResolutionClearRequest
from ethos.adapters.mutation.resolution.receipts import clear_lane_resolution_package
from ethos.adapters.mutation.resolution.receipts import lane_resolution_inventory
from ethos.adapters.mutation.resolution.receipts import verify_preservation_package
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from ethos.surface.cli.lane.resolution import _default_decision_path
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import orphan_work_lane

_LEGACY_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"
_CARRIER_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000002"


def _preserve(repo: Path, lane: Path) -> dict[str, object]:
    (lane / "README.md").write_text("# preserved\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve recoverable owner-unknown work.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-artifacts", token="preserve"
        ),
        recovery_plan="Preserve the exact observed state before any later judgment.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    assert planned["ok"] is True
    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert applied["ok"] is True
    return applied


def test_resolution_materializes_immutable_receipt_and_inventory(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)

    receipt = applied["receipt"]
    receipt_path = repo / str(applied["receipt_path"])
    assert receipt_path.is_file()
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is True
    assert inventory["summary"] == {
        "package_count": 1,
        "receipt_count": 1,
        "clear_count": 0,
    }
    assert inventory["entries"] == [
        {
            "decision_id": receipt["decision_id"],
            "lane_ref": "work/orphan",
            "head": receipt["head"],
            "state": "retained",
            "receipt_path": str(applied["receipt_path"]),
            "package_path": str(applied["preservation_package"]["path"]),
            "manifest_sha256": receipt["preservation_manifest_sha256"],
        }
    ]


def test_resolution_receipt_refuses_to_overwrite_existing_decision(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)

    with pytest.raises(FileExistsError):
        write_resolution_receipt(root=repo, receipt=applied["receipt"])


def test_inventory_reports_receipt_without_preservation_package(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)

    package = repo / str(applied["preservation_package"]["path"])
    receipt_adapter.shutil.rmtree(package)

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["entries"][0]["state"] == "receipt_only"


def test_inventory_keeps_legacy_manifest_visible_without_inventing_receipt(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    package = repo / "build" / "artifacts" / "lane-resolution" / "legacy"
    package.mkdir(parents=True)
    manifest = {
        "decision_id": _LEGACY_DECISION_ID,
        "lane_ref": "work/legacy",
        "head": "a" * 40,
        "observation_digest": "b" * 64,
        "bundle_sha256": "c" * 64,
        "patch_sha256": "d" * 64,
        "untracked_archive_sha256": "",
        "source_lease_transferred": False,
    }
    manifest_path = package / "manifest.json"
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is True
    assert inventory["entries"] == [
        {
            "decision_id": _LEGACY_DECISION_ID,
            "lane_ref": "work/legacy",
            "head": "a" * 40,
            "state": "unindexed",
            "receipt_path": "",
            "package_path": "build/artifacts/lane-resolution/legacy",
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        }
    ]


def test_inventory_reads_legacy_manifest_from_registered_carrier_worktree(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    carrier = tmp_path / "repo-work-carrier"
    git(repo, "worktree", "add", "-b", "work/carrier", carrier.as_posix(), "dev")
    package = carrier / "build/artifacts/lane-resolution/legacy-carrier"
    package.mkdir(parents=True)
    manifest = {
        "decision_id": _CARRIER_DECISION_ID,
        "lane_ref": "work/carrier",
        "head": "a" * 40,
    }
    (package / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is True
    assert inventory["entries"][0]["decision_id"] == _CARRIER_DECISION_ID
    assert inventory["entries"][0]["package_path"] == package.as_posix()


def test_inventory_blocks_conflicting_canonical_and_legacy_decision_records(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    manifest = dict(applied["preservation_package"]["manifest"])
    manifest["head"] = "f" * 40
    legacy = repo / "build/artifacts/lane-resolution/conflicting/manifest.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["state"] == "blocked"
    assert inventory["required_gaps"] == ["lane_resolution_decision_record_conflict"]


def test_clear_blocks_conflicting_canonical_and_legacy_decision_records(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    raw_package = Path(str(applied["preservation_package"]["path"]))
    package = raw_package if raw_package.is_absolute() else repo / raw_package
    canonical_manifest = package / "manifest.json"
    manifest = dict(applied["preservation_package"]["manifest"])
    manifest["head"] = "f" * 40
    legacy = repo / "build/artifacts/lane-resolution/conflicting/manifest.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")

    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=str(applied["receipt"]["decision_id"]),
            expect_manifest_sha256=hashlib.sha256(canonical_manifest.read_bytes()).hexdigest(),
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-artifacts", token="clear-preservation"
            ),
            reason="Conflicting local records must be reconciled before clear.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_decision_record_conflict"]
    assert package.is_dir()
    assert legacy.parent.is_dir()


def test_clear_blocks_identical_canonical_and_legacy_package_copies(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = Path(str(applied["preservation_package"]["path"]))
    canonical_manifest = package / "manifest.json"
    legacy = repo / "build/artifacts/lane-resolution/identical/manifest.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(canonical_manifest.read_bytes())

    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=str(applied["receipt"]["decision_id"]),
            expect_manifest_sha256=hashlib.sha256(canonical_manifest.read_bytes()).hexdigest(),
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-artifacts", token="clear-preservation"
            ),
            reason="Ambiguous duplicate packages require reconciliation.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_clear_package_ambiguous"]
    assert package.is_dir()
    assert legacy.parent.is_dir()


def test_inventory_and_verify_bind_actual_manifest_to_immutable_receipt(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_path = package / "manifest.json"
    tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered["head"] = "f" * 40
    manifest_path.write_text(
        json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["required_gaps"] == ["lane_resolution_manifest_receipt_mismatch"]
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        verify_preservation_package(root=repo, package=applied["preservation_package"])


def test_manual_clear_requires_exact_chronicle_and_manifest_binding(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = repo / str(applied["preservation_package"]["path"])
    manifest_path = package / "manifest.json"
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    decision_id = str(applied["receipt"]["decision_id"])

    blocked = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-artifacts", token="clear-preservation"
            ),
            reason="",
            break_glass=False,
            confirm_irreversible=False,
            apply=True,
        ),
    )

    assert blocked["ok"] is False
    assert set(blocked["required_gaps"]) >= {
        "lane_resolution_clear_reason_required",
        "lane_resolution_clear_requires_break_glass",
        "irreversible_confirmation_required",
    }
    assert package.is_dir()

    cleared = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref="evidence/chronicle/lane-resolution-artifacts/clear-preservation.md",
            reason="Retention review accepted deletion of this exact package.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert cleared["ok"] is True
    assert cleared["state"] == "cleared"
    assert not package.exists()
    assert (repo / str(cleared["clear_receipt_path"])).is_file()


def test_manual_clear_reports_missing_package_and_manifest_mismatch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id="lane-decision:missing",
            expect_manifest_sha256="a" * 64,
            chronicle_ref="evidence/chronicle/missing.md",
            reason="Preservation review requires an exact retained package.",
            break_glass=True,
            confirm_irreversible=True,
            apply=False,
        ),
    )

    assert set(report["required_gaps"]) >= {
        "lane_resolution_clear_package_missing",
        "lane_resolution_clear_manifest_mismatch",
    }


def test_manual_clear_removal_failure_keeps_package_and_discards_clear_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = repo / str(applied["preservation_package"]["path"])
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    decision_id = str(applied["receipt"]["decision_id"])
    chronicle_ref = write_chronicle_decision(
        repo, topic="lane-resolution-artifacts", token="clear-preservation"
    )

    original_rmtree = receipt_adapter.shutil.rmtree

    def fail_remove(path: Path, *args: object, **kwargs: object) -> None:
        if Path(path) == package:
            raise OSError
        original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(receipt_adapter.shutil, "rmtree", fail_remove)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=chronicle_ref,
            reason="The removal path is deliberately exercised before promotion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["required_gaps"] == ["lane_resolution_clear_remove_failed"]
    assert package.is_dir()
    assert not list((repo / "build/artifacts/lane-resolution/clears").glob("*.json"))


def test_receipt_inventory_ignores_malformed_records_and_rejects_invalid_schema(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    artifacts = repo / "build/artifacts/lane-resolution"
    malformed_manifest = artifacts / "malformed" / "manifest.json"
    malformed_manifest.parent.mkdir(parents=True)
    malformed_manifest.write_text("not json", encoding="utf-8")
    receipts = artifacts / "receipts"
    receipts.mkdir()
    (receipts / "invalid-schema.json").write_text("{}", encoding="utf-8")
    (receipts / "malformed.json").write_text("not json", encoding="utf-8")

    assert receipt_adapter._manifests(repo) == {}  # noqa: RUF100, SLF001 - coverage exercises malformed manifest handling
    assert (
        receipt_adapter._records(  # noqa: RUF100, SLF001 - coverage exercises invalid record handling
            repo, "receipts", "lane-resolution-receipt.schema.json"
        )
        == {}
    )
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        receipt_adapter._validate_schema(  # noqa: RUF100, SLF001 - coverage exercises schema refusal
            repo, "lane-resolution-receipt.schema.json", {}
        )


def test_clear_chronicle_rejects_outside_missing_and_mismatched_records(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    outside = tmp_path / "outside.md"
    outside.write_text("decision: lane_resolution/clear-preservation\n", encoding="utf-8")
    mismatch = repo / "evidence/chronicle/lane-resolution-artifacts/mismatch.md"
    mismatch.parent.mkdir(parents=True)
    mismatch.write_text("decision: lane_resolution/preserve\n", encoding="utf-8")

    assert receipt_adapter._clear_chronicle(  # noqa: RUF100, SLF001 - coverage exercises Chronicle boundary refusal
        repo, outside.as_posix()
    )[2] == ["lane_resolution_clear_chronicle_outside_repository"]
    assert receipt_adapter._clear_chronicle(  # noqa: RUF100, SLF001 - coverage exercises missing Chronicle refusal
        repo, "evidence/chronicle/missing.md"
    )[2] == ["lane_resolution_clear_chronicle_missing"]
    assert receipt_adapter._clear_chronicle(  # noqa: RUF100, SLF001 - coverage exercises Chronicle token refusal
        repo, "evidence/chronicle/lane-resolution-artifacts/mismatch.md"
    )[2] == ["lane_resolution_clear_chronicle_disposition_mismatch"]
