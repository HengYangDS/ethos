"""Type-check gate adapter — enforces the ty policy tiers.

The ty ratchet (.config/checks/ty/policy.toml) declared enforcement via an
`ethos quality types` command that did not exist, so the baselines drifted uncaught
(packages/ethos grew past its pin with nothing blocking). This adapter is the
runner that binds the policy to a real gate: it runs ty per package and fails when a
zero-tolerance package has ANY diagnostic or a ratchet package exceeds its baseline
(failure-blocking moves upstream; the ratchet may only shrink).
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_COUNT_RE = re.compile(r"Found (\d+) diagnostic")
_DIAGNOSTIC_EXCERPT_LIMIT = 12


def _diagnostic_report(root: Path, package_src: str) -> dict[str, object]:
    command = f"ty check {package_src}"
    completed = subprocess.run(
        [sys.executable, "-m", "ty", "check", package_src],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = completed.stdout + completed.stderr
    return {
        "count": _diagnostic_count_from_output(output),
        "command": command,
        "diagnostic_excerpt": _diagnostic_excerpt(output),
    }


def _diagnostic_count_from_output(output: str) -> int:
    if "All checks passed" in output:
        return 0
    match = _COUNT_RE.search(output)
    return int(match.group(1)) if match else 0


def _diagnostic_excerpt(output: str) -> list[str]:
    return [line for line in (line.strip() for line in output.splitlines()) if line][
        :_DIAGNOSTIC_EXCERPT_LIMIT
    ]


def _package_result(root: Path, package: str, *, tier: str, limit: int) -> dict[str, object]:
    report = _diagnostic_report(root, f"{package}/src")
    return {
        "count": report["count"],
        "limit": limit,
        "tier": tier,
        "command": report["command"],
        "diagnostic_excerpt": report["diagnostic_excerpt"],
    }


def _count_value(report: dict[str, object]) -> int:
    value = report["count"]
    return value if isinstance(value, int) else 0


def ty_gate_report(root: Path) -> dict[str, object]:
    """Run ty per package and enforce the policy tiers (zero-tolerance + ratchet)."""
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
    ratchet = {str(k): int(v) for k, v in policy.get("ratchet", {}).items()}
    results: dict[str, dict[str, object]] = {}
    gaps: list[str] = []
    for package in zero_tolerance:
        package_result = _package_result(root, package, tier="zero_tolerance", limit=0)
        count = _count_value(package_result)
        results[package] = package_result
        if count > 0:
            gaps.append(f"ty_zero_tolerance_violation:{package}:{count}")
    for package, baseline in ratchet.items():
        package_result = _package_result(root, package, tier="ratchet", limit=baseline)
        count = _count_value(package_result)
        results[package] = package_result
        if count > baseline:
            gaps.append(f"ty_ratchet_exceeded:{package}:{count}>{baseline}")
    return {
        "ok": not gaps,
        "state": "clean" if not gaps else "blocked",
        "required_gaps": gaps,
        "packages": results,
    }
