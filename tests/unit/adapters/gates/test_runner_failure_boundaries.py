"""Gate failure, declaration and dependency execution boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.configuration as configuration_gate
import ethos.adapters.gates.formatting as formatting_gate
import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.gates.tool as gate_tool
import ethos.adapters.gates.verification as gate_verification
import ethos.adapters.mutation.proof_artifacts as proof_artifacts
import ethos.adapters.repo.git as git_adapter
from ethos.adapters.gates.verification import classify_action_result
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.surface.cli.proof.report import summarize_checks
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("boundary", ["invalid-repository", "missing-executable"])
@pytest.mark.parametrize(
    ("provider", "gate_id"),
    [
        ("markdown_lint_report", "markdown-lint"),
        ("markdown_links_report", "markdown-links"),
        ("external_links_report", "external-links"),
        ("prose_report", "prose"),
        ("module_layout_gate_report", "module-layout"),
        ("configuration_report", "config-quality"),
        ("source_format_report", "source-format"),
    ],
)
def test_native_quality_inventory_failure_is_not_empty_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider: str, gate_id: str, boundary: str
) -> None:
    """Unavailable native input retains its actual failure instead of granting a pass."""
    (tmp_path / "source.json").write_text('{\n  "value": 1\n}\n')
    (tmp_path / ".git").write_text("gitdir: missing-repository\n")
    if boundary == "missing-executable":
        monkeypatch.setattr(git_adapter, "git_executable", lambda _: str(tmp_path / "missing-git"))
    try:
        owner = (
            configuration_gate
            if provider == "configuration_report"
            else formatting_gate
            if provider == "source_format_report"
            else gate_tool
        )
        report = (
            configuration_gate.configuration_report(tmp_path, paths=("source.json",))
            if provider == "configuration_report"
            else getattr(owner, provider)(tmp_path)
        )
    except (ValueError, subprocess.CalledProcessError) as error:
        pytest.fail(f"native inventory failure escaped its public result: {error}")
    assert (report["verdict"], report["state"]) == ("unknown", "inventory_unavailable")
    assert report["required_gaps"] == [f"quality_input_inventory_unavailable:{gate_id}"]
    evidence = report["errors"][0]
    assert evidence["cwd"] == str(tmp_path)
    if boundary == "invalid-repository":
        assert evidence["exit_code"] == 128
        assert "gitfile does not point to a valid repository" in evidence["stderr"]
    else:
        assert evidence["code"] == "git_process_spawn_failed"
        assert evidence["command"][0] == str(tmp_path / "missing-git")
    assert (tmp_path / "source.json").read_text() == '{\n  "value": 1\n}\n'


def test_native_markdown_consumes_literal_tracked_and_untracked_authored_inputs(tmp_path: Path):
    """Native selection includes pending Unicode paths but not immutable or ignored bytes."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "README.md").unlink()
    contents = {
        ".gitignore": "build/\n",
        "docs/usage-\u03b1-[literal].md": "# Usage\n\nWords.\n",
        "docs/deleted.md": "# Deleted\n",
        "evidence/retained.md": "[Empty]()\n",
        "openspec/changes/archive/2020-01-01-old/README.md": "[Empty]()\n",
        "build/ignored.md": "[Empty]()\n",
    }
    for relative, content in contents.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    commit_fixture(repo, "record authored Markdown")
    (repo / "docs/deleted.md").unlink()
    pending = "docs/pending-\u03b2-[literal].md"
    (repo / pending).write_text("# Pending\n\n[Empty]()\n")
    report = gate_tool.markdown_lint_report(repo)
    expected = {"AGENTS.md", "docs/usage-\u03b1-[literal].md", pending}
    assert (report["verdict"], report["file_count"]) == ("block", len(expected))
    assert "MD042" in report["native"][1]["stderr"]
    assert set(report["native"][0]["files"]) == expected
    accepted, _ignored = formatting_gate.render_source_content(
        repo, pending, "prettier", b"# Pending\n\nWords.\n"
    )
    (repo / pending).write_bytes(accepted)
    for _ in range(2):
        assert gate_tool.markdown_lint_report(repo)["verdict"] == "pass"
        assert (repo / pending).read_bytes() == accepted
    assert (repo / "evidence/retained.md").read_text() == "[Empty]()\n"
    assert (repo / "build/ignored.md").read_text() == "[Empty]()\n"


