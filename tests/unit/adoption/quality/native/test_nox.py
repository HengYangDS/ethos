"""Consume official Nox, pytest, coverage and Ruff results without replay."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from ethos.adapters.gates.native.attempt import native_attempt
from ethos.adapters.gates.native.attempt import retained_execution
from ethos.adapters.gates.python_quality import behavior_report
from ethos.adapters.gates.python_quality import static_report
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.contracts.evidence.observer import ObserverIdentity
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import committed_source_repo

if TYPE_CHECKING:
    from tests.unit.adoption.quality.native.conftest import NativeNoxSupply


def _native_gate(root: Path, supply: NativeNoxSupply, outcome: str = "pass") -> Gate:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    behavior, static = f"behavior-{version}", f"static-{version}"
    source = f'''"""A native producer for one exact quality attempt."""
import json
import hashlib
import os
from pathlib import Path
import nox

VERSION = {version!r}
UV = {str(supply.uv)!r}
FLOOR = {str(supply.project)!r}
OUTCOME = {outcome!r}
nox.options.envdir = {str(supply.environments)!r}
nox.options.reuse_existing_virtualenvs = True

def prepare(session):
    requirement = os.environ["ETHOS_NATIVE_OBSERVER_REQUIREMENT"]
    from urllib.parse import urlsplit
    from urllib.request import url2pathname
    parsed = urlsplit(requirement.removeprefix("ethos @ "))
    wheel = Path(url2pathname(parsed.path))
    with wheel.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == parsed.fragment[7:]
    python = Path(session.virtualenv.location) / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python")
    session.run(UV, "sync", "--offline", "--frozen", "--no-default-groups", "--group", "dev",
        "--no-install-project", "--inexact", "--no-python-downloads", "--project", FLOOR,
        "--python", str(python), env={{"UV_PROJECT_ENVIRONMENT": str(session.virtualenv.location)}},
        external=True)
    session.run(UV, "pip", "install", "--offline", "--no-deps", "--python", str(python),
        requirement, external=True)
    return python

def runtime(session, python):
    output = Path(os.environ["ETHOS_NATIVE_OUTPUT_DIR"])
    session.run(str(python), "-B", "-I", "-c",
        "import json,sys; from pathlib import Path; "
        "from ethos.domain.quality.observer import runtime_identity; "
        "Path(sys.argv[1]).write_text(json.dumps(runtime_identity()))",
        str(output / (session.name + "-runtime.json")), external=True)
    return output

@nox.session(python=VERSION, venv_backend="uv")
def behavior(session):
    python = prepare(session)
    output = Path(os.environ["ETHOS_NATIVE_OUTPUT_DIR"])
    if OUTCOME == "runtime-detached":
        runtime(session, python)
    with (output / "behavior-count.txt").open("a") as stream:
        stream.write("one\\n")
    env = {{"COVERAGE_FILE": str(output / ".coverage")}}
    config = (".config/pytest-alternate/pytest.toml" if OUTCOME == "runtime-config"
              else ".config/pytest/pytest.toml")
    capture = [] if OUTCOME == "runtime-detached" else [
        "-p", "ethos.surface.pytest.plugin",
        "--ethos-runtime-output=" + str(output / (session.name + "-runtime.json")),
        "--ethos-native-session=" + session.name + "-" + VERSION,
    ]
    session.run(str(python), "-B", "-I", "-m", "pytest", "--rootdir", ".", "-c", config,
        *capture, "-q", "-W", "error",
        "--junitxml=" + str(output / "behavior.xml"),
        "--report-log=" + str(output / "behavior-events.jsonl"), "--cov=src",
        "--cov-branch", "--cov-report=xml:" + str(output / "coverage.xml"),
        "tests", env=env, external=True)

@nox.session(python=VERSION, venv_backend="uv")
def static(session):
    python = prepare(session)
    output = runtime(session, python)
    targets = ("src/app.py",) if OUTCOME == "static-scope" else ("src", "tests", "noxfile.py")
    config = ".config/ruff-alternate.toml" if OUTCOME == "static-config" else ".config/ruff.toml"
    if OUTCOME == "static-detached":
        session.run(str(python), "-m", "ruff", "check", "--config", config,
            "--output-format", "json", "--output-file", str(output / "ruff.json"),
            "src", "tests", "noxfile.py", external=True)
    else:
        binary = python.with_name("ruff.exe" if os.name == "nt" else "ruff")
        session.run(str(python), "-B", "-I", "-m", "ethos.domain.quality.nox", "run",
            "--runtime-output", str(output / (session.name + "-runtime.json")),
            "--session", session.name + "-" + VERSION, "--configuration", config, "--",
            str(binary), "check", "--config", config, "--verbose", "--no-cache",
            "--output-format", "json", "--output-file", str(output / "ruff.json"),
            *targets, external=True)
    if OUTCOME == "timeout":
        session.run(str(python), "-c",
            "import time; print('timeout-sentinel', flush=True); time.sleep(60)",
            external=True)
    if OUTCOME == "missing":
        (output / "coverage.xml").unlink()
    if OUTCOME == "junit":
        from xml.etree import ElementTree
        target = output / "behavior.xml"
        tree = ElementTree.fromstring(target.read_bytes())
        ElementTree.SubElement(next(tree.iter("testcase")), "failure")
        target.write_bytes(ElementTree.tostring(tree))
    if OUTCOME == "runtime":
        target = output / (session.name + "-runtime.json")
        value = json.loads(target.read_text())
        value["version"] = [0, 0, 0]
        target.write_text(json.dumps(value))
    if OUTCOME == "runtime-path":
        target = output / (session.name + "-runtime.json")
        value = json.loads(target.read_text())
        value["executable"] = str(output / "missing-interpreter")
        value["prefix"] = str(output / "missing-environment")
        target.write_text(json.dumps(value))
'''
    fixture = Path(__file__).resolve().parents[4] / "fixtures/quality-sample"
    metadata = (fixture / "pyproject.toml").read_text()
    lock = (fixture / "uv.lock").read_text()
    if outcome == "toolchain":
        lock = lock.replace(
            'name = "ruff"\nversion = "0.16.10"',
            'name = "ruff"\nversion = "0.0.1"',
        )
        assert 'name = "ruff"\nversion = "0.0.1"' in lock
    repo = committed_source_repo(
        root,
        {
            ".gitignore": ".nox/\n.pytest_cache/\n__pycache__/\n",
            ".gitattributes": "noxfile.py ethos-role=tooling\n",
            "noxfile.py": source,
            ".config/pytest/pytest.toml": (
                '[pytest]\npythonpath = ["../.."]\nfilterwarnings = ["error"]\n'
            ),
            ".config/pytest-alternate/pytest.toml": (
                '[pytest]\npythonpath = ["../.."]\nfilterwarnings = ["error"]\n'
            ),
            ".config/ruff.toml": '[lint]\nselect = ["F"]\n',
            ".config/ruff-alternate.toml": '[lint]\nselect = ["F"]\n',
            "pyproject.toml": metadata,
            **({"uv.lock": lock} if outcome != "lock-missing" else {}),
            "src/app.py": "def answer():\n    return 42\n",
            "tests/test_app.py": (
                "from src.app import answer\n\ndef test_answer(subtests):\n"
                "    for expected in (42, 42):\n"
                "        with subtests.test(expected=expected):\n"
                "            assert answer() == expected\n"
            ),
        },
    )
    supply.bind(repo)
    outputs = (
        {"path": "nox.json", "format": "nox-json", "sessions": (behavior, static)},
        {"path": "behavior.xml", "format": "junit-xml", "sessions": (behavior,)},
        {"path": "behavior-events.jsonl", "format": "pytest-jsonl", "sessions": (behavior,)},
        {"path": "coverage.xml", "format": "coverage-xml", "sessions": (behavior,)},
        {"path": "ruff.json", "format": "ruff-json", "sessions": (static,)},
        {
            "path": "behavior-runtime.json",
            "configuration": ".config/pytest/pytest.toml",
            "format": "python-runtime-json",
            "sessions": (behavior,),
            "python": version,
            "dependency_groups": ("absent",) if outcome == "group-missing" else ("dev",),
        },
        {
            "path": "static-runtime.json",
            "configuration": ".config/ruff.toml",
            "format": "python-runtime-json",
            "sessions": (static,),
            "python": version,
            "dependency_groups": ("absent",) if outcome == "group-missing" else ("dev",),
        },
    )
    return Gate.model_validate(
        {
            "id": "native-python",
            "kind": "test",
            "command": (
                str(supply.parent),
                "-B",
                "-I",
                "-m",
                "nox",
                "--non-interactive",
                "--nocolor",
                "-f",
                str(repo / "noxfile.py"),
                "-s",
                behavior,
                static,
                "--report",
                "{native_output}/nox.json",
            ),
            "verification_providers": (
                "ethos.adapters.gates.python_quality:behavior_report",
                "ethos.adapters.gates.python_quality:static_report",
            ),
            "native_outputs": outputs,
            "timeout_seconds": 15 if outcome == "timeout" else 45,
        }
    )


def test_native_nox_reports_qualify_the_original_attempt(
    tmp_path: Path, native_nox_supply: NativeNoxSupply
) -> None:
    """Two native sessions produce one complete, interpreter-bound observation."""
    gate = _native_gate(tmp_path, native_nox_supply)
    root = tmp_path / "repo"
    locks = {name: (root / name).read_bytes() for name in ("uv.lock", "pyproject.toml")}
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
    result = LocalGateRunner().run(node, gate, root=tmp_path / "repo")
    assert result.verdict == "pass", (result.stdout, result.stderr, result.verification)
    assert result.exit_code == 0
    assert result.verification is not None
    providers = result.verification["providers"]
    assert isinstance(providers, list)
    reports = [item["report"] for item in providers]
    assert reports[0]["tests"]["total"] == 3
    assert reports[0]["coverage"]["combined_percent"] == 100
    _, subjects = observe_quality_subjects(tmp_path / "repo", language="python")
    assert reports[0]["quality_evidence"]["selected_paths"] == [
        subject.path for subject in subjects if subject.requires_behavior
    ]
    assert reports[1]["quality_evidence"]["selected_paths"] == [
        subject.path for subject in subjects
    ]
    assert reports[1]["quality_evidence"]["axis"] == "static-analysis"
    assert reports[0]["native"]["same_attempt"] is True
    artifact_value = result.verification["native_artifact"]
    assert isinstance(artifact_value, str)
    artifact = Path(artifact_value)
    with ZipFile(artifact) as stored:
        identity = json.loads(stored.read("execution.json"))
        observer = identity["observer"]
        assert observer["wheel_sha256"] == native_nox_supply.wheel_sha256
        for output in gate.native_outputs:
            if output.format == "python-runtime-json":
                assert json.loads(stored.read("reports/" + output.path))["observer"] == observer
        checks = identity["dependency_checks"]
        assert len(checks) == 2
        assert {tuple(item["dependency_groups"]) for item in checks} == {("dev",)}
        assert all(
            json.loads(json.loads(stored.read(f"dependency-checks/{index}.json"))["stdout"])[
                "sync"
            ]["changes"]
            == []
            for index in range(len(checks))
        )
    assert all((root / name).read_bytes() == content for name, content in locks.items())
    assert not Path(identity["output_root"]).exists()
    selected = ObserverIdentity.from_requirement(
        observer["requirement"], observer["runtime_digest"]
    )
    selected.wheel.write_bytes(b"changed selected observer wheel\n")
    completed, refused = native_attempt(root, gate, gate.command, timeout=45)
    assert completed.returncode == 1
    assert refused.gaps == ("hook_runtime_wheel_provenance_missing",)
    assert refused.outputs == ()
    assert not Path(refused.output_root).exists()


@pytest.mark.parametrize(
    "outcome",
    ["missing", "runtime", "runtime-path", "junit", "toolchain", "lock-missing", "group-missing"],
)
def test_native_nox_reports_refuse_incomplete_producer_outputs(
    tmp_path: Path, native_nox_supply: NativeNoxSupply, outcome: str
) -> None:
    """Successful session text cannot repair missing evidence or another interpreter."""
    gate = _native_gate(tmp_path, native_nox_supply, outcome)
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
    result = LocalGateRunner().run(node, gate, root=tmp_path / "repo")
    assert result.verdict == "block"
    assert result.verification is not None or result.diagnostics
    if outcome == "toolchain":
        assert result.verification is not None
        artifact_value = result.verification["native_artifact"]
        assert isinstance(artifact_value, str)
        with ZipFile(Path(artifact_value)) as stored:
            assert "reports/behavior-runtime.json" in stored.namelist()
            checks = [name for name in stored.namelist() if name.startswith("dependency-checks/")]
            assert checks
            failed = json.loads(stored.read(checks[0]))
            assert failed["returncode"] != 0
            assert failed["stdout"] or failed["stderr"]
    if outcome == "junit":
        assert result.exit_code == 0
        assert result.verification is not None
        providers = result.verification["providers"]
        assert isinstance(providers, list)
        assert providers[0]["report"]["required_gaps"] == [
            "quality_behavior_pytest_junit_outcome_mismatch"
        ]


@pytest.mark.parametrize("outcome", ["runtime-detached", "runtime-config"])
def test_native_behavior_requires_same_run_configuration(
    tmp_path: Path, native_nox_supply: NativeNoxSupply, outcome: str
) -> None:
    """A separate interpreter print cannot qualify the actual pytest invocation."""
    gate = _native_gate(tmp_path, native_nox_supply, outcome)
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
    result = LocalGateRunner().run(node, gate, root=tmp_path / "repo")
    assert result.verdict == "block", result.verification
    assert result.verification is not None
    assert "python_native_pytest_invocation_unbound" in json.dumps(result.verification)


@pytest.mark.parametrize(
    ("outcome", "gap"),
    [
        ("static-detached", "python_native_static_invocation_unbound"),
        ("static-config", "python_native_static_invocation_unbound"),
        ("static-scope", "python_native_static_scope_incomplete"),
    ],
)
def test_native_static_requires_the_actual_checker_launch(
    tmp_path: Path, native_nox_supply: NativeNoxSupply, outcome: str, gap: str
) -> None:
    """A different environment or config cannot reuse another Ruff runtime print."""
    gate = _native_gate(tmp_path, native_nox_supply, outcome)
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
    result = LocalGateRunner().run(node, gate, root=tmp_path / "repo")
    assert result.verdict == "block", result.verification
    assert gap in json.dumps(result.verification)


@pytest.mark.parametrize("boundary", ["command", "outputs", "sessions", "runtime-scope"])
def test_native_evidence_is_bound_to_one_declared_attempt(
    tmp_path: Path, native_nox_supply: NativeNoxSupply, boundary: str
) -> None:
    """Original bytes cannot be promoted through a different command or producer scope."""
    gate = _native_gate(tmp_path, native_nox_supply)
    root = tmp_path / "repo"
    completed, evidence = native_attempt(root, gate, gate.command, timeout=45)
    execution = retained_execution(
        NativeExecution(
            gate_execution_identity(gate),
            tuple(completed.args),
            root.resolve(),
            completed.returncode,
            completed.stdout,
            completed.stderr,
            executable=gate.command[0],
            evidence=evidence,
        )
    )
    behavior = behavior_report(root, execution=execution)
    static = static_report(root, execution=execution)
    assert behavior["verdict"] == "pass", behavior
    assert static["verdict"] == "pass", static
    assert execution.evidence is not None
    if boundary == "command":
        execution = replace(execution, declared_identity=("different",))
    else:
        outputs = list(execution.evidence.outputs)
        if boundary == "outputs":
            descriptor, content = outputs[-1]
            outputs[-1] = (descriptor.model_copy(update={"path": "unselected.json"}), content)
        elif boundary == "sessions":
            descriptor, content = outputs[0]
            report = json.loads(content)
            report["sessions"].append(report["sessions"][0])
            outputs[0] = descriptor, json.dumps(report).encode()
        else:
            descriptor, content = outputs[-1]
            outputs[-1] = (
                descriptor.model_copy(update={"sessions": outputs[0][0].sessions}),
                content,
            )
            outputs = [entry for entry in outputs if entry[0].path != "behavior-runtime.json"]
        execution = replace(execution, evidence=replace(execution.evidence, outputs=tuple(outputs)))
    assert behavior_report(root, execution=execution)["verdict"] == "block"
    assert static_report(root, execution=execution)["verdict"] == "block"


def test_native_each_selected_session_requires_its_quality_outputs(
    tmp_path: Path, native_nox_supply: NativeNoxSupply
) -> None:
    """One reported session cannot lend its quality evidence to another session."""
    gate = _native_gate(tmp_path, native_nox_supply)
    extra = "unobserved-static"
    outputs = [
        output.model_copy(update={"sessions": (*output.sessions, extra)})
        if output.format == "nox-json"
        else output
        for output in gate.native_outputs
    ]
    runtime = next(output for output in outputs if output.format == "python-runtime-json")
    outputs.append(runtime.model_copy(update={"path": "extra-runtime.json", "sessions": (extra,)}))
    gate = gate.model_copy(update={"native_outputs": tuple(outputs)})
    root = tmp_path / "repo"
    completed, evidence = native_attempt(root, gate, gate.command, timeout=45)
    retained = retained_execution(
        NativeExecution(
            gate_execution_identity(gate),
            tuple(completed.args),
            root.resolve(),
            completed.returncode,
            completed.stdout,
            completed.stderr,
            executable=gate.command[0],
            evidence=evidence,
        )
    )
    assert retained.evidence is not None
    reports = list(retained.evidence.outputs)
    descriptor, content = reports[0]
    producer = json.loads(content)
    session = dict(producer["sessions"][-1])
    session["name"] = extra
    session["signatures"] = [extra]
    producer["sessions"].append(session)
    reports[0] = descriptor, json.dumps(producer).encode()
    runtime_content = next(
        content for output, content in reports if output.format == "python-runtime-json"
    )
    reports.append((outputs[-1], runtime_content))
    retained = replace(
        retained,
        evidence=replace(retained.evidence, outputs=tuple(reports), gaps=()),
    )
    for report in (behavior_report, static_report):
        assert report(root, execution=retained)["verdict"] == "block"


def test_native_timeout_preserves_partial_output_and_owned_cleanup(
    tmp_path: Path, native_nox_supply: NativeNoxSupply
) -> None:
    """A timed-out original command retains its partial reports before scratch disposal."""
    gate = _native_gate(tmp_path, native_nox_supply, "timeout")
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
    result = LocalGateRunner().run(node, gate, root=tmp_path / "repo")
    assert result.verdict == "unknown"
    assert result.exit_code == 124
    assert result.verification is not None
    artifact = result.verification["native_artifact"]
    assert isinstance(artifact, str)
    with ZipFile(artifact) as archive:
        assert "timeout-sentinel" in archive.read("stdout.txt").decode()
        metadata = json.loads(archive.read("execution.json"))
        assert metadata["gaps"][0] == "native_execution_timeout"
        assert "reports/behavior.xml" in archive.namelist()
    assert metadata["output_root"]
    assert not Path(metadata["output_root"]).exists()
