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
import ethos.adapters.gates.native.inputs as native_inputs
import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.gates.tool as gate_tool
import ethos.adapters.gates.verification as gate_verification
from ethos.contracts.gates import Gate
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_policy_fields
from ethos.repository.policy.quality.obligations import quality_obligation_gaps
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import git


def _quality_files(monkeypatch: pytest.MonkeyPatch, *files: str) -> None:
    monkeypatch.setattr(native_inputs, "quality_source_files", lambda *_args: list(files))


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

    def command(
        _root: Path,
        argv: tuple[str, ...],
        *,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
        remove_env: tuple[str, ...] = (),
    ):
        assert env is None
        assert remove_env == ()
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
        assert (report["stdout"], report["stderr"]) == ("x" * 5000, "failed")


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


def test_packaged_markdown_gate_uses_shipped_node_tools_and_selected_native_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Markdown proof needs no adopter Python recipe or dependency installation."""
    config = tmp_path / ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("noInlineConfig: true\nconfig:\n  default: false\n")
    (tmp_path / "README.md").write_text("# Current\n\n[Empty link]()\n")
    _quality_files(monkeypatch, "README.md", str(config.relative_to(tmp_path)))
    selected = load_gate_registry_declaration().registry()["markdown-lint"]
    assert selected.command == ()
    assert selected.providers == ("ethos.adapters.gates.tool:markdown_lint_report",)
    report = gate_tool.markdown_lint_report(tmp_path)
    assert report["verdict"] == "block"
    native = report["native"]
    assert len(native) == 3
    assert native[2]["command"][3] == str(config)
    assert all(item["file_count"] == 1 for item in native)
    assert "MD042" in native[1]["stderr"]
    assert native[2]["verdict"] == "pass"


def test_native_markdown_configuration_preserves_nested_rule_parameters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The official CLI consumes nested native parameters, not just Boolean rules."""
    config = tmp_path / ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "config:\n  default: false\n  MD024: {siblings_only: true}\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(
        "# Native\n\n## One\n\n### Fixed\n\nWords.\n\n## Two\n\n### Fixed\n\nMore words.\n",
        encoding="utf-8",
    )
    _quality_files(monkeypatch, "README.md", str(config.relative_to(tmp_path)))
    report = gate_tool.markdown_lint_report(tmp_path)
    assert report["verdict"] == "pass", report


def test_common_markdown_policy_accepts_native_formatter_container_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The native fix/check journey has one spacing owner and preserves semantic lint."""
    document = tmp_path / "README.md"
    accepted = b"# Spacing\n\n- First.\n  ```text\n  example\n  ```\n- Second.\n"
    document.write_bytes(accepted)
    _quality_files(monkeypatch, "README.md")

    report = gate_tool.markdown_lint_report(tmp_path)

    assert report["verdict"] == "pass", report
    assert document.read_bytes() == accepted
    native = report["native"]
    assert native[0]["files"] == ["README.md"]
    assert native[0]["required_gaps"] == []
    document.write_bytes(accepted.rstrip(b"\n"))
    refused = gate_tool.markdown_lint_report(tmp_path)
    assert refused["verdict"] == "block"
    assert document.read_bytes() == accepted.rstrip(b"\n")
    fixed, _ignored = gate_tool.render_source_content(
        tmp_path, "README.md", "prettier", document.read_bytes()
    )
    document.write_bytes(fixed)
    assert document.read_bytes() == accepted
    assert gate_tool.markdown_lint_report(tmp_path)["verdict"] == "pass"
    repeated, _ignored = gate_tool.render_source_content(
        tmp_path, "README.md", "prettier", document.read_bytes()
    )
    document.write_bytes(repeated)
    assert document.read_bytes() == accepted
    document.write_text("# Semantic lint\n\n[Empty link]()\n", encoding="utf-8")
    semantic = gate_tool.markdown_lint_report(tmp_path)
    assert semantic["verdict"] == "block"
    assert "MD042" in semantic["native"][1]["stderr"]


def test_markdown_links_use_declared_installed_supply_without_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The installed native link checker is independent of adopter and ambient tools."""
    repo = committed_source_repo(
        tmp_path,
        {
            "README.md": "# Links\n\n[Current](README.md)\n",
            ".config/checks/lychee/lychee.toml": "offline = true\n",
        },
    )
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    monkeypatch.setenv("PATH", "")

    report = gate_tool.markdown_links_report(repo)

    assert report["verdict"] == "pass", report
    assert report["file_count"] == 2
    assert report["source_tree"] == tree
    assert Path(report["native"][0]["command"][0]).is_absolute()


def test_prose_gate_keeps_native_spelling_without_adopter_toolchain(tmp_path, monkeypatch):
    """The installed owner ignores ambient policy and preserves exact authored bytes."""
    gate = load_gate_registry_declaration().registry()["prose"]
    assert gate.providers == ("ethos.adapters.gates.tool:prose_report",)
    assert not gate.command
    document = tmp_path / "README.md"
    local = tmp_path / ".config/checks/codespell/codespell.toml"
    local.parent.mkdir(parents=True)
    local.write_text('[tool.codespell]\nignore-words-list = "teh"\n')
    (tmp_path / "pyproject.toml").write_text('[tool.codespell]\nskip = "*"\n')
    _quality_files(monkeypatch, "README.md", local.relative_to(tmp_path).as_posix())
    monkeypatch.setenv("PATH", "")
    for source, verdict in (
        ("The result is verified.\n", "pass"),
        ("The result is teh result.\n", "block"),
    ):
        document.write_text(source)
        report = gate_tool.prose_report(tmp_path)
        assert (report["verdict"], document.read_text()) == (verdict, source), report
        assert len(report["native"]) == 2
        commands = [result["command"][:4] for result in report["native"]]
        assert commands == [[sys.executable, "-B", "-I", "-m"]] * 2
    assert report["native"][0]["exit_code"] != 0
    assert report["native"][1]["exit_code"] == 0
    local.write_text("[tool.codespell]\nwrite-changes = true\n")
    report = gate_tool.prose_report(tmp_path)
    assert (report["verdict"], document.read_text()) == ("block", source)
    _quality_files(monkeypatch)
    report = gate_tool.prose_report(tmp_path)
    assert (report["verdict"], report["file_count"]) == ("pass", 0)


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
