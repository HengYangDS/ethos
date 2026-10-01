"""Qualify fail-closed native Mise selection without ambient-tool fallback."""

from __future__ import annotations

import os
import shutil
import subprocess
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.toolchain.mise as mise

if TYPE_CHECKING:
    from collections.abc import Mapping


@pytest.mark.parametrize("interrupt", [False, True])
@pytest.mark.parametrize("link_mode", ["symlink", "hardlink", "copy"])
def test_locked_environment_exposes_only_selected_mise_during_native_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, interrupt: bool, link_mode: str
) -> None:
    """A nested check can call mise without inheriting sibling operator tools."""
    operator = tmp_path / "operator"
    operator.mkdir()
    suffix = ".exe" if os.name == "nt" else ""
    selected = operator / f"selected-mise{suffix}"
    sibling = operator / f"unrelated{suffix}"
    for executable in (selected, sibling):
        executable.write_bytes(b"selected executable")
        executable.chmod(0o755)
    locked_bin = tmp_path / "locked-bin"
    locked_bin.mkdir()
    locked_go = locked_bin / f"go{suffix}"
    locked_go.write_bytes(b"locked go")
    locked_go.chmod(0o755)
    files = {mise.MISE_CONFIG: "config", mise.MISE_LOCK: "lock"}

    def observe(
        _root: Path,
        arguments: tuple[str, ...],
        *,
        files: Mapping[str, str],
        executable: Path,
        offline: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert offline
        assert files == {mise.MISE_CONFIG: "config", mise.MISE_LOCK: "lock"}
        assert executable == selected
        output = '{"MISE_TEST":"selected"}' if arguments == ("env", "--json") else f"{locked_bin}\n"
        return subprocess.CompletedProcess(arguments, 0, output, "")

    monkeypatch.setattr(mise, "run_mise", observe)
    monkeypatch.setattr(mise, "mise_executable", lambda: selected)
    if link_mode != "symlink":

        def deny_link(*_args: object, **_kwargs: object) -> None:
            raise OSError

        monkeypatch.setattr(Path, "symlink_to", deny_link)
        if link_mode == "copy":
            monkeypatch.setattr(os, "link", deny_link)

    expected = pytest.raises(RuntimeError) if interrupt else nullcontext()
    with expected, mise.locked_environment(tmp_path, files) as environment:
        alias = shutil.which("mise", path=environment["PATH"])
        assert alias is not None
        assert Path(alias).read_bytes() == selected.read_bytes()
        assert shutil.which("go", path=environment["PATH"]) == str(locked_go)
        assert shutil.which("unrelated", path=environment["PATH"]) is None
        assert str(operator) not in environment["PATH"].split(os.pathsep)
        alias_root = Path(alias).parent
        assert environment["MISE_SAFE"] == "1"
        assert environment["MISE_LOCKED"] == "1"
        assert environment["MISE_OFFLINE"] == "1"
        assert environment["MISE_AUTO_INSTALL"] == "0"
        assert environment["MISE_DISABLE_UPDATE_WARNING"] == "1"
        assert Path(environment["MISE_GLOBAL_CONFIG_FILE"]).parent == alias_root
        if interrupt:
            raise RuntimeError
    assert not alias_root.exists()


@pytest.mark.parametrize(
    ("phase", "returncode", "stdout", "stderr", "gap"),
    [
        ("env", 1, "", "failed", "mise_environment_unavailable"),
        ("env", 0, "{}", "warning", "mise_environment_unavailable"),
        ("env", 0, "not-json", "", "mise_environment_invalid"),
        ("env", 0, "[]", "", "mise_environment_invalid"),
        ("env", 0, '{"PATH":2}', "", "mise_environment_invalid"),
        ("bin-paths", 1, "", "failed", "mise_bin_paths_unavailable"),
        ("bin-paths", 0, "", "warning", "mise_bin_paths_unavailable"),
        ("bin-paths", 0, "", "", "mise_bin_paths_invalid"),
        ("bin-paths", 0, "relative\n", "", "mise_bin_paths_invalid"),
    ],
)
def test_locked_environment_rejects_unproved_native_supply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    returncode: int,
    stdout: str,
    stderr: str,
    gap: str,
) -> None:
    """A failed or malformed native response cannot become a usable PATH."""
    files = {mise.MISE_CONFIG: "config", mise.MISE_LOCK: "lock"}
    calls: list[tuple[str, ...]] = []

    def execute(
        _root: Path,
        arguments: tuple[str, ...],
        *,
        files: Mapping[str, str],
        executable: Path,
        offline: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert files == {mise.MISE_CONFIG: "config", mise.MISE_LOCK: "lock"}
        assert executable == tmp_path / "mise"
        assert offline is True
        calls.append(arguments)
        if arguments == ("env", "--json") and phase == "bin-paths":
            return subprocess.CompletedProcess(arguments, 0, '{"PATH":"native"}', "")
        return subprocess.CompletedProcess(arguments, returncode, stdout, stderr)

    monkeypatch.setattr(mise, "run_mise", execute)
    monkeypatch.setattr(mise, "mise_executable", lambda: tmp_path / "mise")

    with pytest.raises(ValueError, match=gap), mise.locked_environment(tmp_path, files):
        pytest.fail("invalid native supply was admitted")
    assert calls == ([("env", "--json")] if phase == "env" else [("env", "--json"), ("bin-paths",)])


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "gap"),
    [
        (1, "", "failed", "mise_supply_unavailable:node"),
        (0, "relative", "", "mise_executable_unavailable:node"),
        (0, "absent", "", "mise_executable_unavailable:node"),
    ],
)
def test_locked_tool_requires_an_installed_absolute_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    stderr: str,
    gap: str,
) -> None:
    """Neither a successful selector exit nor a path string proves a tool exists."""
    files = {mise.MISE_CONFIG: "config", mise.MISE_LOCK: "lock"}

    def select(
        _root: Path, arguments: tuple[str, ...], *, files: Mapping[str, str], offline: bool
    ) -> subprocess.CompletedProcess[str]:
        assert arguments == ("which", "node")
        assert files == {mise.MISE_CONFIG: "config", mise.MISE_LOCK: "lock"}
        assert offline is True
        output = str(tmp_path / "absent-node") if stdout == "absent" else stdout
        return subprocess.CompletedProcess(arguments, returncode, output, stderr)

    monkeypatch.setattr(mise, "run_mise", select)

    with pytest.raises(ValueError, match=gap):
        mise.locked_tool(tmp_path, "node", files=files)


def test_mise_executable_does_not_invent_a_host_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable native Mise is an explicit supply gap."""
    monkeypatch.setattr(mise.shutil, "which", lambda _name: None)

    with pytest.raises(ValueError, match="mise_unavailable"):
        mise.mise_executable()


@pytest.mark.parametrize("layout", ["missing-lock", "ambiguous"])
def test_repository_mise_files_rejects_incomplete_selection(tmp_path: Path, layout: str) -> None:
    """A selected config needs exactly one complete native lock pair."""
    (tmp_path / "mise.toml").write_text('[tools]\nnode = "26"\n')
    if layout == "ambiguous":
        (tmp_path / ".mise.toml").write_text('[tools]\nnode = "26"\n')
        (tmp_path / "mise.lock").write_text("lockfile_version = 2\n")

    with pytest.raises(
        ValueError,
        match="mise_config_ambiguous" if layout == "ambiguous" else "locked_toolchain_missing",
    ):
        mise.repository_mise_files(tmp_path)
