"""Release and quality execution preserve declared inputs and proof boundaries."""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast
from unittest.mock import Mock

import pytest

import ethos.adapters.gates.runner as gate_execution
import ethos.repository.policy.gates as gate_policy
import tools.ci.local_ci as local_ci
import tools.ci.python_test_gate as python_test_gate
import tools.ci.sessions as ci_sessions
from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node.supply import NodeSupply
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos.contracts.artifacts.topology import path_policy_from_declaration
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files
from tests.support.architecture import isolated_path
from tests.support.runtime_scenarios import empty_node_package_supply
from tools.ci.delivery.pipeline import DeliveryPipeline
from tools.ci.dependency_hygiene import declaration_gaps
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]


def test_native_node_identity_uses_the_mise_declaration_and_lock() -> None:
    """CI and source builds select one platform archive, not an ambient Node."""
    declaration = tomllib.loads((ROOT / ".config/mise/config.toml").read_text())
    locked = tomllib.loads((ROOT / ".config/mise/mise.lock").read_text())
    supply = NodeSupply.read(ROOT)
    (record,) = [row for row in locked["tools"]["node"] if row["version"] == supply.version]
    material = record[f"platforms.{supply.target}"]

    assert supply.version == declaration["tools"]["node"]
    assert material["url"] == supply.url
    assert material["checksum"] == f"sha256:{supply.sha256}"
    assert supply.installed_root(ROOT) == supply.cache(ROOT) / "runtime"


def test_bootstrap_builds_the_environment_on_the_locked_python() -> None:
    """A host interpreter upgrade cannot change the Python that bootstrap builds on."""
    mise = tomllib.loads((ROOT / ".config/mise/config.toml").read_text())
    assert re.fullmatch(r"3\.\d+\.\d+", mise["tools"]["python"])
    syncs = [step for step in mise["tasks"]["bootstrap"]["run"] if step.startswith("uv sync")]
    assert syncs
    assert all(step.endswith(' --python "{{tools.python.path}}"') for step in syncs)


def test_native_tool_declarations_have_one_locked_supply_identity() -> None:
    """Native tool identities and archive digests share the Mise lock owner."""
    mise = tomllib.loads((ROOT / ".config/mise/config.toml").read_text())
    locked = tomllib.loads((ROOT / ".config/mise/mise.lock").read_text())
    assert locked["lockfile_version"] == 3
    for name, version in mise["tools"].items():
        (record,) = [row for row in locked["tools"][name] if row["version"] == version]
        materials = [value for key, value in record.items() if key.startswith("platforms.")]
        assert materials
        assert all(re.fullmatch(r"sha256:[a-f0-9]{64}", value["checksum"]) for value in materials)

    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert any(item.startswith("lychee-bin>=") for item in project["project"]["dependencies"])
    assert not any(item.startswith("lychee-bin>=") for item in project["dependency-groups"]["dev"])


def test_ci_supply_provides_the_declared_linux_signing_tool() -> None:
    dockerfile = (ROOT / ".config/ci/supply/Dockerfile").read_text(encoding="utf-8")
    assert "openssh-client=" in dockerfile


def test_direct_python_bounds_equal_the_locked_resolution() -> None:
    assert declaration_gaps() == []


def test_local_ci_logs_use_declared_disposable_runtime_home() -> None:
    declaration = load_generated_artifact_topology_declaration()
    relative = local_ci.LOG_ROOT.relative_to(ROOT).as_posix()

    assert relative == "build/runtime/work/local-ci/logs"
    assert path_policy_from_declaration(relative, declaration)["decision"] == "allow"


def test_direct_node_declarations_equal_the_lock_root() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    locked = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))["packages"][""]
    for group in ("dependencies", "devDependencies"):
        assert package.get(group, {}) == locked.get(group, {})


def test_current_node_package_supply_read_has_one_observed_owner() -> None:
    files = {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for parent in (ROOT / "src", ROOT / "tools", ROOT / "tests")
        for path in parent.rglob("*.py")
    }
    observed = reference_consumer_sources_from_files(files)

    assert observed.unknown_paths == ()
    assert observed.sources["value"].get("ETHOS_NODE_PACKAGE_SUPPLY") == frozenset(
        {"src/ethos/adapters/repo/runtime/materialization/node_package_supply.py"}
    )


def test_python_test_sessions_receive_the_frozen_node_package_supply(tmp_path, monkeypatch) -> None:
    supply, session = tmp_path / "node_modules", SimpleNamespace(posargs=())
    factory = Mock()
    monkeypatch.setattr(ProjectRuntime, "node_package_supply", lambda _self: supply)
    monkeypatch.setattr(python_test_gate.PythonTestGate, "from_environment", factory)

    ci_sessions.tests(session)
    ci_sessions.coverage_floor(session)

    assert factory.call_count == 2
    assert all(call.kwargs == {"node_package_supply": supply} for call in factory.call_args_list)
    factory.return_value.run_tests.assert_called_once_with(session)
    factory.return_value.enforce_floor.assert_called_once_with(session)


