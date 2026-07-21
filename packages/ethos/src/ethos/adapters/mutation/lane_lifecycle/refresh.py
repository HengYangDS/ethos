from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
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


def _ref_head(root: Path, ref: str) -> str:
    completed = run_git(root, "rev-parse", ref, check=False)
    return str(completed.stdout).strip() if completed.returncode == 0 else ""


def bootstrap_candidate(
    *,
    root: Path,
    path: Path | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = repo_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    current_head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    target = (path or default_candidate_path(repo, policy.candidate_branch)).resolve()

    def report(*, ok: bool, state: str, gaps: list[str], **details: object) -> dict[str, object]:
        return _refresh_report(
            ok=ok,
            state=state,
            branch=policy.candidate_branch,
            head=current_head,
            gaps=gaps,
            **details,
        )

    details = {"path": target.as_posix()}
    gaps = [
        gap
        for gap, present in (
            (
                "candidate_bootstrap_requires_clean_accepted_root",
                status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"],
            ),
            ("expect_head_mismatch", expect_head is not None and expect_head != current_head),
        )
        if present
    ]
    if gaps:
        return report(ok=False, state="blocked", gaps=gaps, **details)
    candidate = cast("dict[str, object]", status["candidate"])
    if candidate["exists"] and candidate["worktree_exists"]:
        return report(ok=True, state="present", gaps=[], path=str(candidate["worktree_path"]))
    if not apply:
        return report(ok=True, state="planned", gaps=[], **details)
    if target.exists():
        return report(ok=False, state="blocked", gaps=["candidate_worktree_path_exists"], **details)
    args = (
        ("worktree", "add", target.as_posix(), policy.candidate_branch)
        if candidate["exists"]
        else (
            "worktree",
            "add",
            "-b",
            policy.candidate_branch,
            target.as_posix(),
            current_head,
        )
    )
    completed = run_git(repo, *args, check=False)
    failed = completed.returncode != 0
    return report(
        ok=not failed,
        state="blocked" if failed else "bootstrapped",
        gaps=["candidate_worktree_add_failed"] if failed else [],
        stderr=completed.stderr.strip() if failed else "",
        **details,
    )


def _apply_gaps(
    *, apply: bool, authorized: bool, expect_head: str | None, current_head: str
) -> list[str]:
    return [
        gap
        for gap, present in (
            ("authorization_required", apply and not authorized),
            ("expect_head_required", apply and expect_head is None),
            (
                "expect_head_mismatch",
                apply and expect_head is not None and expect_head != current_head,
            ),
        )
        if present
    ]


def _candidate_worktree_gaps(
    candidate: dict[str, object],
    candidate_path: str,
) -> list[str]:
    if not candidate["exists"]:
        return ["candidate_branch_missing"]
    if not candidate["worktree_exists"]:
        return ["candidate_worktree_missing"]
    return ["candidate_worktree_dirty"] if changed_paths(Path(candidate_path)) else []


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
) -> dict[str, object]:
    repo = repo_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    current_head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")

    def report(*, ok: bool, state: str, gaps: list[str], **more: object) -> dict[str, object]:
        return _refresh_report(
            ok=ok,
            state=state,
            branch=policy.candidate_branch,
            head=current_head,
            gaps=gaps,
            previous_head=candidate_head,
            path=candidate_path,
            **more,
        )

    gaps = [
        gap
        for gap, present in (
            ("accepted_root_required", status["role"] != ROLE_ACCEPTED_ROOT),
            ("accepted_root_dirty", status["role"] == ROLE_ACCEPTED_ROOT and status["dirty"]),
        )
        if present
    ]
    gaps.extend(_candidate_worktree_gaps(candidate, candidate_path))
    gaps.extend(
        _apply_gaps(
            apply=apply, authorized=authorized, expect_head=expect_head, current_head=current_head
        )
    )
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
    completed = run_git(Path(candidate_path), "reset", "--hard", current_head, check=False)
    if completed.returncode != 0:
        return report(
            ok=False,
            state="blocked",
            gaps=["candidate_refresh_from_accepted_failed"],
            stderr=completed.stderr.strip(),
        )
    return report(ok=True, state="refreshed_from_accepted", gaps=[])


