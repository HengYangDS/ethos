"""Digest-bound maintenance for ignored SQLite, proof, and recovery state."""

from __future__ import annotations

import fcntl
import hashlib
import json
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from contextlib import closing
from contextlib import contextmanager
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from ethos.adapters.mutation.proof import apply_proof_retention
from ethos.adapters.mutation.proof import proof_retention_inventory
from ethos.adapters.mutation.proof import proof_state_dir
from ethos.adapters.store.state.lease.lifecycle.effects import delete_exact_leases_from_connection
from ethos.adapters.store.state.lease.projection import lease_inventory_rows
from ethos.adapters.store.state.lease.projection import lease_maintenance_inventory
from ethos.adapters.store.state.lease.projection import live_lease_expected_heads
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import state_database_inventory


def local_state_maintenance_inventory(
    root: Path,
    archive_root: Path,
    observed_at: datetime | str,
) -> dict[str, Any]:
    """Return a read-only, deterministic inventory of conservative maintenance."""
    repo, external_archive = _validated_roots(root, archive_root)
    observed = _normalized_observed_at(observed_at)
    current_head = _git_lines(repo, "rev-parse", "HEAD")[0]
    refs = set(_git_lines(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads"))
    worktrees = _git_worktrees(repo)
    leases, live_lease_heads = lease_maintenance_inventory(
        repo,
        observed=observed,
        branch_refs=refs,
        worktree_branches={item["branch"] for item in worktrees if item["branch"]},
    )
    reachable_heads = set(_git_lines(repo, "rev-list", "--all"))
    worktree_heads = _git_worktree_heads(repo)
    proofs = proof_retention_inventory(
        repo,
        reachable_heads=reachable_heads,
        protected_heads={current_head, *worktree_heads, *live_lease_heads},
    )
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "ethos_local_state_maintenance_inventory",
        "root": repo.as_posix(),
        "archive_root": external_archive.as_posix(),
        "observed_at": observed.isoformat(),
        "head": current_head,
        "database": state_database_inventory(repo / ".ethos" / "state" / "state.sqlite"),
        "leases": leases,
        "proofs": proofs,
        "recovery": _recovery_inventory(repo),
    }
    payload["inventory_digest"] = _payload_digest(payload)
    return payload


def apply_local_state_maintenance(
    root: Path,
    archive_root: Path,
    observed_at: datetime | str,
    *,
    expect_inventory_digest: str,
    confirm_irreversible: bool,
) -> dict[str, Any]:
    """Archive, verify, then apply one exact local-state inventory through CAS."""
    if not confirm_irreversible:
        msg = "maintenance_irreversible_confirmation_required"
        raise ValueError(msg)
    repo, external_archive = _validated_roots(root, archive_root)
    observed = _normalized_observed_at(observed_at)
    external_archive.mkdir(parents=True, exist_ok=True)
    with _maintenance_lock(repo):
        return _apply_local_state_maintenance_locked(
            repo,
            external_archive,
            observed,
            expect_inventory_digest=expect_inventory_digest,
        )


def _apply_local_state_maintenance_locked(
    repo: Path,
    external_archive: Path,
    observed: datetime,
    *,
    expect_inventory_digest: str,
) -> dict[str, Any]:
    existing = _verified_existing_receipt(external_archive, expect_inventory_digest, repo)
    if existing is not None:
        _verify_receipt_postconditions(repo, existing)
        return {**existing, "state": "already_applied"}
    inventory = local_state_maintenance_inventory(repo, external_archive, observed)
    if inventory["inventory_digest"] != expect_inventory_digest:
        msg = "maintenance_inventory_digest_mismatch"
        raise ValueError(msg)
    with tempfile.TemporaryDirectory(prefix=".ethos-maintenance-", dir=external_archive) as temp:
        staging = Path(temp) / "local-state"
        _stage_local_state(repo, staging)
        manifest = _archive_manifest(inventory, staging)
        bundle_verifications = _verify_bundles(
            staging / ".ethos" / "state" / "residue-snapshots",
            cwd=repo,
        )
        archive = _create_archive(external_archive, expect_inventory_digest, staging)
        archive_digest = _file_sha256(archive)
        archive_size = archive.stat().st_size
        manifest["archive"] = {
            "path": archive.as_posix(),
            "sha256": archive_digest,
            "size": archive_size,
        }
        manifest["bundle_verifications"] = bundle_verifications
        manifest_path = _manifest_path(external_archive, expect_inventory_digest)
        _write_json_atomic(manifest_path, manifest)
        extraction = verify_archive_extraction(archive, manifest, repository_root=repo)
        deleted: dict[str, Any] = {
            "lease_ids": [],
            "proof_paths": [],
            "recovery_snapshot": False,
        }
        db_path = repo / ".ethos" / "state" / "state.sqlite"
        connection = sqlite3.connect(db_path) if db_path.exists() else None
        receipt_path = _receipt_path(external_archive, expect_inventory_digest)
        try:
            if connection is not None:
                connection.execute("pragma foreign_keys = on")
                connection.execute("begin immediate")
                initialize_state_connection(connection)
            deleted["lease_ids"] = _delete_inventory_leases(
                connection,
                inventory["leases"]["delete_candidates"],
            )
            _assert_proof_candidates_still_unprotected(
                repo,
                inventory["proofs"]["delete_candidates"],
                observed=observed,
                connection=connection,
            )
            deleted["proof_paths"] = apply_proof_retention(
                repo,
                inventory["proofs"]["delete_candidates"],
            )
            deleted["recovery_snapshot"] = _delete_recovery_snapshot(repo, inventory["recovery"])
            archive_payload = {
                "path": archive.as_posix(),
                "sha256": archive_digest,
                "size": archive_size,
                "manifest_path": manifest_path.as_posix(),
                "entry_manifest_digest": _payload_digest(manifest),
                "entry_count": len(manifest["entries"]),
                "bundle_verifications": bundle_verifications,
                "extraction": extraction,
            }
            receipt = {
                "schema_version": 1,
                "kind": "ethos_local_state_maintenance_receipt",
                "ok": True,
                "state": "applied",
                "inventory_digest": expect_inventory_digest,
                "root": repo.as_posix(),
                "head": inventory["head"],
                "observed_at": inventory["observed_at"],
                "archive": archive_payload,
                "deleted": deleted,
            }
            _write_json_atomic(receipt_path, receipt)
            if connection is not None:
                connection.commit()
        except Exception:
            if connection is not None:
                connection.rollback()
            receipt_path.unlink(missing_ok=True)
            _restore_staged_state(repo, staging, inventory)
            raise
        finally:
            if connection is not None:
                connection.close()
        return receipt


@contextmanager
def _maintenance_lock(root: Path) -> Any:
    lock_path = root / ".ethos" / "state" / "local-state-maintenance.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _validated_roots(root: Path, archive_root: Path) -> tuple[Path, Path]:
    if not archive_root.is_absolute():
        msg = "maintenance_archive_root_must_be_absolute"
        raise ValueError(msg)
    repo = root.resolve()
    archive = archive_root.resolve()
    if archive == repo or archive.is_relative_to(repo):
        msg = "maintenance_archive_root_must_be_external"
        raise ValueError(msg)
    return repo, archive


def _normalized_observed_at(value: datetime | str) -> datetime:
    try:
        observed = datetime.fromisoformat(value) if isinstance(value, str) else value
    except ValueError as exc:
        msg = "maintenance_observed_at_invalid"
        raise ValueError(msg) from exc
    if observed.tzinfo is None:
        msg = "maintenance_observed_at_timezone_required"
        raise ValueError(msg)
    return observed.astimezone(UTC)


def _git_lines(root: Path, *args: str) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        msg = f"maintenance_git_observation_failed:{args[0]}"
        raise RuntimeError(msg)
    return completed.stdout.splitlines()


def _git_worktrees(root: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in [*_git_lines(root, "worktree", "list", "--porcelain"), ""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "branch" and value.startswith("refs/heads/"):
            value = value.removeprefix("refs/heads/")
        if key in {"worktree", "HEAD", "branch"}:
            current[key.lower()] = value
    return records


def _git_worktree_heads(root: Path) -> set[str]:
    return {item["head"] for item in _git_worktrees(root) if item.get("head")}


def _recovery_inventory(root: Path) -> dict[str, Any]:
    source = root / ".ethos" / "state" / "residue-snapshots"
    return {
        "path": source.as_posix(),
        "source_exists": source.is_dir(),
        "entries": _tree_entries(source) if source.is_dir() else [],
    }


def _tree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            msg = f"maintenance_archive_symlink_unsupported:{relative}"
            raise ValueError(msg)
        if path.is_dir():
            entries.append({"path": relative, "kind": "directory"})
        elif path.is_file():
            entries.append(
                {
                    "path": relative,
                    "kind": "file",
                    "size": path.stat().st_size,
                    "sha256": _file_sha256(path),
                }
            )
        else:
            msg = f"maintenance_archive_entry_unsupported:{relative}"
            raise ValueError(msg)
    return entries


def _stage_local_state(root: Path, staging: Path) -> None:
    state_target = staging / ".ethos" / "state"
    state_target.mkdir(parents=True, exist_ok=True)
    source_db = root / ".ethos" / "state" / "state.sqlite"
    if source_db.exists():
        with (
            closing(sqlite3.connect(source_db)) as source,
            closing(sqlite3.connect(state_target / "state.sqlite")) as target,
        ):
            source.backup(target)
    source_proof = proof_state_dir(root)
    if source_proof.is_dir():
        shutil.copytree(source_proof, state_target / "proof")
    source_recovery = root / ".ethos" / "state" / "residue-snapshots"
    if source_recovery.is_dir():
        shutil.copytree(source_recovery, state_target / "residue-snapshots")


def _assert_proof_candidates_still_unprotected(
    root: Path,
    candidates: list[dict[str, Any]],
    *,
    observed: datetime,
    connection: sqlite3.Connection | None,
) -> None:
    if not candidates:
        return
    current_head = _git_lines(root, "rev-parse", "HEAD")[0]
    reachable_heads = set(_git_lines(root, "rev-list", "--all"))
    worktree_heads = _git_worktree_heads(root)
    live_lease_heads = live_lease_expected_heads(connection, observed)
    protected = {current_head, *reachable_heads, *worktree_heads, *live_lease_heads}
    newly_protected = sorted(
        str(candidate.get("head") or "")
        for candidate in candidates
        if str(candidate.get("head") or "") in protected
    )
    if newly_protected:
        msg = f"maintenance_proof_candidate_became_protected:{newly_protected[0]}"
        raise ValueError(msg)


def _delete_inventory_leases(
    connection: sqlite3.Connection | None,
    candidates: list[dict[str, Any]],
) -> list[str]:
    if connection is None:
        if candidates:
            msg = "lease_maintenance_database_missing"
            raise ValueError(msg)
        return []
    return delete_exact_leases_from_connection(connection, candidates)


def _archive_manifest(inventory: dict[str, Any], staging: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "ethos_local_state_archive_manifest",
        "inventory_digest": inventory["inventory_digest"],
        "root": inventory["root"],
        "head": inventory["head"],
        "entries": _tree_entries(staging),
    }


def _create_archive(archive_root: Path, digest: str, staging: Path) -> Path:
    target = _archive_path(archive_root, digest)
    temporary = target.with_suffix(".tar.tmp")
    with tarfile.open(temporary, "w") as archive:
        for path in [staging, *sorted(staging.rglob("*"))]:
            arcname = Path("local-state") / path.relative_to(staging)
            info = archive.gettarinfo(path.as_posix(), arcname.as_posix())
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            if path.is_file():
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
            else:
                archive.addfile(info)
    temporary.replace(target)
    return target


def verify_archive_extraction(
    archive: Path,
    manifest: dict[str, Any],
    *,
    repository_root: Path,
) -> dict[str, Any]:
    """Extract an archive and verify its manifest entries and recovery bundles."""
    with tempfile.TemporaryDirectory(prefix="ethos-archive-verify-") as temp:
        destination = Path(temp)
        try:
            with tarfile.open(archive, "r") as payload:
                payload.extractall(destination, filter="data")
        except (OSError, tarfile.TarError) as exc:
            msg = "maintenance_archive_extraction_failed"
            raise RuntimeError(msg) from exc
        extracted = destination / "local-state"
        if _tree_entries(extracted) != manifest["entries"]:
            msg = "maintenance_archive_entry_verification_failed"
            raise RuntimeError(msg)
        bundles = _verify_bundles(
            extracted / ".ethos" / "state" / "residue-snapshots",
            cwd=repository_root,
        )
    return {"entry_count": len(manifest["entries"]), "bundle_verifications": bundles}


def _verify_bundles(root: Path, *, cwd: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    verified: list[dict[str, Any]] = []
    for bundle in sorted(root.rglob("*.bundle")):
        completed = subprocess.run(
            ["git", "bundle", "verify", bundle.as_posix()],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
        relative = bundle.relative_to(root).as_posix()
        if completed.returncode != 0:
            msg = f"maintenance_bundle_verify_failed:{relative}"
            raise RuntimeError(msg)
        verified.append({"path": relative, "verified": True})
    return verified


def _delete_recovery_snapshot(root: Path, recovery: dict[str, Any]) -> bool:
    source = root / ".ethos" / "state" / "residue-snapshots"
    if not recovery["source_exists"]:
        return False
    if not source.is_dir() or _tree_entries(source) != recovery["entries"]:
        msg = "maintenance_recovery_snapshot_drift"
        raise ValueError(msg)
    shutil.rmtree(source)
    return True


def _restore_missing_tree(source_root: Path, target_root: Path) -> None:
    for source in sorted(source_root.rglob("*")):
        target = target_root / source.relative_to(source_root)
        if target.exists() or target.is_symlink():
            continue
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as source_stream, target.open("xb") as target_stream:
            shutil.copyfileobj(source_stream, target_stream)
        shutil.copystat(source, target)


def _restore_staged_state(root: Path, staging: Path, inventory: dict[str, Any]) -> None:
    state_source = staging / ".ethos" / "state"
    proof_backup = state_source / "proof"
    proof_target = proof_state_dir(root)
    for candidate in inventory["proofs"]["delete_candidates"]:
        source = proof_backup / f"{candidate['head']}.json"
        target = proof_target / source.name
        if source.is_file() and not target.exists():
            proof_target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    recovery_backup = state_source / "residue-snapshots"
    recovery_target = root / ".ethos" / "state" / "residue-snapshots"
    if inventory["recovery"]["source_exists"]:
        _restore_missing_tree(recovery_backup, recovery_target)


def _verified_existing_receipt(
    archive_root: Path, digest: str, repository_root: Path
) -> dict[str, Any] | None:
    path = _receipt_path(archive_root, digest)
    if not path.is_file():
        return None
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        manifest_path = _manifest_path(archive_root, digest)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        msg = "maintenance_existing_receipt_invalid"
        raise ValueError(msg) from exc
    archive = _archive_path(archive_root, digest)
    expected = receipt.get("archive") if isinstance(receipt, dict) else None
    if (
        not isinstance(expected, dict)
        or receipt.get("inventory_digest") != digest
        or not archive.is_file()
        or expected.get("sha256") != _file_sha256(archive)
        or expected.get("size") != archive.stat().st_size
        or expected.get("entry_manifest_digest") != _payload_digest(manifest)
    ):
        msg = "maintenance_existing_receipt_invalid"
        raise ValueError(msg)
    verify_archive_extraction(archive, manifest, repository_root=repository_root)
    return receipt


def _verify_receipt_postconditions(root: Path, receipt: dict[str, Any]) -> None:
    deleted = receipt.get("deleted")
    if not isinstance(deleted, dict):
        msg = "maintenance_existing_receipt_invalid"
        raise ValueError(  # noqa: TRY004 - stable maintenance validation contract
            msg
        )
    gaps: list[str] = []
    deleted_lease_ids = {str(value) for value in deleted.get("lease_ids", [])}
    db_path = root / ".ethos" / "state" / "state.sqlite"
    if db_path.exists() and deleted_lease_ids:
        current_lease_ids = {row["id"] for row in lease_inventory_rows(db_path)}
        gaps.extend(
            f"lease_present:{lease_id}"
            for lease_id in sorted(deleted_lease_ids & current_lease_ids)
        )
    for value in deleted.get("proof_paths", []):
        relative = Path(str(value))
        if relative.is_absolute() or ".." in relative.parts:
            msg = "maintenance_existing_receipt_invalid"
            raise ValueError(msg)
        if (root / relative).exists():
            gaps.append(f"proof_present:{relative.as_posix()}")
    recovery = root / ".ethos" / "state" / "residue-snapshots"
    if deleted.get("recovery_snapshot") is True and recovery.exists():
        gaps.append("recovery_snapshot_present")
    if gaps:
        msg = f"maintenance_existing_receipt_postcondition_failed:{gaps[0]}"
        raise ValueError(msg)


def _archive_path(root: Path, digest: str) -> Path:
    return root / f"local-state-{digest}.tar"


def _manifest_path(root: Path, digest: str) -> Path:
    return root / f"local-state-{digest}.manifest.json"


def _receipt_path(root: Path, digest: str) -> Path:
    return root / f"local-state-{digest}.receipt.json"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _payload_digest(payload: object) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
