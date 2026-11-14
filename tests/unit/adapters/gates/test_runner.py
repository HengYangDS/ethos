"""Native gate execution preserves declared identity and provider verdicts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.gates.native.attempt as gate_attempt
import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.gates.tool as gate_tool
import ethos.adapters.gates.verification as gate_verification
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.paradigm.parameters import repository_parameters
from ethos.repository.policy.gates import gate_policy_fields
from ethos.repository.policy.quality.obligations import quality_obligation_gaps


def _gate(*providers: str) -> Gate:
    return Gate(id="gate", kind="test", providers=providers)


def _node(gate: Gate) -> PlanNode:
    return PlanNode(id=gate.id, kind="check", command=gate_runner.gate_execution_identity(gate))


def _runner(monkeypatch, **providers: object) -> gate_runner.LocalGateRunner:
    # These fixtures name their own callables, which the provider catalog does not hold.
    monkeypatch.setattr(gate_verification, "provider_target", str)
    monkeypatch.setattr(
        gate_verification.importlib, "import_module", lambda _: SimpleNamespace(**providers)
    )
    return gate_runner.LocalGateRunner()


@pytest.mark.parametrize("verified", [False, True])
def test_runner_transports_one_deadline_to_native_and_provider_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, verified: bool
) -> None:
    """The same declared budget reaches a command and its optional native verifier."""
    budgets: list[float | None] = []

    def provider(root: Path, *, timeout_seconds: float | None = None) -> dict[str, object]:
        assert root == tmp_path
        budgets.append(timeout_seconds)
        return {"verdict": "pass"}

    def command(
        _root: Path,
        argv: tuple[str, ...],
        *,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
        remove_env: tuple[str, ...] = (),
    ):
        assert env is None
        # Only the product-owned output root and observer are withheld from a gate without outputs.
        assert remove_env == ("ETHOS_NATIVE_OUTPUT_DIR", "ETHOS_NATIVE_OBSERVER_REQUIREMENT")
        budgets.append(timeout)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(gate_attempt, "run_command", command)
    runner = _runner(monkeypatch, report=provider)
    attributes = (
        {
            "command": (sys.executable, "-c", "pass"),
            "verification_providers": ("ethos.test:report",),
        }
        if verified
        else {"providers": ("ethos.test:report",)}
    )
    gate = Gate.model_validate(
        {"id": "bounded", "kind": "test", "timeout_seconds": 30, **attributes}
    )
    assert runner.run(_node(gate), gate, root=tmp_path).verdict == "pass"
    assert len(budgets) == (2 if verified else 1)
    assert all(budget is not None and 0 < budget <= 30 for budget in budgets)


@pytest.mark.parametrize(
    ("payload", "verdict", "gap"),
    [
        ({"verdict": "pass"}, "pass", ""),
        ({"verdict": "block"}, "block", "gate_provider_blocked:gate:ethos.test:report"),
        ({"ok": True}, "unknown", "gate_provider_unknown:gate:ethos.test:report"),
        (
            {"verdict": "pass", "warnings": ["deprecated"]},
            "block",
            "gate_provider_warning:gate:ethos.test:report:deprecated",
        ),
        ({"verdict": "pass", "diagnostics": [{"severity": "info", "message": "note"}]}, "pass", ""),
        ({"verdict": "pass", "required_gaps": "unproved"}, "block", ""),
        ({"verdict": "pass", "warnings": "deprecated"}, "block", ""),
        ({"verdict": "pass", "diagnostics": {"severity": "error", "message": "bad"}}, "block", ""),
    ],
)
def test_provider_report_preserves_verdict_and_root(monkeypatch, tmp_path, payload, verdict, gap):
    """Reduce provider truth without treating informational notes as warnings."""
    seen = []

    def report(root):
        seen.append(root)
        return payload

    gate = _gate("ethos.test:report", "ethos.test:second")

    def second(root):
        seen.append(("second", root))
        return {"verdict": "pass"}

    result = _runner(monkeypatch, report=report, second=second).run(
        _node(gate), gate, root=tmp_path
    )
    assert (result.verdict, result.exit_code) == (verdict, int(verdict != "pass"))
    assert seen == [tmp_path, ("second", tmp_path)]
    assert [item["provider"] for item in json.loads(result.stdout)["providers"]] == list(
        gate.providers
    )
    if gap:
        assert result.diagnostics[0]["required_gaps"] == [gap]


def test_legacy_name_runs_the_provider_of_its_id_and_a_note_names_that_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both spellings give one report; only the legacy one adds a note, which decides nothing."""

    def imported(module: str) -> object:
        report = {"verdict": "pass", "module": module}
        return SimpleNamespace(schema_validation_report=lambda _root: report)

    monkeypatch.setattr(gate_verification.importlib, "import_module", imported)
    legacy = "ethos.repository.policy.schema:schema_validation_report"
    by_id, by_name = (
        gate_runner.LocalGateRunner().run(_node(gate), gate, root=tmp_path)
        for gate in (_gate("provider.schemas"), _gate(legacy))
    )
    reports = [json.loads(result.stdout)["providers"][0]["report"] for result in (by_id, by_name)]
    assert reports == [{"verdict": "pass", "module": "ethos.repository.policy.schema"}] * 2
    assert (by_id.verdict, by_id.diagnostics, by_name.verdict) == ("pass", (), "pass")
    (note,) = by_name.diagnostics
    assert (note["severity"], note["code"]) == ("note", "gate_provider_legacy_name")
    assert "provider.schemas" in note["message"]


