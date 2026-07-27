"""ETHOS CLI entrypoint."""

from __future__ import annotations

import sys

from ethos.surface.cli.application import app
from ethos.surface.cli.application import command_name
from ethos.surface.cli.application import dispatch_arguments
from ethos.surface.cli.application import load_command_groups
from ethos.surface.cli.output import emit_invalid_adopter_profile


def main() -> None:
    """Run the ETHOS CLI."""
    argv = sys.argv[1:]
    load_command_groups(argv)
    try:
        app(dispatch_arguments(argv))
    except ValueError as exc:
        if str(exc) != "adopter_profile_invalid:.ethos/profile.toml":
            raise
        _emit_invalid_profile(command_name(argv) or "ethos", argv)


def _emit_invalid_profile(command: str, argv: list[str]) -> None:
    """Emit the stable structured invalid-profile result for one public command."""
    emit_invalid_adopter_profile(
        command=command,
        json_output="--json" in argv,
        enforce=command == "prove" or (command in {"land", "publish"} and "--apply" in argv),
    )


if __name__ == "__main__":
    main()
