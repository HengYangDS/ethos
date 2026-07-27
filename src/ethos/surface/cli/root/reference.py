"""Internal docs-registry adapter over the live command surface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.registry.docs.health import docs_health_report
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups

if TYPE_CHECKING:
    from pathlib import Path


def _live_cyclopts_command(tokens: list[str]) -> str:
    """Return an unknown command path using the loaded Cyclopts operation tree."""
    command_chain, apps, remaining = app.parse_commands(tokens)
    if not command_chain:
        return " ".join(("ethos", *(token for token in tokens if not token.startswith("-"))))
    if apps[-1].default_command is None and remaining and not remaining[0].startswith("-"):
        return " ".join(("ethos", *command_chain, remaining[0]))
    return ""


def docs_registry_report(root: Path) -> dict[str, object]:
    """Validate docs metadata and examples against the live command surface."""
    load_command_groups([])
    return docs_health_report(root, command_validator=_live_cyclopts_command)
