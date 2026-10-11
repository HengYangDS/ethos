"""The existing build is the single package supply for tests and installation."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast
from unittest.mock import Mock
from unittest.mock import call

import pytest

import tools.ci.python_test_gate as test_gate
from ethos.adapters.repo.runtime.transition import PackageArtifact
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import build_identity_bytes
from ethos.repository.release.resources import BUILD_IDENTITY_RESOURCE
from ethos.repository.release.resources import WHEEL_RESOURCE_ROOT
from tools.ci.delivery.artifact import require_artifact_current
from tools.ci.delivery.artifact import selected_wheel

if TYPE_CHECKING:
    import nox


def _wheel(tmp_path: Path, *, tree: str = "b" * 40) -> PackageArtifact:
    wheel = tmp_path / "build/artifacts/python/ethos-selected.whl"
    wheel.parent.mkdir(parents=True, exist_ok=True)
    build = build_identity(product="0.2.0-alpha.5", source_commit="a" * 40, source_tree=tree)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            (WHEEL_RESOURCE_ROOT / BUILD_IDENTITY_RESOURCE).as_posix(),
            build_identity_bytes(build),
        )
    return PackageArtifact(wheel, hashlib.sha256(wheel.read_bytes()).hexdigest(), build)


def test_selected_build_output_is_shared_without_materialization(tmp_path, monkeypatch) -> None:
    artifact = _wheel(tmp_path)
    observed = Mock(return_value=artifact.build)
    monkeypatch.setattr("tools.ci.delivery.artifact.source_build_identity", observed)
    before = artifact.path.stat()
    assert selected_wheel(tmp_path, head=artifact.build.source_commit) == artifact
    observed.assert_called_once_with(tmp_path)
    require_artifact_current(artifact, head=artifact.build.source_commit, repo=tmp_path)
    assert observed.call_args_list == [call(tmp_path), call(tmp_path)]
    after = artifact.path.stat()
    assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)
    assert tuple(artifact.path.parent.iterdir()) == (artifact.path,)


@pytest.mark.parametrize("state", ["missing", "multiple", "directory", "symlink"])
def test_selected_output_requires_one_regular_file(tmp_path, state) -> None:
    artifact = _wheel(tmp_path)
    if state == "multiple":
        artifact.path.with_name("ethos-other.whl").touch()
    else:
        artifact.path.unlink()
        if state == "directory":
            artifact.path.mkdir()
        elif state == "symlink":
            artifact.path.symlink_to("missing")
    with pytest.raises(ValueError, match="package_build_output_invalid"):
        selected_wheel(tmp_path, head=artifact.build.source_commit)


@pytest.mark.parametrize("field", ["head", "tree"])
def test_build_identity_rejects_stale_source_and_overlay(tmp_path, monkeypatch, field) -> None:
    artifact = _wheel(tmp_path)
    expected = build_identity(
        product=artifact.build.product_version,
        source_commit="c" * 40 if field == "head" else artifact.build.source_commit,
        source_tree="c" * 40 if field == "tree" else artifact.build.source_tree,
    )
    monkeypatch.setattr("tools.ci.delivery.artifact.source_build_identity", lambda _: expected)
    with pytest.raises(ValueError, match="package_build_source_stale"):
        selected_wheel(tmp_path, head=artifact.build.source_commit)


def test_reobserved_artifact_rejects_changed_bytes(tmp_path) -> None:
    artifact = _wheel(tmp_path)
    with zipfile.ZipFile(artifact.path, "a") as archive:
        archive.writestr("changed.txt", b"new bytes")
    with pytest.raises(ValueError, match="package_acceptance_artifact_changed"):
        require_artifact_current(artifact, head=artifact.build.source_commit, repo=tmp_path)


def _gate(tmp_path: Path, *, shards: int = 1) -> test_gate.PythonTestGate:
    return test_gate.PythonTestGate(
        test_gate.Settings(
            head="a" * 40,
            evidence=tmp_path / "evidence",
            basetemp=tmp_path / "scratch",
            basetemp_owned=True,
            workers=1,
            shards=shards,
            durations=0,
            timeout=None,
            lock_wait=0,
            uv_cache=None,
            node_package_supply=tmp_path / "node_modules",
        )
    )


def test_native_test_command_receives_only_selected_build_supply(tmp_path, monkeypatch) -> None:
    artifact = _wheel(tmp_path)
    gate = _gate(tmp_path)
    monkeypatch.setattr(test_gate, "ROOT", tmp_path)
    monkeypatch.setattr(test_gate, "_head", lambda: gate.s.head)
    monkeypatch.setattr(
        "tools.ci.delivery.artifact.source_build_identity", lambda _: artifact.build
    )
    monkeypatch.setenv("ETHOS_TEST_OBSERVER_WHEEL", str(tmp_path / "ambient.whl"))
    session = SimpleNamespace(run=Mock())
    gate.run_tests(cast("nox.Session", session))
    session.run.assert_called_once()
    assert session.run.call_args.kwargs["env"]["ETHOS_TEST_OBSERVER_WHEEL"] == str(artifact.path)
    assert gate.head_file.read_text().strip() == gate.s.head
    assert not gate.s.basetemp.exists()


def test_missing_test_supply_cannot_launch_or_retain_success(tmp_path, monkeypatch) -> None:
    gate = _gate(tmp_path)
    gate.coverage.mkdir(parents=True)
    gate.head_file.write_text(gate.s.head)
    monkeypatch.setattr(test_gate, "ROOT", tmp_path)
    monkeypatch.setattr(test_gate, "_head", lambda: gate.s.head)
    session = SimpleNamespace(run=Mock())
    with pytest.raises(ValueError, match="package_build_output_invalid"):
        gate.run_tests(cast("nox.Session", session))
    session.run.assert_not_called()
    assert not gate.head_file.exists()
    assert not gate.s.basetemp.exists()


def test_selected_supply_rejects_a_redirected_build_parent(tmp_path, monkeypatch) -> None:
    """An owned-looking final path cannot inherit a foreign parent's bytes."""
    repo = tmp_path / "repo"
    repo.mkdir()
    artifact = _wheel(tmp_path / "foreign")
    (repo / "build").symlink_to(artifact.path.parents[2], target_is_directory=True)
    monkeypatch.setattr(
        "tools.ci.delivery.artifact.source_build_identity", lambda _: artifact.build
    )
    before = artifact.path.read_bytes()
    with pytest.raises(ValueError, match="package_build_output_invalid"):
        selected_wheel(repo, head=artifact.build.source_commit)
    assert artifact.path.read_bytes() == before


