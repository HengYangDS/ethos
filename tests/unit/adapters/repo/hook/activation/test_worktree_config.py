"""Git-common hook activation owns linked configuration and bounded maintenance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import linked_runtime_case


def _configured_worktrees(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, linked, _runtime, generations = linked_runtime_case(tmp_path, monkeypatch)
    stale = hook_activation.materialize_hook_launchers(generations)
    config = hook_activation.config_effects
    common_values: dict[str, tuple[str, ...]] = {
        "extensions.worktreeConfig": ("true",),
        "gc.packRefs": ("true",),
        "maintenance.pack-refs.enabled": ("true",),
        "core.hooksPath": (stale.as_posix(),),
    }
    worktree_values = {
        key: common_values[key]
        for key in ("core.hooksPath", "gc.packRefs", "maintenance.pack-refs.enabled")
    }
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
    before = git_process(repo, "show-ref").stdout
    trace = tmp_path / "native-maintenance.jsonl"
    monkeypatch.setenv("GIT_TRACE2_EVENT", trace.as_posix())
    maintenance = git_process(
        linked,
        "-c",
        "maintenance.strategy=incremental",
        "-c",
        "maintenance.gc.enabled=false",
        "-c",
        "maintenance.commit-graph.enabled=false",
        "-c",
        "maintenance.prefetch.enabled=false",
        "-c",
        "maintenance.loose-objects.enabled=false",
        "-c",
        "maintenance.incremental-repack.enabled=false",
        "maintenance",
        "run",
        "--no-quiet",
        "--no-detach",
    )
    assert maintenance.returncode == 0, maintenance.stderr
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    assert not any(
        record.get("event") == "child_start" and "pack-refs" in record.get("argv", [])
        for record in records
    )
    assert git_process(repo, "show-ref").stdout == before
    assert installed["linked_worktrees"] == [
        {"path": root.as_posix(), "state": "repaired"} for root in (repo, linked)
    ]
    assert read(repo, tuple(common_values), scope="local") == {
        "extensions.worktreeConfig": ("true",),
        "gc.packRefs": ("false",),
        "maintenance.pack-refs.enabled": ("false",),
        "core.hooksPath": (expected,),
    }
    for root in (repo, linked):
        assert read(root, tuple(worktree_values), scope="worktree") == dict.fromkeys(
            worktree_values, ()
        )
        assert git_process(root, "config", "--get", "gc.packRefs").stdout.strip() == "false"
        assert (
            git_process(root, "config", "--get", "maintenance.pack-refs.enabled").stdout.strip()
            == "false"
        )
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
            config.replace_config_values(
                root, {"maintenance.pack-refs.enabled": ("true",)}, scope="worktree"
            )

    def set_common_config(root, values):
        set_common(root, values)
        if fault == "common" and "core.hooksPath" in values:
            set_common(root, {"maintenance.pack-refs.enabled": "true"})

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
