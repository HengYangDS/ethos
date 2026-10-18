"""Qualify fail-closed native Mise selection without ambient-tool fallback."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.toolchain.mise as mise
from ethos.adapters.process import run_command
from ethos.repository.release.resources import canonical_resource

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
    files = {mise.MISE_CONFIG: "[settings]\n", mise.MISE_LOCK: "lock"}

    def observe(
        _root: Path,
        arguments: tuple[str, ...],
        *,
        files: Mapping[str, str],
        executable: Path,
        offline: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert offline
        assert files == {mise.MISE_CONFIG: "[settings]\n", mise.MISE_LOCK: "lock"}
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
    files = {mise.MISE_CONFIG: "[settings]\n", mise.MISE_LOCK: "lock"}
    calls: list[tuple[str, ...]] = []

    def execute(
        _root: Path,
        arguments: tuple[str, ...],
        *,
        files: Mapping[str, str],
        executable: Path,
        offline: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert files == {mise.MISE_CONFIG: "[settings]\n", mise.MISE_LOCK: "lock"}
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
    files = {mise.MISE_CONFIG: "[settings]\n", mise.MISE_LOCK: "lock"}

    def select(
        _root: Path, arguments: tuple[str, ...], *, files: Mapping[str, str], offline: bool
    ) -> subprocess.CompletedProcess[str]:
        assert arguments == ("which", "node")
        assert files == {mise.MISE_CONFIG: "[settings]\n", mise.MISE_LOCK: "lock"}
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


@pytest.mark.parametrize("tools", ["", "[tools]\n"])
def test_a_task_only_owner_selects_no_native_tools(tmp_path: Path, tools: str) -> None:
    """Task verbs without explicit or idiomatic tool selection need no tool lock."""
    config = tmp_path / mise.MISE_CONFIG
    config.parent.mkdir(parents=True)
    config.write_text(f'[settings]\nlocked = true\n{tools}\n[tasks]\ncheck = "nox"\n')

    assert mise.repository_mise_files(tmp_path) is None


def test_an_unreadable_owner_still_needs_its_lock(tmp_path: Path) -> None:
    """Unreadable configuration is never mistaken for a task-only owner."""
    (tmp_path / "mise.toml").write_text("[tools\n")

    with pytest.raises(ValueError, match="locked_toolchain_missing"):
        mise.repository_mise_files(tmp_path)


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


def test_native_idiomatic_declaration_survives_locked_input_isolation(tmp_path: Path) -> None:
    """The producer and native consumer retain versions owned by package.json."""
    repo = tmp_path / "idiomatic"
    config = repo / mise.MISE_CONFIG
    config.parent.mkdir(parents=True)
    config.write_text(
        '[tool_alias]\nnpm = "npm:npm"\n[settings]\nlocked = true\n'
        'idiomatic_version_file_enable_tools = ["node", "npm"]\n',
        encoding="utf-8",
    )
    lock = canonical_resource(mise.MISE_LOCK).read_text(encoding="utf-8")
    node = tomllib.loads(lock)["tools"]["node"][0]
    npm = json.loads(canonical_resource("package.json").read_text(encoding="utf-8"))[
        "dependencies"
    ]["npm"]
    (repo / mise.MISE_LOCK).write_text(
        lock + f'\n[[tools.npm]]\nversion = "{npm}"\nbackend = "npm:npm"\nspecifiers = ["{npm}"]\n',
        encoding="utf-8",
    )
    declaration = json.dumps(
        {
            "devEngines": {
                "runtime": {"name": "node", "version": node["specifiers"][0]},
                "packageManager": {"name": "npm", "version": npm},
            }
        },
    )
    (repo / "package.json").write_text(declaration, encoding="utf-8")
    materials = mise.repository_mise_files(repo)
    assert materials is not None
    assert materials.get("package.json") == declaration
    native = mise.run_mise(repo, ("ls", "--current", "--json"), files=materials, offline=True)
    assert native.returncode == 0, native
    assert not native.stderr, native
    observed = json.loads(native.stdout)
    for tool, version in (("node", node["version"]), ("npm", npm)):
        assert observed[tool][0]["active"]
        assert observed[tool][0]["installed"]
        assert observed[tool][0]["version"] == version
        source = observed[tool][0]["source"]
        assert source["type"] == "idiomatic-version-file"
        assert Path(source["path"]).name == "package.json"
        assert not Path(source["path"]).is_relative_to(repo)
    with mise.locked_environment(repo, materials) as environment:
        for tool, version in (("node", "v" + node["version"]), ("npm", npm)):
            executable = shutil.which(tool, path=environment["PATH"])
            assert executable is not None
            result = run_command(repo, (executable, "--version"), env=environment, timeout=15)
            assert result.returncode == 0, result
            assert not result.stderr, result
            assert result.stdout.strip() == version
    incomplete = {path: content for path, content in materials.items() if path != "package.json"}
    with (
        pytest.raises(ValueError, match="mise_bin_paths_invalid"),
        mise.locked_environment(repo, incomplete),
    ):
        pytest.fail("live package.json replaced the explicit incomplete declaration")


@pytest.mark.parametrize(
    ("fault", "gap"),
    [
        ("none", ""),
        ("failure", "mise_declaration_discovery_unavailable"),
        ("warning", "mise_declaration_discovery_unavailable"),
        ("invalid-json", "mise_declaration_discovery_invalid"),
        ("empty", "mise_declaration_discovery_invalid"),
        ("untyped-row", "mise_declaration_discovery_invalid"),
        ("outside", "mise_declaration_outside_root"),
        ("drift", "mise_declaration_changed"),
    ],
)
def test_native_declaration_discovery_preserves_selection_and_refuses_unproved_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, gap: str
) -> None:
    """Native discovery selects exact inputs; failure never falls back to ambient files."""
    config = tmp_path / mise.MISE_CONFIG
    config.parent.mkdir(parents=True)
    source = '[settings]\nidiomatic_version_file_enable_tools = ["node"]\n'
    config.write_text(source)
    lock = tmp_path / mise.MISE_LOCK
    lock.write_text("lockfile_version = 2\n")
    package = tmp_path / "package.json"
    package.write_text('{"devEngines":{"runtime":{"name":"node","version":"26"}}}')
    executable = tmp_path / "selected-mise"
    calls = []

    def discover(root: Path, command: tuple[str, ...], **options: object):
        calls.append(command)
        assert root == tmp_path
        assert command == (str(executable), "config", "ls", "--json")
        assert options["timeout"] == 15
        assert options["remove_env_prefixes"] == ("MISE_",)
        environment = options["env"]
        assert environment["MISE_SAFE"] == environment["MISE_OFFLINE"] == "1"
        assert environment["MISE_IDIOMATIC_VERSION_FILE_ENABLE_TOOLS"] == "node"
        paths = [config, package]
        if fault == "outside":
            paths.append(tmp_path.parent / "external.json")
        rows = [{}] if fault == "untyped-row" else [{"path": str(path)} for path in paths]
        output = (
            "not-json" if fault == "invalid-json" else json.dumps([] if fault == "empty" else rows)
        )
        if fault == "drift":
            config.write_text(source + "[tasks]\ncheck = 'changed'\n")
        return subprocess.CompletedProcess(
            command,
            1 if fault == "failure" else 0,
            output,
            "unproved native response" if fault in {"failure", "warning"} else "",
        )

    monkeypatch.setattr(mise, "run_command", discover)
    if gap:
        with pytest.raises(ValueError if fault != "untyped-row" else TypeError, match=gap):
            mise.repository_mise_files(tmp_path, executable=executable)
    else:
        assert mise.repository_mise_files(tmp_path, executable=executable) == {
            mise.MISE_CONFIG: source,
            mise.MISE_LOCK: lock.read_text(),
            "package.json": package.read_text(),
        }
    assert calls == [(str(executable), "config", "ls", "--json")]
    assert config.read_text() == (
        source + "[tasks]\ncheck = 'changed'\n" if fault == "drift" else source
    )


@pytest.mark.parametrize(
    ("fault", "gap"),
    [
        ("incomplete", "locked_toolchain_missing"),
        ("outside", "mise_declaration_path_invalid"),
        ("invalid-settings", "mise_idiomatic_settings_invalid"),
    ],
)
def test_locked_mise_execution_rejects_unadmitted_input_without_native_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, gap: str
) -> None:
    """An explicit bad closure cannot borrow live files or start a native process."""
    files = {mise.MISE_CONFIG: '[tools]\nnode = "26"\n', mise.MISE_LOCK: "lockfile_version = 2\n"}
    if fault == "incomplete":
        files.pop(mise.MISE_LOCK)
    elif fault == "outside":
        files["../external.json"] = "{}"
    else:
        files[mise.MISE_CONFIG] = "[settings]\nidiomatic_version_file_enable_tools = [7]\n"
    before = files.copy()
    entries = set(tmp_path.iterdir())
    monkeypatch.setattr(
        mise, "run_command", lambda *_args, **_kwargs: pytest.fail("unadmitted native execution")
    )
    with pytest.raises(ValueError, match=gap):
        mise.run_mise(tmp_path, ("which", "node"), files=files, executable=tmp_path / "mise")
    assert files == before
    assert set(tmp_path.iterdir()) == entries
