"""ETHOS CLI entrypoint."""

from __future__ import annotations

from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit_invalid_adopter_profile
from ethos.surface.cli._base import load_command_groups
from ethos.surface.cli.root.registry import load_root_commands

load_root_commands()


def main() -> None:
    """Run the ETHOS CLI."""
    import sys

    load_command_groups(sys.argv[1:])
    try:
        app()
    except ValueError as exc:
        if str(exc) != "adopter_profile_invalid:.ethos/profile.toml":
            raise
        command = next((arg for arg in sys.argv[1:] if not arg.startswith("-")), "ethos")
        emit_invalid_adopter_profile(
            command=command,
            json_output="--json" in sys.argv[1:],
            enforce=command == "prove"
            or (command in {"land", "publish"} and "--apply" in sys.argv[1:]),
        )


if __name__ == "__main__":
    main()
