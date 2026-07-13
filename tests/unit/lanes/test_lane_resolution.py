from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.receipts import verify_preservation_package
from ethos.repository.policy.schema import validate_schema_instance
from ethos.surface.cli.lane.resolution import _default_decision_path
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo


def _orphan_lane(tmp_path: Path) -> tuple[Path, Path]:
    repo = init_repo(tmp_path / "repo")
    lane = tmp_path / "repo-work-orphan"
    git(repo, "worktree", "add", "-b", "work/orphan", lane.as_posix(), "dev")
    return repo, lane


def _chronicle(repo: Path, disposition: str) -> str:
    relative = Path("evidence") / "chronicle" / "lane-resolution-test" / f"{disposition}.md"
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"decision: lane_resolution/{disposition}\n", encoding="utf-8")
    git(repo, "add", relative.as_posix())
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        f"record {disposition} decision",
    )
    return relative.as_posix()


def test_resolution_decision_default_path_is_a_valid_local_artifact_home(
    tmp_path: Path,
) -> None:
    expected = tmp_path / "build/artifacts/lane-resolution/decisions/work-owner-recovery.json"
    assert _default_decision_path(tmp_path, "work/owner/recovery") == expected


def test_exceptional_resolution_recomputes_observation_before_effect(
    tmp_path: Path,
) -> None:
    repo, lane = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Unknown owner; block mutation.",
        evidence_refs=("evidence:review",),
        chronicle_ref=_chronicle(repo, "block"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    assert planned["ok"] is True
    (lane / "README.md").write_text("# changed after decision\n", encoding="utf-8")

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is False
    assert "lane_resolution_observation_stale" in applied["required_gaps"]


def test_exceptional_resolution_observation_binds_untracked_content(
    tmp_path: Path,
) -> None:
    repo, lane = _orphan_lane(tmp_path)
    untracked = lane / "notes.txt"
    untracked.write_text("first\n", encoding="utf-8")
    decision_path = tmp_path / "decision.json"
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Unknown owner; block mutation.",
        evidence_refs=("evidence:review",),
        chronicle_ref=_chronicle(repo, "block"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    untracked.write_text("second\n", encoding="utf-8")

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is False
    assert "lane_resolution_observation_stale" in applied["required_gaps"]


def test_exceptional_resolution_requires_accepted_chronicle_binding(
    tmp_path: Path,
) -> None:
    repo, _ = _orphan_lane(tmp_path)
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Unknown owner; block mutation.",
        evidence_refs=("evidence:review",),
        chronicle_ref="evidence/chronicle/missing/decision.md",
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=tmp_path / "decision.json",
        break_glass=False,
        apply=True,
    )

    assert planned["ok"] is False
    assert "lane_resolution_chronicle_missing" in planned["required_gaps"]


def test_preserve_resolution_writes_recovery_package_and_completion_receipt(
    tmp_path: Path,
) -> None:
    repo, lane = _orphan_lane(tmp_path)
    (lane / "README.md").write_text("# dirty preserved\n", encoding="utf-8")
    decision_path = tmp_path / "decision.json"
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve owner-unknown work.",
        evidence_refs=("evidence:review",),
        chronicle_ref=_chronicle(repo, "preserve"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is True
    package = applied["preservation_package"]
    assert (repo / package["path"] / "manifest.json").is_file()
    assert applied["receipt"]["completed"] is True
    assert applied["receipt"]["disposition"] == "preserve"
    assert git(repo, "show-ref", "--verify", "refs/heads/work/orphan")


def test_preserve_resolution_includes_non_ignored_untracked_files(
    tmp_path: Path,
) -> None:
    repo, lane = _orphan_lane(tmp_path)
    (lane / "notes.txt").write_text("owner-unknown work\n", encoding="utf-8")
    decision_path = tmp_path / "decision.json"
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve all recoverable work.",
        evidence_refs=("evidence:review",),
        chronicle_ref=_chronicle(repo, "preserve"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    package = repo / applied["preservation_package"]["path"]
    assert (package / "untracked.tar").is_file()
    assert (
        "notes.txt"
        in subprocess.run(
            ["tar", "-tf", (package / "untracked.tar").as_posix()],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )


def test_preserve_retire_requires_break_glass_and_irreversible_confirmation(
    tmp_path: Path,
) -> None:
    repo, lane = _orphan_lane(tmp_path)
    (lane / "README.md").write_text("# dirty preserved then retired\n", encoding="utf-8")
    decision_path = tmp_path / "decision.json"

    blocked = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve-retire",
        reason="Retire only after durable preservation.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=_chronicle(repo, "preserve-retire"),
        recovery_plan="Preserve exact dirty state, verify it, then retire the lane.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    assert "retire_exception_requires_break_glass" in blocked["required_gaps"]

    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve-retire",
        reason="Retire only after durable preservation.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref="evidence/chronicle/lane-resolution-test/preserve-retire.md",
        recovery_plan="Preserve exact dirty state, verify it, then retire the lane.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )

    assert planned["ok"] is True

    pending = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert "irreversible_confirmation_required" in pending["required_gaps"]
    assert lane.exists()


def test_preserve_retire_keeps_verified_recovery_package_before_lane_removal(
    tmp_path: Path,
) -> None:
    repo, lane = _orphan_lane(tmp_path)
    (lane / "README.md").write_text("# tracked delta\n", encoding="utf-8")
    (lane / "notes.txt").write_text("untracked delta\n", encoding="utf-8")
    decision_path = tmp_path / "decision.json"
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve-retire",
        reason="Owner is unavailable; preserve before exceptional retirement.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=_chronicle(repo, "preserve-retire"),
        recovery_plan="Preserve exact dirty state, verify it, then retire the lane.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert planned["ok"] is True
    assert applied["ok"] is True
    assert applied["state"] == "preserved_and_retired"
    package = repo / applied["preservation_package"]["path"]
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    assert (package / "repository.bundle").is_file()
    assert (package / "tracked.patch").is_file()
    assert (package / "untracked.tar").is_file()
    assert manifest["bundle_sha256"]
    assert manifest["patch_sha256"]
    assert manifest["untracked_archive_sha256"]
    assert not lane.exists()
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "refs/heads/work/orphan"],
            cwd=repo,
            check=False,
        ).returncode
        != 0
    )


def test_preservation_package_verifier_fails_closed_on_invalid_packages(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_outside_root"):
        verify_preservation_package(root=root, package={"path": "../outside", "manifest": {}})

    package = root / "build" / "artifacts" / "recovery"
    package.mkdir(parents=True)
    with pytest.raises(TypeError, match="lane_resolution_preservation_manifest_invalid"):
        verify_preservation_package(root=root, package={"path": "build/artifacts/recovery"})
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        verify_preservation_package(
            root=root,
            package={"path": "build/artifacts/recovery", "manifest": {}},
        )

    bundle = package / "repository.bundle"
    patch = package / "tracked.patch"
    archive = package / "untracked.tar"
    bundle.write_bytes(b"bundle")
    patch.write_bytes(b"patch")
    archive.write_bytes(b"archive")
    manifest = {
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "untracked_archive_sha256": "0" * 64,
    }
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        verify_preservation_package(
            root=root,
            package={"path": "build/artifacts/recovery", "manifest": manifest},
        )


def test_resolution_decision_and_receipt_validate_against_kernel_schemas(
    tmp_path: Path,
) -> None:
    repo, _ = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep ambiguous state intact.",
        evidence_refs=("evidence:review",),
        chronicle_ref=_chronicle(repo, "block"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert (
        validate_schema_instance(
            "lane-resolution-decision.schema.json", planned["decision"], root=repo
        )["ok"]
        is True
    )
    assert (
        validate_schema_instance(
            "lane-resolution-receipt.schema.json", applied["receipt"], root=repo
        )["ok"]
        is True
    )


def test_resolution_rejects_tampered_schema_constants(tmp_path: Path) -> None:
    repo, _ = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep ambiguous state intact.",
        evidence_refs=("evidence:review",),
        chronicle_ref=_chronicle(repo, "block"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["mints_authority"] = True
    decision_path.write_text(json.dumps(decision), encoding="utf-8")

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is False
    assert "lane_resolution_decision_invalid" in applied["required_gaps"]


def test_resolution_decide_does_not_write_tracked_chronicle_path(
    tmp_path: Path,
) -> None:
    repo, _ = _orphan_lane(tmp_path)
    decision_path = repo / "evidence" / "chronicle" / "decision.json"

    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep ambiguous state intact.",
        evidence_refs=("evidence:review",),
        chronicle_ref=_chronicle(repo, "block"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    assert planned["ok"] is False
    assert "lane_resolution_decision_path_not_local_artifact" in planned["required_gaps"]
    assert not decision_path.exists()


def test_retire_resolution_requires_clean_target_and_irreversible_confirmation(
    tmp_path: Path,
) -> None:
    repo, lane = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="retire",
        reason="Reviewed obsolete lane.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=_chronicle(repo, "retire"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )

    blocked = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert "irreversible_confirmation_required" in blocked["required_gaps"]

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )
    assert applied["ok"] is True
    assert not lane.exists()
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "refs/heads/work/orphan"],
            cwd=repo,
            check=False,
        ).returncode
        != 0
    )


def test_break_glass_requires_reconciliation_receipt(tmp_path: Path) -> None:
    repo, _ = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Emergency containment.",
        evidence_refs=("evidence:incident",),
        chronicle_ref=_chronicle(repo, "block"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["break_glass"] is True

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert planned["ok"] is True
    assert applied["receipt"]["reconciliation_required"] is True
