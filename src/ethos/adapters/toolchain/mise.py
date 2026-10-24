"""Resolve native tool supply from exact mise inputs without executing project hooks."""

from __future__ import annotations

import json
import os
import shutil
import tomllib
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from pathlib import PurePosixPath
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.repo.content.observation import read_regular_bytes

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Generator
    from collections.abc import Mapping


MISE_CONFIG = ".config/mise/config.toml"
MISE_LOCK = ".config/mise/mise.lock"
# The caller's own mise storage and safe-mode choice; resolution overrides the last two.
_CALLER_INPUTS = frozenset(
    ("MISE_DATA_DIR", "MISE_CACHE_DIR", "MISE_INSTALLS_DIR", "MISE_STATE_DIR", "MISE_SAFE")
)


def native_tool_cache(root: Path) -> Path:
    """Share native supply across linked worktrees, honoring explicit CI roots."""
    selected = os.environ.get("ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR") or os.environ.get(
        "ETHOS_CI_TOOL_CACHE_DIR"
    )
    if selected:
        home = Path(selected)
        return home if home.is_absolute() else root / home
    common = import_module("ethos.adapters.repo.git").git_common_dir(root)
    return (
        Path(common) / "ethos/tool-cache/ci-tools"
        if common
        else root / "build/runtime/tool-cache/ci-tools"
    )


def _mise_environment(
    isolated: Path,
    *,
    offline: bool,
    files: Mapping[str, str] | None = None,
    execution: bool = False,
) -> dict[str, str]:
    """Bind native storage and safety inputs; execution keeps only the caller's explicit policy."""
    environment = {key: value for key, value in os.environ.items() if key in _CALLER_INPUTS} | {
        "MISE_DISABLE_UPDATE_WARNING": "1",
        "MISE_LOCKED": "1",
        "MISE_NOT_FOUND_SYSTEM_FALLBACK": "0",
        "MISE_YES": "0",
        "MISE_GLOBAL_CONFIG_FILE": str(isolated / "absent-global.toml"),
        "MISE_SYSTEM_CONFIG_DIR": str(isolated / "absent-system"),
        "MISE_CEILING_PATHS": str(isolated.parent),
    }
    if not execution:
        # Resolution runs no repository task, and mise's record of what it loaded stays disposable.
        environment |= {"MISE_SAFE": "1", "MISE_STATE_DIR": str(isolated / "state")}
    settings = tomllib.loads(files[MISE_CONFIG]).get("settings", {}) if files else {}
    if type(settings) is not dict:
        message = "mise_idiomatic_settings_invalid"
        raise ValueError(message)
    for name in (
        "idiomatic_version_file_enable_tools",
        "idiomatic_version_file_disable_files",
    ):
        values = settings.get(name, [])
        if not isinstance(values, list) or any(
            not isinstance(value, str)
            or not value
            or "," in value
            or "\0" in value
            or any(char.isspace() for char in value)
            for value in values
        ):
            message = "mise_idiomatic_settings_invalid"
            raise ValueError(message)
        environment[f"MISE_{name.upper()}"] = ",".join(values)
    if offline:
        environment.update(MISE_AUTO_INSTALL="0", MISE_OFFLINE="1")
    return environment


def _task_only_configuration(config_text: str) -> bool:
    """Only a readable native declaration with no tool selection is task-only."""
    try:
        declared = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError:
        return False
    settings = declared.get("settings", {})
    return (
        not declared.get("tools")
        and isinstance(settings, dict)
        and not settings.get("idiomatic_version_file_enable_tools")
    )


def repository_mise_files(root: Path, *, executable: Path | None = None) -> dict[str, str] | None:
    """Select the native declaration closure without repository or host fallback."""
    canonical = root.resolve()
    layouts = (
        (MISE_CONFIG, MISE_LOCK),
        ("mise.toml", "mise.lock"),
        (".mise.toml", "mise.lock"),
    )
    selected = [(config, lock) for config, lock in layouts if (canonical / config).is_file()]
    if not selected:
        return None
    if len(selected) != 1:
        message = "mise_config_ambiguous"
        raise ValueError(message)
    config, lock = selected[0]
    if (
        _task_only_configuration(_mise_input(canonical, config))
        and not (canonical / ".tool-versions").is_file()
    ):
        return None
    if not (canonical / lock).is_file():
        message = "locked_toolchain_missing"
        raise ValueError(message)
    origins = {MISE_CONFIG: config, MISE_LOCK: lock}
    materials = {name: _mise_input(canonical, path) for name, path in origins.items()}
    with TemporaryDirectory(prefix="ethos-mise-discovery-") as directory:
        environment = _mise_environment(Path(directory), offline=True, files=materials)
        environment["MISE_CEILING_PATHS"] = str(canonical.parent)
        declared = (
            _mise_declaration_paths(canonical, environment, executable)
            if environment["MISE_IDIOMATIC_VERSION_FILE_ENABLE_TOOLS"]
            or (canonical / ".tool-versions").is_file()
            else ()
        )
    for relative in declared:
        if relative != config:
            materials[relative] = _mise_input(canonical, relative)
            origins[relative] = relative
    if any(_mise_input(canonical, path) != materials[name] for name, path in origins.items()):
        message = "mise_declaration_changed"
        raise ValueError(message)
    return materials


