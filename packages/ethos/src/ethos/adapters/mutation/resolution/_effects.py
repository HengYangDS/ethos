"""Preservation and retirement effects for exceptional lane resolution."""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos.adapters.mutation.resolution.closeout.effect as ownerless_effect
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.resolution._observation import observe_lane
from ethos.adapters.mutation.resolution._observation import untracked_files
from ethos.adapters.mutation.resolution._shared import canonical_package_path
from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import sha256_digest
from ethos.adapters.mutation.resolution.closeout.wcp.core import run_worktree_closeout_check
from ethos.adapters.mutation.resolution.receipts import verify_preservation_package
from ethos.adapters.mutation.resolution.records.core import ownerless_closeout_reservation_path
from ethos.adapters.mutation.resolution.records.core import read_ownerless_closeout_reservation
from ethos.adapters.mutation.resolution.records.core import reserve_ownerless_closeout_target
from ethos.adapters.mutation.resolution.records.core import (
    transition_ownerless_closeout_reservation,
)
from ethos.adapters.mutation.resolution.records.release import (
    release_ownerless_no_effect_reservation,
)
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.closeout import acquire_closeout_fence
from ethos.adapters.store.state.closeout import get_closeout_fence
from ethos.adapters.store.state.closeout import probe_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.closeout import LaneResolutionReceipt
from ethos_core.contracts.resolution.closeout import LaneResolutionState

if TYPE_CHECKING:
    from ethos_core.contracts.resolution.lane import LaneObservation

_OWNERLESS_REF_PREPARE_FAILED = "lane_resolution_ownerless_ref_prepare_failed"


class OwnerlessCloseoutError(ValueError):
    """A fail-closed ownerless transition with durable-fence state."""

    def __init__(self, gap: str, *, fence_acquired: bool) -> None:
        super().__init__(gap)
        self.fence_acquired = fence_acquired


def _ownerless_error(gap: str, *, fence_acquired: bool) -> OwnerlessCloseoutError:
    return OwnerlessCloseoutError(gap, fence_acquired=fence_acquired)


def prepare_resolution_effect(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
) -> tuple[dict[str, object], dict[str, object], LaneResolutionState, str]:
    """Prepare and validate the package, state, and completion receipt."""
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
    """Create one no-clobber preservation package when required."""
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
    """Materialize a recovery bundle, worktree/index patches, archive, and manifest."""
    bundle, patch, index_patch, archive = (
        package / "repository.bundle",
        package / "tracked.patch",
        package / "index.patch",
        package / "untracked.tar",
    )
    source = Path(observation.path)
    run_command(source, "git", "bundle", "create", bundle.as_posix(), observation.lane_ref)
    patch.write_bytes(run_command_bytes(source, "git", "diff", "--binary", "HEAD", "--"))
    index_patch.write_bytes(
        run_command_bytes(source, "git", "diff", "--cached", "--binary", "HEAD", "--")
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
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "path": display_path(root, package),
        "manifest": manifest,
        "manifest_sha256": sha256_digest(manifest_path),
    }


def _ownerless_runtime() -> ownerless_effect.OwnerlessCloseoutRuntime:
    return ownerless_effect.OwnerlessCloseoutRuntime(
        run_git=run_git,
        observe_lane=observe_lane,
        current_record_root=current_record_root,
        reservation_path=ownerless_closeout_reservation_path,
        read_reservation=read_ownerless_closeout_reservation,
        reserve_target=reserve_ownerless_closeout_target,
        release_no_effect_reservation=release_ownerless_no_effect_reservation,
        transition_reservation=transition_ownerless_closeout_reservation,
        leases_by_branch=leases_by_branch,
        acquire_fence=acquire_closeout_fence,
        release_fence=release_closeout_fence,
        get_fence=get_closeout_fence,
        probe_fence=probe_closeout_fence,
        state_database=state_database,
        run_wcp=run_worktree_closeout_check,
        ownerless_error=_ownerless_error,
        ownerless_error_type=OwnerlessCloseoutError,
        verify_pre_effect=_verify_ownerless_pre_effect,
        retire_cas=_retire_clean_ownerless_cas,
        probe_ref=probe_ownerless_ref,
        verify_postconditions=_verify_ownerless_postconditions,
    )


