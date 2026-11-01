"""Minimal independent host environment for the installed-package smoke."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def independent_host_environment() -> tuple[dict[str, str], str]:
    """Retain native OS context and signing tools without agent control planes."""
    tools = {}
    for name in ("git", "ssh-keygen"):
        executable = shutil.which(name)
        if executable is None:
            message = f"required executable is unavailable: {name}"
            raise RuntimeError(message)
        tools[name] = Path(executable).resolve()
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