def _mise_declaration_paths(
    root: Path, environment: Mapping[str, str], executable: Path | None
) -> tuple[str, ...]:
    """Use native discovery for idiomatic source names, never a filename registry."""
    discovered = run_command(
        root,
        (str(executable or mise_executable()), "config", "ls", "--json"),
        timeout=15,
        remove_env_prefixes=("MISE_",),
        env=environment,
    )
    if discovered.returncode or discovered.stderr:
        message = "mise_declaration_discovery_unavailable"
        raise ValueError(message)
    try:
        rows = json.loads(discovered.stdout)
    except json.JSONDecodeError as error:
        message = "mise_declaration_discovery_invalid"
        raise ValueError(message) from error
    if not isinstance(rows, list) or not rows:
        message = "mise_declaration_discovery_invalid"
        raise ValueError(message)
    paths = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            message = "mise_declaration_discovery_invalid"
            raise TypeError(message)
        selected = Path(row["path"])
        if not selected.is_absolute() or not selected.is_relative_to(root):
            message = "mise_declaration_outside_root"
            raise ValueError(message)
        paths.append(selected.relative_to(root).as_posix())
    return tuple(paths)


def _mise_input(root: Path, relative: str) -> str:
    """Read the native declaration bytes without following a repository alias."""
    return read_regular_bytes(
        root,
        relative,
        unsafe_gap="mise_declaration_unsafe",
        unstable_gap="mise_declaration_changed",
        size_gap="mise_declaration_size_exceeded",
    ).decode("utf-8")


def mise_executable() -> Path:
    """Resolve only the operator-selected native mise executable."""
    if not (installed := shutil.which("mise")):
        message = "mise_unavailable:put the mise executable on PATH"
        raise ValueError(message)
    return Path(installed).resolve()


def run_mise(
    root: Path,
    arguments: tuple[str, ...],
    *,
    files: Mapping[str, str] | None = None,
    executable: Path | None = None,
    timeout: float = 15,
    offline: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run native mise over exact inputs with no project hooks or ambient config."""
    materials = repository_mise_files(root, executable=executable) if files is None else files
    if materials is None or any(path not in materials for path in (MISE_CONFIG, MISE_LOCK)):
        message = "locked_toolchain_missing"
        raise ValueError(message)
    for path, content in materials.items():
        selected = PurePosixPath(path)
        if (
            selected.is_absolute()
            or not selected.parts
            or ".." in selected.parts
            or "\\" in path
            or "\0" in path
            or selected.as_posix() != path
            or not isinstance(content, str)
        ):
            message = "mise_declaration_path_invalid"
            raise ValueError(message)
        if path not in (MISE_CONFIG, MISE_LOCK):
            try:
                current = _mise_input(root.resolve(), path)
            except (OSError, ValueError) as error:
                message = f"mise_version_carrier_changed:{path}"
                raise ValueError(message) from error
            if current != content:
                message = f"mise_version_carrier_changed:{path}"
                raise ValueError(message)
    with TemporaryDirectory(prefix="ethos-mise-") as directory:
        isolated = Path(directory)
        environment = _mise_environment(isolated, offline=offline, files=materials)
        for path, content in materials.items():
            target = isolated / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="")
        return run_command(
            isolated,
            (str(executable or mise_executable()), *arguments),
            timeout=timeout,
            remove_env_prefixes=("MISE_",),
            env=environment,
        )


def locked_tool(root: Path, name: str, files: Mapping[str, str] | None = None) -> Path:
    """Resolve installed locked supply; never install or use an ambient tool fallback."""
    result = run_mise(root, ("which", name), files=files, offline=True)
    if result.returncode or result.stderr:
        message = f"mise_supply_unavailable:{name}:{result.stderr.strip()}"
        raise ValueError(message)
    executable = Path(result.stdout.strip())
    if not executable.is_absolute() or not executable.is_file():
        message = f"mise_executable_unavailable:{name}"
        raise ValueError(message)
    return executable


@contextmanager
def locked_environment(root: Path, files: Mapping[str, str]) -> Generator[dict[str, str]]:
    """Expose locked tools and the selected mise only for the child lifetime."""
    executable = mise_executable()
    selected = run_mise(root, ("env", "--json"), files=files, executable=executable, offline=True)
    if selected.returncode or selected.stderr:
        message = f"mise_environment_unavailable:{selected.stderr.strip()[:512]}"
        raise ValueError(message)
    try:
        environment = json.loads(selected.stdout)
    except json.JSONDecodeError as error:
        message = "mise_environment_invalid"
        raise ValueError(message) from error
    if not isinstance(environment, dict) or any(
        not isinstance(key, str) or not isinstance(value, str) for key, value in environment.items()
    ):
        message = "mise_environment_invalid"
        raise ValueError(message)
    listed = run_mise(root, ("bin-paths",), files=files, executable=executable, offline=True)
    if listed.returncode or listed.stderr:
        message = f"mise_bin_paths_unavailable:{listed.stderr.strip()[:512]}"
        raise ValueError(message)
    paths = tuple(Path(line) for line in listed.stdout.splitlines() if line)
    if not paths or any(not path.is_absolute() or not path.is_dir() for path in paths):
        message = "mise_bin_paths_invalid"
        raise ValueError(message)
    with TemporaryDirectory(prefix="ethos-mise-bin-") as directory:
        suffix = executable.suffix.lower()
        alias_name = "mise"
        if os.name == "nt":
            alias_name += suffix if suffix in {".exe", ".cmd", ".bat"} else ".exe"
        alias = Path(directory) / alias_name
        try:
            alias.symlink_to(executable)
        except OSError:
            try:
                os.link(executable, alias)
            except OSError:
                shutil.copy2(executable, alias)
        if not alias.is_file():
            message = "mise_executable_unavailable"
            raise ValueError(message)
        yield {
            **environment,
            **_mise_environment(Path(directory), offline=True, files=files, execution=True),
            "PATH": os.pathsep.join((directory, *(str(path) for path in paths), os.defpath)),
        }
