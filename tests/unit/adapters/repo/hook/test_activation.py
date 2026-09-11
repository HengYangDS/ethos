"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.hook.observation as hook_observation
import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
import ethos.adapters.repo.runtime.selection as runtime_selection
import ethos.surface.cli.hook.commands as hook_commands
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.authority import runtime_build_identity
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.repository.release.identity import BuildIdentity
from tests.support.runtime_scenarios import REPOSITORY_ROOT
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import linked_runtime_case
from tests.support.runtime_scenarios import materialize_runtime_case


def _materialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, runtime = materialize_runtime_case(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime_materialization, "materialize_runtime", lambda *_a, **_k: runtime)
    return repo, runtime, Path(git_common_dir(repo))


def _legacy_state(common: Path) -> Path:
    database = common / "ethos/state.sqlite"
    database.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "lane_ref": "work/example",
        "holder_ref": "agent:test:case:owner",
        "epoch": 3,
        "expires_at": "2026-08-31T00:00:00+00:00",
    }
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "create table leases ("
            "id text primary key, subject text not null, owner text not null, "
            "expires_at text not null, payload_json text not null)"
        )
        connection.execute("create unique index leases_subject_unique on leases(subject)")
        connection.execute(
            "insert into leases values (:id, :lane_ref, :holder_ref, :expires_at, :payload_json)",
            payload | {"id": "lease:legacy", "payload_json": json.dumps(payload, sort_keys=True)},
        )
        connection.commit()
    return database


@pytest.mark.parametrize(
    ("reset", "relative", "reason"),
    [
        (True, False, "state_reset_authorization_required"),
        (False, True, "hook_runtime_python_invalid"),
        (False, False, "hook_runtime_python_invalid"),
    ],
)
def test_hook_install_rejects_invalid_admission_before_creating_state(
    tmp_path: Path, reason: str, *, reset: bool, relative: bool
) -> None:
    python = Path("relative-python") if relative else tmp_path / "missing-python"
    before = frozenset(tmp_path.iterdir())
    with pytest.raises(ValueError, match=reason):
        install_hook_launchers(tmp_path / "repo", python=python, reset_state=reset)
    assert frozenset(tmp_path.iterdir()) == before


def test_hook_install_migrates_state_before_returning_current_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, runtime, common = _materialized(tmp_path, monkeypatch)
    database = _legacy_state(common)
    observed: list[Path] = []
    inventory = runtime_selection.runtime_file_inventory

    def record_inventory(root: Path) -> dict[str, str]:
        observed.append(root)
        return inventory(root)

    monkeypatch.setattr(runtime_selection, "runtime_file_inventory", record_inventory)

    installed = install_hook_launchers(repo)
    assert observed == [runtime.parent, runtime.parent]
    assert installed["required_gaps"] == []

    assert installed["state_transition"] == {
        "before": "legacy",
        "after": "current",
        "state": "migrated",
        "row_count": 1,
    }
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "select lane_ref, holder_ref, generation, expires_at from leases"
        ).fetchall() == [
            (
                "work/example",
                "agent:test:case:owner",
                3,
                "2026-08-31T00:00:00+00:00",
            )
        ]


