"""Select and invoke one immutable Git-common ETHOS runtime."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple

from filelock import FileLock

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import canonical_architecture
from ethos.adapters.repo.runtime.manifest import load_runtime_manifest_bytes
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.transition import require_release_identity_attested
from ethos.repository.release.admission import accepted_release_identity
from ethos.repository.release.identity import is_release_build

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ethos.repository.release.identity import BuildIdentity

_SELECTOR = "CURRENT"
_CURRENT_MISSING = "hook_runtime_current_missing"
_CURRENT_INVALID = "hook_runtime_current_invalid"
_CURRENT_TARGET_INVALID = "hook_runtime_current_target_invalid"
_MANIFEST_INVALID = "hook_runtime_manifest_invalid"
_CURRENT_STALE = "hook_runtime_current_stale"
_UNSPECIFIED = object()


class SelectedRuntime(NamedTuple):
    """One validated immutable runtime selected for a Git common directory."""

    root: Path
    digest: str
    python: Path
    manifest: Path
    wheel_sha256: str
    python_abi: str
    python_version: str
    python_implementation: str
    dependency_lock_sha256: str
    platform: str
    architecture: str
    build: BuildIdentity


def current_runtime(
    common: Path,
    *,
    expected_build: BuildIdentity | None = None,
) -> SelectedRuntime:
    """Read and validate the canonical runtime selected by ``CURRENT``."""
    runtime_root, digest = _selected_runtime_root(common)
    return require_selected_runtime(runtime_root / digest, expected_build=expected_build)


def _selected_runtime_root(common: Path) -> tuple[Path, str]:
    common_root = common.resolve()
    ethos_root = common_root / "ethos"
    runtime_root = ethos_root / "runtime"
    if ethos_root.is_symlink() or runtime_root.is_symlink():
        raise ValueError(_CURRENT_TARGET_INVALID)
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
    return runtime_root, digest


def activate_runtime(
    common: Path,
    runtime: Path,
    *,
    expected_current: bytes | object | None = _UNSPECIFIED,
) -> SelectedRuntime:
    """Validate ``runtime`` and atomically select its content-addressed identity."""
    common_root = common.resolve()
    runtime_root = common_root / "ethos" / "runtime"
    if runtime.is_symlink():
        raise ValueError(_CURRENT_TARGET_INVALID)
    candidate = runtime.resolve()
    if candidate.parent != runtime_root:
        raise ValueError(_CURRENT_TARGET_INVALID)
    runtime_root.mkdir(parents=True, exist_ok=True)
    with FileLock(_selection_lock_path(common_root).as_posix()):
        selected = require_selected_runtime(candidate)
        release = (
            accepted_release_identity(selected.build, wheel_sha256=selected.wheel_sha256)
            if is_release_build(selected.build)
            else None
        )
        require_release_identity_attested(common_root, release)
        desired = f"{selected.digest}\n".encode("ascii")
        current = _selector_bytes(runtime_root / _SELECTOR)
        if expected_current is not _UNSPECIFIED and current != expected_current:
            raise ValueError(_CURRENT_STALE)
        _require_release_runtime_closure_unique(common_root, selected)
        _replace_selector(runtime_root / _SELECTOR, desired)
        return current_runtime(common_root, expected_build=selected.build)


def restore_runtime_selection(
    common: Path,
    previous: bytes | None,
    *,
    expected_current: bytes | object | None = _UNSPECIFIED,
) -> None:
    """Restore the exact prior selector bytes after failed activation."""
    common_root = common.resolve()
    selector = common_root / "ethos" / "runtime" / _SELECTOR
    with FileLock(_selection_lock_path(common_root).as_posix()):
        if expected_current is not _UNSPECIFIED and _selector_bytes(selector) != expected_current:
            raise ValueError(_CURRENT_STALE)
        _replace_selector(selector, previous)


@contextmanager
def runtime_selection_transaction(
    common: Path,
    *,
    expected_current: bytes,
) -> Iterator[None]:
    """Guard selector-dependent effects with the canonical lock and exact CAS."""
    common_root = common.resolve()
    selector = common_root / "ethos" / "runtime" / _SELECTOR
    with FileLock(_selection_lock_path(common_root).as_posix()):
        if _selector_bytes(selector) != expected_current:
            raise ValueError(_CURRENT_STALE)
        yield


def runtime_command(root: Path, *arguments: str) -> str:
    """Render one shell command through the repository's selected runtime."""
    selected = current_runtime(Path(git_common_dir(root.resolve())).resolve())
    return shlex.join((selected.python.as_posix(), "-B", "-I", "-m", "ethos.cli", *arguments))


