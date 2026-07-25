from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution._effects as effect_adapter
import ethos.adapters.mutation.resolution.closeout.cleanup.core as cleanup_adapter
import ethos.adapters.mutation.resolution.closeout.recovery as recovery_adapter
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.receipts import verify_preservation_package
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.repository.policy.schema import validate_schema_instance
from ethos.surface.cli.lane.resolution import _default_decision_path
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import orphan_work_lane


def _decide(
    root: Path,
    decision_path: Path,
    disposition: str = "block",
    *,
    chronicle_ref: str | None = None,
    break_glass: bool | None = None,
) -> dict[str, object]:
    exceptional = disposition in {"preserve-retire", "retire"}
    return plan_lane_resolution(
        root=root,
        branch="work/orphan",
        disposition=disposition,
        reason="Exercise the bounded lane-resolution transition.",
        evidence_refs=(("evidence:maintainer-decision",) if exceptional else ("evidence:review",)),
        chronicle_ref=chronicle_ref
        or write_chronicle_decision(root, topic="lane-resolution-test", token=disposition),
        recovery_plan="Preserve exact observed state or block before effect.",
        decision_path=decision_path,
        break_glass=exceptional if break_glass is None else break_glass,
        apply=True,
    )


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
    expected_parent = tmp_path / "repo-records/recovery/lane-resolution-v2/decisions"

    assert all(path.parent == expected_parent for path in paths)
    assert len(set(paths)) == len(paths)


