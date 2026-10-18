"""The toolchain owner of the repository paradigm and the common verbs it exposes.

mise owns the verbs when its configuration is tracked, and then resolves tools from a
tracked lock; npm owns them otherwise when the Node module applies. uv and Go run no
tasks, so a repository without either owner adds mise.
"""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
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
        settings = declared.get("settings")
        if not isinstance(settings, dict) or settings.get("locked") is not True:
            yield ParadigmGap(
                "toolchain-lock",
                f"{config}:settings.locked",
                f"set locked = true under [settings] in {config}",
            )
        if lock not in tracked:
            yield ParadigmGap("toolchain-lock", lock, f"track {lock}, written by mise lock")
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
