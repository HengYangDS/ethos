from __future__ import annotations

# fmt: off
import json
import sqlite3
import tarfile
from contextlib import closing
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.store.state.maintenance as maintenance
from ethos.adapters.mutation.proof import proof_state_dir
from ethos.adapters.store.state.events import initialize_state
from ethos.adapters.store.state.maintenance import apply_local_state_maintenance
from ethos.adapters.store.state.maintenance import local_state_maintenance_inventory
from ethos.surface.cli.root import inspection as inspection_cli
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

OBSERVED_AT = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)


def _repo(tmp_path: Path) -> Path:
    return init_git_repo(tmp_path / "repo")


def _insert_lease(
    repo: Path, *, lease_id: str, subject: str, expires_at: str,
    payload: dict[str, object] | str,
) -> None:
    db_path = repo / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)
    if isinstance(payload, dict):
        payload = dict(payload)
        payload["lease_id"] = lease_id if payload.get("lease_id") == "lease:fixture" else payload.get("lease_id")
        payload["lane_ref"] = subject if payload.get("lane_ref") == "work/fixture" else payload.get("lane_ref")
    payload_json = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) values (?, ?, 'agent:test:case:owner', ?, ?)",
            (lease_id, subject, expires_at, payload_json),
        )
        connection.commit()


def _normalized_payload(*, path: str = "", expected_head: str = "") -> dict[str, object]:
    return {
        "lease_id": "lease:fixture", "lane_incarnation_id": "lane-incarnation:fixture",
        "lane_ref": "work/fixture", "holder_ref": "agent:test:case:owner", "epoch": 1,
        "issued_at": "2026-07-01T00:00:00+00:00", "renewed_at": "2026-07-01T00:00:00+00:00",
        "expected_head": expected_head, "normalization_state": "normalized", "path": path,
    }


def _write_proof(repo: Path, head: str) -> Path:
    path = proof_state_dir(repo) / f"{head}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 3, "head": head, "state": "proven"}))
    return path


def _apply(repo: Path, archive_root: Path, inventory: dict[str, Any], *, digest: str = "", confirm: bool = True) -> dict[str, Any]:
    return apply_local_state_maintenance(repo, archive_root, OBSERVED_AT,
        expect_inventory_digest=digest or str(inventory["inventory_digest"]),
        confirm_irreversible=confirm)


