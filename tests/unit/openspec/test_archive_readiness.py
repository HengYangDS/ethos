"""Proof requires the selected Change to archive into strictly valid specifications."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.proof import declare_native_proof_checks
from tests.support.proof import proof_repository

if TYPE_CHECKING:
    from pathlib import Path

_MARKER = (
    "from pathlib import Path\n"
    "Path('build').mkdir(exist_ok=True)\n"
    "Path('build/ran').write_text('executed')\n"
)
_REQUIREMENT = "The governed fixture SHALL remain valid throughout its lifecycle."


def _modify_fixture_requirement(repo: Path, length: int) -> str:
    text = f"{_REQUIREMENT} {'x' * (length - len(_REQUIREMENT) - 1)}"
    assert len(text) == length
    delta = repo / "openspec/changes/proof-binding/specs/contracts/spec.md"
    delta.write_text(
        "## MODIFIED Requirements\n\n### Requirement: Governed fixture\n\n"
        f"{text}\n\n#### Scenario: Fixture is exercised\n\n"
        "- **WHEN** the test lifecycle runs\n"
        "- **THEN** the governed fixture remains valid\n",
        encoding="utf-8",
    )
    return commit_fixture(repo, "docs(openspec): modify the fixture requirement")


@pytest.mark.parametrize("length", [500, 501])
def test_proof_gates_run_only_after_the_selected_change_archives_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, length: int
) -> None:
    repo, _head = proof_repository(tmp_path / "repo")
    (repo / ".gitignore").write_text("build/\n", encoding="utf-8")
    declare_native_proof_checks(repo, test=_MARKER, typecheck="print('static green')")
    commit_fixture(repo, "ci: declare real proof gates")
    head = _modify_fixture_requirement(repo, length)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", scratch.as_posix())

    completed = run_ethos_raw(
        "prove", "--full", "--execute", "--expect-head", head, "--json", cwd=repo
    )
    report = json.loads(completed.stdout)

    archivable = length == 500
    assert (completed.returncode == 0, report["verdict"]) == (
        (True, "pass") if archivable else (False, "block")
    )
    assert report["required_gaps"] == (
        []
        if archivable
        else ["openspec_archived_requirement_invalid:proof-binding:contracts:Governed fixture"]
    )
    assert (repo / "build/ran").exists() is archivable
    assert list(scratch.iterdir()) == []
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain=v1") == ""
