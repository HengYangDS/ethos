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

# The modules that declare the commands outside the operation catalog, by their first word.
_COMMAND_MODULES = {
    "mcp": "ethos.surface.cli.root.mcp",
    "lane": "ethos.surface.cli.lane.lifecycle",
    "hook": "ethos.surface.cli.hook.commands",
}


def load_command_groups(argv: list[str]) -> None:
    """Declare only the commands this invocation names, or every command for none."""
    selected_name = root_command(argv)
    if selected_name not in _COMMAND_MODULES:
        importlib.import_module("ethos.surface.cli.catalog").register(selected_name)
    if selected_name in _COMMAND_MODULES:
        selected = (_COMMAND_MODULES[selected_name],)
    elif selected_name:
        selected = ()
    else:
        selected = tuple(_COMMAND_MODULES.values())
    for module in selected:
        importlib.import_module(module)
        if module == _COMMAND_MODULES["lane"]:
            importlib.import_module("ethos.surface.cli.lane.formatting")
            importlib.import_module("ethos.surface.cli.lane.projections")
            importlib.import_module("ethos.surface.cli.lane.commit_signer")
            importlib.import_module("ethos.surface.cli.lane.lease")
            importlib.import_module("ethos.surface.cli.lane.handoff")
            importlib.import_module("ethos.surface.cli.lane.paradigm_repair")
            importlib.import_module("ethos.surface.cli.lane.redaction")
            importlib.import_module("ethos.surface.cli.lane.retirement")


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
