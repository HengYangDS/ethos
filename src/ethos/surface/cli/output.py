"""CLI result rendering and exit-status enforcement."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.repo.git import git_common_dir
from ethos.domain.execution import process_failure_result
from ethos.domain.execution import profile_failure_result
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
    """Render CLI results without writing diagnostics into an MCP protocol stream."""
    if json_output and artifact_root is not None:
        common_dir = git_common_dir(artifact_root)
        receipt_root = Path(common_dir) / "ethos" if common_dir else artifact_root / ".ethos"
        result = apply_payload_budget(result, root=receipt_root)
    stream = sys.stderr if result.command == "mcp" else sys.stdout
    try:
        if json_output:
            stream.write(f"{result.to_json()}\n")
        else:
            stream.write(f"{result.command}: {result.state}\n")
            if result.next_action:
                stream.write(f"next: {result.next_action}\n")
    except (BrokenPipeError, BlockingIOError):
        return
    native_failure = result.data.get("error_boundary") in {"git_execution", "process_execution"}
    if (enforce or native_failure) and result.verdict != "pass":
        raise SystemExit(1)


def emit_invalid_repository_profile(*, command: str, json_output: bool, enforce: bool) -> None:
    """Render the shared invalid-profile result with the requested CLI enforcement."""
    emit(profile_failure_result(command), json_output=json_output, enforce=enforce)


def emit_process_execution_failure(
    *, command: str, error: ProcessExecutionError, json_output: bool, root: Path | None = None
) -> None:
    """Render the shared application failure without reinterpreting its meaning."""
    emit(
        process_failure_result(command, error, root=root),
        json_output=json_output,
        enforce=True,
    )