@pytest.mark.parametrize(
    ("command_exit", "provider_verdict", "expected_verdict", "expected_calls"),
    [(0, "pass", "pass", 1), (0, "block", "block", 1), (4, "pass", "block", 0)],
)
def test_verified_command_conjoins_native_and_product_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command_exit: int,
    provider_verdict: str,
    expected_verdict: str,
    expected_calls: int,
) -> None:
    """A passing provider cannot rescue a failed command, or vice versa."""
    calls: list[Path] = []

    def report(root: Path) -> dict[str, str]:
        calls.append(root)
        return {"verdict": provider_verdict}

    gate = Gate(
        id="gate",
        kind="test",
        command=(sys.executable, "-c", f"raise SystemExit({command_exit})"),
        verification_providers=("ethos.test:report",),
    )

    result = _runner(monkeypatch, report=report).run(_node(gate), gate, root=tmp_path)

    assert result.verdict == expected_verdict
    assert calls == [tmp_path] * expected_calls
    assert (result.verification is not None) == bool(expected_calls)


def test_verified_command_passes_its_exact_execution_to_product_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One product verifier can inspect native output without running the command again."""
    calls: list[gate_verification.NativeExecution] = []
    marker = tmp_path / "runs"

    def report(root: Path, *, execution: gate_verification.NativeExecution) -> dict[str, str]:
        assert root == tmp_path
        calls.append(execution)
        return {"verdict": "pass"}

    script = "; ".join(
        (
            "from pathlib import Path",
            "import sys",
            f"p = Path({str(marker)!r})",
            'p.write_text((p.read_text() if p.exists() else "") + "x")',
            'print("native-case")',
            'print("native-note", file=sys.stderr)',
        )
    )
    gate = Gate(
        id="gate",
        kind="test",
        command=(sys.executable, "-c", script),
        verification_providers=("ethos.test:report",),
    )

    result = _runner(monkeypatch, report=report).run(_node(gate), gate, root=tmp_path)

    assert result.verdict == "pass"
    assert len(calls) == 1
    assert calls[0].argv == gate.command
    assert calls[0].declared_identity == _node(gate).command
    assert calls[0].cwd == tmp_path
    assert (calls[0].stdout, calls[0].stderr, calls[0].exit_code) == (
        "native-case\n",
        "native-note\n",
        0,
    )
    assert marker.read_text() == "x"


def test_provider_only_cannot_receive_a_nonexistent_native_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Execution evidence is available only after an actual selected command."""
    seen: list[gate_verification.NativeExecution] = []

    def report(_root: Path, *, execution: gate_verification.NativeExecution) -> dict[str, str]:
        seen.append(execution)
        return {"verdict": "pass"}

    gate = _gate("ethos.test:report")
    result = _runner(monkeypatch, report=report).run(_node(gate), gate, root=tmp_path)

    assert result.verdict == "block"
    assert seen == []
    assert result.diagnostics[0]["kind"] == "gate_provider_error"