def test_inventory_requires_an_absolute_external_archive_root(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(ValueError, match="maintenance_archive_root_must_be_absolute"):
        local_state_maintenance_inventory(repo, Path("relative"), OBSERVED_AT)
    with pytest.raises(ValueError, match="maintenance_archive_root_must_be_external"):
        local_state_maintenance_inventory(repo, repo / "archive", OBSERVED_AT)


def test_inventory_prunes_only_expired_unobservable_normalized_leases(tmp_path: Path) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    missing_path, existing_path = tmp_path / "missing-worktree", tmp_path / "recorded-worktree"
    existing_path.mkdir()
    git(repo, "branch", "work/ref-present")
    git(repo, "worktree", "add", "-b", "work/linked", (tmp_path / "linked-worktree").as_posix(), "HEAD")
    expired, active = "2026-07-18T00:00:00+00:00", "2026-07-20T00:00:00+00:00"
    fixtures = (
        ("lease:orphan", "work/orphan", expired, _normalized_payload(path=missing_path.as_posix())),
        ("lease:active", "work/active", active, _normalized_payload(path=missing_path.as_posix())),
        ("lease:ref", "work/ref-present", expired, _normalized_payload(path=missing_path.as_posix())),
        ("lease:linked", "work/linked", expired, _normalized_payload(path=missing_path.as_posix())),
        ("lease:path", "work/path", expired, _normalized_payload(path=existing_path.as_posix())),
        ("lease:bad-expiry", "work/bad-expiry", "not-a-time", _normalized_payload()),
        ("lease:bad-payload", "work/bad-payload", expired, "[not-an-object]"),
        ("lease:legacy", "work/legacy", expired, {}),
        ("lease:mismatched", "work/mismatched", expired, {**_normalized_payload(), "lease_id": "lease:different"}),
        ("lease:bad-subject", "work/bad..subject", expired, _normalized_payload()),
    )
    for lease_id, subject, expires_at, payload in fixtures:
        _insert_lease(repo, lease_id=lease_id, subject=subject, expires_at=expires_at, payload=payload)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert [item["id"] for item in inventory["leases"]["delete_candidates"]] == ["lease:orphan"]
    retained = {item["id"]: item["reasons"] for item in inventory["leases"]["retained"]}
    expected = {"lease:active": "unexpired", "lease:ref": "branch_ref_present",
        "lease:linked": "linked_worktree_present", "lease:path": "recorded_path_present",
        "lease:bad-expiry": "malformed_expiry", "lease:bad-payload": "malformed_payload",
        "lease:legacy": "ambiguous_lease", "lease:mismatched": "ambiguous_lease",
        "lease:bad-subject": "malformed_subject"}
    assert all(reason in retained[lease_id] for lease_id, reason in expected.items())


def test_inventory_protects_current_ref_worktree_and_live_lease_proofs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    ref_reachable = git(repo, "rev-parse", "HEAD")
    (repo / "next.txt").write_text("next\n", encoding="utf-8")
    git(repo, "add", "next.txt")
    git(repo, "-c", "user.name=Test User", "-c", "user.email=test@example.com", "commit", "-m", "next")
    current, worktree_head, live_lease_head, unreachable = git(repo, "rev-parse", "HEAD"), "c" * 40, "d" * 40, "e" * 40
    for head in (current, ref_reachable, worktree_head, live_lease_head, unreachable):
        _write_proof(repo, head)
    _insert_lease(repo, lease_id="lease:live", subject="work/live", expires_at="2026-07-20T00:00:00+00:00",
        payload=_normalized_payload(expected_head=live_lease_head))
    monkeypatch.setattr(maintenance, "_git_worktree_heads", lambda _root: {current, worktree_head})
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert [item["head"] for item in inventory["proofs"]["delete_candidates"]] == [unreachable]
    assert {item["head"] for item in inventory["proofs"]["retained"]} == {current, ref_reachable, worktree_head, live_lease_head}


def test_inventory_is_read_only_and_digest_changes_when_source_changes(tmp_path: Path) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    source = repo / ".ethos" / "state" / "residue-snapshots" / "dirty.patch"
    source.parent.mkdir(parents=True)
    source.write_text("first\n", encoding="utf-8")
    first = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert (source.read_text(encoding="utf-8"), archive_root.exists()) == ("first\n", False)
    source.write_text("second\n", encoding="utf-8")
    assert first["inventory_digest"] != local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)["inventory_digest"]


def test_apply_requires_confirmation_and_exact_inventory_digest(tmp_path: Path) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    with pytest.raises(ValueError, match="maintenance_irreversible_confirmation_required"):
        _apply(repo, archive_root, inventory, confirm=False)
    with pytest.raises(ValueError, match="maintenance_inventory_digest_mismatch"):
        _apply(repo, archive_root, inventory, digest="0" * 64)


