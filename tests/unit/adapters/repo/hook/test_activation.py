"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.authority import runtime_build_identity
from ethos.repository.release.identity import BuildIdentity
from tests.support.runtime_scenarios import REPOSITORY_ROOT
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import linked_runtime_case
from tests.support.runtime_scenarios import materialize_runtime_case


def test_hook_install_removes_only_unreferenced_generated_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runtime_materialization,
        "materialize_runtime",
        lambda *_args, **_kwargs: venv,
    )
    common = Path(git_common_dir(repo))
    hooks_root = common / "ethos" / "hooks"
    runtime_root = common / "ethos" / "runtime"
    retained_digest = "a" * 64
    removed_digest = "b" * 64
    retained_runtime = runtime_root / retained_digest
    removed_runtime = runtime_root / removed_digest
    retained_runtime.mkdir(parents=True)
    removed_runtime.mkdir()
    active_hooks = hook_activation.materialize_hook_launchers(hooks_root)
    operations = common / "ethos" / "operations"
    operations.mkdir()
    (operations / "consumer.json").write_text(
        json.dumps({"runtime": retained_runtime.as_posix()}),
        encoding="utf-8",
    )

    installed = install_hook_launchers(repo)

    cleanup = installed["generation_cleanup"]
    assert cleanup["removed"] == [removed_runtime.as_posix()]
    assert retained_runtime.as_posix() in cleanup["retained"]
    assert active_hooks.as_posix() in cleanup["retained"]
    assert not removed_runtime.exists()
    assert retained_runtime.is_dir()
    assert active_hooks.is_dir()


def test_hook_install_retires_unreferenced_legacy_hook_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runtime_materialization,
        "materialize_runtime",
        lambda *_args, **_kwargs: venv,
    )
    common = Path(git_common_dir(repo))
    legacy = common / "ethos-hooks"
    digest_legacy = common / ("ethos-hooks-" + "a" * 64)
    unrelated = common / "ethos-hooks-manual"
    for path in (legacy, digest_legacy, unrelated):
        path.mkdir()

    installed = install_hook_launchers(repo)

    removed = installed["generation_cleanup"]["removed"]
    assert legacy.as_posix() in removed
    assert digest_legacy.as_posix() in removed
    assert not legacy.exists()
    assert not digest_legacy.exists()
    assert unrelated.is_dir()


def test_hook_install_converges_every_linked_worktree_on_one_common_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, linked, _venv, generations = linked_runtime_case(tmp_path, monkeypatch)
    root_stale = hook_activation.materialize_hook_launchers(generations)
    linked_stale = hook_activation.materialize_hook_launchers(generations)
    assert git_process(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        git_process(
            repo, "config", "--worktree", "core.hooksPath", root_stale.as_posix()
        ).returncode
        == 0
    )
    assert git_process(repo, "config", "--worktree", "gc.packRefs", "true").returncode == 0
    assert (
        git_process(
            linked,
            "config",
            "--worktree",
            "core.hooksPath",
            linked_stale.as_posix(),
        ).returncode
        == 0
    )
    assert git_process(linked, "config", "--worktree", "gc.packRefs", "true").returncode == 0

    installed = install_hook_launchers(linked)

    expected = installed["hooks_path"]
    assert installed["linked_worktrees"] == [
        {"path": repo.as_posix(), "state": "repaired"},
        {"path": linked.as_posix(), "state": "repaired"},
    ]
    assert (
        git_process(repo, "config", "--local", "--path", "--get", "core.hooksPath").stdout.strip()
        == expected
    )
    assert git_process(repo, "config", "--local", "--get", "gc.packRefs").stdout.strip() == "false"
    for worktree in (repo, linked):
        assert (
            git_process(worktree, "config", "--path", "--get", "core.hooksPath").stdout.strip()
            == expected
        )
        assert git_process(worktree, "config", "--get", "gc.packRefs").stdout.strip() == "false"
        assert (
            git_process(worktree, "config", "--worktree", "--get", "core.hooksPath").returncode == 1
        )
        assert git_process(worktree, "config", "--worktree", "--get", "gc.packRefs").returncode == 1
        assert hook_runtime_binding(worktree)["required_gaps"] == []