@pytest.mark.parametrize("before_state", ["legacy", "absent"])
@pytest.mark.parametrize("failure", ["activation", "commit"])
def test_hook_install_restores_state_and_activation_after_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, before_state: str, failure: str
) -> None:
    repo, runtime, common = _materialized(tmp_path, monkeypatch)
    database = _legacy_state(common) if before_state == "legacy" else common / "ethos/state.sqlite"
    before = database.read_bytes() if database.exists() else None
    keys = ("extensions.worktreeConfig", "gc.packRefs", "core.hooksPath")
    configured = hook_activation.config_effects.config_values(repo, keys, scope="local")
    connect = sqlite3.connect

    class CommitFailure(sqlite3.Connection):
        def commit(self) -> None:
            message = "commit failed"
            raise sqlite3.OperationalError(message)

    def fail_activation(*_args, **_kwargs):
        message = "activation failed"
        raise ValueError(message)

    with monkeypatch.context() as patch:
        if failure == "activation":
            patch.setattr(hook_activation, "_require_common_activation", fail_activation)
        else:
            patch.setattr(sqlite3, "connect", lambda path: connect(path, factory=CommitFailure))
        reason = (
            "activation failed"
            if failure == "activation"
            else "state_activation_failed:commit failed"
        )
        with pytest.raises(ValueError, match=reason):
            install_hook_launchers(repo)
    assert (database.read_bytes() if database.exists() else None) == before
    assert all(
        not database.with_name(database.name + suffix).exists() for suffix in ("-wal", "-shm")
    )
    assert not (common / "ethos/runtime/CURRENT").exists()
    assert hook_activation.config_effects.config_values(repo, keys, scope="local") == configured
    assert runtime.parent.is_dir()
    if before_state == "legacy":
        with closing(sqlite3.connect(database)) as connection:
            assert tuple(row[1] for row in connection.execute("pragma table_xinfo(leases)")) == (
                "id",
                "subject",
                "owner",
                "expires_at",
                "payload_json",
            )


@pytest.mark.parametrize("before_state", ["legacy", "absent"])
def test_hook_install_query_timeout_survives_rollback_and_public_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    before_state: str,
) -> None:
    """An observation timeout must not become a blind reinstall instruction."""
    repo, runtime, common = _materialized(tmp_path, monkeypatch)
    database = _legacy_state(common) if before_state == "legacy" else common / "ethos/state.sqlite"
    before = database.read_bytes() if database.exists() else None
    keys = ("extensions.worktreeConfig", "gc.packRefs", "core.hooksPath")
    configured = hook_activation.config_effects.config_values(repo, keys, scope="local")
    attempts = []

    def expire(root, command, **kwargs):
        attempts.append((root, command, kwargs["timeout"]))
        raise subprocess.TimeoutExpired(
            command, kwargs["timeout"], output=b"partial", stderr=b"deadline"
        )

    monkeypatch.setattr(hook_observation, "run_command", expire)
    with pytest.raises(SystemExit) as stopped:
        hook_commands.install(root=repo, json_output=True)
    assert stopped.value.code != 0
    result = json.loads(capsys.readouterr().out)
    assert result["verdict"] == "block"
    assert not result["summary"]["wired"]
    assert len(attempts) == 1
    assert (database.read_bytes() if database.exists() else None) == before
    assert all(
        not database.with_name(database.name + suffix).exists() for suffix in ("-wal", "-shm")
    )
    assert not (common / "ethos/runtime/CURRENT").exists()
    assert hook_activation.config_effects.config_values(repo, keys, scope="local") == configured
    assert runtime.parent.is_dir()
    assert result["data"]["process_failure"]["observation"] == {
        "state": "unknown",
        "reason": "runtime_hook_contract_timeout",
        "command": list(attempts[0][1]),
        "binary": attempts[0][1][0],
        "cwd": attempts[0][0].as_posix(),
        "timeout_seconds": 10,
        "stdout": "partial",
        "stderr": "deadline",
        "effect_attempted": False,
    }
    assert result["next_action"] == f"ethos status --root {repo.as_posix()} --json"


@pytest.mark.parametrize("failure", ["io", "residue", "retained"])
def test_hook_install_reports_deferred_generation_cleanup_after_successful_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    repo, runtime, common = _materialized(tmp_path, monkeypatch)
    stale, retained = (common / "ethos/runtime" / (letter * 64) for letter in "bc")
    stale.mkdir()
    retained.mkdir()
    monkeypatch.setattr(hook_activation, "process_commands", lambda _root: retained.as_posix())
    remove = runtime_materialization.remove_generated_tree

    def remove_tree(path):
        assert path == stale
        if failure == "io":
            message = "cleanup failed"
            raise OSError(message)
        if failure == "retained":
            remove(path)
            retained.rmdir()

    monkeypatch.setattr(runtime_materialization, "remove_generated_tree", remove_tree)
    installed = install_hook_launchers(repo)
    cleanup = installed["generation_cleanup"]
    assert (common / "ethos/runtime/CURRENT").read_text(
        encoding="ascii"
    ) == f"{runtime.parent.name}\n"
    assert installed["state_transition"]["after"] == "current"
    assert installed["current"] is True
    assert installed["required_gaps"] == ["hook_runtime_cleanup_deferred"]
    assert installed["next_action"] == "ethos hook install --json"
    assert cleanup["state"] == "deferred"
    assert cleanup["removed"] == []
    assert cleanup["error"] == (
        "cleanup failed" if failure == "io" else "hook_runtime_generation_cleanup_failed"
    )
    assert cleanup["deferred"] == ([] if failure == "retained" else [stale.as_posix()])
    assert stale.exists() is (failure != "retained")


