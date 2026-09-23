"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tarfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.selection as runtime_selection
import ethos.cli as cli
import tools.ci.delivery.distribution as distribution
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import load_runtime_manifest_bytes
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.manifest import runtime_manifest_bytes
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import restore_runtime_selection
from ethos.adapters.repo.runtime.selection import runtime_command
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build


def test_windows_standalone_runtime_preserves_native_python_layout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    interpreter_home = tmp_path / "python"
    monkeypatch.setattr(runtime_filesystem, "os", SimpleNamespace(name="nt"))

    assert runtime_filesystem.runtime_python(interpreter_home) == interpreter_home / "python.exe"


@pytest.mark.parametrize("external", [False, True])
def test_activation_authenticates_the_package_under_lock_and_renders_exact_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, external: bool
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    if external:
        destination = tmp_path / "host supply" / venv.parent.name
        destination.parent.mkdir()
        shutil.copytree(venv.parent, destination)
        venv = destination / "python"
    common = Path(git_common_dir(repo))
    lock_type = runtime_selection.FileLock
    validate = runtime_selection.require_selected_runtime
    locks = []

    def selection_lock(path, **kwargs):
        lock = lock_type(path, **kwargs)
        locks.append(lock)
        return lock

    def authenticate(*args, **kwargs):
        assert locks[-1].is_locked
        return validate(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(runtime_selection, "FileLock", selection_lock)
        patch.setattr(runtime_selection, "require_selected_runtime", authenticate)
        selected = activate_runtime(common, venv.parent, expected_current=None)
    assert locks
    assert not locks[-1].is_locked
    assert shlex.split(runtime_command(repo, "status", "--json")) == [
        selected.python.as_posix(),
        *shlex.split("-B -I -m ethos.cli status --json"),
    ]
    selector = common / "ethos/runtime/CURRENT"
    original = selector.read_bytes()
    with pytest.raises(ValueError, match="hook_runtime_current_stale"):
        activate_runtime(common, venv.parent, expected_current=None)
    assert selector.read_bytes() == original
    selected = activate_runtime(common, venv.parent)
    assert selected.root == venv.parent
    assert selected.python.is_file()
    assert current_runtime(common) == selected
    if external:
        second = tmp_path / "second-common"
        assert activate_runtime(second, selected.root) == selected
        restore_runtime_selection(common, None, expected_current=original)
        assert current_runtime(second) == selected
        assert activate_runtime(common, selected.root) == selected
    alias = selected.root.parent / "alias"
    alias.symlink_to(selected.root, target_is_directory=True)
    for candidate in (alias, tmp_path / selected.digest):
        with pytest.raises(ValueError, match="hook_runtime_current_target_invalid"):
            activate_runtime(common, candidate)
        assert selector.read_bytes() == original
    package = selected.root / "python/lib/python3.14/site-packages/ethos/module.py"
    package.chmod(0o644)
    package.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        current_runtime(common)
    assert selector.read_bytes() == original


@pytest.mark.parametrize("obstruction", ["none", "unreadable"])
def test_runtime_selection_compensation_is_exact_cas(tmp_path, obstruction):
    common = tmp_path / "common"
    selector = common / "ethos/runtime/CURRENT"
    selector.parent.mkdir(parents=True)
    previous = f"{'a' * 64}\n".encode()
    operation_selection = f"{'b' * 64}\n".encode()
    concurrent_selection = f"{'c' * 64}\n".encode()
    selector.write_bytes(concurrent_selection)

    with pytest.raises(ValueError, match="hook_runtime_current_stale"):
        restore_runtime_selection(common, previous, expected_current=operation_selection)

    assert selector.read_bytes() == concurrent_selection
    restore_runtime_selection(common, previous, expected_current=concurrent_selection)
    assert selector.read_bytes() == previous
    transaction = runtime_selection.runtime_selection_transaction(
        common, expected_current=operation_selection
    )
    with pytest.raises(ValueError, match="hook_runtime_current_stale"), transaction:
        pass
    with runtime_selection.runtime_selection_transaction(common, expected_current=previous):
        assert selector.read_bytes() == previous
    restore_runtime_selection(common, None, expected_current=previous)
    assert not selector.exists()
    if obstruction == "unreadable":
        selector.mkdir()
        with pytest.raises(ValueError, match="hook_runtime_current_invalid"):
            restore_runtime_selection(common, previous, expected_current=None)
        assert selector.is_dir()
        return
    restore_runtime_selection(common, None, expected_current=None)


@pytest.mark.parametrize("relative", ["ethos", "ethos/runtime", "ethos/runtime/CURRENT"])
def test_current_runtime_rejects_symlinked_selection_components(tmp_path, relative):
    common = tmp_path / "common"
    external = tmp_path / "external"
    external.mkdir()
    marker = external / "keep"
    marker.write_bytes(b"a" * 64 + b"\n")
    link = common / relative
    link.parent.mkdir(parents=True)
    link.symlink_to(marker if link.name == "CURRENT" else external)
    reason = (
        "hook_runtime_current_invalid"
        if link.name == "CURRENT"
        else "hook_runtime_current_target_invalid"
    )
    with pytest.raises(ValueError, match=reason):
        current_runtime(common)
    if link.name == "CURRENT":
        for expected in ({}, {"expected_current": b"a" * 64 + b"\n"}):
            with pytest.raises(ValueError, match=reason):
                restore_runtime_selection(common, None, **expected)
    assert marker.read_bytes() == b"a" * 64 + b"\n"


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (None, "hook_runtime_current_missing"),
        (b"bad\n", "hook_runtime_current_invalid"),
        (b"\xff", "hook_runtime_current_invalid"),
        (b"a" * 64, "hook_runtime_current_invalid"),
        (b"a" * 64 + b"\n", "hook_runtime_current_target_invalid"),
        (b"a" * 64 + b"\nrelative\n", "hook_runtime_current_target_invalid"),
        (b"a" * 64 + b"\n/invalid\n", "hook_runtime_current_target_invalid"),
        (b"a" * 64 + b"\n/x/" + b"a" * 64 + b"\nextra\n", "hook_runtime_current_invalid"),
    ],
)
def test_current_runtime_rejects_missing_or_noncanonical_selection(tmp_path, raw, reason):
    selector = tmp_path / "ethos/runtime/CURRENT"
    selector.parent.mkdir(parents=True)
    if raw is not None:
        selector.write_bytes(raw)
    with pytest.raises(ValueError, match=reason):
        current_runtime(tmp_path)
    assert (selector.read_bytes() if selector.exists() else None) == raw


