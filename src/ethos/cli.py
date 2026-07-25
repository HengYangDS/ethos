"""ETHOS CLI entrypoint."""

from __future__ import annotations

import sys

from ethos.repository.registry.commands import known_root_command_names
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit_invalid_adopter_profile
from ethos.surface.cli._base import load_command_groups
from ethos.surface.cli.root.registry import load_root_commands

load_root_commands()


def main() -> None:
    """Run the ETHOS CLI."""
    argv = sys.argv[1:]
    load_command_groups(argv)
    try:
        app(argv)
    except ValueError as exc:
        if str(exc) != "adopter_profile_invalid:.ethos/profile.toml":
            raise
        _emit_invalid_profile(_command(argv), argv)


def _command(argv: list[str]) -> str:
    """Return the declared root command without mistaking an option value for it."""
    root_commands = known_root_command_names()
    skip_value = False
    for argument in argv:
        if skip_value:
            skip_value = False
            continue
        if argument == "--root":
            skip_value = True
            continue
        if argument.startswith("-"):
            continue
        return argument if argument in root_commands else "ethos"
    return "ethos"


def _emit_invalid_profile(command: str, argv: list[str]) -> None:
    """Emit the stable structured invalid-profile result for one public command."""
    emit_invalid_adopter_profile(
        command=command,
        json_output="--json" in argv,
        enforce=command == "prove" or (command in {"land", "publish"} and "--apply" in argv),
    )


if __name__ == "__main__":
    main()