def test_repeated_hook_install_reuses_the_exact_common_runtime_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, runtime = materialize_runtime_case(tmp_path, monkeypatch)
    selected = runtime_selection.activate_runtime(Path(git_common_dir(repo)), runtime.parent)
    monkeypatch.setattr(
        hook_activation,
        "expected_runtime_build",
        lambda _root: (selected.build, None),
    )
    environment = runtime_environment(
        python_abi=selected.python_abi,
        python_version=selected.python_version,
        python_implementation=selected.python_implementation,
        dependency_lock_sha256=selected.dependency_lock_sha256,
        platform_name=selected.platform,
        architecture_name=selected.architecture,
    )
    monkeypatch.setattr(
        runtime_materialization,
        "require_python_image_source",
        lambda _python: {
            "executable": selected.python.resolve().as_posix(),
            "base_executable": selected.python.resolve().as_posix(),
            "python_abi": selected.python_abi,
            "python_version": selected.python_version,
            "python_implementation": selected.python_implementation,
            "architecture": selected.architecture,
            "prefix": selected.python.parent.parent.resolve().as_posix(),
            "base_prefix": selected.python.parent.parent.resolve().as_posix(),
        },
    )
    monkeypatch.setattr(
        runtime_materialization,
        "observe_runtime_environment",
        lambda *_args, **_kwargs: environment,
    )
    monkeypatch.setattr(
        runtime_materialization,
        "resolve_runtime_wheel",
        lambda *_args, **_kwargs: pytest.fail("exact runtime generation was rebuilt"),
    )

    first = install_hook_launchers(repo)
    second = install_hook_launchers(repo)

    assert first["runtime_digest"] == second["runtime_digest"]


@pytest.mark.parametrize("consumer", ["operations", "transactions", "ref-intent"])
def test_hook_install_removes_only_unreferenced_generated_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, consumer: str
) -> None:
    repo, runtime, common = _materialized(tmp_path, monkeypatch)
    runtime_root = common / "ethos/runtime"
    retained, unrelated = runtime_root / ("a" * 64), common / "ethos-hooks-manual"
    removable = (
        runtime_root / ("b" * 64),
        common / "ethos-hooks",
        common / ("ethos-hooks-" + "c" * 64),
    )
    for path in (retained, unrelated, *removable):
        path.mkdir(parents=True)
    sealed = removable[0] / "sealed.txt"
    sealed.write_text("immutable\n", encoding="utf-8")
    sealed.chmod(0o444)
    removable[0].chmod(0o555)
    hooks = hook_activation.materialize_hook_launchers(common / "ethos/hooks")
    operations = common / "ethos" / consumer / "nested"
    operations.mkdir(parents=True)
    receipt = json.dumps({"runtime": retained.as_posix()})
    (operations / "consumer.json").write_text(receipt, encoding="utf-8")

    cleanup = install_hook_launchers(repo)["generation_cleanup"]

    assert cleanup["removed"] == sorted(path.as_posix() for path in removable)
    assert all(not path.exists() for path in removable)
    assert cleanup["retained"] == sorted(
        path.as_posix() for path in (retained, hooks, runtime.parent)
    )
    assert all(path.is_dir() for path in (retained, hooks, unrelated, runtime.parent))
    assert (operations / "consumer.json").read_text(encoding="utf-8") == receipt


