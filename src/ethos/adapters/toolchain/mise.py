"""Resolve native tool supply from exact mise inputs without executing project hooks."""

from __future__ import annotations

import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Iterator
    from collections.abc import Mapping


MISE_CONFIG = ".config/mise/config.toml"
MISE_LOCK = ".config/mise/mise.lock"


def _mise_environment(isolated: Path, *, offline: bool) -> dict[str, str]:
    """Bind native safe-mode and storage inputs without ambient Mise policy."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"MISE_DATA_DIR", "MISE_CACHE_DIR", "MISE_INSTALLS_DIR"}
    } | {
        "MISE_SAFE": "1",
        "MISE_DISABLE_UPDATE_WARNING": "1",
        "MISE_LOCKED": "1",
        "MISE_NOT_FOUND_SYSTEM_FALLBACK": "0",
        "MISE_YES": "0",
        "MISE_GLOBAL_CONFIG_FILE": str(isolated / "absent-global.toml"),
        "MISE_SYSTEM_CONFIG_DIR": str(isolated / "absent-system"),
    }
    if offline:
        environment.update(MISE_AUTO_INSTALL="0", MISE_OFFLINE="1")
    return environment


def repository_mise_files(root: Path) -> dict[str, str] | None:
    """Select one repository-owned native Mise lock without host fallback."""
    layouts = (
        (root / MISE_CONFIG, root / MISE_LOCK),
        (root / "mise.toml", root / "mise.lock"),
        (root / ".mise.toml", root / "mise.lock"),
    )
    selected = [(config, lock) for config, lock in layouts if config.is_file()]
    if not selected:
        return None
    if len(selected) != 1:
        message = "mise_config_ambiguous"
        raise ValueError(message)
    config, lock = selected[0]
    if not lock.is_file():
        message = "locked_toolchain_missing"
        raise ValueError(message)
    return {
        MISE_CONFIG: config.read_text(encoding="utf-8"),
        MISE_LOCK: lock.read_text(encoding="utf-8"),
    }


def mise_executable() -> Path:
    """Resolve only the operator-selected native mise executable."""
    if not (installed := shutil.which("mise")):
        message = "mise_unavailable:run tools/ci/scripts/bootstrap-python.sh"
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
    materials = (
        {path: (root / path).read_text(encoding="utf-8") for path in (MISE_CONFIG, MISE_LOCK)}
        if files is None
        else files
    )
    with TemporaryDirectory(prefix="ethos-mise-") as directory:
        isolated = Path(directory)
        for path in (MISE_CONFIG, MISE_LOCK):
            target = isolated / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(materials[path], encoding="utf-8")
        return run_command(
            isolated,
            (str(executable or mise_executable()), *arguments),
            timeout=timeout,
            remove_env_prefixes=("MISE_",),
            env=_mise_environment(isolated, offline=offline),
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
def locked_environment(root: Path, files: Mapping[str, str]) -> Iterator[dict[str, str]]:
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
            **_mise_environment(Path(directory), offline=True),
            "PATH": os.pathsep.join((directory, *(str(path) for path in paths), os.defpath)),
        }
