"""Public command tree; native Git hooks enter their protocol without CLI dispatch."""

from __future__ import annotations

from importlib import import_module

from cyclopts import App
from cyclopts.exceptions import CycloptsError

from ethos.application.catalog import usage_refusal
from ethos.contracts.admission import ethos_command_path
from ethos.contracts.admission import root_command
from ethos.contracts.operations.catalog import COMMANDS
from ethos.contracts.operations.catalog import GROUPS
from ethos.surface.cli.output import emit
from ethos.surface.cli.version import version_text

app = App(name="ethos", help="ETHOS command plane.", version=version_text)


def dispatch_arguments(argv: list[str]) -> list[str]:
    """Preserve help only when Cyclopts resolved a real command target."""
    if not any(argument in app.help_flags for argument in argv):
        return argv
    _, applications, remaining = app.parse_commands(argv)
    if remaining and applications[-1].default_command is None:
        return [argument for argument in argv if argument not in app.help_flags]
    return argv


def run_application(argv: list[str]) -> None:
    """Declare the commands under the argv's first word, and run the argv.

    A usage error is a structured result that exits 2, like a refusal. It names the longest catalog
    command or group the argv starts with, else the MCP launcher when the argv names it, else
    `ethos`.
    """
    words = ethos_command_path(["ethos", *argv])
    import_module("ethos.surface.cli.catalog").register(words[0] if words else "")
    try:
        app(dispatch_arguments(argv), exit_on_error=False, print_error=False)
    except CycloptsError as error:
        name = root_command(argv)
        paths = (" ".join(words[:count]) for count in (3, 2, 1))
        declared = name if name in app.resolved_commands() else "ethos"
        command = next((path for path in paths if path in COMMANDS or path in GROUPS), declared)
        gap = f"command_usage_invalid:{command}"
        refusal = usage_refusal(command, (gap,), {"usage": str(error)}, message=str(error))
        emit(refusal, json_output="--json" in argv)