def _configured_worktrees(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, linked, _runtime, generations = linked_runtime_case(tmp_path, monkeypatch)
    stale = hook_activation.materialize_hook_launchers(generations)
    config = hook_activation.config_effects
    common_values: dict[str, tuple[str, ...]] = {
        "extensions.worktreeConfig": ("true",),
        "gc.packRefs": ("true",),
        "core.hooksPath": (stale.as_posix(),),
    }
    worktree_values = {key: common_values[key] for key in ("core.hooksPath", "gc.packRefs")}
    configs = [(repo, "local", common_values)] + [
        (root, "worktree", worktree_values) for root in (repo, linked)
    ]
    for root, scope, values in configs:
        config.replace_config_values(root, values, scope=scope)
    common = Path(git_common_dir(repo))
    return repo, linked, stale, common, configs


def test_hook_install_converges_every_linked_worktree_on_one_common_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, linked, _stale, _common, configs = _configured_worktrees(tmp_path, monkeypatch)
    read = hook_activation.config_effects.config_values
    common_values, worktree_values = configs[0][2], configs[1][2]
    installed = install_hook_launchers(linked)
    expected = installed["hooks_path"]
    assert installed["linked_worktrees"] == [
        {"path": root.as_posix(), "state": "repaired"} for root in (repo, linked)
    ]
    assert read(repo, tuple(common_values), scope="local") == {
        "extensions.worktreeConfig": ("true",),
        "gc.packRefs": ("false",),
        "core.hooksPath": (expected,),
    }
    for root in (repo, linked):
        assert read(root, tuple(worktree_values), scope="worktree") == dict.fromkeys(
            worktree_values, ()
        )
        assert git_process(root, "config", "--get", "gc.packRefs").stdout.strip() == "false"
        assert (
            git_process(root, "config", "--path", "--get", "core.hooksPath").stdout.strip()
            == expected
        )
        assert hook_runtime_binding(root)["required_gaps"] == []


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("unset", "activation failed"),
        ("unreadable", "git_config_observation_failed"),
        ("common", "hook_runtime_common_activation_drift"),
        ("worktree", "hook_runtime_worktree_activation_drift"),
    ],
)
def test_hook_install_restores_all_configs_after_linked_activation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, reason: str
) -> None:
    repo, linked, stale, common, configs = _configured_worktrees(tmp_path, monkeypatch)
    config = hook_activation.config_effects
    unset, set_common, read = (
        config.unset_worktree_config,
        config.set_common_config,
        config.config_values,
    )

    def unset_worktree(root, keys):
        if root == linked and fault == "unset":
            message = "activation failed"
            raise ValueError(message)
        unset(root, keys)
        if root == linked and fault == "worktree":
            config.replace_config_values(root, {"gc.packRefs": ("true",)}, scope="worktree")

    def set_common_config(root, values):
        set_common(root, values)
        if fault == "common" and "core.hooksPath" in values:
            set_common(root, {"gc.packRefs": "true"})

    def read_config(root, keys, *, scope):
        if fault == "unreadable" and root == linked and scope == "worktree":
            message = "git_config_observation_failed"
            raise ValueError(message)
        return read(root, keys, scope=scope)

    with monkeypatch.context() as patch:
        patch.setattr(config, "unset_worktree_config", unset_worktree)
        patch.setattr(config, "set_common_config", set_common_config)
        patch.setattr(config, "config_values", read_config)
        with pytest.raises(ValueError, match=reason):
            install_hook_launchers(repo)
    assert not (common / "ethos/runtime/CURRENT").exists()
    assert not (common / "ethos/state.sqlite").exists()
    assert all(read(root, tuple(values), scope=scope) == values for root, scope, values in configs)
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

    assert source_selections == [repo, repo]
    assert materialized_with == [accepted_identity]
    assert installed["expected_source_commit"] == accepted_identity.source_commit
    assert installed["expected_source_tree"] == accepted_identity.source_tree
    assert installed["required_gaps"] == []


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


