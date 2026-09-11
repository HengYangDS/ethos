from __future__ import annotations

import importlib
import json
import shlex
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest

import tools.ci.local_ci as local_ci
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.release.identity import BuildIdentity
from tools.ci.delivery import pipeline
from tools.ci.delivery.acceptance import adopter as fixture
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import invocation
from tools.ci.delivery.acceptance import lane
from tools.ci.delivery.acceptance import receipt
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[3]
_LIFECYCLE_STAGES = {
    "development_dependencies",
    "hook_activation",
    "immutable_identity",
    "lane_bootstrap",
    "relocation_repair",
    "retirement_recovery",
    "successor_activation",
    "signature_repair",
}


def test_package_lifecycle_has_one_execution_owner() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["full"]
    gates = {item["id"]: item for item in declaration["gates"]}
    lifecycle_gates = {
        gate["id"]
        for gate in declaration["gates"]
        if "installability" in gate.get("dimensions", [])
    }

    assert lifecycle_gates == {"local-install-smoke"}
    assert full.count("local-install-smoke") == 1
    assert full.index("build") < full.index("local-install-smoke")
    assert gates["local-install-smoke"]["depends_on"] == ["build"]
    assert gates["local-install-smoke"]["network_policy"] == "offline"
    assert gates["local-install-smoke"]["writes_files"] is True
    assert "installability" not in gates["unit-architecture"]["dimensions"]


def test_package_acceptance_evidence_requires_every_runtime_lifecycle_stage(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "ethos.whl"
    wheel.write_bytes(b"wheel")
    lifecycle = {stage: {"state": "passed"} for stage in _LIFECYCLE_STAGES}
    generated_at = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)

    compile_receipt = partial(
        receipt.package_acceptance_evidence,
        root=tmp_path,
        head="a" * 40,
        wheel=wheel,
        origin="/runtime/site-packages/ethos/__init__.py",
        version="ethos 0.2.0-alpha.3",
        line_endings=["lf", "crlf"],
        independent_host={"external_governance_available": False},
        resources=["ethos/data/gates.toml"],
        runtime_lifecycle=lifecycle,
        generated_at=generated_at,
    )
    payload = compile_receipt()

    assert payload["head"] == "a" * 40
    assert payload["runtime_lifecycle"] == lifecycle
    assert payload["generated_at"] == "2026-09-03T12:00:00+00:00"
    assert payload["hosted_ci_status_claimed"] is False
    assert payload["remote_publication_claimed"] is False
    assert payload["registry_publication_claimed"] is False
    assert isinstance(payload["conformance"], dict)
    assert "sdk_commitment_digest" not in payload["conformance"]
    assert payload["wheels"] == [
        {
            "path": "ethos.whl",
            "sha256": "ba59926159d2aa256eb8739b8da7e2b574b960e1202c6d624cbe981cef996c91",
        }
    ]

    incomplete = dict(lifecycle)
    incomplete.pop("retirement_recovery")
    with pytest.raises(ValueError, match="package_runtime_lifecycle_incomplete"):
        compile_receipt(resources=[], runtime_lifecycle=incomplete)


def test_install_smoke_invokes_one_acceptance_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []
    session = cast("nox.Session", object())
    monkeypatch.setattr(
        pipeline.acceptance_effect,
        "run",
        lambda observed: events.append(("accept", observed)),
    )

    pipeline.DeliveryPipeline(
        runtime=ProjectRuntime.discover(ROOT),
        node_package_supply=ROOT / "node_modules",
    ).prove_install(session)

    assert events == [("accept", session)]


def test_local_ci_uses_the_declared_full_quality_closure() -> None:
    """Local verification cannot silently omit declared full-proof obligations."""

    expected = resolve_gate_policy(ROOT, full=True)
    assert local_ci.owner_commands() == [
        shlex.join(gate_execution_identity(expected.registry[node.id])) for node in expected.nodes
    ]
    assert expected.gate_ids.count("local-install-smoke") == 1