def refresh_work_lane_base(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    status = workspace_status(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    branch = str(status.get("branch") or "")
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")

    def report(
        *, ok: bool, state: str, head: str, gaps: list[str], **more: object
    ) -> dict[str, object]:
        return _refresh_report(
            ok=ok,
            state=state,
            branch=branch,
            head=head,
            gaps=gaps,
            candidate_branch=policy.candidate_branch,
            candidate_head=candidate_head,
            candidate_path=candidate_path,
            **more,
        )

    gaps = [
        gap
        for gap, present in (
            ("protected_root_mutation", status["role"] != ROLE_WORK_LANE),
            ("work_lane_dirty", status["role"] == ROLE_WORK_LANE and status["dirty"]),
        )
        if present
    ]
    gaps.extend(_candidate_worktree_gaps(candidate, candidate_path))
    gaps.extend(
        _apply_gaps(
            apply=apply, authorized=authorized, expect_head=expect_head, current_head=current_head
        )
    )
    if gaps:
        return report(ok=False, state="blocked", head=current_head, gaps=gaps)
    if is_ancestor(root, candidate_head, current_head):
        return report(ok=True, state="base_current", head=current_head, gaps=[])
    if not apply:
        return report(ok=True, state="ready_to_refresh_base", head=current_head, gaps=[])
    return _replay_work_lane(
        root=root,
        snapshot=(branch, policy.candidate_branch, candidate_head, current_head),
        report=report,
    )


def _replay_work_lane(
    *,
    root: Path,
    snapshot: tuple[str, str, str, str],
    report: Callable[..., dict[str, object]],
) -> dict[str, object]:
    branch, candidate_branch, candidate_head, current_head = snapshot
    snapshot_gaps: list[str] = [
        f"refresh_base_snapshot_stale:{name}"
        for name, ref, admitted in (
            ("work_lane", "HEAD", current_head),
            ("candidate", candidate_branch, candidate_head),
        )
        if _ref_head(root, ref) != admitted
    ]
    if snapshot_gaps:
        return report(ok=False, state="blocked", head=current_head, gaps=snapshot_gaps)
    completed = run_git(
        root, "-c", "rebase.updateRefs=false", "rebase", candidate_head, current_head, check=False
    )
    projection_resolution = resolve_projection_rebase(root, completed)
    projection_recovered = completed.returncode != 0 and projection_resolution["ok"]
    if completed.returncode != 0 and not projection_recovered:
        run_git(root, "rebase", "--abort", check=False)
        restored = run_git(root, "switch", branch, check=False)
        return report(
            ok=False,
            state="blocked",
            head=_ref_head(root, "HEAD"),
            gaps=[
                "refresh_base_failed",
                *([] if restored.returncode == 0 else ["refresh_base_worktree_restore_failed"]),
            ],
            stderr=str(projection_resolution["stderr"] or completed.stderr).strip(),
        )

    def finish(rebased_head: str) -> dict[str, object]:
        def blocked(gaps: list[str], *, head: str, **more: object) -> dict[str, object]:
            return report(
                ok=False, state="blocked", head=head, gaps=gaps, previous_head=current_head, **more
            )

        if not is_ancestor(root, candidate_head, rebased_head):
            run_git(root, "switch", branch, check=False)
            return blocked(
                ["refresh_base_postcondition_failed"],
                head=_ref_head(root, "HEAD"),
                next_actions=[
                    "inspect current Git ancestry and runner, signing, or hook diagnostics",
                    "repair the replay environment and rerun ethos lane refresh-base",
                ],
                stderr="candidate head is not an ancestor of refreshed work-lane head",
            )
        updated = run_git(
            root,
            "update-ref",
            f"refs/heads/{branch}",
            rebased_head,
            current_head,
            check=False,
        )
        if updated.returncode != 0:
            restored = run_git(root, "switch", branch, check=False)
            return blocked(
                [
                    "refresh_base_snapshot_stale:work_lane",
                    *([] if restored.returncode == 0 else ["refresh_base_worktree_restore_failed"]),
                ],
                head=_ref_head(root, "HEAD"),
                stderr=updated.stderr.strip(),
            )
        attached = run_git(root, "switch", branch, check=False)
        if attached.returncode != 0:
            return blocked(
                ["refresh_base_worktree_attach_failed"],
                head=rebased_head,
                stderr=attached.stderr.strip(),
            )
        refreshed_head = _ref_head(root, "HEAD")
        if refreshed_head != rebased_head:
            return blocked(
                ["refresh_base_snapshot_stale:work_lane"],
                head=refreshed_head,
                stderr="work-lane branch advanced after refresh compare-and-swap",
            )
        result = report(
            ok=True,
            state="base_refreshed",
            head=refreshed_head,
            gaps=[],
            previous_head=current_head,
        )
        if projection_recovered:
            projection_gaps = [
                gap
                for gap in projection_resolution["gaps"]
                if gap.startswith("projection_regeneration_required:")
            ]
            projection_paths = [
                path
                for path in projection_resolution["paths"]
                if path.startswith("evidence/parity/")
            ]
            result.update(
                {
                    "state": (
                        "base_refreshed_projection_stale" if projection_gaps else "base_refreshed"
                    ),
                    "projection_refresh_required": bool(projection_gaps),
                    "projection_refresh_gaps": projection_resolution["gaps"],
                    "stale_projection_paths": projection_paths,
                    "next_actions": projection_resolution["next_actions"]
                    + ["ethos prove --execute --expect-head $(git rev-parse HEAD) --json"],
                }
            )
        return result

    return finish(_ref_head(root, "HEAD"))