def test_resolution_decision_record_refuses_to_clobber_existing_path(
    tmp_path: Path,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text("do not replace\n", encoding="utf-8")

    planned = _decide(repo, decision_path)

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

    assert current_record_root(caller) == (tmp_path / "repo-records/recovery/lane-resolution-v2")


def test_resolution_decision_rejects_symlinked_records_owner(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    outside = tmp_path / "outside-records"
    outside.mkdir()
    (tmp_path / "repo-records").symlink_to(outside, target_is_directory=True)
    decision_path = _default_decision_path(repo, "work/orphan")

    report = _decide(repo, decision_path)

    assert report["required_gaps"] == ["lane_resolution_decision_path_not_local_artifact"]
    assert not tuple(outside.rglob("*"))


def test_exceptional_resolution_recomputes_observation_before_effect(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
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
    _decide(repo, decision_path)
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
    planned = _decide(
        repo,
        _default_decision_path(repo, "work/orphan"),
        chronicle_ref="evidence/chronicle/missing/decision.md",
    )

    assert planned["ok"] is False
    assert "lane_resolution_chronicle_missing" in planned["required_gaps"]


def test_preserve_resolution_writes_recovery_package_and_completion_receipt(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# dirty preserved\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    _decide(repo, decision_path, "preserve")

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
    assert applied["receipt"]["state"] == "preserved"
    assert "disposition" not in applied["receipt"]
    assert git(repo, "show-ref", "--verify", "refs/heads/work/orphan")


def test_preserve_resolution_includes_non_ignored_untracked_files(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "notes.txt").write_text("owner-unknown work\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    _decide(repo, decision_path, "preserve")

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

    blocked = _decide(repo, decision_path, "preserve-retire", break_glass=False)
    assert "retire_exception_requires_break_glass" in blocked["required_gaps"]

    planned = _decide(
        repo,
        decision_path,
        "preserve-retire",
        chronicle_ref="evidence/chronicle/lane-resolution-test/preserve-retire.md",
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
    planned = _decide(repo, decision_path, "preserve-retire")

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


def test_preserve_retire_keeps_exact_index_and_worktree_deltas(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    tracked = lane / "README.md"
    tracked.write_text("# staged state\n", encoding="utf-8")
    git(lane, "add", "README.md")
    expected_index = subprocess.run(
        ["git", "diff", "--cached", "--binary", "HEAD", "--"],
        cwd=lane,
        check=True,
        capture_output=True,
    ).stdout
    tracked.write_text("# unstaged state\n", encoding="utf-8")
    expected_worktree = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--"],
        cwd=lane,
        check=True,
        capture_output=True,
    ).stdout
    decision_path = _default_decision_path(repo, "work/orphan")
    _decide(repo, decision_path, "preserve-retire")

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    package = Path(str(applied["preservation_package"]["path"]))
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    assert (package / "tracked.patch").read_bytes() == expected_worktree
    assert (package / "index.patch").read_bytes() == expected_index
    assert manifest["package_format_version"] == "v2"
    assert manifest["index_patch_sha256"] == hashlib.sha256(expected_index).hexdigest()

    recovered = tmp_path / "recovered"
    git(
        repo,
        "clone",
        "--branch",
        "work/orphan",
        (package / "repository.bundle").as_posix(),
        recovered.as_posix(),
    )
    git(recovered, "apply", (package / "tracked.patch").as_posix())
    git(recovered, "apply", "--cached", (package / "index.patch").as_posix())
    assert (
        subprocess.run(
            ["git", "diff", "--binary", "HEAD", "--"],
            cwd=recovered,
            check=True,
            capture_output=True,
        ).stdout
        == expected_worktree
    )
    assert (
        subprocess.run(
            ["git", "diff", "--cached", "--binary", "HEAD", "--"],
            cwd=recovered,
            check=True,
            capture_output=True,
        ).stdout
        == expected_index
    )
    verify_preservation_package(root=repo, package=applied["preservation_package"])
    (package / "index.patch").write_bytes(b"tampered index state")
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        verify_preservation_package(root=repo, package=applied["preservation_package"])


def test_preservation_package_verifier_keeps_v1_packages_compatible(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    package = current_record_root(repo) / "legacy"
    package.mkdir(parents=True)
    bundle = package / "repository.bundle"
    patch = package / "tracked.patch"
    bundle.write_bytes(b"legacy bundle")
    patch.write_bytes(b"legacy patch")
    manifest = {
        "decision_id": f"lane-decision:{uuid.uuid4()}",
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "untracked_archive_sha256": "",
    }
    (package / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    verify_preservation_package(root=repo, package={"path": package.as_posix()})
    manifest["package_format_version"] = "v3"
    (package / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        verify_preservation_package(root=repo, package={"path": package.as_posix()})


def test_preserve_retire_rechecks_the_source_after_package_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# initial dirty state\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    _decide(repo, decision_path, "preserve-retire")
    verify = effect_adapter.verify_preservation_package

    def mutate_after_verification(**kwargs) -> None:
        verify(**kwargs)
        (lane / "late.txt").write_text("late write\n", encoding="utf-8")

    monkeypatch.setattr(effect_adapter, "verify_preservation_package", mutate_after_verification)

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_observation_stale"]
    assert (lane / "late.txt").read_text(encoding="utf-8") == "late write\n"
    assert not tuple((current_record_root(repo) / "receipts").glob(".*.receipt-reservation"))


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
    planned = _decide(carrier, decision_path, "preserve-retire", chronicle_ref=chronicle_ref)

    applied = apply_lane_resolution(
        root=carrier,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    records_root = tmp_path / "repo-records/recovery/lane-resolution-v2"
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


@pytest.mark.parametrize(
    "case",
    [
        (
            "preserve",
            False,
            False,
            "blocked",
            "lane_resolution_receipt_write_failed",
            False,
            0,
        ),
        (
            "preserve-retire",
            True,
            True,
            "partial_transition",
            "lane_resolution_receipt_write_failed_after_effect",
            True,
            1,
        ),
    ],
    ids=("preserve", "preserve-retire"),
)
def test_receipt_failure_is_classified_by_effect_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, bool, bool, str, str, bool, int],
) -> None:
    disposition, break_glass, confirm, expected_state, gap, removed, reservations = case
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# receipt failure\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    _decide(
        repo,
        decision_path,
        disposition,
        break_glass=break_glass,
    )

    def fail_receipt_write(
        *,
        root: Path,
        receipt: dict[str, object],
        artifact_root: Path | None = None,
        require_ownerless_closeout_binding: bool = False,
    ) -> str:
        del root, receipt, artifact_root, require_ownerless_closeout_binding
        message = "receipt unavailable"
        raise OSError(message)

    monkeypatch.setattr(recovery_adapter, "write_resolution_receipt", fail_receipt_write)
    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=confirm,
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == expected_state
    assert report["required_gaps"] == [gap]
    assert report["receipt"] == {}
    assert report["receipt_path"] == ""
    assert lane.exists() is not removed
    assert Path(str(report["preservation_package"]["path"])).is_dir()
    pending = tuple((current_record_root(repo) / "receipts").glob(".*.receipt-reservation"))
    assert len(pending) == reservations


def test_resolution_reports_reservation_cleanup_failure_after_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    _decide(repo, decision_path)
    monkeypatch.setattr(
        cleanup_adapter,
        "release_resolution_receipt_reservation",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("cleanup failed")),
    )

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert (report["ok"], report["state"], report["required_gaps"]) == (
        False,
        "partial_transition",
        ["lane_resolution_receipt_reservation_release_failed"],
    )
    assert report["receipt"]["completed"] is True
    assert len(tuple((current_record_root(repo) / "receipts").glob(".*.receipt-reservation"))) == 1


def test_existing_receipt_blocks_preserve_retire_before_destructive_effect(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# receipt destination already exists\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path, "preserve-retire")
    decision_id = str(planned["decision"]["decision_id"])
    receipt_path = (
        current_record_root(repo)
        / "receipts"
        / f"{hashlib.sha256(decision_id.encode()).hexdigest()}.json"
    )
    receipt_path.parent.mkdir(parents=True)
    original = b"do not replace\n"
    receipt_path.write_bytes(original)

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert lane.is_dir()
    assert git(repo, "show-ref", "--verify", "refs/heads/work/orphan")
    assert receipt_path.read_bytes() == original
    assert report["preservation_package"] == {}
    assert report["receipt"] == {}
    assert not (current_record_root(repo) / decision_id).exists()
    assert not tuple(receipt_path.parent.glob(".*.receipt-reservation"))


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

    package = current_record_root(root) / "recovery"
    package.mkdir(parents=True)
    with pytest.raises(TypeError, match="lane_resolution_preservation_manifest_invalid"):
        verify_preservation_package(root=root, package={"path": package})
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        verify_preservation_package(
            root=root,
            package={"path": package, "manifest": {}},
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
            package={"path": package, "manifest": manifest},
        )


def test_resolution_decision_and_receipt_validate_against_kernel_schemas(
    tmp_path: Path,
) -> None:
    repo, _ = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
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
    _decide(repo, decision_path)
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
    _decide(repo, decision_path, "preserve")
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
    planned = _decide(repo, decision_path, "preserve")
    decision_id = str(planned["decision"]["decision_id"])
    uuid.UUID(decision_id.removeprefix("lane-decision:"))
    outside = tmp_path / "outside-package"
    outside.mkdir()
    package_path = current_record_root(repo) / decision_id
    package_path.symlink_to(outside, target_is_directory=True)

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is False
    assert applied["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert list(outside.iterdir()) == []


def test_resolution_preservation_package_refuses_to_clobber_existing_directory(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# preserve without clobber\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path, "preserve")
    package = current_record_root(repo) / str(planned["decision"]["decision_id"])
    package.mkdir(parents=True)
    tracked_patch = package / "tracked.patch"
    tracked_patch.write_bytes(b"existing recovery bytes")

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is False
    assert applied["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert tracked_patch.read_bytes() == b"existing recovery bytes"
    assert lane.is_dir()
    assert not tuple((current_record_root(repo) / "receipts").glob(".*.receipt-reservation"))


def test_resolution_decide_does_not_write_tracked_chronicle_path(
    tmp_path: Path,
) -> None:
    repo, _ = orphan_work_lane(tmp_path)
    decision_path = repo / "evidence" / "chronicle" / "decision.json"

    planned = _decide(repo, decision_path)

    assert planned["ok"] is False
    assert "lane_resolution_decision_path_not_local_artifact" in planned["required_gaps"]
    assert not decision_path.exists()


def test_resolution_decide_rejects_registered_legacy_worktree_path(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = lane / "build/artifacts/lane-resolution/decisions/foreign.json"

    planned = _decide(repo, decision_path)

    assert planned["ok"] is False
    assert planned["required_gaps"] == ["lane_resolution_decision_path_not_local_artifact"]
    assert not decision_path.exists()


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
        recovery_plan="Preserve exact observed state or block before effect.",
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
