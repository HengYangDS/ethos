"""Locked supply is complete, and each declared tool's executable comes from that tool."""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.toolchain.mise as mise

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

# The installs are POSIX executables; the refusal logic itself is platform-neutral.
pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX executable installs")

GRAPH_LOCK = """[[tools.npm]]
version = "12.2.1"
aube = { path = "locks/npm/12.2.1", digest = "sha256:00" }
backend = "npm:npm"
"""


def _install(tmp_path: Path, tool: str, *executables: str) -> Path:
    path = tmp_path / "installs" / tool
    (path / "bin").mkdir(parents=True)
    for name in executables:
        executable = path / "bin" / name
        executable.write_text("#!/bin/sh\n", encoding="utf-8")
        executable.chmod(0o755)
    return path


def _row(path: Path, version: str, *, installed: bool = True) -> list[dict[str, object]]:
    return [
        {
            "version": version,
            "requested_version": version,
            "installed": installed,
            "active": True,
            "install_path": str(path),
            "source": "mise.toml",
        }
    ]


class _Mise:
    """Answer one resolution's native queries from a fixed supply."""

    def __init__(
        self, rows: Mapping[str, object], which: Path, bin_paths: tuple[Path, ...]
    ) -> None:
        self.rows = rows
        self.which = which
        self.bin_paths = bin_paths

    def __call__(
        self,
        _root: Path,
        arguments: tuple[str, ...],
        *,
        files: object = None,
        offline: bool,
        executable: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del files, executable
        assert offline is True
        answers = {
            ("ls", "--current", "--json"): json.dumps(self.rows),
            ("env", "--json"): "{}",
            ("bin-paths",): "\n".join(str(path) for path in self.bin_paths),
        }
        output = f"{self.which}\n" if arguments[0] == "which" else answers[arguments]
        return subprocess.CompletedProcess(arguments, 0, output, "")


@pytest.fixture
def supply(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Node with its bundled npm and a locked npm, as aigw-cli declares them."""
    node = _install(tmp_path, "node/26.13.0", "node", "npm")
    npm = _install(tmp_path, "npm/12.2.1", "npm")
    selected = tmp_path / "mise"
    selected.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(mise, "mise_executable", lambda: selected)
    monkeypatch.setattr(mise, "_root_trusted", lambda _root, _executable: True)
    monkeypatch.setattr(mise, "_mise_version", lambda _executable: (2026, 10, 25), raising=False)
    return {"node": node, "npm": npm}


def _files(lock: str = "lock") -> dict[str, str]:
    return {mise.MISE_CONFIG: "[settings]\n", mise.MISE_LOCK: lock}


def _resolve(root: Path, *, environment: bool, lock: str = "lock") -> None:
    if not environment:
        mise.locked_tool(root, "npm", files=_files(lock))
        return
    with mise.locked_environment(root, _files(lock)):
        pass


@pytest.mark.parametrize("environment", [False, True])
@pytest.mark.parametrize("missing", ["not-installed", "absent-path"])
def test_a_missing_declared_tool_refuses_its_locked_supply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    supply: dict[str, Path],
    *,
    environment: bool,
    missing: str,
) -> None:
    """A locked npm that mise lists as missing never yields Node's bundled npm in its place."""
    npm = supply["npm"] if missing == "not-installed" else tmp_path / "installs/npm/absent"
    rows = {"node": _row(supply["node"], "26.13.0"), "npm": _row(npm, "12.2.1", installed=False)}
    if missing == "absent-path":
        rows["npm"] = _row(npm, "12.2.1")
    bundled = supply["node"] / "bin/npm"
    monkeypatch.setattr(mise, "run_mise", _Mise(rows, bundled, (supply["node"] / "bin",)))

    with pytest.raises(ValueError, match=r"mise_supply_incomplete:npm@12\.2\.1"):
        _resolve(tmp_path, environment=environment)


@pytest.mark.parametrize("environment", [False, True])
def test_an_executable_outside_its_own_tool_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, supply: dict[str, Path], *, environment: bool
) -> None:
    """An installed locked npm still loses if Node's bundled npm is the one that resolves."""
    rows = {"node": _row(supply["node"], "26.13.0"), "npm": _row(supply["npm"], "12.2.1")}
    paths = (supply["node"] / "bin", supply["npm"] / "bin")
    monkeypatch.setattr(mise, "run_mise", _Mise(rows, supply["node"] / "bin/npm", paths))

    with pytest.raises(ValueError, match="mise_executable_outside_tool:npm"):
        _resolve(tmp_path, environment=environment)


def test_a_complete_supply_resolves_an_undeclared_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, supply: dict[str, Path]
) -> None:
    """Where only node is declared, its bundled npm is the native selection."""
    bundled = supply["node"] / "bin/npm"
    rows = {"node": _row(supply["node"], "26.13.0")}
    monkeypatch.setattr(mise, "run_mise", _Mise(rows, bundled, (supply["node"] / "bin",)))

    assert mise.locked_tool(tmp_path, "npm", files=_files()) == bundled
    with mise.locked_environment(tmp_path, _files()) as selected:
        assert str(supply["node"] / "bin") in selected["PATH"]


@pytest.mark.parametrize(
    ("version", "trusted", "expected", "absent"),
    [
        ((2026, 11, 0), False, "jdx/mise/issues/15363", "trust"),
        ((2026, 10, 25), False, "trust", "install --locked"),
        ((2026, 10, 25), True, "install --locked", "trust"),
    ],
)
def test_the_refusal_names_the_action_that_can_help(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    supply: dict[str, Path],
    *,
    version: tuple[int, ...],
    trusted: bool,
    expected: str,
    absent: str,
) -> None:
    """The regression, trust and installation each fix a different missing supply."""
    rows = {
        "node": _row(supply["node"], "26.13.0"),
        "npm": _row(supply["npm"], "12.2.1", installed=False),
    }
    monkeypatch.setattr(mise, "run_mise", _Mise(rows, supply["node"] / "bin/npm", ()))
    monkeypatch.setattr(mise, "_root_trusted", lambda _root, _executable: trusted)
    monkeypatch.setattr(mise, "_mise_version", lambda _executable: version, raising=False)

    with pytest.raises(ValueError, match="mise_supply_incomplete") as refused:
        _resolve(tmp_path, environment=False, lock=GRAPH_LOCK)

    assert expected in str(refused.value)
    assert absent not in str(refused.value).split(";", 1)[1]
