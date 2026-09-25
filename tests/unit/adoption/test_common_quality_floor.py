"""Reject native gate success that proves no applicable quality property."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_success_only_commands_do_not_qualify_broken_code(tmp_path: Path) -> None:
    """Two successful commands cannot prove behavior or static correctness."""
    repo = init_git_repo(tmp_path / "adopter")
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "false-gate-adopter"\n\n'
        '[openspec]\nmaterial_paths = ["**"]\n\n'
        '[proof]\ncode_correctness_gates = ["behavior", "static"]\n\n'
        "[proof.code_correctness_map]\n"
        'behavior = "behavior"\nstatic-analysis = "static"\n\n'
        '[[proof.gates]]\nid = "behavior"\nkind = "test"\n'
        f"command = {json.dumps([sys.executable, '-c', 'pass'])}\n"
        'dimensions = ["behavior"]\n\n'
        '[[proof.gates]]\nid = "static"\nkind = "typing"\n'
        f"command = {json.dumps([sys.executable, '-c', 'print("ok")'])}\n"
        'dimensions = ["static-analysis"]\n',
        encoding="utf-8",
    )
    (repo / "src").mkdir()
    (repo / "src/app.py").write_text('raise RuntimeError("broken")\n', encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests/test_app.py").write_text('raise AssertionError("not run")\n', encoding="utf-8")
    head = commit_fixture(repo, "declare native checks")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert any(
        str(gap).startswith("quality_obligation_unproven:") for gap in payload["required_gaps"]
    )
