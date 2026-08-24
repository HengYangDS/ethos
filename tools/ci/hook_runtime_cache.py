"""Test-only immutable package-runtime cache for governed repository fixtures."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from filelock import FileLock

import ethos.adapters.repo.hook_runtime_install as hook_runtime_install
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.source_identity import RuntimeSourceIdentity

if TYPE_CHECKING:
    import pytest


def session_hook_runtime_cache_root(base: Path) -> Path:
    """Return one cache root shared by all xdist workers in a pytest run."""
    run_root = base.parent if base.name.startswith("popen-gw") else base
    return run_root / "ethos-hook-runtime-cache"


def warm_session_hook_runtime_cache(
    cache_root: Path,
    *,
    expected_source: RuntimeSourceIdentity,
) -> None:
    """Publish the shared template before pytest-xdist workers start."""
    source = Path(hook_runtime_install.__file__).resolve().parents[4]
    templates = _templates(cache_root, source, expected_source)
    with FileLock(templates / ".runtime.lock"):
        if _runtime_template(templates, expected_source) is not None:
            return
        with tempfile.TemporaryDirectory(prefix="bootstrap-", dir=cache_root) as directory:
            repo = Path(directory)
            subprocess.run(
                ("git", "init", "-q", "-b", "dev", repo.as_posix()),
                check=True,
                capture_output=True,
                text=True,
            )
            built = hook_runtime_install.materialize_hook_runtime(
                repo,
                Path(sys.executable),
                expected_source=expected_source,
            ).parent
            _adopt_runtime_template(templates, built)


def install_session_hook_runtime_cache(monkeypatch: pytest.MonkeyPatch, cache_root: Path) -> None:
    """Reuse package bytes while retaining one runtime directory per Git common-dir."""
    source = Path(hook_runtime_install.__file__).resolve().parents[4]
    cache_root = _external_cache_root(cache_root, source)
    original_materialize = hook_runtime_install.materialize_hook_runtime

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
        templates = _templates(cache_root, source, expected_source)
        with FileLock(templates / ".runtime.lock"):
            runtime_template = _runtime_template(templates, expected_source)
            if runtime_template is None:
                built = original_materialize(
                    repo,
                    source_python,
                    expected_source=expected_source,
                ).parent
                runtime_template = _adopt_runtime_template(templates, built)
        target = common / "ethos" / "runtime" / runtime_template.name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            _project_runtime_template(runtime_template, target)
            _finalize_runtime(target)
        return target / "venv"

    monkeypatch.setattr(hook_runtime_install, "materialize_hook_runtime", cached_materialize)


def _templates(
    cache_root: Path,
    source: Path,
    expected_source: RuntimeSourceIdentity,
) -> Path:
    cache_root = _external_cache_root(cache_root, source)
    payload = [platform.system().lower(), expected_source.commit, expected_source.tree]
    key = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    templates = cache_root / key
    templates.mkdir(parents=True, exist_ok=True)
    return templates


def _external_cache_root(cache_root: Path, source: Path) -> Path:
    cache_root = cache_root.resolve()
    if cache_root == source or cache_root.is_relative_to(source):
        message = "test_hook_runtime_cache_inside_repository"
        raise ValueError(message)
    return cache_root


def _adopt_runtime_template(templates: Path, built: Path) -> Path:
    """Atomically move one controller-owned runtime into the shared cache."""
    target = templates / "runtime" / built.name
    if target.is_dir():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{built.name}-{uuid.uuid4().hex}"
    built.rename(staging)
    try:
        staging.rename(target)
        _finalize_runtime(target)
    except FileExistsError:
        shutil.rmtree(staging)
    except (OSError, ValueError):
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target


def _finalize_runtime(runtime: Path) -> None:
    manifest = json.loads((runtime / "manifest.json").read_text(encoding="utf-8"))
    source = RuntimeSourceIdentity(str(manifest["source_commit"]), str(manifest["source_tree"]))
    hook_runtime_install.finalize_runtime(
        runtime,
        str(manifest["runtime_digest"]),
        str(manifest["wheel_sha256"]),
        str(manifest["python_abi"]),
        source,
    )


def _runtime_template(
    templates: Path,
    expected_source: RuntimeSourceIdentity,
) -> Path | None:
    for candidate in sorted((templates / "runtime").glob("*")):
        try:
            manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
            actual_source = RuntimeSourceIdentity(
                commit=str(manifest["source_commit"]),
                tree=str(manifest["source_tree"]),
            )
            if actual_source != expected_source:
                continue
            hook_runtime_install.require_runtime(
                candidate,
                str(manifest["runtime_digest"]),
                str(manifest["wheel_sha256"]),
                str(manifest["python_abi"]),
                actual_source,
            )
        except (KeyError, OSError, TypeError, ValueError):
            continue
        return candidate
    return None


def _project_runtime_template(source: Path, target: Path) -> None:
    """Create a small mutable venv shell over shared immutable site-packages."""
    target.mkdir()
    shutil.copy2(source / "manifest.json", target / "manifest.json")
    source_venv = source / "venv"
    target_venv = target / "venv"
    target_venv.mkdir()
    candidates = tuple(source_venv.glob("lib/python*/site-packages")) + tuple(
        source_venv.glob("Lib/site-packages")
    )
    if len(candidates) != 1 or not candidates[0].is_dir():
        message = "test_hook_runtime_site_packages_invalid"
        raise ValueError(message)
    source_site = candidates[0]
    shared_root = source_site.relative_to(source_venv).parts[0]
    for child in source_venv.iterdir():
        if child.name == shared_root:
            continue
        destination = target_venv / child.name
        if child.is_dir():
            shutil.copytree(child, destination)
        else:
            shutil.copy2(child, destination)
    target_site = target_venv / source_site.relative_to(source_venv)
    target_site.mkdir(parents=True)
    (target_site / "ethos-runtime-cache.pth").write_text(
        source_site.resolve().as_posix() + "\n",
        encoding="utf-8",
        newline="\n",
    )
