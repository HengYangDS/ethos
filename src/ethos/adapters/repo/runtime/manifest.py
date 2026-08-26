"""Canonical identity model for one immutable Python runtime carrier."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import stat
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple
from typing import NoReturn

import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
from ethos.repository.release.identity import build_identity_from_projection

if TYPE_CHECKING:
    from ethos.repository.release.identity import BuildIdentity

_SCHEMA_VERSION = 5
_HEX = frozenset("0123456789abcdef")
_ENVIRONMENT_INVALID = "hook_runtime_environment_invalid"
_MANIFEST_INVALID = "hook_runtime_manifest_invalid"


class RuntimeEnvironment(NamedTuple):
    """Interpreter and dependency closure bound by a runtime identity."""

    python_abi: str
    python_version: str
    python_implementation: str
    dependency_lock_sha256: str
    platform: str
    architecture: str


class RuntimeManifest(NamedTuple):
    """One canonical runtime identity and its exact executable bytes."""

    digest: str
    wheel_sha256: str
    build: BuildIdentity
    environment: RuntimeEnvironment
    runtime_files: dict[str, str]

    def projection(self) -> dict[str, object]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "runtime_digest": self.digest,
            "wheel_sha256": self.wheel_sha256,
            **self.environment._asdict(),
            **{
                key: value
                for key, value in self.build.projection().items()
                if key != "schema_version"
            },
            "runtime_files": self.runtime_files,
        }


def runtime_environment(
    *,
    python_abi: str,
    python_version: str,
    python_implementation: str,
    dependency_lock_sha256: str,
    platform_name: str | None = None,
    architecture_name: str | None = None,
) -> RuntimeEnvironment:
    """Construct and validate one platform-qualified runtime environment."""
    environment = RuntimeEnvironment(
        python_abi,
        python_version,
        python_implementation,
        dependency_lock_sha256,
        platform_name or platform.system().lower(),
        canonical_architecture(architecture_name or platform.machine()),
    )
    if not all(environment) or not _valid_digest(environment.dependency_lock_sha256):
        raise ValueError(_ENVIRONMENT_INVALID)
    return environment


def runtime_digest(
    *,
    wheel_sha256: str,
    build: BuildIdentity,
    environment: RuntimeEnvironment,
    runtime_files: dict[str, str],
) -> str:
    """Return the content address for one complete executable runtime closure."""
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "wheel_sha256": wheel_sha256,
        **{key: value for key, value in build.projection().items() if key != "schema_version"},
        **environment._asdict(),
        "runtime_files": runtime_files,
    }
    return hashlib.sha256(_canonical(payload)).hexdigest()


def runtime_file_inventory(runtime: Path) -> dict[str, str]:
    """Hash every runtime file and symlink without following authority outside its root."""
    if runtime.is_symlink() or runtime_filesystem.is_junction(runtime) or not runtime.is_dir():
        raise ValueError(_MANIFEST_INVALID)
    root = runtime.resolve()
    records: dict[str, str] = {}
    for parent, directories, files in os.walk(runtime, followlinks=False):
        base = Path(parent)
        directories.sort()
        files.sort()
        for name in (*directories, *files):
            path = base / name
            relative = path.relative_to(runtime).as_posix()
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                _raise_manifest_invalid()
            if runtime_filesystem.is_junction(path):
                _raise_manifest_invalid()
            if path == runtime / "manifest.json" or (path.is_dir() and not path.is_symlink()):
                continue
            try:
                mode = stat.S_IMODE(path.lstat().st_mode)
                digest = _inventory_entry_digest(path, root=root, mode=mode)
            except (OSError, RuntimeError, UnicodeError, ValueError) as error:
                raise ValueError(_MANIFEST_INVALID) from error
            records[relative] = digest
    return dict(sorted(records.items()))


def _inventory_entry_digest(path: Path, *, root: Path, mode: int) -> str:
    if path.is_symlink():
        target = path.readlink()
        if target.is_absolute():
            _raise_manifest_invalid()
        path.resolve(strict=True).relative_to(root)
        payload = b"symlink\0" + f"{mode:o}\0".encode() + target.as_posix().encode()
        return hashlib.sha256(payload).hexdigest()
    if not path.is_file():
        _raise_manifest_invalid()
    hasher = hashlib.sha256(b"file\0" + f"{mode:o}\0".encode())
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def runtime_manifest_bytes(
    *,
    digest: str,
    wheel_sha256: str,
    build: BuildIdentity,
    environment: RuntimeEnvironment,
    runtime_files: dict[str, str],
) -> bytes:
    """Serialize one validated runtime manifest as canonical UTF-8 JSON."""
    manifest = RuntimeManifest(digest, wheel_sha256, build, environment, runtime_files)
    _validate(manifest)
    return _canonical(manifest.projection()) + b"\n"


def load_runtime_manifest_bytes(raw: bytes) -> RuntimeManifest:
    """Load one canonical runtime manifest without observing its filesystem."""
    try:
        payload = json.loads(raw.decode("utf-8"))
        build = build_identity_from_projection(
            {
                "schema_version": 1,
                **{
                    key: payload[key]
                    for key in (
                        "product_version",
                        "distribution_version",
                        "source_commit",
                        "source_tree",
                        "channel",
                        "acceptance_state",
                    )
                },
            }
        )
        environment = runtime_environment(
            python_abi=str(payload["python_abi"]),
            python_version=str(payload["python_version"]),
            python_implementation=str(payload["python_implementation"]),
            dependency_lock_sha256=str(payload["dependency_lock_sha256"]),
            platform_name=str(payload["platform"]),
            architecture_name=str(payload["architecture"]),
        )
    except (KeyError, TypeError, UnicodeError, ValueError) as error:
        raise ValueError(_MANIFEST_INVALID) from error
    files = payload.get("runtime_files")
    if not isinstance(files, dict):
        raise TypeError(_MANIFEST_INVALID)
    manifest = RuntimeManifest(
        str(payload["runtime_digest"]),
        str(payload["wheel_sha256"]),
        build,
        environment,
        {str(path): str(digest) for path, digest in files.items()},
    )
    _validate(manifest)
    if payload != manifest.projection() or raw != _canonical(payload) + b"\n":
        raise ValueError(_MANIFEST_INVALID)
    return manifest


def _validate(manifest: RuntimeManifest) -> None:
    if (
        not all(map(_valid_digest, (manifest.digest, manifest.wheel_sha256)))
        or not manifest.runtime_files
        or any(
            not _valid_inventory_path(path) or not _valid_digest(digest)
            for path, digest in manifest.runtime_files.items()
        )
        or runtime_digest(
            wheel_sha256=manifest.wheel_sha256,
            build=manifest.build,
            environment=manifest.environment,
            runtime_files=manifest.runtime_files,
        )
        != manifest.digest
    ):
        raise ValueError(_MANIFEST_INVALID)


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and not set(value) - _HEX


def canonical_architecture(value: str) -> str:
    """Normalize common architecture aliases for runtime identity comparison."""
    normalized = value.strip().lower().replace("-", "_")
    return {
        "aarch64": "arm64",
        "amd64": "x86_64",
        "x64": "x86_64",
    }.get(normalized, normalized)


def _valid_inventory_path(value: str) -> bool:
    path = Path(value)
    return (
        bool(value)
        and not path.is_absolute()
        and ".." not in path.parts
        and path.name != "manifest.json"
    )


def _raise_manifest_invalid() -> NoReturn:
    raise ValueError(_MANIFEST_INVALID)
