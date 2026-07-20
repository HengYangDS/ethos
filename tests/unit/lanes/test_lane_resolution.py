from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.lane as lane_adapter
from ethos.adapters.mutation.resolution._shared import records_artifact_root
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.receipts import lane_resolution_inventory
from ethos.adapters.mutation.resolution.receipts import verify_preservation_package
from ethos.repository.policy.schema import validate_schema_instance
from ethos.surface.cli.lane.resolution import _default_decision_path
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import orphan_work_lane


def test_resolution_decision_default_path_is_a_valid_local_artifact_home(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    paths = (
        _default_decision_path(repo, "work/owner/recovery"),
        _default_decision_path(repo, "work/owner/recovery"),
        _default_decision_path(repo, "work/a-b"),
        _default_decision_path(repo, "work/a/b"),
    )
    expected_parent = tmp_path / "repo-records/recovery/lane-resolution/decisions"

    assert all(path.parent == expected_parent for path in paths)
    assert len(set(paths)) == len(paths)


def test_resolution_decision_record_refuses_to_clobber_existing_path(
    tmp_path: Path,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text("do not replace\n", encoding="utf-8")

    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Existing local records are immutable.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(repo, topic="lane-resolution-test", token="block"),
        recovery_plan="Choose a new unique decision path.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    assert planned["ok"] is False
    assert planned["required_gaps"] == ["lane_resolution_decision_path_exists"]
    assert decision_path.read_text(encoding="utf-8") == "do not replace\n"


def test_records_owner_policy_ignores_dirty_caller_branch_role_bytes(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    caller = tmp_path / "repo-work-caller"
    git(repo, "worktree", "add", "-b", "work/caller", caller.as_posix(), "dev")
    workspace = caller / ".ethos/workspace.toml"
    workspace.parent.mkdir(parents=True, exist_ok=True)
    workspace.write_text('[branch_roles]\naccepted_branch = "work/caller"\n', encoding="utf-8")

    assert records_artifact_root(caller) == (tmp_path / "repo-records/recovery/lane-resolution")


def test_exceptional_resolution_recomputes_observation_before_effect(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Unknown owner; block mutation.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(repo, topic="lane-resolution-test", token="block"),
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
    repo, lane = orphan_work_lane(tmp_path)
    untracked = lane / "notes.txt"
    untracked.write_text("first\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Unknown owner; block mutation.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(repo, topic="lane-resolution-test", token="block"),
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
    repo, _ = orphan_work_lane(tmp_path)
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Unknown owner; block mutation.",
        evidence_refs=("evidence:review",),
        chronicle_ref="evidence/chronicle/missing/decision.md",
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=_default_decision_path(repo, "work/orphan"),
        break_glass=False,
        apply=True,
    )

    assert planned["ok"] is False
    assert "lane_resolution_chronicle_missing" in planned["required_gaps"]


def test_preserve_resolution_writes_recovery_package_and_completion_receipt(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# dirty preserved\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve owner-unknown work.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-test", token="preserve"
        ),
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
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "notes.txt").write_text("owner-unknown work\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve all recoverable work.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-test", token="preserve"
        ),
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
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# dirty preserved then retired\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")

    blocked = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve-retire",
        reason="Retire only after durable preservation.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-test", token="preserve-retire"
        ),
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
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# tracked delta\n", encoding="utf-8")
    (lane / "notes.txt").write_text("untracked delta\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve-retire",
        reason="Owner is unavailable; preserve before exceptional retirement.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-test", token="preserve-retire"
        ),
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


def test_preserve_retire_records_survive_resolution_carrier_removal(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# retained after carrier removal\n", encoding="utf-8")
    chronicle_ref = write_chronicle_decision(
        repo, topic="lane-resolution-test", token="preserve-retire"
    )
    carrier = tmp_path / "repo-work-carrier"
    git(repo, "worktree", "add", "-b", "work/carrier", carrier.as_posix(), "dev")
    decision_path = _default_decision_path(carrier, "work/orphan")
    planned = plan_lane_resolution(
        root=carrier,
        branch="work/orphan",
        disposition="preserve-retire",
        reason="Preserve outside the disposable resolution carrier.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=chronicle_ref,
        recovery_plan="Retain the exact package after both lanes are absent.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )

    applied = apply_lane_resolution(
        root=carrier,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    records_root = tmp_path / "repo-records/recovery/lane-resolution"
    assert Path(str(planned["decision_path"])).is_relative_to(records_root)
    assert Path(str(applied["preservation_package"]["path"])).is_relative_to(records_root)
    assert Path(str(applied["receipt_path"])).is_relative_to(records_root)
    git(repo, "worktree", "remove", "--force", carrier.as_posix())
    git(repo, "branch", "-D", "work/carrier")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is True
    retained = inventory["entries"][0]
    assert retained["state"] == "retained"
    verify_preservation_package(
        root=repo,
        package={
            "path": retained["package_path"],
            "manifest_sha256": retained["manifest_sha256"],
        },
    )


def test_preserve_retire_from_target_lane_uses_pinned_records_owner(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    chronicle_ref = write_chronicle_decision(
        repo, topic="lane-resolution-test", token="preserve-retire"
    )
    lane = tmp_path / "repo-work-self"
    git(repo, "worktree", "add", "-b", "work/self", lane.as_posix(), "dev")
    (lane / "README.md").write_text("# self-retiring lane\n", encoding="utf-8")
    decision_path = _default_decision_path(lane, "work/self")
    plan_lane_resolution(
        root=lane,
        branch="work/self",
        disposition="preserve-retire",
        reason="Preserve before removing the invoking target lane.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=chronicle_ref,
        recovery_plan="Pin the accepted records owner before the effect.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )

    applied = apply_lane_resolution(
        root=lane,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert applied["ok"] is True
    assert applied["state"] == "preserved_and_retired"
    assert not lane.exists()
    assert Path(str(applied["receipt_path"])).is_file()


def test_receipt_failure_after_destructive_effect_reports_partial_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# destructive receipt failure\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve-retire",
        reason="Exercise the post-effect receipt failure boundary.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-test", token="preserve-retire"
        ),
        recovery_plan="Keep the stable package inspectable if receipt materialization fails.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )

    def fail_receipt_write(
        *,
        root: Path,
        receipt: dict[str, object],
        artifact_root: Path | None = None,
    ) -> str:
        del root, receipt, artifact_root
        raise OSError("receipt unavailable")

    monkeypatch.setattr(lane_adapter, "write_resolution_receipt", fail_receipt_write)
    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_receipt_write_failed_after_effect"]
    assert report["receipt"]["completed"] is True
    assert not lane.exists()
    assert Path(str(report["preservation_package"]["path"])).is_dir()


def test_preservation_package_verifier_fails_closed_on_invalid_packages(
    tmp_path: Path,
) -> None:
    root = init_repo(tmp_path / "repo")
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_outside_root"):
        verify_preservation_package(root=root, package={"path": "../outside", "manifest": {}})
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_outside_root"):
        verify_preservation_package(
            root=root,
            package={"path": "evidence/recovery", "manifest": {}},
        )

    relative_package = "build/artifacts/lane-resolution/recovery"
    package = root / relative_package
    package.mkdir(parents=True)
    with pytest.raises(TypeError, match="lane_resolution_preservation_manifest_invalid"):
        verify_preservation_package(root=root, package={"path": relative_package})
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        verify_preservation_package(
            root=root,
            package={"path": relative_package, "manifest": {}},
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
            package={"path": relative_package, "manifest": manifest},
        )


def test_resolution_decision_and_receipt_validate_against_kernel_schemas(
    tmp_path: Path,
) -> None:
    repo, _ = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep ambiguous state intact.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(repo, topic="lane-resolution-test", token="block"),
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
    repo, _ = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep ambiguous state intact.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(repo, topic="lane-resolution-test", token="block"),
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


@pytest.mark.parametrize("identifier_kind", ["absolute", "traversal"])
def test_resolution_rejects_unsafe_decision_identifier_before_package_write(
    tmp_path: Path,
    identifier_kind: str,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# preserve safely\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Reject identifiers that can escape the package owner.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-test", token="preserve"
        ),
        recovery_plan="Require a canonical lane-decision UUID.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["decision_id"] = (
        (tmp_path / "absolute-escape").as_posix()
        if identifier_kind == "absolute"
        else "lane-decision:../../traversal-escape"
    )
    decision_path.write_text(json.dumps(decision), encoding="utf-8")

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is False
    assert "lane_resolution_decision_invalid" in applied["required_gaps"]


def test_resolution_rejects_symlinked_package_destination_outside_records_owner(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# preserve safely\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Reject a package destination redirected outside the records owner.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-test", token="preserve"
        ),
        recovery_plan="Resolve the final package path before writing.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    decision_id = str(planned["decision"]["decision_id"])
    uuid.UUID(decision_id.removeprefix("lane-decision:"))
    outside = tmp_path / "outside-package"
    outside.mkdir()
    package_path = records_artifact_root(repo) / decision_id
    package_path.symlink_to(outside, target_is_directory=True)

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is False
    assert applied["required_gaps"] == ["lane_resolution_preservation_path_outside_root"]
    assert list(outside.iterdir()) == []


def test_resolution_decide_does_not_write_tracked_chronicle_path(
    tmp_path: Path,
) -> None:
    repo, _ = orphan_work_lane(tmp_path)
    decision_path = repo / "evidence" / "chronicle" / "decision.json"

    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep ambiguous state intact.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(repo, topic="lane-resolution-test", token="block"),
        recovery_plan="Preserve or block exact observed state before effect.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    assert planned["ok"] is False
    assert "lane_resolution_decision_path_not_local_artifact" in planned["required_gaps"]
    assert not decision_path.exists()


def test_resolution_decide_rejects_registered_legacy_worktree_path(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = lane / "build/artifacts/lane-resolution/decisions/foreign.json"

    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="A registered Work Lane must not own a new decision record.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(repo, topic="lane-resolution-test", token="block"),
        recovery_plan="Write new decisions only through the stable records owner.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    assert planned["ok"] is False
    assert planned["required_gaps"] == ["lane_resolution_decision_path_not_local_artifact"]
    assert not decision_path.exists()


def test_retire_resolution_requires_clean_target_and_irreversible_confirmation(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="retire",
        reason="Reviewed obsolete lane.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=write_chronicle_decision(repo, topic="lane-resolution-test", token="retire"),
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
    repo, _ = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Emergency containment.",
        evidence_refs=("evidence:incident",),
        chronicle_ref=write_chronicle_decision(repo, topic="lane-resolution-test", token="block"),
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
