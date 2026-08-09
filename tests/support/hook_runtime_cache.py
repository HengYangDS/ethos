"""Test-only immutable package-runtime cache for governed repository fixtures."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.repo.hook_runtime as hook_runtime
import ethos.adapters.repo.hook_runtime_install as hook_runtime_install

if TYPE_CHECKING:
    import pytest


def install_session_hook_runtime_cache(monkeypatch: pytest.MonkeyPatch, cache_root: Path) -> None:
    """Reuse package bytes while retaining one runtime directory per Git common-dir."""
    source = Path(hook_runtime.__file__).resolve().parents[4]
    cache_root = cache_root.resolve()
    if cache_root == source or cache_root.is_relative_to(source):
        message = "test_hook_runtime_cache_inside_repository"
        raise ValueError(message)
    cache_key = _cache_key(source, Path(sys.executable))
    templates = cache_root / cache_key
    wheel_lock = threading.Lock()
    original_materialize = hook_runtime.materialize_hook_runtime
    original_wheel = hook_runtime_install.resolve_runtime_wheel

    def cached_materialize(repo: Path, source_python: Path) -> Path:
        if source_python.resolve() != Path(sys.executable).resolve():
            return original_materialize(repo, source_python)
        cache_wheels = templates / "wheel"

        def cached_wheel(source: Path, wheel_dir: Path) -> Path:
            with wheel_lock:
                wheel = next(cache_wheels.glob("*.whl"), None)
                if wheel is None:
                    built = original_wheel(source, templates / "wheel-build")
                    cache_wheels.mkdir(parents=True, exist_ok=True)
                    wheel = cache_wheels / built.name
                    temporary = wheel.with_suffix(f"{wheel.suffix}.tmp")
                    shutil.copy2(built, temporary)
                    temporary.replace(wheel)
            wheel_dir.mkdir(parents=True, exist_ok=True)
            destination = wheel_dir / wheel.name
            shutil.copy2(wheel, destination)
            return destination

        with monkeypatch.context() as local:
            local.setattr(hook_runtime_install, "resolve_runtime_wheel", cached_wheel)
            return original_materialize(repo, source_python)

    monkeypatch.setattr(hook_runtime, "materialize_hook_runtime", cached_materialize)


def _cache_key(root: Path, python: Path) -> str:
    completed = subprocess.run(
        (python.as_posix(), "-I", "-c", "import sys; print(sys.implementation.cache_tag or '')"),
        capture_output=True,
        check=True,
        text=True,
    )
    payload = {
        "platform": platform.system().lower(),
        "python_abi": completed.stdout.strip(),
        "source_digest": _source_digest(root),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _source_digest(root: Path) -> str:
    digest = hashlib.sha256()
    paths = [root / "pyproject.toml", root / "uv.lock", *sorted((root / "src").rglob("*"))]
    for path in paths:
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix().encode()
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big") + relative)
        digest.update(len(payload).to_bytes(8, "big") + payload)
    return digest.hexdigest()
