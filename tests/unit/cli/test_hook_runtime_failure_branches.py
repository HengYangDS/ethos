from __future__ import annotations

import json
import os
import subprocess
from io import StringIO
from pathlib import Path

import pytest

import ethos.adapters.repo.config_effects as config_effects
import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.hook.binding as hook_binding
import ethos.adapters.repo.hook_runtime as runtime
from ethos.adapters.repo.hook.source_identity import RuntimeSourceIdentity

_activation_private = vars(hook_activation)
_config_private = vars(config_effects)
_linked_worktree_paths = _activation_private["_linked_worktree_paths"]
_expected_common_activation = _activation_private["_expected_common_activation"]
_require_common_activation = _activation_private["_require_common_activation"]
_restore_activation = _activation_private["_restore_activation"]
_generated_directories = _activation_private["_generated_directories"]
_consumer_text = _activation_private["_consumer_text"]
_process_commands = _activation_private["_process_commands"]
_config_text = _activation_private["_config_text"]
_apply_generation_cleanup = _activation_private["_apply_generation_cleanup"]
_set_config_values = _config_private["_set_values"]


def _candidate_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    status: str,
) -> Path:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    policy = type(
        "Policy",
        (),
        {
            "candidate_branch": "candidate/dev",
            "accepted_branch": "dev",
            "release_branch": "main",
            "release_mirror": "independent",
            "role_for_branch": lambda _self, _branch: "accepted",
        },
    )()
    monkeypatch.setattr(runtime, "resolve_ref_move_policy", lambda *_args: policy)
    monkeypatch.setattr(
        runtime,
        "worktree_records",
        lambda *_args, **_kwargs: [
            {"branch": "candidate/dev", "path": candidate, "head": "b" * 40}
        ],
    )
    monkeypatch.setattr(
        runtime,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, status, ""),
    )
    return candidate


def test_install_rejects_nonexistent_and_relative_python(tmp_path: Path) -> None:
    for python in (Path("python"), tmp_path / "missing-python"):
        with pytest.raises(ValueError, match="hook_runtime_python_invalid"):
            hook_activation.install_hook_launchers(tmp_path, python=python)


def test_install_rejects_unavailable_source_authority_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python = tmp_path / "python"
    python.write_text("python", encoding="utf-8")
    materialized = False

    def unavailable(_root: Path):
        message = "hook_runtime_accepted_source_identity_unavailable"
        raise ValueError(message)

    def materialize(*_args: object, **_kwargs: object) -> Path:
        nonlocal materialized
        materialized = True
        return tmp_path / "runtime/venv"

    monkeypatch.setattr(hook_activation, "expected_runtime_source", unavailable)
    monkeypatch.setattr(hook_activation.runtime_install, "materialize_hook_runtime", materialize)

    with pytest.raises(ValueError, match="hook_runtime_accepted_source_identity_unavailable"):
        hook_activation.install_hook_launchers(tmp_path, python=python)

    assert materialized is False


def test_hook_activation_observation_failures_are_precise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed = subprocess.CompletedProcess([], 1, "", "worktrees failed")
    monkeypatch.setattr(hook_activation, "run_git", lambda *_args, **_kwargs: failed)
    with pytest.raises(ValueError, match="worktrees failed"):
        _linked_worktree_paths(tmp_path)

    empty = subprocess.CompletedProcess([], 0, "", "")
    monkeypatch.setattr(hook_activation, "run_git", lambda *_args, **_kwargs: empty)
    with pytest.raises(ValueError, match="hook_runtime_worktrees_unreadable"):
        _linked_worktree_paths(tmp_path)

    missing = subprocess.CompletedProcess([], 0, f"worktree {tmp_path / 'missing'}\0", "")
    monkeypatch.setattr(hook_activation, "run_git", lambda *_args, **_kwargs: missing)
    with pytest.raises(ValueError, match="hook_runtime_worktrees_unreadable"):
        _linked_worktree_paths(tmp_path)


