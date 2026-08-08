"""Git observations for deterministic OpenSpec repository policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.openspec.audit import active_change_names_from_paths
from ethos.repository.openspec.audit import openspec_shape_report as compile_openspec_shape_report
from ethos.repository.openspec.audit import (
    protected_branch_active_change_report as compile_protected_branch_report,
)
from ethos.repository.openspec.audit import (
    protected_branch_active_change_required_gaps as compile_protected_branch_gaps,
)

if TYPE_CHECKING:
    from pathlib import Path


def active_change_names_in_ref(root: Path, ref: str) -> dict[str, object]:
    """Observe and interpret active OpenSpec Change names in one Git tree."""
    completed = _git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        ref,
        "--",
        "openspec/changes",
    )
    paths = tuple(completed.stdout.splitlines()) if completed.returncode == 0 else None
    return active_change_names_from_paths(ref, paths)


def protected_branch_active_change_report(root: Path, *, current_branch: str) -> dict[str, object]:
    """Observe protected refs before compiling their OpenSpec residue report."""
    policy = load_branch_role_policy(root)
    branches = (policy.release_branch, policy.accepted_branch, policy.candidate_branch)
    observations = {
        branch: _branch_observation(root, branch)
        for branch in branches
        if branch and branch != current_branch
    }
    return compile_protected_branch_report(
        root,
        current_branch=current_branch,
        branch_observations=observations,
    )


def protected_branch_active_change_required_gaps(
    root: Path,
    *,
    current_branch: str,
    roles: set[str] | None = None,
) -> list[str]:
    """Return blocking protected-branch residue from one observed report."""
    report = protected_branch_active_change_report(root, current_branch=current_branch)
    return compile_protected_branch_gaps(report, roles=roles)


def openspec_shape_report(root: Path) -> dict[str, object]:
    """Observe Git branch and diff facts before compiling OpenSpec shape."""
    current_branch = _current_branch(root)
    residue = protected_branch_active_change_report(root, current_branch=current_branch)
    diff = _git(root, "diff", "--unified=0", "--", "openspec/specs/**/*.md")
    return compile_openspec_shape_report(
        root,
        current_branch=current_branch,
        protected_branch_residue=residue,
        spec_diff=diff.stdout if diff.returncode in {0, 1} else None,
    )


def _branch_observation(
    root: Path, branch: str
) -> tuple[dict[str, object], dict[str, object] | None]:
    completed = _git(root, "rev-parse", "--verify", "--quiet", f"{branch}^{{commit}}")
    if completed.returncode == 0:
        branch_report = {
            "verdict": "pass",
            "state": "present",
            "branch": branch,
            "required_gaps": [],
        }
        return branch_report, active_change_names_in_ref(root, branch)
    if completed.returncode == 1:
        return {
            "verdict": "pass",
            "state": "absent",
            "branch": branch,
            "required_gaps": [],
        }, None
    return {
        "verdict": "unknown",
        "state": "unknown",
        "branch": branch,
        "required_gaps": [f"openspec_branch_unavailable:{branch}"],
    }, None


def _current_branch(root: Path) -> str:
    completed = _git(root, "branch", "--show-current")
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _git(root: Path, *args: str):
    return run_git(root, *args, check=False)