def test_hook_install_rolls_back_when_linked_worktree_config_is_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, linked, _venv, hooks_root = linked_runtime_case(tmp_path, monkeypatch)
    stale = hook_activation.materialize_hook_launchers(hooks_root)
    assert (
        git_process(repo, "config", "--local", "core.hooksPath", stale.as_posix()).returncode == 0
    )
    real_values = hook_activation.config_effects.config_values

    def unreadable(root_path: Path, keys: tuple[str, ...], *, scope: str):
        if root_path == linked and scope == "worktree":
            message = "git_config_observation_failed"
            raise ValueError(message)
        return real_values(root_path, keys, scope=scope)

    monkeypatch.setattr(hook_activation.config_effects, "config_values", unreadable)

    with pytest.raises(ValueError, match="git_config_observation_failed"):
        install_hook_launchers(repo)

    assert (
        git_process(repo, "config", "--local", "--path", "--get", "core.hooksPath").stdout.strip()
        == stale.as_posix()
    )
    assert stale.is_dir()


def test_hook_generation_failure_never_mutates_an_existing_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "ethos" / "hooks"
    old = root / ("a" * 64)
    old.mkdir(parents=True)
    (old / "legacy").write_text("retained\n", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in old.iterdir()}
    write_text = Path.write_text

    def fail_pre_push(path: Path, data: str, **kwargs: object) -> int:
        if path.name == "pre-push" and path.parent.name.startswith(".generation-"):
            message = "staging failed"
            raise OSError(message)
        return write_text(path, data, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_pre_push)

    with pytest.raises(OSError, match="staging failed"):
        hook_activation.materialize_hook_launchers(root)

    assert {path.name: path.read_bytes() for path in old.iterdir()} == before
    assert {path.name for path in root.iterdir()} == {old.name}


def test_hook_generation_rejects_a_symlinked_ethos_ancestor(tmp_path: Path) -> None:
    common = tmp_path / "common"
    external = tmp_path / "external"
    common.mkdir()
    external.mkdir()
    (common / "ethos").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="hook_generation_root_invalid"):
        hook_activation.materialize_hook_launchers(common / "ethos" / "hooks")


