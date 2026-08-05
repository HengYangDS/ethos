"""Cyclopts command tree and lazy command registration."""

from __future__ import annotations

import importlib

from cyclopts import App

from ethos.contracts.admission import root_command

app = App(name="ethos", help="ETHOS command plane.")
lane_app = App(name="lane", help="Work Lane lifecycle and write admission.", show=False)
lane_lease_app = App(name="lease", help="Generation-bound local Lane Lease lifecycle.")
lane_handoff_app = App(name="handoff", help="Local and cross-host Work Lane handoff.")
lane_retire_app = App(name="retire", help="Bounded Work Lane retirement lifecycle.")
hook_app = App(name="hook", help="Hook admission and guard reports.", show=False)

for command_group in (
    lane_lease_app,
    lane_handoff_app,
    lane_retire_app,
):
    lane_app.command(command_group)
for command_group in (lane_app, hook_app):
    app.command(command_group)

_COMMAND_MODULES = {
    "status": "ethos.surface.cli.root.inspection",
    "plan": "ethos.surface.cli.root.planning",
    "prove": "ethos.surface.cli.root.proof",
    "land": "ethos.surface.cli.root.land",
    "publish": "ethos.surface.cli.root.publish",
    "adopt": "ethos.surface.cli.root.adoption",
    "lane": "ethos.surface.cli.lane.lifecycle",
    "hook": "ethos.surface.cli.hook.commands",
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
            importlib.import_module("ethos.surface.cli.lane.lease")
            importlib.import_module("ethos.surface.cli.lane.handoff")
            importlib.import_module("ethos.surface.cli.lane.retirement")


def dispatch_arguments(argv: list[str]) -> list[str]:
    """Preserve help only when Cyclopts resolved a real command target."""
    if not any(argument in app.help_flags for argument in argv):
        return argv
    _, applications, remaining = app.parse_commands(argv)
    if remaining and applications[-1].default_command is None:
        return [argument for argument in argv if argument not in app.help_flags]
    return argv
