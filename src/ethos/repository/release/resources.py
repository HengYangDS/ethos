"""Resolve read-only product inputs without adopting caller-owned lookalikes."""

from __future__ import annotations

import base64
import hashlib
import os
import stat
from importlib.metadata import PackageNotFoundError
from importlib.metadata import distribution
from importlib.resources import files
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PureWindowsPath

WHEEL_RESOURCE_ROOT = PurePosixPath("ethos/resources")
SDIST_RESOURCE_ROOT = PurePosixPath("src") / WHEEL_RESOURCE_ROOT
GUIDANCE_RESOURCE = PurePosixPath("skills/ethos-repository-work/SKILL.md")
BUILD_IDENTITY_RESOURCE = PurePosixPath("build/identity.json")


def _relative_name(relative: str | PurePosixPath) -> PurePosixPath:
    name = PurePosixPath(relative)
    if (
        name.is_absolute()
        or ".." in name.parts
        or "\\" in name.as_posix()
        or PureWindowsPath(name.as_posix()).drive
    ):
        message = "product_resource_path_invalid"
        raise ValueError(message)
    return name


def packaged_resource(relative: str | PurePosixPath = "", *, package: Path | None = None) -> Path:
    """Locate shipped inputs within the loaded or explicitly selected package.

    Missing inputs remain missing; callers own their required-input diagnostics.
    The explicit anchor is for observing another installed package, not authority.
    """
    name = _relative_name(relative)
    package_root = (package if package is not None else Path(str(files("ethos")))).resolve()
    root = (package_root / WHEEL_RESOURCE_ROOT.name).resolve()
    path = (root / name).resolve()
    if not root.is_relative_to(package_root) or not path.is_relative_to(root):
        message = "product_resource_path_invalid"
        raise ValueError(message)
    return path


def require_packaged_resource(relative: str | PurePosixPath) -> Path:
    """Verify shipped bytes against the loaded distribution's original native RECORD."""
    name = _relative_name(relative)
    package = Path(str(files("ethos"))).resolve()
    path = package / WHEEL_RESOURCE_ROOT.name / name
    message = f"product_resource_integrity_invalid:{name}"
    try:
        for component in (path, *path.parents):
            if component == package:
                break
            if component.is_symlink() or component.is_junction():
                raise ValueError(message)
        metadata = distribution("ethos")
        entries = [
            entry
            for entry in metadata.files or ()
            if str(entry) == (WHEEL_RESOURCE_ROOT / name).as_posix()
        ]
        if len(entries) != 1:
            raise ValueError(message)
        entry = entries[0]
        if (
            os.path.normcase(str(Path(str(metadata.locate_file(entry))).absolute()))
            != os.path.normcase(str(path))
            or entry.hash is None
            or entry.hash.mode != "sha256"
            or not path.is_file()
        ):
            raise ValueError(message)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            observed = os.fstat(stream.fileno())
            digest = base64.urlsafe_b64encode(hashlib.file_digest(stream, "sha256").digest())
            if (
                not stat.S_ISREG(observed.st_mode)
                or observed.st_size != entry.size
                or digest.rstrip(b"=").decode("ascii") != entry.hash.value
            ):
                raise ValueError(message)
    except (OSError, PackageNotFoundError) as error:
        raise ValueError(message) from error
    return path


def canonical_resource(relative: str | PurePosixPath = "") -> Path:
    """Read source-owned input beside the loaded source package, else shipped input.

    A source runner never falls back to an installed or caller-owned substitute.
    Source-relative names are unchanged by the native wheel projection.
    """
    name = _relative_name(relative)
    package = Path(str(files("ethos"))).resolve()
    source = package.parent.parent
    if package == source / "src/ethos":
        path = (source / name).resolve()
        if not path.is_relative_to(source):
            message = "product_resource_path_invalid"
            raise ValueError(message)
        return path
    return packaged_resource(name, package=package)