def test_native_configuration_consumes_untracked_repository_increment(tmp_path: Path) -> None:
    """A pending stricter policy cannot silently disappear behind the shared floor."""
    repo = init_git_repo(tmp_path / "repo")
    source = repo / "source.json"
    source.write_text('{\n  "value": 1\n}\n')
    relative = ".config/checks/prettier/prettier.toml"
    git(repo, "rm", relative)
    commit_fixture(repo, "record configuration without repository increment")
    increment = repo / relative
    increment.parent.mkdir(parents=True, exist_ok=True)
    policy = "tabWidth = "
    increment.write_text(policy + "4\n")
    refused = configuration_gate.configuration_report(repo, paths=("source.json",))
    assert refused["verdict"] == "block"
    assert "source.json" in str(refused["required_gaps"])
    assert source.read_text() == '{\n  "value": 1\n}\n'
    increment.write_text(policy + "2\n")
    assert (
        configuration_gate.configuration_report(repo, paths=("source.json",))["verdict"] == "pass"
    )


@pytest.mark.parametrize(
    "provider",
    ["markdown_lint_report", "markdown_links_report", "external_links_report", "prose_report"],
)
def test_native_markdown_verified_empty_inventory_still_passes(tmp_path: Path, provider: str):
    """An actual empty Git inventory remains legal without quality-tool execution."""
    repo = init_git_repo(tmp_path / "repo")
    for relative in ("AGENTS.md", "README.md"):
        (repo / relative).unlink()
    commit_fixture(repo, "record empty Markdown inventory")
    report = getattr(gate_tool, provider)(repo)
    assert (report["verdict"], report["file_count"]) == ("pass", 0)
    assert all(item["state"] == "skipped" for item in report.get("native", []))


@pytest.mark.parametrize("exit_code", [0, 7])
def test_quality_tool_complete_streams_survive_native_proof_custody(
    tmp_path: Path, exit_code: int
) -> None:
    """Read-only reports retain native text; existing proof artifacts own persistence."""
    repo = init_git_repo(tmp_path / "repo")
    work = repo / "work"
    work.mkdir()
    stdout, stderr = "stdout \u03b1\n" * 700 + "stdout-end", "stderr \u03b2\n" * 700 + "stderr-end"
    command = [
        sys.executable,
        "-c",
        (
            f"import sys; print({stdout!r}, end=''); "
            f"print({stderr!r}, end='', file=sys.stderr); sys.exit({exit_code})"
        ),
    ]
    report = gate_tool.quality_tool_report(
        root=repo,
        gate_id="quality",
        tool=sys.executable,
        command=command,
        files=["source.py"],
        cwd=work,
    )
    assert (report["stdout"], report["stderr"]) == (stdout, stderr)
    assert (report["verdict"], report["exit_code"]) == (
        "pass" if exit_code == 0 else "block",
        exit_code,
    )
    store = proof_artifacts.proof_artifact_root(repo)
    assert not store.exists()
    check = {
        "action_id": "quality",
        "command": command,
        "verdict": report["verdict"],
        "exit_code": exit_code,
        "stdout": "native provider result",
        "diagnostics": [],
        "evidence_class": "test",
        "trust_bearing": False,
        "verification": {
            "gate": "quality",
            "providers": [
                {"provider": "ethos.adapters.gates.tool:quality_tool_report", "report": report},
            ],
        },
    }
    normalized = proof_artifacts.normalize_checks((check,))
    descriptor = proof_artifacts.write_proof_artifact(store, "a" * 40, normalized)
    stored = json.loads((store / str(descriptor["path"])).read_text())
    assert stored["checks"][0]["verification"] == check["verification"]
    summary = summarize_checks([check])[0]
    assert not {"stdout", "stderr", "verification"}.intersection(summary)


