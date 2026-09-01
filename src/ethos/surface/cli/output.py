"""CLI result rendering and exit-status enforcement."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import git_common_dir
from ethos.result import EthosResult
from ethos.result import apply_payload_budget

if TYPE_CHECKING:
    from ethos.adapters.process import ProcessExecutionError

JsonFlag = Annotated[bool, Parameter(name="--json")]


def emit(
    result: EthosResult,
    *,
    json_output: bool,
    enforce: bool = True,
    artifact_root: Path | None = None,
) -> None:
    """Render a result and fail closed when an enforced verdict is not okay."""
    if json_output and artifact_root is not None:
        common_dir = git_common_dir(artifact_root)
        receipt_root = Path(common_dir) / "ethos" if common_dir else artifact_root / ".ethos"
        result = apply_payload_budget(result, root=receipt_root)
    try:
        if json_output:
            sys.stdout.write(f"{result.to_json()}\n")
        else:
            sys.stdout.write(f"{result.command}: {result.state}\n")
            if result.next_action:
                sys.stdout.write(f"next: {result.next_action}\n")
    except (BrokenPipeError, BlockingIOError):
        return
    if enforce and result.verdict != "pass":
        raise SystemExit(1)


def emit_invalid_repository_profile(*, command: str, json_output: bool, enforce: bool) -> None:
    """Emit the fail-closed envelope for an invalid repository profile."""
    emit(
        EthosResult(
            command=command,
            verdict="block",
            state="gapped",
            required_gaps=("repository_profile_invalid:.ethos/profile.toml",),
            next_action="repair .ethos/profile.toml and rerun the command",
            data={"error_boundary": "repository_profile_validation"},
        ),
        json_output=json_output,
        enforce=enforce,
    )


def emit_process_execution_failure(
    *, command: str, error: ProcessExecutionError, json_output: bool
) -> None:
    """Emit one stable fail-closed envelope for external process creation."""
    emit(
        EthosResult(
            command=command,
            verdict="block",
            state="gapped",
            required_gaps=(error.code,),
            next_action="repair the reported process boundary and rerun the command",
            data={"error_boundary": "process_execution", **error.evidence()},
        ),
        json_output=json_output,
        enforce=True,
    )


def emit_git_execution_failure(
    *, command: str, error: GitExecutionError, json_output: bool
) -> None:
    """Emit one stable fail-closed envelope for Git execution infrastructure."""
    emit(
        EthosResult(
            command=command,
            verdict="block",
            state="gapped",
            required_gaps=(error.code,),
            next_action=(
                "install Git on the effective PATH and rerun the command"
                if error.code == "git_executable_unavailable"
                else "verify the repository root and rerun the command"
            ),
            data={"error_boundary": "git_execution", **error.evidence()},
        ),
        json_output=json_output,
        enforce=True,
    )
