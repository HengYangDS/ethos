"""Installed acceptance observes and retires one complete runtime lifecycle."""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from contextlib import nullcontext
from contextvars import copy_context
from pathlib import Path
from time import monotonic
from time import sleep
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest

from ethos.adapters.process import CommandScope
from ethos.adapters.process import command_scope
from ethos.adapters.process import run_command
from ethos.repository.release.identity import BuildIdentity
from tests.support.runtime_scenarios import fixture_runtime_generation
from tests.support.runtime_scenarios import runtime_build
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import invocation
from tools.ci.delivery.acceptance import receipt
from tools.ci.delivery.acceptance import runtime as runtime_acceptance

if TYPE_CHECKING:
    import subprocess

    import nox

    from ethos.adapters.repo.runtime.transition import PackageArtifact


@pytest.mark.parametrize(
    "failure_stage",
    [
        None,
        "activate_from_entrypoint",
        "activate_from_runtime",
        "bootstrap_manifest",
        "successor_manifest",
    ],
)
def test_one_acceptance_effect_observes_fresh_installation_and_repository_reuse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure_stage: str | None,
) -> None:
    bootstrap_environment, bootstrap_repository, repository = (
        tmp_path / name for name in ("bootstrap-environment", "bootstrap-repository", "adopter")
    )
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
        for digit in ("1", "1")
    )
    successor_report["hooks_path"] = (tmp_path / "hooks").as_posix()

    def require_manifest(report, *_args, **_kwargs):
        stage = "bootstrap_manifest" if report is bootstrap_report else "successor_manifest"
        events.append(stage)
        if stage == failure_stage:
            raise RuntimeError(stage)
        return bootstrap_python if report is bootstrap_report else runtime_python

    monkeypatch.setattr(runtime_acceptance, "require_manifest", require_manifest)
    declarations = (
        (runtime_acceptance.adopter_fixture, "materialize_bootstrap_repository", None),
        (
            runtime_acceptance.adopter_fixture,
            "prepare_acceptance_topology",
            tmp_path / "candidate",
        ),
        (runtime_acceptance, "activate_from_entrypoint", bootstrap_report),
        (runtime_acceptance, "activate_from_runtime", successor_report),
        (runtime_acceptance, "require_production_dependencies", {"state": "passed"}),
        (runtime_acceptance, "require_version_identity", {"state": "passed"}),
        (runtime_acceptance, "prove_repair", {"state": "passed"}),
        (
            runtime_acceptance.lane_acceptance,
            "prove_signature_repair",
            {"state": "passed"},
        ),
        (
            runtime_acceptance.lane_acceptance,
            "prove_lifecycle",
            {
                stage: {"state": "passed"}
                for stage in ("lane_bootstrap", "retirement_recovery", "native_merge")
            },
        ),
    )
    for owner, method, result in declarations:

        def observe(*_args, stage=method, result=result, **_kwargs):
            events.append(stage)
            if stage == failure_stage:
                raise RuntimeError(stage)
            return result

        monkeypatch.setattr(owner, method, observe)

    def require_bound_identity(*arguments, **identity):
        assert arguments == (runtime_python, repository)
        assert identity["runtime_digest"] == "1" * 64
        events.append("require_version_identity")
        return {"state": "passed"}

    monkeypatch.setattr(runtime_acceptance, "require_version_identity", require_bound_identity)
    settled: list[bool] = []

    def settle(users):
        events.append("bootstrap_users")
        settled.append(bootstrap_environment.exists() and bootstrap_repository.exists())
        formation.set_result({"state": "passed"})
        return wait(users)

    monkeypatch.setattr(runtime_acceptance, "wait", settle)
    formation: Future[dict[str, object]] = Future()
    formation.set_running_or_notify_cancel()
    with pytest.raises(RuntimeError, match=failure_stage) if failure_stage else nullcontext():
        lifecycle = runtime_acceptance.observe_lifecycle(
            installed_ethos=tmp_path / "wheel-environment/bin/ethos",
            bootstrap_environment=bootstrap_environment,
            bootstrap_repository=bootstrap_repository,
            repository=repository,
            build=BuildIdentity("0.2.0-alpha.3", "0.2.0a3.dev0+ga.ta", "a" * 40, "b" * 40),
            wheel_sha256="c" * 64,
            environment={},
            bootstrap_users=(formation,),
            run=lambda *_args, **_kwargs: "",
        )
    assert formation.done()
    assert settled == [True]
    assert not bootstrap_environment.exists()
    assert not bootstrap_repository.exists()
    if failure_stage:
        assert events[-1] == "bootstrap_users"
        return

    expected = [method for _owner, method, _result in declarations]
    expected.insert(expected.index("activate_from_entrypoint") + 1, "bootstrap_manifest")
    expected.insert(expected.index("activate_from_runtime") + 1, "successor_manifest")
    expected.insert(expected.index("successor_manifest") + 1, "bootstrap_users")
    assert events == expected
    assert set(lifecycle) == receipt.REQUIRED_LIFECYCLE_STAGES
    assert all(observation["state"] == "passed" for observation in lifecycle.values())


@pytest.mark.skipif(os.name != "posix", reason="POSIX owned-group cancellation")
def test_outer_cancellation_preserves_failure_before_slow_cleanup(
    tmp_path: Path,
) -> None:
    """The child retains failure before the native parent closes its cleanup window."""
    root = tmp_path / "attempt"
    ready = root / "work" / "ready"
    script = f"""
import time
from pathlib import Path
from types import SimpleNamespace
from tools.ci.delivery.acceptance import effect
root = Path({str(root)!r})
effect.ROOT, effect.WORK, effect.EVIDENCE = root, root / "work", root / "smoke.json"
effect.current_tracked_head = lambda _: "a" * 40
effect.selected_wheel = lambda *args, **kwargs: SimpleNamespace(sha256="b" * 64)
effect.require_artifact_current = lambda *args, **kwargs: None
native_cleanup = effect.remove_generated_tree
def observe(*args, **kwargs):
    (effect.WORK / "ready").touch()
    time.sleep(60)
def cleanup(path):
    if (path / "ready").exists():
        time.sleep(2)
    native_cleanup(path)
effect.observe_package, effect.remove_generated_tree = observe, cleanup
effect.run(SimpleNamespace(log=lambda _: None))
"""
    with (
        ThreadPoolExecutor(max_workers=1) as pool,
        command_scope(timeout_seconds=20) as scope,
    ):
        child = cast(
            "Future[subprocess.CompletedProcess[str]]",
            pool.submit(
                copy_context().run,
                run_command,
                Path(__file__).resolve().parents[5],
                (sys.executable, "-B", "-c", script),
            ),
        )
        deadline = monotonic() + 20
        while not ready.is_file() and not child.done() and monotonic() < deadline:
            sleep(0.01)
        assert ready.is_file(), child.result() if child.done() else "child readiness timed out"
        scope.cancel()
        assert child.result(timeout=5).returncode != 0
    report = json.loads((root / "smoke.terminal.json").read_text())
    assert report["verdict"] == "block"
    assert report["error_type"] == "KeyboardInterrupt"
    assert report["owned_work_absent"] is False
    assert report["acceptance_written"] is False
    assert not (root / "smoke.json").exists()


@pytest.mark.parametrize("failed_write", [1, 2])
def test_terminal_refresh_preserves_complete_failure(monkeypatch, tmp_path, failed_write):
    work, output = tmp_path / "work", tmp_path / "smoke.json"
    terminal, events, writes = output.with_suffix(".terminal.json"), [], []
    write, cleanup, cancel = (
        Path.write_text,
        effect.remove_generated_tree,
        CommandScope.cancel,
    )
    for name, value in {
        "ROOT": tmp_path,
        "WORK": work,
        "current_tracked_head": lambda _: "a" * 40,
        "require_artifact_current": lambda *_args, **_kwargs: None,
    }.items():
        monkeypatch.setattr(effect, name, value)

    def fail(*_args, **_kwargs):
        (work / "partial-supply").mkdir()
        raise RuntimeError

    def interrupt(path, *args, **kwargs):
        if path != terminal.with_suffix(".tmp"):
            return write(path, *args, **kwargs)
        writes.append(path)
        if len(writes) == failed_write:
            write(path, "{", encoding="utf-8")
            message = "interrupted terminal refresh"
            raise OSError(message)
        return write(path, *args, **kwargs)

    def cancel_owned(scope):
        events.append("cancel")
        cancel(scope)

    def remove(path):
        events.append("cleanup")
        cleanup(path)

    monkeypatch.setattr(effect, "observe_package", fail)
    monkeypatch.setattr(Path, "write_text", interrupt)
    monkeypatch.setattr(CommandScope, "cancel", cancel_owned)
    monkeypatch.setattr(effect, "remove_generated_tree", remove)
    with pytest.raises(OSError, match="interrupted terminal refresh"):
        effect.run(
            cast("nox.Session", SimpleNamespace(log=lambda _: None)),
            artifact=cast("PackageArtifact", SimpleNamespace(sha256="b" * 64)),
            evidence=output,
        )
    assert events.index("cancel") < events.index("cleanup")
    assert not output.exists()
    assert not work.exists()
    assert not terminal.with_suffix(".tmp").exists()
    payload = json.loads(terminal.read_text())
    assert len(writes) == 2
    assert payload["error_type"] == ("RuntimeError" if failed_write == 2 else "OSError")
    assert payload["owned_work_absent"] is (failed_write == 1)


