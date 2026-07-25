"""Compile command declarations into native Cyclopts lazy registrations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.contracts.commands import load_command_registry_declaration

if TYPE_CHECKING:
    from cyclopts import App


def register_declared_group(app: App, group: str) -> int:
    """Register one declared group without importing its handler modules."""
    registered = 0
    for command in load_command_registry_declaration().group(group):
        if command.name in app:
            continue
        app.command(command.import_path, name=command.name, help=command.help, show=command.show)
        registered += 1
    return registered
