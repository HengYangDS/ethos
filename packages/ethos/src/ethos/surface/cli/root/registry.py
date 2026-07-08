"""Register root command modules onto the shared ETHOS CLI app."""

from __future__ import annotations

import importlib

ROOT_COMMAND_MODULES = (
    "adoption",
    "inspection",
    "lifecycle",
    "planning",
    "proof",
    "reference",
)


def load_root_commands() -> None:
    """Import root command modules for decorator registration."""
    for name in ROOT_COMMAND_MODULES:
        importlib.import_module(f"ethos.surface.cli.root.{name}")
