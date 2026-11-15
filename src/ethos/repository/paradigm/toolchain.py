"""The toolchain owner of the repository paradigm and the common verbs it exposes.

mise owns the verbs when its configuration is tracked, and then resolves tools from a
tracked lock; npm owns them otherwise when the Node module applies. uv and Go run no
tasks, so a repository without either owner adds mise.
"""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING

from packaging.version import Version

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text
from ethos.repository.release.pin import bare_entry
from ethos.repository.release.pin import declared_pin

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm


def toolchain_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Report a missing or unlocked toolchain owner and each verb it does not expose."""
    carriers = {tool.id: tool.carrier for tool in paradigm.tool}
    config, lock = carriers["mise"], carriers["mise-lock"]
    manifest = next(module.manifest for module in paradigm.module if module.id == "node")
    if config in tracked:
        declared = _declared(tracked_text(root, config, tracked), tomllib.loads)
        if declared is None:
            yield ParadigmGap("toolchain-owner", config, f"make {config} readable TOML")
            return
        yield from _lock_gaps(config, lock, declared, tracked)
        yield from _verb_gaps(paradigm, config, "tasks", declared.get("tasks"))
    elif manifest in tracked:
        declared = _declared(tracked_text(root, manifest, tracked), json.loads)
        if declared is None:
            yield ParadigmGap("toolchain-owner", manifest, f"make {manifest} readable JSON")
            return
        yield from _verb_gaps(paradigm, manifest, "scripts", declared.get("scripts"))
    else:
        yield ParadigmGap(
            "toolchain-owner",
            config,
            f"add {config} with locked resolution and {_listed(paradigm.toolchain.verbs)} "
            "tasks; only mise and npm run tasks",
        )


# The obligation of a requested pin move; its repair is the one handler that a request adds.
PIN_OBLIGATION = "runtime-pin"


def pin_gap(config: str, text: str | None, release: str) -> ParadigmGap | None:
    """Report an ETHOS selection that is not the release's bare entry; None when it is.

    Only an upgrade asks: the paradigm report holds no repository to the release that reads it.
    A build that is no release gives an empty `release` and names no target.
    """
    repair = f"declare {release}'s bare entry as the ETHOS selection"
    try:
        pin = declared_pin(text or "")
    except ValueError:
        return ParadigmGap(PIN_OBLIGATION, config, f"declare one exact ETHOS pin in {config}")
    if not release:
        repair = "run ethos lane repair-paradigm --pin from a released ETHOS"
    elif pin == declared_pin(bare_entry(release)):
        return None
    return ParadigmGap(PIN_OBLIGATION, config, repair)


def pin_ahead(text: str | None, release: str) -> str:
    """Return the version of a selection newer than the release, or nothing when it is none.

    A pin moves up only, so an upgrade to an older release is refused and never planned.
    """
    try:
        pin = declared_pin(text or "")
    except ValueError:
        return ""
    return pin.version if release and pin and Version(pin.version) > Version(release) else ""


def _lock_gaps(
    config: str, lock: str, declared: Mapping[str, object], tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """A locked mise owner sets `locked = true` and tracks its lock once it selects a tool."""
    settings = declared.get("settings")
    if not isinstance(settings, dict) or settings.get("locked") is not True:
        yield ParadigmGap(
            "toolchain-lock",
            f"{config}:settings.locked",
            f"set locked = true under [settings] in {config}",
        )
    if lock not in tracked and selects_tools(declared, tool_versions=".tool-versions" in tracked):
        yield ParadigmGap("toolchain-lock", lock, f"track {lock}, written by mise lock")


def selects_tools(declared: Mapping[str, object], *, tool_versions: bool) -> bool:
    """Whether a mise declaration resolves tools; mise writes no lock for one that does not."""
    settings = declared.get("settings", {})
    return (
        bool(declared.get("tools"))
        or not isinstance(settings, dict)
        or bool(settings.get("idiomatic_version_file_enable_tools"))
        or tool_versions
    )


def _declared(text: str | None, parse: Callable[[str], object]) -> dict[str, object] | None:
    """Parse an owner's declaration, or return None when it is unreadable or not a table."""
    if text is None:
        return None
    try:
        declared = parse(text)
    except ValueError:
        return None
    return declared if isinstance(declared, dict) else None


def _verb_gaps(
    paradigm: RepositoryParadigm, owner: str, table: str, tasks: object
) -> Iterator[ParadigmGap]:
    declared = tasks if isinstance(tasks, dict) else {}
    for verb in paradigm.toolchain.verbs:
        if verb not in declared:
            yield ParadigmGap(
                "toolchain-verb",
                f"{owner}:{table}.{verb}",
                f"add a {verb} task to {owner} that runs the native {verb} commands",
            )


def _listed(verbs: tuple[str, ...]) -> str:
    *rest, last = verbs
    return f"{', '.join(rest)} and {last}" if rest else last
