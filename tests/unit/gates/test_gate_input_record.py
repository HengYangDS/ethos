"""An executed exact-source run keys its gates, compares their verdicts and records the run."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.input_key as input_key
from ethos.adapters.store.state.schema import local_state_root
from ethos.result import expand_result
from tests.support.ethos_cli_runner import ROOT
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.proof import declare_native_proof_checks

if TYPE_CHECKING:
    from pathlib import Path

_PROGRAM = """
import os
import pathlib

if os.environ.get('ETHOS_SOURCE_PROBE'):
    pathlib.Path('README.md').write_text('# another source\\n')
"""


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A governed repository whose full proof runs two real command gates."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    declare_native_proof_checks(repo, test=_PROGRAM, typecheck="print('static green')")
    commit_fixture(repo, "ci: declare real proof gates")
    return repo


def _prove(root: Path, *plane: str) -> dict:
    """Run one executed exact-source proof command on its plane and return its whole result."""
    exact = ("--execute", "--expect-head", git(root, "rev-parse", "HEAD"), "--json")
    full = () if plane == ("--readiness",) else ("--full",)
    return expand_result(json.loads(run_ethos_raw("prove", *plane, *full, *exact, cwd=root).stdout))


def test_each_exact_source_run_is_recorded_and_compared_by_the_next(repository: Path) -> None:
    """Three planes share one record; a planted block is a note of a proof that stands."""
    runs = [_prove(repository, *plane) for plane in (("--readiness",), ("--host",), ())]
    store = local_state_root(repository)
    recorded = {path.name: path for path in (store / "gate-results").iterdir()}
    record = recorded[runs[2]["data"]["gate_inputs"]["record"]]
    rows = json.loads(record.read_text(encoding="utf-8"))["results"]
    planted = [row | {"verdict": "block"} for row in rows]
    input_key.record_results(
        store, {"schema": 1, "head": "h", "tree": "f" * 40, "results": planted}
    )
    runs.append(_prove(repository))
    artifact = (store / runs[3]["data"]["artifact_reference"]["path"]).read_text(encoding="utf-8")

    assert [run["data"]["gate_inputs"]["compared"] for run in runs] == [
        {state: len(rows)} for state in ("none", "agree", "agree", "mismatch")
    ]
    assert set(recorded) == {run["data"]["gate_inputs"]["record"] for run in runs[:3]}
    assert {(row["statement"], *row["opened"]) for row in rows} == {("declared",), ("tree",)}
    assert [(run["verdict"], run["required_gaps"]) for run in runs] == [("pass", [])] * 4
    assert [len(run["diagnostics"]) for run in runs] == [0, 0, 0, len(rows)]
    assert {(note["severity"], note["code"]) for note in runs[3]["diagnostics"]} == {
        ("note", "gate_input_mismatch")
    }
    assert "f" * 40 in runs[3]["diagnostics"][0]["message"]
    assert all(run["data"]["attestation"] for run in runs[2:])
    assert rows[0]["key"] not in artifact
    assert '"executable"' not in artifact
    assert "gate_input_mismatch" not in artifact


def test_a_store_that_refuses_the_record_changes_no_proof(repository: Path) -> None:
    """The record is a cache: a proof without one passes, and its result names it unavailable."""
    store = local_state_root(repository)
    store.mkdir(parents=True, exist_ok=True)
    (store / "gate-results").write_text("", encoding="utf-8")

    proof = _prove(repository)

    assert (proof["verdict"], proof["required_gaps"]) == ("pass", [])
    assert proof["data"]["attestation"]
    assert proof["data"]["gate_inputs"] == {"record": "", "unavailable": "FileExistsError"}


@pytest.mark.parametrize("plane", [(), ("--host",)])
def test_a_run_whose_source_changed_under_its_gates_records_nothing(
    repository: Path, monkeypatch, plane
) -> None:
    """No key and no verdict of a run is kept once its source no longer equals the commit.

    The gate ran and the run names the changed source: a run refused before its gates would
    record nothing for another reason.
    """
    monkeypatch.setenv("ETHOS_SOURCE_PROBE", "1")

    result = _prove(repository, *plane)

    assert (repository / "README.md").read_text(encoding="utf-8") == "# another source\n"
    assert result["required_gaps"][0] == "proof_execution_source_changed"
    assert "gate_inputs" not in result["data"]
    assert ("footprint" in result["data"]) is (plane == ())
    assert not (local_state_root(repository) / "gate-results").exists()


def test_a_governed_run_of_an_edited_tree_ends_before_its_gates_and_any_record(
    repository: Path,
) -> None:
    """The governed call reads no source of its own for the record: such a run never reaches it."""
    write_active_commitment(repository)
    commit_fixture(repository, "docs(openspec): declare fixture-change")
    (repository / "README.md").write_text("# edited, not committed\n", encoding="utf-8")
    exact = ("--execute", "--expect-head", git(repository, "rev-parse", "HEAD"), "--json")

    result = expand_result(json.loads(run_ethos_raw("prove", *exact, cwd=repository).stdout))

    assert result["required_gaps"] == ["proof_execution_source_mismatch"]
    assert not (local_state_root(repository) / "gate-results").exists()


def test_only_a_run_s_own_readiness_results_stand_for_a_gate() -> None:
    """No recorded result reaches the runner: each caller settles gates from its own tier run."""
    source = ROOT / "src/ethos"
    passing = {
        path.relative_to(source).as_posix(): text
        for path in source.rglob("*.py")
        if "settled=" in (text := path.read_text(encoding="utf-8"))
    }

    assert set(passing) == {"application/proof/host.py", "application/proof/operation.py"}
    assert [text.count("for result in readiness}") for text in passing.values()] == [1, 1]
