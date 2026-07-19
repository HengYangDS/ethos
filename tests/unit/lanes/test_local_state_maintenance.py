from __future__ import annotations

import json
import sqlite3
import tarfile
from contextlib import closing
from datetime import UTC
from datetime import datetime
from pathlib import Path

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
    repo: Path,
    *,
    lease_id: str,
    subject: str,
    expires_at: str,
    payload: dict[str, object] | str,
) -> None:
    db_path = repo / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)
    if isinstance(payload, dict):
        payload = dict(payload)
        if payload.get("lease_id") == "lease:fixture":
            payload["lease_id"] = lease_id
        if payload.get("lane_ref") == "work/fixture":
            payload["lane_ref"] = subject
    payload_json = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            insert into leases(id, subject, owner, expires_at, payload_json)
            values (?, ?, 'agent:test:case:owner', ?, ?)
            """,
            (lease_id, subject, expires_at, payload_json),
        )
        connection.commit()


def _normalized_payload(*, path: str = "", expected_head: str = "") -> dict[str, object]:
    return {
        "lease_id": "lease:fixture",
        "lane_incarnation_id": "lane-incarnation:fixture",
        "lane_ref": "work/fixture",
        "holder_ref": "agent:test:case:owner",
        "epoch": 1,
        "issued_at": "2026-07-01T00:00:00+00:00",
        "renewed_at": "2026-07-01T00:00:00+00:00",
        "expected_head": expected_head,
        "normalization_state": "normalized",
        "path": path,
    }


def _write_proof(repo: Path, head: str) -> Path:
    path = proof_state_dir(repo) / f"{head}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 3, "head": head, "state": "proven"}))
    return path


def test_inventory_requires_an_absolute_external_archive_root(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(ValueError, match="maintenance_archive_root_must_be_absolute"):
        local_state_maintenance_inventory(repo, Path("relative"), OBSERVED_AT)
    with pytest.raises(ValueError, match="maintenance_archive_root_must_be_external"):
        local_state_maintenance_inventory(repo, repo / "archive", OBSERVED_AT)


def test_inventory_prunes_only_expired_unobservable_normalized_leases(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    missing_path = tmp_path / "missing-worktree"
    existing_path = tmp_path / "recorded-worktree"
    existing_path.mkdir()
    git(repo, "branch", "work/ref-present")
    linked_path = tmp_path / "linked-worktree"
    git(repo, "worktree", "add", "-b", "work/linked", linked_path.as_posix(), "HEAD")
    expired = "2026-07-18T00:00:00+00:00"
    active = "2026-07-20T00:00:00+00:00"
    fixtures = (
        (
            "lease:orphan",
            "work/orphan",
            expired,
            _normalized_payload(path=missing_path.as_posix()),
        ),
        (
            "lease:active",
            "work/active",
            active,
            _normalized_payload(path=missing_path.as_posix()),
        ),
        (
            "lease:ref",
            "work/ref-present",
            expired,
            _normalized_payload(path=missing_path.as_posix()),
        ),
        (
            "lease:linked",
            "work/linked",
            expired,
            _normalized_payload(path=missing_path.as_posix()),
        ),
        (
            "lease:path",
            "work/path",
            expired,
            _normalized_payload(path=existing_path.as_posix()),
        ),
        ("lease:bad-expiry", "work/bad-expiry", "not-a-time", _normalized_payload()),
        ("lease:bad-payload", "work/bad-payload", expired, "[not-an-object]"),
        ("lease:legacy", "work/legacy", expired, {}),
        (
            "lease:mismatched",
            "work/mismatched",
            expired,
            {**_normalized_payload(), "lease_id": "lease:different"},
        ),
        (
            "lease:bad-subject",
            "work/bad..subject",
            expired,
            _normalized_payload(),
        ),
    )
    for lease_id, subject, expires_at, payload in fixtures:
        _insert_lease(
            repo,
            lease_id=lease_id,
            subject=subject,
            expires_at=expires_at,
            payload=payload,
        )

    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

    assert [item["id"] for item in inventory["leases"]["delete_candidates"]] == ["lease:orphan"]
    retained = {item["id"]: item["reasons"] for item in inventory["leases"]["retained"]}
    assert "unexpired" in retained["lease:active"]
    assert "branch_ref_present" in retained["lease:ref"]
    assert "linked_worktree_present" in retained["lease:linked"]
    assert "recorded_path_present" in retained["lease:path"]
    assert "malformed_expiry" in retained["lease:bad-expiry"]
    assert "malformed_payload" in retained["lease:bad-payload"]
    assert "ambiguous_lease" in retained["lease:legacy"]
    assert "ambiguous_lease" in retained["lease:mismatched"]
    assert "malformed_subject" in retained["lease:bad-subject"]


def test_inventory_protects_current_ref_worktree_and_live_lease_proofs(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    current = git(repo, "rev-parse", "HEAD")
    (repo / "next.txt").write_text("next\n", encoding="utf-8")
    git(repo, "add", "next.txt")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "next",
    )
    ref_reachable = current
    current = git(repo, "rev-parse", "HEAD")
    worktree_head = "c" * 40
    live_lease_head = "d" * 40
    unreachable = "e" * 40
    for head in (current, ref_reachable, worktree_head, live_lease_head, unreachable):
        _write_proof(repo, head)
    _insert_lease(
        repo,
        lease_id="lease:live",
        subject="work/live",
        expires_at="2026-07-20T00:00:00+00:00",
        payload=_normalized_payload(expected_head=live_lease_head),
    )
    monkeypatch_heads = {current, worktree_head}

    original = maintenance._git_worktree_heads
    maintenance._git_worktree_heads = lambda _root: monkeypatch_heads
    try:
        inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    finally:
        maintenance._git_worktree_heads = original

    assert [item["head"] for item in inventory["proofs"]["delete_candidates"]] == [unreachable]
    assert {item["head"] for item in inventory["proofs"]["retained"]} == {
        current,
        ref_reachable,
        worktree_head,
        live_lease_head,
    }


def test_inventory_is_read_only_and_digest_changes_when_source_changes(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    snapshots = repo / ".ethos" / "state" / "residue-snapshots"
    snapshots.mkdir(parents=True)
    source = snapshots / "dirty.patch"
    source.write_text("first\n", encoding="utf-8")

    first = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert source.read_text(encoding="utf-8") == "first\n"
    assert not archive_root.exists()
    source.write_text("second\n", encoding="utf-8")
    second = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

    assert first["inventory_digest"] != second["inventory_digest"]


def test_apply_requires_confirmation_and_exact_inventory_digest(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

    with pytest.raises(ValueError, match="maintenance_irreversible_confirmation_required"):
        apply_local_state_maintenance(
            repo,
            archive_root,
            OBSERVED_AT,
            expect_inventory_digest=inventory["inventory_digest"],
            confirm_irreversible=False,
        )
    with pytest.raises(ValueError, match="maintenance_inventory_digest_mismatch"):
        apply_local_state_maintenance(
            repo,
            archive_root,
            OBSERVED_AT,
            expect_inventory_digest="0" * 64,
            confirm_irreversible=True,
        )


def test_apply_archives_verifies_and_prunes_exact_inventory_idempotently(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    snapshots = repo / ".ethos" / "state" / "residue-snapshots"
    (snapshots / "nested").mkdir(parents=True)
    (snapshots / "dirty.patch").write_text("patch\n", encoding="utf-8")
    (snapshots / "nested" / "untracked.txt").write_text("recover\n", encoding="utf-8")
    _insert_lease(
        repo,
        lease_id="lease:orphan",
        subject="work/orphan",
        expires_at="2026-07-18T00:00:00+00:00",
        payload=_normalized_payload(path=(tmp_path / "gone").as_posix()),
    )
    unreachable = "e" * 40
    proof = _write_proof(repo, unreachable)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

    applied = apply_local_state_maintenance(
        repo,
        archive_root,
        OBSERVED_AT,
        expect_inventory_digest=inventory["inventory_digest"],
        confirm_irreversible=True,
    )

    assert applied["ok"] is True
    assert applied["state"] == "applied"
    assert applied["deleted"]["lease_ids"] == ["lease:orphan"]
    assert applied["deleted"]["proof_paths"] == [proof.relative_to(repo).as_posix()]
    assert applied["deleted"]["recovery_snapshot"] is True
    assert not snapshots.exists()
    archive_path = Path(applied["archive"]["path"])
    assert archive_path.is_file()
    assert applied["archive"]["sha256"]
    assert applied["archive"]["entry_manifest_digest"]
    manifest = json.loads(Path(applied["archive"]["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["archive"] == {
        "path": archive_path.as_posix(),
        "sha256": applied["archive"]["sha256"],
        "size": applied["archive"]["size"],
    }
    assert manifest["bundle_verifications"] == []
    with tarfile.open(archive_path, "r") as archive:
        names = set(archive.getnames())
    assert "local-state/.ethos/state/residue-snapshots/dirty.patch" in names
    assert "local-state/.ethos/state/residue-snapshots/nested/untracked.txt" in names

    replay = apply_local_state_maintenance(
        repo,
        archive_root,
        OBSERVED_AT,
        expect_inventory_digest=inventory["inventory_digest"],
        confirm_irreversible=True,
    )
    assert replay["state"] == "already_applied"
    assert replay["archive"]["sha256"] == applied["archive"]["sha256"]


def test_apply_keeps_sources_when_bundle_verification_fails(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    snapshots = repo / ".ethos" / "state" / "residue-snapshots"
    snapshots.mkdir(parents=True)
    bundle = snapshots / "recovery.bundle"
    bundle.write_text("not a git bundle\n", encoding="utf-8")
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

    with pytest.raises(RuntimeError, match="maintenance_bundle_verify_failed"):
        apply_local_state_maintenance(
            repo,
            archive_root,
            OBSERVED_AT,
            expect_inventory_digest=inventory["inventory_digest"],
            confirm_irreversible=True,
        )

    assert bundle.exists()


def test_apply_verifies_extracted_valid_git_bundle_against_repository(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    snapshots = repo / ".ethos" / "state" / "residue-snapshots"
    snapshots.mkdir(parents=True)
    bundle = snapshots / "recovery.bundle"
    git(repo, "bundle", "create", bundle.as_posix(), "--all")
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

    applied = apply_local_state_maintenance(
        repo,
        archive_root,
        OBSERVED_AT,
        expect_inventory_digest=inventory["inventory_digest"],
        confirm_irreversible=True,
    )

    assert applied["archive"]["bundle_verifications"] == [
        {"path": "recovery.bundle", "verified": True}
    ]
    assert applied["archive"]["extraction"]["bundle_verifications"] == [
        {"path": "recovery.bundle", "verified": True}
    ]


def test_apply_keeps_sources_when_archive_extraction_verification_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    snapshots = repo / ".ethos" / "state" / "residue-snapshots"
    snapshots.mkdir(parents=True)
    source = snapshots / "dirty.patch"
    source.write_text("patch\n", encoding="utf-8")
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

    def fail_extraction(*_args: object, **_kwargs: object) -> dict[str, object]:
        message = "maintenance_archive_extraction_failed"
        raise RuntimeError(message)

    monkeypatch.setattr(maintenance, "_verify_archive_extraction", fail_extraction)

    with pytest.raises(RuntimeError, match="maintenance_archive_extraction_failed"):
        apply_local_state_maintenance(
            repo,
            archive_root,
            OBSERVED_AT,
            expect_inventory_digest=inventory["inventory_digest"],
            confirm_irreversible=True,
        )

    assert source.exists()


def test_apply_restores_sources_when_receipt_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / "archive"
    snapshots = repo / ".ethos" / "state" / "residue-snapshots"
    snapshots.mkdir(parents=True)
    source = snapshots / "dirty.patch"
    source.write_text("patch\n", encoding="utf-8")
    _insert_lease(
        repo,
        lease_id="lease:orphan",
        subject="work/orphan",
        expires_at="2026-07-18T00:00:00+00:00",
        payload=_normalized_payload(path=(tmp_path / "gone").as_posix()),
    )
    proof = _write_proof(repo, "e" * 40)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    original_write = maintenance._write_json_atomic

    def fail_receipt(path: Path, payload: dict[str, object]) -> None:
        if path.name.endswith(".receipt.json"):
            raise OSError("receipt write failed")
        original_write(path, payload)

    monkeypatch.setattr(maintenance, "_write_json_atomic", fail_receipt)

    with pytest.raises(OSError, match="receipt write failed"):
        apply_local_state_maintenance(
            repo,
            archive_root,
            OBSERVED_AT,
            expect_inventory_digest=inventory["inventory_digest"],
            confirm_irreversible=True,
        )

    assert source.exists()
    assert proof.exists()
    restored = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert [item["id"] for item in restored["leases"]["delete_candidates"]] == ["lease:orphan"]


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
