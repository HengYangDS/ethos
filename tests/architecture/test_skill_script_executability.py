from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_repo_local_skill_python_scripts_are_directly_executable() -> None:
    """Repo-local skill scripts advertised as executable checks must be runnable."""
    for package in (ROOT / ".agents" / "skills").glob("ethos-*/package.toml"):
        for line in package.read_text(encoding="utf-8").splitlines():
            stripped = line.strip().strip(",").strip('"')
            if not stripped.startswith("scripts/") or not stripped.endswith(".py"):
                continue
            script = package.parent / stripped
            assert script.exists(), f"{package}: missing included script {stripped}"
            assert os.access(script, os.X_OK), f"{script} must be directly executable"


def test_repository_governance_script_uses_the_shared_cli_contract() -> None:
    """The governance skill must use Cyclopts and one explicit root option."""
    script = ROOT / ".agents/skills/ethos-repository-governance/scripts/govern_check.py"
    text = script.read_text(encoding="utf-8")
    assert "from cyclopts import App" in text
    assert "--root" in text
    assert "govern_check.py [--root PATH]" in text