def test_hook_install_uses_one_source_identity_for_historical_linked_worktrees(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, linked, venv, _generations = linked_runtime_case(tmp_path, monkeypatch)
    accepted_identity = runtime_build_identity(REPOSITORY_ROOT)
    source_selections: list[Path] = []
    materialized_with: list[BuildIdentity] = []
    (linked / ".ethos").mkdir()
    (linked / ".ethos/profile.toml").write_text('profile_id = "ethos"\n', encoding="utf-8")
    (linked / ".ethos/workspace.toml").write_text(
        '[branch_roles]\naccepted_branch = "dev"\n\n[branch_roles.transition]\nunknown = true\n',
        encoding="utf-8",
    )

    def select_source(root: Path):
        source_selections.append(root)
        return accepted_identity, None

    def materialize(
        _root: Path,
        _python: Path,
        *,
        expected_build: BuildIdentity,
        build_source: Path | None = None,
    ) -> Path:
        del build_source
        materialized_with.append(expected_build)
        return venv

    monkeypatch.setattr(hook_activation, "expected_runtime_build", select_source)
    monkeypatch.setattr(runtime_materialization, "materialize_runtime", materialize)

    installed = install_hook_launchers(repo)

    assert source_selections == [repo]
    assert materialized_with == [accepted_identity]
    assert installed["expected_source_commit"] == accepted_identity.source_commit
    assert installed["expected_source_tree"] == accepted_identity.source_tree
    assert installed["required_gaps"] == []


def test_hook_activation_failure_keeps_the_old_generation_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, linked, _venv, root = linked_runtime_case(tmp_path, monkeypatch)
    old_common = hook_activation.materialize_hook_launchers(root)
    old_root = hook_activation.materialize_hook_launchers(root)
    old_linked = hook_activation.materialize_hook_launchers(root)
    assert git_process(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        git_process(repo, "config", "--local", "core.hooksPath", old_common.as_posix()).returncode
        == 0
    )
    assert git_process(repo, "config", "--local", "gc.packRefs", "true").returncode == 0
    assert (
        git_process(repo, "config", "--worktree", "core.hooksPath", old_root.as_posix()).returncode
        == 0
    )
    assert git_process(repo, "config", "--worktree", "gc.packRefs", "true").returncode == 0
    assert (
        git_process(
            linked, "config", "--worktree", "core.hooksPath", old_linked.as_posix()
        ).returncode
        == 0
    )
    assert git_process(linked, "config", "--worktree", "gc.packRefs", "true").returncode == 0
    real_unset = hook_activation.config_effects.unset_worktree_config
    failed = False

    def fail_activation(root_path: Path, keys: tuple[str, ...]) -> None:
        nonlocal failed
        if root_path == linked and not failed:
            failed = True
            message = "activation failed"
            raise ValueError(message)
        real_unset(root_path, keys)

    monkeypatch.setattr(hook_activation.config_effects, "unset_worktree_config", fail_activation)

    with pytest.raises(ValueError, match="activation failed"):
        install_hook_launchers(repo)

    assert (
        git_process(repo, "config", "--local", "--path", "--get", "core.hooksPath").stdout.strip()
        == old_common.as_posix()
    )
    assert git_process(repo, "config", "--local", "--get", "gc.packRefs").stdout.strip() == "true"
    assert (
        git_process(
            repo, "config", "--worktree", "--path", "--get", "core.hooksPath"
        ).stdout.strip()
        == old_root.as_posix()
    )
    assert (
        git_process(repo, "config", "--worktree", "--get", "gc.packRefs").stdout.strip() == "true"
    )
    assert (
        git_process(
            linked, "config", "--worktree", "--path", "--get", "core.hooksPath"
        ).stdout.strip()
        == old_linked.as_posix()
    )
    assert (
        git_process(linked, "config", "--worktree", "--get", "gc.packRefs").stdout.strip() == "true"
    )
    assert {old_common, old_root, old_linked} <= set(root.iterdir())


def test_hook_generation_repairs_drift_without_changing_identity(tmp_path: Path) -> None:
    root = tmp_path / "ethos" / "hooks"
    generation = hook_activation.materialize_hook_launchers(root)
    (generation / "pre-push").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")

    repaired = hook_activation.materialize_hook_launchers(root)

    assert repaired == generation
    assert (repaired / "pre-push").read_text(encoding="utf-8") == hook_launcher("pre-push")


def test_hook_generations_are_content_addressed_and_immutable(tmp_path: Path) -> None:
    root = tmp_path / "ethos" / "hooks"

    generation = hook_activation.materialize_hook_launchers(root)
    inode = generation.stat().st_ino
    repeated = hook_activation.materialize_hook_launchers(root)

    assert repeated == generation
    assert repeated.stat().st_ino == inode
    assert generation.parent == root
    assert len(generation.name) == 64
    assert {path.name for path in generation.iterdir()} == set(HOOK_NAMES)
    assert all(
        (generation / name).read_text(encoding="utf-8") == hook_launcher(name)
        for name in HOOK_NAMES
    )


def test_hook_install_blocks_cleanup_when_an_active_consumer_is_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runtime_materialization,
        "materialize_runtime",
        lambda *_args, **_kwargs: venv,
    )
    common = Path(git_common_dir(repo))
    hooks_root = common / "ethos" / "hooks"
    stale = hook_activation.materialize_hook_launchers(hooks_root)
    operations = common / "ethos" / "operations"
    operations.mkdir()
    (operations / "unknown").symlink_to(tmp_path / "missing-consumer")

    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        install_hook_launchers(repo)

    assert stale.is_dir()


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