@pytest.mark.parametrize(
    "case",
    [
        "pass",
        "coverage",
        "dirty",
        "head-missing",
        "policy",
        "empty",
        "missing",
        "duplicate",
        "command",
        "no-exit",
        "bad-exit",
        "overlay",
        "head",
        "policy-drift",
        "crash",
    ],
)
def test_local_ci_requires_complete_exact_source_evidence(tmp_path, monkeypatch, case):
    """A transport cannot mint HEAD success from an overlay or incomplete execution."""
    monkeypatch.setattr(local_ci, "EVIDENCE", tmp_path / "result.json")
    monkeypatch.setattr(local_ci, "LOG_ROOT", tmp_path / "logs")
    monkeypatch.setattr(
        gate_execution,
        "current_tracked_head",
        lambda _root: "" if case == "head-missing" else "a" * 40,
    )
    monkeypatch.setattr(local_ci, "current_tracked_head", gate_execution.current_tracked_head)
    monkeypatch.setattr(gate_execution, "current_tree", lambda *_a: "b" * 40)
    monkeypatch.setattr(
        gate_execution,
        "observe_execution_source",
        lambda *_a: {"index": "b" * 40, "worktree": "dirty" if case == "dirty" else "b" * 40},
    )
    policy = local_ci.resolve_gate_policy(ROOT, full=True)
    if case == "policy":
        policy = replace(policy, gaps=("invalid_policy",))
    monkeypatch.setattr(gate_execution, "resolve_gate_policy", lambda *_a, **_k: policy)
    observed = []
    base_run = gate_execution.run_gate_graph

    class Runner:
        def __init__(self, *, candidate: bool = False):
            assert candidate is False

        def run(self, node, _gate, **_context):
            observed.append(node.id)
            verdict = "block" if case == "coverage" and node.id == "coverage-floor" else "pass"
            return ActionRunResult(node.id, node.command, verdict, int(verdict != "pass"))

    def execute(*args, **kwargs):
        if case == "crash":
            message = "interrupted runner"
            raise RuntimeError(message)
        result = base_run(*args, **kwargs)
        if case in {"overlay", "head", "policy-drift"}:
            name, value = {
                "overlay": ("observe_execution_source", {"index": "b" * 40, "worktree": "changed"}),
                "head": ("current_tracked_head", "b" * 40),
                "policy-drift": (
                    "resolve_gate_policy",
                    replace(
                        policy, sources=(("ruff", ((".config/checks/ruff/ruff.toml", "changed"),)),)
                    ),
                ),
            }[case]
            monkeypatch.setattr(gate_execution, name, lambda *_a, **_k: value)
        return (
            ()
            if case == "empty"
            else result[:-1]
            if case == "missing"
            else (
                (*result, result[0])
                if case == "duplicate"
                else (replace(result[0], command=("wrong",)), *result[1:])
                if case == "command"
                else (replace(result[0], exit_code=None if case == "no-exit" else 7), *result[1:])
                if case in {"no-exit", "bad-exit"}
                else result
            )
        )

    monkeypatch.setattr(gate_execution, "LocalGateRunner", Runner)
    monkeypatch.setattr(gate_execution, "run_gate_graph", execute)
    # The verifier payloads have their own regressions; this transport keeps only its own claim.
    monkeypatch.setattr(gate_policy, "quality_obligation_gaps", lambda *_a, **_k: ())
    session = SimpleNamespace(error=pytest.fail, log=lambda _message: None)
    if case == "pass":
        local_ci.run(cast("nox.Session", session))
        assert observed.index("build") < observed.index("local-install-smoke")
    else:
        with pytest.raises((pytest.fail.Exception, RuntimeError)):
            local_ci.run(cast("nox.Session", session))
    payload = json.loads(local_ci.EVIDENCE.read_text())
    assert payload["verdict"] == ("pass" if case == "pass" else "block")
    if case in {"dirty", "head-missing", "policy", "crash"}:
        assert not observed
    else:
        assert observed.count("unit-architecture") == observed.count("coverage-floor") == 1
    assert len(observed) == len(set(observed))