def legacy_runtime_migration_source(common: Path) -> tuple[str, str] | None:
    """Observe exact schema-v2 source coordinates without executing that runtime."""
    try:
        runtime_root, digest = _selected_runtime_root(common)
        runtime = runtime_root / digest
        manifest = runtime / "manifest.json"
        if runtime.is_symlink() or manifest.is_symlink() or not manifest.is_file():
            return None
        raw = manifest.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        fields = {
            "schema_version",
            "runtime_digest",
            "wheel_sha256",
            "python_abi",
            "platform",
            "source_commit",
            "source_tree",
            "runtime_files",
        }
        files = payload["runtime_files"]
        if (
            not isinstance(payload, dict)
            or set(payload) != fields
            or payload["schema_version"] != 2
            or payload["runtime_digest"] != digest
            or payload["platform"] != platform.system().lower()
            or not isinstance(files, dict)
            or raw != json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        ):
            return None
        names = {str(path) for path in files}
        if len(names) != 2:
            return None
        observed = {
            name: hashlib.sha256((runtime / name).read_bytes()).hexdigest() for name in names
        }
        source = (str(payload["source_commit"]), str(payload["source_tree"]))
        valid_source = all(_valid_source_identity(value) for value in source)
    except (KeyError, OSError, TypeError, UnicodeError, ValueError):
        return None
    return source if observed == files and valid_source else None


def require_selected_runtime(
    runtime: Path,
    *,
    expected_root: Path | None = None,
    expected_build: BuildIdentity | None = None,
) -> SelectedRuntime:
    """Validate one immutable package runtime and return its executable identity."""
    digest = (expected_root or runtime).name
    if (
        not _valid_digest(digest)
        or (expected_root is None and runtime.name != digest)
        or runtime.is_symlink()
        or not runtime.is_dir()
    ):
        raise ValueError(_CURRENT_TARGET_INVALID)
    manifest = runtime / "manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError(_MANIFEST_INVALID)
    try:
        identity = load_runtime_manifest_bytes(manifest.read_bytes())
    except (OSError, ValueError) as error:
        raise ValueError(_MANIFEST_INVALID) from error
    python = runtime_python(runtime / "python")
    expected_files = runtime_file_inventory(runtime)
    if (
        identity.digest != digest
        or identity.environment.platform != platform.system().lower()
        or identity.environment.architecture != canonical_architecture(platform.machine())
        or (expected_build is not None and identity.build != expected_build)
        or identity.runtime_files != expected_files
    ):
        raise ValueError(_MANIFEST_INVALID)
    return SelectedRuntime(
        runtime,
        digest,
        python,
        manifest,
        identity.wheel_sha256,
        *identity.environment,
        identity.build,
    )


def runtime_python(interpreter_home: Path) -> Path:
    """Return the executable inside one owned interpreter home."""
    return (
        interpreter_home / "python.exe"
        if os.name == "nt"
        else runtime_scripts(interpreter_home) / "python"
    )


def runtime_scripts(interpreter_home: Path) -> Path:
    """Return the console-script directory inside one owned interpreter home."""
    return interpreter_home / ("Scripts" if os.name == "nt" else "bin")


def _selector_bytes(selector: Path) -> bytes | None:
    if selector.is_symlink():
        raise ValueError(_CURRENT_INVALID)
    try:
        return selector.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ValueError(_CURRENT_INVALID) from error


def _replace_selector(selector: Path, value: bytes | None) -> None:
    if selector.parent.is_symlink() or selector.is_symlink():
        raise ValueError(_CURRENT_INVALID)
    if value is None:
        selector.unlink(missing_ok=True)
        return
    selector.parent.mkdir(parents=True, exist_ok=True)
    staging = selector.parent / f".{selector.name.lower()}-{uuid.uuid4().hex}"
    try:
        staging.write_bytes(value)
        staging.replace(selector)
    finally:
        staging.unlink(missing_ok=True)


def _selection_lock_path(common: Path) -> Path:
    return common / "ethos" / "runtime-selection.lock"


def _require_release_runtime_closure_unique(
    common: Path,
    candidate: SelectedRuntime,
) -> None:
    if not is_release_build(candidate.build):
        return
    runtime_root = common / "ethos" / "runtime"
    for path in runtime_root.iterdir():
        if path.name in {_SELECTOR, candidate.digest} or not _valid_digest(path.name):
            continue
        try:
            existing = require_selected_runtime(path)
        except ValueError:
            continue
        if (
            existing.build == candidate.build
            and existing.python_abi == candidate.python_abi
            and existing.platform == candidate.platform
            and existing.architecture == candidate.architecture
            and existing.digest != candidate.digest
        ):
            message = "release_runtime_identity_conflict"
            raise ValueError(message)


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and not set(value) - set("0123456789abcdef")


def _valid_source_identity(value: str) -> bool:
    return len(value) in {40, 64} and not set(value) - set("0123456789abcdef")
