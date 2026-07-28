"""Destination transaction for cross-host Work Lane handoff imports."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import tempfile
import uuid
from contextlib import closing
from contextlib import contextmanager
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.lane_lifecycle.handoff.destination_cleanup import (
    compensate_failed_import,
)
from ethos.adapters.mutation.lane_lifecycle.handoff.destination_cleanup import (
    import_worktree_record,
)
from ethos.adapters.mutation.lane_lifecycle.handoff.package import lease_binding
from ethos.adapters.mutation.lane_lifecycle.handoff.package import validated_handoff_acknowledgement
from ethos.adapters.mutation.lane_lifecycle.handoff.package import verified_package_snapshot
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.git import run_git
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.lifecycle.transitions import expected_current_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.lifecycle.declaration import load_lifecycle_declaration

if TYPE_CHECKING:
    from collections.abc import Iterator


def apply_handoff_import(
    *,
    destination: Path,
    package: Path,
    manifest: dict[str, Any],
    target_holder_ref: str,
) -> dict[str, object]:
    """Apply one destination-local import with exact compensation before commit."""
    branch, head = str(manifest["source_lane_ref"]), str(manifest["source_head"])
    worktree_path = destination.with_name(f"{destination.name}-{branch.replace('/', '-')}")
    lease: dict[str, Any] = {}
    lease_identity = {
        "lane_incarnation_id": f"lane-incarnation:{uuid.uuid4()}",
        "lease_id": f"lease:{uuid.uuid4()}",
    }
    observed = observe_lease(state_database(destination), branch)
    if observed.state != "missing":
        lease = _recover_import_lease(
            destination,
            manifest,
            target_holder_ref,
            lease_identity,
        )
    with (
        verified_package_snapshot(package=package, manifest=manifest, root=destination) as snapshot,
        _verified_import_repository(snapshot, manifest, destination) as isolated,
    ):
        object_environment = _import_object_environment(destination, isolated)
        with _prepared_import_pack(destination, isolated, head) as prepared_pack:
            try:
                lease = _acquire_or_recover_lease(
                    destination,
                    manifest,
                    target_holder_ref,
                    lease_identity,
                )
                _ensure_import_ref(destination, branch, head, object_environment)
                _ensure_import_worktree(
                    destination,
                    worktree_path,
                    branch,
                    head,
                    object_environment,
                )
                acknowledgement = _validate_import(
                    destination,
                    worktree_path,
                    manifest,
                    lease,
                    object_environment=object_environment,
                )
                _install_pack(_object_directory(destination), prepared_pack)
            except (OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError, ValueError):
                lease = lease or _recover_import_lease(
                    destination,
                    manifest,
                    target_holder_ref,
                    lease_identity,
                )
                if lease:
                    compensate_failed_import(
                        destination=destination,
                        manifest=manifest,
                        worktree_path=worktree_path,
                        lease=lease,
                        object_environment=object_environment,
                        run_git=run_git,
                        verify_destination_identity=_verify_destination_identity,
                    )
                raise
    return {
        "state": "imported",
        "package_id": str(manifest["package_id"]),
        "worktree": {"branch": branch, "path": worktree_path.as_posix(), "head": head},
        "lease": lease,
        "acknowledgement": acknowledgement,
    }


def _require(gap: str, *, holds: bool) -> None:
    if not holds:
        raise ValueError(gap)


def _unbundle(destination: Path, bundle: Path, branch: str, head: str, tree: str) -> None:
    heads = run_git(destination, "bundle", "list-heads", bundle.as_posix()).stdout.splitlines()
    _require(
        "handoff_bundle_identity_mismatch",
        holds=heads == [f"{head} refs/heads/{branch}"],
    )
    run_git(destination, "bundle", "unbundle", bundle.as_posix())
    actual = tuple(
        run_git(destination, "rev-parse", f"{head}^{{{kind}}}").stdout.strip()
        for kind in ("commit", "tree")
    )
    _require("handoff_bundle_identity_mismatch", holds=actual == (head, tree))


@contextmanager
def _verified_import_repository(
    snapshot: Path, manifest: dict[str, Any], destination: Path
) -> Iterator[Path]:
    branch, head = str(manifest["source_lane_ref"]), str(manifest["source_head"])
    object_format = run_git(destination, "rev-parse", "--show-object-format").stdout.strip()
    expected_width = {"sha1": 40, "sha256": 64}.get(object_format)
    _require("handoff_object_format_unsupported", holds=expected_width is not None)
    _require("handoff_object_format_mismatch", holds=len(head) == expected_width)
    with tempfile.TemporaryDirectory(
        prefix="handoff-bare-", ignore_cleanup_errors=True
    ) as temporary:
        isolated = Path(temporary) / "repository.git"
        isolated.mkdir()
        run_git(isolated, "init", "--bare", f"--object-format={object_format}", ".")
        _unbundle(
            isolated,
            snapshot / "repository.bundle",
            branch,
            head,
            str(manifest["source_tree"]),
        )
        _verify_import_contract(isolated, manifest)
        yield isolated


def _object_directory(destination: Path) -> Path:
    common = Path(
        run_git(
            destination, "rev-parse", "--path-format=absolute", "--git-common-dir"
        ).stdout.strip()
    )
    objects = Path(
        run_git(
            destination, "rev-parse", "--path-format=absolute", "--git-path", "objects"
        ).stdout.strip()
    )
    _require(
        "handoff_destination_object_store_unsafe",
        holds=objects == common / "objects"
        and objects.is_dir()
        and not objects.is_symlink()
        and (objects / "pack").is_dir()
        and not (objects / "pack").is_symlink(),
    )
    return objects


def _import_object_environment(destination: Path, isolated: Path) -> dict[str, str]:
    object_directory = _object_directory(destination)
    alternates_file = object_directory / "info" / "alternates"
    _require(
        "handoff_destination_alternate_object_store_forbidden",
        holds=not alternates_file.is_symlink(),
    )
    configured_alternates = (
        alternates_file.read_text(encoding="utf-8").strip() if alternates_file.exists() else ""
    )
    _require(
        "handoff_destination_alternate_object_store_forbidden",
        holds=not configured_alternates,
    )
    return {
        "GIT_OBJECT_DIRECTORY": str(object_directory),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(isolated / "objects"),
    }


@contextmanager
def _prepared_import_pack(destination: Path, isolated: Path, head: str) -> Iterator[list[Path]]:
    object_directory = _object_directory(destination)
    closure = run_git(
        destination,
        "rev-list",
        "--objects",
        "--missing=print",
        head,
        check=False,
        env={"GIT_OBJECT_DIRECTORY": str(object_directory)},
    )
    _require("handoff_destination_object_store_invalid", holds=closure.returncode in {0, 128})
    if closure.returncode == 0 and not any(
        line.startswith("?") for line in closure.stdout.splitlines()
    ):
        yield []
        return
    packed = run_git(
        isolated,
        "pack-objects",
        "--stdout",
        "--revs",
        "--no-thin",
        stdin=f"{head}\n".encode(),
        text=False,
    ).stdout
    _require("handoff_import_object_pack_empty", holds=bool(packed))
    with tempfile.TemporaryDirectory(
        prefix="handoff-import-",
        dir=object_directory,
        ignore_cleanup_errors=True,
    ) as temporary:
        quarantine = Path(temporary)
        (quarantine / "pack").mkdir()
        installed = run_git(
            destination,
            "index-pack",
            "--stdin",
            "--strict",
            env={"GIT_OBJECT_DIRECTORY": str(quarantine)},
            stdin=packed,
            text=False,
        )
        pack_id = installed.stdout.decode().strip().removeprefix("pack\t")
        candidates = sorted((quarantine / "pack").glob(f"pack-{pack_id}.*"))
        suffixes = {path.suffix for path in candidates}
        _require(
            "handoff_import_object_install_failed",
            holds=len(pack_id) == len(head)
            and all(character in "0123456789abcdef" for character in pack_id)
            and {".idx", ".pack"} <= suffixes <= {".idx", ".pack", ".rev"},
        )
        yield candidates


def _install_pack(
    object_directory: Path,
    candidates: list[Path],
) -> None:
    if not candidates:
        return
    by_suffix = {path.suffix: path for path in candidates}
    ordered = [by_suffix[".idx"], *([by_suffix[".rev"]] if ".rev" in by_suffix else [])]
    installed: list[Path] = []
    try:
        for source in ordered:
            target = object_directory / "pack" / source.name
            os.link(source, target)
            installed.append(target)
        os.link(by_suffix[".pack"], object_directory / "pack" / by_suffix[".pack"].name)
    except OSError:
        try:
            for path in reversed(installed):
                path.unlink()
        except OSError:
            gap = "handoff_import_object_cleanup_failed"
            raise ValueError(gap) from None
        raise


def _recover_import_lease(
    destination: Path,
    manifest: dict[str, Any],
    target_holder_ref: str,
    identity: dict[str, str],
) -> dict[str, Any]:
    observed = observe_lease(state_database(destination), str(manifest["source_lane_ref"]))
    if observed.state == "missing":
        return {}
    record = observed.record()
    expected = {
        **identity,
        "holder_ref": target_holder_ref,
        "expected_head": str(manifest["source_head"]),
        "base_commitment_digest": str(manifest["base_commitment_digest"]),
        "epoch": 1,
    }
    _require(
        "handoff_import_lease_conflict",
        holds=observed.state in {"valid", "expired"}
        and all(record.get(key) == value for key, value in expected.items()),
    )
    return record


def _acquire_or_recover_lease(
    destination: Path,
    manifest: dict[str, Any],
    target_holder_ref: str,
    identity: dict[str, str],
) -> dict[str, Any]:
    observed = observe_lease(state_database(destination), str(manifest["source_lane_ref"]))
    if observed.state != "missing":
        recovered = _recover_import_lease(destination, manifest, target_holder_ref, identity)
        if observed.state == "expired":
            return _resume_import_lease(destination, manifest, target_holder_ref, recovered)
        return recovered
    now = datetime.now(UTC)
    return acquire_lease(
        state_database(destination),
        lease=LaneLease(
            lane_incarnation_id=identity["lane_incarnation_id"],
            lease_id=identity["lease_id"],
            lane_ref=str(manifest["source_lane_ref"]),
            holder_ref=HolderRef.parse(target_holder_ref),
            epoch=1,
            issued_at=now,
            renewed_at=now,
            expires_at=now + timedelta(days=1),
            expected_head=str(manifest["source_head"]),
            base_commitment_digest=str(manifest["base_commitment_digest"]),
            path_scope=(),
        ),
    )


def _resume_import_lease(
    destination: Path,
    manifest: dict[str, Any],
    holder_ref: str,
    lease: dict[str, Any],
) -> dict[str, Any]:
    transition = next(
        item
        for item in load_lifecycle_declaration(destination).lease_transition
        if item.id == "resume"
    )
    return apply_lease_operation(
        state_database(destination),
        transition=transition,
        request=LeaseOperationRequest(
            operation="resume",
            branch=str(manifest["source_lane_ref"]),
            holder_ref=holder_ref,
            lease_id=str(lease["lease_id"]),
            expected_epoch=int(lease["epoch"]),
            expect_head=str(manifest["source_head"]),
            expected_expires_at=str(lease["expires_at"]),
            expected_payload_sha256=str(lease["payload_sha256"]),
            apply=True,
            ttl_seconds=86_400,
        ),
    )


def _ensure_import_ref(
    destination: Path,
    branch: str,
    head: str,
    object_environment: dict[str, str],
) -> None:
    ref = f"refs/heads/{branch}"
    observed = run_git(
        destination, "rev-parse", "--verify", ref, check=False, env=object_environment
    )
    _require("handoff_destination_ref_conflict", holds=observed.returncode in {0, 128})
    if observed.returncode == 0:
        _require("handoff_destination_ref_conflict", holds=observed.stdout.strip() == head)
        return
    run_git(
        destination,
        "update-ref",
        "--stdin",
        env=object_environment,
        stdin=f"create {ref} {head}\n",
    )


def _ensure_import_worktree(
    destination: Path,
    path: Path,
    branch: str,
    head: str,
    object_environment: dict[str, str],
) -> None:
    record = import_worktree_record(destination, path, run_git=run_git)
    if record:
        _require(
            "handoff_destination_worktree_conflict",
            holds=not path.is_symlink()
            and path.is_dir()
            and record.get("branch") == branch
            and record.get("HEAD") == head
            and not any(flag in record for flag in ("locked", "prunable")),
        )
        return
    _require("handoff_destination_path_exists", holds=not os.path.lexists(path))
    run_git(destination, "worktree", "add", path.as_posix(), branch, env=object_environment)


def _verify_destination_identity(
    destination: Path,
    worktree: Path,
    manifest: dict[str, Any],
    lease: dict[str, Any],
    *,
    object_environment: dict[str, str],
) -> None:
    head, tree = str(manifest["source_head"]), str(manifest["source_tree"])
    actual = (
        run_git(
            destination,
            "rev-parse",
            f"refs/heads/{manifest['source_lane_ref']}",
            env=object_environment,
        ).stdout.strip(),
        run_git(worktree, "rev-parse", "HEAD", env=object_environment).stdout.strip(),
        run_git(worktree, "rev-parse", "HEAD^{tree}", env=object_environment).stdout.strip(),
        str(lease.get("expected_head") or head),
    )
    _require("handoff_destination_identity_drift", holds=actual == (head, head, tree, head))


def _verify_import_contract(destination: Path, manifest: dict[str, Any]) -> None:
    head = str(manifest["source_head"])
    expected_digest = str(manifest["base_commitment_digest"])
    try:
        load_commitment(
            destination,
            tree_ref=head,
            expected_digest=expected_digest,
        )
    except ValueError as error:
        if str(error) == "commitment_digest_mismatch":
            gap = "handoff_base_commitment_digest_mismatch"
            raise ValueError(gap) from None
        gap = "handoff_base_commitment_invalid"
        raise ValueError(gap) from None


def _validate_import(
    destination: Path,
    worktree: Path,
    manifest: dict[str, Any],
    lease: dict[str, Any],
    *,
    object_environment: dict[str, str],
) -> dict[str, object]:
    with closing(sqlite3.connect(state_database(destination))) as connection:
        connection.execute("begin immediate")
        expected_current_lease(
            connection,
            request=lease_binding(str(manifest["source_lane_ref"]), lease),
            require_expired=False,
        )
        _verify_destination_identity(
            destination,
            worktree,
            manifest,
            lease,
            object_environment=object_environment,
        )
        return validated_handoff_acknowledgement(
            root=destination,
            manifest=manifest,
            lease=lease,
        )
