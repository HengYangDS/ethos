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
import tempfile
from contextlib import closing
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.store.state.lease.lifecycle.transitions import expected_current_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from ethos.contracts.coordination import CrossHostHandoff


def require(gap: str, *, holds: bool) -> None:
    """Raise one stable handoff gap when an invariant does not hold."""
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
    commitment = load_lease_bound_commitment(
        repo,
        lease={
            "expected_head": handoff.source_head,
            "expected_tree": handoff.source_tree,
            "base_commitment_path": handoff.base_commitment_path,
            "base_commitment_bytes_sha256": handoff.base_commitment_bytes_sha256,
            "base_commitment_digest": handoff.base_commitment_digest,
        },
    )
    recognized = False
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
        require(
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
        recognized = package_dir.exists()
        _publish_package(staging=staging, package_dir=package_dir, manifest=manifest, root=repo)
    return {
        "state": "exported",
        "package_id": package_id,
        "package_path": package_dir.as_posix(),
        "manifest": manifest,
        "attestation": issue_native_effect(
            repo,
            effect=NativeEffect(
                predicate="effect:handoff-package",
                operation="filesystem.publish-no-replace",
                command=("rename-no-replace",),
                subject={"package_id": package_id, "path": package_dir.as_posix()},
                before={"present": recognized, "manifest": manifest if recognized else {}},
                after={"present": True, "manifest": manifest},
            ),
            state="recognized" if recognized else "applied",
            commitment_digest=commitment.digest(),
            repository_id=commitment.subjects[0],
        ).model_dump(mode="json"),
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
        elif hashlib.sha256(path.read_bytes()).hexdigest() != str(artifact.get("sha256") or ""):
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


def _verify_export_snapshot(
    *,
    repo: Path,
    handoff: CrossHostHandoff,
) -> None:
    current = run_git(repo, "rev-parse", handoff.source_lane_ref).stdout.strip()
    require("handoff_export_head_drift", holds=current == handoff.source_head)
    require(
        "handoff_export_dirty_drift",
        holds=dirty_content_sha256(repo) == handoff.dirty_content_sha256,
    )
    source = cast("dict[str, Any]", handoff.to_payload()["source_lease_binding"])
    with closing(sqlite3.connect(state_database(repo))) as connection:
        connection.execute("begin immediate")
        try:
            _, lease = expected_current_lease(
                connection,
                request=lease_binding(handoff.source_lane_ref, source),
                require_expired=False,
            )
            require(
                "handoff_export_lane_incarnation_mismatch",
                holds=lease.lane_incarnation_id == handoff.source_lane_incarnation_id,
            )
            require(
                "handoff_export_base_commitment_path_mismatch",
                holds=lease.base_commitment_path == handoff.base_commitment_path,
            )
            require(
                "handoff_export_base_commitment_bytes_mismatch",
                holds=(lease.base_commitment_bytes_sha256 == handoff.base_commitment_bytes_sha256),
            )
            require(
                "handoff_export_base_commitment_digest_mismatch",
                holds=lease.base_commitment_digest == handoff.base_commitment_digest,
            )
        except ValueError as error:
            message = "handoff_export_lease_drift"
            raise ValueError(message) from error
    try:
        load_lease_bound_commitment(repo, lease=lease.to_payload())
    except ValueError as error:
        if str(error) == "lease_base_commitment_digest_mismatch":
            message = "handoff_export_base_commitment_digest_mismatch"
            raise ValueError(message) from error
        message = "handoff_export_base_commitment_invalid"
        raise ValueError(message) from error


@contextmanager
def verified_package_snapshot(*, package: Path, manifest: dict[str, Any], root: Path):
    """Yield one immutable verified package snapshot for an import transaction."""
    with tempfile.TemporaryDirectory(
        prefix="handoff-import-", ignore_cleanup_errors=True
    ) as temporary:
        snapshot = Path(temporary) / str(manifest["package_id"])
        shutil.copytree(
            package.resolve(), snapshot, symlinks=True, copy_function=_copy_regular_file
        )
        copied, gaps = verified_handoff_manifest(package=snapshot, root=root)
        require(
            "handoff_package_changed_after_verification",
            holds=not gaps and copied == manifest,
        )
        yield snapshot


def _publish_package(
    *, staging: Path, package_dir: Path, manifest: dict[str, Any], root: Path
) -> None:
    try:
        _rename_no_replace(staging, package_dir)
    except FileExistsError:
        existing, gaps = verified_handoff_manifest(package=package_dir, root=root)
        require("handoff_package_collision_or_invalid", holds=not gaps and existing == manifest)


def validated_handoff_acknowledgement(
    *,
    root: Path,
    manifest: dict[str, Any],
    lease: dict[str, Any],
) -> dict[str, object]:
    """Serialize and validate one destination acknowledgement."""
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
        "destination_lease_expected_tree": lease["expected_tree"],
        "destination_lease_expires_at": lease["expires_at"],
        "destination_lease_payload_sha256": lease["payload_sha256"],
        "destination_lease_base_commitment_path": lease["base_commitment_path"],
        "destination_lease_base_commitment_bytes_sha256": lease["base_commitment_bytes_sha256"],
        "base_commitment_digest": lease["base_commitment_digest"],
        "source_lease_transferred": False,
        "truth_boundary": "destination_holder_asserted_local_generation",
        "mints_authority": False,
    }
    acknowledgement = {"acknowledgement_id": _content_id("handoff-ack", payload), **payload}
    _require_schema(root, acknowledgement, "acknowledgement")
    return acknowledgement


def lease_binding(branch: str, lease: dict[str, Any]) -> LeaseOperationRequest:
    """Compile one exact Lease compare-and-swap request."""
    return LeaseOperationRequest(
        operation="handoff_validate",
        branch=branch,
        holder_ref=str(lease["holder_ref"]),
        lease_id=str(lease["lease_id"]),
        expected_epoch=int(lease["epoch"]),
        expect_head=str(lease["expected_head"]),
        expected_expires_at=str(lease["expires_at"]),
        expected_payload_sha256=str(lease["payload_sha256"]),
        apply=True,
    )


def _require_schema(root: Path, payload: dict[str, object], kind: str) -> None:
    validation = validate_schema_instance(f"handoff-{kind}.schema.json", payload, root=root)
    label = "manifest" if kind == "package" else kind
    gaps = [f"handoff_{label}_invalid:{gap}" for gap in validation["required_gaps"]]
    require(",".join(gaps), holds=not gaps)


def _content_id(prefix: str, payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _artifact(path: Path, package_dir: Path, kind: str) -> dict[str, str]:
    return {
        "path": path.relative_to(package_dir).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "kind": kind,
    }


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
