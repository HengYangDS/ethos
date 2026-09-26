"""Native gate execution preserves declared identity and provider verdicts."""

from __future__ import annotations

import json
import subprocess
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.gates.tool as gate_tool
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_policy_fields
from ethos.repository.policy.gates import quality_obligation_gaps

if TYPE_CHECKING:
    from pathlib import Path


def _gate(*providers: str) -> Gate:
    return Gate(id="gate", kind="test", providers=providers)


def _node(gate: Gate) -> PlanNode:
    return PlanNode(id=gate.id, kind="check", command=gate_runner.gate_execution_identity(gate))


def _runner(monkeypatch, **providers: object) -> gate_runner.LocalGateRunner:
    monkeypatch.setattr(
        gate_runner.importlib, "import_module", lambda _: SimpleNamespace(**providers)
    )
    return gate_runner.LocalGateRunner()


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
    monkeypatch.setattr(gate_runner.importlib, "import_module", lambda _name: SimpleNamespace())

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

    monkeypatch.setattr(gate_tool.subprocess, "run", run)
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
        assert str(report["stdout"]).endswith("[trimmed 1000 bytes]")


def test_markdown_link_gate_excludes_deleted_tracked_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A staged or unstaged deletion is not an input to the link checker."""
    (tmp_path / "README.md").write_text("# Current\n", encoding="utf-8")
    monkeypatch.setattr(
        gate_tool,
        "git_files",
        lambda *_args: ["README.md", "docs/deleted.md"],
    )
    monkeypatch.setattr(gate_tool.shutil, "which", lambda _tool: "/bin/lychee")
    observed: list[list[str]] = []

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(gate_tool.subprocess, "run", run)

    report = gate_tool.markdown_links_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["file_count"] == 1
    assert observed[0][-1] == "README.md"
    assert "docs/deleted.md" not in observed[0]


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
