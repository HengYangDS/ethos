"""Exact missing-to-owned coordination without retained-content mutation."""

from __future__ import annotations

import hashlib
import os
import shlex
import sqlite3
import subprocess
from dataclasses import asdict
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.workspace import worktree_records
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_or_recognize_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_text
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.semantic import canonical_json_digest


def _require_reacquire(*, condition: bool, gap: str) -> None:
    if not condition:
        raise ValueError(gap)


def _reacquire_coordinates(root: Path, path: Path) -> dict[str, str]:
    repo, target = repository_root(root), path.resolve()
    records = worktree_records(repo, current_path=repo, policy=BranchRolePolicy())
    controls = []
    for row in records:
        try:
            declared = run_git(
                repo,
                "ls-tree",
                "--name-only",
                row["head"],
                "--",
                ".ethos/workspace.toml",
                observation=True,
            ).stdout
            policy = (
                strict_branch_role_policy_from_text(
                    committed_file_text(repo, row["head"], ".ethos/workspace.toml")
                )
                if declared
                else BranchRolePolicy()
            )
        except ValueError:
            continue
        if row["branch"] == policy.accepted_branch:
            controls.append((Path(row["path"]).resolve(), row["head"], policy))
    _require_reacquire(
        condition=len(controls) == 1,
        gap="lease_reacquire_control_root_unavailable",
    )
    control, control_head, policy = controls[0]
    records = worktree_records(control, current_path=control, policy=policy)
    matching = [row for row in records if Path(row["path"]).resolve() == target]
    _require_reacquire(
        condition=len(matching) == 1 and target.is_dir(), gap="lease_reacquire_worktree_not_linked"
    )
    lane = matching[0]
    _require_reacquire(
        condition=lane["role"] == ROLE_WORK_LANE, gap="lease_reacquire_work_lane_required"
    )
    _require_reacquire(condition=lane["locked"] == "false", gap="lease_reacquire_worktree_locked")
    _require_reacquire(
        condition=git_common_dir(target) == git_common_dir(control),
        gap="lease_reacquire_common_directory_mismatch",
    )
    _require_reacquire(
        condition=current_branch(target) == lane["branch"], gap="lease_reacquire_branch_drift"
    )
    indexed = run_git(target, "ls-files", "--stage", "-z", text=False, observation=True).stdout
    return {
        "control_root": control.as_posix(),
        "control_head": current_head(control),
        "policy_digest": canonical_json_digest(asdict(policy)),
        "repository": repository_identity(control, tree_ref=control_head),
        "common_directory": git_common_dir(control),
        "path": target.as_posix(),
        "branch": lane["branch"],
        "head": current_head(target),
        "tree": current_tree(target),
        "index_sha256": hashlib.sha256(indexed).hexdigest(),
        "dirty_content_sha256": dirty_content_sha256(target),
    }


