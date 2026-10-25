"""One offline acceptance effect owns package lifecycle execution and its receipt."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast
from unittest.mock import Mock

import pytest

from ethos.adapters.process import command_scope
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.transition import PackageArtifact
from ethos.repository.release.identity import build_identity
from tools.ci.delivery import artifact as artifact_owner
from tools.ci.delivery import distribution as native_distribution
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import receipt

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def acceptance_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Isolate expensive lifecycle effects while retaining the real receipt compiler."""
    artifacts = tmp_path / "artifacts"
    work = tmp_path / "work"
    evidence = tmp_path / "evidence/smoke.json"
    artifacts.mkdir()
    wheel = artifacts / "ethos-0.2.0a3-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    sealed_runtime = work / "shared-installation" / ("f" * 64) / "python"
    sealed_runtime.mkdir(parents=True)
    sealed_payload = sealed_runtime / "sealed.txt"
    sealed_payload.write_text("immutable runtime\n", encoding="utf-8")
    sealed_payload.chmod(0o444)
    sealed_runtime.chmod(0o555)
    sealed_runtime.parent.chmod(0o555)
    lifecycle = {stage: {"state": "passed"} for stage in receipt.REQUIRED_LIFECYCLE_STAGES}
    build = build_identity(product="0.2.0-alpha.3", source_commit="a" * 40, source_tree="b" * 40)
    lifecycle["repository_activation"]["runtime_digest"] = "f" * 64
    monkeypatch.setattr(effect, "git_common_dir", lambda root: str(root / ".git"))
    selected_runtime = Mock(
        return_value=SimpleNamespace(root=sealed_runtime.parent, digest="f" * 64)
    )
    monkeypatch.setattr(effect, "current_runtime", selected_runtime)
    observed: dict[str, object] = {}
    logs: list[str] = []
    cleanup_evidence_states: list[bool] = []
    remove_generated_tree = effect.remove_generated_tree

    source_python = tmp_path / "project-python"
    image_python = tmp_path / "image-python"
    image_source = Mock(return_value={"executable": str(image_python)})
    monkeypatch.setattr(effect, "require_python_image_source", image_source)
    for name, value in {
        "ROOT": tmp_path,
        "ARTIFACTS": artifacts,
        "WORK": work,
        "EVIDENCE": evidence,
        "RUNTIME": SimpleNamespace(python=source_python, script=lambda _name: "/locked/uv"),
        "current_tracked_head": lambda _root: "a" * 40,
        "selected_wheel": lambda _root, **_kwargs: PackageArtifact(
            wheel, hashlib.sha256(wheel.read_bytes()).hexdigest(), build
        ),
        "_run": lambda *_command, **_kwargs: "",
        "prepare_locked_requirements": lambda _root, work, _python: (
            work / "locked-requirements.txt"
        ),
        "install_locked_runtime": lambda *args: observed.update(supply=args),
    }.items():
        monkeypatch.setattr(effect, name, value)
    monkeypatch.setattr(
        effect.runtime_acceptance,
        "observe_lifecycle",
        lambda **kwargs: observed.update(kwargs) or lifecycle,
    )
    monkeypatch.setattr(artifact_owner, "source_build_identity", lambda _root: build)
    monkeypatch.setattr(artifact_owner, "wheel_build_identity", lambda _wheel: build)

    def package_runtime(_runtime: Path, wheel: Path, destination: Path, **_kwargs):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"qualified native archive")
        cask = destination.parent / "homebrew/Casks/ethos.rb"
        cask.parent.mkdir(parents=True, exist_ok=True)
        cask.write_text(destination.as_uri())
        return {
            "path": str(destination),
            "homebrew_cask": str(cask),
            "runtime_digest": "f" * 64,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        }

    package = Mock(side_effect=package_runtime)
    monkeypatch.setattr(effect, "package_runtime", package)
    monkeypatch.setattr(native_distribution, "package_runtime", package)
    for owner, method, value in (
        (effect, "prove_shared_supply", {"state": "passed"}),
        (effect.adopter_fixture, "materialize_adopter", "d" * 40),
        (effect.adopter_fixture, "line_ending_conformance", ["lf", "crlf"]),
        (
            effect.adopter_fixture,
            "prove_formation",
            {
                "state": "passed",
                "first_change": "lane_admitted",
                "agent_handoff": "passed",
                "formatting": "passed",
            },
        ),
        (
            effect,
            "observe_installed_package",
            (
                "/installed/ethos/__init__.py",
                "ethos 0.2.0-alpha.3",
                {"state": "passed", "native_git_loss": "not_qualified"},
            ),
        ),
        (
            effect,
            "observe_independent_command_plane",
            {"external_governance_available": False},
        ),
        (
            effect.brownfield_acceptance,
            "prove_brownfield",
            {
                "state": "passed",
                "authored_content_preserved": True,
                "planned_files": [".ethos/profile.toml", "openspec/config.yaml"],
            },
        ),
        (effect, "_verify_resources", ["ethos/resources/system/gates.toml"]),
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
        selected_runtime=selected_runtime,
        image_source=image_source,
    )


