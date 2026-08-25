"""Select and invoke one immutable Git-common ETHOS runtime."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import uuid
from dataclasses import dataclass
from pathlib import Path

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.adapters.repo.runtime.transition import require_runtime_identity_attested
from ethos.repository.release.admission import accepted_release_candidate
from ethos.repository.release.admission import accepted_runtime_candidate
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import load_build_identity_bytes

_DIGEST_LENGTH = 64
_HEX = frozenset("0123456789abcdef")
_SELECTOR = "CURRENT"
_CURRENT_MISSING = "hook_runtime_current_missing"
_CURRENT_INVALID = "hook_runtime_current_invalid"
_CURRENT_TARGET_INVALID = "hook_runtime_current_target_invalid"
_MANIFEST_INVALID = "hook_runtime_manifest_invalid"


@dataclass(frozen=True, slots=True)
class SelectedRuntime:
    """One validated immutable runtime selected for a Git common directory."""

    root: Path
    digest: str
    python: Path
    entrypoint: Path
    manifest: Path
    wheel_sha256: str
    python_abi: str
    python_version: str
    python_implementation: str
    dependency_lock_sha256: str
    platform: str
    build: BuildIdentity


def current_runtime(
    common: Path,
    *,
    expected_build: BuildIdentity | None = None,
) -> SelectedRuntime:
    """Read and validate the canonical runtime selected by ``CURRENT``."""
    runtime_root = common.resolve() / "ethos" / "runtime"
    selector = runtime_root / _SELECTOR
    try:
        raw = selector.read_bytes()
    except OSError as error:
        raise ValueError(_CURRENT_MISSING) from error
    if selector.is_symlink():
        raise ValueError(_CURRENT_INVALID)
    try:
        text = raw.decode("ascii")
    except UnicodeError as error:
        raise ValueError(_CURRENT_INVALID) from error
    digest = text.removesuffix("\n")
    if raw != f"{digest}\n".encode() or not _valid_digest(digest):
        raise ValueError(_CURRENT_INVALID)
    return require_selected_runtime(runtime_root / digest, expected_build=expected_build)


def activate_runtime(common: Path, runtime: Path) -> SelectedRuntime:
    """Validate ``runtime`` and atomically select its content-addressed identity."""
    common_root = common.resolve()
    runtime_root = common_root / "ethos" / "runtime"
    if runtime.is_symlink():
        raise ValueError(_CURRENT_TARGET_INVALID)
    candidate = runtime.resolve()
    if candidate.parent != runtime_root:
        raise ValueError(_CURRENT_TARGET_INVALID)
    selected = require_selected_runtime(candidate)
    release = accepted_release_candidate(
        selected.build,
        wheel_sha256=selected.wheel_sha256,
    )
    require_runtime_identity_attested(
        common_root,
        accepted_runtime_candidate(
            release,
            runtime_digest=selected.digest,
            python_abi=selected.python_abi,
            platform=platform.system().lower(),
        ),
    )
    runtime_root.mkdir(parents=True, exist_ok=True)
    staging = runtime_root / f".{_SELECTOR.lower()}-{uuid.uuid4().hex}"
    try:
        staging.write_text(f"{selected.digest}\n", encoding="ascii", newline="\n")
        staging.replace(runtime_root / _SELECTOR)
    finally:
        staging.unlink(missing_ok=True)
    return current_runtime(common_root, expected_build=selected.build)


def restore_runtime_selection(common: Path, previous: bytes | None) -> None:
    """Restore the exact prior selector bytes after failed activation."""
    selector = common.resolve() / "ethos" / "runtime" / _SELECTOR
    if previous is None:
        selector.unlink(missing_ok=True)
        return
    staging = selector.parent / f".{_SELECTOR.lower()}-{uuid.uuid4().hex}"
    try:
        staging.write_bytes(previous)
        staging.replace(selector)
    finally:
        staging.unlink(missing_ok=True)


def runtime_command(root: Path, *arguments: str) -> str:
    """Render one shell command through the repository's selected runtime."""
    selected = current_runtime(Path(git_common_dir(root.resolve())))
    return shlex.join((selected.entrypoint.as_posix(), *arguments))


