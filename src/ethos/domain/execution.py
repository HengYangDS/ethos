"""Normalize known execution and profile failures across application transports."""

from __future__ import annotations

import shlex
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import GIT_PROCESS_TIMED_OUT
from ethos.adapters.repo.git import GitExecutionError
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Callable


def profile_failure_result(command: str) -> EthosResult:
    """Project the repository profile owner's stable failure without transport policy."""
    return EthosResult(
        command=command,
        verdict="block",
        state="gapped",
        required_gaps=(INVALID_PROFILE_ERROR,),
        next_action="repair .ethos/profile.toml and rerun the command",
        data={"error_boundary": "repository_profile_validation"},
    )


def process_failure_result(
    command: str, error: ProcessExecutionError, *, root: Path | None = None
) -> EthosResult:
    """Distinguish an unavailable capability from a native observation that timed out."""
    git_failure = isinstance(error, GitExecutionError)
    unknown = git_failure and error.code == GIT_PROCESS_TIMED_OUT
    evidence = error.evidence()
    evidence["cwd"] = error.cwd or (str(root.resolve()) if root is not None else "")
    return EthosResult(
        command=command,
        verdict="unknown" if unknown else "block",
        state="unknown" if unknown else "gapped",
        required_gaps=(error.code,),
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
                return operation(*args, **kwargs)
            except ProcessExecutionError as error:
                root = kwargs.get("root", args[0] if args else None)
                return process_failure_result(
                    command, error, root=root if isinstance(root, Path) else None
                )

            except ValueError as error:
                if str(error) != INVALID_PROFILE_ERROR:
                    raise
                return profile_failure_result(command)

        return invoke

    return decorate
