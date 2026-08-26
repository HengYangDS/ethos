"""Hatch hook for the lock-bound, production-only OpenSpec runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_BUILD_IDENTITY_PATH = Path("src/ethos/data/build/identity.json")


class OpenSpecRuntimeHook(BuildHookInterface):
    """Compile the npm production closure into wheel build data."""

    PLUGIN_NAME = "openspec-runtime"

    def _cleanup_supply(self) -> None:
        owned = self.__dict__.pop("_owned_supply", None)
        if owned is not None:
            owned.cleanup()

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if version == "editable":
            return
        self._cleanup_supply()
        root = Path(self.root)
        owned = tempfile.TemporaryDirectory(prefix="ethos-openspec-supply-")
        supply = Path(owned.name)
        self._owned_supply = owned
        try:
            identity_bytes, distribution_version = _build_identity_payload(root)
            if version not in {"standard", distribution_version}:
                _distribution_identity_mismatch()
            identity_file = supply / "identity.json"
            identity_file.write_bytes(identity_bytes)
            if self.target_name == "sdist":
                build_data["force_include"][str(identity_file)] = _BUILD_IDENTITY_PATH.as_posix()
                return
            build_data["force_include"][str(identity_file)] = "ethos/data/build/identity.json"
            for relative in ("package.json", "package-lock.json"):
                shutil.copy2(root / relative, supply / relative)
            node = os.environ.get("ETHOS_BUILD_NODE", "")
            npm_cli = os.environ.get("ETHOS_BUILD_NPM_CLI", "")
            if not node or not npm_cli:
                _runtime_unavailable()
            subprocess.run(
                (
                    node,
                    npm_cli,
                    "ci",
                    "--omit=dev",
                    "--ignore-scripts",
                    "--offline",
                    "--workspaces=false",
                    "--no-audit",
                    "--no-fund",
                ),
                cwd=supply,
                check=True,
            )
            build_data["force_include"][str(supply / "node_modules")] = (
                "ethos/data/openspec-runtime/node_modules"
            )
        except BaseException as error:
            try:
                self._cleanup_supply()
            except OSError as cleanup_error:
                error.add_note(f"OpenSpec supply cleanup failed: {cleanup_error}")
            raise

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        del version, build_data, artifact_path
        self._cleanup_supply()


def get_build_hook() -> type[OpenSpecRuntimeHook]:
    """Expose the single custom hook class to Hatchling."""
    return OpenSpecRuntimeHook


def _runtime_unavailable() -> None:
    message = "Nox must bind the package-local Node/npm runtime"
    raise RuntimeError(message)


def _distribution_identity_mismatch() -> None:
    message = "package_build_distribution_identity_mismatch"
    raise RuntimeError(message)


def _build_identity_payload(root: Path) -> tuple[bytes, str]:
    """Load the single identity owner from source without requiring ETHOS installed."""
    source_root = root / "src"
    source_path = source_root.as_posix()
    inserted = source_path not in sys.path
    if inserted:
        sys.path.insert(0, source_path)
    try:
        source = import_module("ethos.adapters.repo.runtime.source")
        identity = source.build_input_identity(root)
        codec = import_module("ethos.repository.release.identity")
        return codec.build_identity_bytes(identity), identity.distribution_version
    finally:
        if inserted:
            sys.path.remove(source_path)