def reacquire_lease(
    *,
    root: Path,
    path: Path,
    holder_ref: str,
    expect_head: str = "",
    expect_snapshot: str = "",
    expires_at: str = "",
    authorize: bool = False,
    apply: bool = False,
) -> dict[str, object]:
    """Acquire missing coordination without replacing any retained Git content."""
    lease: dict[str, object] = {}
    coordinates: dict[str, str] = {}
    derive_command = (
        "ethos",
        "lane",
        "lease",
        "reacquire",
        "--path",
        str(path),
        "--holder-ref",
        holder_ref,
        "--root",
        str(root),
        "--json",
    )
    continuation = shlex.join(derive_command)
    committed = False
    try:
        holder = HolderRef.parse(holder_ref)
        _require_reacquire(
            condition=os.environ.get("ETHOS_ACTOR", "").strip() == holder.serialize(),
            gap="lease_reacquire_actor_mismatch",
        )
        coordinates = _reacquire_coordinates(root, path)
        now = datetime.now(UTC)
        expected_lease = LaneLease(
            lane_ref=coordinates["branch"],
            holder_ref=holder,
            generation=1,
            expires_at=datetime.fromisoformat(expires_at)
            if expires_at
            else now + timedelta(days=1),
        )
        _require_reacquire(
            condition=(not apply or bool(expires_at))
            and now < expected_lease.expires_at <= now + timedelta(days=1),
            gap="lease_reacquire_expiry_invalid",
        )
        snapshot = canonical_json_digest(
            {"coordinates": coordinates, "lease": expected_lease.to_payload()}
        )

        def recheck() -> None:
            _require_reacquire(
                condition=coordinates == _reacquire_coordinates(root, path)
                and os.environ.get("ETHOS_ACTOR", "").strip() == holder.serialize(),
                gap="lease_reacquire_snapshot_drift",
            )

        recheck()
        database = state_database(Path(coordinates["control_root"]))
        observed = observe_lease(database, coordinates["branch"])
        _require_reacquire(
            condition=observed.state == "missing"
            or (observed.state == "valid" and observed.lease == expected_lease),
            gap=f"lease_reacquire_existing_lease:{observed.state}",
        )
        _require_reacquire(condition=not apply or authorize, gap="authorization_required")
        _require_reacquire(
            condition=not apply
            or (expect_head == coordinates["head"] and expect_snapshot == snapshot),
            gap="lease_reacquire_snapshot_drift",
        )
        continuation = shlex.join(
            (
                *derive_command,
                "--expect-head",
                coordinates["head"],
                "--expect-snapshot",
                snapshot,
                "--expires-at",
                expected_lease.expires_at.isoformat(),
                "--authorize",
                "--apply",
            )
        )
        if not apply:
            return {
                "verdict": "pass",
                "state": "planned",
                "head": coordinates["head"],
                "snapshot": snapshot,
                "expires_at": expected_lease.expires_at.isoformat(),
                "coordinates": coordinates,
                "required_gaps": [],
                "next_action": continuation,
            }
        lease, recognized = acquire_or_recognize_lease(
            database,
            lease=expected_lease,
            recheck=recheck,
        )
        committed = True
        control = Path(coordinates["control_root"])
        after = {"coordinates": coordinates, "lease": lease}
        attestation = next(
            (
                item
                for item in read_attestation_set(control)[1]
                if item.predicate == "lane-resolution:reacquire"
                and item.verdict == "pass"
                and item.payload.body.get("repository") == coordinates["repository"]
                and item.payload.body.get("output") == after
            ),
            None,
        )
        if attestation is None:
            attestation = issue_native_effect(
                control,
                effect=NativeEffect(
                    predicate="lane-resolution:reacquire",
                    operation="reacquire",
                    command=("ethos", "lane", "lease", "reacquire"),
                    subject={"branch": coordinates["branch"]},
                    before={"coordinates": coordinates, "lease_state": observed.state},
                    after=after,
                ),
                state="recognized" if recognized else "applied",
                commitment_digest=None,
                repository_id=coordinates["repository"],
            )
            record_attestations(control, (attestation,))
        return {
            "verdict": "pass",
            "state": "recognized" if recognized else "acquired",
            "lease": lease,
            "attestation": attestation.model_dump(mode="json"),
            "head": coordinates["head"],
            "snapshot": snapshot,
            "required_gaps": [],
            "next_action": shlex.join(("ethos", "status", "--root", str(path), "--json")),
        }
    except (OSError, sqlite3.Error, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        unknown = not isinstance(error, ValueError)
        if str(error).startswith("state_schema_"):
            continuation = shlex.join(("ethos", "hook", "install", "--root", str(root), "--json"))
        return {
            "verdict": "unknown" if unknown else "block",
            "state": "partial_transition" if committed else "blocked",
            "lease": lease if committed else {},
            "coordinates": coordinates,
            "required_gaps": [str(error)],
            "next_action": continuation,
        }
