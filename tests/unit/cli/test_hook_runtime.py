"""Portable Git-hook launcher and runtime-provenance contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib import import_module
from io import StringIO
from pathlib import Path

import pytest

import ethos.adapters.repo.hook_runtime as hook_runtime
import ethos.adapters.repo.hook_runtime_install as runtime_install
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.hook.binding import runtime_locator
from ethos.adapters.repo.hook_runtime import execute_hook
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.contracts.branch.roles import BranchRolePolicy
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


def _materialize_runtime_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
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
    return repo, runtime_install.materialize_hook_runtime(repo, source_python)


@pytest.mark.parametrize(
    "drift",
    ["manifest", "digest", "wheel", "abi", "platform", "files", "python", "hash"],
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
            "files": "runtime_files",
        }[drift]
        payload[key] = {} if drift == "files" else "drift"
        manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        runtime_install.materialize_hook_runtime(repo, Path(sys.executable))


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


def test_source_hook_runtime_installs_the_locked_dependency_closure_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    source = tmp_path / "source"
    module = source / "a" / "b" / "c" / "d" / "module.py"
    module.parent.mkdir(parents=True)
    (source / "pyproject.toml").touch()
    (source / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    wheel = tmp_path / "ethos-test.whl"
    wheel.write_bytes(b"wheel")
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(runtime_install, "__file__", module.as_posix())
    monkeypatch.setattr(runtime_install, "resolve_runtime_wheel", lambda *_args: wheel)
    monkeypatch.setattr(runtime_install, "_python_abi", lambda _python: "cpython-test")

    def run_runtime_tool(_source: Path, *args: str) -> None:
        calls.append(args)
        if args[0] == "venv":
            _venv_executable(Path(args[-1]), "python").parent.mkdir(parents=True)

    monkeypatch.setattr(runtime_install, "_run_runtime_tool", run_runtime_tool)
    monkeypatch.setattr(runtime_install, "write_runtime_manifest", lambda *_args: None)
    monkeypatch.setattr(runtime_install, "finalize_runtime", lambda *_args: None)
    monkeypatch.setattr(runtime_install, "require_runtime", lambda *_args: None)

    runtime_install.materialize_hook_runtime(repo, Path(sys.executable))

    assert [call[0] for call in calls] == ["venv", "export", "pip", "pip"]
    export = calls[1]
    assert export[1:6] == ("--locked", "--offline", "--no-dev", "--no-emit-project", "--format")
    assert export[6] == "requirements-txt"
    requirements = Path(export[export.index("--output-file") + 1])
    assert calls[2] == (
        "pip",
        "install",
        "--offline",
        "--python",
        calls[0][-1] + ("/Scripts/python.exe" if os.name == "nt" else "/bin/python"),
        "--requirements",
        requirements.as_posix(),
    )
    assert calls[3][0:4] == ("pip", "install", "--offline", "--no-deps")
    installed_wheel = Path(calls[3][-1])
    assert installed_wheel.name == wheel.name
    assert installed_wheel.read_bytes() == wheel.read_bytes()


def test_hook_runtime_python_and_manifest_require_executable_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _git(tmp_path, "init", "--quiet", "--initial-branch=dev").returncode == 0
    monkeypatch.setattr(
        runtime_install.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "failed"),
    )
    with pytest.raises(ValueError, match="hook_runtime_python_abi_invalid"):
        runtime_install.materialize_hook_runtime(tmp_path, tmp_path / "missing-python")


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
        runtime_install.materialize_hook_runtime(repo, Path(sys.executable))

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
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    root = Path(git_common_dir(repo)) / "ethos" / "hooks"
    old = runtime_install.materialize_hook_launchers(
        root, "../../runtime/" + "a" * 64 + "/venv/bin/python"
    )
    assert _git(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert _git(repo, "config", "--worktree", "core.hooksPath", old.as_posix()).returncode == 0
    fake_venv = Path(git_common_dir(repo)) / "ethos" / "runtime" / ("b" * 64) / "venv"
    monkeypatch.setattr(hook_runtime, "materialize_hook_runtime", lambda *_args: fake_venv)
    real_set = hook_runtime.set_worktree_config

    def fail_activation(root_path: Path, values: dict[str, str]) -> None:
        if "core.hooksPath" in values:
            message = "activation failed"
            raise ValueError(message)
        real_set(root_path, values)

    monkeypatch.setattr(hook_runtime, "set_worktree_config", fail_activation)

    with pytest.raises(ValueError, match="activation failed"):
        install_hook_launchers(repo)

    assert (
        _git(repo, "config", "--path", "--get", "core.hooksPath").stdout.strip() == old.as_posix()
    )
    assert old.is_dir()
    assert len(tuple(root.iterdir())) == 2


def test_hook_install_runs_from_an_isolated_wheel_without_checkout(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    uv = Path(sys.executable).with_name("uv.exe" if os.name == "nt" else "uv")
    node_root = Path(import_module("nodejs_wheel").__file__).resolve().parent
    environment = {
        **os.environ,
        "ETHOS_BUILD_NODE": (
            node_root / "bin" / ("node.exe" if os.name == "nt" else "node")
        ).as_posix(),
        "ETHOS_BUILD_NPM_CLI": (node_root / "lib/node_modules/npm/bin/npm-cli.js").as_posix(),
    }
    environment.pop("PYTHONPATH", None)
    dist = tmp_path / "dist"
    subprocess.run(
        (uv, "build", "--offline", "--wheel", "--out-dir", dist),
        cwd=root,
        env=environment,
        check=True,
    )
    wheel = next(dist.glob("ethos-*.whl"))
    package_venv = tmp_path / "package-venv"
    subprocess.run(
        (uv, "venv", "--relocatable", "--python", sys.executable, package_venv),
        check=True,
    )
    package_python = _venv_executable(package_venv, "python")
    requirements = tmp_path / "locked-requirements.txt"
    subprocess.run(
        (
            uv,
            "export",
            "--locked",
            "--offline",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            requirements,
        ),
        cwd=root,
        env=environment,
        check=True,
    )
    subprocess.run(
        (
            uv,
            "pip",
            "install",
            "--offline",
            "--python",
            package_python,
            "--requirements",
            requirements,
        ),
        check=True,
    )
    subprocess.run(
        (uv, "pip", "install", "--offline", "--no-deps", "--python", package_python, wheel),
        check=True,
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0

    installed = subprocess.run(
        (_venv_executable(package_venv, "ethos"), "hook", "install", "--root", repo, "--json"),
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert installed.returncode == 0, installed.stderr
    report = json.loads(installed.stdout)
    assert report["verdict"] == "pass", report
    runtime_python = Path(report["data"]["python"])
    package_venv.rename(tmp_path / "retired-package-venv")
    runtime_ethos = _venv_executable(runtime_python.parent.parent, "ethos")
    rebind_help = subprocess.run(
        (runtime_ethos, "lane", "rebind-commitment", "--help"),
        capture_output=True,
        text=True,
        check=False,
        env={key: value for key, value in environment.items() if key != "PYTHONPATH"},
    )
    derive_help = subprocess.run(
        (runtime_ethos, "lane", "rebind-commitment", "derive", "--help"),
        capture_output=True,
        text=True,
        check=False,
        env={key: value for key, value in environment.items() if key != "PYTHONPATH"},
    )
    assert rebind_help.returncode == 0, rebind_help.stderr
    assert "--receipt" in rebind_help.stdout
    assert derive_help.returncode == 0, derive_help.stderr
    assert "--target-commit" in derive_help.stdout
    version = subprocess.run(
        (runtime_ethos, "--version"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert version.returncode == 0, version.stderr
    assert version.stdout.strip()


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


def test_pre_push_binds_remote_and_reconciliation_observations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setenv("ETHOS_RECONCILIATION_RECEIPT", "/receipt.json")
    monkeypatch.setattr(
        hook_runtime,
        "_remote_head",
        lambda _root, remote, ref: f"{remote}:{ref}",
    )
    monkeypatch.setattr(
        hook_runtime,
        "_declared_peer_heads",
        lambda _root: (
            ("gitlab", "origin:refs/heads/dev", "origin:refs/heads/main"),
            ("github", "github:refs/heads/dev", "github:refs/heads/main"),
        ),
    )
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
    observation = calls[0]["reconciliation"]
    assert observation.receipt_path == "/receipt.json"
    assert observation.peer_heads == (
        ("gitlab", "origin:refs/heads/dev", "origin:refs/heads/main"),
        ("github", "github:refs/heads/dev", "github:refs/heads/main"),
    )


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
