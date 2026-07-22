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
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease_from_connection
from ethos.adapters.store.state.schema import state_database
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from ethos_core.contracts.coordination import CrossHostHandoff


def _require(gap: str, *, holds: bool) -> None:
    if not holds:
        raise ValueError(gap)


def write_handoff_package(
    *,
    repo: Path,
    handoff: CrossHostHandoff,
    context: str,
    output_root: Path | None,
) -> dict[str, object]:
    base = (output_root or repo / "build" / "artifacts" / "handoff").resolve()
    base.mkdir(parents=True, exist_ok=True)
    _verify_export_snapshot(repo=repo, handoff=handoff)
    with tempfile.TemporaryDirectory(prefix="handoff-", dir=base) as temporary:
        staging = Path(temporary)
        bundle = staging / "repository.bundle"
        run_git(
            repo,
            "bundle",
            "create",
            bundle.as_posix(),
            f"refs/heads/{handoff.source_lane_ref}",
        )
        _require(
            "handoff_bundle_identity_mismatch",
            holds=run_git(repo, "bundle", "list-heads", bundle.as_posix()).stdout.splitlines()
            == [f"{handoff.source_head} refs/heads/{handoff.source_lane_ref}"],
        )
        context_path = staging / "context.md"
        context_path.write_text(context, encoding="utf-8")
        artifacts = [
            _artifact(bundle, staging, "git_bundle"),
            _artifact(context_path, staging, "context"),
        ]
        validated = type(handoff).model_validate(
            {**handoff.model_dump(mode="python"), "artifacts": tuple(artifacts)}
        )
        body = {
            "schema_version": 1,
            **validated.to_payload(),
        }
        package_id = _content_id("handoff", body)
        package_dir = base / package_id
        manifest = {"package_id": package_id, **body}
        _require_schema(repo, manifest, "package")
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
    if package.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
        return {}, [
            "handoff_package_unsafe"
            if package.is_symlink()
            else "handoff_manifest_unsafe"
            if manifest_path.is_symlink()
            else "handoff_manifest_missing"
        ]
    manifest, gaps = _verified_json(manifest_path, root, "package")
    if not manifest:
        return manifest, gaps
    artifact_gaps, expected_paths = _artifact_gaps(package_dir, manifest.get("artifacts", []))
    gaps += artifact_gaps
    actual_paths = {
        path.relative_to(package_dir).as_posix()
        for path in package_dir.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    gaps += ["handoff_artifact_inventory_mismatch"] * (actual_paths != expected_paths)
    gaps += ["handoff_package_id_mismatch"] * (
        not gaps and package_dir.name != manifest.get("package_id")
    )
    return manifest, list(dict.fromkeys(gaps))


def _artifact_gaps(package_dir: Path, artifacts: object) -> tuple[list[str], set[str]]:
    source = artifacts if isinstance(artifacts, list) else []
    items = [artifact for artifact in source if isinstance(artifact, dict)]
    paths = [str(artifact.get("path") or "") for artifact in items]
    kinds = [str(artifact.get("kind") or "") for artifact in items]
    gaps = ["handoff_artifact_invalid"] * (len(items) != len(source))
    gaps += [
        f"handoff_artifact_{label}_duplicate:{value}"
        for label, values in (("path", paths), ("kind", kinds))
        for value in dict.fromkeys(values)
        if values.count(value) > 1
    ]
    for artifact, relative in zip(items, paths, strict=True):
        path = package_dir / relative
        if path.is_symlink() or not path.is_file():
            gaps.append(f"handoff_artifact_missing:{path.name}")
        elif sha256_bytes(path.read_bytes()) != str(artifact.get("sha256") or ""):
            gaps.append(f"handoff_artifact_digest_mismatch:{path.name}")
    gaps += [
        f"handoff_artifact_kind_missing:{kind}"
        for kind in ("git_bundle", "context")
        if kind not in kinds
    ]
    return gaps, {"manifest.json", *paths}


def verified_handoff_acknowledgement(
    *, acknowledgement: Path, root: Path
) -> tuple[dict[str, Any], list[str]]:
    """Validate one content-addressed destination assertion without minting authority."""
    return _verified_json(acknowledgement, root, "acknowledgement")


def _verified_json(path: Path, root: Path, kind: str) -> tuple[dict[str, Any], list[str]]:
    label = "manifest" if kind == "package" else kind
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        suffix = "unreadable" if isinstance(exc, OSError) else "invalid_json"
        return {}, [f"handoff_{label}_{suffix}"]
    if not isinstance(payload, dict):
        return {}, [f"handoff_{label}_invalid"]
    result = cast("dict[str, Any]", payload)
    field, prefix = {
        "package": ("package_id", "handoff"),
        "acknowledgement": ("acknowledgement_id", "handoff-ack"),
    }[kind]
    errors = validate_schema_instance(f"handoff-{kind}.schema.json", result, root=root)[
        "required_gaps"
    ]
    gaps = [f"handoff_{label}_invalid:{error}" for error in errors]
    expected = _content_id(prefix, {key: value for key, value in result.items() if key != field})
    gaps += [f"handoff_{kind}_id_mismatch"] * (not gaps and result.get(field) != expected)
    return result, gaps


def apply_handoff_import(
    *,
    destination: Path,
    package: Path,
    manifest: dict[str, Any],
    target_holder_ref: str,
) -> dict[str, object]:
    branch, head = str(manifest["source_lane_ref"]), str(manifest["source_head"])
    worktree_path = destination.with_name(f"{destination.name}-{branch.replace('/', '-')}")
    _require("handoff_destination_path_exists", holds=not os.path.lexists(worktree_path))
    ref_created = worktree_created = False
    lease: dict[str, Any] = {}
    try:
        with _verified_package_snapshot(
            package=package, manifest=manifest, root=destination
        ) as snapshot:
            _unbundle(
                destination,
                snapshot / "repository.bundle",
                branch,
                head,
                str(manifest["source_tree"]),
            )
            run_git(
                destination,
                "update-ref",
                "--stdin",
                stdin=f"create refs/heads/{branch} {head}\n",
            )
            ref_created = True
            run_git(destination, "worktree", "add", worktree_path.as_posix(), branch)
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
    _require("handoff_destination_identity_drift", holds=actual == (head, head, tree, head))


def _verify_export_snapshot(
    *,
    repo: Path,
    handoff: CrossHostHandoff,
) -> None:
    current = run_git(repo, "rev-parse", handoff.source_lane_ref).stdout.strip()
    _require("handoff_export_head_drift", holds=current == handoff.source_head)
    _require(
        "handoff_export_dirty_drift",
        holds=dirty_content_sha256(repo) == handoff.dirty_content_sha256,
    )
    source = cast("dict[str, Any]", handoff.to_payload()["source_lease_binding"])
    with closing(sqlite3.connect(state_database(repo))) as connection:
        connection.execute("begin immediate")
        try:
            expected_current_lease(
                connection,
                **_lease_binding(handoff.source_lane_ref, source),
                require_expired=False,
            )
        except ValueError:
            _require("handoff_export_lease_drift", holds=False)


def _commit_import(
    destination: Path,
    worktree: Path,
    manifest: dict[str, Any],
    lease: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, object]]:
    with closing(sqlite3.connect(state_database(destination))) as connection:
        connection.execute("begin immediate")
        expected_current_lease(
            connection,
            **_lease_binding(str(manifest["source_lane_ref"]), lease),
            require_expired=False,
        )
        _verify_destination_identity(destination, worktree, manifest, lease)
        return lease, _validated_handoff_acknowledgement(
            root=destination,
            manifest=manifest,
            lease=lease,
        )