@pytest.mark.parametrize("encoded", [False, True])
def test_quality_tool_timeout_preserves_observed_partial_streams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, encoded: bool
) -> None:
    """A deadline remains unknown while retaining all output observed before it."""
    stdout, stderr = "partial \u03b1\n" * 700, "partial \u03b2\n" * 700

    def expired(_root: Path, command: tuple[str, ...], **_options: object):
        raise subprocess.TimeoutExpired(
            command,
            1,
            output=stdout.encode() if encoded else stdout,
            stderr=stderr.encode() if encoded else stderr,
        )

    monkeypatch.setattr(gate_tool, "run_command", expired)
    report = gate_tool.quality_tool_report(
        root=tmp_path,
        gate_id="quality",
        tool=sys.executable,
        command=[sys.executable, "-c", "pass"],
        files=["source.py"],
    )
    assert (report["verdict"], report["state"]) == ("unknown", "tool_error")
    assert report["required_gaps"] == ["quality_tool_execution_unknown:quality"]
    assert (report["stdout"], report["stderr"]) == (stdout, stderr)
    assert report["exit_code"] is None


@pytest.mark.parametrize("boundary", ["nonzero", "missing", "denied", "identity"])
def test_command_runner_surfaces_missing_command_and_nonzero_exit(
    tmp_path: Path, boundary: str
) -> None:
    marker = tmp_path / "executed"
    native = (
        sys.executable,
        "-c",
        (
            f"from pathlib import Path; Path({str(marker)!r}).touch(); "
            "import sys; print('output'); print('failure',file=sys.stderr); sys.exit(7)"
        ),
    )
    command = {
        "missing": (str(tmp_path / "missing-tool"),),
        "denied": (str(tmp_path),),
    }.get(boundary, native)
    gate = Gate(id="gate", kind="test", command=command)
    identity = (
        ("old-check",) if boundary == "identity" else gate_runner.gate_execution_identity(gate)
    )
    node = PlanNode(id=gate.id, kind="check", command=identity)
    if boundary == "denied":
        with pytest.raises(gate_runner.ProcessExecutionError) as failure:
            gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)
        assert isinstance(failure.value.__cause__, PermissionError)
        return
    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)
    assert (result.verdict, result.exit_code) == (
        "block",
        {"missing": 127, "identity": 1}.get(boundary, 7),
    )
    assert marker.exists() == (boundary == "nonzero")
    if boundary == "identity":
        assert result.diagnostics[0]["required_gaps"] == ["gate_execution_identity_mismatch:gate"]
        return
    if boundary == "missing":
        assert result.diagnostics[0]["required_gaps"] == [f"missing_command:{command[0]}"]
        assert result.diagnostics[0]["cwd"] == str(tmp_path)
    else:
        assert (result.stdout, result.stderr) == ("output\n", "failure\n")


@pytest.mark.parametrize(
    ("exit_code", "stdout", "verdict", "gap"),
    [
        (1, "{}", "block", ""),
        (0, '{"value": 1}', "pass", ""),
        (0, "not-json", "pass", ""),
        (0, '{"command":"status","verdict":"unknown","state":"unknown"}', "unknown", ""),
        (
            0,
            '{"command":"prove","verdict":[]}',
            "unknown",
            "ethos_result_verdict_missing_or_invalid",
        ),
        (
            0,
            '{"command":"prove","state":"done"}',
            "unknown",
            "ethos_result_verdict_missing_or_invalid",
        ),
        (
            0,
            (
                '{"command":"prove","verdict":"pass","state":"done",'
                '"diagnostics":[{"severity":"error","code":"gate_broken"}]}'
            ),
            "block",
            "ethos_result:error:gate_broken",
        ),
        (
            0,
            (
                '{"command":"ethos","verdict":"block","state":"gapped",'
                '"diagnostics":["skip",{"severity":"warning","code":"warn"}]}'
            ),
            "block",
            "ethos_result:warning:warn",
        ),
    ],
)
def test_command_runner_rejects_invalid_or_adverse_ethos_envelopes(
    exit_code: int, stdout: str, verdict: str, gap: str
) -> None:
    observed, diagnostics = classify_action_result(exit_code=exit_code, stdout=stdout)
    assert observed == verdict
    assert not gap or gap in diagnostics[0]["required_gaps"]
    if verdict == "pass" or exit_code:
        assert diagnostics == ()


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("capacity", "proof_node_capacity_invalid"),
        ("missing", "missing_dependency"),
        ("cycle", "cycle_detected"),
        ("duplicate", "duplicate_node_id"),
    ],
)
def test_gate_graph_rejects_invalid_plan_before_execution(tmp_path, case, message):
    gate = Gate(id="gate", kind="test", command=("check",))
    dependencies = ("missing",) if case == "missing" else ("gate",) if case == "cycle" else ()
    node = PlanNode(id="gate", kind="check", command=gate.command, depends_on=dependencies)
    nodes = (node, node) if case == "duplicate" else (node,)

    class Runner(gate_runner.LocalGateRunner):
        def run(self, *_args, **_kwargs):
            pytest.fail("an invalid plan executed a check")

    with pytest.raises(ValueError, match=message):
        gate_runner.run_gate_graph(
            Runner(),
            nodes,
            {"gate": gate},
            root=tmp_path,
            capacity=0 if case == "capacity" else 1,
            parallel=True,
        )


