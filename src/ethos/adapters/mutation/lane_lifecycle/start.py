"""Start one owned Work Lane from the exact candidate object."""

from __future__ import annotations

import os
import re
import shlex
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.carriers import openspec_carrier_gaps
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.runtime.materialization.input_resolution import (
    require_runtime_wheel_provenance,
)
from ethos.adapters.repo.runtime.selection import runtime_command
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.adapters.repo.worktree_effects import remove_worktree
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip().lower()).strip("-") or "work"


def default_worktree_path(repo: Path, branch: str) -> Path:
    """Return the default sibling worktree path for one branch."""
    return repo.with_name(f"{repo.name}-{_slug(branch)}")


def _target(
    repo: Path,
    policy: BranchRolePolicy,
    *,
    name: str,
    path: Path | None,
    observed_at: datetime,
) -> tuple[str, Path, dict[str, object] | None]:
    if not policy.canonical_sibling_worktrees:
        branch = policy.work_branch(_slug(name))
        return branch, (path or default_worktree_path(repo, branch)).resolve(), None
    lane_id = f"{observed_at.astimezone(UTC):%Y%m%d}-{_slug(name)}"
    branch = f"work/{lane_id}"
    target = (repo.parent / f"{repo.name}-worktrees" / lane_id).resolve()
    if policy.work_branch_prefix != "work/":
        return (
            branch,
            target,
            _blocked(branch, target, "repository_family_profile_requires_work_branch_prefix"),
        )
    if path is not None and path.resolve() != target:
        return (
            branch,
            target,
            _blocked(
                branch,
                target,
                "work_lane_path_not_canonical",
                supplied_path=path.resolve().as_posix(),
            ),
        )
    return branch, target, None


def _candidate_gap(repo: Path, candidate: dict[str, object]) -> tuple[str, dict[str, object]]:
    if not candidate["exists"]:
        return "candidate_branch_missing", {}
    if not candidate["worktree_exists"]:
        return "candidate_worktree_missing", {}
    candidate_path = Path(str(candidate["worktree_path"]))
    branch = str(candidate["branch"])
    head = str(candidate["head"])
    checks = (
        ("candidate_worktree_dirty", bool(changed_paths(candidate_path))),
        ("candidate_head_changed_during_lane_start", ref_head(repo, branch) != head),
        (
            "candidate_worktree_head_changed_during_lane_start",
            run_git(candidate_path, "rev-parse", "HEAD", check=False).stdout.strip() != head,
        ),
    )
    if gap := next((name for name, failed in checks if failed), ""):
        return gap, {}
    gaps = openspec_carrier_gaps(candidate_path, "candidate")
    return (gaps[0], {}) if gaps else ("", {})


def _admit(
    repo: Path, *, branch: str, target: Path
) -> tuple[dict[str, object], dict[str, object] | None]:
    status = workspace_status(repo)
    if status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]:
        return {}, _blocked(
            branch,
            target,
            "lane_start_requires_clean_accepted_root",
            role=status["role"],
            dirty=status["dirty"],
        )
    candidate = cast("dict[str, object]", status["candidate"])
    gap, details = _candidate_gap(repo, candidate)
    if gap:
        return {}, _blocked(branch, target, gap, **details)
    head = str(candidate["head"])
    current_ref = ref_head(repo, branch)
    if current_ref and current_ref != head:
        return {}, _blocked(branch, target, "lane_start_target_ref_exists")
    if os.path.lexists(target):
        listed = run_git(repo, "worktree", "list", "--porcelain", check=False).stdout
        expected = f"worktree {target}\nHEAD {head}\nbranch refs/heads/{branch}\n"
        if expected not in f"{listed}\n":
            return {}, _blocked(branch, target, "lane_start_target_path_exists")
    return candidate, None


def _lease(repo: Path, branch: str, holder_ref: str) -> dict[str, object]:
    observation = observe_lease(state_database(repo), branch)
    if observation.state != "missing":
        record = observation.record()
        if observation.state != "valid":
            msg = f"work_lane_lease_{observation.state}:{branch}"
            raise ValueError(msg)
        if record.get("holder_ref") != holder_ref:
            msg = f"lease_holder_mismatch:{branch}"
            raise ValueError(msg)
        return record
    now = datetime.now(UTC)
    return acquire_lease(
        state_database(repo),
        lease=LaneLease(
            lane_ref=branch,
            holder_ref=HolderRef.parse(holder_ref),
            generation=1,
            expires_at=now + timedelta(days=1),
        ),
    )


def _revoke_started_lease(repo: Path, *, branch: str, holder_ref: str, generation: int) -> bool:
    database = state_database(repo)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("begin immediate")
        cursor = connection.execute(
            "delete from leases where lane_ref = ? and holder_ref = ? and generation = ?",
            (branch, holder_ref, generation),
        )
        connection.commit()
    return cursor.rowcount == 1


def _rollback_start(
    repo: Path,
    *,
    policy: BranchRolePolicy,
    branch: str,
    target: Path,
    head: str,
    holder_ref: str,
    lease: dict[str, object] | None,
    ref_created: bool,
) -> list[str]:
    gaps: list[str] = []
    if os.path.lexists(target):
        try:
            remove_worktree(repo, target, branch=branch, head=head, force=True)
        except ValueError:
            gaps.append("lane_start_worktree_cleanup_failed")
    if lease is not None and not _revoke_started_lease(
        repo,
        branch=branch,
        holder_ref=holder_ref,
        generation=integer_value(lease.get("generation")),
    ):
        gaps.append("lane_start_lease_cleanup_failed")
    if ref_created:
        try:
            _delete_started_ref(
                repo,
                policy=policy,
                branch=branch,
                head=head,
                holder_ref=holder_ref,
            )
        except ValueError:
            gaps.append("lane_start_ref_cleanup_failed")
    return gaps