@pytest.mark.parametrize("consumer", ["operations", "transactions", "ref-intent"])
@pytest.mark.parametrize(
    "invalidity",
    [
        "symlink",
        "invalid-utf8",
        "directory-file",
        "nested-link",
        "root-link",
        "root-junction",
        "nested-junction",
        pytest.param(
            "scan-error",
            marks=pytest.mark.skipif(os.name == "nt", reason="POSIX directory permissions"),
        ),
    ],
)
def test_hook_install_blocks_cleanup_when_an_active_consumer_is_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalidity: str, consumer: str
) -> None:
    repo, _venv, common = _materialized(tmp_path, monkeypatch)
    stale = common / "ethos/runtime" / ("f" * 64)
    stale.mkdir()
    sentinel = stale / "needed"
    sentinel.write_bytes(b"retained runtime")
    monkeypatch.setattr(hook_activation, "process_commands", lambda _root: "")
    operations = common / "ethos" / consumer
    external = tmp_path / "external"
    external.mkdir()
    (external / "receipt").write_text(stale.as_posix(), encoding="utf-8")
    if invalidity == "directory-file":
        operations.write_text("not a directory", encoding="utf-8")
    elif invalidity == "root-link":
        operations.symlink_to(tmp_path / "missing", target_is_directory=True)
    else:
        operations.mkdir()
        if invalidity in {"symlink", "nested-link"}:
            (operations / "unknown").symlink_to(
                external if invalidity == "nested-link" else tmp_path / "missing"
            )
        else:
            (operations / "unknown").write_bytes(b"ok" if "junction" in invalidity else b"\xff")
    if invalidity == "nested-junction":
        (operations / "nested").mkdir()
    monkeypatch.setattr(
        runtime_filesystem,
        "is_junction",
        lambda path: (
            (invalidity == "root-junction" and path == operations)
            or (invalidity == "nested-junction" and path == operations / "nested")
        ),
    )
    refused = ""
    if invalidity == "scan-error":
        operations.chmod(0o000)
    try:
        install_hook_launchers(repo)
    except ValueError as error:
        refused = str(error)
    finally:
        if invalidity == "scan-error":
            operations.chmod(0o700)
    assert sentinel.is_file(), "cleanup deleted an unobserved consumer's runtime"
    assert sentinel.read_bytes() == b"retained runtime"
    assert refused == "hook_runtime_consumers_unknown"
    assert not (common / "ethos/runtime/CURRENT").exists()
    assert not (common / "ethos/state.sqlite").exists()


@pytest.mark.parametrize("platform", ["nt", "posix"])
@pytest.mark.parametrize("status", [0, 2])
def test_consumer_observation_uses_native_tools_and_rejects_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, status: int
) -> None:
    executable = tmp_path / "System32/WindowsPowerShell/v1.0/powershell.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("native\n", encoding="utf-8")
    monkeypatch.setenv("SYSTEMROOT", tmp_path.as_posix())
    monkeypatch.setenv("PATH", (tmp_path / "git-only").as_posix())
    expected = (
        (
            executable.resolve().as_posix(),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-CimInstance Win32_Process | % CommandLine",
        )
        if platform == "nt"
        else ("/native/ps", "-axo", "command=")
    )
    if platform == "posix":
        monkeypatch.setattr(hook_activation, "process_listing_command", lambda **_kwargs: expected)
    observed = []

    def capture(_root, command, **kwargs):
        observed.append((command, kwargs))
        return subprocess.CompletedProcess(command, status, "consumer\n", "observer failed")

    monkeypatch.setattr(hook_activation, "run_command", capture)
    if status:
        with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
            hook_activation.process_commands(tmp_path, platform_name=platform)
    else:
        assert hook_activation.process_commands(tmp_path, platform_name=platform) == "consumer\n"
    assert observed == [(expected, {"remove_env_prefixes": ("GIT_",)})]


