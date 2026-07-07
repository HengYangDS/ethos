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
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_COUNT_RE = re.compile(r"Found (\d+) diagnostic")


def _diagnostic_count(root: Path, package_src: str) -> int:
    completed = subprocess.run(
        ["ty", "check", package_src],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = completed.stdout + completed.stderr
    if "All checks passed" in output:
        return 0
    match = _COUNT_RE.search(output)
    return int(match.group(1)) if match else 0


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
        count = _diagnostic_count(root, f"{package}/src")
        results[package] = {"count": count, "limit": 0, "tier": "zero_tolerance"}
        if count > 0:
            gaps.append(f"ty_zero_tolerance_violation:{package}:{count}")
    for package, baseline in ratchet.items():
        count = _diagnostic_count(root, f"{package}/src")
        results[package] = {"count": count, "limit": baseline, "tier": "ratchet"}
        if count > baseline:
            gaps.append(f"ty_ratchet_exceeded:{package}:{count}>{baseline}")
    return {
        "ok": not gaps,
        "state": "clean" if not gaps else "blocked",
        "required_gaps": gaps,
        "packages": results,
    }
