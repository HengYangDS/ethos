"""Install one declared ETHOS tool as adopters do: a locked Mise `http:` tool and its console."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.process import command_failure
from ethos.adapters.process import run_command

if TYPE_CHECKING:
    from collections.abc import Mapping

# The only archive directory a package manager puts on PATH; it holds the ETHOS console alone.
CONSOLE_DIRECTORY = "ethos/bin"


class InstalledTool(NamedTuple):
    """One Mise installation of `http:ethos` in its own isolated Mise home."""

    mise: Path
    project: Path
    installed: Path
    environment: dict[str, str]


def run(
    mise: Path, project: Path, arguments: tuple[str, ...], environment: Mapping[str, str]
) -> str:
    """Run one Mise command for the project and return its output."""
    completed = run_command(
        project,
        (str(mise), "--cd", str(project), *arguments),
        env=environment,
        inherit_environment=False,
        timeout=600,
    )
    if completed.returncode:
        output = (completed.stderr.strip() or completed.stdout.strip())[-2000:]
        detail = f"{shlex.join(arguments)}:exit={completed.returncode}:{output}"
        message = f"shared_supply_package_manager_failed:{detail}"
        # The bounded message names the call; the chained native failure keeps both whole streams.
        raise RuntimeError(message) from command_failure(completed)
    return completed.stdout


def install_declared(
    declaration: str,
    home: Path,
    *,
    mise: Path,
    environment: Mapping[str, str],
    distribution: str,
    offline: bool,
) -> InstalledTool:
    """Lock and install the declared tool in a fresh Mise home and check its console.

    The project is its own repository, as an adopter's is before ETHOS selects a runtime: the
    installed console then runs its own runtime, not one an enclosing checkout selected. Mise
    compares its ceiling with the canonical directories it walks, so the home is resolved first;
    otherwise an enclosing checkout's toolchain joins the installation.
    """
    home = home.resolve()
    project = home / "project"
    project.mkdir(parents=True)
    run_command(home, ("git", "init", "--quiet", "--initial-branch=dev", str(project)), check=True)
    carrier = project / "mise.toml"
    carrier.write_text(declaration, encoding="utf-8")
    scoped = {
        **environment,
        **{f"MISE_{name}_DIR": str(home / name.lower()) for name in ("DATA", "CONFIG", "STATE")},
        "MISE_CACHE_DIR": str(home / "cache"),
        "MISE_CEILING_PATHS": str(home),
        "MISE_GLOBAL_CONFIG_FILE": str(home / "absent-global.toml"),
        "MISE_SYSTEM_CONFIG_DIR": str(home / "absent-system"),
        "MISE_TRUSTED_CONFIG_PATHS": str(carrier),
        **dict.fromkeys(("MISE_DISABLE_UPDATE_WARNING", "MISE_YES"), "1"),
        **({"MISE_OFFLINE": "1"} if offline else {}),
    }
    for arguments in (("lock",), ("install", "--locked")):
        run(mise, project, arguments, scoped)
    installed = Path(run(mise, project, ("where", "http:ethos"), scoped).strip())
    entries = sorted(path.name for path in (installed / CONSOLE_DIRECTORY).iterdir())
    if entries not in (["ethos"], ["ethos.cmd"]):
        message = f"shared_supply_path_entries_invalid:{','.join(entries)}"
        raise RuntimeError(message)
    console = run(mise, project, ("exec", "--locked", "--", "ethos", "--version"), scoped)
    if not distribution or distribution not in console:
        message = f"shared_supply_console_failed:{console.strip()}"
        raise RuntimeError(message)
    return InstalledTool(mise, project, installed, scoped)