def test_console_uses_image_source_without_changing_locked_dependency_owner(
    monkeypatch, tmp_path, acceptance_case
):
    command = Mock(return_value="")
    requirements = Mock(return_value=effect.WORK / "locked-requirements.txt")
    monkeypatch.setattr(effect, "_run", command)
    monkeypatch.setattr(effect, "prepare_locked_requirements", requirements)
    effect.run(cast("nox.Session", SimpleNamespace(error=pytest.fail, log=lambda _: None)))
    assert command.call_args_list[0].args == (
        "/locked/uv",
        "venv",
        "--offline",
        "--python",
        str(tmp_path / "image-python"),
        str(effect.WORK / "venv"),
    )
    acceptance_case.image_source.assert_called_once_with(tmp_path / "project-python")
    requirements.assert_called_once_with(tmp_path, effect.WORK, tmp_path / "project-python")
    assert acceptance_case.observed["supply"][1] == tmp_path / "project-python"


@pytest.mark.parametrize(
    "selection", ["default", "explicit", "changed", "changed-after", "changed-head"]
)
def test_acceptance_runs_one_offline_lifecycle_and_cleans_before_evidence(
    monkeypatch,
    tmp_path,
    acceptance_case,
    selection,
) -> None:
    monkeypatch.setenv("UV_PYTHON_INSTALL_DIR", str(tmp_path / "python-images"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "ambient-data"))
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
            monkeypatch.setattr(effect, "prove_shared_supply", change_artifact)
        with pytest.raises(ValueError, match="package_acceptance_artifact_changed"):
            effect.run(cast("nox.Session", session), artifact=artifact, evidence=output)
        assert not output.exists()
        assert not (tmp_path / "build/artifacts/native").exists()
        assert case.sealed_payload.exists() == (selection != "changed-after")
    else:
        effect.run(cast("nox.Session", session), artifact=artifact, evidence=output)
        payload = json.loads(output.read_text())
        events = [
            json.loads(line)
            for line in output.with_suffix(".events.jsonl").read_text().splitlines()
        ]
        assert events[0]["head"] == case.build.source_commit
        assert events[0]["wheel_sha256"] == hashlib.sha256(selected.read_bytes()).hexdigest()
        assert any(
            event.get("name") == "owned_cleanup" and event.get("state") == "completed"
            for event in events
        )
        case.selected_runtime.assert_called_once_with(
            work / "adopter/.git", expected_build=case.build
        )
        _assert_retained_distribution(case, payload, work=work, root=tmp_path)
        assert case.observed["supply"] == (
            tmp_path,
            tmp_path / "project-python",
            work / "venv/bin/python",
            selected,
            work / "locked-requirements.txt",
        )
        expected_environment = {
            "UV_OFFLINE": "1",
            "UV_PYTHON_INSTALL_DIR": str(tmp_path / "python-images"),
            "XDG_DATA_HOME": str(work / "host-data"),
        }
        assert expected_environment.items() <= case.observed["environment"].items()
        assert "UV_CACHE_DIR" not in case.observed["environment"]
        for observer in (
            effect.observe_installed_package,
            effect.observe_independent_command_plane,
        ):
            assert (
                cast("Mock", observer).call_args.kwargs["environment"]
                == case.observed["environment"]
            )
        _assert_acceptance_receipt(case, payload, selected, tmp_path, artifact, output)
        assert not work.exists()
        assert case.cleanup == [bool(artifact), bool(artifact)]
        assert json.loads(case.logs[0]) == payload
    if artifact:
        assert evidence.read_text() == "previous development acceptance"


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        ("command", RuntimeError),
        ("cleanup", OSError),
        ("interrupt", KeyboardInterrupt),
        ("deadline", subprocess.TimeoutExpired),
        pytest.param(
            "terminate",
            KeyboardInterrupt,
            marks=pytest.mark.skipif(os.name != "posix", reason="POSIX SIGTERM delivery"),
        ),
    ],
)
def test_failed_package_supply_cleans_owned_work(monkeypatch, acceptance_case, failure, expected):
    previous_handler = signal.getsignal(signal.SIGTERM)
    cleanup = effect.remove_generated_tree

    def remove(path):
        partial = (path / "partial-supply").exists()
        cleanup(path)
        if failure == "cleanup" and partial:
            message = "private cleanup detail"
            raise OSError(message)

    def fail_supply(*_args):
        (effect.WORK / "partial-supply").mkdir()
        if failure == "deadline":
            with command_scope(timeout_seconds=0.01):
                run_command(effect.WORK, (sys.executable, "-c", "import time; time.sleep(1)"))
        if failure == "terminate":
            assert callable(signal.getsignal(signal.SIGTERM))
            assert signal.getsignal(signal.SIGTERM) != previous_handler
            os.kill(os.getpid(), signal.SIGTERM)
        message = "expected supply failure"
        if failure == "interrupt":
            raise KeyboardInterrupt(message)
        raise RuntimeError(message)

    monkeypatch.setattr(effect, "install_locked_runtime", fail_supply)
    monkeypatch.setattr(effect, "remove_generated_tree", remove)
    with pytest.raises(expected):
        effect.run(cast("nox.Session", object()))
    assert not effect.WORK.exists()
    assert not effect.EVIDENCE.exists()
    assert not acceptance_case.observed
    terminal = json.loads(effect.EVIDENCE.with_suffix(".terminal.json").read_text())
    assert terminal["verdict"] == "block"
    assert terminal["error_type"] == expected.__name__
    assert terminal["error_types"] == (
        ["OSError", "RuntimeError"] if failure == "cleanup" else [expected.__name__]
    )
    assert "private cleanup detail" not in json.dumps(terminal)
    assert terminal["owned_work_absent"] is True
    assert terminal["acceptance_written"] is False
    assert (
        terminal["wheel_sha256"] == hashlib.sha256(acceptance_case.wheel.read_bytes()).hexdigest()
    )
    assert signal.getsignal(signal.SIGTERM) == previous_handler