@pytest.mark.parametrize(("capacity", "may_overlap"), [(1, False), (3, False), (4, True)])
def test_gate_cpu_reservations_respect_host_capacity(
    tmp_path: Path, capacity: int, *, may_overlap: bool
) -> None:
    """Two heavy gates serialize on three CPUs but share a four-CPU host."""
    gates = {
        name: Gate(id=name, kind="test", command=(name,), cpu_reservation=2)
        for name in ("unit", "install")
    }
    nodes = tuple(PlanNode(id=name, kind="check", command=gates[name].command) for name in gates)
    events: list[tuple[str, str]] = []

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, _gate, *, root):
            assert root == tmp_path
            return gate_runner.ActionRunResult(node.id, node.command, "pass", 0)

    results = gate_runner.run_gate_graph(
        Runner(),
        nodes,
        gates,
        root=tmp_path,
        capacity=capacity,
        parallel=True,
        on_schedule=lambda name: events.append(("scheduled", name)),
        on_result=lambda result: events.append(("completed", result.action_id)),
    )

    assert all(result.verdict == "pass" for result in results)
    assert (
        events.index(("scheduled", "install")) < events.index(("completed", "unit"))
    ) is may_overlap


@pytest.mark.parametrize(
    ("prerequisite", "exit_code", "expected"),
    [
        ("pass", 0, ("pass", 0)),
        ("block", 1, ("block", None)),
        ("unknown", None, ("block", None)),
        ("pass", None, ("block", None)),
        ("pass", 7, ("block", None)),
        ("planned", None, ("unknown", None)),
    ],
)
def test_failed_dependency_never_executes_delivery(tmp_path, prerequisite, exit_code, expected):
    """Only passed prerequisites admit their dependent effects."""
    nodes = (
        PlanNode(id="coverage", kind="check", command=("coverage",)),
        PlanNode(id="delivery", kind="check", command=("delivery",), depends_on=("coverage",)),
        PlanNode(id="diagnostic", kind="check", command=("diagnostic",)),
    )
    gates = {node.id: Gate(id=node.id, kind="test", command=node.command) for node in nodes}
    executed = []

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, gate, *, root):
            assert root == tmp_path
            assert gate.id == node.id
            executed.append(node.id)
            verdict = prerequisite if node.id == "coverage" else "pass"
            return gate_runner.ActionRunResult(
                node.id, node.command, verdict, exit_code if node.id == "coverage" else 0
            )

    planned = prerequisite == "planned"
    results = gate_runner.run_gate_graph(
        gate_runner.DryRunRunner() if planned else Runner(),
        nodes,
        gates,
        root=tmp_path,
        capacity=2,
        parallel=False,
    )
    assert executed == [
        node.id
        for node in nodes
        if not planned and (node.id != "delivery" or expected == ("pass", 0))
    ]
    assert {result.action_id for result in results} == {node.id for node in nodes}
    blocked = next(result for result in results if result.action_id == "delivery")
    assert (blocked.verdict, blocked.exit_code) == expected
    for result in results:
        if planned or (result.exit_code is None and result.action_id == "delivery"):
            assert result.started_after_seconds is result.duration_seconds is None
        else:
            assert result.started_after_seconds >= 0
            assert result.duration_seconds >= 0
    assert (
        not blocked.diagnostics
        if expected[0] != "block"
        else (blocked.diagnostics[0]["required_gaps"] == ["gate_dependency_not_proven:coverage"])
    )


