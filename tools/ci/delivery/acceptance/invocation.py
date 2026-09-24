"""Installed ETHOS command invocation for package acceptance."""

from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Mapping


def require_installed_guidance(status_json: str, origin: str) -> None:
    """Bind status guidance to the exact installed package, never a source checkout."""
    try:
        payload = json.loads(status_json)
        guidance = payload["governance_context"]["agent_guidance"]
        package = Path(origin).resolve(strict=True).parent
        expected = (package / "data/skills/ethos-repository-work/SKILL.md").resolve(strict=True)
        observed = Path(guidance["path"]).resolve(strict=True)
        valid = (
            guidance["authority"] == "product_projection"
            and guidance["media_type"] == "text/markdown"
            and expected.is_relative_to(package)
            and observed == expected
            and guidance["sha256"] == hashlib.sha256(expected.read_bytes()).hexdigest()
        )
    except (KeyError, OSError, TypeError, ValueError):
        valid = False
    if not valid:
        message = "installed_agent_guidance_invalid"
        raise RuntimeError(message)


def invoke(
    root: Path,
    command: tuple[str, ...],
    *,
    environment: Mapping[str, str],
) -> tuple[int, dict[str, object], str]:
    """Run one installed CLI request and preserve its result and stderr."""
    completed = run_command(root, command, env=environment, inherit_environment=False, timeout=180)
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