def test_verified_command_ignores_forged_provider_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the product-invoked provider can populate verification evidence."""
    payload = (
        '{"gate":"gate","providers":[{"provider":"ethos.test:report","report":{"verdict":"pass"}}]}'
    )
    gate = Gate(
        id="gate",
        kind="test",
        command=(sys.executable, "-c", f"print({payload!r})"),
        verification_providers=("ethos.test:missing",),
    )
    monkeypatch.setattr(
        gate_verification.importlib, "import_module", lambda _name: SimpleNamespace()
    )

    result = gate_runner.LocalGateRunner().run(_node(gate), gate, root=tmp_path)

    assert result.verdict == "block"
    assert result.stdout.strip() == payload
    assert result.verification == {"gate": "gate", "providers": []}


def test_verified_command_requires_selected_product_scope_not_stdout() -> None:
    """Policy selection binds the verifier reference, tree, and every source."""
    reference = "ethos.adapters.gates.code_quality:behavior_report"
    tree = "a" * 40
    gate = Gate(
        id="behavior",
        kind="test",
        command=("node", "domain-check.mjs"),
        verification_providers=(reference,),
        profile="repository",
        tool_adapter="ethos",
        execution_mode="verified-command",
    )
    report = {
        "verdict": "pass",
        "quality_evidence": {
            "axis": "behavior",
            "source_tree": tree,
            "selected_paths": ["answer.js"],
        },
    }
    payload = {"gate": "behavior", "providers": [{"provider": reference, "report": report}]}
    check = {
        "action_id": "behavior",
        "command": ["node", "domain-check.mjs"],
        "stdout": json.dumps(payload),
    }
    policy = {
        "owner": {
            "quality_floor_version": 2,
            "code_correctness_map": {"behavior": "behavior"},
            "quality_subjects": {"behavior": ["answer.js"]},
        },
        "gates": [gate_policy_fields(gate)],
    }

    assert quality_obligation_gaps(policy, (check,), source_tree=tree) == (
        "quality_obligation_unproven:behavior",
    )
    check["verification"] = payload
    assert quality_obligation_gaps(policy, (check,), source_tree=tree) == ()
    report["quality_evidence"]["source_tree"] = "b" * 40
    assert quality_obligation_gaps(policy, (check,), source_tree=tree) == (
        "quality_obligation_unproven:behavior",
    )


@pytest.mark.parametrize(
    ("tool_path", "outcome", "verdict", "state", "gap"),
    [
        (None, None, "unknown", "missing_tool", "quality_tool_missing:checker"),
        (None, None, "pass", "skipped", ""),
        (
            "/bin/checker",
            OSError("offline"),
            "unknown",
            "tool_error",
            "quality_tool_execution_unknown:quality",
        ),
        ("/bin/checker", subprocess.CompletedProcess([], 0, "ok", ""), "pass", "passed", ""),
        (
            "/bin/checker",
            subprocess.CompletedProcess([], 2, "x" * 5000, "failed"),
            "block",
            "failed",
            "quality_gate_failed:quality",
        ),
    ],
)
def test_quality_tool_public_failure_matrix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tool_path: str | None,
    outcome: subprocess.CompletedProcess[str] | OSError | None,
    verdict: str,
    state: str,
    gap: str,
) -> None:
    def which(_tool):
        if state == "skipped":
            pytest.fail("empty input must not resolve a host tool")
        return tool_path

    monkeypatch.setattr(gate_tool.shutil, "which", which)

    def run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if isinstance(outcome, OSError):
            raise outcome
        assert isinstance(outcome, subprocess.CompletedProcess)
        return outcome

    monkeypatch.setattr(gate_tool, "run_command", run)
    report = gate_tool.quality_tool_report(
        root=tmp_path,
        gate_id="quality",
        tool="checker",
        command=["checker", "--strict"],
        files=[] if state == "skipped" else ["src/example.py"],
    )

    assert (report["verdict"], report["state"]) == (verdict, state)
    assert report["required_gaps"] == ([gap] if gap else [])
    if state == "skipped":
        assert report["file_count"] == 0
    if state == "failed":
        assert (report["stdout"], report["stderr"]) == ("x" * 5000, "failed")


def test_command_gate_executes_declared_python_not_ambient_canonical_identity(
    monkeypatch, tmp_path: Path
) -> None:
    marker = tmp_path / "hijacked"
    fake_python = tmp_path / "python"
    fake_python.write_text(f"#!/bin/sh\nprintf hijacked > {marker}\nexit 91\n", encoding="utf-8")
    fake_python.chmod(0o755)
    monkeypatch.setenv("PATH", tmp_path.as_posix())
    gate = Gate(id="gate", kind="test", command=(sys.executable, "-c", "print('trusted')"))
    node = _node(gate)

    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)

    assert result.verdict == "pass"
    assert result.stdout == "trusted\n"
    assert not marker.exists()


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (RuntimeError("boom"), "RuntimeError: boom"),
        (KeyError("lost"), "KeyError: 'lost'"),
        (ZeroDivisionError("zero"), "ZeroDivisionError: zero"),
        ("not-a-mapping", "TypeError: gate provider must return a mapping: ethos.test:broken"),
        (
            {"verdict": "pass", "values": {1}},
            "TypeError: Object of type set is not JSON serializable",
        ),
    ],
)
def test_provider_exception_becomes_failed_result(
    monkeypatch, tmp_path: Path, outcome: object, expected: str
) -> None:
    """Any provider failure, or a report that cannot be recorded, blocks with the provider's gap."""

    def broken(_: Path) -> object:
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    gate = _gate("ethos.test:broken")
    result = _runner(monkeypatch, broken=broken).run(_node(gate), gate, root=tmp_path)

    assert (result.verdict, result.exit_code) == ("block", 1)
    (diagnostic,) = result.diagnostics
    assert diagnostic["kind"] == "gate_provider_error"
    assert diagnostic["error"] == expected
    assert diagnostic["required_gaps"] == ["gate_provider_error:gate:ethos.test:broken"]


