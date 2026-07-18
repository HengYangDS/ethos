from __future__ import annotations

# fmt: off
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import default_candidate_path
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.lane_lifecycle.projection_rebase.core import resolve_projection_rebase
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class LaneRefreshRuntime:
    """Explicit dependencies used for candidate and Work Lane base refresh."""

    repo_root: Callable[..., Any] = repo_root
    default_candidate_path: Callable[..., Any] = default_candidate_path
    load_branch_role_policy: Callable[..., Any] = load_branch_role_policy
    workspace_status: Callable[..., Any] = workspace_status
    changed_paths: Callable[..., Any] = changed_paths
    is_ancestor: Callable[..., Any] = is_ancestor
    run_git: Callable[..., Any] = run_git


SSH_SIGNING_TRANSPORT_TIMEOUT_SECONDS = 5.0


def _ssh_agent_has_signing_key(key: str, *, env: dict[str, str] | None = None) -> bool:
    try:
        completed = subprocess.run(
            ["ssh-add", "-T", key], check=False, text=True, capture_output=True,
            timeout=SSH_SIGNING_TRANSPORT_TIMEOUT_SECONDS, env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def ssh_signing_transport_ready(key: str) -> bool:
    """Check the inherited then GUI-projected SSH-agent transport."""
    if _ssh_agent_has_signing_key(key):
        return True
    try:
        completed = subprocess.run(
            ["launchctl", "getenv", "SSH_AUTH_SOCK"], check=False, text=True, capture_output=True,
            timeout=SSH_SIGNING_TRANSPORT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    socket = completed.stdout.strip() if completed.returncode == 0 else ""
    return bool(socket) and _ssh_agent_has_signing_key(key, env={"SSH_AUTH_SOCK": socket})


def _signing_preflight_gaps(root: Path, *, runtime: LaneRefreshRuntime) -> list[str]:
    def config(key: str) -> str:
        return str(runtime.run_git(root, "config", "--get", key, check=False).stdout).strip()

    if (config("commit.gpgsign").casefold() not in {"true", "yes", "on", "1"}
            or config("gpg.format").casefold() != "ssh"):
        return []
    key_path = Path(config("user.signingkey")).expanduser()
    key_path = key_path if key_path.is_absolute() else root / key_path
    if not key_path.is_file():
        return []
    public_key = key_path if key_path.suffix.casefold() == ".pub" else key_path.with_name(
        f"{key_path.name}.pub"
    )
    return [] if public_key.is_file() and ssh_signing_transport_ready(public_key.as_posix()) else [
        "refresh_signing_transport_unavailable"
    ]


def _ref_head(root: Path, ref: str, *, runtime: LaneRefreshRuntime) -> str:
    completed = runtime.run_git(root, "rev-parse", ref, check=False)
    return str(completed.stdout).strip() if completed.returncode == 0 else ""


def bootstrap_candidate(
    *,
    root: Path,
    path: Path | None = None,
    expect_head: str | None = None,
    apply: bool = False,
    runtime: LaneRefreshRuntime | None = None,
) -> dict[str, object]:
    active_runtime = runtime or LaneRefreshRuntime()
    repo = active_runtime.repo_root(root)
    policy = active_runtime.load_branch_role_policy(repo)
    status = active_runtime.workspace_status(repo)
    current_head = active_runtime.run_git(repo, "rev-parse", "HEAD").stdout.strip()
    target = (path or active_runtime.default_candidate_path(repo, policy.candidate_branch)
              ).resolve()

    def report(*, ok: bool, state: str, gaps: list[str], **details: object) -> dict[str, object]:
        return _refresh_report(ok=ok, state=state, branch=policy.candidate_branch,
                               head=current_head, gaps=gaps, **details)

    details = {"path": target.as_posix()}
    gaps = [gap for gap, present in (
        ("candidate_bootstrap_requires_clean_accepted_root",
         status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]),
        ("expect_head_mismatch", expect_head is not None and expect_head != current_head),
    ) if present]
    if gaps:
        return report(ok=False, state="blocked", gaps=gaps, **details)
    candidate = cast("dict[str, object]", status["candidate"])
    if candidate["exists"] and candidate["worktree_exists"]:
        return report(ok=True, state="present", gaps=[], path=str(candidate["worktree_path"]))
    if not apply:
        return report(ok=True, state="planned", gaps=[], **details)
    if target.exists():
        return report(ok=False, state="blocked", gaps=["candidate_worktree_path_exists"], **details)
    if not candidate["exists"]:
        completed = active_runtime.run_git(repo, "branch", policy.candidate_branch, current_head,
                                           check=False)
        if completed.returncode != 0:
            return report(ok=False, state="blocked", gaps=["candidate_bootstrap_failed"],
                          stderr=completed.stderr.strip(), **details)
    completed = active_runtime.run_git(repo, "worktree", "add", target.as_posix(),
                                       policy.candidate_branch, check=False)
    failed = completed.returncode != 0
    return report(ok=not failed, state="blocked" if failed else "bootstrapped",
                  gaps=["candidate_worktree_add_failed"] if failed else [],
                  stderr=completed.stderr.strip() if failed else "", **details)


def _apply_gaps(
    *, apply: bool, authorized: bool, expect_head: str | None, current_head: str
) -> list[str]:
    gaps: list[str] = []
    if apply and not authorized:
        gaps.append("authorization_required")
    if apply and expect_head is None:
        gaps.append("expect_head_required")
    elif apply and expect_head != current_head:
        gaps.append("expect_head_mismatch")
    return gaps


def _candidate_worktree_gaps(
    candidate: dict[str, object],
    candidate_path: str,
    *,
    runtime: LaneRefreshRuntime | None = None,
) -> list[str]:
    active_runtime = runtime or LaneRefreshRuntime()
    if not candidate["exists"]:
        return ["candidate_branch_missing"]
    if not candidate["worktree_exists"]:
        return ["candidate_worktree_missing"]
    return (
        ["candidate_worktree_dirty"] if active_runtime.changed_paths(Path(candidate_path)) else []
    )


def _refresh_report(
    *,
    ok: bool,
    state: str,
    branch: str,
    head: str,
    gaps: list[str],
    **details: object,
) -> dict[str, object]:
    return {
        key: value
        for key, value in {
            "ok": ok,
            "state": state,
            "branch": branch,
            "head": head,
            "required_gaps": gaps,
            **details,
        }.items()
        if value not in ("", None)
    }


def refresh_candidate_from_accepted(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
    runtime: LaneRefreshRuntime | None = None,
) -> dict[str, object]:
    active_runtime = runtime or LaneRefreshRuntime(run_git=run_git)
    repo = active_runtime.repo_root(root)
    policy = active_runtime.load_branch_role_policy(repo)
    status = active_runtime.workspace_status(repo)
    current_head = active_runtime.run_git(repo, "rev-parse", "HEAD").stdout.strip()
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")

    def report(*, ok: bool, state: str, gaps: list[str], **more: object) -> dict[str, object]:
        return _refresh_report(ok=ok, state=state, branch=policy.candidate_branch,
                               head=current_head, gaps=gaps, previous_head=candidate_head,
                               path=candidate_path, **more)

    gaps: list[str] = []
    if status["role"] != ROLE_ACCEPTED_ROOT:
        gaps.append("accepted_root_required")
    elif status["dirty"]:
        gaps.append("accepted_root_dirty")
    gaps.extend(_candidate_worktree_gaps(candidate, candidate_path, runtime=active_runtime))
    gaps.extend(_apply_gaps(apply=apply, authorized=authorized, expect_head=expect_head,
                            current_head=current_head))
    if gaps:
        return report(ok=False, state="blocked", gaps=gaps)
    if candidate_head == current_head:
        return report(ok=True, state="base_current", gaps=[])
    if not apply:
        return report(ok=True, state="ready_to_refresh_from_accepted", gaps=[])
    # Rewind candidate/dev onto the accepted head. This target is already contained in the
    # accepted branch, so the reference-transaction hook's candidate admission admits it
    # without a fresh proof (see _contained_in_accepted); no ref-move escape is needed now
    # that the ETHOS_ALLOW_REF_MOVE bypass has been removed from the candidate train.
    completed = active_runtime.run_git(Path(candidate_path), "reset", "--hard", current_head,
                                       check=False)
    if completed.returncode != 0:
        return report(ok=False, state="blocked", gaps=["candidate_refresh_from_accepted_failed"],
                      stderr=completed.stderr.strip())
    return report(ok=True, state="refreshed_from_accepted", gaps=[])


def refresh_work_lane_base(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
    runtime: LaneRefreshRuntime | None = None,
) -> dict[str, object]:
    active_runtime = runtime or LaneRefreshRuntime()
    policy = active_runtime.load_branch_role_policy(root)
    status = active_runtime.workspace_status(root)
    current_head = active_runtime.run_git(root, "rev-parse", "HEAD").stdout.strip()
    branch = str(status.get("branch") or "")
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")

    def report(
        *, ok: bool, state: str, head: str, gaps: list[str], **more: object
    ) -> dict[str, object]:
        return _refresh_report(ok=ok, state=state, branch=branch, head=head, gaps=gaps,
                               candidate_branch=policy.candidate_branch,
                               candidate_head=candidate_head,
                               candidate_path=candidate_path, **more)

    gaps: list[str] = []
    if status["role"] != ROLE_WORK_LANE:
        gaps.append("protected_root_mutation")
    elif status["dirty"]:
        gaps.append("work_lane_dirty")
    gaps.extend(_candidate_worktree_gaps(candidate, candidate_path, runtime=active_runtime))
    gaps.extend(_apply_gaps(apply=apply, authorized=authorized, expect_head=expect_head,
                            current_head=current_head))
    if gaps:
        return report(ok=False, state="blocked", head=current_head, gaps=gaps)
    if active_runtime.is_ancestor(root, candidate_head, current_head):
        return report(ok=True, state="base_current", head=current_head, gaps=[])
    if not apply:
        return report(ok=True, state="ready_to_refresh_base", head=current_head, gaps=[])
    signing_gaps = _signing_preflight_gaps(root, runtime=active_runtime)
    if signing_gaps:
        return report(ok=False, state="blocked", head=current_head, gaps=signing_gaps)
    return _replay_work_lane(
        root=root, snapshot=(branch, policy.candidate_branch, candidate_head, current_head),
        runtime=active_runtime, report=report,
    )


def _replay_work_lane(
    *, root: Path, snapshot: tuple[str, str, str, str],
    runtime: LaneRefreshRuntime, report: Callable[..., dict[str, object]],
) -> dict[str, object]:
    branch, candidate_branch, candidate_head, current_head = snapshot
    snapshot_gaps: list[str] = [
        f"refresh_base_snapshot_stale:{name}" for name, ref, admitted in (
            ("work_lane", "HEAD", current_head),
            ("candidate", candidate_branch, candidate_head),
        ) if _ref_head(root, ref, runtime=runtime) != admitted
    ]
    if snapshot_gaps:
        return report(ok=False, state="blocked", head=current_head, gaps=snapshot_gaps)
    completed = runtime.run_git(root, "-c", "rebase.updateRefs=false", "rebase", candidate_head,
                                current_head, check=False)
    projection_resolution = resolve_projection_rebase(root, completed, runtime=runtime)
    projection_recovered = completed.returncode != 0 and projection_resolution["ok"]
    if completed.returncode != 0 and not projection_recovered:
        runtime.run_git(root, "rebase", "--abort", check=False)
        restored = runtime.run_git(root, "switch", branch, check=False)
        return report(
            ok=False,
            state="blocked",
            head=_ref_head(root, "HEAD", runtime=runtime),
            gaps=[
                "refresh_base_failed",
                *([] if restored.returncode == 0 else ["refresh_base_worktree_restore_failed"]),
            ],
            stderr=str(projection_resolution["stderr"] or completed.stderr).strip(),
        )

    def finish(rebased_head: str) -> dict[str, object]:
        if not runtime.is_ancestor(root, candidate_head, rebased_head):
            runtime.run_git(root, "switch", branch, check=False)
            return report(
                ok=False,
                state="blocked",
                head=_ref_head(root, "HEAD", runtime=runtime),
                gaps=["refresh_base_postcondition_failed"],
                previous_head=current_head,
                next_actions=[
                    "inspect current Git ancestry and runner, signing, or hook diagnostics",
                    "repair the replay environment and rerun ethos lane refresh-base",
                ],
                stderr="candidate head is not an ancestor of refreshed work-lane head",
            )
        updated = runtime.run_git(
            root,
            "update-ref",
            f"refs/heads/{branch}",
            rebased_head,
            current_head,
            check=False,
        )
        if updated.returncode != 0:
            restored = runtime.run_git(root, "switch", branch, check=False)
            return report(
                ok=False, state="blocked", head=_ref_head(root, "HEAD", runtime=runtime),
                gaps=[
                    "refresh_base_snapshot_stale:work_lane",
                    *([] if restored.returncode == 0 else ["refresh_base_worktree_restore_failed"]),
                ],
                previous_head=current_head, stderr=updated.stderr.strip())
        attached = runtime.run_git(root, "switch", branch, check=False)
        if attached.returncode != 0:
            return report(ok=False, state="blocked", head=rebased_head,
                          gaps=["refresh_base_worktree_attach_failed"],
                          previous_head=current_head, stderr=attached.stderr.strip())
        refreshed_head = _ref_head(root, "HEAD", runtime=runtime)
        if refreshed_head != rebased_head:
            return report(ok=False, state="blocked", head=refreshed_head,
                          gaps=["refresh_base_snapshot_stale:work_lane"],
                          previous_head=current_head,
                          stderr="work-lane branch advanced after refresh compare-and-swap")
        result = report(ok=True, state="base_refreshed", head=refreshed_head, gaps=[],
                        previous_head=current_head)
        if projection_recovered:
            semantic = "semantic_ledger_merged:source_budget_debt" in projection_resolution["gaps"]
            result.update(
                {
                    "state": "base_refreshed" if semantic else "base_refreshed_projection_stale",
                    "projection_refresh_required": not semantic,
                    "projection_refresh_gaps": projection_resolution["gaps"],
                    "stale_projection_paths": projection_resolution["paths"],
                    "next_actions": projection_resolution["next_actions"]
                    + ["ethos prove --execute --expect-head $(git rev-parse HEAD) --json"],
                }
            )
        return result

    return finish(_ref_head(root, "HEAD", runtime=runtime))
# fmt: on
