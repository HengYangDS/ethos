"""State what a declared command inherits from its launch: names, classes and counts.

ETHOS does not confine a declared command: its child receives the launch environment and the
first match on the launch path. This owner reports that, and holds no variable's value.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import TypedDict

from ethos.adapters.toolchain.mise import host_command_baseline
from ethos.adapters.toolchain.mise import launch_supply
from ethos.adapters.toolchain.mise import lock_supplies
from ethos.adapters.toolchain.mise import repository_mise_files

# The names that a declared command's child keeps once its environment is built from a list.
# Until a repository declares that state, a result counts what its launch holds beside them.
# Names compare without case, as the process adapter compares the names it removes.
KEPT_NAMES = frozenset(
    {
        "home",
        "logname",
        "path",
        "tmpdir",
        "user",
        "temp",
        "tmp",
    }
)
# A class is read from the shape of a name, the first alternative first; a value is never read.
# A one-word marker ends its name, so `MAX_TOKENS` holds none; a compound one may carry a suffix.
_CREDENTIAL_CLASS = re.compile(
    r"""(?P<ssh_agent>ssh_(auth_sock|agent_pid))
    |(?P<forge_token>(gh|github|gitlab|glab|gitea|ci_job)_(.*_)?token)
    |(?P<cloud_credential>(aws|azure|google|gcp|cloudsdk)_.*(key|secret|token|cred).*)
    |(?P<credential>.*(token|secret|password|passwd|passphrase|api_?key|credentials?|_pat)
        |.*((secret|private|signing|access)_?key|auth_config).*)""",
    re.VERBOSE,
)
# A refusal's message starts with its gap code; any other message is named by its class alone.
_GAP_CODE = re.compile(r"[a-z]+(?:_[a-z]+)+")
# A Git key's subsection can hold a URL with a credential, so only its two names are kept.
_OVERLAY_KEY = re.compile(r"(?is)([a-z][a-z0-9-]*)\.(?:.*\.)?([a-z][a-z0-9-]*)")
# Native mise's report of a lock: each declared tool's versions with their install state.
Supply = dict[str, list[dict[str, object]]]


class CommandOrigin(TypedDict):
    """The two members that a declared command's check carries."""

    executable: str
    supplier: str


def locked_toolchain(root: Path) -> tuple[str, tuple[str, ...], Supply]:
    """Read the lock against the launch path: its state, the tools found elsewhere, its supply.

    A lock that cannot be read is a state of the report and never a failure of the proof.
    """
    try:
        files = repository_mise_files(root)
        if files is None:
            return "undeclared", (), {}
        gaps, supply = launch_supply(root, files, os.environ.get("PATH", os.defpath))
    except (OSError, RuntimeError, TypeError, ValueError, subprocess.SubprocessError) as error:
        code = _GAP_CODE.match(str(error))
        return f"unread:{code[0] if code else type(error).__name__}", (), {}
    return "declared", gaps, supply


def inherited_environment(root: Path, *, executed: bool) -> dict[str, object]:
    """State, for a result that executed gates, what its declared commands inherited."""
    if not executed:
        return {}
    outside = [name.casefold() for name in os.environ if name.casefold() not in KEPT_NAMES]
    classes = {found.lastgroup for name in outside if (found := _CREDENTIAL_CLASS.fullmatch(name))}
    toolchain, outside_lock, _supply = locked_toolchain(root)
    return {
        "environment": {
            "mode": "inherited",
            "names": len(os.environ),
            "outside_allow_list": len(outside),
            "credential_classes": sorted(str(label).replace("_", "-") for label in classes),
            "locked_toolchain": toolchain,
            "outside_lock": sorted(outside_lock),
            "git_overlay_keys": sorted(
                key.expand(r"\1.\2") if (key := _OVERLAY_KEY.fullmatch(value)) else "unreadable"
                for name, value in os.environ.items()
                if name.startswith("GIT_CONFIG_KEY_")
            ),
        }
    }


def names_a_path(word: str) -> bool:
    """Whether a command's first word is a path: it is declared, and no lock supplies it."""
    return Path(word).name != word


def command_origin(word: str, found: str | None, supply: Supply) -> CommandOrigin:
    """Name the executable that a declared command starts, and what supplied it."""
    started = Path(found).absolute() if found else None
    baseline = host_command_baseline()
    supplier = (
        "declared"
        if names_a_path(word)
        else "unresolved"
        if started is None
        else "locked"
        if lock_supplies(supply, word, started)
        else "host-baseline"
        if started.parent in map(Path, baseline)
        else "launch-path"
    )
    return {"executable": str(started or ""), "supplier": supplier}
