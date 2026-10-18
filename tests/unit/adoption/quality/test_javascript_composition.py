"""Native launcher composition preserves one test attempt and both outcomes."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from zipfile import ZipFile

import pytest

from ethos.adapters.gates.runner import LocalGateRunner
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import committed_source_repo


@pytest.mark.parametrize("command", ["check", "test"])
@pytest.mark.parametrize("outcome", ["pass", "warning", "failure"])
def test_verified_launcher_keeps_native_prerequisite_and_outer_attempt(
    tmp_path: Path, command: str, outcome: str
) -> None:
    """A wrapper test is reused; a document command gets its own test prerequisite."""
    repo = committed_source_repo(
        tmp_path,
        {
            ".gitignore": "launcher-runs\ntest-runs\n",
            "package.json": json.dumps(
                {"type": "module", "scripts": {"test": "node tools.mjs test"}}
            ),
            "answer.mjs": "export function answer() { return 42; }\n",
            "answer.test.mjs": (
                'import test from "node:test"; import {appendFileSync} from "node:fs";\n'
                'import {answer} from "./answer.mjs";\n'
                'test("answer", () => { appendFileSync("test-runs", "x");\n'
                + ('process.emitWarning("native warning");\n' if outcome == "warning" else "")
                + ('throw Error("native failure");\n' if outcome == "failure" else "")
                + 'if (answer() !== 42) throw Error("wrong answer"); });\n'
            ),
            "tools.mjs": (
                'import {appendFileSync} from "node:fs";\n'
                'import {spawnSync} from "node:child_process";\n'
                'appendFileSync("launcher-runs", "x");\n'
                'if (process.argv[2] === "test") {\n'
                '  console.log("native launcher started tests");\n'
                "  const result = spawnSync(process.execPath,\n"
                '    ["--test", "--test-concurrency=2", "answer.test.mjs"],\n'
                '    {stdio: "inherit", timeout: 10000});\n'
                "  if (result.error) throw result.error;\n"
                "  process.exitCode = result.status;\n"
                '} else { console.log("document integrity checked"); }\n'
            ),
        },
    )
    gate = Gate(
        id="integrity",
        kind="test",
        command=("node", "tools.mjs", command),
        verification_providers=("ethos.adapters.gates.code_quality:behavior_report",),
        timeout_seconds=30,
    )
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
    result = LocalGateRunner().run(node, gate, root=repo)
    assert result.verdict == ("pass" if outcome == "pass" else "block"), result
    assert (repo / "launcher-runs").read_text() == ("x" if command == "test" else "xx")
    assert (repo / "test-runs").read_text() == "x"
    assert result.command == gate.command
    assert result.verification is not None
    providers = result.verification["providers"]
    assert isinstance(providers, list)
    report = providers[0]["report"]
    assert isinstance(report, dict)
    native = report["native"][0]
    artifact = native["artifact"]
    assert isinstance(artifact, dict)
    with ZipFile(artifact["path"]) as archive:
        observed = json.loads(archive.read("observation.json"))
    assert observed["outer_execution"]["argv"][-1] == command
    assert observed["test_execution"]["exit_code"] == int(outcome == "failure")
    assert "native launcher started tests" in observed["stdout"]
    assert observed["journal"] != observed["stdout"]
    assert observed["raw_identity_preserved"]
    assert not Path(observed["raw_directory"]).exists()


@pytest.mark.parametrize("condition", ["unbound", "changed"])
def test_native_attempt_source_refusal_is_a_gate_result(tmp_path: Path, condition: str) -> None:
    """Missing or changed source cannot escape as an exception or qualify a test."""
    if condition == "unbound":
        repo = tmp_path / "unbound"
        repo.mkdir()
    else:
        repo = committed_source_repo(
            tmp_path,
            {
                "package.json": '{"type":"module"}\n',
                "answer.mjs": "export const answer = 42;\n",
                "answer.test.mjs": (
                    'import test from "node:test"; import {writeFileSync} from "node:fs";\n'
                    'import {answer} from "./answer.mjs";\n'
                    'test("source changes", () => {\n'
                    'writeFileSync("answer.mjs", "export const answer = 0;\\n");\n'
                    'if (answer !== 42) throw Error("wrong answer"); });\n'
                ),
            },
        )
    gate = Gate(
        id="source-bound",
        kind="test",
        command=("node", "--test", "answer.test.mjs"),
        verification_providers=("ethos.adapters.gates.code_quality:behavior_report",),
        timeout_seconds=30,
    )
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
    result = LocalGateRunner().run(node, gate, root=repo)
    assert result.verdict == "block"
    assert result.command == gate.command
    assert result.diagnostics
    assert any("source" in json.dumps(diagnostic) for diagnostic in result.diagnostics)
    if condition == "changed":
        diagnostic = result.diagnostics[-1]
        assert diagnostic["kind"] == "native_source_binding"
        artifact = diagnostic["observation"]["artifact"]
        with ZipFile(artifact["path"]) as archive:
            observed = json.loads(archive.read("observation.json"))
            assert observed["source_tree"] == diagnostic["observation"]["source_tree"]
            assert archive.read("journal.jsonl")
            assert any(name.startswith("raw/") for name in archive.namelist())


def test_native_timeout_retains_partial_output_and_owned_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interruption retains native partial input without inventing a successful test."""
    # The child starts slower than the gate timeout, as under host contention. The timeout
    # starts only once it has written its partial output, so it always interrupts that child.
    ready = tmp_path / "ready"
    communicate = subprocess.Popen.communicate

    def after_ready(process: subprocess.Popen, *args: object, **kwargs: object) -> object:
        deadline = time.monotonic() + 60
        while process.poll() is None and not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        return communicate(process, *args, **kwargs)

    monkeypatch.setattr(subprocess.Popen, "communicate", after_ready)
    repo = committed_source_repo(
        tmp_path,
        {
            "package.json": '{"type":"module"}\n',
            "answer.mjs": "export const answer = 42;\n",
            "answer.test.mjs": (
                'import test from "node:test"; import {answer} from "./answer.mjs";\n'
                'test("answer", () => { if (answer !== 42) throw Error(); });\n'
            ),
            "launcher.mjs": (
                'import {writeFileSync} from "node:fs"; import {takeCoverage} from "node:v8";\n'
                "await new Promise((resolve) => setTimeout(resolve, 1500));\n"
                'console.log("native attempt started"); takeCoverage();\n'
                'process.stderr.write("native partial diagnostic\\n", () =>\n'
                f'  writeFileSync({json.dumps(str(ready))}, ""));\n'
                "setTimeout(() => {}, 10000);\n"
            ),
        },
    )
    gate = Gate(
        id="interrupted",
        kind="test",
        command=("node", "launcher.mjs"),
        verification_providers=("ethos.adapters.gates.code_quality:behavior_report",),
        timeout_seconds=1,
    )
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
    result = LocalGateRunner().run(node, gate, root=repo)
    assert result.verdict == "unknown"
    assert result.exit_code == 124
    assert result.stdout == "native attempt started\n"
    assert result.stderr == "native partial diagnostic\n"
    diagnostic = result.diagnostics[0]
    assert diagnostic["kind"] == "gate_timeout"
    with ZipFile(diagnostic["observation"]["artifact"]["path"]) as archive:
        observed = json.loads(archive.read("observation.json"))
        assert observed["stdout"] == result.stdout
        assert observed["stderr"] == result.stderr
        assert observed["source_tree"]
        assert any(name.startswith("raw/") for name in archive.namelist())
        assert not Path(observed["raw_directory"]).exists()
