"""CLI result rendering and exit-status enforcement."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from typing import Annotated

from cyclopts import Parameter

from ethos.result import EthosResult
from ethos.result import apply_payload_budget

if TYPE_CHECKING:
    from pathlib import Path

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
        result = apply_payload_budget(result, root=artifact_root)
    try:
        if json_output:
            sys.stdout.write(f"{result.to_json()}\n")
        else:
            sys.stdout.write(f"{result.command}: {result.state}\n")
            for action in result.next_actions:
                sys.stdout.write(f"next: {action}\n")
    except (BrokenPipeError, BlockingIOError):
        return
    if enforce and not result.ok:
        raise SystemExit(1)


def emit_invalid_repository_profile(*, command: str, json_output: bool, enforce: bool) -> None:
    """Emit the fail-closed envelope for an invalid repository profile."""
    emit(
        EthosResult(
            command=command,
            ok=False,
            state="gapped",
            required_gaps=("repository_profile_invalid:.ethos/profile.toml",),
            next_actions=("repair .ethos/profile.toml and rerun the command",),
            data={"error_boundary": "repository_profile_validation"},
        ),
        json_output=json_output,
        enforce=enforce,
    )
