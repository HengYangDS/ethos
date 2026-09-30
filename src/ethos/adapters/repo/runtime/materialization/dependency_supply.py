"""Project a lock-current Python environment into an immutable runtime image."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import NoReturn

from ethos.adapters.repo.runtime.materialization.input_resolution import run_runtime_tool
from ethos.adapters.repo.runtime.materialization.python_environment import file_sha256
from ethos.adapters.repo.runtime.materialization.python_environment import observe_python_facts
from ethos.adapters.repo.runtime.materialization.python_environment import same_python_identity
from ethos.adapters.repo.runtime.materialization.python_environment import same_python_path

_SUPPLY_OBSERVATION = """
import hashlib
import json
import os
import sys
from importlib.metadata import distributions
from pathlib import Path

prefix = Path(sys.prefix).resolve()
files = {}
for distribution in distributions():
    for entry in distribution.files or ():
        path = Path(os.path.abspath(distribution.locate_file(entry)))
        if path.is_symlink() or not path.is_file():
            raise ValueError(path)
        relative = path.relative_to(prefix).as_posix()
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
print(json.dumps({"prefix": prefix.as_posix(), "files": files}, sort_keys=True))
"""


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def prepare_locked_requirements(
    source: Path,
    work: Path,
    source_python: Path,
    *,
    require_build_tools: bool = False,
) -> Path:
    """Verify one invocation environment and export its production lock closure."""
    sync_arguments = [
        "sync",
        "--locked",
        "--offline",
        "--check",
        "--active",
        "--no-install-project",
        "--inexact",
    ]
    if not require_build_tools:
        sync_arguments.insert(3, "--no-dev")
    run_runtime_tool(
        source,
        *sync_arguments,
        python=source_python,
    )
    requirements = work / "pylock.toml"
    run_runtime_tool(
        source,
        "export",
        "--locked",
        "--offline",
        "--no-dev",
        "--no-emit-project",
        "--format",
        "pylock.toml",
        "--output-file",
        requirements.as_posix(),
        python=source_python,
    )
    if not requirements.is_file():
        _fail("hook_runtime_locked_requirements_missing")
    return requirements


def install_locked_runtime(
    source: Path,
    source_python: Path,
    target_python: Path,
    wheel: Path,
    requirements: Path,
) -> None:
    """Install locked artifacts natively, never infer them from installed names."""
    source_facts = observe_python_facts(source_python)
    target_facts = observe_python_facts(target_python)
    if same_python_path(source_facts["prefix"], target_facts["prefix"]):
        _fail("hook_runtime_dependency_supply_alias")
    if not same_python_identity(source_facts, target_facts):
        _fail("hook_runtime_dependency_supply_incompatible")
    commands = (
        (
            "pip",
            "sync",
            "--offline",
            "--no-config",
            "--preview-features",
            "pylock",
            "--break-system-packages",
            "--require-hashes",
            "--strict",
            "--reinstall",
            "--no-build",
            "--python",
            target_python.as_posix(),
            requirements.as_posix(),
        ),
        (
            "pip",
            "install",
            "--offline",
            "--no-config",
            "--break-system-packages",
            "--no-deps",
            "--reinstall",
            "--python",
            target_python.as_posix(),
            wheel.as_posix(),
        ),
    )
    run_runtime_tool(source, *commands[0], python=source_python, use_cache=True)
    run_runtime_tool(source, *commands[1], python=source_python)


def project_dependency_supply(source_python: Path, target_python: Path) -> None:
    """Copy a validated sealed runtime's closure between congruent prefixes."""
    source_prefix, files = observe_dependency_supply(source_python)
    source_facts = observe_python_facts(source_python)
    target_facts = observe_python_facts(target_python)
    target_prefix = Path(target_facts["prefix"]).resolve()
    if not same_python_path(source_prefix, Path(source_facts["prefix"]).resolve()):
        _fail("hook_runtime_dependency_supply_invalid")
    if not same_python_identity(source_facts, target_facts):
        _fail("hook_runtime_dependency_supply_incompatible")
    if same_python_path(source_prefix, target_prefix):
        _fail("hook_runtime_dependency_supply_alias")
    projection: list[tuple[Path, Path, str]] = []
    for relative, expected_sha256 in files:
        source = source_prefix / relative
        target = target_prefix / relative
        if (
            source.is_symlink()
            or not source.is_file()
            or not source.resolve().is_relative_to(source_prefix)
            or file_sha256(source) != expected_sha256
            or target.is_symlink()
            or not target.resolve().is_relative_to(target_prefix)
        ):
            _fail("hook_runtime_dependency_supply_invalid")
        projection.append((source, target, expected_sha256))
    for source, target, expected_sha256 in projection:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if file_sha256(target) != expected_sha256:
            _fail("hook_runtime_dependency_supply_invalid")


def observe_dependency_supply(python: Path) -> tuple[Path, tuple[tuple[Path, str], ...]]:
    """Observe already validated runtime bytes without claiming artifact origin."""
    completed = subprocess.run(
        (
            python.as_posix(),
            "-B",
            "-I",
            "-c",
            _SUPPLY_OBSERVATION,
        ),
        capture_output=True,
        check=False,
        text=True,
    )
    try:
        payload = json.loads(completed.stdout)
        prefix = Path(payload["prefix"])
        files = tuple(
            (Path(relative), sha256) for relative, sha256 in sorted(payload["files"].items())
        )
    except (KeyError, TypeError, ValueError) as error:
        detail = completed.stderr.strip() or completed.stdout.strip()
        _fail(f"hook_runtime_dependency_supply_invalid:{detail}", error)
    if (
        completed.returncode
        or not prefix.is_absolute()
        or not prefix.is_dir()
        or any(
            relative.is_absolute() or ".." in relative.parts or len(sha256) != 64
            for relative, sha256 in files
        )
    ):
        detail = completed.stderr.strip() or completed.stdout.strip()
        _fail(f"hook_runtime_dependency_supply_invalid:{detail}")
    return prefix, files