@pytest.mark.skipif(os.name != "posix", reason="POSIX SIGTERM delivery")
@pytest.mark.parametrize("stage", ["setup", "cleanup", "terminal"])
def test_interruption_completes_owned_terminalization(monkeypatch, acceptance_case, stage):
    """A first signal at a critical boundary cannot strand work or lose its result."""
    previous = signal.getsignal(signal.SIGTERM)
    wheel = acceptance_case.wheel
    mkdir, replace, remove = Path.mkdir, Path.replace, effect.remove_generated_tree
    supplied = effect.install_locked_runtime
    delivered = []

    def deliver():
        assert callable(signal.getsignal(signal.SIGTERM))
        assert signal.getsignal(signal.SIGTERM) != previous
        os.kill(os.getpid(), signal.SIGTERM)
        delivered.append(stage)

    def create(path, *args, **kwargs):
        mkdir(path, *args, **kwargs)
        if path == effect.WORK and stage == "setup":
            deliver()

    def cleanup(path):
        if stage == "cleanup" and (path / "partial-supply").exists():
            deliver()
        remove(path)

    def terminal(path, target):
        if stage == "terminal" and target == effect.EVIDENCE.with_suffix(".terminal.json"):
            deliver()
        return replace(path, target)

    def supply(*args):
        (effect.WORK / "partial-supply").mkdir()
        if stage == "terminal":
            message = "expected supply failure"
            raise RuntimeError(message)
        return supplied(*args)

    monkeypatch.setattr(Path, "mkdir", create)
    monkeypatch.setattr(Path, "replace", terminal)
    monkeypatch.setattr(effect, "remove_generated_tree", cleanup)
    monkeypatch.setattr(effect, "install_locked_runtime", supply)
    expected = RuntimeError if stage == "terminal" else KeyboardInterrupt
    with pytest.raises(expected):
        effect.run(cast("nox.Session", SimpleNamespace(error=pytest.fail, log=lambda _: None)))
    payload = json.loads(effect.EVIDENCE.with_suffix(".terminal.json").read_text())
    assert payload["owned_work_absent"] is True
    assert payload["acceptance_written"] is False
    assert payload["error_type"] == expected.__name__
    assert payload["wheel_sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert not effect.WORK.exists()
    assert not effect.EVIDENCE.exists()
    assert signal.getsignal(signal.SIGTERM) == previous
    assert delivered


def test_concurrent_formation_failure_fails_acceptance_and_cleans_owned_work(
    monkeypatch, acceptance_case
):
    def fail_formation(*_args, **_kwargs):
        message = "expected formation failure"
        raise RuntimeError(message)

    monkeypatch.setattr(effect.adopter_fixture, "prove_formation", fail_formation)
    with pytest.raises(RuntimeError, match="expected formation failure"):
        effect.run(cast("nox.Session", object()))
    (formation,) = acceptance_case.observed["bootstrap_users"]
    assert formation.done()
    assert not effect.WORK.exists()
    assert not effect.EVIDENCE.exists()


def _assert_retained_distribution(case, payload, *, work: Path, root: Path) -> None:
    """Retain the same native package the smoke qualified, beside the source artifacts."""
    packages = cast("Mock", effect.package_runtime).call_args_list
    assert [package.args[0] for package in packages] == [case.sealed_payload.parent.parent] * 2
    assert packages[0].args[2].is_relative_to(work)
    distribution = payload["distribution"]
    archive = Path(distribution["path"])
    assert archive == packages[1].args[2]
    assert archive.is_relative_to(root / "build/artifacts/native" / ("f" * 64))
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == distribution["sha256"]
    assert Path(distribution["homebrew_cask"]).read_text() == archive.as_uri()
    assert distribution["runtime_digest"] == "f" * 64
    assert distribution["shared_supply"] == {"state": "passed"}
    assert distribution["retained"] is True


def _assert_acceptance_receipt(case, payload, selected, tmp_path, artifact, output):
    """Check the real producer's binding and the negative incomplete-stage contract."""
    assert payload["build_identity"] == case.build.projection()
    assert payload["runtime_lifecycle"] == case.lifecycle
    assert payload["head"] == "a" * 40
    inputs = case.receipt.call_args.kwargs
    assert payload["generated_at"] == inputs["generated_at"].isoformat()
    assert payload["execution_events"] == output.with_suffix(".events.jsonl").as_posix()
    assert payload["qualification"] == {
        "fresh_installation": "passed",
        "cross_repository_activation": "passed",
        "retained_state_upgrade": "not_qualified",
        "interruption_recovery": "not_qualified",
        "live_consumer_safe_uninstall": "not_qualified",
    }
    for field in (
        "hosted_ci_status_claimed",
        "remote_publication_claimed",
        "registry_publication_claimed",
    ):
        assert payload[field] is False
    for field in ("command_plane", "formation", "brownfield"):
        assert payload["conformance"][field] == inputs[field]
    invalid_cases = (
        (
            "package_brownfield_preservation_incomplete",
            "brownfield",
            {"authored_content_preserved": False},
        ),
        ("package_first_change_claim_invalid", "formation", {"first_change": "skeleton_created"}),
        ("package_formation_incomplete", "formation", {"state": "blocked"}),
        ("package_agent_handoff_incomplete", "formation", {"agent_handoff": "not_attempted"}),
        ("package_source_format_incomplete", "formation", {"formatting": "not_attempted"}),
        ("package_command_plane_incomplete", "command_plane", {"state": "blocked"}),
    )
    for error, field, invalid in invalid_cases:
        with pytest.raises(ValueError, match=error):
            receipt.package_acceptance_evidence(**(inputs | {field: inputs[field] | invalid}))
    assert "sdk_commitment_digest" not in payload["conformance"]
    assert payload["wheels"][0]["path"] == selected.relative_to(tmp_path).as_posix()
    incomplete = dict(case.lifecycle)
    incomplete.pop("retirement_recovery")
    with pytest.raises(ValueError, match="package_runtime_lifecycle_incomplete"):
        receipt.package_acceptance_evidence(
            **(inputs | {"resources": [], "runtime_lifecycle": incomplete})
        )
    upgraded = case.lifecycle | {"retained_state_upgrade": {"state": "passed"}}
    qualified = receipt.package_acceptance_evidence(**(inputs | {"runtime_lifecycle": upgraded}))
    assert qualified["qualification"] == payload["qualification"] | {
        "retained_state_upgrade": "passed"
    }
    with pytest.raises(ValueError, match="package_runtime_lifecycle_incomplete"):
        receipt.package_acceptance_evidence(
            **(
                inputs
                | {"runtime_lifecycle": upgraded | {"retained_state_upgrade": {"state": "blocked"}}}
            )
        )
    assert payload["wheels"][0]["sha256"] == hashlib.sha256(selected.read_bytes()).hexdigest()
    assert (" -- --release --expect-head " in payload["command"]) == bool(artifact)