def test_apply_archives_verifies_and_prunes_exact_inventory_idempotently(tmp_path: Path) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    snapshots = repo / ".ethos" / "state" / "residue-snapshots"
    (snapshots / "nested").mkdir(parents=True)
    (snapshots / "dirty.patch").write_text("patch\n", encoding="utf-8")
    (snapshots / "nested" / "untracked.txt").write_text("recover\n", encoding="utf-8")
    _insert_lease(repo, lease_id="lease:orphan", subject="work/orphan", expires_at="2026-07-18T00:00:00+00:00",
        payload=_normalized_payload(path=(tmp_path / "gone").as_posix()))
    proof = _write_proof(repo, "e" * 40)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    applied = _apply(repo, archive_root, inventory)
    assert (applied["ok"], applied["state"], applied["deleted"]["lease_ids"]) == (True, "applied", ["lease:orphan"])
    assert applied["deleted"]["proof_paths"] == [proof.relative_to(repo).as_posix()]
    assert (applied["deleted"]["recovery_snapshot"], snapshots.exists()) == (True, False)
    archive_path = Path(applied["archive"]["path"])
    assert (
        archive_path.is_file(),
        bool(applied["archive"]["sha256"]),
        bool(applied["archive"]["entry_manifest_digest"]),
    ) == (True, True, True)
    manifest = json.loads(Path(applied["archive"]["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["archive"] == {"path": archive_path.as_posix(), "sha256": applied["archive"]["sha256"], "size": applied["archive"]["size"]}
    assert manifest["bundle_verifications"] == []
    with tarfile.open(archive_path, "r") as archive:
        names = set(archive.getnames())
    assert {"local-state/.ethos/state/residue-snapshots/dirty.patch",
        "local-state/.ethos/state/residue-snapshots/nested/untracked.txt"} <= names
    replay = _apply(repo, archive_root, inventory)
    assert (replay["state"], replay["archive"]["sha256"]) == ("already_applied", applied["archive"]["sha256"])


def test_apply_keeps_sources_when_bundle_verification_fails(tmp_path: Path) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    bundle = repo / ".ethos" / "state" / "residue-snapshots" / "recovery.bundle"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("not a git bundle\n", encoding="utf-8")
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    with pytest.raises(RuntimeError, match="maintenance_bundle_verify_failed"):
        _apply(repo, archive_root, inventory)
    assert bundle.exists()


def test_apply_verifies_extracted_valid_git_bundle_against_repository(tmp_path: Path) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    bundle = repo / ".ethos" / "state" / "residue-snapshots" / "recovery.bundle"
    bundle.parent.mkdir(parents=True)
    git(repo, "bundle", "create", bundle.as_posix(), "--all")
    applied = _apply(repo, archive_root, local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT))
    expected = [{"path": "recovery.bundle", "verified": True}]
    assert applied["archive"]["bundle_verifications"] == expected
    assert applied["archive"]["extraction"]["bundle_verifications"] == expected


def test_apply_keeps_sources_when_archive_extraction_verification_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    source = repo / ".ethos" / "state" / "residue-snapshots" / "dirty.patch"
    source.parent.mkdir(parents=True)
    source.write_text("patch\n", encoding="utf-8")
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    def fail_extraction(*_args: object, **_kwargs: object) -> dict[str, object]:
        message = "maintenance_archive_extraction_failed"
        raise RuntimeError(message)
    monkeypatch.setattr(maintenance, "_verify_archive_extraction", fail_extraction)
    with pytest.raises(RuntimeError, match="maintenance_archive_extraction_failed"):
        _apply(repo, archive_root, inventory)
    assert source.exists()


def test_apply_restores_sources_when_receipt_write_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    source = repo / ".ethos" / "state" / "residue-snapshots" / "dirty.patch"
    source.parent.mkdir(parents=True)
    source.write_text("patch\n", encoding="utf-8")
    _insert_lease(repo, lease_id="lease:orphan", subject="work/orphan", expires_at="2026-07-18T00:00:00+00:00",
        payload=_normalized_payload(path=(tmp_path / "gone").as_posix()))
    proof = _write_proof(repo, "e" * 40)
    inventory, original_write = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT), maintenance._write_json_atomic
    def fail_receipt(path: Path, payload: dict[str, object]) -> None:
        if path.name.endswith(".receipt.json"):
            message = "receipt write failed"
            raise OSError(message)
        original_write(path, payload)
    monkeypatch.setattr(maintenance, "_write_json_atomic", fail_receipt)
    with pytest.raises(OSError, match="receipt write failed"):
        _apply(repo, archive_root, inventory)
    assert (source.exists(), proof.exists()) == (True, True)
    restored = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert [item["id"] for item in restored["leases"]["delete_candidates"]] == ["lease:orphan"]


def test_maintenance_helpers_preserve_fail_closed_edges(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    for observed, gap in (("not-a-time", "invalid"), (OBSERVED_AT.replace(tzinfo=None), "timezone_required")):
        with pytest.raises(ValueError, match=gap):
            maintenance._normalized_observed_at(observed)
    with monkeypatch.context() as scoped:
        scoped.setattr(maintenance.subprocess, "run", lambda *_args, **_kwargs: maintenance.subprocess.CompletedProcess([], 1, "", ""))
        with pytest.raises(RuntimeError, match="maintenance_git_observation_failed"):
            maintenance._git_lines(repo, "bad")
    with monkeypatch.context() as scoped:
        scoped.setattr(maintenance, "_git_lines", lambda *_args: ["", "worktree /tmp/lane", "HEAD abc", "branch refs/heads/work/x", "locked reason"])
        assert maintenance._git_worktrees(repo) == [{"worktree": "/tmp/lane", "head": "abc", "branch": "work/x"}]
    bad_db = tmp_path / "bad.sqlite"
    bad_db.touch()
    with monkeypatch.context() as scoped:
        scoped.setattr(maintenance.sqlite3, "connect", lambda *_args, **_kwargs: (_ for _ in ()).throw(sqlite3.OperationalError()))
        assert maintenance._database_inventory(bad_db)["error"] == "OperationalError"
    with monkeypatch.context() as scoped:
        scoped.setattr(maintenance, "lease_inventory_rows", lambda *_args: (_ for _ in ()).throw(sqlite3.OperationalError()))
        assert maintenance._lease_inventory(repo, observed=OBSERVED_AT, branch_refs=set(), worktree_branches=set())[0]["error"] == "OperationalError"
    row = {"id": "lease:x", "subject": "work/x", "owner": "agent:test:case:owner",
        "expires_at": "2026-07-18T00:00:00+00:00", "payload_json": "{}", "payload_valid": True,
        "payload": {**_normalized_payload(), "lease_id": "lease:x", "lane_ref": "work/x", "path": 1}}
    assert "malformed_recorded_path" in maintenance._lease_retention_reasons(repo, row, observed=OBSERVED_AT, branch_refs=set(), worktree_branches=set())[0]
    assert not maintenance._valid_branch_subject(repo, "")
    assert maintenance._lease_time_reasons({"expires_at": "2026-07-18T00:00:00"}, OBSERVED_AT) == (["malformed_expiry"], None)
    assert (
        maintenance._tree_entries(tmp_path / "missing"),
        maintenance._verify_bundles(tmp_path / "missing", cwd=repo),
    ) == ([], [])
    fifo = tmp_path / "fifo"
    maintenance.os.mkfifo(fifo)
    with pytest.raises(ValueError, match="entry_unsupported"):
        maintenance._tree_entries(tmp_path)
    symlink_root = tmp_path / "symlinks"
    symlink_root.mkdir()
    symlink = symlink_root / "link"
    symlink.symlink_to(bad_db)
    with pytest.raises(ValueError, match="symlink_unsupported"):
        maintenance._tree_entries(symlink_root)
    maintenance._stage_local_state(repo, tmp_path / "stage")
    invalid_tar = tmp_path / "invalid.tar"
    invalid_tar.write_text("not a tar", encoding="utf-8")
    with pytest.raises(RuntimeError, match="archive_extraction_failed"):
        maintenance._verify_archive_extraction(invalid_tar, {"entries": []}, repository_root=repo)
    staged = tmp_path / "archive-stage"
    staged.mkdir()
    (staged / "entry").write_text("x", encoding="utf-8")
    valid_archive = maintenance._create_archive(tmp_path, "valid", staged)
    with pytest.raises(RuntimeError, match="entry_verification_failed"):
        maintenance._verify_archive_extraction(valid_archive, {"entries": []}, repository_root=repo)
    assert maintenance._delete_recovery_snapshot(repo, {"source_exists": False}) is False
    snapshots = repo / ".ethos" / "state" / "residue-snapshots"
    snapshots.mkdir(parents=True)
    with pytest.raises(ValueError, match="snapshot_drift"):
        maintenance._delete_recovery_snapshot(repo, {"source_exists": True, "entries": [{"path": "missing"}]})
    maintenance._restore_staged_state(repo, tmp_path / "empty", {"proofs": {"delete_candidates": [{"head": "f" * 40}]}, "recovery": {"source_exists": False}})
    archive_root.mkdir()
    receipt = maintenance._receipt_path(archive_root, "bad")
    receipt.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="existing_receipt_invalid"):
        maintenance._verified_existing_receipt(archive_root, "bad", repo)
    receipt.write_text("{}", encoding="utf-8")
    maintenance._manifest_path(archive_root, "bad").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="existing_receipt_invalid"):
        maintenance._verified_existing_receipt(archive_root, "bad", repo)


def test_doctor_default_is_read_only_and_explicit_maintenance_emits_inventory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    repo, archive_root = _repo(tmp_path), tmp_path / "archive"
    source = repo / ".ethos" / "state" / "residue-snapshots" / "dirty.patch"
    source.parent.mkdir(parents=True)
    source.write_text("patch\n", encoding="utf-8")
    emitted = []
    monkeypatch.setattr(inspection_cli, "emit", lambda result, **_kwargs: emitted.append(result))
    inspection_cli.doctor(root=repo, json_output=True)
    assert (emitted[-1].data["maintenance"], source.exists()) == ({}, True)
    inspection_cli.doctor(root=repo, maintenance=True, archive_root=archive_root,
        observed_at=OBSERVED_AT.isoformat(), json_output=True)
    report = emitted[-1].data["maintenance"]
    assert (bool(report["inventory_digest"]), report["recovery"]["source_exists"]) == (True, True)
    assert (source.exists(), archive_root.exists()) == (True, False)
