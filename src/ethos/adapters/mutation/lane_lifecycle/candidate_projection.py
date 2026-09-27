"""Create and synchronize the local candidate branch projection."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.start import default_worktree_path
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_ref_worktrees import sync_ref_worktrees
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan

if TYPE_CHECKING:
    from collections.abc import Mapping


def _report(
    branch: str, head: str, state: str, gaps: list[str], **details: object
) -> dict[str, object]:
    return {
        key: value
        for key, value in {
            "verdict": "block" if gaps else "pass",
            "state": state,
            "branch": branch,
            "head": head,
            "required_gaps": gaps,
            **details,
        }.items()
        if value not in ("", None)
    }


def _candidate_plan(
    *,
    root: Path,
    accepted_branch: str,
    candidate_branch: str,
    expected: str,
    desired: str,
    operation: str,
) -> TransitionPlan:
    effect = GitEffect(
        updates={
            f"refs/heads/{candidate_branch}": GitRefUpdate(expected=expected, desired=desired)
        },
        assertions={f"refs/heads/{accepted_branch}": desired},
    )
    return compile_observed_git_effect(
        root,
        None,
        effect,
        head=desired,
        prior_attestations={},
        policy={"operation": operation, "subject": candidate_branch},
    )


def _recovery_plan(root: Path, accepted: str, candidate: str, desired: str, operation: str):
    return recover_plan(
        root=root,
        ref_name=f"refs/heads/{candidate}",
        operation=operation,
        desired=desired,
        assertions={f"refs/heads/{accepted}": desired},
    )


def _add_candidate_worktree(root: Path, path: Path, branch: str) -> None:
    head = run_git(root, "rev-parse", branch).stdout.strip()
    add_worktree(root, path, branch=branch, head=head)
    install_hook_launchers(path)


def _candidate_target(requested: Path) -> tuple[Path, str, str]:
    """Keep the requested leaf distinct from its physical parent and collisions."""
    try:
        parent = requested.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        parent = requested.parent
    target = parent / requested.name
    if not parent.is_dir():
        return (
            target,
            "candidate_worktree_parent_unsafe",
            f"Choose an existing directory for the candidate worktree parent: {parent}",
        )
    if requested.is_symlink() or target.exists() or target.is_symlink():
        return (
            target,
            "candidate_worktree_path_exists",
            f"Inspect {target} and preserve its content before choosing another path",
        )
    return target, "", ""


def _accepted_head(repo: Path) -> str:
    """Observe a candidate base without treating an unborn HEAD as an exception."""
    observed = run_git(repo, "rev-parse", "HEAD", check=False, observation=True)
    return observed.stdout.strip() if observed.returncode == 0 else ""


def _head_recovery_action(repo: Path, accepted_branch: str) -> str:
    """Keep unavailable accepted HEAD recovery ahead of candidate effects."""
    return (
        f"Create or repair the first commit on {accepted_branch}; "
        f"then ethos status --root {shlex.quote(repo.as_posix())} --json"
    )


def _bootstrap_preflight(
    repo: Path,
    policy: BranchRolePolicy,
    status: Mapping[str, object],
    head: str,
    expect_head: str | None,
    details: Mapping[str, object],
) -> dict[str, object] | None:
    """Refuse a missing accepted base or mismatched candidate precondition."""
    gap = (
        "accepted_head_unavailable"
        if not head
        else "candidate_bootstrap_requires_clean_accepted_root"
        if status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]
        else "expect_head_mismatch"
        if expect_head is not None and expect_head != head
        else ""
    )
    if not gap:
        return None
    if gap == "accepted_head_unavailable":
        details = dict(details) | {
            "next_action": _head_recovery_action(repo, policy.accepted_branch),
            "user_decision_required": True,
        }
    return _report(policy.candidate_branch, head, "blocked", [gap], **details)


def _candidate_facts(
    repo: Path, observed_status: Mapping[str, object] | None, *, apply: bool
) -> tuple[Mapping[str, object], str]:
    """Reuse one preview snapshot but require fresh effect-time observation."""
    if observed_status is None:
        return workspace_status(repo), _accepted_head(repo)
    if apply:
        message = "candidate_snapshot_preview_only"
        raise ValueError(message)
    if Path(str(observed_status.get("root") or "")).resolve() != repo:
        message = "candidate_snapshot_root_mismatch"
        raise ValueError(message)
    return observed_status, str(observed_status.get("head") or "")


def bootstrap_candidate(
    *,
    root: Path,
    path: Path | None = None,
    expect_head: str | None = None,
    apply: bool = False,
    observed_status: Mapping[str, object] | None = None,
) -> dict[str, object]:
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    status, head = _candidate_facts(repo, observed_status, apply=apply)
    issuer = os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"
    requested = (path or default_worktree_path(repo, policy.candidate_branch)).absolute()
    target, path_gap, path_action = _candidate_target(requested)
    status_action = f"ethos status --root {shlex.quote(repo.as_posix())} --json"
    start_action = "ethos lane start --help"
    apply_action = (
        "ethos lane candidate "
        f"--path {shlex.quote(target.as_posix())} --expect-head {head} "
        f"--apply --root {shlex.quote(repo.as_posix())} --json"
    )
    details = {"path": target.as_posix(), "next_action": status_action}
    refusal = _bootstrap_preflight(repo, policy, status, head, expect_head, details)
    if refusal is not None:
        return refusal
    candidate = cast("dict[str, object]", status["candidate"])
    if candidate["exists"] and candidate["worktree_exists"]:
        gaps: list[str] = []
        if apply:
            try:
                plan = _recovery_plan(
                    repo,
                    policy.accepted_branch,
                    policy.candidate_branch,
                    head,
                    "candidate.bootstrap",
                )
                if plan is not None:
                    execute_git_effect(repo, plan, issuer=issuer)
                install_hook_launchers(Path(str(candidate["worktree_path"])))
            except ValueError as error:
                gaps.append(str(error))
        return _report(
            policy.candidate_branch,
            head,
            "blocked" if gaps else "present",
            gaps,
            path=str(candidate["worktree_path"]),
            next_action=status_action if gaps else start_action,
            user_decision_required=not gaps,
        )
    if not apply or path_gap:
        return _report(
            policy.candidate_branch,
            head,
            "blocked" if path_gap else "planned",
            [path_gap] if path_gap else [],
            **(
                details
                | {
                    "next_action": path_action or apply_action,
                    "user_decision_required": True,
                }
            ),
        )
    operation = "candidate.bootstrap"
    try:
        plan = (
            _recovery_plan(repo, policy.accepted_branch, policy.candidate_branch, head, operation)
            if candidate["exists"]
            else _candidate_plan(
                root=repo,
                accepted_branch=policy.accepted_branch,
                candidate_branch=policy.candidate_branch,
                expected="0" * len(head),
                desired=head,
                operation=operation,
            )
        )
        if plan is None:
            return _report(
                policy.candidate_branch,
                head,
                "blocked",
                ["git_effect_recovery_unproven"],
                **details,
            )
        execute_git_effect(repo, plan, issuer=issuer)
        _add_candidate_worktree(repo, target, policy.candidate_branch)
    except (OSError, ValueError) as error:
        ref = run_git(repo, "rev-parse", policy.candidate_branch, check=False)
        gap = (
            "candidate_worktree_add_failed"
            if ref.returncode == 0 and ref.stdout.strip() == head
            else "candidate_ref_creation_failed"
        )
        if str(error).startswith("git_effect_recovery_"):
            gap = str(error)
        return _report(
            policy.candidate_branch, head, "blocked", [gap], stderr=str(error), **details
        )
    return _report(
        policy.candidate_branch,
        head,
        "bootstrapped",
        [],
        **(details | {"next_action": start_action, "user_decision_required": True}),
    )


def _sync_candidate_worktree(
    root: Path, path: Path, branch: str, ref_head: str, previous: str, desired: str
) -> None:
    paths = (path,)
    gap = worktree_sync_gap(root, paths, branch, ref_head, previous, desired)
    if gap:
        if worktree_sync_gap(root, paths, branch, ref_head, desired, desired):
            raise ValueError(gap)
        return
    result = cast(
        "list[dict[str, str]]",
        sync_ref_worktrees(root, paths, branch, desired, previous)["worktrees"],
    )[0]
    if result["state"] != "synced":
        raise ValueError(result["stderr"] or "candidate_worktree_sync_failed")


def refresh_candidate_from_accepted(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    head = _accepted_head(repo)
    issuer = os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"
    candidate = cast("dict[str, object]", status["candidate"])
    previous = str(candidate.get("head") or "")
    path = Path(str(candidate.get("worktree_path") or ""))
    details = {"previous_head": previous, "path": str(path)}
    status_action = f"ethos status --root {shlex.quote(repo.as_posix())} --json"
    refresh_action = (
        "ethos lane candidate --refresh-from-accepted --apply --authorize "
        f"--expect-head {head} --root {shlex.quote(repo.as_posix())} --json"
    )
    start_action = "ethos lane start --help"
    gaps = [
        gap
        for gap, present in (
            ("accepted_head_unavailable", not head),
            ("accepted_root_required", status["role"] != ROLE_ACCEPTED_ROOT),
            ("accepted_root_dirty", status["role"] == ROLE_ACCEPTED_ROOT and status["dirty"]),
            ("candidate_branch_missing", not candidate["exists"]),
            (
                "candidate_worktree_missing",
                candidate["exists"] and not candidate["worktree_exists"],
            ),
            ("authorization_required", apply and not authorized),
            ("expect_head_required", apply and expect_head is None),
            ("expect_head_mismatch", apply and expect_head not in {None, head}),
        )
        if present
    ]
    plan = None
    if not gaps and apply and previous == head:
        try:
            plan = _recovery_plan(
                repo, policy.accepted_branch, policy.candidate_branch, head, "candidate.refresh"
            )
        except ValueError as error:
            gaps.append(str(error))
    if not gaps:
        current_gap = worktree_sync_gap(
            repo, (path,), policy.candidate_branch, previous, previous, previous
        )
        if current_gap and plan is None:
            gap = (
                "git_effect_recovery_unproven"
                if apply and previous == head and current_gap == "worktree_index_mismatch"
                else "candidate_worktree_dirty"
            )
            gaps.append(gap)
    if gaps:
        action = (
            _head_recovery_action(repo, policy.accepted_branch)
            if "accepted_head_unavailable" in gaps
            else status_action
        )
        return _report(
            policy.candidate_branch,
            head,
            "blocked",
            gaps,
            **(details | {"next_action": action}),
        )
    if previous == head and plan is None:
        return _report(
            policy.candidate_branch,
            head,
            "base_current",
            [],
            **(details | {"next_action": start_action, "user_decision_required": True}),
        )
    if not apply:
        return _report(
            policy.candidate_branch,
            head,
            "ready_to_refresh_from_accepted",
            [],
            **(details | {"next_action": refresh_action, "user_decision_required": True}),
        )
    try:
        plan = plan or _candidate_plan(
            root=repo,
            accepted_branch=policy.accepted_branch,
            candidate_branch=policy.candidate_branch,
            expected=previous,
            desired=head,
            operation="candidate.refresh",
        )
        previous = (
            git_effect_from_plan(plan).updates[f"refs/heads/{policy.candidate_branch}"].expected
        )
        execute_git_effect(repo, plan, issuer=issuer)
        _sync_candidate_worktree(repo, path, policy.candidate_branch, head, previous, head)
    except (OSError, ValueError) as error:
        message = str(error)
        gap = (
            message
            if previous == head and message.startswith(("git_effect_recovery_", "candidate_"))
            else "candidate_worktree_dirty"
            if previous == head
            else "candidate_refresh_from_accepted_failed"
        )
        return _report(policy.candidate_branch, head, "blocked", [gap], stderr=message, **details)
    return _report(
        policy.candidate_branch,
        head,
        "refreshed_from_accepted",
        [],
        **(details | {"next_action": start_action, "user_decision_required": True}),
    )
