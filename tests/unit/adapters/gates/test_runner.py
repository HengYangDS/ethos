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
from ethos.repository.policy.gates import gate_policy_fields
from ethos.repository.policy.quality.obligations import quality_obligation_gaps
from tests.support.governed_repository import committed_source_repo


def _gate(*providers: str) -> Gate:
    return Gate(id="gate", kind="test", providers=providers)


def _node(gate: Gate) -> PlanNode:
    return PlanNode(id=gate.id, kind="check", command=gate_runner.gate_execution_identity(gate))


def _runner(monkeypatch, **providers: object) -> gate_runner.LocalGateRunner:
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

    def command(_root: Path, argv: tuple[str, ...], *, timeout: float | None = None):
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


@pytest.mark.parametrize(
    ("command_exit", "provider_verdict", "expected_verdict", "expected_calls"),
    [
        (0, "pass", "pass", 1),
        (0, "block", "block", 1),
        (4, "pass", "block", 0),
    ],
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
        assert report["stdout"] == "x" * 5000


def test_markdown_link_gate_excludes_deleted_tracked_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing selected source fails before the native checker can omit it."""
    repo = committed_source_repo(
        tmp_path,
        {
            ".config/checks/lychee/lychee.toml": "offline = true\n",
            "README.md": "# Current\n",
            "docs/deleted.md": "# Deleted\n",
        },
    )
    (repo / "docs/deleted.md").unlink()
    observed: list[tuple[str, ...]] = []

    def run(
        _root: Path, command: tuple[str, ...], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(gate_tool, "run_command", run)

    report = gate_tool.markdown_links_report(repo)

    assert report["verdict"] == "unknown", report
    assert report["file_count"] == 3
    assert report["required_gaps"] == ["source_member_link_or_type_forbidden:docs/deleted.md"]
    assert not observed


def test_command_gate_executes_declared_python_not_ambient_canonical_identity(
    monkeypatch, tmp_path: Path
) -> None:
    marker = tmp_path / "hijacked"
    fake_python = tmp_path / "python"
    fake_python.write_text(
        f"#!/bin/sh\nprintf hijacked > {marker}\nexit 91\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    monkeypatch.setenv("PATH", tmp_path.as_posix())
    gate = Gate(
        id="gate",
        kind="test",
        command=(sys.executable, "-c", "print('trusted')"),
    )
    node = _node(gate)

    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)

    assert result.verdict == "pass"
    assert result.stdout == "trusted\n"
    assert not marker.exists()


@pytest.mark.parametrize("non_mapping", [False, True])
def test_provider_exception_becomes_failed_result(monkeypatch, tmp_path: Path, non_mapping) -> None:
    def broken(_: Path):
        if non_mapping:
            return "not-a-mapping"
        message = "boom"
        raise RuntimeError(message)

    gate = _gate("ethos.test:broken")
    result = _runner(monkeypatch, broken=broken).run(_node(gate), gate, root=tmp_path)

    assert (result.verdict, result.exit_code) == ("block", 1)
    assert result.diagnostics[0]["kind"] == "gate_provider_error"
    expected = (
        "TypeError: gate provider must return a mapping: ethos.test:broken"
        if non_mapping
        else "RuntimeError: boom"
    )
    assert result.diagnostics[0]["error"] == expected


@pytest.mark.parametrize("selection", ["absolute", "relative", "path", "dot-relative"])
def test_runner_preserves_python_virtual_environment_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    selection: str,
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
