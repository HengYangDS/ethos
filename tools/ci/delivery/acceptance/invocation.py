"""Installed ETHOS command invocation for package acceptance."""

from __future__ import annotations

import json
import shlex
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def invoke(
    root: Path,
    command: tuple[str, ...],
    *,
    environment: Mapping[str, str],
) -> tuple[int, dict[str, object], str]:
    """Run one installed CLI request and preserve its result and stderr."""
    completed = run_command(root, command, env=environment, remove_env_prefixes=("GIT_",))
    try:
        result = EthosResult.from_payload(json.loads(completed.stdout))
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        message = f"package_cli_result_invalid:{shlex.join(command)}:{completed.stderr.strip()}"
        raise RuntimeError(message) from error
    if "Traceback" in completed.stdout + completed.stderr:
        message = f"package_cli_traceback:{shlex.join(command)}"
        raise RuntimeError(message)
    payload = result.to_dict()
    diagnostic = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if stderr := completed.stderr.strip():
        diagnostic = f"{diagnostic}\nstderr:{stderr}"
    return completed.returncode, payload, diagnostic
