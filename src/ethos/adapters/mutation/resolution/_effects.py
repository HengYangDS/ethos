"""Preservation and retirement effects for exceptional Work Lane resolution."""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from typing import Any
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.resolution._observation import untracked_files
from ethos.adapters.mutation.resolution._shared import canonical_package_path
from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import sha256_digest
from ethos.adapters.mutation.resolution.receipts import verify_preservation_package
from ethos.contracts.resolution.lane import LaneObservation
from ethos.contracts.resolution.lane import LaneResolutionReceipt
from ethos.contracts.resolution.lane import LaneResolutionState
from ethos.repository.policy.schema import validate_schema_instance


def prepare_resolution_effect(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
) -> tuple[dict[str, object], dict[str, object], LaneResolutionState, str]:
    """Prepare the optional recovery package and completion receipt."""
    package, gap = prepare_preservation_package(
        root=control_root,
        artifact_root=artifact_root,
        decision=decision,
        observation=observation,
        disposition=disposition,
    )
    state = cast(
        "LaneResolutionState",
        {
            "preserve-retire": "preserved_and_retired",
            "preserve": "preserved",
            "retire": "retired",
        }.get(disposition, "blocked_by_decision"),
    )
    if gap:
        return {}, {}, state, gap
    if disposition == "preserve-retire":
        verify_preservation_package(root=control_root, package=package, artifact_root=artifact_root)
    receipt = completion_receipt(decision, observation, state, package)
    if not validate_schema_instance(
        "lane-resolution-receipt.schema.json", receipt, root=control_root
    )["ok"]:
        return package, {}, state, "lane_resolution_receipt_invalid"
    return package, receipt, state, ""


def prepare_preservation_package(
    *,
    root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
) -> tuple[dict[str, object], str]:
    """Create one no-clobber recovery package when requested."""
    if disposition not in {"preserve", "preserve-retire"}:
        return {}, ""
    package = canonical_package_path(artifact_root, str(decision.get("decision_id") or ""))
    if package is None:
        return {}, "lane_resolution_preservation_path_outside_root"
    package.parent.mkdir(parents=True, exist_ok=True)
    try:
        package.mkdir()
    except FileExistsError:
        return {}, "lane_resolution_preservation_package_exists"
    return preserve_package(root, package, observation, decision), ""


def preserve_package(
    root: Path,
    package: Path,
    observation: LaneObservation,
    decision: dict[str, Any],
) -> dict[str, object]:
    """Materialize a Git bundle, exact patches, untracked archive, and manifest."""
    bundle = package / "repository.bundle"
    patch = package / "tracked.patch"
    index_patch = package / "index.patch"
    archive = package / "untracked.tar"
    source = Path(observation.path)
    run_command(source, "git", "bundle", "create", bundle.as_posix(), observation.lane_ref)
    patch.write_bytes(run_command_bytes(source, "git", "diff", "--binary", "HEAD", "--"))
    index_patch.write_bytes(
        run_command_bytes(source, "git", "diff", "--cached", "--binary", "HEAD", "--")
    )
    inventory = untracked_files(source)
    if inventory is None:
        msg = "lane_resolution_untracked_inventory_failed"
        raise ValueError(msg)
    if inventory:
        run_command(
            source,
            "tar",
            "-cf",
            archive.as_posix(),
            "--",
            *(item.decode(errors="surrogateescape") for item in inventory),
        )
    manifest = {
        "package_format_version": "v2",
        "decision_id": decision["decision_id"],
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        "observation_digest": observation.digest(),
        "bundle_sha256": sha256_digest(bundle),
        "patch_sha256": sha256_digest(patch),
        "index_patch_sha256": sha256_digest(index_patch),
        "untracked_archive_sha256": sha256_digest(archive) if archive.is_file() else "",
        "source_lease_transferred": False,
    }
    manifest_path = package / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "path": display_path(root, package),
        "manifest": manifest,
        "manifest_sha256": sha256_digest(manifest_path),
    }


def retire_lane(*, root: Path, observation: LaneObservation, force: bool = False) -> None:
    """Delete the exact branch and linked worktree with compare-and-swap semantics."""
    ref = f"refs/heads/{observation.lane_ref}"
    removed = False
    try:
        with subprocess.Popen(
            ["git", "update-ref", "--stdin"],
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as transaction:
            stdin, stdout = transaction.stdin, transaction.stdout
            if stdin is None or stdout is None or transaction.stderr is None:
                msg = "lane_resolution_branch_delete_failed"
                raise ValueError(msg)
            stdin.write("start\n")
            stdin.flush()
            started = stdout.readline() == "start: ok\n"
            stdin.write(f"delete {ref} {observation.head}\nprepare\n")
            stdin.flush()
            prepared = stdout.readline() == "prepare: ok\n"
            if not (started and prepared):
                stdin.write("abort\n")
                stdin.close()
                msg = "lane_resolution_branch_delete_failed"
                raise ValueError(msg)
            remove = ("worktree", "remove", *(("--force",) if force else ()), observation.path)
            if run_git(root, *remove, check=False).returncode:
                stdin.write("abort\n")
                stdin.close()
                msg = "lane_resolution_worktree_remove_failed"
                raise ValueError(msg)
            removed = True
            stdin.write("commit\n")
            stdin.close()
            committed = stdout.readline() == "commit: ok\n" and transaction.wait() == 0
    except OSError as error:
        if not removed:
            msg = "lane_resolution_branch_delete_failed"
            raise ValueError(msg) from error
        committed = False
    if committed:
        return
    present = run_git(root, "show-ref", "--verify", "--quiet", ref, check=False).returncode == 0
    raise ValueError(
        "lane_resolution_branch_delete_failed_after_worktree_removed"
        if present
        else "lane_resolution_branch_delete_state_uncertain"
    )


def completion_receipt(
    decision: dict[str, Any],
    observation: LaneObservation,
    state: LaneResolutionState,
    package: dict[str, object],
) -> dict[str, object]:
    """Build the immutable completion receipt."""
    return LaneResolutionReceipt(
        receipt_id=f"lane-resolution-receipt:{uuid.uuid4()}",
        decision_id=str(decision["decision_id"]),
        completed=True,
        state=state,
        observation_digest=observation.digest(),
        reconciliation_required=bool(decision.get("break_glass")),
        lane_ref=observation.lane_ref,
        head=observation.head,
        preservation_package=str(package.get("path") or ""),
        preservation_manifest_sha256=str(package.get("manifest_sha256") or ""),
        mints_authority=False,
    ).to_payload()


def run_command(root: Path, *args: str) -> None:
    _run_required_command(root, *args, text=True)


def run_command_bytes(root: Path, *args: str) -> bytes:
    return cast("bytes", _run_required_command(root, *args, text=False).stdout)


def _run_required_command(root: Path, *args: str, text: bool) -> subprocess.CompletedProcess[Any]:
    completed = subprocess.run(args, cwd=root, check=False, capture_output=True, text=text)
    if completed.returncode:
        stderr = completed.stderr
        detail = stderr.decode(errors="replace") if isinstance(stderr, bytes) else str(stderr or "")
        raise ValueError(detail.strip() or "command_failed")
    return completed
