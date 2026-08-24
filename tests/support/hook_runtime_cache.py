"""Test-only immutable package-runtime cache for governed repository fixtures."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.repo.hook_runtime_install as hook_runtime_install
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.source_identity import RuntimeSourceIdentity

if TYPE_CHECKING:
    import pytest


def install_session_hook_runtime_cache(monkeypatch: pytest.MonkeyPatch, cache_root: Path) -> None:
    """Reuse package bytes while retaining one runtime directory per Git common-dir."""
    source = Path(hook_runtime_install.__file__).resolve().parents[4]
    cache_root = cache_root.resolve()
    if cache_root == source or cache_root.is_relative_to(source):
        message = "test_hook_runtime_cache_inside_repository"
        raise ValueError(message)
    templates = cache_root / _cache_key(source)
    wheel_lock = threading.Lock()
    runtime_lock = threading.Lock()
    runtime_templates: dict[RuntimeSourceIdentity, Path] = {}
    original_materialize = hook_runtime_install.materialize_hook_runtime
    original_wheel = hook_runtime_install.resolve_runtime_wheel

    def cached_wheel(source_root: Path, wheel_dir: Path) -> Path:
        if source_root.resolve() != source:
            return original_wheel(source_root, wheel_dir)
        cache_wheels = templates / "wheel"
        with wheel_lock:
            wheel = next(cache_wheels.glob("*.whl"), None)
            if wheel is None:
                built = original_wheel(source_root, templates / "wheel-build")
                cache_wheels.mkdir(parents=True, exist_ok=True)
                wheel = cache_wheels / built.name
                temporary = wheel.with_suffix(f"{wheel.suffix}.tmp")
                shutil.copy2(built, temporary)
                temporary.replace(wheel)
        wheel_dir.mkdir(parents=True, exist_ok=True)
        destination = wheel_dir / wheel.name
        shutil.copy2(wheel, destination)
        return destination

    def cached_materialize(
        repo: Path,
        source_python: Path,
        *,
        expected_source: RuntimeSourceIdentity,
    ) -> Path:
        canonical_source = Path(hook_runtime_install.__file__).resolve().parents[4]
        if source_python.resolve() != Path(sys.executable).resolve() or canonical_source != source:
            return original_materialize(
                repo,
                source_python,
                expected_source=expected_source,
            )
        common = Path(git_common_dir(repo))
        if (common / "ethos").is_symlink():
            return original_materialize(
                repo,
                source_python,
                expected_source=expected_source,
            )
        with runtime_lock:
            runtime_template = runtime_templates.get(expected_source)
            if runtime_template is None:
                built = original_materialize(
                    repo,
                    source_python,
                    expected_source=expected_source,
                ).parent
                runtime_template = templates / "runtime" / built.name
                runtime_template.parent.mkdir(parents=True, exist_ok=True)
                _clone_tree(built, runtime_template)
                runtime_templates[expected_source] = runtime_template
            target = common / "ethos" / "runtime" / runtime_template.name
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                _clone_tree(runtime_template, target)
                manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
                hook_runtime_install.finalize_runtime(
                    target,
                    str(manifest["runtime_digest"]),
                    str(manifest["wheel_sha256"]),
                    str(manifest["python_abi"]),
                    RuntimeSourceIdentity(
                        commit=str(manifest["source_commit"]),
                        tree=str(manifest["source_tree"]),
                    ),
                )
            return target / "venv"

    monkeypatch.setattr(hook_runtime_install, "resolve_runtime_wheel", cached_wheel)
    monkeypatch.setattr(hook_runtime_install, "materialize_hook_runtime", cached_materialize)


def _clone_tree(source: Path, target: Path) -> None:
    """Clone one immutable runtime tree without duplicating its physical bytes."""
    shutil.copytree(source, target, copy_function=os.link)
    mutable = [target / "manifest.json"]
    scripts = target / "venv" / ("Scripts" if os.name == "nt" else "bin")
    mutable.append(scripts / ("ethos.exe" if os.name == "nt" else "ethos"))
    for path in mutable:
        detached = path.with_name(f".{path.name}.detached")
        shutil.copy2(path, detached)
        detached.replace(path)


def _cache_key(root: Path) -> str:
    payload = {
        "platform": platform.system().lower(),
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
