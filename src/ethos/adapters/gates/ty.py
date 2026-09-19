"""Type-check gate adapter that fails closed for unavailable or invalid results."""

from __future__ import annotations

import json
import subprocess
import tomllib
from typing import TYPE_CHECKING

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.contracts.verdict import close_verdict

if TYPE_CHECKING:
    from pathlib import Path

_DIAGNOSTIC_EXCERPT_LIMIT = 12


def _runtime_command(root: Path, package_src: str) -> list[str]:
    """Build the source-bound command for one checkout-local type check."""
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
        "--output-format",
        "gitlab",
        "--error-on-warning",
        "--python",
        str(venv),
        "--extra-search-path",
        str(root / "src"),
        package_src,
    ]


def _diagnostic_report(root: Path, package_src: str) -> dict[str, object]:
    """Interpret native findings, preserving tool failure and owned execution bounds."""
    command = _runtime_command(root, package_src)
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


def _package_result(root: Path, package: str) -> dict[str, object]:
    package_src = "src" if package == "." else f"{package}/src"
    return _diagnostic_report(root, package_src) | {"limit": 0, "tier": "zero_tolerance"}


def ty_gate_report(root: Path) -> dict[str, object]:
    """Run ty per governed package and enforce zero diagnostic tolerance."""
    policy_path = root / ".config" / "checks" / "ty" / "policy.toml"
    if not policy_path.exists():
        return {
            "verdict": "block",
            "state": "blocked",
            "required_gaps": ["ty_policy_missing"],
            "packages": {},
        }
    policy = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    zero_tolerance = [str(p) for p in policy.get("zero_tolerance", {}).get("packages", [])]
    results: dict[str, dict[str, object]] = {}
    gaps: list[str] = []
    for package in zero_tolerance:
        package_result = _package_result(root, package)
        results[package] = package_result
        count = package_result["count"]
        if package_result["state"] == "tool_error":
            failure = package_result["returncode"]
            failure_kind = str(failure) if failure is not None else "launch"
            gaps.append(f"ty_execution_failed:{package}:{failure_kind}")
        elif isinstance(count, int) and count > 0:
            gaps.append(f"ty_zero_tolerance_violation:{package}:{count}")
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "state": "clean" if not gaps else "blocked",
        "required_gaps": gaps,
        "packages": results,
    }