@contextmanager
def _verified_package_snapshot(*, package: Path, manifest: dict[str, Any], root: Path):
    with tempfile.TemporaryDirectory(prefix="handoff-import-") as temporary:
        snapshot = Path(temporary) / str(manifest["package_id"])
        shutil.copytree(
            package.resolve(), snapshot, symlinks=True, copy_function=_copy_regular_file
        )
        copied, gaps = verified_handoff_manifest(package=snapshot, root=root)
        _require(
            "handoff_package_changed_after_verification",
            holds=not gaps and copied == manifest,
        )
        yield snapshot


def dirty_content_sha256(repo: Path) -> str:
    digest = hashlib.sha256()
    parts = [
        run_git(repo, "diff", "--binary", "HEAD", "--").stdout.encode(errors="surrogateescape")
    ]
    for relative in _git_lines(repo, "ls-files", "--others", "--exclude-standard", "-z"):
        parts.extend((relative.encode(errors="surrogateescape"), (repo / relative).read_bytes()))
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def _publish_package(
    *, staging: Path, package_dir: Path, manifest: dict[str, Any], root: Path
) -> None:
    try:
        _rename_no_replace(staging, package_dir)
    except FileExistsError:
        existing, gaps = verified_handoff_manifest(package=package_dir, root=root)
        _require("handoff_package_collision_or_invalid", holds=not gaps and existing == manifest)


def _validated_handoff_acknowledgement(
    *,
    root: Path,
    manifest: dict[str, Any],
    lease: dict[str, Any],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "package_id": manifest["package_id"],
        "destination_lane_ref": manifest["source_lane_ref"],
        "destination_head": manifest["source_head"],
        "destination_tree": manifest["source_tree"],
        "destination_holder_ref": manifest["target_holder_ref"],
        "destination_lane_incarnation_id": lease["lane_incarnation_id"],
        "destination_lease_id": lease["lease_id"],
        "destination_lease_epoch": lease["epoch"],
        "destination_lease_expected_head": lease["expected_head"],
        "destination_lease_expires_at": lease["expires_at"],
        "destination_lease_payload_sha256": lease["payload_sha256"],
        "source_lease_transferred": False,
        "truth_boundary": "destination_holder_asserted_local_generation",
        "mints_authority": False,
    }
    acknowledgement = {"acknowledgement_id": _content_id("handoff-ack", payload), **payload}
    _require_schema(root, acknowledgement, "acknowledgement")
    return acknowledgement


