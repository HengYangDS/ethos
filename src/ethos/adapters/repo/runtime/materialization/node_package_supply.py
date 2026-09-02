"""Resolve the repository's one lock-bound Node package supply."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import NoReturn

_LOCK_PREFIX = "node_modules/"


def resolve_node_package_supply(source: Path) -> Path:
    """Return one absolute prepared tree matching the source package lock."""
    source, supply, _explicit = _select_supply(source)
    return _validate_complete_supply(source, supply)


def _select_supply(source: Path) -> tuple[Path, Path, bool]:
    source = source.resolve()
    configured = os.environ.get("ETHOS_NODE_PACKAGE_SUPPLY")
    if not configured:
        return source, source / "node_modules", False
    supply = Path(configured)
    if not supply.is_absolute():
        _fail("node_package_supply_path_not_absolute")
    return source, supply, True


def _validate_complete_supply(source: Path, supply: Path) -> Path:
    if supply.is_symlink() or not supply.is_dir():
        _fail("node_package_supply_unavailable")
    source_packages = _lock_packages(source / "package-lock.json", include_root=False)
    installed_packages = _lock_packages(supply / ".package-lock.json", include_root=True)
    if source_packages != installed_packages:
        _fail("node_package_supply_lock_mismatch")
    return supply.resolve()


def resolve_node_package_projection(source: Path) -> tuple[Path, tuple[Path, ...]]:
    """Return the prepared tree and its validated production package roots."""
    source, supply, explicit = _select_supply(source)
    if supply.is_symlink() or not supply.is_dir():
        _fail("node_package_supply_unavailable")
    if explicit or (supply / ".package-lock.json").is_file():
        supply = _validate_complete_supply(source, supply)
    packages = _lock_packages(source / "package-lock.json", include_root=True)
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
        _fail(f"node_package_supply_invalid:{_LOCK_PREFIX}{undeclared[0].as_posix()}")
    return supply.resolve(), tuple(selected)


def _lock_packages(path: Path, *, include_root: bool) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        _fail("node_package_supply_lock_invalid")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail("node_package_supply_lock_invalid", error)
    if not isinstance(payload, dict):
        _fail("node_package_supply_lock_invalid")
    packages = payload.get("packages")
    if payload.get("lockfileVersion") != 3 or not isinstance(packages, dict):
        _fail("node_package_supply_lock_invalid")
    return {
        key: value
        for key, value in packages.items()
        if isinstance(key, str) and (include_root or key)
    }


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
        _fail(f"node_package_supply_invalid:{lock_key}")
    declaration = package / "package.json"
    if declaration.is_symlink() or not declaration.is_file():
        _fail(f"node_package_supply_invalid:{lock_key}")
    try:
        observed = json.loads(declaration.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"node_package_supply_invalid:{lock_key}", error)
    if not isinstance(observed, dict) or observed.get("version") != expected_version:
        _fail(f"node_package_supply_invalid:{lock_key}")


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause
