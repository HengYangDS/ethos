"""The delivery pipeline owns one locked build and one package acceptance transaction."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import call

import pytest

from tools.ci import dependency_audit
from tools.ci import sessions
from tools.ci.delivery import pipeline
from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("release_head", ["", "a" * 40])
@pytest.mark.parametrize("predecessor", [False, True])
def test_install_smoke_invokes_one_acceptance_transaction(
    monkeypatch, tmp_path, release_head, predecessor
):
    previous = tmp_path / "predecessor"
    supplied = previous if predecessor else None
    session = SimpleNamespace(
        posargs=(("--release", "--expect-head", release_head) if release_head else ())
        + (("--predecessor-runtime", str(previous)) if predecessor else ())
    )
    artifact = object()
    accept = Mock()
    audit = Mock()
    prepare = Mock(return_value=artifact)
    monkeypatch.setattr(dependency_audit, "run", audit)
    monkeypatch.setattr(pipeline.acceptance_effect, "run", accept)
    monkeypatch.setattr(pipeline, "prepare_release_candidate", prepare)
    monkeypatch.setattr(sessions, "RUNTIME", ProjectRuntime.discover(tmp_path))
    monkeypatch.setattr(ProjectRuntime, "node_package_supply", lambda _: tmp_path / "node_modules")
    sessions.install_smoke(session)
    if release_head:
        audit.assert_called_once_with(session, root=tmp_path, scope="production-release")
        prepare.assert_called_once_with(tmp_path, release_head, tag="")
        accept.assert_called_once_with(
            session,
            artifact=artifact,
            evidence=tmp_path / "build/evidence/local-install/release-smoke.json",
            predecessor=supplied,
        )
    else:
        audit.assert_not_called()
        prepare.assert_not_called()
        accept.assert_called_once_with(session, predecessor=supplied)


def test_wheel_build_reuses_the_locked_project_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = Mock()

    monkeypatch.setattr(pipeline, "publish_built_wheel", lambda *_args: tmp_path / "ethos.whl")
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
    calls, session = Mock(), Mock()
    for name in ("build", "prove_install"):
        monkeypatch.setattr(pipeline.DeliveryPipeline, name, getattr(calls, name))
    calls.attach_mock(session.run, "run")
    delivery = pipeline.DeliveryPipeline(
        ProjectRuntime(ROOT, Path("/locked/python"), Path("/locked")),
        ROOT / "node_modules",
    )
    preflight = call.run(
        "/locked/python",
        "-m",
        "pytest",
        "-q",
        "-c",
        str(ROOT / ".config/checks/pytest/pytest.toml"),
        "tests/architecture/test_portable_toolchain.py",
        "tests/unit/adapters/repo/trust_anchor/test_filesystem.py"
        "::test_windows_native_acl_protection_rejects_foreign_writer",
    )
    delivery.prove_host(session)
    assert calls.mock_calls == [
        preflight,
        call.build(session),
        call.prove_install(session),
    ]
    calls.reset_mock()
    session.run.side_effect = RuntimeError("native preflight failed")
    with pytest.raises(RuntimeError, match="native preflight failed"):
        delivery.prove_host(session)
    assert calls.mock_calls == [preflight]
