"""Portable Git-hook launcher and runtime-provenance contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.hook_runtime as hook_runtime
import ethos.adapters.repo.hook_runtime_install as runtime_install
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.hook.binding import runtime_locator
from ethos.adapters.repo.hook.source_identity import expected_runtime_source
from ethos.adapters.repo.hook.source_identity import runtime_source_identity
from ethos.adapters.repo.hook_runtime import execute_hook
from ethos.contracts.branch.roles import BranchRolePolicy
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane


def _git(root: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=root,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def _venv_executable(venv: Path, name: str) -> Path:
    directory = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return venv / directory / f"{name}{suffix}"


def _materialize_runtime_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_identity: runtime_install.RuntimeSourceIdentity | None = None,
) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    source = tmp_path / "installed" / "a" / "b" / "c" / "d"
    source.mkdir(parents=True)
    wheel = tmp_path / "ethos-test.whl"
    wheel.write_bytes(b"wheel")
    source_python = Path(sys.executable)
    monkeypatch.setattr(runtime_install, "__file__", (source / "module.py").as_posix())
    monkeypatch.setattr(runtime_install, "resolve_runtime_wheel", lambda *_args: wheel)
    monkeypatch.setattr(runtime_install, "_python_abi", lambda _python: "cpython-test")
    identity = source_identity or runtime_source_identity(Path(__file__).resolve().parents[3])
    monkeypatch.setattr(runtime_install, "wheel_source_identity", lambda *_args: identity)

    def copy_runtime(target: Path, _python: Path) -> None:
        runtime_python = _venv_executable(target, "python")
        runtime_python.parent.mkdir(parents=True)
        source_python = Path(sys.executable)
        runtime_python.write_bytes(source_python.read_bytes())
        runtime_python.chmod(source_python.stat().st_mode)
        entrypoint = _venv_executable(target, "ethos")
        entrypoint.write_text(
            f"#!{runtime_python}\nprint('ethos-test')\n",
            encoding="utf-8",
        )
        entrypoint.chmod(0o755)

    monkeypatch.setattr(runtime_install, "_copy_installed_runtime", copy_runtime)
    return repo, runtime_install.materialize_hook_runtime(
        repo,
        source_python,
        expected_source=identity,
    )


def _linked_runtime_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path, Path]:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runtime_install,
        "materialize_hook_runtime",
        lambda *_args, **_kwargs: venv,
    )
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    assert _git(repo, "add", "tracked.txt").returncode == 0
    assert (
        _git(
            repo,
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "base",
        ).returncode
        == 0
    )
    linked = tmp_path / "linked"
    assert _git(repo, "worktree", "add", "-q", "-b", "work/linked", linked).returncode == 0
    common = Path(git_common_dir(repo))
    return repo, linked, venv, common / "ethos" / "hooks"


def test_hook_binding_rejects_an_intact_runtime_from_an_older_source_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = runtime_install.RuntimeSourceIdentity(commit="a" * 40, tree="b" * 40)
    repo, venv = _materialize_runtime_case(
        tmp_path,
        monkeypatch,
        source_identity=installed,
    )
    common = Path(git_common_dir(repo))
    generation = runtime_install.materialize_hook_launchers(
        common / "ethos" / "hooks", runtime_locator(venv)
    )
    assert _git(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        _git(repo, "config", "--worktree", "core.hooksPath", generation.as_posix()).returncode == 0
    )
    expected = runtime_install.RuntimeSourceIdentity(commit="c" * 40, tree="d" * 40)

    observed = hook_runtime_binding(repo, expected_source=expected)

    assert observed["source_commit"] == "a" * 40
    assert observed["source_tree"] == "b" * 40
    assert observed["expected_source_commit"] == "c" * 40
    assert observed["expected_source_tree"] == "d" * 40
    assert observed["current"] is False
    assert observed["required_gaps"] == ["write_admission_not_armed:runtime_source_stale"]
    assert observed["next_action"] == (f"ethos hook install --root {repo.as_posix()} --json")


def test_status_projects_the_single_hook_runtime_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    generation = runtime_install.materialize_hook_launchers(
        common / "ethos" / "hooks",
        runtime_locator(venv),
    )
    assert _git(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        _git(repo, "config", "--worktree", "core.hooksPath", generation.as_posix()).returncode == 0
    )
    installed = hook_runtime_binding(repo)

    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    assert projected["data"]["hook_runtime"] == installed


def test_self_hosted_expectation_uses_the_accepted_ref_and_linked_checkout(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "ethos"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    (repo / ".ethos").mkdir()
    (repo / ".ethos/profile.toml").write_text('profile_id = "ethos"\n', encoding="utf-8")
    (repo / ".ethos/workspace.toml").write_text(
        '[branch_roles]\naccepted_branch = "dev"\n',
        encoding="utf-8",
    )
    (repo / "tracked.txt").write_text("accepted\n", encoding="utf-8")
    assert _git(repo, "add", ".").returncode == 0
    accepted = _git(
        repo,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "accepted",
    )
    assert accepted.returncode == 0
    accepted_commit = _git(repo, "rev-parse", "dev").stdout.strip()
    accepted_tree = _git(repo, "rev-parse", "dev^{tree}").stdout.strip()
    lane = tmp_path / "lane"
    assert _git(repo, "worktree", "add", "-q", "-b", "work/runtime", lane).returncode == 0
    (lane / "tracked.txt").write_text("candidate\n", encoding="utf-8")
    assert _git(lane, "add", "tracked.txt").returncode == 0
    candidate = _git(
        lane,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "candidate",
    )
    assert candidate.returncode == 0

    identity, source_root = expected_runtime_source(lane)

    assert identity == runtime_install.RuntimeSourceIdentity(
        commit=accepted_commit,
        tree=accepted_tree,
    )
    assert source_root == repo.resolve()


@pytest.mark.parametrize(
    "drift",
    [
        "manifest",
        "schema",
        "digest",
        "wheel",
        "abi",
        "platform",
        "source_commit",
        "source_tree",
        "files",
        "python",
        "hash",
    ],
)
def test_hook_runtime_manifest_rejects_every_binding_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    runtime = venv.parent
    manifest = runtime / "manifest.json"
    python = _venv_executable(venv, "python")
    if drift == "manifest":
        manifest.write_text("not-json", encoding="utf-8")
    elif drift == "schema":
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["schema_version"] = 1
        manifest.write_text(json.dumps(payload), encoding="utf-8")
    elif drift == "python":
        python.unlink()
    elif drift == "hash":
        python.write_text("drift\n", encoding="utf-8")
    else:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        key = {
            "digest": "runtime_digest",
            "wheel": "wheel_sha256",
            "abi": "python_abi",
            "platform": "platform",
            "source_commit": "source_commit",
            "source_tree": "source_tree",
            "files": "runtime_files",
        }[drift]
        payload[key] = {} if drift == "files" else "drift"
        manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        runtime_install.materialize_hook_runtime(
            repo,
            Path(sys.executable),
            expected_source=expected_runtime_source(repo)[0],
        )


def test_hook_runtime_manifest_and_runtime_locator_bind_exact_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    runtime = venv.parent

    executable = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    assert runtime_locator(runtime / "venv") == f"../../runtime/{runtime.name}/venv/{executable}"


def test_hook_runtime_wheel_provenance_and_tool_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "installed"
    source.mkdir()

    class Metadata:
        def read_text(self, _name: str) -> str:
            return '{"url":"https://example.invalid/ethos.whl"}'

    monkeypatch.setattr(runtime_install, "distribution", lambda _name: Metadata())
    with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
        runtime_install.resolve_runtime_wheel(source, tmp_path / "wheel")

    (source / "pyproject.toml").touch()
    monkeypatch.setattr(runtime_install.sys, "executable", (tmp_path / "python").as_posix())
    with pytest.raises(ValueError, match="hook_runtime_uv_unavailable"):
        runtime_install.resolve_runtime_wheel(source, tmp_path / "build" / "wheel")


def test_hook_runtime_python_and_manifest_require_executable_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _git(tmp_path, "init", "--quiet", "--initial-branch=dev").returncode == 0
    identity = runtime_install.RuntimeSourceIdentity(commit="e" * 40, tree="f" * 40)
    monkeypatch.setattr(runtime_install, "wheel_source_identity", lambda _wheel: identity)
    monkeypatch.setattr(
        runtime_install.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "failed"),
    )
    with pytest.raises(ValueError, match="hook_runtime_python_abi_invalid"):
        runtime_install.materialize_hook_runtime(
            tmp_path,
            tmp_path / "missing-python",
            expected_source=identity,
        )


def test_hook_install_materializes_a_common_dir_package_runtime(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    checkout_python = tmp_path / "stale-checkout" / ".venv" / "bin" / "python"
    checkout_python.parent.mkdir(parents=True)
    checkout_python.symlink_to(Path(sys.executable))

    report = install_hook_launchers(repo, python=checkout_python)
    common_runtime = Path(git_common_dir(repo)) / "ethos" / "runtime"

    assert Path(str(report["python"])).is_relative_to(common_runtime)
    manifest = Path(str(report["runtime_manifest_path"]))
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["runtime_digest"] == report["runtime_digest"]
    assert payload["wheel_sha256"] == report["wheel_sha256"]
    assert len(payload["wheel_sha256"]) == 64
    assert report["scripts"] == ["pre-commit", "pre-push", "reference-transaction"]
    assert report["required_gaps"] == []
    console_script = Path(str(report["python"])).with_name(
        "ethos.exe" if sys.platform == "win32" else "ethos"
    )
    version = subprocess.run(
        (console_script, "--version"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert version.returncode == 0, version.stderr
    assert version.stdout.strip()
    for name in report["scripts"]:
        text = (Path(str(report["hooks_path"])) / name).read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh\n")
        assert checkout_python.as_posix() not in text
        assert 'exec "$HOOK_DIR/../../runtime/' in text


@pytest.mark.parametrize("kind", ["file", "symlink"])
def test_hook_install_retires_the_legacy_runtime_python_locator(tmp_path: Path, kind: str) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
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


def test_hook_generations_are_content_addressed_and_immutable(tmp_path: Path) -> None:
    root = tmp_path / "ethos" / "hooks"
    locator = "../../runtime/" + "a" * 64 + "/venv/bin/python"

    generation = runtime_install.materialize_hook_launchers(root, locator)
    inode = generation.stat().st_ino
    repeated = runtime_install.materialize_hook_launchers(root, locator)

    assert repeated == generation
    assert repeated.stat().st_ino == inode
    assert generation.parent == root
    assert len(generation.name) == 64
    assert {path.name for path in generation.iterdir()} == set(HOOK_NAMES)
    assert all(
        (generation / name).read_text(encoding="utf-8") == hook_launcher(locator, name)
        for name in HOOK_NAMES
    )


def test_hook_generation_failure_never_mutates_an_existing_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "ethos" / "hooks"
    old = runtime_install.materialize_hook_launchers(
        root, "../../runtime/" + "a" * 64 + "/venv/bin/python"
    )
    before = {path.name: path.read_bytes() for path in old.iterdir()}
    write_text = Path.write_text

    def fail_pre_push(path: Path, data: str, **kwargs: object) -> int:
        if path.name == "pre-push" and path.parent.name.startswith(".generation-"):
            message = "staging failed"
            raise OSError(message)
        return write_text(path, data, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_pre_push)

    with pytest.raises(OSError, match="staging failed"):
        runtime_install.materialize_hook_launchers(
            root, "../../runtime/" + "b" * 64 + "/venv/bin/python"
        )

    assert {path.name: path.read_bytes() for path in old.iterdir()} == before
    assert {path.name for path in root.iterdir()} == {old.name}


def test_hook_binding_follows_the_exact_configured_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    generation = runtime_install.materialize_hook_launchers(
        common / "ethos" / "hooks", runtime_locator(venv)
    )
    assert _git(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        _git(repo, "config", "--worktree", "core.hooksPath", generation.as_posix()).returncode == 0
    )

    observed = hook_runtime_binding(repo)

    assert observed["hooks_path"] == generation.as_posix()
    assert observed["required_gaps"] == []


def test_hook_install_converges_every_linked_worktree_on_one_common_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, linked, _venv, generations = _linked_runtime_case(tmp_path, monkeypatch)
    root_stale = runtime_install.materialize_hook_launchers(
        generations,
        "../../runtime/" + "a" * 64 + "/venv/bin/python",
    )
    linked_stale = runtime_install.materialize_hook_launchers(
        generations,
        "../../runtime/" + "b" * 64 + "/venv/bin/python",
    )
    assert _git(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        _git(repo, "config", "--worktree", "core.hooksPath", root_stale.as_posix()).returncode == 0
    )
    assert _git(repo, "config", "--worktree", "gc.packRefs", "true").returncode == 0
    assert (
        _git(
            linked,
            "config",
            "--worktree",
            "core.hooksPath",
            linked_stale.as_posix(),
        ).returncode
        == 0
    )
    assert _git(linked, "config", "--worktree", "gc.packRefs", "true").returncode == 0

    installed = install_hook_launchers(linked)

    expected = installed["hooks_path"]
    assert installed["linked_worktrees"] == [
        {"path": repo.as_posix(), "state": "repaired"},
        {"path": linked.as_posix(), "state": "repaired"},
    ]
    assert (
        _git(repo, "config", "--local", "--path", "--get", "core.hooksPath").stdout.strip()
        == expected
    )
    assert _git(repo, "config", "--local", "--get", "gc.packRefs").stdout.strip() == "false"
    for worktree in (repo, linked):
        assert (
            _git(worktree, "config", "--path", "--get", "core.hooksPath").stdout.strip() == expected
        )
        assert _git(worktree, "config", "--get", "gc.packRefs").stdout.strip() == "false"
        assert _git(worktree, "config", "--worktree", "--get", "core.hooksPath").returncode == 1
        assert _git(worktree, "config", "--worktree", "--get", "gc.packRefs").returncode == 1
        assert hook_runtime_binding(worktree)["required_gaps"] == []


def test_hook_install_uses_one_source_identity_for_historical_linked_worktrees(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, linked, venv, _generations = _linked_runtime_case(tmp_path, monkeypatch)
    accepted_identity = runtime_source_identity(Path(__file__).resolve().parents[3])
    source_selections: list[Path] = []
    materialized_with: list[runtime_install.RuntimeSourceIdentity] = []
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
        expected_source: runtime_install.RuntimeSourceIdentity,
    ) -> Path:
        materialized_with.append(expected_source)
        return venv

    monkeypatch.setattr(hook_activation, "expected_runtime_source", select_source)
    monkeypatch.setattr(runtime_install, "materialize_hook_runtime", materialize)

    installed = install_hook_launchers(repo)

    assert source_selections == [repo]
    assert materialized_with == [accepted_identity]
    assert installed["expected_source_commit"] == accepted_identity.commit
    assert installed["expected_source_tree"] == accepted_identity.tree
    assert installed["required_gaps"] == []


def test_hook_install_removes_only_unreferenced_generated_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runtime_install,
        "materialize_hook_runtime",
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
    retained_hooks = runtime_install.materialize_hook_launchers(
        hooks_root,
        f"../../runtime/{retained_digest}/venv/bin/python",
    )
    removed_hooks = runtime_install.materialize_hook_launchers(
        hooks_root,
        f"../../runtime/{removed_digest}/venv/bin/python",
    )
    operations = common / "ethos" / "operations"
    operations.mkdir()
    (operations / "consumer.json").write_text(
        json.dumps({"runtime": retained_runtime.as_posix()}),
        encoding="utf-8",
    )

    installed = install_hook_launchers(repo)

    cleanup = installed["generation_cleanup"]
    assert cleanup["removed"] == sorted(
        [retained_hooks.as_posix(), removed_hooks.as_posix(), removed_runtime.as_posix()]
    )
    assert retained_runtime.as_posix() in cleanup["retained"]
    assert retained_hooks.as_posix() not in cleanup["retained"]
    assert not removed_hooks.exists()
    assert not removed_runtime.exists()
    assert retained_runtime.is_dir()
    assert not retained_hooks.exists()


def test_hook_install_blocks_cleanup_when_an_active_consumer_is_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runtime_install,
        "materialize_hook_runtime",
        lambda *_args, **_kwargs: venv,
    )
    common = Path(git_common_dir(repo))
    hooks_root = common / "ethos" / "hooks"
    stale = runtime_install.materialize_hook_launchers(
        hooks_root,
        "../../runtime/" + "a" * 64 + "/venv/bin/python",
    )
    operations = common / "ethos" / "operations"
    operations.mkdir()
    (operations / "unknown").symlink_to(tmp_path / "missing-consumer")

    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        install_hook_launchers(repo)

    assert stale.is_dir()


def test_hook_install_retires_unreferenced_legacy_hook_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runtime_install,
        "materialize_hook_runtime",
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


def test_hook_install_rolls_back_when_linked_worktree_config_is_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, linked, _venv, hooks_root = _linked_runtime_case(tmp_path, monkeypatch)
    stale = runtime_install.materialize_hook_launchers(
        hooks_root,
        "../../runtime/" + "a" * 64 + "/venv/bin/python",
    )
    assert _git(repo, "config", "--local", "core.hooksPath", stale.as_posix()).returncode == 0
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
        _git(repo, "config", "--local", "--path", "--get", "core.hooksPath").stdout.strip()
        == stale.as_posix()
    )
    assert stale.is_dir()


def test_hook_binding_rejects_a_configured_path_outside_the_common_generation_root(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    external = tmp_path / "external-hooks"
    external.mkdir()
    assert _git(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert _git(repo, "config", "--worktree", "core.hooksPath", external.as_posix()).returncode == 0

    observed = hook_runtime_binding(repo)

    assert observed["hooks_path"] == external.as_posix()
    assert "write_admission_not_armed:core.hooksPath" in observed["required_gaps"]


@pytest.mark.parametrize("configured_form", ["absolute", "relative"])
def test_hook_binding_rejects_a_symlinked_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured_form: str
) -> None:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    generation = runtime_install.materialize_hook_launchers(
        common / "ethos" / "hooks", runtime_locator(venv)
    )
    alias = generation.with_name("f" * 64)
    alias.symlink_to(generation, target_is_directory=True)
    assert _git(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    configured = (
        alias.relative_to(repo).as_posix() if configured_form == "relative" else alias.as_posix()
    )
    assert _git(repo, "config", "--worktree", "core.hooksPath", configured).returncode == 0

    observed = hook_runtime_binding(repo)

    assert "write_admission_not_armed:core.hooksPath" in observed["required_gaps"]


def test_hook_binding_rejects_a_symlinked_generation_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    real = common / "external-hooks"
    root = common / "ethos" / "hooks"
    real.mkdir()
    root.parent.mkdir(parents=True, exist_ok=True)
    root.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="hook_generation_root_invalid"):
        runtime_install.materialize_hook_launchers(root, runtime_locator(venv))


def test_hook_generation_rejects_a_symlinked_ethos_ancestor(tmp_path: Path) -> None:
    common = tmp_path / "common"
    external = tmp_path / "external"
    common.mkdir()
    external.mkdir()
    (common / "ethos").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="hook_generation_root_invalid"):
        runtime_install.materialize_hook_launchers(
            common / "ethos" / "hooks",
            "../../runtime/" + "a" * 64 + "/venv/bin/python",
        )


def test_hook_runtime_rejects_a_symlinked_ethos_root_before_writing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    common = Path(git_common_dir(repo))
    external = tmp_path / "external"
    external.mkdir()
    (common / "ethos").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="hook_runtime_root_invalid"):
        runtime_install.materialize_hook_runtime(
            repo,
            Path(sys.executable),
            expected_source=expected_runtime_source(repo)[0],
        )

    assert not tuple(external.iterdir())


def test_hook_generation_rejects_an_existing_symlink_target(tmp_path: Path) -> None:
    root = tmp_path / "ethos" / "hooks"
    locator = "../../runtime/" + "a" * 64 + "/venv/bin/python"
    generation = runtime_install.materialize_hook_launchers(root, locator)
    real = generation.with_name("real")
    generation.rename(real)
    generation.symlink_to(real, target_is_directory=True)

    with pytest.raises(ValueError, match="hook_launcher_projection_invalid"):
        runtime_install.materialize_hook_launchers(root, locator)


def test_hook_binding_reports_non_utf8_launcher_as_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, venv = _materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    generation = runtime_install.materialize_hook_launchers(
        common / "ethos" / "hooks", runtime_locator(venv)
    )
    assert _git(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        _git(repo, "config", "--worktree", "core.hooksPath", generation.as_posix()).returncode == 0
    )
    (generation / "pre-push").write_bytes(b"\xff")

    observed = hook_runtime_binding(repo)

    assert "write_admission_not_armed:pre-push_launcher_drift" in observed["required_gaps"]


def test_hook_activation_failure_keeps_the_old_generation_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, linked, _venv, root = _linked_runtime_case(tmp_path, monkeypatch)
    old_common = runtime_install.materialize_hook_launchers(
        root, "../../runtime/" + "a" * 64 + "/venv/bin/python"
    )
    old_root = runtime_install.materialize_hook_launchers(
        root, "../../runtime/" + "b" * 64 + "/venv/bin/python"
    )
    old_linked = runtime_install.materialize_hook_launchers(
        root, "../../runtime/" + "c" * 64 + "/venv/bin/python"
    )
    assert _git(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert _git(repo, "config", "--local", "core.hooksPath", old_common.as_posix()).returncode == 0
    assert _git(repo, "config", "--local", "gc.packRefs", "true").returncode == 0
    assert _git(repo, "config", "--worktree", "core.hooksPath", old_root.as_posix()).returncode == 0
    assert _git(repo, "config", "--worktree", "gc.packRefs", "true").returncode == 0
    assert (
        _git(linked, "config", "--worktree", "core.hooksPath", old_linked.as_posix()).returncode
        == 0
    )
    assert _git(linked, "config", "--worktree", "gc.packRefs", "true").returncode == 0
    fake_venv = Path(git_common_dir(repo)) / "ethos" / "runtime" / ("d" * 64) / "venv"
    monkeypatch.setattr(
        runtime_install,
        "materialize_hook_runtime",
        lambda *_args, **_kwargs: fake_venv,
    )
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
        _git(repo, "config", "--local", "--path", "--get", "core.hooksPath").stdout.strip()
        == old_common.as_posix()
    )
    assert _git(repo, "config", "--local", "--get", "gc.packRefs").stdout.strip() == "true"
    assert (
        _git(repo, "config", "--worktree", "--path", "--get", "core.hooksPath").stdout.strip()
        == old_root.as_posix()
    )
    assert _git(repo, "config", "--worktree", "--get", "gc.packRefs").stdout.strip() == "true"
    assert (
        _git(linked, "config", "--worktree", "--path", "--get", "core.hooksPath").stdout.strip()
        == old_linked.as_posix()
    )
    assert _git(linked, "config", "--worktree", "--get", "gc.packRefs").stdout.strip() == "true"
    assert {old_common, old_root, old_linked} <= set(root.iterdir())


def test_hook_activation_rejects_a_non_current_post_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    runtime = Path(git_common_dir(repo)) / "ethos/runtime" / ("a" * 64) / "venv"
    runtime.mkdir(parents=True)
    hooks = Path(git_common_dir(repo)) / "ethos/hooks" / ("b" * 64)
    hooks.mkdir(parents=True)
    monkeypatch.setattr(
        runtime_install,
        "materialize_hook_runtime",
        lambda *_args, **_kwargs: runtime,
    )
    monkeypatch.setattr(runtime_install, "materialize_hook_launchers", lambda *_args: hooks)
    monkeypatch.setattr(
        hook_runtime,
        "hook_runtime_binding",
        lambda _root: {
            "hooks_path": hooks.as_posix(),
            "required_gaps": ["write_admission_not_armed:runtime_source_stale"],
        },
    )

    with pytest.raises(ValueError, match="hook_runtime_activation_invalid"):
        install_hook_launchers(repo)


def test_hook_launcher_uses_a_validated_git_for_windows_sh_runtime() -> None:
    """Git-for-Windows invokes hooks through sh; this is not a PowerShell launcher."""
    runtime = "../../runtime/" + "a" * 64 + "/venv/Scripts/python.exe"

    text = hook_launcher(runtime, "pre-commit")

    assert 'HOOK_DIR=${0%/*}; [ "$HOOK_DIR" = "$0" ] && HOOK_DIR=.' in text
    assert 'HOOK_DIR=$(CDPATH= cd "$HOOK_DIR" && pwd)' in text
    assert f'exec "$HOOK_DIR/{runtime}" -I -m ethos.cli hook run pre-commit' in text
    assert len(text.splitlines()) == 5


def test_hook_runtime_observation_rejects_launcher_drift(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    report = install_hook_launchers(repo)
    launcher = Path(str(report["hooks_path"])) / "pre-push"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    observed = hook_runtime_binding(repo)

    assert observed["required_gaps"] == ["write_admission_not_armed:pre-push_launcher_drift"]


def test_pre_commit_skips_unselected_staged_secret_capability(monkeypatch, tmp_path: Path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    readme = fixture.worktree / "README.md"
    readme.write_text("# governed work lane\n", encoding="utf-8")
    assert _git(fixture.worktree, "add", "README.md").returncode == 0

    commit = _git(fixture.worktree, "commit", "-m", "change without secret policy")

    assert commit.returncode == 0, commit.stderr


@pytest.mark.parametrize(
    ("name", "arguments", "stdin", "expected", "gap"),
    [
        ("pre-commit", (), "", 0, ""),
        ("pre-push", ("origin",), "invalid\n", 1, "push_update_invalid"),
        ("pre-push", ("origin",), f"refs/heads/x {'0' * 40} refs/heads/x {'a' * 40}\n", 0, ""),
        ("reference-transaction", ("unknown",), "", 0, ""),
        ("reference-transaction", ("prepared",), "invalid\n", 1, "ref_update_invalid"),
        (
            "reference-transaction",
            ("prepared",),
            f"{'a' * 40} {'b' * 40} refs/tags/v1\n",
            0,
            "",
        ),
    ],
)
def test_hook_runtime_public_input_matrix(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    name: hook_runtime.HookName,
    arguments: tuple[str, ...],
    stdin: str,
    expected: int,
    gap: str,
) -> None:
    """Every Git protocol envelope either dispatches once or fails closed."""
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0

    result = execute_hook(repo, name, arguments, stdin=StringIO(stdin))

    assert result == expected
    error = capsys.readouterr().err
    assert (gap in error) if gap else not error


@pytest.mark.parametrize(
    ("capability", "gap"),
    [
        ("secrets", "staged_secret_gitleaks_missing"),
        ("format", "pre_commit_python_format_failed"),
    ],
)
def test_pre_commit_fails_closed_when_a_selected_capability_cannot_prove_clean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    capability: str,
    gap: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    staged = repo / "change.py"
    staged.write_text("VALUE=1\n", encoding="utf-8")
    assert _git(repo, "add", "change.py").returncode == 0
    if capability == "secrets":
        (repo / ".gitleaks.toml").write_text("title = 'policy'\n", encoding="utf-8")
        which = hook_runtime.shutil.which
        monkeypatch.setattr(
            hook_runtime.shutil,
            "which",
            lambda name, **kwargs: None if name == "gitleaks" else which(name, **kwargs),
        )
    else:
        (repo / "ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
        monkeypatch.setattr(
            hook_runtime,
            "run_command",
            lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "format drift"),
        )

    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 1
    assert gap in capsys.readouterr().err


def test_pre_push_binds_named_remote_and_observed_remote_head(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        hook_runtime,
        "push_admission_report",
        lambda **kwargs: (
            calls.append(kwargs) or {"verdict": "pass", "state": "admitted", "required_gaps": []}
        ),
    )
    update = f"refs/heads/dev {'a' * 40} refs/heads/dev {'b' * 40}\n"

    assert execute_hook(tmp_path, "pre-push", ("github",), stdin=StringIO(update)) == 0

    assert calls[0]["remote_name"] == "github"
    assert calls[0]["remote_head"] == "b" * 40
    assert "reconciliation" not in calls[0]


@pytest.mark.parametrize(
    ("branch", "phase", "decision", "expected", "state"),
    [
        ("work/change", "prepared", "allow", 0, "work-prepared"),
        ("topic", "prepared", "allow", 0, "unprotected_ref"),
        ("topic", "prepared", "block", 1, "topic-blocked"),
        ("topic", "aborted", "block", 0, "aborted_observed"),
        ("topic", "committed", "allow", 0, "topic-committed"),
    ],
)
def test_reference_transaction_dispatch_preserves_role_and_phase_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    branch: str,
    phase: str,
    decision: str,
    expected: int,
    state: str,
) -> None:
    policy = BranchRolePolicy()
    monkeypatch.setattr(hook_runtime, "resolve_ref_move_policy", lambda *_args: policy)
    monkeypatch.setattr(
        hook_runtime,
        "work_lane_ref_transition_report",
        lambda **_kwargs: {"verdict": "pass", "state": "work-prepared", "required_gaps": []},
    )
    monkeypatch.setattr(
        hook_runtime,
        "ref_move_admission_report",
        lambda **_kwargs: {
            "verdict": "block" if decision == "block" else "pass",
            "state": f"topic-{phase}" if decision == "allow" else "topic-blocked",
            "decision": {"action": decision},
            "required_gaps": ["raw_ref_blocked"] if decision == "block" else [],
        },
    )
    update = f"{'a' * 40} {'b' * 40} refs/heads/{branch}\n"

    result = execute_hook(
        tmp_path,
        "reference-transaction",
        (phase,),
        stdin=StringIO(update),
    )

    assert result == expected
    error = capsys.readouterr().err
    if expected:
        assert state in error
    else:
        assert not error


@pytest.mark.parametrize(
    ("runner", "stdout", "gap"),
    [
        ("missing", "", "candidate_semantic_runner_unavailable"),
        ("invalid-json", "not-json", "candidate_semantic_runner_invalid"),
        ("invalid-envelope", "{}", "candidate_semantic_runner_invalid"),
        ("pass", '{"data":{"verdict":"pass","state":"admitted","required_gaps":[]}}', ""),
    ],
)
def test_candidate_transition_requires_one_bound_semantic_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    runner: str,
    stdout: str,
    gap: str,
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    python = candidate / "runtime-python"
    python.write_text("runtime", encoding="utf-8")
    policy = BranchRolePolicy()
    monkeypatch.setattr(hook_runtime, "resolve_ref_move_policy", lambda *_args: policy)
    monkeypatch.setattr(
        hook_runtime,
        "worktree_records",
        lambda *_args, **_kwargs: (
            []
            if runner == "missing"
            else [{"branch": policy.candidate_branch, "path": candidate, "head": "b" * 40}]
        ),
    )
    monkeypatch.setattr(
        hook_runtime,
        "hook_runtime_binding",
        lambda _root: {"required_gaps": [], "python": python.as_posix()},
    )
    monkeypatch.setattr(
        hook_runtime,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )
    monkeypatch.setattr(
        hook_runtime,
        "run_command",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout, ""),
    )
    update = f"{'a' * 40} {'b' * 40} refs/heads/dev\n"

    result = execute_hook(
        tmp_path,
        "reference-transaction",
        ("prepared",),
        stdin=StringIO(update),
    )

    assert result == (1 if gap else 0)
    error = capsys.readouterr().err
    assert (gap in error) if gap else not error


def test_governed_repository_git_reads_real_hook_configuration(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    git(repository, "init", "-b", "dev")
    git(repository, "config", "core.hooksPath", ".githooks")

    assert git(repository, "config", "--get", "core.hooksPath") == ".githooks"


def test_repository_does_not_track_host_specific_hook_launchers() -> None:
    root = Path(__file__).resolve().parents[3]

    assert _git(root, "ls-files", ".githooks").stdout == ""
