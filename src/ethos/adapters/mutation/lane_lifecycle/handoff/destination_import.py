"""Destination transaction for cross-host Work Lane handoff imports."""

from __future__ import annotations

import os
import sqlite3
import subprocess
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.lane_lifecycle.handoff.destination_cleanup import (
    compensate_failed_import,
)
from ethos.adapters.mutation.lane_lifecycle.handoff.destination_cleanup import (
    import_worktree_record,
)
from ethos.adapters.mutation.lane_lifecycle.handoff.destination_objects import import_objects
from ethos.adapters.mutation.lane_lifecycle.handoff.destination_objects import install_pack
from ethos.adapters.mutation.lane_lifecycle.handoff.package import lease_binding
from ethos.adapters.mutation.lane_lifecycle.handoff.package import require
from ethos.adapters.mutation.lane_lifecycle.handoff.package import validated_handoff_acknowledgement
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.lifecycle.transitions import expected_current_lease
from ethos.adapters.store.state.lease.projection import LeaseObservation
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from pathlib import Path


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
    observed = observe_lease(state_database(destination), branch)
    lease = _recover_import_lease(observed, target_holder_ref)
    compensate_on_failure = observed.state == "missing"
    with import_objects(destination, package, manifest) as (object_environment, prepared_pack):
        try:
            lease, compensate_on_failure = _acquire_or_recover_lease(
                destination,
                manifest,
                target_holder_ref,
                worktree_path,
            )
            _ensure_import_ref(
                destination,
                branch,
                head,
                lease,
                target_holder_ref,
                object_environment,
            )
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
            object_attestation = install_pack(
                destination,
                prepared_pack,
                commitment_digest=None,
                head=head,
                repository_id=repository_identity(destination),
            )
        except (OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError, ValueError):
            if compensate_on_failure:
                lease = lease or _recover_import_lease(
                    observe_lease(state_database(destination), branch), target_holder_ref
                )
            if lease and compensate_on_failure:
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
        "object_attestation": object_attestation,
    }


def _recover_import_lease(
    observed: LeaseObservation,
    target_holder_ref: str,
) -> dict[str, Any]:
    if observed.state == "missing":
        return {}
    record = observed.record()
    require(
        (
            "handoff_import_lease_unknown"
            if observed.state == "unknown"
            else "handoff_import_lease_conflict"
        ),
        holds=observed.state in {"valid", "expired"}
        and record.get("holder_ref") == target_holder_ref,
    )
    return record


def _acquire_or_recover_lease(
    destination: Path,
    manifest: dict[str, Any],
    target_holder_ref: str,
    worktree_path: Path,
) -> tuple[dict[str, Any], bool]:
    branch = str(manifest["source_lane_ref"])
    observed = observe_lease(state_database(destination), branch)
    if observed.state != "missing":
        recovered = _recover_import_lease(observed, target_holder_ref)
        if observed.state == "expired":
            return _resume_import_lease(destination, manifest, target_holder_ref, recovered), False
        return recovered, False
    ref = run_git(
        destination,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{branch}",
        check=False,
    )
    require("handoff_destination_carrier_state_unknown", holds=ref.returncode in {0, 1})
    try:
        worktree = import_worktree_record(destination, worktree_path, run_git=run_git)
    except ValueError:
        message = "handoff_destination_carrier_state_unknown"
        raise ValueError(message) from None
    require(
        "handoff_destination_orphan_carrier",
        holds=ref.returncode == 1 and not os.path.lexists(worktree_path) and not worktree,
    )
    now = datetime.now(UTC)
    return (
        acquire_lease(
            state_database(destination),
            lease=LaneLease(
                lane_ref=branch,
                holder_ref=HolderRef.parse(target_holder_ref),
                generation=1,
                expires_at=now + timedelta(days=1),
            ),
        ),
        True,
    )


def _resume_import_lease(
    destination: Path,
    manifest: dict[str, Any],
    holder_ref: str,
    lease: dict[str, Any],
) -> dict[str, Any]:
    return apply_lease_operation(
        state_database(destination),
        request=LeaseOperationRequest(
            operation="resume",
            branch=str(manifest["source_lane_ref"]),
            holder_ref=holder_ref,
            generation=int(lease["generation"]),
            expires_at=str(lease["expires_at"]),
            apply=True,
            ttl_seconds=86_400,
        ),
    )


def _ensure_import_ref(
    destination: Path,
    branch: str,
    head: str,
    lease: dict[str, Any],
    target_holder_ref: str,
    object_environment: dict[str, str],
) -> None:
    ref = f"refs/heads/{branch}"
    observed = run_git(
        destination, "rev-parse", "--verify", ref, check=False, env=object_environment
    )
    require("handoff_destination_ref_conflict", holds=observed.returncode in {0, 128})
    if observed.returncode == 0:
        require("handoff_destination_ref_conflict", holds=observed.stdout.strip() == head)
        return
    effect = GitEffect(updates={ref: GitRefUpdate(expected="0" * len(head), desired=head)})
    plan = compile_observed_git_effect(
        destination,
        None,
        effect,
        head=run_git(destination, "rev-parse", "HEAD").stdout.strip(),
        prior_attestations={},
        policy={
            "operation": "lane.import",
            "branch": branch,
            "holder_ref": target_holder_ref,
            "execution_branch": run_git(destination, "branch", "--show-current").stdout.strip(),
        },
        values={"lease_generation": lease_generation(lease)},
        environment=object_environment,
    )
    execute_git_effect(
        destination,
        plan,
        issuer=target_holder_ref,
        environment=object_environment,
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
        require(
            "handoff_destination_worktree_conflict",
            holds=not path.is_symlink()
            and path.is_dir()
            and record.get("branch") == branch
            and record.get("HEAD") == head
            and not any(flag in record for flag in ("locked", "prunable")),
        )
        return
    require("handoff_destination_path_exists", holds=not os.path.lexists(path))
    add_worktree(
        destination,
        path,
        branch=branch,
        head=head,
        environment=object_environment,
        runner=run_git,
    )


def _verify_destination_identity(
    destination: Path,
    worktree: Path,
    manifest: dict[str, Any],
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
    )
    require(
        "handoff_destination_identity_drift",
        holds=actual == (head, head, tree),
    )


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
            object_environment=object_environment,
        )
        return validated_handoff_acknowledgement(
            root=destination,
            manifest=manifest,
            lease=lease,
        )
