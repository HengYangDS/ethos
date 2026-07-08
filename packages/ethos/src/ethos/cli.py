"""ETHOS CLI entrypoint."""

from __future__ import annotations

from ethos.surface.cli._base import app
from ethos.surface.cli._base import load_command_groups
from ethos.surface.cli.root.registry import load_root_commands

load_root_commands()


def main() -> None:
    """Run the ETHOS CLI."""
    import sys

    load_command_groups(sys.argv[1:])
    app()


if __name__ == "__main__":
    main()