def test_common_activation_postconditions_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = tmp_path / "linked"
    worktree.mkdir()
    hooks = tmp_path / "hooks"
    source = RuntimeSourceIdentity(commit="a" * 40, tree="b" * 40)
    expected = _expected_common_activation(hooks)
    empty_worktree = {"core.hooksPath": (), "gc.packRefs": ()}

    monkeypatch.setattr(
        hook_activation.config_effects,
        "config_values",
        lambda *_args, **_kwargs: {},
    )
    with pytest.raises(ValueError, match="hook_runtime_common_activation_drift"):
        _require_common_activation(tmp_path, (worktree,), hooks, expected_source=source)

    def worktree_drift(root: Path, _keys: tuple[str, ...], *, scope: str):
        return expected if scope == "local" else {"core.hooksPath": (root.as_posix(),)}

    monkeypatch.setattr(hook_activation.config_effects, "config_values", worktree_drift)
    with pytest.raises(ValueError, match="hook_runtime_worktree_activation_drift"):
        _require_common_activation(tmp_path, (worktree,), hooks, expected_source=source)

    monkeypatch.setattr(
        hook_activation.config_effects,
        "config_values",
        lambda _root, _keys, *, scope: expected if scope == "local" else empty_worktree,
    )
    monkeypatch.setattr(
        hook_activation,
        "hook_runtime_binding",
        lambda _root, **_kwargs: {"hooks_path": "wrong", "required_gaps": []},
    )
    with pytest.raises(ValueError, match="hook_runtime_activation_drift"):
        _require_common_activation(tmp_path, (worktree,), hooks, expected_source=source)

    monkeypatch.setattr(
        hook_activation,
        "hook_runtime_binding",
        lambda _root, **_kwargs: {
            "hooks_path": hooks.as_posix(),
            "required_gaps": ["stale"],
        },
    )
    with pytest.raises(ValueError, match="hook_runtime_activation_invalid:stale"):
        _require_common_activation(tmp_path, (worktree,), hooks, expected_source=source)


def test_activation_compensation_reports_every_failed_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    linked = tmp_path / "linked"

    def fail(root: Path, _values: object, *, scope: str) -> None:
        message = f"{scope}:{root.name}"
        raise ValueError(message)

    monkeypatch.setattr(hook_activation.config_effects, "replace_config_values", fail)
    with pytest.raises(
        ValueError,
        match="hook_runtime_activation_compensation_failed:worktree:linked,local:test_activation_compensation",
    ):
        _restore_activation(
            tmp_path,
            {"core.hooksPath": ()},
            {linked: {"core.hooksPath": ()}},
        )


def test_generation_inventory_rejects_ambiguous_roots(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert _generated_directories(missing) == ()

    file_root = tmp_path / "file"
    file_root.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="hook_runtime_generation_root_invalid"):
        _generated_directories(file_root)

    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="hook_runtime_generation_root_invalid"):
        _generated_directories(alias)


def test_consumer_inventory_fails_closed_for_unknown_carriers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hook_activation, "_process_commands", lambda _root: "")
    common = tmp_path / "common"
    ethos = common / "ethos"
    ethos.mkdir(parents=True)

    operations = ethos / "operations"
    operations.symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        _consumer_text(tmp_path, common)
    operations.unlink()

    operations.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        _consumer_text(tmp_path, common)
    operations.unlink()

    operations.mkdir()
    (operations / "nested").mkdir()
    (operations / "nested" / "consumer.json").write_text("runtime", encoding="utf-8")
    assert _consumer_text(tmp_path, common) == "\nruntime"
    (operations / "nested" / "consumer.json").write_bytes(b"\xff")
    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        _consumer_text(tmp_path, common)

    (operations / "nested" / "consumer.json").unlink()
    fifo = operations / "consumer.pipe"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        _consumer_text(tmp_path, common)


def test_consumer_process_and_config_observation_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed = subprocess.CompletedProcess([], 2, "", "failed")
    monkeypatch.setattr(hook_activation, "run_command", lambda *_args, **_kwargs: failed)
    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        _process_commands(tmp_path)

    monkeypatch.setattr(hook_activation, "_linked_worktree_paths", lambda _root: (tmp_path,))
    monkeypatch.setattr(hook_activation, "run_git", lambda *_args, **_kwargs: failed)
    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        _config_text(tmp_path)


def test_generation_cleanup_proves_removed_and_retained_postconditions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    removed = tmp_path / "removed"
    removed.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="hook_runtime_generation_cleanup_invalid"):
        _apply_generation_cleanup({"checked": (removed,), "removed": (removed,), "retained": ()})

    removed.unlink()
    removed.mkdir()
    monkeypatch.setattr(hook_activation.shutil, "rmtree", lambda _path: None)
    with pytest.raises(ValueError, match="hook_runtime_generation_cleanup_failed"):
        _apply_generation_cleanup({"checked": (removed,), "removed": (removed,), "retained": ()})

    retained = tmp_path / "retained"
    retained.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="hook_runtime_generation_cleanup_failed"):
        _apply_generation_cleanup({"checked": (retained,), "removed": (), "retained": (retained,)})


