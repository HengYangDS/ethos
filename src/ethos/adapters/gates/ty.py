"""Type-check gate adapter that fails closed for unavailable or invalid results."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.contracts.verdict import close_verdict

if TYPE_CHECKING:
    from pathlib import Path

_DIAGNOSTIC_EXCERPT_LIMIT = 12


def _runtime_command(root: Path) -> list[str]:
    """Build one source-bound check using Ty's native carrier selection."""
    venv = root / ".venv"
    return [
        str(root / "tools/ci/scripts/with-python-runtime.sh"),
        "--",
        "uv",
        "run",
        "--frozen",
        "--offline",
        "--group",
        "dev",
        "python",
        "-m",
        "ty",
        "check",
        "--project",
        str(root),
        "--config-file",
        str(root / ".config/checks/ty/ty.toml"),
        "--output-format",
        "gitlab",
        "--error-on-warning",
        "--python",
        str(venv),
        "--extra-search-path",
        str(root / "src"),
    ]


def _diagnostic_report(root: Path) -> dict[str, object]:
    """Interpret native findings, preserving tool failure and owned execution bounds."""
    command = _runtime_command(root)
    returncode: int | str | None = None
    diagnostics: list[dict[str, object]] | None = None
    stderr = ""
    try:
        completed = run_command(root, tuple(command), timeout=120)
        returncode, stderr = completed.returncode, completed.stderr
        output = completed.stdout + stderr
        try:
            findings = json.loads(completed.stdout)
        except ValueError:
            findings = None
        if isinstance(findings, list) and all(
            isinstance(item, dict)
            and isinstance(item.get("description"), str)
            and isinstance(item.get("severity"), str)
            and item["severity"] in {"info", "minor", "major", "critical", "blocker"}
            for item in findings
        ):
            diagnostics = findings
    except (OSError, ProcessExecutionError, subprocess.TimeoutExpired) as error:
        returncode = "timeout" if isinstance(error, subprocess.TimeoutExpired) else None
        output = stderr = f"{type(error).__name__}: {error}"
    count = len(diagnostics) if diagnostics is not None else None
    state = (
        "tool_error"
        if count is None or returncode not in (0, 1) or (count == 0 and returncode != 0)
        else "diagnostics"
        if count
        else "clean"
    )
    return {
        "count": count,
        "returncode": returncode,
        "state": state,
        "command": command,
        "diagnostics": diagnostics,
        "stderr": stderr,
        "diagnostic_excerpt": _diagnostic_excerpt(output),
    }


def _diagnostic_excerpt(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()][
        :_DIAGNOSTIC_EXCERPT_LIMIT
    ]


def ty_gate_report(root: Path) -> dict[str, object]:
    """Enforce zero Ty diagnostics across its native selected Python carriers."""
    config_path = root / ".config" / "checks" / "ty" / "ty.toml"
    if not config_path.is_file():
        return {
            "verdict": "block",
            "state": "blocked",
            "required_gaps": ["ty_config_missing"],
            "analysis": {},
        }
    result = _diagnostic_report(root)
    gaps: list[str] = []
    count = result["count"]
    if result["state"] == "tool_error":
        failure = result["returncode"]
        failure_kind = str(failure) if failure is not None else "launch"
        gaps.append(f"ty_execution_failed:{failure_kind}")
    elif isinstance(count, int) and count > 0:
        gaps.append(f"ty_zero_tolerance_violation:{count}")
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "state": "clean" if not gaps else "blocked",
        "required_gaps": gaps,
        "analysis": result,
    }
