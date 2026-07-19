"""Digest-bound maintenance for ignored SQLite, proof, and recovery state."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from contextlib import closing
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from ethos.adapters.mutation.proof import apply_proof_retention
from ethos.adapters.mutation.proof import proof_retention_inventory
from ethos.adapters.mutation.proof import proof_state_dir
from ethos.adapters.store.state.lease.lifecycle.effects import delete_exact_leases
from ethos.adapters.store.state.lease.projection import lease_inventory_rows
from ethos.adapters.store.state.schema import SCHEMA_VERSION
from ethos.adapters.store.state.schema import initialize_state


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
    leases, live_lease_heads = _lease_inventory(
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
        "database": _database_inventory(repo / ".ethos" / "state" / "state.sqlite"),
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
        raise ValueError("maintenance_irreversible_confirmation_required")
    repo, external_archive = _validated_roots(root, archive_root)
    observed = _normalized_observed_at(observed_at)
    existing = _verified_existing_receipt(external_archive, expect_inventory_digest, repo)
    if existing is not None:
        return {**existing, "state": "already_applied"}
    inventory = local_state_maintenance_inventory(repo, external_archive, observed)
    if inventory["inventory_digest"] != expect_inventory_digest:
        raise ValueError("maintenance_inventory_digest_mismatch")
    external_archive.mkdir(parents=True, exist_ok=True)
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
        extraction = _verify_archive_extraction(archive, manifest, repository_root=repo)
        deleted: dict[str, Any] = {
            "lease_ids": [],
            "proof_paths": [],
            "recovery_snapshot": False,
        }
        try:
            db_path = repo / ".ethos" / "state" / "state.sqlite"
            if db_path.exists():
                initialize_state(db_path)
            deleted["lease_ids"] = delete_exact_leases(
                db_path,
                inventory["leases"]["delete_candidates"],
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
            _write_json_atomic(_receipt_path(external_archive, expect_inventory_digest), receipt)
        except Exception:
            _restore_staged_state(repo, staging, inventory)
            raise
        return receipt


def _validated_roots(root: Path, archive_root: Path) -> tuple[Path, Path]:
    if not archive_root.is_absolute():
        raise ValueError("maintenance_archive_root_must_be_absolute")
    repo = root.resolve()
    archive = archive_root.resolve()
    if archive == repo or archive.is_relative_to(repo):
        raise ValueError("maintenance_archive_root_must_be_external")
    return repo, archive


def _normalized_observed_at(value: datetime | str) -> datetime:
    try:
        observed = datetime.fromisoformat(value) if isinstance(value, str) else value
    except ValueError as exc:
        raise ValueError("maintenance_observed_at_invalid") from exc
    if observed.tzinfo is None:
        raise ValueError("maintenance_observed_at_timezone_required")
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
        raise RuntimeError(f"maintenance_git_observation_failed:{args[0]}")
    return [line for line in completed.stdout.splitlines() if line]


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


def _database_inventory(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "path": db_path.as_posix(),
            "exists": False,
            "digest": "",
            "schema_versions": [],
            "target_schema_version": SCHEMA_VERSION,
            "cache_entries": {"exists": False, "row_count": 0},
        }
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "select name from sqlite_master where type = 'table'"
                ).fetchall()
            }
            versions = (
                [
                    int(row[0])
                    for row in connection.execute(
                        "select version from schema_migrations order by version"
                    ).fetchall()
                ]
                if "schema_migrations" in tables
                else []
            )
            cache_count = (
                int(connection.execute("select count(*) from cache_entries").fetchone()[0])
                if "cache_entries" in tables
                else 0
            )
            digest = hashlib.sha256(connection.serialize()).hexdigest()
    except sqlite3.Error as exc:
        return {
            "path": db_path.as_posix(),
            "exists": True,
            "digest": "",
            "schema_versions": [],
            "target_schema_version": SCHEMA_VERSION,
            "cache_entries": {"exists": False, "row_count": 0},
            "error": exc.__class__.__name__,
        }
    return {
        "path": db_path.as_posix(),
        "exists": True,
        "digest": digest,
        "schema_versions": versions,
        "target_schema_version": SCHEMA_VERSION,
        "cache_entries": {
            "exists": "cache_entries" in tables,
            "row_count": cache_count,
        },
    }


def _lease_inventory(
    root: Path,
    *,
    observed: datetime,
    branch_refs: set[str],
    worktree_branches: set[str],
) -> tuple[dict[str, Any], set[str]]:
    db_path = root / ".ethos" / "state" / "state.sqlite"
    candidates: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    live_heads: set[str] = set()
    try:
        rows = lease_inventory_rows(db_path)
    except sqlite3.Error as exc:
        return {
            "delete_candidates": [],
            "retained": [],
            "error": exc.__class__.__name__,
        }, live_heads
    for row in rows:
        reasons, expires = _lease_retention_reasons(
            root,
            row,
            observed=observed,
            branch_refs=branch_refs,
            worktree_branches=worktree_branches,
        )
        payload = row["payload"]
        expected_head = str(payload.get("expected_head") or "")
        if expires is not None and expires > observed and expected_head:
            live_heads.add(expected_head)
        item = {
            "id": row["id"],
            "subject": row["subject"],
            "owner": row["owner"],
            "expires_at": row["expires_at"],
            "payload_sha256": hashlib.sha256(row["payload_json"].encode("utf-8")).hexdigest(),
        }
        if reasons:
            retained.append({**item, "reasons": reasons})
        else:
            candidates.append(item)
    return {"delete_candidates": candidates, "retained": retained}, live_heads


def _lease_retention_reasons(
    root: Path,
    row: dict[str, Any],
    *,
    observed: datetime,
    branch_refs: set[str],
    worktree_branches: set[str],
) -> tuple[list[str], datetime | None]:
    reasons, expires = _lease_time_reasons(row, observed)
    payload = row["payload"]
    if not row["payload_valid"]:
        reasons.append("malformed_payload")
    if row["payload_valid"] and _lease_contract_ambiguous(row):
        reasons.append("ambiguous_lease")
    subject = str(row["subject"])
    if not _valid_branch_subject(root, subject):
        reasons.append("malformed_subject")
    if subject in branch_refs:
        reasons.append("branch_ref_present")
    if subject in worktree_branches:
        reasons.append("linked_worktree_present")
    recorded_path = payload.get("path") if row["payload_valid"] else None
    if recorded_path is not None and not isinstance(recorded_path, str):
        reasons.append("malformed_recorded_path")
    elif isinstance(recorded_path, str) and recorded_path:
        path = Path(recorded_path)
        path = path if path.is_absolute() else root / path
        if os.path.lexists(path):
            reasons.append("recorded_path_present")
    return sorted(set(reasons)), expires


def _lease_contract_ambiguous(row: dict[str, Any]) -> bool:
    payload = row["payload"]
    epoch = payload.get("epoch")
    return (
        payload.get("normalization_state") != "normalized"
        or payload.get("lease_id") != row["id"]
        or payload.get("lane_ref") != row["subject"]
        or payload.get("holder_ref") != row["owner"]
        or not str(payload.get("lane_incarnation_id") or "")
        or isinstance(epoch, bool)
        or not isinstance(epoch, int)
        or epoch < 1
    )


def _valid_branch_subject(root: Path, subject: str) -> bool:
    if not subject:
        return False
    completed = subprocess.run(
        ["git", "check-ref-format", f"refs/heads/{subject}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _lease_time_reasons(
    row: dict[str, Any], observed: datetime
) -> tuple[list[str], datetime | None]:
    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except (TypeError, ValueError):
        return ["malformed_expiry"], None
    if expires.tzinfo is None:
        return ["malformed_expiry"], None
    normalized = expires.astimezone(UTC)
    return (["unexpired"] if normalized > observed else []), normalized


def _recovery_inventory(root: Path) -> dict[str, Any]:
    source = root / ".ethos" / "state" / "residue-snapshots"
    return {
        "path": source.as_posix(),
        "source_exists": source.is_dir(),
        "entries": _tree_entries(source) if source.is_dir() else [],
    }


def _tree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not root.exists():
        return entries
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"maintenance_archive_symlink_unsupported:{relative}")
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
            raise ValueError(f"maintenance_archive_entry_unsupported:{relative}")
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


def _verify_archive_extraction(
    archive: Path,
    manifest: dict[str, Any],
    *,
    repository_root: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ethos-archive-verify-") as temp:
        destination = Path(temp)
        try:
            with tarfile.open(archive, "r") as payload:
                payload.extractall(destination, filter="data")
        except (OSError, tarfile.TarError) as exc:
            raise RuntimeError("maintenance_archive_extraction_failed") from exc
        extracted = destination / "local-state"
        if _tree_entries(extracted) != manifest["entries"]:
            raise RuntimeError("maintenance_archive_entry_verification_failed")
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
            raise RuntimeError(f"maintenance_bundle_verify_failed:{relative}")
        verified.append({"path": relative, "verified": True})
    return verified


def _delete_recovery_snapshot(root: Path, recovery: dict[str, Any]) -> bool:
    source = root / ".ethos" / "state" / "residue-snapshots"
    if not recovery["source_exists"]:
        return False
    if not source.is_dir() or _tree_entries(source) != recovery["entries"]:
        raise ValueError("maintenance_recovery_snapshot_drift")
    shutil.rmtree(source)
    return True


def _restore_staged_state(root: Path, staging: Path, inventory: dict[str, Any]) -> None:
    state_source = staging / ".ethos" / "state"
    db_backup = state_source / "state.sqlite"
    db_path = root / ".ethos" / "state" / "state.sqlite"
    if db_backup.exists():
        for suffix in ("-wal", "-shm"):
            Path(f"{db_path}{suffix}").unlink(missing_ok=True)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_backup, db_path)
    proof_backup = state_source / "proof"
    proof_target = proof_state_dir(root)
    for candidate in inventory["proofs"]["delete_candidates"]:
        source = proof_backup / f"{candidate['head']}.json"
        if source.is_file():
            proof_target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, proof_target / source.name)
    recovery_backup = state_source / "residue-snapshots"
    recovery_target = root / ".ethos" / "state" / "residue-snapshots"
    if inventory["recovery"]["source_exists"] and not recovery_target.exists():
        shutil.copytree(recovery_backup, recovery_target)


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
        raise ValueError("maintenance_existing_receipt_invalid") from exc
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
        raise ValueError("maintenance_existing_receipt_invalid")
    _verify_archive_extraction(archive, manifest, repository_root=repository_root)
    return receipt


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