def _compensate_failed_import(
    *,
    destination: Path,
    manifest: dict[str, Any],
    worktree_path: Path,
    created: tuple[bool, bool],
    lease: dict[str, Any],
) -> None:
    try:
        if not lease:
            _remove_import_carriers(destination, manifest, worktree_path, created, {})
            return
        binding = _lease_binding(str(manifest["source_lane_ref"]), lease)
        with closing(sqlite3.connect(state_database(destination))) as connection:
            connection.execute("pragma foreign_keys = on")
            connection.execute("begin immediate")
            expected_current_lease(connection, **binding, require_expired=False)
            _remove_import_carriers(destination, manifest, worktree_path, created, lease)
            revoke_lease_from_connection(connection, **binding)
            connection.commit()
    except (OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError, ValueError):
        _require("handoff_import_compensation_failed", holds=False)


def _remove_import_carriers(
    destination: Path,
    manifest: dict[str, Any],
    worktree_path: Path,
    created: tuple[bool, bool],
    lease: dict[str, Any],
) -> None:
    branch, head = str(manifest["source_lane_ref"]), str(manifest["source_head"])
    ref_created, worktree_created = created
    present = os.path.lexists(worktree_path)
    record = _import_worktree_record(destination, worktree_path)
    _require(
        "handoff_import_compensation_failed",
        holds=(worktree_created, present, bool(record))
        in {(False, False, False), (True, True, True)},
    )
    if record:
        unsafe = (
            worktree_path.is_symlink()
            or not worktree_path.is_dir()
            or record.get("branch") != branch
            or record.get("HEAD") != head
            or any(flag in record for flag in ("locked", "prunable"))
        )
        _require("handoff_import_compensation_failed", holds=not unsafe)
        _verify_destination_identity(destination, worktree_path, manifest, lease)
        status = run_git(
            worktree_path, "status", "--porcelain", "-uall", "--ignored=matching", check=False
        )
        _require(
            "handoff_import_compensation_failed",
            holds=not status.returncode and not status.stdout.strip(),
        )
        removed = run_git(destination, "worktree", "remove", worktree_path.as_posix(), check=False)
        _require("handoff_import_compensation_failed", holds=not removed.returncode)
    _require(
        "handoff_import_compensation_failed",
        holds=not os.path.lexists(worktree_path)
        and not _import_worktree_record(destination, worktree_path),
    )
    if not ref_created:
        return
    ref = f"refs/heads/{branch}"
    observed = run_git(destination, "show-ref", "--verify", "--quiet", ref, check=False)
    _require("handoff_import_compensation_failed", holds=observed.returncode in {0, 1})
    if observed.returncode == 0:
        deleted = run_git(destination, "update-ref", "-d", ref, head, check=False)
        _require("handoff_import_compensation_failed", holds=not deleted.returncode)
    absent = run_git(destination, "show-ref", "--verify", "--quiet", ref, check=False)
    _require("handoff_import_compensation_failed", holds=absent.returncode == 1)


def _import_worktree_record(destination: Path, target: Path) -> dict[str, str]:
    listed = run_git(destination, "worktree", "list", "--porcelain", check=False)
    _require("handoff_import_compensation_failed", holds=not listed.returncode)
    records = [
        dict(line.partition(" ")[::2] for line in block.splitlines() if line)
        for block in listed.stdout.split("\n\n")
        if block.strip()
    ]
    _require(
        "handoff_import_compensation_failed",
        holds=all({"worktree", "HEAD"} <= record.keys() for record in records),
    )
    matches = [
        record for record in records if Path(record["worktree"]).resolve() == target.resolve()
    ]
    _require("handoff_import_compensation_failed", holds=len(matches) <= 1)
    record = matches[0] if matches else {}
    if record:
        record["branch"] = record.get("branch", "").removeprefix("refs/heads/")
    return record


def _lease_binding(branch: str, lease: dict[str, Any]) -> dict[str, Any]:
    return {
        "subject": branch,
        "holder_ref": str(lease["holder_ref"]),
        **{
            f"expected_{key.removeprefix('expected_')}": lease[key]
            for key in ("lease_id", "epoch", "expected_head", "expires_at", "payload_sha256")
        },
    }


def _require_schema(root: Path, payload: dict[str, object], kind: str) -> None:
    validation = validate_schema_instance(f"handoff-{kind}.schema.json", payload, root=root)
    label = "manifest" if kind == "package" else kind
    gaps = [f"handoff_{label}_invalid:{gap}" for gap in validation["required_gaps"]]
    _require(",".join(gaps), holds=not gaps)


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
    return [item for item in run_git(root, *args).stdout.split("\0") if item]


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
