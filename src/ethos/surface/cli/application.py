"""Public command tree; native Git hooks enter their protocol without CLI dispatch."""

from __future__ import annotations

import importlib

from cyclopts import App
from cyclopts.exceptions import CycloptsError

from ethos.application.catalog import usage_refusal
from ethos.contracts.admission import root_command
from ethos.surface.cli.output import emit
from ethos.surface.cli.version import version_text

app = App(name="ethos", help="ETHOS command plane.", version=version_text)

_CATALOG = "ethos.surface.cli.root.catalog"
_COMMAND_MODULES = {
    "status": _CATALOG,
    "plan": _CATALOG,
    "prove": _CATALOG,
    "land": _CATALOG,
    "publish": _CATALOG,
    "mcp": "ethos.surface.cli.root.mcp",
    "adopt": _CATALOG,
    "lane": "ethos.surface.cli.lane.lifecycle",
    "hook": "ethos.surface.cli.hook.commands",
    "attestation": "ethos.surface.cli.root.attestation",
    "host": "ethos.surface.cli.root.host",
}


def load_command_groups(argv: list[str]) -> None:
    """Import only the command registration modules needed by this invocation."""
    selected_name = root_command(argv)
    if selected_name in _COMMAND_MODULES:
        selected = (_COMMAND_MODULES[selected_name],)
    elif selected_name:
        selected = ()
    else:
        selected = tuple(dict.fromkeys(_COMMAND_MODULES.values()))
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
    """Run one command; a usage error is a structured result that exits 2, like a refusal."""
    try:
        app(dispatch_arguments(argv), exit_on_error=False, print_error=False)
    except CycloptsError as error:
        name = root_command(argv)
        command = name if name in app.resolved_commands() else "ethos"
        gap = f"command_usage_invalid:{command}"
        refusal = usage_refusal(command, (gap,), {"usage": str(error)}, message=str(error))
        emit(refusal, json_output="--json" in argv)
