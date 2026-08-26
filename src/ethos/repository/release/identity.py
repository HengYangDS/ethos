"""Product, distribution, source, and package build identity."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Mapping
from importlib import resources
from typing import TYPE_CHECKING
from typing import Literal
from typing import NamedTuple
from typing import NoReturn
from typing import cast

from packaging.version import InvalidVersion
from packaging.version import Version

if TYPE_CHECKING:
    from pathlib import Path

_BUILD_RESOURCE = "data/build/identity.json"
_HEX = frozenset("0123456789abcdef")
_BUILD_SOURCE_INVALID = "build_source_identity_invalid"
_PACKAGE_BUILD_INVALID = "package_build_identity_invalid"
_PACKAGE_BUILD_MISSING = "package_build_identity_missing"


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


class BuildIdentity(NamedTuple):
    """One immutable package build identity without artifact-self hashes."""

    product_version: str
    distribution_version: str
    source_commit: str
    source_tree: str
    channel: Literal["development", "accepted"]
    acceptance_state: Literal["unaccepted", "accepted"]

    def projection(self) -> dict[str, str | int]:
        return {"schema_version": 1, **self._asdict()}


def product_version(root: Path) -> str:
    """Read and validate the sole tracked SemVer product-version authority."""
    try:
        raw = (root / "VERSION").read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        _fail("product_version_missing:VERSION", error)
    return product_version_from_text(raw)


def product_version_from_text(raw: str) -> str:
    """Validate exact text read from the tracked SemVer version authority."""
    value = raw.strip()
    if raw != f"{value}\n" or value != _canonical_semver(value):
        _fail("product_version_invalid:VERSION")
    return value


def build_identity(
    *,
    product: str,
    source_commit: str,
    source_tree: str,
    channel: Literal["development", "accepted"],
    acceptance_state: Literal["unaccepted", "accepted"],
) -> BuildIdentity:
    """Compile one exact source and channel into a package build identity."""
    if not _valid_git_identity(source_commit) or not _valid_git_identity(source_tree):
        raise ValueError(_BUILD_SOURCE_INVALID)
    if (channel, acceptance_state) not in {
        ("development", "unaccepted"),
        ("accepted", "accepted"),
    }:
        _fail("build_acceptance_identity_invalid")
    if product != _canonical_semver(product):
        _fail("product_version_invalid")
    base = str(Version(product))
    distribution = (
        base if acceptance_state == "accepted" else f"{base}.dev0+g{source_commit}.t{source_tree}"
    )
    return BuildIdentity(
        product,
        str(Version(distribution)),
        source_commit,
        source_tree,
        channel,
        acceptance_state,
    )


def build_identity_bytes(identity: BuildIdentity) -> bytes:
    """Serialize one build identity as canonical UTF-8 JSON bytes."""
    return _canonical(identity.projection())


def load_build_identity_bytes(raw: bytes) -> BuildIdentity:
    """Load one canonical package build identity."""
    try:
        identity = build_identity_from_projection(json.loads(raw.decode()))
    except (TypeError, UnicodeError, ValueError) as error:
        raise ValueError(_PACKAGE_BUILD_INVALID) from error
    if raw != _canonical(identity.projection()):
        raise ValueError(_PACKAGE_BUILD_INVALID)
    return identity


def build_identity_from_projection(payload: object) -> BuildIdentity:
    """Reconstruct one canonical build identity projection."""
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ValueError(_PACKAGE_BUILD_INVALID)
    try:
        identity = build_identity(
            product=str(payload["product_version"]),
            source_commit=str(payload["source_commit"]),
            source_tree=str(payload["source_tree"]),
            channel=cast("Literal['development', 'accepted']", payload["channel"]),
            acceptance_state=cast("Literal['unaccepted', 'accepted']", payload["acceptance_state"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(_PACKAGE_BUILD_INVALID) from error
    if dict(payload) != identity.projection():
        raise ValueError(_PACKAGE_BUILD_INVALID)
    return identity


def packaged_build_identity() -> BuildIdentity:
    """Read the immutable identity carried by an installed wheel."""
    try:
        raw = resources.files("ethos").joinpath(_BUILD_RESOURCE).read_bytes()
    except (FileNotFoundError, OSError) as error:
        raise ValueError(_PACKAGE_BUILD_MISSING) from error
    return load_build_identity_bytes(raw)


def wheel_build_identity(wheel: Path) -> BuildIdentity:
    """Read the complete immutable build identity carried by one wheel."""
    try:
        with zipfile.ZipFile(wheel) as archive:
            return load_build_identity_bytes(archive.read(f"ethos/{_BUILD_RESOURCE}"))
    except (KeyError, OSError, ValueError, zipfile.BadZipFile) as error:
        _fail("hook_runtime_wheel_build_identity_invalid", error)


def projected_package_versions(root: Path) -> dict[str, str]:
    """Validate tracked npm projections against the product-version owner."""
    expected = product_version(root)
    package = _json_object(
        root / "distributions/npm/package.json", "distributions/npm/package.json"
    )
    root_package = _json_object(root / "package.json", "root")
    lock = _json_object(root / "package-lock.json", "root")
    raw_packages = lock.get("packages")
    packages = cast("dict[str, object]", raw_packages) if isinstance(raw_packages, dict) else {}
    locked = packages.get("distributions/npm")
    root_locked = packages.get("")
    projections = {
        "distributions/npm/package.json": package.get("version"),
        "package-lock.json#packages/distributions/npm": locked.get("version")
        if isinstance(locked, dict)
        else None,
    }
    drift = next((label for label, value in projections.items() if value != expected), "")
    if drift:
        _fail(f"package_version_projection_drift:{drift}")
    if "version" in root_package:
        _fail("package_version_parallel_owner:package.json")
    if "version" in lock or not isinstance(root_locked, dict) or "version" in root_locked:
        _fail("package_version_parallel_owner:package-lock.json")
    return dict.fromkeys(projections, expected)


def _canonical_semver(raw: str) -> str:
    try:
        version = Version(raw)
    except InvalidVersion:
        return ""
    if version.epoch or version.post is not None or version.dev is not None or version.local:
        return ""
    value = ".".join(map(str, version.release)) if len(version.release) == 3 else ""
    if not value or version.pre is None:
        return value
    label = {"a": "alpha", "b": "beta", "rc": "rc"}.get(version.pre[0])
    return f"{value}-{label}.{version.pre[1]}" if label else ""


def _json_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text())
        if isinstance(value, dict):
            return value
    except (OSError, TypeError, UnicodeError, ValueError):
        pass
    _fail(f"package_version_projection_invalid:{label}")


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _valid_git_identity(value: str) -> bool:
    return len(value) in {40, 64} and not set(value) - _HEX
