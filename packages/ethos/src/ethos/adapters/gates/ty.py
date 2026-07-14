"""Type-check gate adapter that fails closed for unavailable or invalid results."""

from __future__ import annotations

import re
import subprocess
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_COUNT_RE = re.compile(r"Found (\d+) diagnostic")
_DIAGNOSTIC_EXCERPT_LIMIT = 12


def _diagnostic_report(root: Path, package_src: str) -> dict[str, object]:
    """Run ty and retain whether its diagnostic count is determinate."""
    command = f"ty check {package_src}"
    venv = root / "build/runtime/venv"
    try:
        completed = subprocess.run(
            [str(venv / "bin/python"), "-m", "ty", "check", "--python", str(venv), package_src],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        output = completed.stdout + completed.stderr
    except OSError as error:
        completed = None
        output = f"{type(error).__name__}: {error}"
    count = _diagnostic_count_from_output(output) if completed is not None else None
    returncode = completed.returncode if completed is not None else None
    if count is None or (count == 0 and returncode):
        state = "tool_error"
    else:
        state = "diagnostics" if count else "clean"
    return {
        "count": count,
        "returncode": returncode,
        "state": state,
        "command": command,
        "diagnostic_excerpt": _diagnostic_excerpt(output),
    }


def _diagnostic_count_from_output(output: str) -> int | None:
    """Return a count only for a terminal ty result; unknown output is an error."""
    match = _COUNT_RE.search(output)
    return 0 if "All checks passed" in output else int(match.group(1)) if match else None


def _diagnostic_excerpt(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()][
        :_DIAGNOSTIC_EXCERPT_LIMIT
    ]


def _package_result(root: Path, package: str) -> dict[str, object]:
    return _diagnostic_report(root, f"{package}/src") | {"limit": 0, "tier": "zero_tolerance"}


def ty_gate_report(root: Path) -> dict[str, object]:
    """Run ty per governed package and enforce zero diagnostic tolerance."""
    policy_path = root / ".config" / "checks" / "ty" / "policy.toml"
    if not policy_path.exists():
        return {
            "ok": False,
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
            failure_kind = str(failure) if isinstance(failure, int) else "launch"
            gaps.append(f"ty_execution_failed:{package}:{failure_kind}")
        elif isinstance(count, int) and count > 0:
            gaps.append(f"ty_zero_tolerance_violation:{package}:{count}")
    return {
        "ok": not gaps,
        "state": "clean" if not gaps else "blocked",
        "required_gaps": gaps,
        "packages": results,
    }
