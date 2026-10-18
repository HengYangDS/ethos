"""Consume official Nox, pytest, coverage and Ruff results without replay."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

import ethos.adapters.gates.native.attempt as gate_attempt
from ethos.adapters.gates.native.attempt import native_attempt
from ethos.adapters.gates.native.attempt import retained_execution
from ethos.adapters.gates.python_quality import behavior_report
from ethos.adapters.gates.python_quality import static_report
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.contracts.evidence.observer import ObserverIdentity
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import commit_fixture
from tests.support.native_quality import native_quality_gate

if TYPE_CHECKING:
    from tests.unit.adoption.quality.native.conftest import NativeNoxSupply


def test_native_nox_reports_qualify_the_original_attempt(
    tmp_path: Path, native_nox_supply: NativeNoxSupply
) -> None:
    """Two native sessions produce one complete, interpreter-bound observation."""
    gate = native_quality_gate(tmp_path, native_nox_supply)
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


def test_native_static_quality_requires_semantic_code_identities(
    tmp_path: Path, native_nox_supply: NativeNoxSupply
) -> None:
    """A clean native Ruff result cannot certify a numbered authored identity."""
    gate = native_quality_gate(tmp_path, native_nox_supply)
    root = tmp_path / "repo"
    source = root / "src/app.py"
    source.write_text(source.read_text() + "\nanswer_v2 = 42\n", encoding="utf-8")
    commit_fixture(root, "declare a nonsemantic identity")
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))

    result = LocalGateRunner().run(node, gate, root=root)

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.verdict == "block"
    assert result.verification is not None
    providers = result.verification["providers"]
    assert isinstance(providers, list)
    reports = [item["report"] for item in providers]
    assert reports[0]["verdict"] == "pass"
    assert reports[1]["required_gaps"] == [
        "quality_static_code_identifier_semantics:src/app.py:4:answer_v2"
    ]


@pytest.mark.parametrize(
    "outcome",
    ["missing", "runtime", "runtime-path", "junit", "toolchain", "lock-missing", "group-missing"],
)
def test_native_nox_reports_refuse_incomplete_producer_outputs(
    tmp_path: Path, native_nox_supply: NativeNoxSupply, outcome: str
) -> None:
    """Successful session text cannot repair missing evidence or another interpreter."""
    gate = native_quality_gate(tmp_path, native_nox_supply, outcome)
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
    gate = native_quality_gate(tmp_path, native_nox_supply, outcome)
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
    gate = native_quality_gate(tmp_path, native_nox_supply, outcome)
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))
    result = LocalGateRunner().run(node, gate, root=tmp_path / "repo")
    assert result.verdict == "block", result.verification
    assert gap in json.dumps(result.verification)


@pytest.mark.parametrize("boundary", ["command", "outputs", "sessions", "runtime-scope"])
def test_native_evidence_is_bound_to_one_declared_attempt(
    tmp_path: Path, native_nox_supply: NativeNoxSupply, boundary: str
) -> None:
    """Original bytes cannot be promoted through a different command or producer scope."""
    gate = native_quality_gate(tmp_path, native_nox_supply)
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
    gate = native_quality_gate(tmp_path, native_nox_supply)
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
    gate = native_quality_gate(tmp_path, native_nox_supply, "timeout")
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


def test_native_reports_refuse_an_altered_attempt_record(
    tmp_path: Path, native_nox_supply: NativeNoxSupply
) -> None:
    """Every field of the retained attempt record stays bound to the original run."""
    gate = native_quality_gate(tmp_path, native_nox_supply)
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
    assert execution.evidence is not None
    outputs = execution.evidence.outputs
    without_report = tuple(item for item in outputs if item[0].format != "nox-json")
    without_findings = tuple(item for item in outputs if item[0].format != "ruff-json")
    altered = {
        "python_native_evidence_unavailable": replace(execution, evidence=None),
        "native_output_missing:nox.json": replace(
            execution,
            evidence=replace(execution.evidence, gaps=("native_output_missing:nox.json",)),
        ),
        "python_native_custody_missing": replace(execution, cwd=tmp_path.resolve()),
        "python_native_source_changed": replace(
            execution, evidence=replace(execution.evidence, head="0" * 40)
        ),
        "python_native_execution_failed": replace(execution, exit_code=1),
        "python_native_selection_invalid": replace(
            execution, evidence=replace(execution.evidence, outputs=without_report)
        ),
        "python_native_dependency_floor_unbound": replace(
            execution, evidence=replace(execution.evidence, dependency_checks=())
        ),
    }

    def with_content(kind: str, original: bytes, mutated: bytes) -> NativeExecution:
        assert execution.evidence is not None
        changed = []
        for descriptor, content in outputs:
            if descriptor.format == kind:
                assert original in content, (kind, content)
            changed.append(
                (
                    descriptor,
                    content.replace(original, mutated) if descriptor.format == kind else content,
                )
            )
        return replace(execution, evidence=replace(execution.evidence, outputs=tuple(changed)))

    altered["python_native_coverage_scope_incomplete"] = with_content(
        "coverage-xml", b'hits="1"', b'hits="0"'
    )
    altered["python_native_tests_failed"] = with_content(
        "pytest-jsonl", b'"exitstatus": 0', b'"exitstatus": 1'
    )

    def with_record(path: str, field: str, value: object) -> NativeExecution:
        assert execution.evidence is not None
        record = json.loads(next(content for item, content in outputs if item.path == path))
        (record["ruff"] if field == "argv" else record)[field] = value
        changed = tuple(
            (item, json.dumps(record).encode() if item.path == path else content)
            for item, content in outputs
        )
        return replace(execution, evidence=replace(execution.evidence, outputs=changed))

    altered["python_native_toolchain_unbound"] = with_record(
        "behavior-runtime.json", "version", [2, 7, 0]
    )
    altered["python_native_observer_identity_unbound"] = with_record(
        "behavior-runtime.json", "observer", None
    )
    altered["python_native_static_invocation_unbound"] = with_record(
        "static-runtime.json", "argv", ["ruff", "check"]
    )
    for gap, record in altered.items():
        report = behavior_report(root, execution=record)
        assert report["verdict"] == "block", (gap, report)
        assert gap in json.dumps(report), (gap, report)
    static = static_report(
        root,
        execution=replace(
            execution, evidence=replace(execution.evidence, outputs=without_findings)
        ),
    )
    assert "python_native_selection_invalid" in json.dumps(static), static
    diagnosed = with_content("ruff-json", b"[]", b'[{"code": "F401"}]')
    findings = static_report(root, execution=diagnosed)
    assert "python_native_static_diagnostics" in json.dumps(findings), findings


def test_native_attempt_refuses_uncommitted_source_before_launch(
    tmp_path: Path, native_nox_supply: NativeNoxSupply
) -> None:
    """A dirty tracked source cannot be measured as the committed subject."""
    gate = native_quality_gate(tmp_path, native_nox_supply)
    root = tmp_path / "repo"
    project = root / "pyproject.toml"
    project.write_text(project.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"^native_source_changed$"):
        native_attempt(root, gate, gate.command, timeout=45)


@pytest.mark.parametrize("captured", [False, True])
def test_gate_attempt_preserves_scoped_environment_and_native_output_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    native_nox_supply: NativeNoxSupply,
    *,
    captured: bool,
) -> None:
    """One launch keeps caller isolation while native output and observer stay product-owned."""
    gate = native_quality_gate(tmp_path, native_nox_supply)
    script = (
        "import json, os, pathlib; "
        "result = json.dumps({name: os.environ.get(name) for name in "
        "('ETHOS_CALLER_VALUE', 'NODE_OPTIONS', 'ETHOS_NATIVE_OBSERVER_REQUIREMENT')}); "
        "target = os.environ.get('ETHOS_NATIVE_OUTPUT_DIR'); "
        "pathlib.Path(target, 'ruff.json').write_text(result) if target else print(result)"
    )
    outputs = tuple(output for output in gate.native_outputs if output.format == "ruff-json")
    gate = gate.model_copy(
        update={
            "command": (sys.executable, "-c", script),
            "native_outputs": outputs if captured else (),
        }
    )
    monkeypatch.setenv("NODE_OPTIONS", "unselected ambient input")
    environment = {"ETHOS_CALLER_VALUE": "scoped"}
    caller_output = tmp_path / "caller-output"
    if captured:
        environment.update(
            ETHOS_NATIVE_OUTPUT_DIR=str(caller_output),
            ETHOS_NATIVE_OBSERVER_REQUIREMENT="unselected caller observer",
        )
    completed, evidence = gate_attempt.gate_attempt(
        tmp_path / "repo",
        gate,
        gate.command,
        timeout=45,
        env=environment,
        remove_env=("NODE_OPTIONS",),
    )
    assert completed.returncode == 0
    observed = json.loads(evidence.outputs[0][1] if evidence is not None else completed.stdout)
    assert observed == {
        "ETHOS_CALLER_VALUE": "scoped",
        "NODE_OPTIONS": None,
        "ETHOS_NATIVE_OBSERVER_REQUIREMENT": None,
    }
    assert (evidence is not None) is captured
    assert not caller_output.exists()
    if evidence is not None:
        assert evidence.gaps == ()
        assert not Path(evidence.output_root).exists()


@pytest.mark.parametrize(
    ("outcome", "gap"),
    [
        ("unsafe-output", "native_output_unsafe:coverage.xml"),
        ("dirty-source", "native_source_changed"),
        ("advance-head", "native_source_changed"),
        ("commit-change", "code_source_changed"),
    ],
)
def test_native_attempt_reports_unsafe_output_and_changed_source(
    tmp_path: Path, native_nox_supply: NativeNoxSupply, outcome: str, gap: str
) -> None:
    """A non-regular report or a source edit during the run cannot become evidence."""
    gate = native_quality_gate(tmp_path, native_nox_supply, outcome)
    _, evidence = native_attempt(tmp_path / "repo", gate, gate.command, timeout=45)
    assert gap in evidence.gaps, evidence.gaps
