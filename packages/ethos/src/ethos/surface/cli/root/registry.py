"""Register root command modules onto the shared ETHOS CLI app."""

from __future__ import annotations

import importlib

from ethos.surface.cli._base import app
from ethos.surface.cli.quality.registry import register_declared_group

ROOT_COMMAND_MODULES = (
    "adoption",
    "lifecycle",
    "planning",
    "proof",
    "reference",
)


def load_root_commands() -> None:
    """Bind declared root readers before importing bounded legacy command modules."""
    register_declared_group(app, "root")
    for name in ROOT_COMMAND_MODULES:
        importlib.import_module(f"ethos.surface.cli.root.{name}")
