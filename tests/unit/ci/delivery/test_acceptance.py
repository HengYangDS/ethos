"""One offline acceptance effect owns package lifecycle execution and its receipt."""

from __future__ import annotations

import hashlib
import json
import shlex
import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast
from unittest.mock import Mock
from unittest.mock import call

import pytest

import tools.ci.local_ci as local_ci
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.runtime.transition import PackageArtifact
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.release.identity import BuildIdentity
from tools.ci import sessions
from tools.ci.delivery import pipeline
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import receipt
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[4]
_LIFECYCLE_STAGES = {
    "development_dependencies",
    "hook_activation",
    "immutable_identity",
    "lane_bootstrap",
    "relocation_repair",
    "retirement_recovery",
    "successor_activation",
    "signature_repair",
    "native_merge",
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
    expected = resolve_gate_policy(ROOT, full=True)
    assert local_ci.owner_commands() == [
        shlex.join(gate_execution_identity(expected.registry[node.id])) for node in expected.nodes
    ]
    assert expected.gate_ids.count("local-install-smoke") == 1


@pytest.mark.parametrize("release_head", ["", "a" * 40])
def test_install_smoke_invokes_one_acceptance_transaction(monkeypatch, tmp_path, release_head):
    session = SimpleNamespace(
        posargs=("--release", "--expect-head", release_head) if release_head else ()
    )
    artifact = object()
    accept = Mock()
    prepare = Mock(return_value=artifact)
    monkeypatch.setattr(pipeline.acceptance_effect, "run", accept)
    monkeypatch.setattr(pipeline, "prepare_release_candidate", prepare)
    monkeypatch.setattr(sessions, "RUNTIME", ProjectRuntime.discover(tmp_path))
    monkeypatch.setattr(ProjectRuntime, "node_package_supply", lambda _: tmp_path / "node_modules")
    sessions.install_smoke(session)
    if release_head:
        prepare.assert_called_once_with(tmp_path, release_head)
        accept.assert_called_once_with(
            session,
            artifact=artifact,
            evidence=tmp_path / "build/evidence/local-install/release-smoke.json",
        )
    else:
        prepare.assert_not_called()
        accept.assert_called_once_with(session)


def test_wheel_build_reuses_the_locked_project_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = Mock()

    monkeypatch.setattr(pipeline, "publish_built_wheel", lambda *_args: tmp_path / "ethos.whl")
    monkeypatch.chdir(tmp_path)
    runtime = ProjectRuntime(tmp_path, Path("/locked/bin/python"), Path("/locked/bin"))
    monkeypatch.setattr(ProjectRuntime, "script", lambda _self, name: f"/locked/bin/{name}")

    pipeline.DeliveryPipeline(
        runtime=runtime,
        node_package_supply=tmp_path / "node_modules",
    ).build(session)

    session.run.assert_called_once()
    command = session.run.call_args.args
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
    calls = Mock()
    session = Mock()
    for name, target in (
        ("build", pipeline.DeliveryPipeline),
        ("prove_install", pipeline.DeliveryPipeline),
    ):
        monkeypatch.setattr(target, name, getattr(calls, name))
    calls.attach_mock(session.run, "run")
    pipeline.DeliveryPipeline(
        ProjectRuntime(ROOT, Path("/locked/python"), Path("/locked")), ROOT / "node_modules"
    ).prove_host(session)
    assert calls.mock_calls == [
        call.build(session),
        call.prove_install(session),
        call.run(
            "/locked/python", "-m", "pytest", "-q", "tests/architecture/test_portable_toolchain.py"
        ),
    ]


def test_one_acceptance_effect_observes_the_complete_runtime_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
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
    bootstrap_report, successor_report = (
        {
            "runtime_digest": digit * 64,
            "wheel_sha256": "c" * 64,
            "source_commit": "a" * 40,
            "source_tree": "b" * 40,
        }
        for digit in ("1", "2")
    )
    successor_report["hooks_path"] = (tmp_path / "hooks").as_posix()

    def require_manifest(report, *_args, **_kwargs):
        stage = "bootstrap_manifest" if report is bootstrap_report else "successor_manifest"
        events.append(stage)
        return bootstrap_python if report is bootstrap_report else runtime_python

    monkeypatch.setattr(effect.runtime_acceptance, "require_manifest", require_manifest)
    declarations = (
        (effect.adopter_fixture, "materialize_bootstrap_repository", None),
        (effect.adopter_fixture, "prepare_acceptance_topology", tmp_path / "candidate"),
        (effect.runtime_acceptance, "activate_from_entrypoint", bootstrap_report),
        (effect.runtime_acceptance, "activate_from_runtime", successor_report),
        (effect.runtime_acceptance, "require_production_dependencies", {"state": "passed"}),
        (effect.runtime_acceptance, "require_version_identity", {"state": "passed"}),
        (effect.runtime_acceptance, "prove_repair", {"state": "passed"}),
        (effect.lane_acceptance, "prove_signature_repair", {"state": "passed"}),
        (
            effect.lane_acceptance,
            "prove_lifecycle",
            {
                stage: {"state": "passed"}
                for stage in ("lane_bootstrap", "retirement_recovery", "native_merge")
            },
        ),
    )
    for owner, method, result in declarations:
        monkeypatch.setattr(
            owner,
            method,
            lambda *_args, stage=method, result=result, **_kwargs: events.append(stage) or result,
        )

    lifecycle = effect.observe_runtime_lifecycle(
        installed_ethos=tmp_path / "wheel-environment/bin/ethos",
        bootstrap_environment=bootstrap_environment,
        bootstrap_repository=bootstrap_repository,
        repository=repository,
        build=BuildIdentity("0.2.0-alpha.3", "0.2.0a3.dev0+ga.ta", "a" * 40, "b" * 40),
        wheel_sha256="c" * 64,
        environment={},
    )

    expected = [method for _owner, method, _result in declarations]
    expected.insert(expected.index("activate_from_entrypoint") + 1, "bootstrap_manifest")
    expected.insert(expected.index("activate_from_runtime") + 1, "successor_manifest")
    assert events == expected
    assert set(lifecycle) == _LIFECYCLE_STAGES
    assert all(observation["state"] == "passed" for observation in lifecycle.values())
    assert not bootstrap_environment.exists()
    assert not bootstrap_repository.exists()


@pytest.fixture
def acceptance_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Isolate expensive lifecycle effects while retaining the real receipt compiler."""
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
    build = BuildIdentity("0.2.0-alpha.3", "0.2.0a3.dev0+ga.ta", "a" * 40, "b" * 40)
    lifecycle["successor_activation"]["runtime_digest"] = "f" * 64
    monkeypatch.setattr(effect, "git_common_dir", lambda root: str(root / ".git"))
    observed: dict[str, object] = {}
    logs: list[str] = []
    cleanup_evidence_states: list[bool] = []
    remove_generated_tree = effect.remove_generated_tree

    source_python = tmp_path / "project-python"
    for name, value in {
        "ROOT": tmp_path,
        "ARTIFACTS": artifacts,
        "WORK": work,
        "EVIDENCE": evidence,
        "RUNTIME": SimpleNamespace(python=source_python, script=lambda _name: "/locked/uv"),
        "current_tracked_head": lambda _root: "a" * 40,
        "wheel_build_identity": lambda _wheel: build,
        "_run": lambda *_command, **_kwargs: "",
        "prepare_locked_requirements": lambda _root, work, _python: (
            work / "locked-requirements.txt"
        ),
        "install_locked_runtime": lambda *args: observed.update(supply=args),
        "observe_runtime_lifecycle": lambda **kwargs: observed.update(kwargs) or lifecycle,
    }.items():
        monkeypatch.setattr(effect, name, value)
    for owner, method, value in (
        (effect, "package_runtime", {"path": "archive", "runtime_digest": "f" * 64}),
        (effect.runtime_acceptance, "prove_shared_supply", {"state": "passed"}),
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
        monkeypatch.setattr(owner, method, Mock(return_value=value))

    def remove_owned_work(path: Path) -> None:
        cleanup_evidence_states.append(evidence.exists())
        remove_generated_tree(path)

    monkeypatch.setattr(effect, "remove_generated_tree", remove_owned_work)
    compile_receipt = Mock(wraps=receipt.package_acceptance_evidence)
    monkeypatch.setattr(effect, "package_acceptance_evidence", compile_receipt)
    return SimpleNamespace(
        receipt=compile_receipt,
        wheel=wheel,
        build=build,
        lifecycle=lifecycle,
        observed=observed,
        logs=logs,
        cleanup=cleanup_evidence_states,
        sealed_payload=sealed_payload,
    )


@pytest.mark.parametrize(
    "selection", ["default", "explicit", "changed", "changed-after", "changed-head"]
)
def test_acceptance_runs_one_offline_lifecycle_and_cleans_before_evidence(
    monkeypatch,
    tmp_path,
    acceptance_case,
    selection,
) -> None:
    case = acceptance_case
    work, evidence = effect.WORK, effect.EVIDENCE
    session = SimpleNamespace(error=pytest.fail, log=case.logs.append)
    selected = case.wheel
    output = evidence
    artifact = None
    if selection != "default":
        evidence.parent.mkdir()
        evidence.write_text("previous development acceptance")
        output = evidence.with_name("release-smoke.json")
        selected = tmp_path / "selected.whl"
        selected.write_bytes(b"selected wheel")
        artifact = PackageArtifact(
            selected, hashlib.sha256(selected.read_bytes()).hexdigest(), case.build
        )
    if selection.startswith("changed"):

        def change_artifact(*_args, **_kwargs):
            selected.write_bytes(b"changed after selection")
            return {"state": "passed"}

        if selection == "changed":
            change_artifact()
        elif selection == "changed-head":
            monkeypatch.setattr(effect, "current_tracked_head", lambda _: "e" * 40)
        else:
            monkeypatch.setattr(effect.runtime_acceptance, "prove_shared_supply", change_artifact)
        with pytest.raises(ValueError, match="package_acceptance_artifact_changed"):
            effect.run(cast("nox.Session", session), artifact=artifact, evidence=output)
        assert not output.exists()
        assert case.sealed_payload.exists() == (selection != "changed-after")
    else:
        effect.run(cast("nox.Session", session), artifact=artifact, evidence=output)
        payload = json.loads(output.read_text())
        assert case.observed["supply"] == (
            tmp_path,
            tmp_path / "project-python",
            work / "venv/bin/python",
            selected,
            work / "locked-requirements.txt",
        )
        assert case.observed["environment"]["UV_OFFLINE"] == "1"
        assert "UV_CACHE_DIR" not in case.observed["environment"]
        _assert_acceptance_receipt(case, payload, selected, tmp_path, artifact)
        assert not work.exists()
        assert case.cleanup == [bool(artifact), bool(artifact)]
        assert json.loads(case.logs[0]) == payload
    if artifact:
        assert evidence.read_text() == "previous development acceptance"


def test_failed_package_supply_cleans_owned_work(monkeypatch, acceptance_case):
    work = effect.WORK

    def fail_supply(*_args):
        (work / "partial-supply").mkdir()
        message = "expected supply failure"
        raise RuntimeError(message)

    monkeypatch.setattr(effect, "install_locked_runtime", fail_supply)
    with pytest.raises(RuntimeError, match="expected supply failure"):
        effect.run(cast("nox.Session", object()))
    assert not work.exists()
    assert not effect.EVIDENCE.exists()
    assert not acceptance_case.observed


@pytest.mark.parametrize("shape", ["missing", "directory", "symlink", "multiple"])
def test_release_candidate_requires_one_regular_wheel(monkeypatch, tmp_path, shape):
    wheel = tmp_path / "build/artifacts/release/python/ethos-selected.whl"
    wheel.parent.mkdir(parents=True)
    if shape == "directory":
        wheel.mkdir()
    elif shape == "symlink":
        wheel.symlink_to("absent")
    elif shape == "multiple":
        wheel.touch()
        wheel.with_name("ethos-other.whl").touch()
    monkeypatch.setattr(pipeline, "_release_source_identity", lambda *_: object())
    with pytest.raises(ValueError, match="release_wheel_output_invalid"):
        pipeline.prepare_release_candidate(tmp_path, "a" * 40)
    assert not (tmp_path / ".git").exists()


def _assert_acceptance_receipt(case, payload, selected, tmp_path, artifact):
    """Check the real producer's binding and the negative incomplete-stage contract."""
    assert payload["build_identity"] == case.build.projection()
    assert payload["runtime_lifecycle"] == case.lifecycle
    assert payload["head"] == "a" * 40
    assert payload["generated_at"] == case.receipt.call_args.kwargs["generated_at"].isoformat()
    for field in (
        "hosted_ci_status_claimed",
        "remote_publication_claimed",
        "registry_publication_claimed",
    ):
        assert payload[field] is False
    assert isinstance(payload["conformance"], dict)
    assert "sdk_commitment_digest" not in payload["conformance"]
    assert payload["wheels"][0]["path"] == selected.relative_to(tmp_path).as_posix()
    incomplete = dict(case.lifecycle)
    incomplete.pop("retirement_recovery")
    with pytest.raises(ValueError, match="package_runtime_lifecycle_incomplete"):
        receipt.package_acceptance_evidence(
            **(case.receipt.call_args.kwargs | {"resources": [], "runtime_lifecycle": incomplete})
        )
    assert payload["wheels"][0]["sha256"] == hashlib.sha256(selected.read_bytes()).hexdigest()
    assert (" -- --release --expect-head " in payload["command"]) == bool(artifact)
