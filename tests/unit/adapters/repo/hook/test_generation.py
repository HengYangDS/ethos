"""Native launcher generation preserves exact identity and compensates failed writes."""

from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_launcher


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
