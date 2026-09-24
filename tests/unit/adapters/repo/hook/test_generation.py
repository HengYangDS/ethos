"""Native launcher generation preserves exact identity and compensates failed writes."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.runtime.retirement as retirement
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_launcher
from tests.support.runtime_scenarios import fixture_runtime_generation
from tests.support.runtime_scenarios import materialized_activation_case


@pytest.mark.parametrize("failure", ["io", "residue", "retained"])
def test_hook_install_reports_deferred_generation_cleanup_after_successful_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Installation succeeds while exposing exact cleanup failure and effects."""
    repo, runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    stale, retained = sorted(
        fixture_runtime_generation(runtime.parent, letter * 64) for letter in "bc"
    )
    monkeypatch.setattr(retirement, "process_commands", lambda _root: retained.as_posix())
    remove = retirement.remove_generated_tree

    def remove_tree(path: Path) -> None:
        assert path == stale
        if failure == "io":
            message = "cleanup failed"
            raise OSError(message)
        if failure == "retained":
            remove(path)
            remove(retained)

    monkeypatch.setattr(retirement, "remove_generated_tree", remove_tree)
    installed = install_hook_launchers(repo)
    cleanup = installed["generation_cleanup"]
    assert (common / "ethos/runtime/CURRENT").read_text(encoding="ascii") == (
        f"{runtime.parent.name}\n"
    )
    assert installed["state_transition"]["after"] == "current"
    assert installed["current"] is True
    assert installed["required_gaps"] == ["hook_runtime_cleanup_deferred"]
    assert installed["next_action"] == "ethos hook install --json"
    assert cleanup["state"] == "deferred"
    assert cleanup["removed"] == ([stale.as_posix()] if failure == "retained" else [])
    assert cleanup["error"] == (
        "cleanup failed"
        if failure == "io"
        else "hook_runtime_generation_identity_stale"
        if failure == "retained"
        else "hook_runtime_generation_cleanup_failed"
    )
    assert cleanup["deferred"] == [
        retained.as_posix() if failure == "retained" else stale.as_posix()
    ]
    assert stale.exists() is (failure != "retained")


def test_generation_cleanup_reobserves_a_consumer_after_activation_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The post-activation read cannot reuse a pre-activation process snapshot."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    needed = fixture_runtime_generation(common / "ethos/runtime" / "selected", "b" * 64)
    sentinel = needed / "payload"
    original = sentinel.read_bytes()
    active = False
    native = retirement.process_listing_command()
    run = retirement.run_command

    def observe(root, command, **kwargs):
        if command == native:
            return subprocess.CompletedProcess(command, 0, needed.as_posix() if active else "", "")
        return run(root, command, **kwargs)

    binding = hook_activation.hook_runtime_binding

    def observe_activated(*args, **kwargs):
        nonlocal active
        result = binding(*args, **kwargs)
        active = True
        return result

    monkeypatch.setattr(retirement, "run_command", observe)
    monkeypatch.setattr(hook_activation, "hook_runtime_binding", observe_activated)

    result = install_hook_launchers(repo)

    assert sentinel.is_file(), "cleanup reused the pre-activation process snapshot"
    assert sentinel.read_bytes() == original
    assert needed.as_posix() in result["generation_cleanup"]["retained"]
    assert needed.as_posix() not in result["generation_cleanup"]["removed"]


def test_hook_generation_failure_never_mutates_an_existing_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "ethos" / "hooks"
    old = root / ("a" * 64)
    old.mkdir(parents=True)
    (old / "legacy").write_text("retained\n", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in old.iterdir()}
    write_text = Path.write_text

    def fail_pre_push(path: Path, data: str, **kwargs: str | None) -> int:
        if path.name == "pre-push" and path.parent.name.startswith(".generation-"):
            message = "staging failed"
            raise OSError(message)
        return write_text(path, data, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_pre_push)

    with pytest.raises(OSError, match="staging failed"):
        hook_activation.materialize_hook_launchers(root)

    assert {path.name: path.read_bytes() for path in old.iterdir()} == before
    assert {path.name for path in root.iterdir()} == {old.name}


def test_hook_generation_repairs_drift_without_changing_identity(tmp_path: Path) -> None:
    root = tmp_path / "ethos" / "hooks"
    generation = hook_activation.materialize_hook_launchers(root)
    inode = generation.stat().st_ino
    repeated = hook_activation.materialize_hook_launchers(root)

    assert repeated == generation
    assert repeated.stat().st_ino == inode
    assert generation.parent == root
    assert len(generation.name) == 64
    assert {path.name for path in generation.iterdir()} == set(HOOK_NAMES)
    (generation / "pre-push").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")

    repaired = hook_activation.materialize_hook_launchers(root)

    assert repaired == generation
    assert (repaired / "pre-push").read_text(encoding="utf-8") == hook_launcher("pre-push")
    assert all(
        (repaired / name).read_text(encoding="utf-8") == hook_launcher(name) for name in HOOK_NAMES
    )


def test_hook_generation_post_replace_failure_restores_the_existing_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "ethos" / "hooks"
    generation = hook_activation.materialize_hook_launchers(root)
    (generation / "pre-push").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in generation.iterdir()}
    read_bytes = Path.read_bytes
    target_reads = 0

    def fail_after_replace(path: Path) -> bytes:
        nonlocal target_reads
        if path == generation / "pre-push":
            target_reads += 1
            if target_reads == 2:
                message = "post-replace validation failed"
                raise OSError(message)
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_after_replace)

    with pytest.raises(ValueError, match="hook_launcher_projection_invalid"):
        hook_activation.materialize_hook_launchers(root)

    assert {path.name: path.read_bytes() for path in generation.iterdir()} == before
    assert {path.name for path in root.iterdir()} == {generation.name}


def test_hook_generation_rejects_an_existing_symlink_target(tmp_path: Path) -> None:
    root = tmp_path / "ethos" / "hooks"
    generation = hook_activation.materialize_hook_launchers(root)
    real = generation.with_name("real")
    generation.rename(real)
    generation.symlink_to(real, target_is_directory=True)

    with pytest.raises(ValueError, match="hook_launcher_projection_invalid"):
        hook_activation.materialize_hook_launchers(root)
