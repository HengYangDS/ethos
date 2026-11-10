"""Public command tree; native Git hooks enter their protocol without CLI dispatch."""

from __future__ import annotations

import importlib

from cyclopts import App
from cyclopts.exceptions import CycloptsError

from ethos.application.catalog import usage_refusal
from ethos.contracts.admission import ethos_command_path
from ethos.contracts.admission import root_command
from ethos.contracts.operations.catalog import command_path
from ethos.surface.cli.output import emit
from ethos.surface.cli.version import version_text

app = App(name="ethos", help="ETHOS command plane.", version=version_text)

# The modules that declare the commands outside the operation catalog, by the path they serve;
# `lane` declares the group's App, which the catalog's `lane` commands then join.
_COMMAND_MODULES = {
    "mcp": "ethos.surface.cli.root.mcp",
    "lane": "ethos.surface.cli.lane.lifecycle",
    "lane handoff": "ethos.surface.cli.lane.handoff",
    "lane lease": "ethos.surface.cli.lane.lease",
    "lane retire": "ethos.surface.cli.lane.retirement",
}


def load_command_groups(argv: list[str]) -> None:
    """Declare only the commands this invocation names, or every command for none.

    A module serves the invocation that names its path or a prefix of it, so `lane prewrite`
    builds no `lane retire` command.
    """
    words = ethos_command_path(["ethos", *argv])
    for path, module in _COMMAND_MODULES.items():
        served = tuple(path.split())
        if words[: len(served)] == served or served[: len(words)] == words:
            importlib.import_module(module)
    importlib.import_module("ethos.surface.cli.catalog").register(words[0] if words else "")


def dispatch_arguments(argv: list[str]) -> list[str]:
    """Preserve help only when Cyclopts resolved a real command target."""
    if not any(argument in app.help_flags for argument in argv):
        return argv
    _, applications, remaining = app.parse_commands(argv)
    if remaining and applications[-1].default_command is None:
        return [argument for argument in argv if argument not in app.help_flags]
    return argv


def run_application(argv: list[str]) -> None:
    """Run one command; a usage error is a structured result that exits 2, like a refusal.

    The error names the longest catalog path the argv starts with, else its command word if one
    is declared, else `ethos`.
    """
    try:
        app(dispatch_arguments(argv), exit_on_error=False, print_error=False)
    except CycloptsError as error:
        path, name = command_path(ethos_command_path(["ethos", *argv])), root_command(argv)
        command = path.name if path else name if name in app.resolved_commands() else "ethos"
        gap = f"command_usage_invalid:{command}"
        refusal = usage_refusal(command, (gap,), {"usage": str(error)}, message=str(error))
        emit(refusal, json_output="--json" in argv)
