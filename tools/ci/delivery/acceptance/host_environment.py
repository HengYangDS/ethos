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


def _declared(root: Path) -> dict[str, str]:
    """Name every variable a hermetic child receives; each path it names lies under `root`.

    Windows gets the Git variables alone, over the minimal environment: its home, temporary
    directory and path stay the host's.
    """
    fresh = {name: str(root / directory) for name, directory in _FRESH.items()}
    git = {
        "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_TEMPLATE_DIR": fresh["GIT_TEMPLATE_DIR"],
    }
    return independent_host_environment()[0] | git if os.name == "nt" else fresh | git


@contextmanager
def hermetic_environment(
    root: Path, executables: tuple[str, ...], *, forwarded: tuple[str, ...] = ()
) -> Generator[dict[str, str]]:
    """Give this process, and so each of its children, one fresh environment under `root`.

    A child gets a new home and temporary directory, Git without system or global configuration,
    system attributes or templates, and a path that holds one link for each declared executable.
    It gets no other variable of the host: no agent socket, no forge token and no desktop
    variable. `forwarded` names host variables that this process alone keeps, to find the host's
    tool supply; the yielded environment, which children are handed, leaves them out. The host's
    environment returns when the block ends.
    """
    sources = _resolve(executables)
    for directory in _FRESH.values():
        (root / directory).mkdir(parents=True)
    (root / "gitconfig").touch()
    if os.name != "nt":
        for name, source in sources.items():
            (root / _FRESH["PATH"] / name).symlink_to(source)
    environment, host = _declared(root), dict(os.environ)
    kept = {name: host[name] for name in forwarded if name in host}
    os.environ.clear()
    os.environ.update(environment | kept)
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
    declared = _declared(root)
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