def test_acceptance_observation_retains_incomplete_nested_stage(tmp_path: Path) -> None:
    events = tmp_path / "attempt.events.jsonl"

    def interrupt():
        with (
            invocation.observe_stage("lifecycle"),
            invocation.observe_stage("hook_activation", kind="command"),
        ):
            partial = [json.loads(line) for line in events.read_text().splitlines()]
            assert partial[-1]["state"] == "running"
            assert partial[-1]["parent_span"] == partial[-2]["span"]
            raise KeyboardInterrupt

    with (
        invocation.acceptance_observation(events, head="a" * 40, wheel_sha256="b" * 64),
        pytest.raises(KeyboardInterrupt),
    ):
        interrupt()
    records = [json.loads(line) for line in events.read_text().splitlines()]
    assert records[0]["head"] == "a" * 40
    assert records[0]["wheel_sha256"] == "b" * 64
    assert [record["state"] for record in records[1:]] == [
        "running",
        "running",
        "failed",
        "failed",
    ]
    assert all(record["duration_seconds"] >= 0 for record in records[-2:])
    assert all(record["error_type"] == "KeyboardInterrupt" for record in records[-2:])
    original = events.read_bytes()
    with invocation.observe_stage("unobserved"):
        pass
    assert events.read_bytes() == original


def test_failed_stage_observation_cannot_skip_owned_cleanup(monkeypatch, tmp_path):
    work, output = tmp_path / "work", tmp_path / "smoke.json"
    events = output.with_suffix(".events.jsonl")
    original, refusing = Path.open, []
    for name, value in {
        "ROOT": tmp_path,
        "WORK": work,
        "current_tracked_head": lambda _: "a" * 40,
        "require_artifact_current": lambda *_args, **_kwargs: None,
    }.items():
        monkeypatch.setattr(effect, name, value)

    def fail(*_args, **_kwargs):
        (work / "partial-supply").mkdir()
        refusing.append(True)
        raise RuntimeError

    def open_observation(path, mode="r", *args, **kwargs):
        if path == events and mode == "a" and refusing:
            message = "stage observation refused"
            raise OSError(message)
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(effect, "observe_package", fail)
    monkeypatch.setattr(Path, "open", open_observation)
    with pytest.raises(OSError, match="stage observation refused"):
        effect.run(
            cast("nox.Session", SimpleNamespace(log=lambda _: None)),
            artifact=cast("PackageArtifact", SimpleNamespace(sha256="b" * 64)),
            evidence=output,
        )
    report = json.loads(output.with_suffix(".terminal.json").read_text())
    assert report["owned_work_absent"] is True
    assert "RuntimeError" in report["error_types"]
    assert not work.exists()
    assert not output.exists()


@pytest.mark.parametrize(
    ("predecessor_state", "expected"),
    [
        ("missing", "hook_runtime_current_target_invalid"),
        ("corrupt", "hook_runtime_payload_mismatch"),
        ("same-build", "package_upgrade_predecessor_not_distinct"),
    ],
)
def test_predecessor_preflight_preserves_existing_work_and_evidence(
    monkeypatch, tmp_path, predecessor_state, expected
):
    """A rejected supply cannot destroy the last completed attempt or its recovery."""
    build = runtime_build("a" * 40, "a" * 40)
    previous = fixture_runtime_generation(tmp_path / "prior", "prior")
    if predecessor_state == "missing":
        previous = tmp_path / ("0" * 64)
    elif predecessor_state == "corrupt":
        (previous / "payload").write_bytes(b"changed")
    work, output = tmp_path / "work", tmp_path / "smoke.json"
    work.mkdir()
    original = work / "recovery.txt"
    original.write_bytes(b"required recovery")
    retained = (
        original,
        output,
        output.with_suffix(".terminal.json"),
        output.with_suffix(".events.jsonl"),
    )
    for path in retained[1:]:
        path.write_bytes(b"previous attempt")
    before = {path: path.read_bytes() for path in retained}
    for name, value in {
        "ROOT": tmp_path,
        "WORK": work,
        "current_tracked_head": lambda _: "a" * 40,
        "require_artifact_current": lambda *_args, **_kwargs: None,
    }.items():
        monkeypatch.setattr(effect, name, value)
    artifact = cast("PackageArtifact", SimpleNamespace(build=build, sha256="b" * 64))
    with pytest.raises(ValueError, match=expected):
        effect.run(
            cast("nox.Session", object()), artifact=artifact, evidence=output, predecessor=previous
        )
    assert {path: path.read_bytes() for path in retained} == before
