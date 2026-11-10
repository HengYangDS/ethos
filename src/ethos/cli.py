"""ETHOS CLI entrypoint."""

from __future__ import annotations

import sys
from importlib import import_module
from typing import TYPE_CHECKING

from ethos.application.console import command_boundary
from ethos.application.console import invocation_parameters
from ethos.application.console import run_console
from ethos.contracts.admission import ethos_command_path
from ethos.contracts.admission import root_command
from ethos.surface.cli.version import version_text

if TYPE_CHECKING:
    from ethos.result import EthosResult


def console_main() -> None:
    """Dispatch the installed command through the target repository's exact selection."""
    argv = sys.argv[1:]
    failure = run_console(argv, main)
    if failure is not None:
        _emit(failure, json_output="--json" in argv, enforce=True)


def main() -> None:
    """Run the ETHOS CLI."""
    argv = sys.argv[1:]
    command = "version" if "--version" in argv else root_command(argv) or "ethos"
    with command_boundary(command, argv, _emit):
        if "--version" in argv:
            sys.stdout.write(f"{version_text()}\n")
            return
        commands = import_module("ethos.surface.cli.application")
        if "--json" in argv and {"--help", "-h"} & set(argv):
            # `ethos --help --json` prints the root's part of the catalog, `ethos <path> --help
            # --json` the command's or the group's; the MCP launcher's help is Cyclopts' own.
            described = import_module("ethos.surface.cli.catalog").help_result(
                ethos_command_path(["ethos", *argv])
            )
            if described is not None:
                _emit(described, json_output=True, enforce=False)
                return
        with invocation_parameters(command, argv):
            commands.run_application(argv)


def _emit(result: EthosResult, *, json_output: bool, enforce: bool) -> None:
    """Render through the output surface, imported only when a result is emitted."""
    import_module("ethos.surface.cli.output").emit(result, json_output=json_output, enforce=enforce)


if __name__ == "__main__":
    main()
