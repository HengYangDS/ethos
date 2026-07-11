from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.receipts import LaneResolutionClearRequest
from ethos.adapters.mutation.resolution.receipts import clear_lane_resolution_package
from ethos.adapters.mutation.resolution.receipts import lane_resolution_inventory
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo


def _orphan_lane(tmp_path: Path) -> tuple[Path, Path]:
    repo = init_repo(tmp_path / "repo")
    lane = tmp_path / "repo-work-orphan"
    git(repo, "worktree", "add", "-b", "work/orphan", lane.as_posix(), "dev")
    return repo, lane


def _chronicle(repo: Path, token: str) -> str:
    relative = Path("evidence") / "chronicle" / "lane-resolution-artifacts" / f"{token}.md"
    document = repo / relative
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text(f"decision: lane_resolution/{token}\n", encoding="utf-8")
    git(repo, "add", relative.as_posix())
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        f"record {token} decision",
    )
    return relative.as_posix()


def _preserve(repo: Path, lane: Path, tmp_path: Path) -> dict[str, object]:
    (lane / "README.md").write_text("# preserved\n", encoding="utf-8")
    decision_path = tmp_path / "decision.json"
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve recoverable owner-unknown work.",
        evidence_refs=("evidence:review",),
        chronicle_ref=_chronicle(repo, "preserve"),
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
    repo, lane = _orphan_lane(tmp_path)
    applied = _preserve(repo, lane, tmp_path)

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
    repo, lane = _orphan_lane(tmp_path)
    applied = _preserve(repo, lane, tmp_path)

    with pytest.raises(FileExistsError):
        write_resolution_receipt(root=repo, receipt=applied["receipt"])


def test_inventory_keeps_legacy_manifest_visible_without_inventing_receipt(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    package = repo / "build" / "artifacts" / "lane-resolution" / "legacy"
    package.mkdir(parents=True)
    manifest = {
        "decision_id": "lane-decision:legacy",
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
            "decision_id": "lane-decision:legacy",
            "lane_ref": "work/legacy",
            "head": "a" * 40,
            "state": "unindexed",
            "receipt_path": "",
            "package_path": "build/artifacts/lane-resolution/legacy",
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        }
    ]


def test_manual_clear_requires_exact_chronicle_and_manifest_binding(
    tmp_path: Path,
) -> None:
    repo, lane = _orphan_lane(tmp_path)
    applied = _preserve(repo, lane, tmp_path)
    package = repo / str(applied["preservation_package"]["path"])
    manifest_path = package / "manifest.json"
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    decision_id = str(applied["receipt"]["decision_id"])

    blocked = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=_chronicle(repo, "clear-preservation"),
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