@pytest.mark.parametrize("changed_source", ["closure", "source", "wheel", "target", "rollback"])
@pytest.mark.parametrize("external", [False, True])
def test_release_runtime_identity_rejects_a_second_closure_for_the_same_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    changed_source: str,
    external: bool,
) -> None:
    identity = runtime_build("a" * 40, "b" * 40, release=True)
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch, package_identity=identity)
    common = Path(git_common_dir(repo))
    first = venv.parent
    if external:
        destination = tmp_path / "installed" / first.name
        destination.parent.mkdir()
        first.chmod(0o755)
        first.rename(destination)
        destination.chmod(0o555)
        first = destination
    assert git_process(repo, "update-ref", "-d", ATTESTATION_SET_REF).returncode == 0
    (first.parent / ("f" * 64)).mkdir()
    activate_runtime(common, first)
    assert read_attestation_set(repo)[1] == ()
    second_staging = tmp_path / "second-runtime"
    shutil.copytree(first, second_staging)
    second_staging.chmod(0o755)
    package = second_staging / "python/lib/python3.14/site-packages/ethos/module.py"
    package.chmod(0o644)
    package.write_text("different accepted closure\n", encoding="utf-8")
    manifest = load_runtime_manifest_bytes((first / "manifest.json").read_bytes())
    if changed_source == "source":
        identity = identity._replace(source_commit="e" * 40)
    if changed_source == "rollback":
        identity = identity._replace(
            product_version="0.2.0-alpha.1", distribution_version="0.2.0a1"
        )
    environment = manifest.environment
    if changed_source in {"source", "wheel", "target"}:
        environment = environment._replace(python_abi="cpython-313")
    closure = {
        "wheel_sha256": "d" * 64 if changed_source == "wheel" else manifest.wheel_sha256,
        "build": identity,
        "environment": environment,
        "runtime_files": runtime_file_inventory(second_staging),
    }
    digest = runtime_digest(**closure)
    second = common / "ethos/runtime" / digest
    shutil.move(second_staging, second)
    manifest = second / "manifest.json"
    manifest.chmod(0o644)
    manifest.write_bytes(runtime_manifest_bytes(digest=digest, **closure))

    if changed_source in {"target", "rollback"}:
        assert activate_runtime(common, second).root == second
        assert activate_runtime(common, first).root == first
    else:
        with pytest.raises(ValueError, match="release_runtime_identity_conflict"):
            activate_runtime(common, second)
    assert current_runtime(common).root == first
    assert read_attestation_set(repo)[1] == ()


