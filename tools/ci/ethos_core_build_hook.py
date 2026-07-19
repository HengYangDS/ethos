"""Hatch build hook for declaration-resource projections."""

import tomllib
from contextlib import suppress
from importlib import import_module
from pathlib import Path
from typing import Any

BuildHookInterface = import_module("hatchling.builders.hooks.plugin.interface").BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Project declaration resources for checkout, editable, and sdist builds."""

    def _sdist_resources(self) -> dict[Path, Path]:
        root = Path(self.root)
        config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        sdist = config["tool"]["hatch"]["build"]["targets"]["sdist"]["force-include"]
        return {
            root / target: (root / source).resolve()
            for source, target in sdist.items()
            if target.startswith("src/ethos_core/data/")
        }

    def _remove_materialized(self) -> None:
        for path in getattr(self, "_materialized", ()):
            path.unlink(missing_ok=True)
            with suppress(OSError):
                path.parent.rmdir()
        self._materialized = []

    def clean(self, _versions: list[str]) -> None:
        """Remove only files synthesized by an interrupted checkout build."""
        self._remove_materialized()

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Project canonical declarations without leaving checkout artifacts."""
        root = Path(self.root)
        resources = self._sdist_resources()
        if version == "editable":
            build_data["force_include_editable"] = {
                source.as_posix(): target.relative_to(root / "src").as_posix()
                for target, source in resources.items()
            }
            return
        if version != "standard":
            return
        self._remove_materialized()
        for target, source in resources.items():
            if not target.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
                self._materialized.append(target)

    def finalize(self, version: str, _build_data: dict[str, Any], _artifact_path: str) -> None:
        """Restore a checkout after each standard build."""
        if version == "standard":
            self._remove_materialized()
