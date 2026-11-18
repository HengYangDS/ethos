"""Name what a readiness run did not examine: a report, which refuses nothing.

A readiness run examines the gates of its tier and nothing else. Beside the gates it did not
run, its result names the tests that read what the lane changed, the changed paths that no test
reads, and the task-runner sessions that only a Forge job asks for. A part that cannot be read
is named as unavailable and changes no verdict: a file that the parser cannot read at all, a
base that Git does not resolve and a pipeline file that is gone each end one part, never the run.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import git_stdout_checked
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.gap import tracked_text
from ethos.repository.paradigm.orchestration import forge_only_sessions
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.quality.selection import carried_paths
from ethos.repository.policy.quality.selection import select_tests

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.policy.gates import ResolvedGatePolicy

_PYTHON_MANIFEST = "pyproject.toml"


def readiness_unexamined(repo: Path, policy: ResolvedGatePolicy) -> dict[str, object]:
    """Report the selection and the Forge-only sessions of one committed, source-bound tree."""
    tracked = frozenset(policy.repository_paths)
    report: dict[str, object] = {}
    unavailable: dict[str, str] = {}
    for part, read in (("selection", _selection), ("forge_only_sessions", _forge_sessions)):
        try:
            report.update(read(repo, policy, tracked))
        except (OSError, ValueError, RecursionError, subprocess.SubprocessError) as error:
            unavailable[part] = f"{type(error).__name__}: {error}"
    return {**report, **({"unavailable": unavailable} if unavailable else {})}


def _selection(
    repo: Path, policy: ResolvedGatePolicy, tracked: frozenset[str]
) -> dict[str, object]:
    """Select the tests that read what a Work Lane committed since its candidate branch.

    The run's source is bound to HEAD, so the committed difference is the whole change. Any other
    role has no base here: its selection is empty and its `base` says so.
    """
    roles = load_branch_role_policy(repo)
    lane = roles.role_for_branch(current_branch(repo)) == ROLE_WORK_LANE
    base = roles.candidate_branch if lane else ""
    listed = git_stdout_checked(repo, "diff", "--name-only", "-z", f"{base}...HEAD") if base else ""
    changed = [path for path in listed.split("\0") if path]
    subjects = [
        subject
        for subject in observed_code_subjects(
            policy.repository_paths, roles=dict(policy.carrier_roles)
        )
        if subject.language == "python"
    ]
    files = {
        subject.path: text
        for subject in subjects
        if (text := tracked_text(repo, subject.path, tracked)) is not None
    }
    tests, unread = select_tests(
        changed,
        files,
        frozenset(subject.path for subject in subjects if subject.is_test),
        carried_paths(tracked_text(repo, _PYTHON_MANIFEST, tracked) or ""),
    )
    return {"base": base, "changed_paths": len(changed), "tests": tests, "unread_paths": unread}


def _forge_sessions(
    repo: Path, policy: ResolvedGatePolicy, tracked: frozenset[str]
) -> dict[str, object]:
    """List the sessions that a Forge job asks for and no planned gate's command does."""
    registry = policy.registry
    planned = (" ".join(registry[node.id].command) for node in policy.nodes)
    jobs, sessions = forge_only_sessions(load_repository_paradigm(), repo, tracked, planned)
    return {"forge_jobs": jobs, "forge_only_sessions": sessions}
