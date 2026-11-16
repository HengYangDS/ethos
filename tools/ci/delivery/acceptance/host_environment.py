"""Environments for acceptance children: the smoke's minimal one and the journey's fresh one.

The journey's owner replaces this process's own environment, so a child receives the same fresh
environment whether it inherits it or is handed it.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Mapping

# The directories of a fresh environment, by the variable that names each to a child.
_FRESH = {"HOME": "home", "TMPDIR": "tmp", "PATH": "bin", "GIT_TEMPLATE_DIR": "templates"}


def _resolve(names: tuple[str, ...]) -> dict[str, Path]:
    """Resolve each named executable on this host, or name the first that it lacks."""
    tools = {}
    for name in names:
        executable = shutil.which(name)
        if executable is None:
            message = f"required executable is unavailable: {name}"
            raise RuntimeError(message)
        tools[name] = Path(executable).resolve()
    return tools


def independent_host_environment() -> tuple[dict[str, str], str]:
    """Retain native OS context and signing tools without agent control planes."""
    tools = _resolve(("git", "ssh-keygen"))
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        in {
            "ALLUSERSPROFILE",
            "APPDATA",
            "COMMONPROGRAMFILES",
            "COMSPEC",
            "HOME",
            "HOMEDRIVE",
            "HOMEPATH",
            "LOCALAPPDATA",
            "PATHEXT",
            "PROGRAMDATA",
            "PROGRAMFILES",
            "SYSTEMDRIVE",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "TMPDIR",
            "USER",
            "USERPROFILE",
            "USERNAME",
            "UV_PYTHON_INSTALL_DIR",
            "WINDIR",
        }
    }
    native_dirs = tuple(path.parent for path in tools.values())
    if os.name == "nt":
        system_root = os.environ.get("SYSTEMROOT")
        if not system_root:
            message = "minimal host environment requires SYSTEMROOT"
            raise RuntimeError(message)
        native_dirs += (Path(system_root) / "System32", Path(system_root))
    env["PATH"] = os.pathsep.join(dict.fromkeys(str(path) for path in native_dirs))
    for name in tools:
        if shutil.which(name, path=env["PATH"]) is None:
            message = f"minimal host environment cannot resolve {name}"
            raise RuntimeError(message)
    unavailable = [name for name in ("workstation", "wcp") if shutil.which(name, path=env["PATH"])]
    if unavailable:
        raise RuntimeError(
            "external governance executable leaked into package smoke: " + ", ".join(unavailable)
        )
    return env, tools["git"].as_posix()


def _declared(root: Path, executables: tuple[str, ...]) -> dict[str, str]:
    """Name every variable a hermetic child receives; each path it names lies under `root`.

    Windows gets the Git variables alone, over the minimal environment: its home, temporary
    directory and path stay the host's. It links nothing and its path gains no directory,
    which would show a child every neighbour of an executable; a declared executable that
    the minimal path does not hold is refused by name.
    """
    fresh = {name: str(root / directory) for name, directory in _FRESH.items()}
    git = {
        "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_TEMPLATE_DIR": fresh["GIT_TEMPLATE_DIR"],
    }
    if os.name != "nt":
        return fresh | git
    host = independent_host_environment()[0]
    for name in executables:
        if shutil.which(name, path=host["PATH"]) is None:
            message = (
                f"minimal host environment cannot resolve {name}: a Windows stage's path holds "
                "the directories of git and ssh-keygen and the system's alone"
            )
            raise RuntimeError(message)
    return host | git


@contextmanager
def host_supply(values: Mapping[str, str]) -> Generator[None]:
    """Show this process where the host's tool supply is, for one block alone.

    The block prepares a tool from that supply, and the commands of that preparation inherit
    the variables. No child that starts after the block does: each name is then as the
    process held it before, set or unset.
    """
    before = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, held in before.items():
            os.environ.pop(name, None)
            os.environ.update({} if held is None else {name: held})


@contextmanager
def hermetic_environment(root: Path, executables: tuple[str, ...]) -> Generator[dict[str, str]]:
    """Give this process, and so each of its children, one fresh environment under `root`.

    A child gets a new home and temporary directory, Git without system or global configuration,
    system attributes or templates, and a path that holds one link for each declared executable.
    It gets no other variable of the host: no agent socket, no forge token and no desktop
    variable. The host's environment returns when the block ends.
    """
    sources = _resolve(executables)
    # The declaration can refuse, so it is made before anything is created under the root.
    environment, host = _declared(root, executables), dict(os.environ)
    for directory in _FRESH.values():
        (root / directory).mkdir(parents=True)
    (root / "gitconfig").touch()
    if os.name != "nt":
        for name, source in sources.items():
            (root / _FRESH["PATH"] / name).symlink_to(source)
    os.environ.clear()
    os.environ.update(environment)
    # Python remembers the first temporary directory it resolved, on either side of the change.
    tempfile.tempdir = None
    try:
        yield environment
    finally:
        os.environ.clear()
        os.environ.update(host)
        tempfile.tempdir = None


def hermetic_gap(root: Path, executables: tuple[str, ...]) -> str:
    """Name the first thing that shows a child more than the fresh environment under `root`.

    That is a variable of this process that is undeclared, missing or changed; a home, temporary
    directory, template directory or global configuration that is no longer empty; or a path
    that holds anything but one link to an existing file for each declared executable.
    """
    declared = _declared(root, executables)
    for name in sorted(declared.keys() | os.environ.keys()):
        if os.environ.get(name) != declared.get(name):
            return name
    if os.name == "nt":
        return ""
    for name in ("HOME", "TMPDIR", "GIT_TEMPLATE_DIR"):
        if any(Path(declared[name]).iterdir()):
            return name
    if (root / "gitconfig").stat().st_size:
        return "GIT_CONFIG_GLOBAL"
    links = sorted(Path(declared["PATH"]).iterdir())
    linked = all(link.is_symlink() and link.is_file() for link in links)
    return "" if linked and [link.name for link in links] == sorted(executables) else "PATH"
