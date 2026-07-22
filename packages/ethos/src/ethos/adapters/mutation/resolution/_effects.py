"""Preservation and retirement effects for exceptional lane resolution."""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.resolution._observation import untracked_files
from ethos.adapters.mutation.resolution._shared import canonical_package_path
from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import sha256_digest
from ethos.adapters.mutation.resolution.receipts import verify_preservation_package
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionReceipt


def prepare_resolution_effect(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
) -> tuple[dict[str, object], dict[str, object], str, str]:
    """Prepare and validate the package, state, and completion receipt."""
    package, gap = prepare_preservation_package(
        root=control_root,
        artifact_root=artifact_root,
        decision=decision,
        observation=observation,
        disposition=disposition,
    )
    if gap:
        return {}, {}, "", gap
    state = {
        "preserve-retire": "preserved_and_retired",
        "preserve": "preserved",
        "retire": "retired",
    }.get(disposition, "blocked_by_decision")
    if disposition == "preserve-retire":
        verify_preservation_package(
            root=control_root,
            package=package,
            artifact_root=artifact_root,
        )
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
    """Create one no-clobber preservation package when the disposition requires it."""
    if disposition not in {"preserve", "preserve-retire"}:
        return {}, ""
    package_path = canonical_package_path(artifact_root, str(decision.get("decision_id") or ""))
    if package_path is None:
        return {}, "lane_resolution_preservation_path_outside_root"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        package_path.mkdir()
    except FileExistsError:
        return {}, "lane_resolution_preservation_package_exists"
    return preserve_package(root, package_path, observation, decision), ""


def preserve_package(
    root: Path,
    package: Path,
    observation: LaneObservation,
    decision: dict[str, Any],
) -> dict[str, object]:
    """Materialize a recovery bundle, patch, untracked archive, and manifest."""
    bundle, patch, archive = (
        package / "repository.bundle",
        package / "tracked.patch",
        package / "untracked.tar",
    )
    source = Path(observation.path)
    run_command(source, "git", "bundle", "create", bundle.as_posix(), observation.lane_ref)
    patch.write_bytes(
        subprocess.run(
            ["git", "diff", "--binary", "HEAD", "--"], cwd=source, check=False, capture_output=True
        ).stdout
    )
    inventory = untracked_files(source)
    if inventory is None:
        raise ValueError("lane_resolution_untracked_inventory_failed")  # noqa: EM101, RUF100
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
        "decision_id": decision["decision_id"],
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        "observation_digest": observation.digest(),
        "bundle_sha256": sha256_digest(bundle),
        "patch_sha256": sha256_digest(patch),
        "untracked_archive_sha256": sha256_digest(archive) if archive.is_file() else "",
        "source_lease_transferred": False,
    }
    manifest_path = package / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "path": display_path(root, package),
        "manifest": manifest,
        "manifest_sha256": sha256_digest(manifest_path),
    }


def retire_lane(*, root: Path, observation: LaneObservation) -> None:
    """Delete the exact observed branch and worktree, restoring the ref on remove failure."""
    ref = f"refs/heads/{observation.lane_ref}"
    if run_git(root, "update-ref", "-d", ref, observation.head, check=False).returncode:
        raise ValueError("lane_resolution_branch_delete_failed")  # noqa: EM101, RUF100
    if run_git(root, "worktree", "remove", "--force", observation.path, check=False).returncode:
        run_git(root, "update-ref", ref, observation.head, "0" * 40, check=False)
        raise ValueError("lane_resolution_worktree_remove_failed")  # noqa: EM101, RUF100


def completion_receipt(
    decision: dict[str, Any],
    observation: LaneObservation,
    state: str,
    package: dict[str, object],
) -> dict[str, object]:
    """Build one schema-bound completion receipt payload."""
    manifest_digest = str(package.get("manifest_sha256") or "")
    return LaneResolutionReceipt(
        receipt_id=f"lane-resolution-receipt:{uuid.uuid4()}",
        decision_id=str(decision["decision_id"]),
        disposition=decision["disposition"],
        completed=True,
        state=state,
        observation_digest=observation.digest(),
        reconciliation_required=bool(decision.get("break_glass")),
        lane_ref=observation.lane_ref,
        head=observation.head,
        preservation_package=str(package.get("path") or ""),
        preservation_manifest_sha256=manifest_digest,
        mints_authority=False,
    ).to_payload()


def write_completion_receipt(
    *,
    control_root: Path,
    artifact_root: Path,
    receipt: dict[str, object],
    destructive_effect: bool,
) -> tuple[str, str]:
    """Write a receipt or report the post-effect partial-transition gap."""
    try:
        return (
            write_resolution_receipt(
                root=control_root,
                receipt=receipt,
                artifact_root=artifact_root,
            ),
            "",
        )
    except OSError:
        if not destructive_effect:
            raise
        return "", "lane_resolution_receipt_write_failed_after_effect"


def run_command(root: Path, *args: str) -> None:
    """Run one required preservation command and fail with its diagnostic."""
    completed = subprocess.run(args, cwd=root, check=False, capture_output=True, text=True)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "command_failed")
