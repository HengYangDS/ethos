"""Hatch build hook for editable declaration-resource projections."""

from __future__ import annotations

import tomllib
from importlib import import_module
from pathlib import Path
from typing import Any

BuildHookInterface = import_module("hatchling.builders.hooks.plugin.interface").BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Project checkout declarations only while Hatch builds an editable wheel."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Supply editable-only sources without changing the self-contained sdist path."""
        if version == "editable":
            root = Path(self.root)
            sdist = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"][
                "hatch"
            ]["build"]["targets"]["sdist"]["force-include"]
            build_data["force_include_editable"] = {
                (root / source).resolve().as_posix(): target.removeprefix("src/")
                for source, target in sdist.items()
            }
