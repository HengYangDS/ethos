"""A declared command names the scratch directory of its attempt with `{scratch}`."""

from __future__ import annotations

import gc
import json
import sys
from pathlib import Path

import pytest

import ethos.adapters.gates.scratch as scratch
from ethos.adapters.actor import ACTOR_VARIABLE
from ethos.adapters.gates.host_admission import ADMISSION_ENV
from ethos.adapters.gates.host_work import work_owner
from ethos.adapters.gates.native.attempt import gate_attempt
from ethos.adapters.gates.native.evidence import native_report
from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.gates.runner import run_gate_graph
from ethos.adapters.gates.verification import NativeEvidence
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import run_git
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.governed_repository import init_git_repo

_WRITE = "import sys; open(sys.argv[1] + '/made', 'w').write('made'); print(sys.argv[1])"
_READ = "import sys; print(sys.argv[1], open(sys.argv[1] + '/made').read())"
_SHOW = "import json, os, sys; print(json.dumps([sys.argv[1:], os.getcwd(), sorted(os.environ)]))"


def _gate(name: str, script: str, argument: str, *depends_on: str) -> Gate:
    command = (sys.executable, "-c", script, argument)
    return Gate(id=name, kind="check", command=command, depends_on=depends_on, trust_bearing=True)


def _attempt(repo: Path, runner: LocalGateRunner, *gates: Gate) -> dict[str, ActionRunResult]:
    nodes = tuple(
        PlanNode(
            id=gate.id,
            kind="check",
            command=gate_execution_identity(gate),
            depends_on=gate.depends_on,
        )
        for gate in gates
    )
    registry = {gate.id: gate for gate in gates}
    results = run_gate_graph(runner, nodes, registry, root=repo, capacity=1, parallel=False)
    return {result.action_id: result for result in results}


def test_the_commands_of_one_attempt_share_a_marked_scratch_outside_the_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One command's file is another's input; the lane holds nothing; it ends with the runner."""
    monkeypatch.setenv(ADMISSION_ENV, "ticket")
    monkeypatch.setenv(ACTOR_VARIABLE, "agent/scratch")
    repo = init_git_repo(tmp_path / "repo")
    write, read = _gate("write", _WRITE, "{scratch}"), _gate("read", _READ, "{scratch}", "write")
    runner = LocalGateRunner()

    results = _attempt(repo, runner, write, read)

    assert [results[name].verdict for name in ("write", "read")] == ["pass", "pass"]
    made = Path(results["write"].stdout.strip())
    assert results["read"].stdout.split() == [str(made), "made"]
    assert made.is_dir()
    assert not made.resolve().is_relative_to(repo.resolve())
    assert work_owner(made.parent) == "agent/scratch"
    assert run_git(repo, "status", "--porcelain").stdout == ""
    assert results["write"].command == gate_execution_identity(write)
    assert "{scratch}" in results["write"].command
    del runner
    gc.collect()
    assert not made.parent.exists()


def test_the_scratch_of_a_failing_gate_ends_with_its_runner(tmp_path: Path) -> None:
    """A gate that fails keeps its scratch no longer than one that passes."""
    repo = init_git_repo(tmp_path / "repo")
    runner = LocalGateRunner()

    result = _attempt(repo, runner, _gate("fail", _WRITE + "; sys.exit(3)", "{scratch}"))["fail"]

    made = Path(result.stdout.strip())
    assert (result.verdict, result.exit_code, made.is_dir()) == ("block", 3, True)
    del runner
    gc.collect()
    assert not made.parent.exists()


def test_two_attempts_of_one_gate_have_equal_identities(tmp_path: Path) -> None:
    """The identity keeps the placeholder, so it does not follow an attempt's directory."""
    repo = init_git_repo(tmp_path / "repo")
    gate = _gate("write", _WRITE, "{scratch}")

    first, second = (_attempt(repo, LocalGateRunner(), gate)["write"] for _ in range(2))

    assert first.command == second.command
    assert (first.verdict, second.verdict) == ("pass", "pass")
    assert first.stdout != second.stdout


def test_a_command_without_the_placeholder_is_launched_as_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Its arguments, working directory and environment names are the launcher's own."""
    repo = init_git_repo(tmp_path / "repo")
    gate = _gate("show", _SHOW, "plain")
    monkeypatch.setattr(scratch, "mkdtemp", lambda **_options: pytest.fail("a scratch was made"))
    direct, _evidence = gate_attempt(repo, gate, gate.command, timeout=30)

    result = _attempt(repo, LocalGateRunner(), gate)["show"]

    arguments, directory, names = json.loads(result.stdout)
    assert [arguments, names] == [["plain"], json.loads(direct.stdout)[2]]
    assert Path(directory).resolve() == repo.resolve()


@pytest.mark.parametrize("recorded", ["made", "other"])
def test_native_evidence_binds_the_scratch_of_its_launch(tmp_path: Path, recorded: str) -> None:
    """The custody check reads the launched arguments with the attempt's scratch in place."""
    repo = init_git_repo(tmp_path / "repo")
    gate = Gate(
        id="native",
        kind="test",
        command=("tool", "{scratch}/in", "{native_output}/report.xml"),
        verification_providers=("ethos.adapters.gates.code_quality:behavior_report",),
        native_outputs=({"path": "report.xml", "format": "junit-xml", "sessions": ("tests",)},),
        trust_bearing=True,
    )
    evidence = NativeEvidence(
        gate=gate,
        head="head",
        tree="tree",
        subjects=(),
        output_root="out",
        outputs=((gate.native_outputs[0], b""),),
        gaps=(),
        artifact="artifact",
        scratch=recorded,
    )
    execution = NativeExecution(
        gate_execution_identity(gate),
        ("tool", "made/in", "out/report.xml"),
        repo.resolve(),
        0,
        "",
        "",
        executable="tool",
        evidence=evidence,
    )

    with pytest.raises((ValueError, ProcessExecutionError)) as refused:
        native_report(repo, execution, "behavior", language="javascript")

    assert ("native_selection_invalid" in str(refused.value)) is (recorded != "made")


def test_the_gate_schema_admits_a_command_that_names_the_scratch() -> None:
    gate = Gate(id="build", kind="check", command=("tool", "--out", "{scratch}/dist"))

    assert validate_schema_instance("gate.schema.json", gate.to_dict())["verdict"] == "pass"