def test_hook_binding_primitives_reject_invalid_runtime_projections(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="hook_name_invalid"):
        hook_binding.hook_launcher("../../runtime/" + "a" * 64 + "/venv/bin/python", "post")
    with pytest.raises(ValueError, match="hook_runtime_locator_invalid"):
        hook_binding.hook_launcher("/absolute/python", "pre-commit")
    with pytest.raises(ValueError, match="hook_launcher_projection_invalid"):
        hook_binding.hook_generation_digest({"pre-commit": "only"})

    hooks = tmp_path / "hooks"
    hooks.mkdir()
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    launcher = hooks / "pre-commit"
    launcher.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        hook_binding.launcher_runtime_generation(hooks, runtime_root)
    launcher.write_text("#!/bin/sh\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        hook_binding.launcher_runtime_generation(hooks, runtime_root)
    launcher.write_text(
        hook_binding.hook_launcher("../../runtime/" + "a" * 64 + "/venv/bin/python", "pre-commit"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        hook_binding.launcher_runtime_generation(hooks, runtime_root)


def test_hook_binding_reports_unavailable_source_and_generation_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert (
        subprocess.run(
            ("git", "init", "--quiet", "--initial-branch=dev"), cwd=repo, check=False
        ).returncode
        == 0
    )
    common = repo / ".git"
    generations = common / "ethos/hooks"
    generation = generations / ("a" * 64)
    generation.mkdir(parents=True)
    assert (
        subprocess.run(
            ("git", "config", "core.hooksPath", generation.as_posix()), cwd=repo, check=False
        ).returncode
        == 0
    )
    monkeypatch.setattr(
        hook_binding,
        "_runtime_from_launcher",
        lambda *_args: (None, None, "", "", None),
    )
    monkeypatch.setattr(
        hook_binding,
        "expected_runtime_source",
        lambda _repo: (_ for _ in ()).throw(ValueError("missing")),
    )
    report = hook_binding.hook_runtime_binding(repo)
    assert (
        "write_admission_not_armed:runtime_expected_source_unavailable" in report["required_gaps"]
    )


def test_config_effect_failures_report_the_exact_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = subprocess.CompletedProcess([], 2, "", "config failed")
    monkeypatch.setattr(config_effects, "run_git", lambda *_args, **_kwargs: failure)
    with pytest.raises(ValueError, match="config failed"):
        config_effects.config_values(tmp_path, ("core.hooksPath",), scope="local")
    with pytest.raises(ValueError, match="config failed"):
        config_effects.replace_config_values(tmp_path, {"core.hooksPath": ()}, scope="local")
    with pytest.raises(ValueError, match="config failed"):
        _set_config_values(tmp_path, {"core.hooksPath": "hooks"}, scope="local")


def test_reference_transition_policy_failure_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runtime,
        "resolve_ref_move_policy",
        lambda *_args: (_ for _ in ()).throw(TypeError("bad policy")),
    )
    result = runtime.execute_hook(
        tmp_path,
        "reference-transaction",
        ("prepared",),
        stdin=StringIO(f"{'a' * 40} {'b' * 40} refs/heads/work/example\n"),
    )
    assert result == 1


def test_candidate_report_rejects_dirty_or_unbound_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _candidate_runtime(monkeypatch, tmp_path, status="dirty\n")
    result = runtime.execute_hook(
        tmp_path,
        "reference-transaction",
        ("prepared",),
        stdin=StringIO(f"{'a' * 40} {'b' * 40} refs/heads/dev\n"),
    )

    assert result == 1
    assert json.loads(capsys.readouterr().err)["required_gaps"] == [
        "candidate_semantic_runner_unavailable"
    ]


@pytest.mark.parametrize(
    "binding",
    [
        {"required_gaps": ["binding_stale"], "python": ""},
        {"required_gaps": [], "python": "missing"},
    ],
)
def test_candidate_runner_requires_clean_binding_and_real_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    binding: dict[str, object],
) -> None:
    _candidate_runtime(monkeypatch, tmp_path, status="")
    if binding["python"]:
        binding["python"] = str(tmp_path / str(binding["python"]))
    monkeypatch.setattr(
        runtime,
        "hook_runtime_binding",
        lambda _root: binding,
    )
    result = runtime.execute_hook(
        tmp_path,
        "reference-transaction",
        ("prepared",),
        stdin=StringIO(f"{'a' * 40} {'b' * 40} refs/heads/dev\n"),
    )

    assert result == 1
    assert "candidate_semantic_runner_unavailable" in capsys.readouterr().err


def test_execute_hook_converts_runtime_exception_to_json_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        runtime,
        "run_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("state unavailable")),
    )
    assert runtime.execute_hook(tmp_path, "pre-commit", (), stdin=StringIO()) == 1
    assert json.loads(capsys.readouterr().err)["required_gaps"] == ["state unavailable"]
