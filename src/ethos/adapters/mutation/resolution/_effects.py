"""Preservation and retirement effects for exceptional lane resolution."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.resolution.capture import write_git_preservation_payloads
from ethos.adapters.mutation.resolution.capture import write_untracked_archive
from ethos.adapters.mutation.resolution.observation import untracked_files
from ethos.adapters.mutation.resolution.receipts import verify_preservation_package
from ethos.adapters.mutation.resolution.records.roots import display_record_path
from ethos.adapters.mutation.resolution.records.roots import record_path_is_safe
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.closeout import probe_closeout_fence
from ethos.contracts.resolution.closeout import LaneResolutionReceipt
from ethos.contracts.resolution.closeout import LaneResolutionState
from ethos.contracts.resolution.lane import is_lane_decision_id
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from ethos.contracts.resolution.closeout import OwnerlessCloseoutPhase
    from ethos.contracts.resolution.closeout import OwnerlessCloseoutRecoveryState
    from ethos.contracts.resolution.lane import LaneObservation


_OWNERLESS_ACCEPTED_HEAD_STALE = "lane_resolution_ownerless_accepted_head_stale"
_OWNERLESS_UNTRACKED_INVENTORY_FAILED = "lane_resolution_untracked_inventory_failed"
_OWNERLESS_BRANCH_DELETE_FAILED = "lane_resolution_branch_delete_failed"
_OWNERLESS_WORKTREE_REMOVE_FAILED = "lane_resolution_worktree_remove_failed"
_WORKTREE_VALUE_FIELDS = {"worktree", "HEAD", "branch"}
_WORKTREE_MARKER_FIELDS = {"detached", "bare"}
_WORKTREE_OPTIONAL_VALUE_FIELDS = {"locked", "prunable"}
_WORKTREE_ALLOWED_FIELDS = (
    _WORKTREE_VALUE_FIELDS | _WORKTREE_MARKER_FIELDS | _WORKTREE_OPTIONAL_VALUE_FIELDS
)


class OwnerlessCloseoutError(ValueError):
    """A fail-closed transition with explicit durable reservation state."""

    def __init__(
        self,
        gap: str,
        *,
        phase: OwnerlessCloseoutPhase | None = None,
        recovery_state: OwnerlessCloseoutRecoveryState | None = None,
    ) -> None:
        super().__init__(gap)
        if (phase is None) != (recovery_state is None):
            message = "ownerless closeout error state must be complete"
            raise ValueError(message)
        self.phase = phase
        self.recovery_state = recovery_state

    @property
    def reservation_visible(self) -> bool:
        """Return whether the error is bound to a durable reservation."""
        return self.phase is not None


@dataclass(frozen=True, slots=True)
class OwnerlessCloseoutPostconditionContext:
    """Exact immutable facts required for one ownerless postcondition check."""

    root: Path
    database: Path
    decision_path: Path
    decision_sha256: str
    observation: LaneObservation
    accepted_branch: str
    accepted_head: str


def retire_clean_ownerless_cas(
    *,
    root: Path,
    observation: LaneObservation,
    accepted_branch: str,
    accepted_head: str,
) -> None:
    """Remove without force, verify accepted, then exact-delete the target ref."""
    try:
        remove = run_git(root, "worktree", "remove", observation.path, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        raise _classified_transition(root, observation, allow_no_effect=True) from error
    if remove.returncode:
        raise _classified_transition(root, observation, allow_no_effect=True)
    if ref_head(root, accepted_branch) != accepted_head:
        classified = _classified_transition(root, observation, allow_no_effect=False)
        raise OwnerlessCloseoutError(
            _OWNERLESS_ACCEPTED_HEAD_STALE,
            phase=classified.phase,
            recovery_state=classified.recovery_state,
        )
    accepted_ref = f"refs/heads/{accepted_branch}"
    target_ref = f"refs/heads/{observation.lane_ref}"
    commands = (
        "start\n"
        f"update {accepted_ref} {accepted_head} {accepted_head}\n"
        f"delete {target_ref} {observation.head}\n"
        "prepare\ncommit\n"
    )
    try:
        result = run_git(root, "update-ref", "--stdin", check=False, stdin=commands)
    except (OSError, subprocess.SubprocessError) as error:
        raise _classified_transition(root, observation, allow_no_effect=False) from error
    if result.returncode or result.stdout != "start: ok\nprepare: ok\ncommit: ok\n":
        raise _classified_transition(root, observation, allow_no_effect=False)


def _classified_transition(
    root: Path, observation: LaneObservation, *, allow_no_effect: bool
) -> OwnerlessCloseoutError:
    ref_state, oid = probe_ownerless_ref(root, observation.lane_ref)
    registration = probe_ownerless_worktree_registration(root, observation.path)
    path_state = probe_ownerless_path(observation.path)
    ref_intact = ref_state == "oid" and oid == observation.head
    if allow_no_effect and ref_intact and registration == "present" and path_state == "present":
        return OwnerlessCloseoutError(
            _gap("worktree_remove_failed"),
            phase="reserved",
            recovery_state="reserved_no_effect",
        )
    if ref_intact and registration == "absent" and path_state == "absent":
        return OwnerlessCloseoutError(
            _gap("worktree_removed_ref_present"),
            phase="effect",
            recovery_state="worktree_removed_ref_present",
        )
    return OwnerlessCloseoutError(
        _gap("transition_unknown"),
        phase="unknown",
        recovery_state="transition_unknown",
    )


def probe_ownerless_ref(root: Path, branch: str) -> tuple[str, str]:
    """Return an exact ref OID, explicit absence, or unverifiable state."""
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


def probe_ownerless_worktree_registration(root: Path, path: str) -> str:
    """Return present, absent, or unverifiable for one exact registration."""
    try:
        result = run_git(root, "worktree", "list", "--porcelain", "-z", check=False)
    except (OSError, subprocess.SubprocessError):
        return "unverifiable"
    if result.returncode or result.stderr or not isinstance(result.stdout, str):
        return "unverifiable"
    records = _strict_worktree_records(result.stdout)
    if records is None or not _absolute_worktree_path(path):
        return "unverifiable"
    return "present" if any(record["worktree"] == path for record in records) else "absent"


def _strict_worktree_records(output: str) -> tuple[dict[str, str], ...] | None:
    if not output or not output.endswith("\0\0"):
        return None
    records: list[dict[str, str]] = []
    paths: set[str] = set()
    for raw_record in output[:-2].split("\0\0"):
        record = _parse_worktree_record(raw_record)
        if record is None or not _valid_worktree_registration(record, paths):
            return None
        paths.add(record["worktree"])
        records.append(record)
    return tuple(records)


def _parse_worktree_record(raw_record: str) -> dict[str, str] | None:
    fields = raw_record.split("\0")
    if not fields or any(not field for field in fields):
        return None
    record: dict[str, str] = {}
    for field in fields:
        key, separator, value = field.partition(" ")
        if key not in _WORKTREE_ALLOWED_FIELDS or key in record:
            return None
        if key in _WORKTREE_VALUE_FIELDS and (not separator or not value):
            return None
        if key in _WORKTREE_MARKER_FIELDS and separator:
            return None
        record[key] = value
    return record


def _valid_worktree_registration(record: dict[str, str], paths: set[str]) -> bool:
    raw_path = record.get("worktree", "")
    head = record.get("HEAD", "")
    branch = record.get("branch", "")
    registration_kinds = int(bool(branch)) + int("detached" in record) + int("bare" in record)
    return (
        _absolute_worktree_path(raw_path)
        and raw_path not in paths
        and _valid_oid(head)
        and registration_kinds == 1
        and (
            not branch
            or (branch.startswith("refs/heads/") and bool(branch.removeprefix("refs/heads/")))
        )
    )


def _absolute_worktree_path(raw: str) -> bool:
    path = Path(raw)
    return bool(raw) and path.is_absolute() and ".." not in path.parts


def _valid_oid(value: str) -> bool:
    return len(value) in {40, 64} and set(value) <= set("0123456789abcdef")


def probe_ownerless_path(path: str) -> str:
    """Return present or absent without treating dangling symlinks as absent."""
    try:
        return "present" if os.path.lexists(path) else "absent"
    except OSError:
        return "unverifiable"


def verify_ownerless_postconditions(
    *,
    context: OwnerlessCloseoutPostconditionContext,
    fence: dict[str, object] | None,
    decision_bytes: bytes | None = None,
) -> dict[str, object]:
    """Verify exact ref, registration, path, coordination, decision, and fence state."""
    root = context.root
    observation = context.observation
    target_ref_state, _ = probe_ownerless_ref(root, observation.lane_ref)
    registration_state = probe_ownerless_worktree_registration(root, observation.path)
    path_state = probe_ownerless_path(observation.path)
    fence_state, current_fence = probe_closeout_fence(
        context.database, subject=observation.lane_ref
    )
    try:
        coordinated = observation.lane_ref in leases_by_branch(root)
    except (OSError, RuntimeError, TypeError, ValueError):
        coordinated = True
    checks = {
        "target_ref_absent": target_ref_state == "absent",
        "worktree_registration_absent": registration_state == "absent",
        "target_path_absent": path_state == "absent",
        "accepted_head_unchanged": (
            ref_head(root, context.accepted_branch) == context.accepted_head
        ),
        "coordination_absent": not coordinated,
        "decision_unchanged": (
            hashlib.sha256(decision_bytes).hexdigest()
            if decision_bytes is not None
            else _path_digest(context.decision_path)
        )
        == context.decision_sha256,
        "fence_unchanged": fence_state == ("absent" if fence is None else "present")
        and current_fence == fence,
    }
    failed = next((name for name, ok in checks.items() if not ok), "")
    if failed:
        raise OwnerlessCloseoutError(
            _gap(f"postcondition_failed:{failed}"),
            phase="postcondition",
            recovery_state="postcondition_failed",
        )
    return checks


def ref_head(root: Path, branch: str) -> str:
    """Return one exact branch OID or an empty string for non-OID states."""
    state, oid = probe_ownerless_ref(root, branch)
    return oid if state == "oid" else ""


def _path_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _gap(suffix: str) -> str:
    return f"lane_resolution_ownerless_{suffix}"


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


def _preservation_package_path(artifact_root: Path, decision_id: str) -> Path | None:
    if not is_lane_decision_id(decision_id):
        return None
    candidate = artifact_root / decision_id
    return candidate if record_path_is_safe(artifact_root, candidate) else None


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
    package_path = _preservation_package_path(artifact_root, str(decision.get("decision_id") or ""))
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
    write_git_preservation_payloads(
        source=source,
        bundle=bundle,
        tracked_patch=patch,
        index_patch=index_patch,
        lane_ref=observation.lane_ref,
    )
    inventory = untracked_files(source)
    if inventory is None:
        raise ValueError(_OWNERLESS_UNTRACKED_INVENTORY_FAILED)
    if inventory:
        write_untracked_archive(source=source, archive=archive, inventory=inventory)
    manifest = {
        "package_format_version": "v2",
        "decision_id": decision["decision_id"],
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        "observation_digest": observation.digest(),
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "index_patch_sha256": hashlib.sha256(index_patch.read_bytes()).hexdigest(),
        "untracked_archive_sha256": (
            hashlib.sha256(archive.read_bytes()).hexdigest() if archive.is_file() else ""
        ),
        "source_lease_transferred": False,
    }
    manifest_path = package / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "path": display_record_path(root, package),
        "manifest": manifest,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }


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
                raise ValueError(_OWNERLESS_BRANCH_DELETE_FAILED)
            stdin.write("start\n")
            stdin.flush()
            started = stdout.readline() == "start: ok\n"
            stdin.write(f"delete {ref} {observation.head}\nprepare\n")
            stdin.flush()
            prepared = stdout.readline() == "prepare: ok\n"
            if not (started and prepared):
                stdin.write("abort\n")
                stdin.close()
                raise ValueError(_OWNERLESS_BRANCH_DELETE_FAILED)
            remove = ("worktree", "remove", *(("--force",) if force else ()), observation.path)
            if run_git(root, *remove, check=False).returncode:
                stdin.write("abort\n")
                stdin.close()
                raise ValueError(_OWNERLESS_WORKTREE_REMOVE_FAILED)
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