def retire_clean_ownerless_lane(  # noqa: PLR0913, RUF100 - compatibility effect boundary
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    executor_ref: str,
    accepted_branch: str,
    accepted_head: str,
    artifact_root: Path | None = None,
) -> dict[str, object]:
    """Run strict WCP admission, durable fencing, exact CAS, and postverification."""
    return ownerless_effect.retire_clean_ownerless_lane(
        root=root,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        executor_ref=executor_ref,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
        artifact_root=artifact_root,
        runtime=_ownerless_runtime(),
    )


def recover_completed_ownerless_closeout(  # noqa: PLR0913, RUF100 - compatibility recovery boundary
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    executor_ref: str,
    reservation: dict[str, object],
    receipt: dict[str, object] | None = None,
) -> dict[str, object]:
    """Reverify one exact completed effect before its missing receipt is written."""
    return ownerless_effect.recover_completed_ownerless_closeout(
        root=root,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        executor_ref=executor_ref,
        reservation=reservation,
        receipt=receipt,
        runtime=_ownerless_runtime(),
    )


def _verify_ownerless_pre_effect(  # noqa: PLR0913, RUF100 - exact pre-effect CAS dimensions
    *,
    root: Path,
    database: Path,
    decision_path: Path,
    decision_sha256: str,
    observation: LaneObservation,
    accepted_branch: str,
    accepted_head: str,
    fence: dict[str, object],
) -> None:
    ownerless_effect.verify_ownerless_pre_effect(
        runtime=_ownerless_runtime(),
        root=root,
        database=database,
        decision_path=decision_path,
        decision_sha256=decision_sha256,
        observation=observation,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
        fence=fence,
    )


