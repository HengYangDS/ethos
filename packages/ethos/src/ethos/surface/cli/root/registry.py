"""Register root command modules onto the shared ETHOS CLI app."""

from __future__ import annotations

from ethos.surface.cli._base import app
from ethos.surface.cli.quality.registry import register_declared_group


def load_root_commands() -> None:
    """Bind the entire public root command plane from its declaration."""
    register_declared_group(app, "root")
