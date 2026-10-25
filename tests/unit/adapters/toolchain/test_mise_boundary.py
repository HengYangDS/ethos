"""Qualify the native mise boundary: disposable resolution state and native execution policy."""

from __future__ import annotations

import json
import os
import shutil
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

import ethos.adapters.toolchain.mise as mise
from ethos.adapters.process import run_command

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable
    from collections.abc import Mapping

# Owned installs are POSIX executables; hosted Windows runs package conformance, not these.
POSIX_INSTALLS = pytest.mark.skipif(os.name != "posix", reason="POSIX executable installs")


@pytest.fixture
def host_mise_state(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Observe the state mise would keep for the host, with no caller-selected policy or trust."""
    state = tmp_path_factory.mktemp("host-state")
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    absent = tmp_path_factory.mktemp("host-config")
    monkeypatch.setenv("MISE_GLOBAL_CONFIG_FILE", str(absent / "config.toml"))
    monkeypatch.setenv("MISE_SYSTEM_CONFIG_DIR", str(absent))
    for name in ("MISE_STATE_DIR", "MISE_SAFE", "MISE_TRUSTED_CONFIG_PATHS", "MISE_PARANOID"):
        monkeypatch.delenv(name, raising=False)
    return state


def _state(root: Path) -> dict[str, str]:
    """Every entry under a mise state directory: directories, file bytes and link targets."""
    return {
        entry.relative_to(root).as_posix(): (
            f"link:{entry.readlink()}"
            if entry.is_symlink()
            else entry.read_text()
            if entry.is_file()
            else "directory"
        )
        for entry in root.rglob("*")
    }


def _initialized_state(root: Path, state: Path) -> dict[str, str]:
    """Let native mise lay out the state that a host using it already has, then observe it."""
    run_command(root, (str(mise.mise_executable()), "trust", "--show"), timeout=30, check=True)
    return _state(state)


def _declared_node() -> str:
    root = Path(__file__).resolve().parents[4]
    return tomllib.loads((root / mise.MISE_CONFIG).read_text())["tools"]["node"]


def _locked_repository(root: Path, declared: str, body: str) -> dict[str, str]:
    """Declare one locked node selection beside the given native configuration."""
    config = root / mise.MISE_CONFIG
    config.parent.mkdir(parents=True)
    config.write_text(f'[tools]\nnode = "{declared}"\n{body}')
    (root / mise.MISE_LOCK).write_text(
        f'lockfile_version = 3\n[[tools.node]]\nversion = "{declared}"\n'
        f'backend = "core:node"\nspecifiers = ["{declared}"]\n'
    )
    files = mise.repository_mise_files(root)
    assert files is not None
    return files


def _execute(
    root: Path, files: Mapping[str, str], *arguments: str
) -> tuple[dict[str, str], subprocess.CompletedProcess[str]]:
    """Run one admitted native mise command the way a gate runs its children."""
    with mise.locked_environment(root, files) as environment:
        selected = shutil.which("mise", path=environment["PATH"])
        assert selected is not None
        observed = run_command(
            root,
            (selected, *arguments),
            timeout=60,
            remove_env_prefixes=("MISE_",),
            env=environment,
        )
    return environment, observed


@POSIX_INSTALLS
def test_native_supply_resolution_leaves_no_host_mise_state(
    tmp_path: Path, mise_installs: Callable[[str, str, str], None], host_mise_state: Path
) -> None:
    """Resolution runs no repository task, and mise's record of what it loaded stays disposable."""
    declared = _declared_node()
    mise_installs("node", declared, f"v{declared}")
    (tmp_path / ".node-version").write_text(f"{declared}\n")
    files = _locked_repository(
        tmp_path,
        declared,
        '[settings]\nidiomatic_version_file_enable_tools = ["node"]\n'
        '[tasks.forbidden]\nrun = "touch forbidden-task"\n',
    )
    assert ".node-version" in files
    before = _initialized_state(tmp_path, host_mise_state)
    node = mise.locked_tool(tmp_path, "node", files=files)
    with mise.locked_environment(tmp_path, files) as environment:
        selected = shutil.which("node", path=environment["PATH"])
    assert selected is not None
    assert Path(selected).resolve() == node.resolve()
    assert not (tmp_path / "forbidden-task").exists()
    assert _state(host_mise_state) == before


@POSIX_INSTALLS
@pytest.mark.parametrize("caller_safe", ["", "1", "true"])
def test_locked_execution_runs_admitted_tasks_under_native_mise_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mise_installs: Callable[[str, str, str], None],
    host_mise_state: Path,
    caller_safe: str,
) -> None:
    """Resolution's safe mode and state stay out of execution; only the caller's own apply."""
    declared = _declared_node()
    mise_installs("node", declared, f"v{declared}")
    caller_state = tmp_path / "caller-state"
    monkeypatch.setenv("MISE_STATE_DIR", str(caller_state))
    if caller_safe:
        monkeypatch.setenv("MISE_SAFE", caller_safe)
    repository = tmp_path / "repository"
    files = _locked_repository(
        repository,
        declared,
        '[tasks.outer]\nrun = "mise run inner"\n[tasks.inner]\nrun = "node --version"\n',
    )
    environment, observed = _execute(repository, files, "run", "outer")
    assert environment["MISE_STATE_DIR"] == str(caller_state)
    if caller_safe:
        assert environment["MISE_SAFE"] == caller_safe
        assert observed.returncode != 0
        assert "safe mode" in observed.stderr
    else:
        assert "MISE_SAFE" not in environment
        assert observed.returncode == 0, observed.stderr
        assert f"v{declared}" in observed.stdout.splitlines()
    assert sorted(path.name for path in host_mise_state.iterdir()) == []


