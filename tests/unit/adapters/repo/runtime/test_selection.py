"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import shlex
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.runtime.selection as runtime_selection
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import load_runtime_manifest_bytes
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.manifest import runtime_manifest_bytes
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import restore_runtime_selection
from ethos.adapters.repo.runtime.selection import runtime_command
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build


def test_windows_standalone_runtime_preserves_native_python_layout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    interpreter_home = tmp_path / "python"
    monkeypatch.setattr(runtime_selection, "os", SimpleNamespace(name="nt"))

    assert runtime_selection.runtime_python(interpreter_home) == interpreter_home / "python.exe"


def test_activation_authenticates_the_package_under_lock_and_renders_exact_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    lock_type = runtime_selection.FileLock
    validate = runtime_selection.require_selected_runtime
    locks = []

    def selection_lock(path):
        lock = lock_type(path)
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


def test_release_runtime_identity_rejects_a_second_closure_for_the_same_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = runtime_build("a" * 40, "b" * 40, release=True)
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch, package_identity=identity)
    common = Path(git_common_dir(repo))
    first = venv.parent
    assert git_process(repo, "update-ref", "-d", ATTESTATION_SET_REF).returncode == 0
    with pytest.raises(ValueError, match="accepted_release_identity_unattested"):
        activate_runtime(common, first)
    assert not (common / "ethos/runtime/CURRENT").exists()
    monkeypatch.setattr(runtime_selection, "require_release_identity_attested", lambda *_a: None)
    (first.parent / ("f" * 64)).mkdir()
    activate_runtime(common, first)
    second_staging = tmp_path / "second-runtime"
    shutil.copytree(first, second_staging)
    second_staging.chmod(0o755)
    package = second_staging / "python/lib/python3.14/site-packages/ethos/module.py"
    package.chmod(0o644)
    package.write_text("different accepted closure\n", encoding="utf-8")
    manifest = load_runtime_manifest_bytes((first / "manifest.json").read_bytes())
    closure = {
        "wheel_sha256": manifest.wheel_sha256,
        "build": identity,
        "environment": manifest.environment,
        "runtime_files": runtime_file_inventory(second_staging),
    }
    digest = runtime_digest(**closure)
    second = common / "ethos/runtime" / digest
    shutil.move(second_staging, second)
    manifest = second / "manifest.json"
    manifest.chmod(0o644)
    manifest.write_bytes(runtime_manifest_bytes(digest=digest, **closure))

    with pytest.raises(ValueError, match="release_runtime_identity_conflict"):
        activate_runtime(common, second)

    assert current_runtime(common).root == first
