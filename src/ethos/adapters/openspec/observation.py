"""Git observations for deterministic OpenSpec repository policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.openspec.configuration import official_config_report
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.openspec.audit import active_change_names_from_paths
from ethos.repository.openspec.audit import compile_governed_branch_intent_report
from ethos.repository.openspec.audit import compile_openspec_shape_report

if TYPE_CHECKING:
    from pathlib import Path


def active_change_names_in_ref(root: Path, ref: str) -> dict[str, object]:
    """Observe and interpret active OpenSpec Change names in one Git tree."""
    completed = run_git(
        root, "ls-tree", "-r", "--name-only", ref, "--", "openspec/changes", check=False
    )
    paths = tuple(completed.stdout.splitlines()) if completed.returncode == 0 else None
    return active_change_names_from_paths(ref, paths)


def governed_branch_intent_report(
    root: Path, *, current_branch: str, repository: Path | None = None
) -> dict[str, object]:
    """Observe configured role refs without classifying active intent as residue.

    `repository` names where Git is read when `root` holds only the files of another tree.
    """
    policy = load_branch_role_policy(root)
    branches = (policy.release_branch, policy.accepted_branch, policy.candidate_branch)
    observations = {
        branch: _branch_observation(repository or root, branch)
        for branch in branches
        if branch and branch != current_branch
    }
    return compile_governed_branch_intent_report(
        root,
        current_branch=current_branch,
        branch_observations=observations,
    )


def openspec_shape_report(root: Path) -> dict[str, object]:
    """Observe Git branch and diff facts before compiling OpenSpec shape."""
    current_branch = git_stdout(root, "branch", "--show-current")
    intent = governed_branch_intent_report(root, current_branch=current_branch)
    diff = run_git(root, "diff", "--unified=0", "--", "openspec/specs/**/*.md", check=False)
    return compile_openspec_shape_report(
        root,
        branch_intent=intent,
        spec_diff=diff.stdout if diff.returncode in {0, 1} else None,
        official_config=official_config_report(root),
    )


def _branch_observation(
    root: Path, branch: str
) -> tuple[dict[str, object], dict[str, object] | None]:
    completed = run_git(
        root, "rev-parse", "--verify", "--quiet", f"{branch}^{{commit}}", check=False
    )
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