@POSIX_INSTALLS
def test_locked_execution_leaves_trust_to_native_mise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mise_installs: Callable[[str, str, str], None],
    host_mise_state: Path,
) -> None:
    """Untrusted code-running configuration never runs, and ETHOS records no trust for it.

    Outside CI mise refuses such a configuration; in CI it skips the parts that need trust.
    """
    declared = _declared_node()
    mise_installs("node", declared, f"v{declared}")
    caller_state = tmp_path / "caller-state"
    monkeypatch.setenv("MISE_STATE_DIR", str(caller_state))
    repository = tmp_path / "repository"
    files = _locked_repository(
        repository, declared, "[env]\nPROBE = \"{{ exec(command='touch template-ran') }}\"\n"
    )
    _execute(repository, files, "env", "--json")
    assert not (repository / "template-ran").exists()
    trusted = caller_state / "trusted-configs"
    assert not trusted.exists() or not any(trusted.iterdir())
    assert sorted(path.name for path in host_mise_state.iterdir()) == []


def _trust_keyed_repository(root: Path) -> dict[str, str]:
    """Lock one npm tool through an aube entry, which mise honors only for trusted configuration."""
    config = root / mise.MISE_CONFIG
    config.parent.mkdir(parents=True)
    config.write_text('[settings]\nlocked = true\n[tools]\n"npm:ethos-probe" = "1.0.0"\n')
    (root / mise.MISE_LOCK).write_text(
        'lockfile_version = 3\n[[tools."npm:ethos-probe"]]\nversion = "1.0.0"\n'
        f'aube = {{ path = "locks/npm-ethos-probe/1.0.0", digest = "sha256:{"0" * 64}" }}\n'
        'backend = "npm:ethos-probe"\nspecifiers = ["1.0.0"]\n'
    )
    files = mise.repository_mise_files(root)
    assert files is not None
    return files


def _trust_keyed_install(scratch: Path, files: Mapping[str, str]) -> str:
    """Name the install native mise selects for a copy it trusts, without the code under test."""
    for path, content in files.items():
        (scratch / path).parent.mkdir(parents=True, exist_ok=True)
        (scratch / path).write_text(content)
    listed = run_command(
        scratch,
        (str(mise.mise_executable()), "ls", "--json"),
        timeout=30,
        check=True,
        env={
            "MISE_STATE_DIR": str(scratch / "state"),
            "MISE_TRUSTED_CONFIG_PATHS": str(scratch / mise.MISE_CONFIG),
            "MISE_SAFE": "1",
            "MISE_OFFLINE": "1",
            "MISE_CEILING_PATHS": str(scratch.parent),
        },
    )
    return Path(json.loads(listed.stdout)["npm:ethos-probe"][0]["install_path"]).name


@POSIX_INSTALLS
@pytest.mark.parametrize("trust", ["", "record", "environment"])
def test_resolution_carries_only_native_trust_to_its_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mise_installs: Callable[[str, str, str], None],
    host_mise_state: Path,
    trust: str,
) -> None:
    """The caller's own native trust selects a trust-keyed install; nothing records or keeps it."""
    repository = tmp_path / "repository"
    files = _trust_keyed_repository(repository)
    (tmp_path / "scratch").mkdir()
    mise_installs("npm-ethos-probe", _trust_keyed_install(tmp_path / "scratch", files), "aube")
    if trust == "record":
        run_command(repository, (str(mise.mise_executable()), "trust"), timeout=30, check=True)
    elif trust:
        monkeypatch.setenv("MISE_TRUSTED_CONFIG_PATHS", str(repository))
    before = _initialized_state(repository, host_mise_state)
    with patch.object(mise, "run_command", wraps=mise.run_command) as native:
        if trust:
            tool = mise.locked_tool(repository, "npm-ethos-probe", files)
            assert run_command(repository, (str(tool),), timeout=15).stdout.strip() == "aube"
            with mise.locked_environment(repository, files) as environment:
                assert shutil.which("npm-ethos-probe", path=environment["PATH"]) == str(tool)
                assert "MISE_TRUSTED_CONFIG_PATHS" not in environment
        else:
            refusal = r"; next: mise --cd \S+ trust$"
            with pytest.raises(ValueError, match=refusal):
                mise.locked_tool(repository, "npm-ethos-probe", files)
            with (
                pytest.raises(ValueError, match=refusal),
                mise.locked_environment(repository, files),
            ):
                pytest.fail("an untrusted copy selected the trust-keyed install")
    copies = [call for call in native.call_args_list if "MISE_STATE_DIR" in call.kwargs["env"]]
    assert copies
    for call in copies:
        assert call.kwargs["env"]["MISE_SAFE"] == "1"
        assert call.kwargs["env"].get("MISE_TRUSTED_CONFIG_PATHS") == (
            str(call.args[0] / mise.MISE_CONFIG) if trust else None
        )
    assert _state(host_mise_state) == before
