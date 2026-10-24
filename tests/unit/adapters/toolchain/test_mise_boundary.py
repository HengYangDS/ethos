"""Qualify the native mise boundary: disposable resolution state and native execution policy."""

from __future__ import annotations

import os
import shutil
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

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
    """Observe the state mise would keep for the host, with no caller-selected policy."""
    state = tmp_path_factory.mktemp("host-state")
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.delenv("MISE_STATE_DIR", raising=False)
    monkeypatch.delenv("MISE_SAFE", raising=False)
    return state


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
    node = mise.locked_tool(tmp_path, "node", files=files)
    with mise.locked_environment(tmp_path, files) as environment:
        selected = shutil.which("node", path=environment["PATH"])
    assert selected is not None
    assert Path(selected).resolve() == node.resolve()
    assert not (tmp_path / "forbidden-task").exists()
    assert sorted(path.name for path in host_mise_state.iterdir()) == []


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