@pytest.mark.parametrize("invalidity", ["junction", "file", "symlink"])
def test_hook_install_rejects_invalid_runtime_generation_without_touching_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalidity: str,
) -> None:
    repo, _venv, common = _materialized(tmp_path, monkeypatch)
    junction = common / "ethos/runtime" / ("f" * 64)
    if invalidity == "file":
        junction.write_text("outside authority\n", encoding="utf-8")
        sentinel = junction
    else:
        external = tmp_path / "external-generation"
        external.mkdir()
        if invalidity == "symlink":
            junction.symlink_to(external, target_is_directory=True)
        else:
            junction.mkdir(parents=True)
        sentinel = junction / "sentinel"
        sentinel.write_text("outside authority\n", encoding="utf-8")
    monkeypatch.setattr(
        runtime_filesystem,
        "is_junction",
        lambda path: invalidity == "junction" and path == junction,
    )

    with pytest.raises(ValueError, match="hook_runtime_generation_root_invalid"):
        install_hook_launchers(repo)

    assert sentinel.read_text(encoding="utf-8") == "outside authority\n"


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


@pytest.mark.parametrize("drift", ["path", "gaps"])
def test_hook_activation_rejects_a_non_current_post_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    repo, _runtime, common = _materialized(tmp_path, monkeypatch)
    observe = hook_activation.hook_runtime_binding

    def stale_binding(*args, **kwargs):
        binding = observe(*args, **kwargs)
        if drift == "path":
            binding["hooks_path"] = (common / "foreign-hooks").as_posix()
        else:
            binding["required_gaps"] = ["write_admission_not_armed:runtime_build_stale"]
        return binding

    monkeypatch.setattr(hook_activation, "hook_runtime_binding", stale_binding)
    reason = (
        "hook_runtime_activation_drift" if drift == "path" else "hook_runtime_activation_invalid"
    )
    with pytest.raises(ValueError, match=reason):
        install_hook_launchers(repo)
    assert not (common / "ethos/runtime/CURRENT").exists()
    assert not (common / "ethos/state.sqlite").exists()


def test_hook_activation_compensates_when_expected_build_drifts_during_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, runtime, common = _materialized(tmp_path, monkeypatch)
    selected = runtime_selection.require_selected_runtime(runtime.parent)
    drifted = BuildIdentity(
        selected.build.product_version,
        selected.build.distribution_version,
        "d" * 40,
        "e" * 40,
    )
    observations = iter((selected.build, drifted))
    monkeypatch.setattr(
        hook_activation,
        "expected_runtime_build",
        lambda _root: (next(observations), None),
    )

    with pytest.raises(ValueError, match="hook_runtime_expected_build_stale"):
        install_hook_launchers(repo)

    assert not (common / "ethos/runtime/CURRENT").exists()
    assert git_process(repo, "config", "--local", "--get", "core.hooksPath").returncode != 0


def test_hook_cleanup_rejects_selector_drift_before_deleting_generations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _runtime, common = _materialized(tmp_path, monkeypatch)
    concurrent_digest = "c" * 64
    concurrent = common / "ethos/runtime" / concurrent_digest
    concurrent.mkdir(parents=True)
    sentinel = concurrent / "sentinel"
    sentinel.write_text("concurrent selection\n", encoding="utf-8")
    original_plan = vars(hook_activation)["_generation_cleanup_plan"]

    def drift_after_plan(*args: object, **kwargs: object) -> dict[str, tuple[Path, ...]]:
        plan = original_plan(*args, **kwargs)
        (common / "ethos/runtime/CURRENT").write_text(
            f"{concurrent_digest}\n",
            encoding="ascii",
        )
        return plan

    monkeypatch.setattr(hook_activation, "_generation_cleanup_plan", drift_after_plan)

    with pytest.raises(ValueError, match="hook_runtime_current_stale"):
        install_hook_launchers(repo)

    assert sentinel.read_text(encoding="utf-8") == "concurrent selection\n"


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


