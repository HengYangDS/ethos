"""Hatch hook for the lock-bound, production-only OpenSpec runtime."""

from __future__ import annotations

import sys
import tempfile
from importlib import import_module
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_BUILD_IDENTITY_PATH = Path("src/ethos/data/build/identity.json")


class OpenSpecRuntimeHook(BuildHookInterface):
    """Project one validated prepared npm closure into package build data."""

    PLUGIN_NAME = "openspec-runtime"

    def _cleanup_identity(self) -> None:
        owned = self.__dict__.pop("_owned_identity", None)
        if owned is not None:
            owned.cleanup()

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if version == "editable":
            return
        self._cleanup_identity()
        root = Path(self.root)
        supply, production_roots = _prepared_projection(root)
        identity_bytes, distribution_version = _build_identity_payload(root)
        if version not in {"standard", distribution_version}:
            _distribution_identity_mismatch()
        owned = tempfile.TemporaryDirectory(prefix="ethos-build-identity-")
        self._owned_identity = owned
        try:
            identity_file = Path(owned.name) / "identity.json"
            identity_file.write_bytes(identity_bytes)
            destination = (
                _BUILD_IDENTITY_PATH.as_posix()
                if self.target_name == "sdist"
                else "ethos/data/build/identity.json"
            )
            build_data["force_include"][str(identity_file)] = destination
            for relative in production_roots:
                target = (
                    Path("node_modules") / relative
                    if self.target_name == "sdist"
                    else Path("ethos/data/openspec-runtime/node_modules") / relative
                )
                build_data["force_include"][str(supply / relative)] = target.as_posix()
        except BaseException as error:
            try:
                self._cleanup_identity()
            except OSError as cleanup_error:
                error.add_note(f"Build identity cleanup failed: {cleanup_error}")
            raise

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        del version, build_data, artifact_path
        self._cleanup_identity()


def get_build_hook() -> type[OpenSpecRuntimeHook]:
    """Expose the single custom hook class to Hatchling."""
    return OpenSpecRuntimeHook


def _prepared_projection(root: Path) -> tuple[Path, tuple[Path, ...]]:
    source_path = (root / "src").as_posix()
    inserted = source_path not in sys.path
    if inserted:
        sys.path.insert(0, source_path)
    try:
        owner = import_module("ethos.adapters.repo.runtime.materialization.node_package_supply")
        try:
            return owner.resolve_node_package_projection(root)
        except ValueError as error:
            raise RuntimeError(str(error)) from error
    finally:
        if inserted:
            sys.path.remove(source_path)


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
