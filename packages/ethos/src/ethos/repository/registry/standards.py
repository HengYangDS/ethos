"""Thin standards-adapter registry projection."""

from __future__ import annotations

from ethos_core.contracts.registry.declarations import load_standards_declaration


def standard_adapter_registry() -> dict[str, dict[str, str]]:
    """Return the declared standards-adapter registry."""
    return load_standards_declaration().registry()
