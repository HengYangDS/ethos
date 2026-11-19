"""A proof's result reports what its gates left in the lane, and the report decides nothing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.proof import declare_native_proof_checks

if TYPE_CHECKING:
    from pathlib import Path

_LEFT = "ETHOS_FIXTURE_LEFT_BYTES"
_GATE = f"""
import os
from pathlib import Path

size = int(os.environ.get('{_LEFT}', '0'))
if size:
    Path('build/evidence/quality').mkdir(parents=True)
    Path('build/evidence/quality/report.json').write_text('x' * size)
"""


@pytest.mark.parametrize("left", [0, 2048])
def test_two_proofs_that_differ_only_in_what_a_gate_left_decide_the_same(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, left: int
) -> None:
    """A real gate writes a report under the evidence home; the proof passes either way."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    (repo / ".gitignore").write_text("build/\n", encoding="utf-8")
    declare_native_proof_checks(repo, test=_GATE, typecheck="print('static green')")
    commit_fixture(repo, "ci: declare a gate that may leave a report")
    monkeypatch.setenv(_LEFT, str(left))
    head = git(repo, "rev-parse", "HEAD")

    proved = run_ethos("prove", "--full", "--execute", "--expect-head", head, "--json", cwd=repo)

    assert (proved["verdict"], proved["state"], proved["required_gaps"]) == ("pass", "proven", [])
    assert proved["data"]["footprint"] == (
        {
            "machine_evidence_files": 1,
            "machine_evidence_bytes": left,
            "new_roots": 1,
            "homes": {
                "build/evidence": {"files": 1, "bytes": left, "paths": ["quality/report.json"]}
            },
            "roots": ["build/"],
        }
        if left
        else {}
    )
