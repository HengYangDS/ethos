"""Hatch hook for the lock-bound, production-only OpenSpec runtime."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_BUILD_IDENTITY_PATH = Path("src/ethos/data/build/identity.json")
_LOCK_PREFIX = "node_modules/"


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
        supply = _prepared_supply(root)
        production_roots = _production_roots(root / "package-lock.json", supply)
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
                    Path(_LOCK_PREFIX) / relative
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


def _prepared_supply(root: Path) -> Path:
    raw = os.environ.get("ETHOS_BUILD_OPENSPEC_SUPPLY")
    supply = Path(raw) if raw else root / "node_modules"
    if supply.is_symlink() or not supply.is_dir():
        _supply_invalid(_LOCK_PREFIX.rstrip("/"))
    return supply


def _production_roots(lock_path: Path, supply: Path) -> tuple[Path, ...]:
    invalid_lock = "openspec_supply_lock_invalid:package-lock.json"
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        packages = lock["packages"]
    except (KeyError, OSError, json.JSONDecodeError, TypeError) as error:
        raise RuntimeError(invalid_lock) from error
    if not isinstance(packages, dict):
        raise TypeError(invalid_lock)
    selected: list[Path] = []
    declared: set[Path] = set()
    for key, metadata in sorted(packages.items()):
        if not key.startswith(_LOCK_PREFIX) or not isinstance(metadata, dict):
            continue
        relative = Path(key.removeprefix(_LOCK_PREFIX))
        declared.add(relative)
        if metadata.get("dev") or metadata.get("link"):
            continue
        package = supply / relative
        _validate_package(package, key, str(metadata.get("version") or ""))
        if not any(package.is_relative_to(supply / parent) for parent in selected):
            selected.append(relative)
    undeclared = sorted(_observed_package_roots(supply) - declared)
    if undeclared:
        _supply_invalid(f"{_LOCK_PREFIX}{undeclared[0].as_posix()}")
    return tuple(selected)


def _observed_package_roots(supply: Path) -> set[Path]:
    observed: set[Path] = set()
    pending = [supply]
    while pending:
        node_modules = pending.pop()
        for entry in node_modules.iterdir():
            candidates = (
                entry.iterdir() if entry.name.startswith("@") and entry.is_dir() else (entry,)
            )
            for package in candidates:
                if package.is_symlink():
                    observed.add(package.relative_to(supply))
                    continue
                if not package.is_dir():
                    continue
                declaration = package / "package.json"
                if declaration.is_file():
                    observed.add(package.relative_to(supply))
                nested = package / "node_modules"
                if nested.is_dir() and not nested.is_symlink():
                    pending.append(nested)
    return observed


def _validate_package(package: Path, lock_key: str, expected_version: str) -> None:
    if not expected_version or package.is_symlink() or not package.is_dir():
        _supply_invalid(lock_key)
    declaration = package / "package.json"
    if declaration.is_symlink() or not declaration.is_file():
        _supply_invalid(lock_key)
    try:
        observed = json.loads(declaration.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        message = f"openspec_supply_invalid:{lock_key}"
        raise RuntimeError(message) from error
    if not isinstance(observed, dict) or observed.get("version") != expected_version:
        _supply_invalid(lock_key)


def _supply_invalid(lock_key: str) -> None:
    message = f"openspec_supply_invalid:{lock_key}:run npm ci --ignore-scripts --no-audit --no-fund"
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