def _create_ref(
    repo: Path,
    *,
    policy: BranchRolePolicy,
    branch: str,
    head: str,
    holder_ref: str,
):
    effect = GitEffect(
        updates={f"refs/heads/{branch}": GitRefUpdate(expected="0" * len(head), desired=head)},
        assertions={f"refs/heads/{policy.candidate_branch}": head},
    )
    plan = compile_observed_git_effect(
        repo,
        None,
        effect,
        head=head,
        prior_attestations={},
        policy={
            "operation": "lane.start",
            "subject": branch,
            "holder_ref": holder_ref,
            "candidate_branch": policy.candidate_branch,
        },
    )
    return execute_git_effect(repo, plan, issuer=holder_ref)


def _delete_started_ref(
    repo: Path,
    *,
    policy: BranchRolePolicy,
    branch: str,
    head: str,
    holder_ref: str,
) -> None:
    zero = "0" * len(head)
    effect = GitEffect(
        updates={f"refs/heads/{branch}": GitRefUpdate(expected=head, desired=zero)},
        assertions={f"refs/heads/{policy.candidate_branch}": head},
    )
    plan = compile_observed_git_effect(
        repo,
        None,
        effect,
        head=head,
        prior_attestations={},
        policy={
            "operation": "lane.start.compensate",
            "subject": branch,
            "holder_ref": holder_ref,
            "candidate_branch": policy.candidate_branch,
        },
    )
    execute_git_effect(repo, plan, issuer=holder_ref)


def _runner_bootstrap(repo: Path, target: Path) -> dict[str, str]:
    resolved = target.resolve().as_posix()
    command = runtime_command(repo)
    return {
        "command": command,
        "environment_scope": "git_common_package_runtime",
        "next_action": (f"{command} status --root {shlex.quote(resolved)} --json"),
    }


def start_work_lane(
    *,
    root: Path,
    name: str,
    path: Path | None = None,
    holder_ref: str,
    apply: bool = False,
) -> dict[str, object]:
    """Create or resume one exact candidate-based Work Lane and minimal Lease."""
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    branch, target, target_block = _target(
        repo,
        policy,
        name=name,
        path=path,
        observed_at=datetime.now(UTC),
    )
    if target_block is not None:
        return target_block | {
            "next_action": f"ethos status --root {shlex.quote(repo.as_posix())} --json"
        }
    try:
        holder_ref = HolderRef.parse(holder_ref).serialize()
    except ValueError:
        return _blocked(branch, target, "holder_ref_invalid") | {
            "next_action": "ethos lane start --help",
            "user_decision_required": True,
        }
    candidate, admission_block = _admit(repo, branch=branch, target=target)
    bootstrap: dict[str, str] = {}
    head = str(candidate.get("head") or "")
    if admission_block is None:
        try:
            bootstrap = _runner_bootstrap(repo, target)
        except ValueError as error:
            admission_block = _blocked(
                branch,
                target,
                str(error) or "hook_runtime_current_invalid",
            )
    if admission_block is not None:
        return admission_block | {
            "next_action": f"ethos status --root {shlex.quote(repo.as_posix())} --json"
        }
    if not apply:
        apply_action = (
            f"ethos lane start {shlex.quote(name)} --path {shlex.quote(target.as_posix())} "
            f"--holder-ref {shlex.quote(holder_ref)} --apply "
            f"--root {shlex.quote(repo.as_posix())} --json"
        )
        return {
            "verdict": "pass",
            "state": "planned",
            "branch": branch,
            "base": policy.candidate_branch,
            "base_head": head,
            "head": head,
            "path": target.as_posix(),
            "runner_bootstrap": bootstrap,
            "required_gaps": [],
            "next_action": apply_action,
        }
    lease: dict[str, object] | None = None
    ref_created = False
    try:
        require_runtime_wheel_provenance()
        if ref_head(repo, branch) == head:
            ref_attestation = None
        else:
            ref_attestation = _create_ref(
                repo,
                policy=policy,
                branch=branch,
                head=head,
                holder_ref=holder_ref,
            )
            ref_created = True
        lease = _lease(repo, branch, holder_ref)
        worktree_attestation = add_worktree(repo, target, branch=branch, head=head)
        hook_runtime = install_hook_launchers(target)
    except (OSError, ValueError) as error:
        cleanup_gaps = _rollback_start(
            repo,
            policy=policy,
            branch=branch,
            target=target,
            head=head,
            holder_ref=holder_ref,
            lease=lease,
            ref_created=ref_created,
        )
        return _blocked(
            branch,
            target,
            str(error) or "lane_start_failed",
            *cleanup_gaps,
            head=head,
            ref_state="present" if ref_head(repo, branch) == head else "absent",
            lease_state=observe_lease(state_database(repo), branch).state,
            next_action=(
                f"ethos lane start {name} --path {target.as_posix()} "
                f"--holder-ref {holder_ref} --apply --json"
            ),
        )
    return {
        "verdict": "pass",
        "state": "started",
        "branch": branch,
        "base": policy.candidate_branch,
        "base_head": head,
        "head": head,
        "path": target.as_posix(),
        "holder_ref": holder_ref,
        "lease": lease,
        "ref_attestation": ref_attestation.model_dump(mode="json") if ref_attestation else {},
        "worktree_attestation": worktree_attestation.model_dump(mode="json"),
        "hook_runtime": hook_runtime,
        "runner_bootstrap": bootstrap,
        "required_gaps": [],
        "next_action": bootstrap["next_action"],
    }


def _blocked(branch: str, target: Path, *gaps: str, **details: object) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        "path": target.as_posix(),
        **details,
        "required_gaps": list(gaps),
    }