def require_selected_runtime(
    runtime: Path,
    *,
    expected_build: BuildIdentity | None = None,
    expected_digest: str | None = None,
    expected_wheel_sha256: str | None = None,
    expected_python_abi: str | None = None,
) -> SelectedRuntime:
    """Validate one immutable package runtime and return its executable identity."""
    digest = runtime.name
    if not _valid_digest(digest) or runtime.is_symlink() or not runtime.is_dir():
        raise ValueError(_CURRENT_TARGET_INVALID)
    manifest = runtime / "manifest.json"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError) as error:
        raise ValueError(_MANIFEST_INVALID) from error
    python = runtime_python(runtime / "python")
    entrypoint = runtime_entrypoint(runtime / "python")
    build = _manifest_build(payload)
    wheel = str(payload.get("wheel_sha256") or "")
    abi = str(payload.get("python_abi") or "")
    python_version = str(payload.get("python_version") or "")
    python_implementation = str(payload.get("python_implementation") or "")
    dependency_lock_sha256 = str(payload.get("dependency_lock_sha256") or "")
    platform_name = str(payload.get("platform") or "")
    files = payload.get("runtime_files")
    expected_files = {
        path.relative_to(runtime).as_posix(): _sha256(path)
        for path in (python, entrypoint)
        if path.is_file()
    }
    if (
        payload.get("schema_version") != 4
        or payload.get("runtime_digest") != digest
        or (expected_digest is not None and digest != expected_digest)
        or not _valid_digest(wheel)
        or not abi
        or platform_name != platform.system().lower()
        or build is None
        or (expected_build is not None and build != expected_build)
        or (expected_wheel_sha256 is not None and wheel != expected_wheel_sha256)
        or (expected_python_abi is not None and abi != expected_python_abi)
        or not isinstance(files, dict)
        or set(expected_files)
        != {
            python.relative_to(runtime).as_posix(),
            entrypoint.relative_to(runtime).as_posix(),
        }
        or files != expected_files
        or not _entrypoint_bound_to_runtime(entrypoint, python)
    ):
        raise ValueError(_MANIFEST_INVALID)
    try:
        environment = runtime_environment(
            python_abi=abi,
            python_version=python_version,
            python_implementation=python_implementation,
            dependency_lock_sha256=dependency_lock_sha256,
            platform_name=platform_name,
        )
    except ValueError as error:
        raise ValueError(_MANIFEST_INVALID) from error
    if (
        runtime_digest(
            wheel_sha256=wheel,
            build=build,
            environment=environment,
        )
        != digest
    ):
        raise ValueError(_MANIFEST_INVALID)
    return SelectedRuntime(
        root=runtime,
        digest=digest,
        python=python,
        entrypoint=entrypoint,
        manifest=manifest,
        wheel_sha256=wheel,
        python_abi=abi,
        python_version=python_version,
        python_implementation=python_implementation,
        dependency_lock_sha256=dependency_lock_sha256,
        platform=platform_name,
        build=build,
    )


def runtime_entrypoint(interpreter_home: Path) -> Path:
    """Return the ETHOS entrypoint inside one owned interpreter home."""
    directory = interpreter_home / ("Scripts" if os.name == "nt" else "bin")
    return directory / ("ethos.exe" if os.name == "nt" else "ethos")


def runtime_python(interpreter_home: Path) -> Path:
    """Return the executable inside one owned interpreter home."""
    return interpreter_home / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _entrypoint_bound_to_runtime(entrypoint: Path, python: Path) -> bool:
    if os.name == "nt":
        return entrypoint.is_file()
    try:
        return entrypoint.read_text(encoding="utf-8").splitlines()[0] == f"#!{python}"
    except (OSError, UnicodeError, IndexError):
        return False


def _manifest_build(payload: dict[str, object]) -> BuildIdentity | None:
    projection = {
        "schema_version": 1,
        "product_version": payload.get("product_version"),
        "distribution_version": payload.get("distribution_version"),
        "source_commit": payload.get("source_commit"),
        "source_tree": payload.get("source_tree"),
        "channel": payload.get("channel"),
        "acceptance_state": payload.get("acceptance_state"),
    }
    try:
        return load_build_identity_bytes(
            (json.dumps(projection, sort_keys=True, separators=(",", ":")) + "\n").encode()
        )
    except ValueError:
        return None


def _valid_digest(value: str) -> bool:
    return len(value) == _DIGEST_LENGTH and not set(value) - _HEX


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
