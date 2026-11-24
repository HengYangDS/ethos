"""Install a root's own locked tools with native mise: the one run that may leave safe mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.toolchain.mise import MISE_ENVIRONMENT_PREFIXES
from ethos.adapters.toolchain.mise import MISE_TRUSTED_CONFIG
from ethos.adapters.toolchain.mise import disposable_copy
from ethos.adapters.toolchain.mise import repository_mise_files
from ethos.repository.paradigm.parameters import seconds

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Mapping
    from pathlib import Path


def install_mode(
    environment: Mapping[str, str], trust: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Return an install's environment: in safe mode unless it carries the root's native trust.

    In safe mode mise 2026.11 loads a copy as untrusted whatever trust it carries: its lock then
    pins versions and checksums only, and mise downloads what the backend resolves, so a rebuilt
    archive of a locked version fails the locked checksum. A trusted install leaves safe mode and
    takes the archive at its lock's URL. Outside safe mode an install trusts its active
    configuration by itself, so this function sets safe mode itself whenever no trust is carried,
    whatever the environment said. Trust is the carried configuration path alone, read from
    `trust` when a caller holds it apart; no other entry of that mapping reaches the child.
    """
    carried = (environment if trust is None else trust).get(MISE_TRUSTED_CONFIG)
    fixed = {
        key: value
        for key, value in environment.items()
        if key not in {"MISE_SAFE", MISE_TRUSTED_CONFIG}
    }
    return fixed | ({MISE_TRUSTED_CONFIG: carried} if carried else {"MISE_SAFE": "1"})


def install_locked(
    root: Path, tools: tuple[str, ...], *, executable: Path, timeout: float
) -> subprocess.CompletedProcess[str]:
    """Install the named locked tools of the root in a disposable copy of its declarations.

    The configuration and the lock are read from the root, never from a caller, and the copy
    checks them as it checks every run's. The tool names follow `--`, so none of them is read as
    an option of mise. A trusted root's install runs as native `mise install` does there: code
    that its configuration declares for install time can run. Nothing above the copy is read,
    and mise's state stays inside it.
    """
    materials = repository_mise_files(root, executable=executable)
    with disposable_copy(root, materials, executable) as (isolated, selected, environment):
        return run_command(
            isolated,
            (str(selected), "install", "--locked", "--", *tools),
            timeout=seconds("probe", timeout),
            remove_env_prefixes=MISE_ENVIRONMENT_PREFIXES,
            env=install_mode(environment),
        )