def test_hook_activation_rejects_a_non_current_post_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, runtime = materialize_runtime_case(tmp_path, monkeypatch)
    hooks = Path(git_common_dir(repo)) / "ethos/hooks" / ("b" * 64)
    hooks.mkdir(parents=True)
    monkeypatch.setattr(
        runtime_materialization,
        "materialize_runtime",
        lambda *_args, **_kwargs: runtime,
    )
    monkeypatch.setattr(hook_activation, "materialize_hook_launchers", lambda *_args: hooks)
    monkeypatch.setattr(
        hook_activation,
        "hook_runtime_binding",
        lambda _root, **_kwargs: {
            "hooks_path": hooks.as_posix(),
            "required_gaps": ["write_admission_not_armed:runtime_build_stale"],
        },
    )

    with pytest.raises(ValueError, match="hook_runtime_activation_invalid"):
        install_hook_launchers(repo)

    selector = Path(git_common_dir(repo)) / "ethos" / "runtime" / "CURRENT"
    assert not selector.exists()


def test_hook_runtime_rejects_a_symlinked_ethos_root_before_writing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    common = Path(git_common_dir(repo))
    external = tmp_path / "external"
    external.mkdir()
    (common / "ethos").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="hook_runtime_root_invalid"):
        runtime_materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=expected_runtime_build(repo)[0],
        )

    assert not tuple(external.iterdir())


@pytest.mark.parametrize("kind", ["file", "symlink"])
def test_hook_install_retires_the_legacy_runtime_python_locator(tmp_path: Path, kind: str) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    common = Path(git_common_dir(repo))
    legacy = common / "ethos-runtime-python"
    if kind == "symlink":
        legacy.symlink_to(tmp_path / "retired-python")
    else:
        legacy.write_text("/retired/runtime/bin/python\n", encoding="utf-8")

    report = install_hook_launchers(repo)

    assert not legacy.exists()
    assert not legacy.is_symlink()
    assert report["legacy_runtime_locator"] == {
        "path": legacy.as_posix(),
        "state": "retired",
        "removed": True,
    }


def test_install_restores_runtime_selector_with_exact_cas_when_activation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    python = tmp_path / "python"
    python.write_text("python", encoding="utf-8")
    common = Path(git_common_dir(repo))
    runtime_digest = "a" * 64
    runtime = common / "ethos" / "runtime" / runtime_digest / "python"
    source = BuildIdentity(
        "0.2.0-alpha.1",
        "0.2.0a1.dev0+gcccccccccccc.tdddddddddddd",
        "c" * 40,
        "d" * 40,
        "development",
        "unaccepted",
    )
    restored: list[tuple[bytes | None, bytes | None]] = []
    monkeypatch.setattr(hook_activation, "expected_runtime_build", lambda _root: (source, None))
    monkeypatch.setattr(
        hook_activation.runtime_materialization,
        "materialize_runtime",
        lambda *_args, **_kwargs: runtime,
    )
    monkeypatch.setattr(hook_activation, "activate_runtime", lambda *_args, **_kwargs: None)

    def fail_config(*_args: object, **_kwargs: object) -> None:
        message = "activation failed"
        raise ValueError(message)

    monkeypatch.setattr(hook_activation.config_effects, "set_common_config", fail_config)
    monkeypatch.setattr(
        hook_activation,
        "restore_runtime_selection",
        lambda _common, previous, *, expected_current: restored.append(
            (previous, expected_current)
        ),
    )

    with pytest.raises(ValueError, match="activation failed"):
        hook_activation.install_hook_launchers(repo, python=python)

    selected = f"{runtime_digest}\n".encode("ascii")
    assert restored == [(None, selected)]