def _retire_clean_ownerless_cas(
    *,
    root: Path,
    observation: LaneObservation,
    accepted_branch: str,
    accepted_head: str,
) -> None:
    target_ref = f"refs/heads/{observation.lane_ref}"
    accepted_ref = f"refs/heads/{accepted_branch}"
    removed = remove_failed = committed = False
    try:
        with subprocess.Popen(
            ["git", "update-ref", "--stdin"],  # noqa: S607, RUF100 - effect boundary
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as transaction:
            stdin, stdout = transaction.stdin, transaction.stdout
            if stdin is None or stdout is None or transaction.stderr is None:
                raise _ownerless_error(_OWNERLESS_REF_PREPARE_FAILED, fence_acquired=True)
            stdin.write("start\n")
            stdin.flush()
            started = stdout.readline() == "start: ok\n"
            stdin.write(f"update {accepted_ref} {accepted_head} {accepted_head}\n")
            stdin.write(f"delete {target_ref} {observation.head}\nprepare\n")
            stdin.flush()
            prepared = stdout.readline() == "prepare: ok\n"
            if not (started and prepared):
                stdin.write("abort\n")
                stdin.close()
                raise _ownerless_error(_OWNERLESS_REF_PREPARE_FAILED, fence_acquired=True)
            remove_failed = True
            remove = run_git(root, "worktree", "remove", observation.path, check=False)
            if remove.returncode:
                stdin.write("abort\n")
                stdin.close()
                transaction.wait()
            else:
                remove_failed = False
                removed = True
                stdin.write("commit\n")
                stdin.close()
                committed = stdout.readline() == "commit: ok\n" and transaction.wait() == 0
    except OSError as error:
        if not (removed or remove_failed):
            raise _ownerless_error(_OWNERLESS_REF_PREPARE_FAILED, fence_acquired=True) from error
        committed = False
    if remove_failed:
        raise _ownerless_error(
            _failed_ownerless_remove_gap(root, observation, allow_no_effect=True),
            fence_acquired=True,
        )
    if committed:
        return
    raise _ownerless_error(
        _failed_ownerless_remove_gap(root, observation, allow_no_effect=False),
        fence_acquired=True,
    )


def _failed_ownerless_remove_gap(
    root: Path, observation: LaneObservation, *, allow_no_effect: bool
) -> str:
    ref_state, oid = probe_ownerless_ref(root, observation.lane_ref)
    registration = _ownerless_worktree_registration(root, observation.path)
    path_intact = Path(observation.path).is_dir() and not Path(observation.path).is_symlink()
    ref_intact = ref_state == "oid" and oid == observation.head
    if allow_no_effect and ref_intact and registration is True and path_intact:
        return "lane_resolution_ownerless_worktree_remove_failed"
    if ref_intact and (registration is False or not path_intact):
        return "lane_resolution_ownerless_worktree_removed_ref_present"
    return "lane_resolution_ownerless_transition_unknown"


def _ownerless_worktree_registration(root: Path, path: str) -> bool | None:
    try:
        result = run_git(root, "worktree", "list", "--porcelain", check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    return f"worktree {path}" in result.stdout.splitlines()


def probe_ownerless_ref(root: Path, branch: str) -> tuple[str, str]:
    """Return the exact ref OID, explicit absence, or an unverifiable state."""
    ref = f"refs/heads/{branch}"
    try:
        presence = run_git(root, "show-ref", "--verify", "--quiet", ref, check=False)
        if presence.returncode == 1:
            return "absent", ""
        if presence.returncode:
            return "unverifiable", ""
        result = run_git(root, "show-ref", "--hash", "--verify", ref, check=False)
    except (OSError, subprocess.SubprocessError):
        return "unverifiable", ""
    oid = result.stdout.strip()
    if result.returncode == 0 and len(oid) in {40, 64} and set(oid) <= set("0123456789abcdef"):
        return "oid", oid
    return "unverifiable", ""


def _verify_ownerless_postconditions(  # noqa: PLR0913, RUF100 - exact postcondition dimensions
    *,
    root: Path,
    database: Path,
    decision_path: Path,
    decision_sha256: str,
    observation: LaneObservation,
    accepted_branch: str,
    accepted_head: str,
    fence: dict[str, object] | None,
    decision_bytes: bytes | None = None,
) -> dict[str, object]:
    return ownerless_effect.verify_ownerless_postconditions(
        runtime=_ownerless_runtime(),
        root=root,
        database=database,
        decision_path=decision_path,
        decision_sha256=decision_sha256,
        observation=observation,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
        fence=fence,
        decision_bytes=decision_bytes,
    )


def retire_lane(*, root: Path, observation: LaneObservation, force: bool = False) -> None:
    """Prepare ref deletion, remove the exact worktree, then commit deletion."""
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
                raise ValueError("lane_resolution_branch_delete_failed")  # noqa: EM101, RUF100
            stdin.write("start\n")
            stdin.flush()
            started = stdout.readline() == "start: ok\n"
            stdin.write(f"delete {ref} {observation.head}\nprepare\n")
            stdin.flush()
            prepared = stdout.readline() == "prepare: ok\n"
            if not (started and prepared):
                stdin.write("abort\n")
                stdin.close()
                raise ValueError("lane_resolution_branch_delete_failed")  # noqa: EM101, RUF100
            remove = ("worktree", "remove", *(("--force",) if force else ()), observation.path)
            if run_git(root, *remove, check=False).returncode:
                stdin.write("abort\n")
                stdin.close()
                raise ValueError("lane_resolution_worktree_remove_failed")  # noqa: EM101, RUF100
            removed = True
            stdin.write("commit\n")
            stdin.close()
            committed = stdout.readline() == "commit: ok\n" and transaction.wait() == 0
    except OSError as error:
        if not removed:
            message = "lane_resolution_branch_delete_failed"
            raise ValueError(message) from error
        committed = False
    if not committed:
        present = run_git(root, "show-ref", "--verify", "--quiet", ref, check=False).returncode == 0
        message = (
            "lane_resolution_branch_delete_failed_after_worktree_removed"
            if present
            else "lane_resolution_branch_delete_state_uncertain"
        )
        raise ValueError(message)


def completion_receipt(
    decision: dict[str, Any],
    observation: LaneObservation,
    state: LaneResolutionState,
    package: dict[str, object],
) -> dict[str, object]:
    """Build one schema-bound completion receipt payload."""
    return LaneResolutionReceipt(
        schema_version=3,
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
    """Run one required preservation command and fail with its diagnostic."""
    _run_required_command(root, *args, text=True)


def run_command_bytes(root: Path, *args: str) -> bytes:
    """Run one byte-preserving command and fail with its diagnostic."""
    return cast("bytes", _run_required_command(root, *args, text=False).stdout)


def _run_required_command(root: Path, *args: str, text: bool) -> subprocess.CompletedProcess[Any]:
    completed = subprocess.run(args, cwd=root, check=False, capture_output=True, text=text)
    if completed.returncode:
        stderr = completed.stderr
        detail = stderr.decode(errors="replace") if isinstance(stderr, bytes) else str(stderr or "")
        raise ValueError(detail.strip() or "command_failed")
    return completed
