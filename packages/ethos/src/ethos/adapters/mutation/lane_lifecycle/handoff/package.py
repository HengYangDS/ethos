"""Content-addressed package effects for cross-host Work Lane handoff."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.coordination import CrossHostHandoff
from ethos_core.contracts.coordination import HolderRef
from ethos_core.normalization.core import string_sequence

if TYPE_CHECKING:
    from collections.abc import Sequence


def write_handoff_package(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    repo: Path,
    branch: str,
    head: str,
    tree: str,
    holder_ref: str,
    target_holder_ref: str,
    lease_id: str,
    epoch: int,
    context: str,
    output_root: Path | None,
    dirty_disposition: str,
    dirty_paths: Sequence[str],
) -> dict[str, object]:
    context_digest = hashlib.sha256(context.encode()).hexdigest()
    base = (output_root or repo / "build" / "artifacts" / "handoff").resolve()
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="handoff-", dir=base) as temporary:
        staging = Path(temporary)
        bundle = staging / "repository.bundle"
        _run(repo, "git", "bundle", "create", bundle.as_posix(), branch)
        context_path = staging / "context.md"
        context_path.write_text(context, encoding="utf-8")
        artifacts = [
            _artifact(bundle, staging, "git_bundle"),
            _artifact(context_path, staging, "context"),
        ]
        if dirty_paths and dirty_disposition == "preserved":
            artifacts.extend(_preserve_dirty_work(repo=repo, package_dir=staging))
        package_id = _handoff_package_id(
            branch=branch,
            head=head,
            tree=tree,
            target_holder_ref=target_holder_ref,
            context_digest=context_digest,
            dirty_disposition=dirty_disposition,
            artifacts=artifacts,
        )
        package_dir = base / package_id
        if package_dir.exists():
            shutil.rmtree(package_dir)
        shutil.move(staging.as_posix(), package_dir.as_posix())
    contract = CrossHostHandoff(
        source_lane_ref=branch,
        source_head=head,
        source_tree=tree,
        target_holder_ref=HolderRef.parse(target_holder_ref),
        context_digest=context_digest,
        dirty_disposition=dirty_disposition,
        source_lease_id=lease_id,
        source_lease_epoch=epoch,
        source_holder_ref=HolderRef.parse(holder_ref),
        artifacts=tuple(artifacts),
    ).to_payload()
    manifest = {"schema_version": 1, "package_id": package_id, **contract}
    validation = validate_schema_instance("handoff-package.schema.json", manifest, root=repo)
    if not validation["ok"]:
        raise ValueError(
            "handoff_manifest_invalid:" + ",".join(string_sequence(validation.get("required_gaps")))
        )
    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "ok": True,
        "state": "exported",
        "package_id": package_id,
        "package_path": package_dir.as_posix(),
        "manifest": manifest,
        "receipt": {
            "operation": "cross-host-export",
            "package_id": package_id,
            "source_head": head,
            "source_lease_transferred": False,
        },
        "required_gaps": [],
    }


def verified_handoff_manifest(*, package: Path, root: Path) -> tuple[dict[str, Any], list[str]]:
    package_dir = package.resolve()
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.is_file():
        return {}, ["handoff_manifest_missing"]
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
    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict):
            gaps.append("handoff_artifact_invalid")
            continue
        path = package_dir / str(artifact.get("path") or "")
        if not path.is_file():
            gaps.append(f"handoff_artifact_missing:{path.name}")
        elif _sha256_file(path) != str(artifact.get("sha256") or ""):
            gaps.append(f"handoff_artifact_digest_mismatch:{path.name}")
    return cast("dict[str, Any]", manifest), gaps


def apply_handoff_import(
    *,
    destination: Path,
    package: Path,
    manifest: dict[str, Any],
    target_holder_ref: str,
) -> dict[str, object]:
    branch = str(manifest["source_lane_ref"])
    head = str(manifest["source_head"])
    bundle = package.resolve() / "repository.bundle"
    worktree_path = destination.with_name(f"{destination.name}-{branch.replace('/', '-')}")
    branch_created = False
    worktree_created = False
    try:
        _run(destination, "git", "fetch", bundle.as_posix(), f"{branch}:{branch}")
        branch_created = True
        _run(destination, "git", "worktree", "add", worktree_path.as_posix(), branch)
        worktree_created = True
        lease = acquire_lease(
            destination / ".ethos" / "state" / "state.sqlite",
            subject=branch,
            holder_ref=target_holder_ref,
            payload={
                "path": worktree_path.as_posix(),
                "branch": branch,
                "expected_head": head,
                "handoff_package_id": str(manifest["package_id"]),
                "source_lane_ref": branch,
                "source_head": head,
            },
        )
        _restore_preserved_work(package=package, manifest=manifest, worktree=worktree_path)
    except (OSError, subprocess.SubprocessError, ValueError):
        if worktree_created:
            subprocess.run(
                ["git", "worktree", "remove", "--force", worktree_path.as_posix()],
                cwd=destination,
                check=False,
                capture_output=True,
            )
        if branch_created:
            subprocess.run(
                ["git", "update-ref", "-d", f"refs/heads/{branch}", head],
                cwd=destination,
                check=False,
                capture_output=True,
            )
        raise
    ack = {
        "acknowledgement_id": f"handoff-ack:{uuid.uuid4()}",
        "package_id": str(manifest["package_id"]),
        "destination_lane_ref": branch,
        "destination_head": head,
        "destination_holder_ref": target_holder_ref,
        "destination_lane_incarnation_id": str(lease["lane_incarnation_id"]),
        "destination_lease_id": str(lease["lease_id"]),
        "source_lease_transferred": False,
    }
    return {
        "ok": True,
        "state": "imported",
        "package_id": str(manifest["package_id"]),
        "worktree": {"branch": branch, "path": worktree_path.as_posix(), "head": head},
        "lease": lease,
        "acknowledgement": ack,
        "receipt": {"operation": "cross-host-import", **ack},
        "required_gaps": [],
    }


def _restore_preserved_work(*, package: Path, manifest: dict[str, Any], worktree: Path) -> None:
    if manifest.get("dirty_disposition") != "preserved":
        return
    artifacts = {
        str(artifact.get("kind") or ""): package.resolve() / str(artifact.get("path") or "")
        for artifact in manifest.get("artifacts", [])
        if isinstance(artifact, dict)
    }
    patch = artifacts.get("tracked_patch")
    if patch is not None:
        _run(worktree, "git", "apply", "--binary", patch.as_posix())
    archive = artifacts.get("untracked_archive")
    if archive is not None:
        _run(worktree, "tar", "-xf", archive.as_posix())


def _preserve_dirty_work(*, repo: Path, package_dir: Path) -> list[dict[str, str]]:
    patch_path = package_dir / "tracked.patch"
    with patch_path.open("wb") as stream:
        completed = subprocess.run(
            ["git", "diff", "--binary", "HEAD", "--"],
            cwd=repo,
            check=False,
            stdout=stream,
            stderr=subprocess.PIPE,
        )
    if completed.returncode != 0:
        raise subprocess.SubprocessError(completed.stderr.decode(errors="replace"))
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


def _handoff_package_id(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    branch: str,
    head: str,
    tree: str,
    target_holder_ref: str,
    context_digest: str,
    dirty_disposition: str,
    artifacts: list[dict[str, str]],
) -> str:
    identity = json.dumps(
        {
            "branch": branch,
            "head": head,
            "tree": tree,
            "target_holder_ref": target_holder_ref,
            "context_digest": context_digest,
            "dirty_disposition": dirty_disposition,
            "artifacts": artifacts,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return f"handoff:{hashlib.sha256(identity).hexdigest()}"


def _artifact(path: Path, package_dir: Path, kind: str) -> dict[str, str]:
    return {
        "path": path.relative_to(package_dir).as_posix(),
        "sha256": _sha256_file(path),
        "kind": kind,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_lines(root: Path, *args: str) -> list[str]:
    value = run_git(root, *args).stdout
    return [item for item in value.split("\0") if item]


def _run(root: Path, *args: str) -> None:
    completed = subprocess.run(args, cwd=root, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise subprocess.SubprocessError(completed.stderr.strip() or completed.stdout.strip())