@pytest.mark.parametrize("local_provider", [False, True])
@pytest.mark.parametrize("transport", ["owner", "cli"])
def test_public_execution_rejects_foreign_provider_before_any_gate(
    tmp_path, local_provider, transport
):
    """A bound candidate provider must not execute an ambient package implementation."""
    repo = init_git_repo(tmp_path / "repo")
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text('profile_id = "provider-fixture"\n[proof]\ngate_registry = "gates.toml"\n')
    marker = repo / "EXECUTED"
    program = f"from pathlib import Path; Path({str(marker)!r}).touch()"
    provider = "ethos.contracts.gates:load_gate_registry_declaration"
    (repo / "gates.toml").write_text(
        'id = "provider-fixture"\n[proof_sets]\n'
        'default = ["external", "provider", "quality-behavior", "quality-static"]\n'
        'full = ["external", "provider", "quality-behavior", "quality-static"]\n'
        '[[gates]]\nid = "external"\nkind = "test"\n'
        f"command = {json.dumps([sys.executable, '-c', program])}\n"
        '[[gates]]\nid = "provider"\nkind = "test"\n'
        f'providers = ["{provider}"]\n'
        '[[gates]]\nid = "quality-behavior"\nkind = "test"\n'
        'profile = "repository"\nexecution_mode = "provider"\ntool_adapter = "ethos"\n'
        'providers = ["ethos.adapters.gates.code_quality:behavior_report"]\n'
        '[[gates]]\nid = "quality-static"\nkind = "lint"\n'
        'profile = "repository"\nexecution_mode = "provider"\ntool_adapter = "ethos"\n'
        'providers = ["ethos.adapters.gates.code_quality:static_report"]\n'
    )
    if local_provider:
        candidate = repo / "src/ethos/contracts/gates.py"
        candidate.parent.mkdir(parents=True)
        candidate.write_text(
            'def load_gate_registry_declaration(root): return {"verdict": "pass"}\n'
        )
    head = commit_fixture(repo, "bind provider")
    if transport == "cli":
        result = run_ethos_raw(
            "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
        )
        payload = json.loads(result.stdout)
        observed = payload["data"] | {
            "verdict": payload["verdict"],
            "required_gaps": payload["required_gaps"],
        }
        assert result.returncode != 0
    else:
        observed = gate_runner.observe_gate_execution(repo, full=True, expect_head=head)
    assert observed["verdict"] == "block"
    expected = (
        f"gate_provider_source_mismatch:provider:{provider}"
        if local_provider
        else "gate_policy_source_missing:provider:src/ethos/contracts/gates.py"
    )
    assert observed["required_gaps"] == [expected], observed
    assert observed["executed"] is False
    assert not marker.exists()


@pytest.mark.parametrize("identity_state", ["exact", "stale", "unavailable"])
def test_packaged_provider_requires_exact_candidate_identity(tmp_path, monkeypatch, identity_state):
    """Installed matching builds remain usable; missing or stale identity grants nothing."""
    repo = init_git_repo(tmp_path / "repo")
    source = repo / "src/ethos/contracts/verdict.py"
    source.parent.mkdir(parents=True)
    source.write_text("def report_verdict(root): return 'pass'\n")
    head = commit_fixture(repo, "candidate provider")
    tree = gate_runner.current_tree(repo, head)

    def build():
        if identity_state == "unavailable":
            message = "identity unavailable"
            raise ValueError(message)
        return SimpleNamespace(
            source_commit=head, source_tree=tree if identity_state == "exact" else ""
        )

    monkeypatch.setattr(gate_verification, "invoking_build_identity", build)
    gate = Gate(id="check", kind="test", providers=("ethos.contracts.verdict:report_verdict",))
    if identity_state == "exact":
        gate_verification.assert_provider_execution_source(repo, (gate,))
    else:
        with pytest.raises(ValueError, match="gate_provider_source_mismatch:check:"):
            gate_verification.assert_provider_execution_source(repo, (gate,))
    # Packaged-only adopter checks have no falsely claimed repository source.
    source.unlink()
    gate_verification.assert_provider_execution_source(repo, (gate,))