@pytest.mark.parametrize("selection", ["absolute", "relative", "path", "dot-relative"])
def test_runner_preserves_python_virtual_environment_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selection: str
) -> None:
    """Following the executable symlink must not change the selected Python prefix."""
    environment = tmp_path / "selected-environment"
    if selection == "dot-relative":
        environment = tmp_path
    subprocess.run(
        [sys.executable, "-I", "-m", "venv", "--without-pip", str(environment)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if selection == "path":
        monkeypatch.setenv("PATH", str(python.parent) + os.pathsep + os.environ["PATH"])
        invocation = python.name
    else:
        invocation = str(python if selection == "absolute" else python.relative_to(tmp_path))
    if selection == "dot-relative":
        root = python.parent
        invocation = "./" + python.name
        monkeypatch.chdir(Path(sys.executable).parent)
    else:
        root = tmp_path
    command = (invocation, "-I", "-c", "import sys; print(sys.prefix)")
    gate = Gate(id="prefix", kind="test", command=command)
    result = gate_runner.LocalGateRunner().run(_node(gate), gate, root=root)
    assert result.verdict == "pass", result.stderr
    assert Path(result.stdout.strip()).resolve() == environment.resolve()


def test_canonical_dependency_audit_uses_fresh_release_acceptance(
    monkeypatch, tmp_path: Path
) -> None:
    """Release risk permission is read through the native audit, not raw-result relabeling."""
    observed = []

    def accepted(stdout, *, scope, **_options):
        observed.append((stdout, scope))
        return {"verdict": "pass", "reason": "authorized_findings"}

    monkeypatch.setattr(gate_runner, "captured_dependency_acceptance", accepted)
    monkeypatch.setattr(gate_runner, "current_tracked_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        gate_attempt,
        "run_command",
        lambda *_args, **_options: subprocess.CompletedProcess(
            [], 0, '{"command":"dependency-audit","verdict":"block"}', ""
        ),
    )
    gate = Gate(
        id="audit",
        kind="quality",
        tool_adapter="vulnerabilities",
        command=(sys.executable, "-m", "nox", "-s", "vulnerabilities"),
    )
    result = gate_runner.LocalGateRunner().run(_node(gate), gate, root=tmp_path)
    assert result.verdict == "pass"
    assert observed == [('{"command":"dependency-audit","verdict":"block"}', "production-release")]


@pytest.mark.parametrize("candidate", [False, True])
def test_provider_only_runner_transports_explicit_candidate_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, candidate: bool
) -> None:
    """Candidate selection is request-bound, not inferred from absent native execution."""
    observed = []

    def report(root, *, candidate=False):
        observed.append((root, candidate))
        return {"verdict": "pass"}

    _runner(monkeypatch, report=report)
    gate = _gate("ethos.test:report")
    runner = gate_runner.LocalGateRunner(candidate=candidate)
    assert runner.run(_node(gate), gate, root=tmp_path).verdict == "pass"
    assert observed == [(tmp_path, candidate)]


@pytest.mark.parametrize("fault", ["gate", "repository", "failure"])
def test_a_provider_keeps_its_native_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """An expired deadline is unknown with its bound and source; a failure keeps its output."""

    def report(_root: Path, *, timeout_seconds: float | None = None) -> dict[str, object]:
        if fault != "failure":
            raise subprocess.TimeoutExpired(("pytest",), timeout_seconds or 0, output=b"partial")
        raise subprocess.CalledProcessError(2, ("ruff", "check"), "o" * 2140, "e" * 2140)

    declared = {} if fault == "repository" else {"timeout_seconds": 5}
    providers = {"providers": ("ethos.test:report",), **declared}
    gate = Gate.model_validate({"id": "bounded", "kind": "test", **providers})
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos/rules.toml").write_text("[paradigm.timeout]\ngate_seconds = 5\n")
    with repository_parameters(tmp_path):
        result = _runner(monkeypatch, report=report).run(_node(gate), gate, root=tmp_path)
        source = gate_runner.gate_timeout(gate)
    (diagnostic,) = result.diagnostics
    if fault != "failure":
        assert (result.verdict, diagnostic["kind"], diagnostic["timeout_seconds"], source) == (
            "unknown",
            "gate_timeout",
            5,
            (5, fault),
        )
        assert diagnostic["required_gaps"] == ["gate_timeout:bounded"]
        assert diagnostic["stdout"] == "partial"
        assert 0 <= diagnostic["elapsed_seconds"] < 5
    else:
        assert (result.verdict, diagnostic["kind"], diagnostic["exit_code"]) == (
            "block",
            "gate_provider_error",
            2,
        )
        assert (diagnostic["command"], diagnostic["stdout"], diagnostic["stderr"]) == (
            ["ruff", "check"],
            "o" * 2140,
            "e" * 2140,
        )


def test_a_provider_that_returns_late_keeps_its_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late report decides nothing, but the result keeps what the provider observed."""
    clock = [100.0]
    monkeypatch.setattr(gate_verification, "monotonic", lambda: clock[0])
    observed = {"verdict": "pass", "native": {"stdout": "220 passed", "exit_code": 0}}

    def report(_root: Path, *, timeout_seconds: float | None = None) -> dict[str, object]:
        clock[0] += (timeout_seconds or 0) + 1
        return observed

    gate = Gate.model_validate(
        {"id": "late", "kind": "test", "timeout_seconds": 5, "providers": ("ethos.test:report",)}
    )
    result = _runner(monkeypatch, report=report).run(_node(gate), gate, root=tmp_path)

    (diagnostic,) = result.diagnostics
    assert (result.verdict, diagnostic["kind"], diagnostic["required_gaps"]) == (
        "unknown",
        "gate_timeout",
        ["gate_timeout:late"],
    )
    assert json.loads(result.stdout)["providers"] == [
        {"provider": "ethos.test:report", "report": observed}
    ]
