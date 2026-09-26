"""Native gate execution preserves declared identity and provider verdicts."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.gates.tool as gate_tool
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_policy_fields
from ethos.repository.policy.gates import quality_obligation_gaps
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

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


def test_native_gate_qualifies_same_run_junit_and_v8_in_spaced_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One command execution supplies test and source evidence without a rerun."""
    root = init_git_repo(tmp_path / "repo with spaces")
    (root / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
    (root / "app.mjs").write_text("export function answer() { return 42; }\n", encoding="utf-8")
    (root / "app.test.mjs").write_text(
        'import test from "node:test";\n'
        'import assert from "node:assert/strict";\n'
        'import { appendFileSync } from "node:fs";\n'
        'import { answer } from "./app.mjs";\n'
        'appendFileSync(process.env.ETHOS_TEST_EXECUTIONS_FILE, "x");\n'
        'test("answer", () => assert.equal(answer(), 42));\n',
        encoding="utf-8",
    )
    commit_fixture(root, "declare native test")
    marker = tmp_path / "executions"
    monkeypatch.setenv("ETHOS_TEST_EXECUTIONS_FILE", str(marker))
    monkeypatch.setenv("NODE_OPTIONS", "--test-reporter=spec")
    gate = Gate(
        id="behavior",
        kind="test",
        command=("node", "--test", "app.test.mjs"),
        evidence_adapters=("ethos.adapters.gates.native_evidence:javascript_behavior",),
        execution_mode="subprocess",
        tool_adapter="repository-native",
    )

    result = gate_runner.LocalGateRunner().run(_node(gate), gate, root=root)

    assert result.verdict == "pass"
    assert marker.read_text(encoding="utf-8") == "x"
    assert len(result.evidence) == 1
    report = result.evidence[0]["report"]
    assert report["verdict"] == "pass"
    assert report["native"]["tests_passed"] == 1
    assert report["quality_evidence"]["selected_paths"] == ["app.mjs"]
    policy = {
        "owner": {
            "quality_floor_version": 2,
            "code_correctness_map": {"behavior": "behavior"},
            "quality_subjects": {"behavior": ["app.mjs"]},
        },
        "gates": [gate_policy_fields(gate)],
    }
    assert (
        quality_obligation_gaps(
            policy, (asdict(result),), source_tree=report["quality_evidence"]["source_tree"]
        )
        == ()
    )


def test_native_evidence_adapter_does_not_qualify_self_reported_json(tmp_path: Path) -> None:
    """A successful command cannot substitute its stdout for native test material."""
    gate = Gate(
        id="behavior",
        kind="test",
        command=(sys.executable, "-c", 'print("{\\"providers\\": []}")'),
        evidence_adapters=("ethos.adapters.gates.native_evidence:javascript_behavior",),
    )

    result = gate_runner.LocalGateRunner().run(_node(gate), gate, root=tmp_path)

    assert result.verdict == "block"
    assert result.exit_code == 0
    assert result.evidence[0]["report"]["verdict"] == "block"


@pytest.mark.parametrize(
    ("second_paths", "second_tree", "second_adapter", "expected_gaps"),
    [
        (["src/other.js"], "a" * 40, "ethos.test:second", ()),
        ([], "a" * 40, "ethos.test:second", ("quality_obligation_unproven:behavior",)),
        (
            ["src/other.js"],
            "b" * 40,
            "ethos.test:second",
            ("quality_obligation_unproven:behavior",),
        ),
        (
            ["src/other.js"],
            "a" * 40,
            "ethos.test:unselected",
            ("quality_obligation_unproven:behavior",),
        ),
        (
            ["src/other.js", "src/extra.js"],
            "a" * 40,
            "ethos.test:second",
            ("quality_obligation_unproven:behavior",),
        ),
    ],
)
def test_native_evidence_requires_exact_union_of_selected_subjects(
    second_paths: list[str],
    second_tree: str,
    second_adapter: str,
    expected_gaps: tuple[str, ...],
) -> None:
    """Several interpreters may jointly prove a scope, never omit or enlarge it."""
    source_tree = "a" * 40
    adapters = ("ethos.test:first", "ethos.test:second")
    command = ("node", "check")
    check = {
        "action_id": "behavior",
        "command": command,
        "evidence": [
            {
                "adapter": adapter,
                "report": {
                    "verdict": "pass",
                    "quality_evidence": {
                        "axis": "behavior",
                        "source_tree": tree,
                        "selected_paths": paths,
                    },
                },
            }
            for adapter, tree, paths in (
                (adapters[0], source_tree, ["src/app.js"]),
                (second_adapter, second_tree, second_paths),
            )
        ],
    }
    policy = {
        "owner": {
            "quality_floor_version": 2,
            "code_correctness_map": {"behavior": "behavior"},
            "quality_subjects": {"behavior": ["src/app.js", "src/other.js"]},
        },
        "gates": [
            {
                "id": "behavior",
                "execution_identity": command,
                "execution_mode": "subprocess",
                "tool_adapter": "repository-native",
                "evidence_adapters": adapters,
            }
        ],
    }

    gaps = quality_obligation_gaps(policy, (check,), source_tree=source_tree)

    assert gaps == expected_gaps


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
