"""Content-addressed package effects for cross-host Work Lane handoff."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import tempfile
from contextlib import closing
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.store.retrieval.common import sha256_bytes
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.core import expected_current_lease
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.projection import lease_record
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import state_database
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.normalization.core import string_sequence

if TYPE_CHECKING:
    from ethos_core.contracts.coordination import CrossHostHandoff


def _error(**gap: None) -> ValueError:
    return ValueError(next(iter(gap)))


def write_handoff_package(
    *,
    repo: Path,
    handoff: CrossHostHandoff,
    context: str,
    output_root: Path | None,
) -> dict[str, object]:
    base = (output_root or repo / "build" / "artifacts" / "handoff").resolve()
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="handoff-", dir=base) as temporary:
        staging = Path(temporary)
        bundle = staging / "repository.bundle"
        bundle_repo = staging / "bundle.git"
        _run(staging, "git", "init", "--bare", bundle_repo.as_posix())
        _run(
            bundle_repo,
            "git",
            "fetch",
            "--no-tags",
            repo.as_posix(),
            f"{handoff.source_head}:refs/heads/source",
        )
        _run(bundle_repo, "git", "bundle", "create", bundle.as_posix(), "refs/heads/source")
        shutil.rmtree(bundle_repo)
        context_path = staging / "context.md"
        context_path.write_text(context, encoding="utf-8")
        artifacts = [
            _artifact(bundle, staging, "git_bundle"),
            _artifact(context_path, staging, "context"),
        ]
        if handoff.dirty_disposition == "preserved":
            artifacts.extend(_preserve_dirty_work(repo=repo, package_dir=staging))
        body = {
            "schema_version": 1,
            **handoff.model_copy(update={"artifacts": tuple(artifacts)}).to_payload(),
        }
        package_id = _content_id("handoff", body)
        package_dir = base / package_id
        manifest = {"package_id": package_id, **body}
        validation = validate_schema_instance("handoff-package.schema.json", manifest, root=repo)
        if not validation["ok"]:
            raise ValueError(
                "handoff_manifest_invalid:"
                + ",".join(string_sequence(validation.get("required_gaps")))
            )
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        _verify_export_snapshot(repo=repo, handoff=handoff)
        _publish_package(staging=staging, package_dir=package_dir, manifest=manifest, root=repo)
    return {
        "state": "exported",
        "package_id": package_id,
        "package_path": package_dir.as_posix(),
        "manifest": manifest,
    }


def verified_handoff_manifest(*, package: Path, root: Path) -> tuple[dict[str, Any], list[str]]:
    package_dir = package.resolve()
    manifest_path = package_dir / "manifest.json"
    if package.is_symlink() or not manifest_path.is_file():
        return {}, [
            "handoff_package_unsafe" if package.is_symlink() else "handoff_manifest_missing"
        ]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, ["handoff_manifest_invalid_json"]
    if not isinstance(manifest, dict):
        return {}, ["handoff_manifest_invalid"]
    validation = validate_schema_instance("handoff-package.schema.json", manifest, root=root)
    gaps = [
        f"handoff_manifest_invalid:{gap}"
        for gap in string_sequence(validation.get("required_gaps"))
    ]
    artifact_gaps, expected_paths = _artifact_gaps(package_dir, manifest.get("artifacts", []))
    gaps.extend(artifact_gaps)
    actual_paths = {
        path.relative_to(package_dir).as_posix()
        for path in package_dir.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if actual_paths != expected_paths:
        gaps.append("handoff_artifact_inventory_mismatch")
    if not gaps and (
        str(manifest.get("package_id") or "")
        != _content_id(
            "handoff",
            {key: value for key, value in manifest.items() if key != "package_id"},
        )
        or package_dir.name != str(manifest.get("package_id") or "")
    ):
        gaps.append("handoff_package_id_mismatch")
    return cast("dict[str, Any]", manifest), list(dict.fromkeys(gaps))


def _artifact_gaps(package_dir: Path, artifacts: object) -> tuple[list[str], set[str]]:
    gaps: list[str] = []
    expected_paths = {"manifest.json"}
    paths: set[str] = set()
    kinds: set[str] = set()
    for artifact in artifacts if isinstance(artifacts, list) else ():
        if not isinstance(artifact, dict):
            gaps.append("handoff_artifact_invalid")
            continue
        relative = str(artifact.get("path") or "")
        kind = str(artifact.get("kind") or "")
        if relative in paths:
            gaps.append(f"handoff_artifact_path_duplicate:{relative}")
        if kind in kinds:
            gaps.append(f"handoff_artifact_kind_duplicate:{kind}")
        paths.add(relative)
        kinds.add(kind)
        expected_paths.add(relative)
        path = package_dir / relative
        if path.is_symlink() or not path.is_file():
            gaps.append(f"handoff_artifact_missing:{path.name}")
        elif sha256_bytes(path.read_bytes()) != str(artifact.get("sha256") or ""):
            gaps.append(f"handoff_artifact_digest_mismatch:{path.name}")
    gaps.extend(
        f"handoff_artifact_kind_missing:{kind}"
        for kind in ("git_bundle", "context")
        if kind not in kinds
    )
    return gaps, expected_paths


def verified_handoff_acknowledgement(
    *, acknowledgement: Path, root: Path
) -> tuple[dict[str, Any], list[str]]:
    """Validate one content-addressed destination assertion without minting authority."""
    try:
        payload = json.loads(acknowledgement.resolve().read_text(encoding="utf-8"))
    except OSError:
        return {}, ["handoff_acknowledgement_unreadable"]
    except json.JSONDecodeError:
        return {}, ["handoff_acknowledgement_invalid_json"]
    if not isinstance(payload, dict):
        return {}, ["handoff_acknowledgement_invalid"]
    validation = validate_schema_instance("handoff-acknowledgement.schema.json", payload, root=root)
    gaps = [
        f"handoff_acknowledgement_invalid:{gap}"
        for gap in string_sequence(validation.get("required_gaps"))
    ]
    if not gaps and payload.get("acknowledgement_id") != _content_id(
        "handoff-ack",
        {key: value for key, value in payload.items() if key != "acknowledgement_id"},
    ):
        gaps.append("handoff_acknowledgement_id_mismatch")
    return cast("dict[str, Any]", payload), gaps


def apply_handoff_import(
    *,
    destination: Path,
    package: Path,
    manifest: dict[str, Any],
    target_holder_ref: str,
) -> dict[str, object]:
    branch = str(manifest["source_lane_ref"])
    head = str(manifest["source_head"])
    worktree_path = destination.with_name(f"{destination.name}-{branch.replace('/', '-')}")
    if os.path.lexists(worktree_path):
        raise _error(handoff_destination_path_exists=None)
    ref_created = worktree_created = False
    lease: dict[str, Any] = {}
    try:
        with _verified_package_snapshot(
            package=package, manifest=manifest, root=destination
        ) as snapshot:
            _unbundle(
                destination,
                snapshot / "repository.bundle",
                head,
                str(manifest["source_tree"]),
            )
            _run(
                destination,
                "git",
                "update-ref",
                f"refs/heads/{branch}",
                head,
                "0" * len(head),
            )
            ref_created = True
            _run(destination, "git", "worktree", "add", worktree_path.as_posix(), branch)
            worktree_created = True
            lease = acquire_lease(
                state_database(destination),
                subject=branch,
                holder_ref=target_holder_ref,
                payload={
                    "path": worktree_path.as_posix(),
                    "expected_head": head,
                    "handoff_package_id": str(manifest["package_id"]),
                },
            )
            _restore_preserved_work(package=snapshot, manifest=manifest, worktree=worktree_path)
            lease, acknowledgement = _commit_import(destination, worktree_path, manifest, lease)
    except (OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError, ValueError):
        _compensate_failed_import(
            destination=destination,
            manifest=manifest,
            worktree_path=worktree_path,
            created=(ref_created, worktree_created),
            lease=lease,
        )
        raise
    return {
        "state": "imported",
        "package_id": str(manifest["package_id"]),
        "worktree": {"branch": branch, "path": worktree_path.as_posix(), "head": head},
        "lease": lease,
        "acknowledgement": acknowledgement,
    }


def _unbundle(destination: Path, bundle: Path, head: str, tree: str) -> None:
    heads = run_git(destination, "bundle", "list-heads", bundle.as_posix()).stdout.splitlines()
    if heads != [f"{head} refs/heads/source"]:
        raise _error(handoff_bundle_identity_mismatch=None)
    _run(destination, "git", "bundle", "unbundle", bundle.as_posix())
    actual = tuple(
        run_git(destination, "rev-parse", f"{head}^{{{kind}}}").stdout.strip()
        for kind in ("commit", "tree")
    )
    if actual != (head, tree):
        raise _error(handoff_bundle_identity_mismatch=None)


def _verify_destination_identity(
    destination: Path,
    worktree: Path,
    manifest: dict[str, Any],
    lease: dict[str, Any] | None = None,
) -> None:
    head, tree = str(manifest["source_head"]), str(manifest["source_tree"])
    actual = (
        run_git(
            destination, "rev-parse", f"refs/heads/{manifest['source_lane_ref']}"
        ).stdout.strip(),
        run_git(worktree, "rev-parse", "HEAD").stdout.strip(),
        run_git(worktree, "rev-parse", "HEAD^{tree}").stdout.strip(),
        str((lease or {}).get("expected_head") or head),
    )
    if actual != (head, head, tree, head):
        raise _error(handoff_destination_identity_drift=None)


def _verify_export_snapshot(
    *,
    repo: Path,
    handoff: CrossHostHandoff,
) -> None:
    if run_git(repo, "rev-parse", handoff.source_lane_ref).stdout.strip() != handoff.source_head:
        raise _error(handoff_export_head_drift=None)
    if dirty_content_sha256(repo) != handoff.dirty_content_sha256:
        raise _error(handoff_export_dirty_drift=None)
    with closing(sqlite3.connect(state_database(repo))) as connection:
        connection.execute("begin immediate")
        try:
            expected_current_lease(
                connection,
                subject=handoff.source_lane_ref,
                holder_ref=handoff.source_holder_ref.serialize(),
                expected_lease_id=handoff.source_lease_id,
                expected_epoch=handoff.source_lease_epoch,
                expected_head=handoff.source_head,
                expected_expires_at=handoff.source_lease_expires_at,
                expected_payload_sha256=handoff.source_lease_payload_sha256,
                require_expired=False,
            )
        except ValueError as exc:
            raise _error(handoff_export_lease_drift=None) from exc


def _commit_import(
    destination: Path,
    worktree: Path,
    manifest: dict[str, Any],
    lease: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, object]]:
    with closing(sqlite3.connect(state_database(destination))) as connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        row, _ = expected_current_lease(
            connection,
            subject=str(manifest["source_lane_ref"]),
            holder_ref=str(manifest["target_holder_ref"]),
            expected_lease_id=str(lease["lease_id"]),
            expected_epoch=int(lease["epoch"]),
            expected_head=str(lease["expected_head"]),
            expected_expires_at=str(lease["expires_at"]),
            expected_payload_sha256=str(lease["payload_sha256"]),
            require_expired=False,
        )
        current = lease_record(row)
        _verify_destination_identity(destination, worktree, manifest, current)
        return current, _validated_handoff_acknowledgement(
            root=destination,
            manifest=manifest,
            lease=current,
        )


@contextmanager
def _verified_package_snapshot(*, package: Path, manifest: dict[str, Any], root: Path):
    with tempfile.TemporaryDirectory(prefix="handoff-import-") as temporary:
        snapshot = Path(temporary) / str(manifest["package_id"])
        shutil.copytree(
            package.resolve(), snapshot, symlinks=True, copy_function=_copy_regular_file
        )
        copied, gaps = verified_handoff_manifest(package=snapshot, root=root)
        if gaps or copied != manifest:
            raise _error(handoff_package_changed_after_verification=None)
        yield snapshot


def _restore_preserved_work(*, package: Path, manifest: dict[str, Any], worktree: Path) -> None:
    if manifest.get("dirty_disposition") != "preserved":
        return
    artifacts = {
        str(artifact.get("kind") or ""): package.resolve() / str(artifact.get("path") or "")
        for artifact in manifest.get("artifacts", [])
        if isinstance(artifact, dict)
    }
    if patch := artifacts.get("tracked_patch"):
        _run(worktree, "git", "apply", "--binary", patch.as_posix())
    if archive := artifacts.get("untracked_archive"):
        _run(worktree, "tar", "-xf", archive.as_posix())


def dirty_content_sha256(repo: Path) -> str:
    paths = _git_lines(repo, "ls-files", "--others", "--exclude-standard", "-z")
    payload = bytearray(
        subprocess.run(
            ("git", "diff", "--binary", "HEAD", "--"),
            cwd=repo,
            check=True,
            capture_output=True,
        ).stdout
    )
    for relative in paths:
        payload.extend(relative.encode() + (repo / relative).read_bytes())
    return sha256_bytes(bytes(payload))


def _publish_package(
    *, staging: Path, package_dir: Path, manifest: dict[str, Any], root: Path
) -> None:
    try:
        _rename_no_replace(staging, package_dir)
    except FileExistsError:
        existing, gaps = verified_handoff_manifest(package=package_dir, root=root)
        if gaps or existing != manifest:
            raise _error(handoff_package_collision_or_invalid=None) from None


def _validated_handoff_acknowledgement(
    *,
    root: Path,
    manifest: dict[str, Any],
    lease: dict[str, Any],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "package_id": str(manifest["package_id"]),
        "destination_lane_ref": str(manifest["source_lane_ref"]),
        "destination_head": str(manifest["source_head"]),
        "destination_tree": str(manifest["source_tree"]),
        "destination_holder_ref": str(manifest["target_holder_ref"]),
        "destination_lane_incarnation_id": str(lease["lane_incarnation_id"]),
        "destination_lease_id": str(lease["lease_id"]),
        "destination_lease_epoch": int(lease["epoch"]),
        "destination_lease_expected_head": str(lease["expected_head"]),
        "destination_lease_expires_at": str(lease["expires_at"]),
        "destination_lease_payload_sha256": str(lease["payload_sha256"]),
        "source_lease_transferred": False,
        "truth_boundary": "destination_holder_asserted_local_generation",
        "mints_authority": False,
    }
    acknowledgement = {"acknowledgement_id": _content_id("handoff-ack", payload), **payload}
    validation = validate_schema_instance(
        "handoff-acknowledgement.schema.json", acknowledgement, root=root
    )
    if not validation["ok"]:
        raise ValueError(
            "handoff_acknowledgement_invalid:"
            + ",".join(string_sequence(validation.get("required_gaps")))
        )
    return acknowledgement


def _compensate_failed_import(
    *,
    destination: Path,
    manifest: dict[str, Any],
    worktree_path: Path,
    created: tuple[bool, bool],
    lease: dict[str, Any],
) -> None:
    branch = str(manifest["source_lane_ref"])
    head = str(manifest["source_head"])
    ref_created, worktree_created = created
    if worktree_created:
        run_git(destination, "worktree", "remove", "--force", worktree_path.as_posix(), check=False)
    worktree_absent = not worktree_path.exists() and not any(
        line == f"worktree {worktree_path.as_posix()}"
        for line in run_git(
            destination, "worktree", "list", "--porcelain", check=False
        ).stdout.splitlines()
    )
    if ref_created and worktree_absent:
        run_git(destination, "update-ref", "-d", f"refs/heads/{branch}", head, check=False)
    if not worktree_absent or (
        ref_created
        and run_git(
            destination, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False
        ).returncode
        == 0
    ):
        raise _error(handoff_import_compensation_failed=None)
    if lease:
        revoke_lease(
            state_database(destination),
            subject=branch,
            holder_ref=str(lease["holder_ref"]),
            expected_lease_id=str(lease["lease_id"]),
            expected_epoch=int(lease["epoch"]),
            expected_head=str(lease["expected_head"]),
            expected_expires_at=str(lease["expires_at"]),
            expected_payload_sha256=str(lease["payload_sha256"]),
        )


def _preserve_dirty_work(*, repo: Path, package_dir: Path) -> list[dict[str, str]]:
    patch_path = package_dir / "tracked.patch"
    with patch_path.open("wb") as stream:
        subprocess.run(
            ["git", "diff", "--binary", "HEAD", "--"],
            cwd=repo,
            check=True,
            stdout=stream,
            stderr=subprocess.PIPE,
        )
    artifacts: list[dict[str, str]] = []
    if patch_path.stat().st_size:
        artifacts.append(_artifact(patch_path, package_dir, "tracked_patch"))
    else:
        patch_path.unlink()
    untracked = _git_lines(repo, "ls-files", "--others", "--exclude-standard", "-z")
    if untracked:
        archive = package_dir / "untracked.tar"
        _run(repo, "tar", "-cf", archive.as_posix(), "--", *untracked)
        artifacts.append(_artifact(archive, package_dir, "untracked_archive"))
    return artifacts


def _content_id(prefix: str, payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _artifact(path: Path, package_dir: Path, kind: str) -> dict[str, str]:
    return {
        "path": path.relative_to(package_dir).as_posix(),
        "sha256": sha256_bytes(path.read_bytes()),
        "kind": kind,
    }


def _git_lines(root: Path, *args: str) -> list[str]:
    value = run_git(root, *args).stdout
    return [item for item in value.split("\0") if item]


def _run(root: Path, *args: str) -> None:
    completed = subprocess.run(args, cwd=root, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise subprocess.SubprocessError(completed.stderr.strip() or completed.stdout.strip())


def _copy_regular_file(source: str | Path, target: str | Path) -> None:
    source, target = Path(source), Path(target)
    descriptor = os.open(source, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as reader:
        if not stat.S_ISREG(os.fstat(reader.fileno()).st_mode):
            message = f"handoff_artifact_unsafe:{source.name}"
            raise ValueError(message)
        with target.open("xb") as writer:
            shutil.copyfileobj(reader, writer)


def _rename_no_replace(source: Path, target: Path) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    source_bytes, target_bytes = os.fsencode(source), os.fsencode(target)
    name = "renamex_np" if hasattr(library, "renamex_np") else "renameat2"
    args = {
        "renamex_np": (source_bytes, target_bytes, 4),
        "renameat2": (-100, source_bytes, -100, target_bytes, 1),
    }[name]
    rename = getattr(library, name)
    if rename(*args) == 0:
        return
    error = ctypes.get_errno()
    exception = {errno.EEXIST: FileExistsError}.get(error, OSError)
    raise exception(error, os.strerror(error), target)