def test_runtime_supply_projects_the_lock_current_environment_without_cache_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    supply = importlib.import_module(
        "ethos.adapters.repo.runtime.materialization.dependency_supply"
    )
    requirements = tmp_path / "acceptance/locked-requirements.txt"
    source_python = tmp_path / "project/.venv/bin/python"
    environment_python = tmp_path / "acceptance/venv/bin/python"
    commands: list[tuple[str, ...]] = []
    projections: list[tuple[Path, Path]] = []

    def run(_root: Path, *command: str, python: Path) -> None:
        del python
        commands.append(command)
        if "--output-file" in command:
            output = Path(command[command.index("--output-file") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("package==1 --hash=sha256:abc\n", encoding="utf-8")

    monkeypatch.setattr(supply, "run_runtime_tool", run)
    monkeypatch.setattr(
        supply,
        "project_dependency_supply",
        lambda source, target: projections.append((source, target)),
        raising=False,
    )

    observed_requirements = supply.prepare_locked_requirements(
        tmp_path,
        requirements.parent,
        source_python,
    )
    supply.install_locked_runtime(
        tmp_path,
        source_python,
        environment_python,
        tmp_path / "ethos.whl",
        observed_requirements,
    )

    assert projections == [(source_python, environment_python)]
    assert len(commands) == 4
    assert all("--offline" in command for command in commands)
    assert not any("venv" in command for command in commands)
    assert not any("--cache-dir" in command for command in commands)
    assert commands[1][-2:] == ("--output-file", str(requirements))
    assert commands[2][:2] == ("pip", "sync")
    assert "--require-hashes" in commands[2]
    assert commands[2][commands[2].index("--python") + 1] == str(environment_python)
    assert commands[2][-1] == str(requirements)


def test_acceptance_failure_cleans_its_transaction_root_without_a_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    work = tmp_path / "work"
    evidence = tmp_path / "evidence/smoke.json"
    artifacts.mkdir()
    (artifacts / "ethos-0.2.0a3-py3-none-any.whl").write_bytes(b"wheel")

    monkeypatch.setattr(effect, "ROOT", tmp_path)
    monkeypatch.setattr(effect, "ARTIFACTS", artifacts)
    monkeypatch.setattr(effect, "WORK", work)
    monkeypatch.setattr(effect, "EVIDENCE", evidence)
    monkeypatch.setattr(
        effect,
        "RUNTIME",
        SimpleNamespace(python=tmp_path / "project-python", script=lambda _name: "/locked/uv"),
    )
    monkeypatch.setattr(effect, "current_tracked_head", lambda _root: "a" * 40)

    def fail_supply(*_args: object, **_kwargs: object) -> None:
        (work / "partial-supply").mkdir(parents=True)
        message = "expected supply failure"
        raise RuntimeError(message)

    monkeypatch.setattr(
        effect,
        "prepare_locked_requirements",
        lambda *_args: work / "locked-requirements.txt",
    )
    monkeypatch.setattr(effect, "install_locked_runtime", fail_supply)
    monkeypatch.setattr(effect, "_run", lambda *_args, **_kwargs: "")
    session = SimpleNamespace(error=pytest.fail, log=pytest.fail)

    with pytest.raises(RuntimeError, match="expected supply failure"):
        effect.run(cast("nox.Session", session))

    assert not work.exists()
    assert not evidence.exists()


def test_wheel_build_reuses_the_locked_project_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[tuple[str, ...]] = []

    class Session:
        @staticmethod
        def run(*command: str, **_kwargs: object) -> None:
            commands.append(command)

    monkeypatch.setattr(pipeline, "publish_built_wheel", lambda *_args: tmp_path / "ethos.whl")
    monkeypatch.chdir(tmp_path)
    runtime = ProjectRuntime(tmp_path, Path("/locked/bin/python"), Path("/locked/bin"))
    monkeypatch.setattr(ProjectRuntime, "script", lambda _self, name: f"/locked/bin/{name}")

    pipeline.DeliveryPipeline(
        runtime=runtime,
        node_package_supply=tmp_path / "node_modules",
    ).build(cast("nox.Session", Session()))

    assert len(commands) == 1
    command = commands[0]
    assert command[:8] == (
        "/locked/bin/uv",
        "build",
        "--offline",
        "--no-build-isolation",
        "--python",
        "/locked/bin/python",
        "--wheel",
        "--out-dir",
    )
    assert Path(command[8]).name.startswith("ethos-wheel-build-")
    assert command[9:] == ("--no-create-gitignore",)


def test_host_conformance_reuses_the_single_package_acceptance_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class Session:
        @staticmethod
        def run(*command: str) -> None:
            events.append(command)

    monkeypatch.setattr(
        pipeline.DeliveryPipeline,
        "build",
        lambda _self, _session: events.append("build"),
    )
    monkeypatch.setattr(
        pipeline.DeliveryPipeline,
        "prove_install",
        lambda _self, _session: events.append("accept"),
    )

    pipeline.DeliveryPipeline(
        runtime=ProjectRuntime(ROOT, Path("/locked/python"), Path("/locked")),
        node_package_supply=ROOT / "node_modules",
    ).prove_host(cast("nox.Session", Session()))

    assert events == [
        "build",
        "accept",
        (
            "/locked/python",
            "-m",
            "pytest",
            "-q",
            "tests/architecture/test_portable_toolchain.py",
        ),
    ]


def test_adopter_is_clean_under_host_autocrlf(monkeypatch, tmp_path: Path) -> None:
    dirty = importlib.import_module("ethos.adapters.repo.dirty.change_provenance")
    global_config = tmp_path / "global.gitconfig"
    global_config.write_text("[core]\n\tautocrlf = true\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))

    def run(*command: str, cwd: Path | None = None) -> str:
        return subprocess.check_output(command, cwd=cwd, text=True).strip()

    adopter = tmp_path / "adopter"
    fixture.materialize_adopter(
        adopter,
        openspec_config=ROOT / "openspec/config.yaml",
        run=run,
    )
    assert fixture.line_ending_conformance(adopter, run=run) == ["lf", "crlf"]

    readme = adopter / "README.md"
    readme.write_bytes(readme.read_bytes().replace(b"\n", b"\r\n"))
    run("git", "add", "README.md", cwd=adopter)

    assert b"\r\n" in readme.read_bytes()
    assert run("git", "status", "--porcelain", cwd=adopter) == ""
    assert dirty.dirty_provenance(adopter)["state"] == "clean"


def test_signature_acceptance_exercises_the_real_isolated_command_boundary(tmp_path):
    def run(*command: str, cwd: Path | None = None) -> str:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
        return completed.stdout.strip()

    adopter = tmp_path / "adopter"
    fixture.materialize_adopter(
        adopter,
        openspec_config=ROOT / "openspec/config.yaml",
        run=run,
    )
    fixture.prepare_acceptance_topology(adopter, run=run)
    observed = lane.prove_signature_repair(Path(sys.executable), adopter, environment={})
    assert observed["state"] == "passed"
    assert observed["head"] != observed["previous_head"]
    assert observed["candidate_unchanged"] is True
    assert observed["remote_unchanged"] is True
    assert observed["reproof_executed"] is True
    assert observed["proof_subject"] == f"git:commit:{observed['head']}"
    assert observed["publication_readiness"] == "local_publish_ready"


def _blocked_command(command, gap, next_action):
    return {
        "schema_version": 2,
        "command": command,
        "verdict": "block",
        "state": "blocked",
        "summary": {},
        "diagnostics": [],
        "required_gaps": [gap],
        "next_action": next_action,
        "user_decision_required": False,
        "data": {},
        "continuation": "blocked",
        "missing_facts_or_evidence": [],
    }


def test_lane_lifecycle_failure_preserves_the_command_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = _blocked_command(
        "lane start", "candidate_worktree_missing", "ethos lane repair --root /repo --json"
    )
    monkeypatch.setattr(
        lane,
        "invoke",
        lambda *_args, **_kwargs: (
            1,
            result,
            json.dumps(result, sort_keys=True, separators=(",", ":")),
        ),
    )

    with pytest.raises(RuntimeError) as error:
        lane.prove_lifecycle(Path("/runtime/python"), tmp_path, environment={})

    assert str(error.value).startswith("package_lane_bootstrap_failed:")
    assert '"required_gaps":["candidate_worktree_missing"]' in str(error.value)
    assert '"next_action":"ethos lane repair --root /repo --json"' in str(error.value)


def test_package_cli_invocation_preserves_result_and_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = _blocked_command("status", "locked_environment_not_provisioned", "uv sync --frozen")
    monkeypatch.setattr(
        invocation,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=2,
            stdout=json.dumps(result),
            stderr="locked dependency unavailable",
        ),
    )

    returncode, observed, diagnostic = invocation.invoke(
        tmp_path,
        ("/runtime/ethos", "status", "--json"),
        environment={"PATH": "/native"},
    )

    assert returncode == 2
    assert observed == result
    assert '"required_gaps":["locked_environment_not_provisioned"]' in diagnostic
    assert diagnostic.endswith("stderr:locked dependency unavailable")


def test_lane_lifecycle_reuses_the_public_started_lane_for_recovery() -> None:
    prove_lifecycle = getattr(lane, "prove_lifecycle", None)

    assert callable(prove_lifecycle), "lane acceptance has no single public lifecycle owner"
    assert not hasattr(fixture, "seed_retirement_lease")


def test_installed_sdk_check_observes_without_mutating_or_authoring_intent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    smoke, adopter = tmp_path / "venv", tmp_path / "adopter"
    adopter.mkdir()
    executed: list[tuple[str, ...]] = []

    def run(*command: str, **_kwargs: object) -> str:
        executed.append(command)
        if command[-1] == "--version":
            return "ethos 0.2.0-alpha.3"
        if "Path(ethos.__file__)" in " ".join(command):
            return (smoke / "site-packages/ethos/__init__.py").as_posix()
        if "status" in command:
            return "{}"
        return ""

    monkeypatch.setattr(effect, "_run", run)
    monkeypatch.setattr(
        effect,
        "run_command",
        lambda *_args, **_kwargs: pytest.fail("SDK observation must not mutate lifecycle state"),
    )

    assert effect.observe_installed_package(smoke, adopter) == (
        (smoke / "site-packages/ethos/__init__.py").as_posix(),
        "ethos 0.2.0-alpha.3",
    )
    rendered = "\n".join(" ".join(command) for command in executed)
    assert "archive-change" not in rendered
    assert "rebuild-from" not in rendered
    assert "Commitment" not in rendered


def test_independent_cli_checks_do_not_replace_a_blocked_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[tuple[str, ...]] = []
    head = "a" * 40

    monkeypatch.setattr(
        effect,
        "_independent_host_environment",
        lambda: ({"PATH": "/native"}, "/native/git"),
    )

    def run_command(_root: Path, command: tuple[str, ...], **_kwargs: object):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout=f"{head}\n", stderr="")

    def invoke(_root: Path, command: tuple[str, ...], **_kwargs: object):
        commands.append(command)
        payload: dict[str, object] = {
            "schema_version": 2,
            "command": command[1],
            "verdict": "pass",
            "state": "ready",
            "required_gaps": [],
            "next_action": "",
            "data": {},
        }
        returncode = 0
        if command[1:3] == ("plan", "--changed"):
            payload.update(
                verdict="block",
                state="blocked",
                required_gaps=["change_generation_binding_invalid"],
                next_action="ethos lane repair --root /repo --json",
            )
            returncode = 1
        elif command[1:3] == ("publish", "--ref"):
            payload["data"] = {
                "transition_plan": {"effect": {"operation": "git.ref.compare-and-swap"}}
            }
        return returncode, payload, json.dumps(payload)

    monkeypatch.setattr(effect, "run_command", run_command)
    monkeypatch.setattr(effect.cli_invocation, "invoke", invoke)

    observation = effect.observe_independent_command_plane(tmp_path / "ethos", tmp_path)

    assert isinstance(observation["commands"], list)
    assert "plan --changed" in observation["commands"]
    assert sum(command[1:3] == ("plan", "--changed") for command in commands) == 1
    assert not any(command[1] == "plan" and "--changed" not in command for command in commands[1:])


def test_one_acceptance_effect_observes_the_complete_runtime_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    accept = getattr(effect, "observe_runtime_lifecycle", None)
    assert callable(accept), "package acceptance has no single lifecycle effect"

    bootstrap_environment = tmp_path / "bootstrap-environment"
    bootstrap_repository = tmp_path / "bootstrap-repository"
    repository = tmp_path / "adopter"
    for directory in (bootstrap_environment, bootstrap_repository, repository):
        directory.mkdir()
    (bootstrap_environment / "owned.txt").write_text("owned\n", encoding="utf-8")
    (bootstrap_repository / "owned.txt").write_text("owned\n", encoding="utf-8")

    events: list[str] = []
    bootstrap_python = tmp_path / "bootstrap-runtime/python/bin/python"
    runtime_python = tmp_path / "adopter-runtime/python/bin/python"
    activation_identity = {
        "wheel_sha256": "c" * 64,
        "source_commit": "a" * 40,
        "source_tree": "b" * 40,
    }
    bootstrap_report = {"runtime_digest": "1" * 64, **activation_identity}
    successor_report = {
        "runtime_digest": "2" * 64,
        "hooks_path": (tmp_path / "hooks").as_posix(),
        **activation_identity,
    }

    monkeypatch.setattr(
        effect.adopter_fixture,
        "materialize_bootstrap_repository",
        lambda *_args, **_kwargs: events.append("materialize_bootstrap_repository"),
    )
    monkeypatch.setattr(
        effect.adopter_fixture,
        "prepare_acceptance_topology",
        lambda *_args, **_kwargs: (
            events.append("prepare_acceptance_topology") or tmp_path / "candidate"
        ),
    )
    for method, stage, report in (
        ("activate_from_entrypoint", "hook_activation", bootstrap_report),
        ("activate_from_runtime", "successor_activation", successor_report),
    ):
        monkeypatch.setattr(
            effect.runtime_acceptance,
            method,
            lambda *_args, stage=stage, report=report, **_kwargs: events.append(stage) or report,
        )

    def require_manifest(report, *_args, **_kwargs):
        stage = "bootstrap_manifest" if report is bootstrap_report else "successor_manifest"
        events.append(stage)
        return bootstrap_python if report is bootstrap_report else runtime_python

    monkeypatch.setattr(effect.runtime_acceptance, "require_manifest", require_manifest)
    for method, stage in (
        ("require_production_dependencies", "development_dependencies"),
        ("require_version_identity", "immutable_identity"),
        ("prove_repair", "relocation_repair"),
    ):
        monkeypatch.setattr(
            effect.runtime_acceptance,
            method,
            lambda *_args, stage=stage, **_kwargs: events.append(stage) or {"state": "passed"},
        )
    monkeypatch.setattr(
        effect.lane_acceptance,
        "prove_lifecycle",
        lambda *_args, **_kwargs: (
            events.append("lane_lifecycle")
            or {
                "lane_bootstrap": {"state": "passed"},
                "retirement_recovery": {"state": "passed"},
            }
        ),
    )
    monkeypatch.setattr(
        effect.lane_acceptance,
        "prove_signature_repair",
        lambda *_args, **_kwargs: events.append("signature_repair") or {"state": "passed"},
        raising=False,
    )

    lifecycle = accept(
        installed_ethos=tmp_path / "wheel-environment/bin/ethos",
        bootstrap_environment=bootstrap_environment,
        bootstrap_repository=bootstrap_repository,
        repository=repository,
        build=BuildIdentity("0.2.0-alpha.3", "0.2.0a3.dev0+ga.ta", "a" * 40, "b" * 40),
        wheel_sha256="c" * 64,
        environment={},
    )

    assert events == [
        "materialize_bootstrap_repository",
        "prepare_acceptance_topology",
        "hook_activation",
        "bootstrap_manifest",
        "successor_activation",
        "successor_manifest",
        "development_dependencies",
        "immutable_identity",
        "relocation_repair",
        "signature_repair",
        "lane_lifecycle",
    ]
    assert set(lifecycle) == _LIFECYCLE_STAGES
    assert all(observation["state"] == "passed" for observation in lifecycle.values())
    assert not bootstrap_environment.exists()
    assert not bootstrap_repository.exists()


def _run_successful_acceptance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> SimpleNamespace:
    artifacts = tmp_path / "artifacts"
    work = tmp_path / "work"
    evidence = tmp_path / "evidence/smoke.json"
    artifacts.mkdir()
    wheel = artifacts / "ethos-0.2.0a3-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    sealed_runtime = work / "adopter/.git/ethos/runtime" / ("f" * 64) / "python"
    sealed_runtime.mkdir(parents=True)
    sealed_payload = sealed_runtime / "sealed.txt"
    sealed_payload.write_text("immutable runtime\n", encoding="utf-8")
    sealed_payload.chmod(0o444)
    sealed_runtime.chmod(0o555)
    sealed_runtime.parent.chmod(0o555)
    lifecycle = {stage: {"state": "passed"} for stage in _LIFECYCLE_STAGES}
    receipt = {"schema_version": 2, "verdict": "pass", "runtime_lifecycle": lifecycle}
    build = BuildIdentity("0.2.0-alpha.3", "0.2.0a3.dev0+ga.ta", "a" * 40, "b" * 40)
    observed: dict[str, object] = {}
    logs: list[str] = []
    cleanup_evidence_states: list[bool] = []
    remove_generated_tree = effect.remove_generated_tree

    monkeypatch.setattr(effect, "ROOT", tmp_path)
    monkeypatch.setattr(effect, "ARTIFACTS", artifacts)
    monkeypatch.setattr(effect, "WORK", work)
    monkeypatch.setattr(effect, "EVIDENCE", evidence)
    source_python = tmp_path / "project-python"
    monkeypatch.setattr(
        effect,
        "RUNTIME",
        SimpleNamespace(python=source_python, script=lambda _name: "/locked/uv"),
    )
    monkeypatch.setattr(effect, "current_tracked_head", lambda _root: "a" * 40)
    monkeypatch.setattr(effect, "wheel_build_identity", lambda _wheel: build)
    monkeypatch.setattr(effect, "_run", lambda *_command, **_kwargs: "")
    monkeypatch.setattr(
        effect,
        "prepare_locked_requirements",
        lambda root, work, python: (
            observed.update(
                supply_root=root,
                supply_work=work,
                supply_source_python=python,
            )
            or work / "locked-requirements.txt"
        ),
    )
    monkeypatch.setattr(
        effect,
        "install_locked_runtime",
        lambda root, source, target, wheel, requirements: observed.update(
            supply_root=root,
            supply_source_python=source,
            supply_python=target,
            supply_wheel=wheel,
            supply_constraints=requirements,
        ),
    )
    for owner, method, value in (
        (effect.adopter_fixture, "materialize_adopter", "d" * 40),
        (effect.adopter_fixture, "line_ending_conformance", ["lf", "crlf"]),
        (
            effect,
            "observe_installed_package",
            ("/installed/ethos/__init__.py", "ethos 0.2.0-alpha.3"),
        ),
        (effect, "observe_independent_command_plane", {"external_governance_available": False}),
        (effect, "_verify_resources", ["ethos/data/gates.toml"]),
    ):
        monkeypatch.setattr(owner, method, lambda *_args, value=value, **_kwargs: value)
    monkeypatch.setattr(
        effect,
        "observe_runtime_lifecycle",
        lambda **kwargs: observed.update(kwargs) or lifecycle,
    )

    def issue_receipt(**kwargs):
        observed["receipt"] = kwargs
        return receipt

    monkeypatch.setattr(effect, "package_acceptance_evidence", issue_receipt)

    def remove_owned_work(path: Path) -> None:
        cleanup_evidence_states.append(evidence.exists())
        remove_generated_tree(path)

    monkeypatch.setattr(effect, "remove_generated_tree", remove_owned_work)
    session = SimpleNamespace(error=pytest.fail, log=logs.append)

    effect.run(cast("nox.Session", session))

    return SimpleNamespace(
        cleanup_evidence_states=cleanup_evidence_states,
        evidence=evidence,
        lifecycle=lifecycle,
        logs=logs,
        observed=observed,
        receipt=receipt,
        sealed_payload=sealed_payload,
        wheel=wheel,
        work=work,
    )


def test_acceptance_runs_one_offline_lifecycle_and_cleans_before_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = _run_successful_acceptance(monkeypatch, tmp_path)

    assert result.observed["supply_python"] == result.work / "venv/bin/python"
    assert result.observed["supply_source_python"] == result.work.parent / "project-python"
    assert result.observed["supply_constraints"] == result.work / "locked-requirements.txt"
    assert result.observed["supply_wheel"] == result.wheel
    assert result.observed["environment"]["UV_OFFLINE"] == "1"
    assert "UV_CACHE_DIR" not in result.observed["environment"]

    assert not result.sealed_payload.exists()
    assert not result.work.exists()
    assert result.cleanup_evidence_states == [False, False]
    assert result.observed["receipt"]["runtime_lifecycle"] == result.lifecycle
    assert json.loads(result.evidence.read_text(encoding="utf-8")) == result.receipt
    assert json.loads(result.logs[0]) == result.receipt