@pytest.mark.parametrize("workers", [None, 1, 8])
@pytest.mark.parametrize(("cores", "expected_default"), [(3, 3), (18, 12)])
def test_test_environment_freezes_locked_supply_as_absolute_paths(
    tmp_path, monkeypatch, workers, cores, expected_default
) -> None:
    root = tmp_path / "repo"
    supply = empty_node_package_supply(root)
    monkeypatch.setattr(python_test_gate, "ROOT", root)
    monkeypatch.setattr(python_test_gate, "_head", lambda: "a" * 40)
    monkeypatch.setenv("UV_CACHE_DIR", "build/runtime/tool-cache/uv")
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    monkeypatch.delenv("ETHOS_TEST_WORKERS", raising=False)
    monkeypatch.delenv("ETHOS_TEST_EVIDENCE_DIR", raising=False)
    monkeypatch.setattr(python_test_gate.os, "cpu_count", lambda: cores)
    assert python_test_gate.Settings.load(node_package_supply=supply).workers == expected_default

    gate = python_test_gate.PythonTestGate.from_environment(node_package_supply=supply)
    gate = python_test_gate.PythonTestGate(replace(gate.s, workers=workers))
    monkeypatch.setenv("UV_CACHE_DIR", "another-cache")
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", str(tmp_path / "other-supply"))
    for method in ("_prepare", "_cleanup", "_stable_head"):
        monkeypatch.setattr(gate, method, lambda: None)
    session = Mock()
    gate.run_tests(session)
    command, options = session.run.call_args
    observed = options["env"]

    assert observed["UV_CACHE_DIR"] == str(root / "build/runtime/tool-cache/uv")
    assert observed["ETHOS_NODE_PACKAGE_SUPPLY"] == str(supply)

    assert {"--dist=load", "--maxschedchunk=1"} <= set(command)
    assert command[command.index("-p") + 1] == "tools.ci.python_test_order"
    assert ("-n" in command) is (workers == 8)
    assert set(python_test_gate.TARGETS) <= set(command)


def test_project_capability_supply_revalidates_each_operation(tmp_path, monkeypatch) -> None:
    """A selected delivery freezes supply, while the next selection rereads it."""
    supply = empty_node_package_supply(tmp_path)
    runtime = ProjectRuntime.discover(tmp_path)
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    pipeline = DeliveryPipeline.from_runtime(runtime)
    assert pipeline.runtime is runtime
    assert pipeline.node_package_supply == supply
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="node_package_supply_unavailable"):
        runtime.node_package_supply()
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", str(supply))
    (supply / ".package-lock.json").write_text(
        '{"lockfileVersion":3,"packages":{"node_modules/x":{}}}'
    )
    with pytest.raises(ValueError, match="node_package_supply_lock_mismatch"):
        DeliveryPipeline.from_runtime(runtime)
    assert pipeline.node_package_supply == supply


def test_config_quality_projects_the_installed_owner(monkeypatch) -> None:
    """Nox owns transport and source hook validation, not generic configuration rules."""
    check = Mock(return_value={"verdict": "pass"})
    monkeypatch.setattr(
        ci_sessions, "import_module", lambda _name: SimpleNamespace(configuration_report=check)
    )
    session = SimpleNamespace(posargs=(), run=Mock(), log=Mock(), error=pytest.fail)

    ci_sessions.config_quality(cast("nox.Session", session))

    check.assert_called_once_with(ci_sessions.ROOT, paths=())
    session.log.assert_called_once()
    session.run.assert_called_once_with(
        ci_sessions.RUNTIME.script("pre-commit"), "validate-config", ci_sessions.PRE_COMMIT_CONFIG
    )


def test_javascript_tests_execute_supplied_node_and_npm_with_shadowed_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real package tests run under c8 on the supplied Node and remove their owned npm cache."""
    shadow = isolated_path(
        tmp_path,
        {"node": "#!/bin/sh\nexit 83\n", "npm": "#!/bin/sh\nexit 84\n"},
    )
    monkeypatch.setenv("PATH", shadow["PATH"] + os.pathsep + os.environ["PATH"])
    runtime = resolve_node_runtime()
    observations = []

    def execute(*command, env):
        result = run_command(ROOT, tuple(command), env=env, timeout=60)
        observations.append((command, env, result))
        assert result.returncode == 0, result.stdout + result.stderr

    ci_sessions.javascript_tests(SimpleNamespace(run=execute))

    ((command, environment, result),) = observations
    supply = ci_sessions.RUNTIME.node_package_supply()
    assert command[:2] == (str(runtime.executable), str(supply / "c8/bin/c8.js"))
    assert command.count(str(runtime.executable)) == 2
    assert environment["PATH"].split(os.pathsep)[0] == str(runtime.executable.parent)
    assert environment["npm_config_offline"] == "true"
    assert not Path(environment["npm_config_cache"]).exists()
    assert "the launcher package exposes only its declared transport" in result.stdout