@pytest.mark.parametrize("mode", ["selected", "self", "missing", "broken", "tampered", "install"])
def test_host_console_obeys_repository_selection(tmp_path, monkeypatch, mode):
    """A host upgrade cannot replace selected bytes or bypass invalid selection."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    if mode != "missing":
        activate_runtime(common, python.parent)
    if mode == "broken":
        (common / "ethos/runtime/CURRENT").write_text("invalid\\n")
    if mode == "tampered":
        target = python.parent / "manifest.json"
        target.chmod(0o644)
        target.write_text("{}")
    calls = []
    monkeypatch.setattr(cli, "main", lambda: calls.append("local"))
    monkeypatch.setattr(
        cli.sys, "executable", str(python / "bin/python") if mode == "self" else "/host/python"
    )
    args = ["hook", "install"] if mode == "install" else ["--version"]
    monkeypatch.setattr(cli.sys, "argv", ["ethos", *args, "--root", str(repo)])
    monkeypatch.setattr(os, "execv", lambda path, argv: calls.append((path, argv)))
    blocked = mode in {"broken", "tampered"}
    with pytest.raises(SystemExit, match="1") if blocked else nullcontext():
        cli.console_main()
    expected = [] if blocked else ["local"]
    if mode == "selected":
        executable = str(runtime_filesystem.runtime_python(python))
        expected = [
            (executable, [executable, "-B", "-I", "-m", "ethos.cli", *args, "--root", str(repo)])
        ]
    assert calls == expected


@pytest.mark.parametrize("producer", ["archive", "wheel", "diskutil", "hdiutil", "failed"])
def test_distribution_retains_exact_input_and_previous_output(tmp_path, monkeypatch, producer):
    """One source-bound workload covers archive and native-envelope success and refusal."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    wheel = Path(git_common_dir(repo)) / "ethos/packages" / selected.wheel_sha256 / "ethos-test.whl"
    native = producer not in {"archive", "wheel"}
    destination = tmp_path / ("ethos.dmg" if native else "ethos.tar.gz")
    destination.write_bytes(b"previous")
    calls = []

    def invoke(root, command, **options):
        calls.append(command)
        assert (
            require_selected_runtime(root / "ethos/runtime" / selected.digest).digest
            == selected.digest
        )
        assert 0 < options["timeout"] <= 180
        if command[-1] == "--help":
            return subprocess.CompletedProcess(command, int(producer == "hdiutil"))
        assert command[0] == f"/usr/{'bin/hdiutil' if producer == 'hdiutil' else 'sbin/diskutil'}"
        assert command[-2] == str(root)
        assert options["check"]
        if producer == "failed":
            raise subprocess.CalledProcessError(1, command, stderr="creation failed")
        Path(command[-1]).write_bytes(b"native image")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(distribution, "run_command", invoke)
    with pytest.raises(ValueError, match="distribution_release_build_required"):
        distribution.package_runtime(
            selected.root, wheel, destination, download_url="https://example.invalid/ethos.tar.gz"
        )
    assert destination.read_bytes() == b"previous"
    assert not (tmp_path / "homebrew").exists()
    failure = {
        "wheel": (ValueError, "distribution_wheel_mismatch"),
        "failed": (subprocess.CalledProcessError, "exit status 1"),
    }.get(producer)
    if native and selected.platform != "darwin":
        failure = (ValueError, "distribution_disk_image_requires_macos")
    if producer == "wheel":
        wheel.write_bytes(b"changed")
    with pytest.raises(failure[0], match=failure[1]) if failure else nullcontext():
        result = distribution.package_runtime(selected.root, wheel, destination)
    assert not list(tmp_path.glob(".ethos-distribution-*"))
    assert require_selected_runtime(selected.root) == selected
    assert len(calls) == (2 if native and selected.platform == "darwin" else 0)
    if failure:
        assert destination.read_bytes() == b"previous"
        return
    if selected.platform == "windows":
        assert result["homebrew_cask"] is None
        assert not (tmp_path / "homebrew").exists()
    else:
        cask = Path(str(result["homebrew_cask"])).read_text()
        assert all(token in cask for token in ('"/usr/bin/codesign"', '"=notarized"'))
        assert "spctl" not in cask
    if native:
        assert destination.read_bytes() == b"native image"
        return
    assert distribution.package_runtime(selected.root, wheel, destination) == result
    with tarfile.open(destination) as archive:
        archive.extractall(tmp_path / "relocated", filter="tar")
    assert (
        require_selected_runtime(tmp_path / "relocated/ethos/runtime" / selected.digest).digest
        == selected.digest
    )
    assert (
        tmp_path / "relocated/ethos/packages" / selected.wheel_sha256 / wheel.name
    ).read_bytes() == wheel.read_bytes()
