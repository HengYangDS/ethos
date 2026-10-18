"""Hatch hook for the lock-bound, production-only OpenSpec runtime."""

from __future__ import annotations

import sys
import tempfile
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import ModuleType


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
        owned = tempfile.TemporaryDirectory(
            prefix="ethos-build-identity-", dir=Path(tempfile.gettempdir()).resolve(strict=True)
        )
        self._owned_identity = owned
        try:
            identity_file = Path(owned.name) / "identity.json"
            identity_file.write_bytes(identity_bytes)
            with _source_module(root, "ethos.repository.release.resources") as layout:
                resource_root = (
                    layout.SDIST_RESOURCE_ROOT
                    if self.target_name == "sdist"
                    else layout.WHEEL_RESOURCE_ROOT
                )
                destination = (resource_root / layout.BUILD_IDENTITY_RESOURCE).as_posix()
                modules = (
                    Path("node_modules")
                    if self.target_name == "sdist"
                    else Path(layout.WHEEL_RESOURCE_ROOT) / "node_modules"
                )
            build_data["force_include"][str(identity_file)] = destination
            with _source_module(
                root, "ethos.repository.policy.quality.dependency_acceptance"
            ) as audit:
                audit_file = Path(owned.name) / "audit.toml"
                audit_file.write_bytes(
                    audit.product_audit_projection((root / audit.AUDIT_POLICY_PATH).read_bytes())
                )
                audit_target = (
                    Path(audit.AUDIT_POLICY_PATH)
                    if self.target_name == "sdist"
                    else Path(resource_root) / audit.AUDIT_POLICY_PATH
                )
            build_data["force_include"][str(audit_file)] = audit_target.as_posix()
            if self.target_name == "wheel":
                native, tag = _node_projection(root, Path(owned.name) / "native")
                build_data["force_include"][str(native)] = (Path(resource_root) / "node").as_posix()
                tool = _native_tool_projection(root, Path(owned.name).resolve() / "vale")
                build_data["force_include"][str(tool)] = (
                    Path(resource_root) / "native/vale"
                ).as_posix()
                build_data.update(pure_python=False, tag=tag)
            for relative in production_roots:
                target = modules / relative
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


@contextmanager
def _source_module(root: Path, name: str) -> Generator[ModuleType]:
    """Scope import lookup in a fresh build process and restore it afterward."""
    source_path = (root / "src").as_posix()
    inserted = source_path not in sys.path
    if inserted:
        sys.path.insert(0, source_path)
    try:
        yield import_module(name)
    finally:
        if inserted:
            sys.path.remove(source_path)


def _prepared_projection(root: Path) -> tuple[Path, tuple[Path, ...]]:
    with _source_module(
        root, "ethos.adapters.repo.runtime.materialization.node_package_supply"
    ) as owner:
        try:
            return owner.resolve_node_package_projection(root)
        except ValueError as error:
            raise RuntimeError(str(error)) from error


def _node_projection(root: Path, directory: Path) -> tuple[Path, str]:
    """Project verified cached native bytes; artifact builds never download supply."""
    with _source_module(root, "ethos.adapters.repo.runtime.materialization.node.supply") as owner:
        supply = owner.NodeSupply.read(root)
        native = supply.project(supply.cache(root) / supply.archive, directory, bootstrap_npm=False)
        return native, supply.tag


def _native_tool_projection(root: Path, directory: Path) -> Path:
    """Project cached native policy tools without downloading or running their installer."""
    with _source_module(root, "ethos.adapters.repo.runtime.materialization.native_supply") as owner:
        supply = owner.NativeSupply.read(root, "vale")
        return supply.project(supply.cache(root) / supply.archive, directory)


def _distribution_identity_mismatch() -> None:
    message = "package_build_distribution_identity_mismatch"
    raise RuntimeError(message)


def _build_identity_payload(root: Path) -> tuple[bytes, str]:
    """Load the single identity owner from source without requiring ETHOS installed."""
    with _source_module(root, "ethos.adapters.repo.runtime.source") as source:
        identity = source.build_input_identity(root)
    with _source_module(root, "ethos.repository.release.identity") as codec:
        return codec.build_identity_bytes(identity), identity.distribution_version
