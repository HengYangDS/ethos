"""A GitHub job that declares its supply-chain components stages syft before it needs it."""

from __future__ import annotations

import shlex
from typing import Any

import pytest
import yaml

import tools.ci.ci_projection as owner

ROOT = owner.ROOT


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))


def _staged(steps: list[dict[str, Any]]) -> set[str]:
    """The native tools that the job's supply step stages through native.py --mise."""
    staged: set[str] = set()
    for step in steps:
        words = shlex.split(str(step.get("run", "")))
        if "tools/ci/toolchain/native.py" in words and "--mise" in words:
            staged.update(words[words.index("--mise") + 1 :])
    return staged


def test_every_supply_chain_job_stages_syft(workflow: dict[str, Any]) -> None:
    """Syft is staged wherever the supply chain runs; otherwise it would need mise on PATH."""
    jobs = {
        name: job["steps"]
        for name, job in workflow["jobs"].items()
        if any("nox -s supply_chain" in str(step.get("run", "")) for step in job.get("steps", ()))
    }
    assert jobs, "no GitHub job runs the supply chain"
    assert {
        name: sorted(_staged(steps)) for name, steps in jobs.items() if "syft" not in _staged(steps)
    } == {}
