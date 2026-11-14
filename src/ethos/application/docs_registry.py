"""The docs-registry gate's provider: document metadata, and examples against the catalog."""

from __future__ import annotations

from itertools import takewhile
from pathlib import Path

from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.adapters.repo.git import git_files
from ethos.adapters.repo.git import git_stdout
from ethos.contracts.operations.catalog import GROUPS
from ethos.contracts.operations.catalog import command_path
from ethos.repository.registry.docs.health import docs_health_report

# The reference that `system/gates.toml` spells literally, for the tests that name this provider.
DOCS_REGISTRY_PROVIDER = "ethos.application.docs_registry:docs_registry_report"
# The one command outside the catalog, the MCP transport launcher, and the flags Cyclopts answers
# before any command.
_LAUNCHER = "mcp"
_META = frozenset({"--help", "-h", "--version"})


def _unknown_command(tokens: list[str]) -> str:
    """Return the `ethos` path an example names that no command or group declares, or nothing.

    The words before the first option name a catalog command, which takes every later token, the
    MCP launcher or a group; an example without words is known only as a help or version request.
    """
    words = list(takewhile(lambda token: not token.startswith("-"), tokens))
    if not words:
        return "" if set(tokens[:1]) & _META else "ethos"
    named = command_path(words) is not None or words[0] == _LAUNCHER
    return "" if named or " ".join(words) in GROUPS else " ".join(("ethos", *words))


def docs_registry_report(root: Path) -> dict[str, object]:
    """Validate docs metadata, and their command examples against the catalog's paths."""
    repository = git_stdout(root, "rev-parse", "--show-toplevel")
    return docs_health_report(
        root,
        command_validator=_unknown_command,
        tracked_documents=tuple(git_files(root, "*.md"))
        if repository and Path(repository).resolve() == root.resolve()
        else None,
        retained_origins=observed_document_origins(root),
    )
