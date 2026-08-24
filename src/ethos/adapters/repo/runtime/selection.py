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
from ethos.adapters.repo.hook.source_identity import RuntimeSourceIdentity

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
    source: RuntimeSourceIdentity


def current_runtime(
    common: Path,
    *,
    expected_source: RuntimeSourceIdentity | None = None,
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
    return require_selected_runtime(runtime_root / digest, expected_source=expected_source)


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
    runtime_root.mkdir(parents=True, exist_ok=True)
    staging = runtime_root / f".{_SELECTOR.lower()}-{uuid.uuid4().hex}"
    try:
        staging.write_text(f"{selected.digest}\n", encoding="ascii", newline="\n")
        staging.replace(runtime_root / _SELECTOR)
    finally:
        staging.unlink(missing_ok=True)
    return current_runtime(common_root, expected_source=selected.source)


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
    expected_source: RuntimeSourceIdentity | None = None,
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
    python = runtime_python(runtime / "venv")
    entrypoint = runtime_entrypoint(runtime / "venv")
    source = _manifest_source(payload)
    wheel = str(payload.get("wheel_sha256") or "")
    abi = str(payload.get("python_abi") or "")
    files = payload.get("runtime_files")
    expected_files = {
        path.relative_to(runtime).as_posix(): _sha256(path)
        for path in (python, entrypoint)
        if path.is_file()
    }
    if (
        payload.get("schema_version") != 2
        or payload.get("runtime_digest") != digest
        or (expected_digest is not None and digest != expected_digest)
        or not _valid_digest(wheel)
        or not abi
        or payload.get("platform") != platform.system().lower()
        or source is None
        or (expected_source is not None and source != expected_source)
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
    return SelectedRuntime(
        root=runtime,
        digest=digest,
        python=python,
        entrypoint=entrypoint,
        manifest=manifest,
        wheel_sha256=wheel,
        python_abi=abi,
        source=source,
    )


def runtime_entrypoint(venv: Path) -> Path:
    """Return the platform entrypoint inside one runtime environment."""
    directory = venv / ("Scripts" if os.name == "nt" else "bin")
    return directory / ("ethos.exe" if os.name == "nt" else "ethos")


def runtime_python(venv: Path) -> Path:
    """Return the platform Python executable inside one runtime environment."""
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _entrypoint_bound_to_runtime(entrypoint: Path, python: Path) -> bool:
    if os.name == "nt":
        return entrypoint.is_file()
    try:
        return entrypoint.read_text(encoding="utf-8").splitlines()[0] == f"#!{python}"
    except (OSError, UnicodeError, IndexError):
        return False


def _manifest_source(payload: dict[str, object]) -> RuntimeSourceIdentity | None:
    commit = str(payload.get("source_commit") or "")
    tree = str(payload.get("source_tree") or "")
    if not all(len(value) in {40, 64} and not set(value) - _HEX for value in (commit, tree)):
        return None
    return RuntimeSourceIdentity(commit=commit, tree=tree)


def _valid_digest(value: str) -> bool:
    return len(value) == _DIGEST_LENGTH and not set(value) - _HEX


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