@pytest.mark.parametrize("kind", ["file", "symlink", "directory"])
def test_hook_install_retires_the_legacy_runtime_python_locator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    repo, _runtime, common = _materialized(tmp_path, monkeypatch)
    legacy = common / "ethos-runtime-python"
    if kind == "symlink":
        legacy.symlink_to(tmp_path / "retired-python")
    elif kind == "directory":
        legacy.mkdir()
    else:
        legacy.write_text("/retired/runtime/bin/python\n", encoding="utf-8")

    report = install_hook_launchers(repo)

    if kind == "directory":
        assert legacy.is_dir()
        assert report["legacy_runtime_locator"]["state"] == "retained"
        assert report["required_gaps"] == ["hook_runtime_cleanup_deferred"]
        assert report["next_action"] == "ethos hook install --json"
        return
    assert not legacy.exists()
    assert not legacy.is_symlink()
    assert report["legacy_runtime_locator"] == {
        "path": legacy.as_posix(),
        "state": "retired",
        "removed": True,
    }


@pytest.mark.parametrize("boundary", ["selection", "config"])
def test_install_restores_only_changed_selector_with_exact_cas_after_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    repo, runtime, common = _materialized(tmp_path, monkeypatch)
    restored = []
    restore = hook_activation.restore_runtime_selection

    def record_restore(root, previous, *, expected_current):
        restored.append((root, previous, expected_current))
        restore(root, previous, expected_current=expected_current)

    def fail(*_args, **_kwargs):
        message = f"{boundary} failed"
        raise ValueError(message)

    owner, name = (
        (hook_activation, "activate_runtime")
        if boundary == "selection"
        else (hook_activation.config_effects, "set_common_config")
    )
    monkeypatch.setattr(owner, name, fail)
    monkeypatch.setattr(hook_activation, "restore_runtime_selection", record_restore)
    with pytest.raises(ValueError, match=f"{boundary} failed"):
        install_hook_launchers(repo)
    expected = (
        []
        if boundary == "selection"
        else [(common, None, f"{runtime.parent.name}\n".encode("ascii"))]
    )
    assert restored == expected
    assert not (common / "ethos/runtime/CURRENT").exists()
    assert runtime.parent.is_dir()


@pytest.mark.parametrize("failure", ["config", "selector", "both", "unreadable"])
def test_failed_activation_attempts_every_compensation_and_reports_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    common, linked = tmp_path / "common", tmp_path / "linked"
    selector = common / "ethos/runtime/CURRENT"
    selector.parent.mkdir(parents=True)
    selected = b"a" * 64 + b"\n"
    if failure == "unreadable":
        selector.mkdir()
    else:
        selector.write_bytes(selected)
    attempted = []
    restore = hook_activation.restore_runtime_selection

    def replace(root, values, *, scope):
        assert values == {}
        attempted.append((root, scope))
        if failure in {"config", "both"} and (root == linked or scope == "local"):
            message = f"{scope} compensation"
            raise ValueError(message)

    def restore_selector(root, previous, *, expected_current):
        attempted.append((root, "selector"))
        assert previous is None
        assert expected_current == selected
        if failure in {"selector", "both"}:
            message = "selector compensation"
            raise OSError(message)
        restore(root, previous, expected_current=expected_current)

    monkeypatch.setattr(hook_activation.config_effects, "replace_config_values", replace)
    monkeypatch.setattr(hook_activation, "restore_runtime_selection", restore_selector)
    with pytest.raises(ValueError, match="hook_runtime_activation_compensation_failed") as error:
        vars(hook_activation)["_restore_failed_activation"](
            tmp_path, common, {}, {linked: {}, tmp_path: {}}, None, selected_runtime=selected
        )
    expected = [(linked, "worktree"), (tmp_path, "worktree"), (tmp_path, "local")]
    assert attempted == expected + ([] if failure == "unreadable" else [(common, "selector")])
    if failure in {"config", "both"}:
        assert "worktree compensation" in str(error.value)
        assert "local compensation" in str(error.value)
    if failure in {"selector", "both"}:
        assert "selector compensation" in str(error.value)
        assert selector.read_bytes() == selected
    elif failure == "unreadable":
        assert "hook_runtime_current_invalid" in str(error.value)
        assert selector.is_dir()
    else:
        assert not selector.exists()
