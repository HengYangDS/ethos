"""Install one declared ETHOS tool as adopters do: a locked Mise tool and its console."""

from __future__ import annotations

import os
import shlex
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.process import command_failure
from ethos.adapters.process import run_command
from ethos.repository.release.pin import PROVENANCE_SETTING
from ethos.repository.release.pin import declared_pin

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

    from ethos.repository.release.pin import DeclaredPin


class InstalledTool(NamedTuple):
    """One Mise installation of the declared tool in its own isolated Mise home.

    Mise strips the archive's one top directory, so the install holds the console in `bin/` and
    the runtime in `runtime/`.
    """

    mise: Path
    project: Path
    installed: Path
    environment: dict[str, str]
    key: str

    @property
    def runtime(self) -> Path:
        """Return the one runtime generation the install holds."""
        generations = tuple((self.installed / "runtime").iterdir())
        if len(generations) != 1:
            message = "shared_supply_generation_ambiguous"
            raise ValueError(message)
        return generations[0]


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


def _project(
    declaration: str, home: Path, *, environment: Mapping[str, str], offline: bool
) -> tuple[Path, dict[str, str], dict[str, str], DeclaredPin]:
    """Write the declaration into a fresh repository under its own isolated Mise home.

    The project is its own repository, as an adopter's is before ETHOS selects a runtime: the
    installed console then runs its own runtime, not one an enclosing checkout selected. Mise
    compares its ceiling with the canonical directories it walks, so the home is resolved first;
    otherwise an enclosing checkout's toolchain joins the installation.

    Returns the project, Mise's environment there, the environment for the calls that reach the
    forge, and the declared pin. Only a GitHub pin's forge calls carry the job's token, and only
    Mise sees it: anonymous calls are capped at 60 an hour for each address.
    """
    declared = declared_pin(declaration)
    if declared is None:
        message = "shared_supply_tool_undeclared"
        raise ValueError(message)
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
    token = os.environ.get("GH_TOKEN")
    forge = {**scoped, "GITHUB_TOKEN": token} if token and declared.form == "github" else scoped
    return project, scoped, forge, declared


def install_declared(
    declaration: str,
    home: Path,
    *,
    mise: Path,
    environment: Mapping[str, str],
    distribution: str,
    offline: bool,
    lock: tuple[str, ...] = (),
    seed: str | None = None,
    admit: Callable[[str], None] | None = None,
) -> InstalledTool:
    """Lock and install the declared tool in a fresh Mise home and check its console.

    `lock` holds the lock command's own arguments and `seed` an existing lock to relock in place.
    `admit` reads the lock Mise wrote and raises to refuse it, before anything is installed. A
    declaration that turns provenance verification on must also read so to Mise.
    """
    project, scoped, forge, declared = _project(
        declaration, home, environment=environment, offline=offline
    )
    setting = ("settings", "get", PROVENANCE_SETTING)
    if declared.verify_provenance and run(mise, project, setting, scoped).strip() != "true":
        message = "shared_supply_provenance_setting_unread"
        raise RuntimeError(message)
    lockfile = project / "mise.lock"
    if seed is not None:
        lockfile.write_text(seed, encoding="utf-8")
    run(mise, project, ("lock", *lock), forge)
    if admit is not None:
        admit(lockfile.read_text(encoding="utf-8"))
    run(mise, project, ("install", "--locked"), forge)
    installed = Path(run(mise, project, ("where", declared.key), scoped).strip())
    entries = sorted(path.name for path in (installed / "bin").iterdir())
    if entries not in (["ethos"], ["ethos.cmd"]):
        message = f"shared_supply_path_entries_invalid:{','.join(entries)}"
        raise RuntimeError(message)
    console = run(mise, project, ("exec", "--locked", "--", "ethos", "--version"), scoped)
    if not distribution or distribution not in console:
        message = f"shared_supply_console_failed:{console.strip()}"
        raise RuntimeError(message)
    return InstalledTool(mise, project, installed, scoped, declared.key)


def refusal(
    declaration: str, lock: str, home: Path, *, mise: Path, environment: Mapping[str, str]
) -> str:
    """Install the declared tool from a given lock in a fresh home; return Mise's refusal.

    The result is empty when Mise installed the tool, or failed and still left one installed.
    """
    project, scoped, forge, declared = _project(
        declaration, home, environment=environment, offline=False
    )
    (project / "mise.lock").write_text(lock, encoding="utf-8")
    try:
        run(mise, project, ("install", "--locked"), forge)
    except RuntimeError as refused:
        with suppress(RuntimeError):
            run(mise, project, ("where", declared.key), scoped)
            return ""
        return str(refused)
    return ""