def test_source_overlay_drift_after_execution_cannot_record_success(tmp_path, monkeypatch) -> None:
    """Unchanged HEAD and wheel do not excuse a changed executing source overlay."""
    artifact = _wheel(tmp_path)
    current = artifact.build
    gate = _gate(tmp_path)
    monkeypatch.setattr(test_gate, "ROOT", tmp_path)
    monkeypatch.setattr(test_gate, "_head", lambda: gate.s.head)
    monkeypatch.setattr("tools.ci.delivery.artifact.source_build_identity", lambda _: current)

    def run(*_args, **_kwargs) -> None:
        nonlocal current
        current = build_identity(
            product=artifact.build.product_version,
            source_commit=artifact.build.source_commit,
            source_tree="c" * 40,
        )

    with pytest.raises(ValueError, match="package_acceptance_artifact_changed"):
        gate.run_tests(cast("nox.Session", SimpleNamespace(run=run)))
    assert not gate.head_file.exists()
    assert not gate.s.basetemp.exists()


def test_shards_reuse_only_identical_selected_wheel_bytes(tmp_path, monkeypatch) -> None:
    """A same-HEAD rebuild reruns its shards while identical supply reuses once."""
    artifact = _wheel(tmp_path)
    gate = _gate(tmp_path, shards=2)
    monkeypatch.setattr(test_gate, "ROOT", tmp_path)
    monkeypatch.setattr(test_gate, "_head", lambda: gate.s.head)
    monkeypatch.setattr(
        "tools.ci.delivery.artifact.source_build_identity", lambda _: artifact.build
    )
    executed = []

    def run(*args, env, stdout=None) -> None:
        if "--collect-only" in args:
            stdout.write("tests/app.py::test_first\ntests/app.py::test_second\n")
        elif any(item.startswith("--junitxml=") for item in args):
            executed.append(args)
            Path(env["COVERAGE_FILE"]).write_bytes(b"covered")
            output = Path(
                next(item.split("=", 1)[1] for item in args if item.startswith("--alluredir="))
            )
            output.mkdir(parents=True)
            (output / "case-result.json").write_text("{}")

    session = cast("nox.Session", SimpleNamespace(run=run))
    gate.run_tests(session)
    assert len(executed) == 2
    gate.run_tests(session)
    assert len(executed) == 2
    artifact = _wheel(tmp_path, tree="c" * 40)
    gate.run_tests(session)
    assert len(executed) == 4


@pytest.mark.parametrize("release", [False, True])
def test_artifact_reobservation_retains_explicit_distribution_identity(
    tmp_path, monkeypatch, release
) -> None:
    """Source freshness preserves a qualified release, without treating build as promotion."""
    artifact = _wheel(tmp_path)
    source = artifact.build
    identity = build_identity(
        product=source.product_version,
        source_commit=source.source_commit,
        source_tree=source.source_tree,
        release=release,
    )
    with zipfile.ZipFile(artifact.path, "w") as archive:
        archive.writestr(
            (WHEEL_RESOURCE_ROOT / BUILD_IDENTITY_RESOURCE).as_posix(),
            build_identity_bytes(identity),
        )
    selected = PackageArtifact(
        artifact.path, hashlib.sha256(artifact.path.read_bytes()).hexdigest(), identity
    )
    monkeypatch.setattr("tools.ci.delivery.artifact.source_build_identity", lambda _: source)
    require_artifact_current(selected, head=source.source_commit, repo=tmp_path)
