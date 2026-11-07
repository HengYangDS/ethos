"""Normalize known execution and profile failures across application transports."""

from __future__ import annotations

import shlex
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import GIT_PROCESS_TIMED_OUT
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.invocation_facts import invocation_scope
from ethos.contracts.paradigm.declaration import binding_path
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Callable


# The problems an invalid-profile result names; its count says how many there are in all.
_PROFILE_PROBLEM_LIMIT = 20


def profile_failure_result(command: str, root: Path | None = None) -> EthosResult:
    """Project the profile owner's stable failure, naming the root's problems by key path."""
    problems = load_repository_profile(root).problems if root is not None else ()
    path = binding_path("profile")
    data: dict[str, object] = {"error_boundary": "repository_profile_validation"}
    if problems:
        data |= {
            "profile_problems": list(problems[:_PROFILE_PROBLEM_LIMIT]),
            "profile_problem_count": len(problems),
        }
    return EthosResult(
        command=command,
        verdict="block",
        state="gapped",
        required_gaps=(INVALID_PROFILE_ERROR,),
        next_action=(
            f"repair the problems that data.profile_problems names in {path} and rerun the command"
            if problems
            else f"repair {path} and rerun the command"
        ),
        data=data,
    )


def process_failure_result(
    command: str, error: ProcessExecutionError, *, root: Path | None = None
) -> EthosResult:
    """Build the result from the decision the error carries, with its native evidence."""
    git_failure = isinstance(error, GitExecutionError)
    evidence = error.evidence()
    evidence["cwd"] = error.cwd or (str(root.resolve()) if root is not None else "")
    return EthosResult.from_outcome(
        command,
        error.outcome,
        next_action=(
            "repair the reported process boundary and rerun the command"
            if not git_failure
            else shlex.join(("ethos", "status", "--root", str(evidence["cwd"]), "--json"))
            if error.code in {GIT_PROCESS_TIMED_OUT, "build_source_identity_changed"}
            else "install Git on the effective PATH and rerun the command"
            if error.code == "git_executable_unavailable"
            else "verify the repository root and rerun the command"
        ),
        data={
            "error_boundary": "git_execution" if git_failure else "process_execution",
            **evidence,
        },
    )


def application_result[**P](
    command: str,
) -> Callable[[Callable[P, EthosResult]], Callable[P, EthosResult]]:
    """Retain operation signatures while normalizing known application failures."""

    def decorate(
        operation: Callable[P, EthosResult],
    ) -> Callable[P, EthosResult]:
        @wraps(operation)
        def invoke(*args: P.args, **kwargs: P.kwargs) -> EthosResult:
            try:
                with invocation_scope():
                    return operation(*args, **kwargs)
            except ProcessExecutionError as error:
                root = kwargs.get("root", args[0] if args else None)
                return process_failure_result(
                    command, error, root=root if isinstance(root, Path) else None
                )

            except ValueError as error:
                if str(error) != INVALID_PROFILE_ERROR:
                    raise
                root = kwargs.get("root", args[0] if args else None)
                return profile_failure_result(command, root if isinstance(root, Path) else None)

        return invoke

    return decorate
