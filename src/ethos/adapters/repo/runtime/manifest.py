"""Canonical identity model for one immutable Python runtime carrier."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import stat
import sysconfig
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple
from typing import NoReturn

import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
from ethos.adapters.repo.runtime.inventory_memo import open_inventory_memo
from ethos.repository.release.identity import build_identity_from_projection

if TYPE_CHECKING:
    from ethos.adapters.repo.runtime.inventory_memo import InventoryMemo
    from ethos.repository.release.identity import BuildIdentity

_SCHEMA_VERSION = 7
_LEGACY_SCHEMA_VERSION = 6
_HEX = frozenset("0123456789abcdef")
_ENVIRONMENT_INVALID = "hook_runtime_environment_invalid"
_MANIFEST_INVALID = "hook_runtime_manifest_invalid"
_PAYLOAD_MISMATCH = "hook_runtime_payload_mismatch"


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
    repository_private: bool

    def projection(self) -> dict[str, object]:
        version = _SCHEMA_VERSION if self.repository_private else _LEGACY_SCHEMA_VERSION
        payload: dict[str, object] = {
            "schema_version": version,
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
        if self.repository_private:
            payload["repository_private"] = True
        return payload


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
        canonical_architecture(architecture_name or process_machine()),
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
    repository_private: bool = True,
) -> str:
    """Return the content address for one complete executable runtime closure."""
    payload = {
        "schema_version": _SCHEMA_VERSION if repository_private else _LEGACY_SCHEMA_VERSION,
        "wheel_sha256": wheel_sha256,
        **{key: value for key, value in build.projection().items() if key != "schema_version"},
        **environment._asdict(),
        "runtime_files": runtime_files,
    }
    if repository_private:
        payload["repository_private"] = True
    return hashlib.sha256(_canonical(payload)).hexdigest()


def runtime_file_inventory(runtime: Path) -> dict[str, str]:
    """Hash every runtime file and symlink without following authority outside its root.

    A payload that cannot be inventoried exactly, such as one holding bytecode, a junction or
    an unreadable entry, is a payload mismatch: no manifest can declare it.
    """
    if runtime.is_symlink() or runtime_filesystem.is_junction(runtime) or not runtime.is_dir():
        raise ValueError(_PAYLOAD_MISMATCH)
    root = runtime.resolve()
    memo = open_inventory_memo(root)
    records: dict[str, str] = {}
    pending = [(runtime, "")]
    try:
        while pending:
            parent, prefix = pending.pop()
            with os.scandir(parent) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    relative = prefix + entry.name
                    if "__pycache__" in path.parts or path.suffix == ".pyc":
                        _raise_payload_mismatch()
                    if runtime_filesystem.is_junction(path):
                        _raise_payload_mismatch()
                    if relative == "manifest.json":
                        continue
                    state = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(state.st_mode):
                        pending.append((path, relative + "/"))
                    else:
                        records[relative] = _entry_record(memo, path, relative, state, root=root)
    except (OSError, RuntimeError, UnicodeError, ValueError) as error:
        raise ValueError(_PAYLOAD_MISMATCH) from error
    if memo is not None:
        memo.save()
    return dict(sorted(records.items()))


def _entry_record(
    memo: InventoryMemo | None, path: Path, relative: str, state: os.stat_result, *, root: Path
) -> str:
    mode = state.st_mode
    if memo is None or not stat.S_ISREG(mode):
        return _inventory_entry_digest(path, root=root, mode=mode)
    return memo.digest(
        relative, state, partial(_inventory_entry_digest, path, root=root, mode=mode)
    )


def _inventory_entry_digest(path: Path, *, root: Path, mode: int) -> str:
    permissions = stat.S_IMODE(mode)
    if os.name == "nt":
        # Windows withholds writes only through the read-only attribute, which archive
        # installers such as Mise do not restore; a sealed runtime binds the same identity.
        permissions &= ~0o222
    if stat.S_ISLNK(mode):
        target = path.readlink()
        if target.is_absolute():
            _raise_payload_mismatch()
        path.resolve(strict=True).relative_to(root)
        payload = b"symlink\0" + f"{permissions:o}\0".encode() + target.as_posix().encode()
        return hashlib.sha256(payload).hexdigest()
    if not stat.S_ISREG(mode):
        _raise_payload_mismatch()
    hasher = hashlib.sha256(b"file\0" + f"{permissions:o}\0".encode())
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
    repository_private: bool = True,
) -> bytes:
    """Serialize one validated runtime manifest as canonical UTF-8 JSON."""
    manifest = RuntimeManifest(
        digest, wheel_sha256, build, environment, runtime_files, repository_private
    )
    _validate(manifest)
    return _canonical(manifest.projection()) + b"\n"


def load_runtime_manifest_bytes(raw: bytes) -> RuntimeManifest:
    """Load one canonical runtime manifest without observing its filesystem."""
    try:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            _raise_manifest_invalid()
        version = payload.get("schema_version")
        private = payload.get("repository_private", False)
        if (
            type(version) is not int
            or version not in {_LEGACY_SCHEMA_VERSION, _SCHEMA_VERSION}
            or private is not (version == _SCHEMA_VERSION)
        ):
            _raise_manifest_invalid()
        build = build_identity_from_projection(
            {
                "schema_version": 2,
                **{
                    key: payload[key]
                    for key in (
                        "product_version",
                        "distribution_version",
                        "source_commit",
                        "source_tree",
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
        private,
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
        or type(manifest.repository_private) is not bool
        or runtime_digest(
            wheel_sha256=manifest.wheel_sha256,
            build=manifest.build,
            environment=manifest.environment,
            runtime_files=manifest.runtime_files,
            repository_private=manifest.repository_private,
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


# CPython names a Windows interpreter's build, while `platform.machine()` there names the CPU.
_WINDOWS_BUILDS = {"win-amd64": "AMD64", "win-arm64": "ARM64"}


def interpreter_machine(build_platform: str, machine: str) -> str:
    """Name the machine an interpreter executes, as `platform.machine()` spells it natively.

    POSIX `uname` reports the process's own view. CPython on Windows reports the native CPU, so
    an x64 interpreter that Windows on Arm emulates would name ARM64, while its build names AMD64.
    """
    return _WINDOWS_BUILDS.get(build_platform, machine)


def process_machine() -> str:
    """Name the machine this interpreter executes."""
    return interpreter_machine(sysconfig.get_platform(), platform.machine())


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


def _raise_payload_mismatch() -> NoReturn:
    raise ValueError(_PAYLOAD_MISMATCH)
