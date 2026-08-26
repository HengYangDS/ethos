"""Resolve immutable wheel, project, interpreter, and build-tool inputs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from importlib import import_module
from importlib.metadata import PackageNotFoundError
from importlib.metadata import distribution
from pathlib import Path
from typing import NoReturn
from urllib.parse import unquote
from urllib.parse import urlparse

from ethos.adapters.repo.runtime.materialization.python_environment import file_sha256
from ethos.adapters.repo.runtime.materialization.python_environment import observe_python_facts
from ethos.adapters.repo.runtime.selection import require_selected_runtime


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def require_runtime_wheel_provenance() -> None:
    """Validate that the current package can supply one provenance-bound wheel."""
    source = Path(__file__).resolve().parents[6]
    if not (source / "pyproject.toml").is_file():
        resolve_runtime_wheel(source, Path())


def resolve_runtime_wheel(source: Path, wheel_dir: Path) -> Path:
    """Resolve exactly one source-built, managed, or installed wheel."""
    if (source / "pyproject.toml").is_file():
        run_runtime_tool(source, "sync", "--locked", "--offline", "--check", "--active")
        wheel_dir.parent.mkdir(parents=True, exist_ok=True)
        if wheel_dir.exists():
            _fail("hook_runtime_wheel_invalid")
        staging = wheel_dir.parent / f".{wheel_dir.name}-{uuid.uuid4().hex}"
        try:
            run_runtime_tool(
                source,
                "build",
                "--offline",
                "--no-build-isolation",
                "--wheel",
                "--out-dir",
                staging.as_posix(),
            )
            wheels = tuple(staging.glob("ethos-*.whl"))
            if len(wheels) != 1:
                _fail("hook_runtime_wheel_invalid")
            staging.rename(wheel_dir)
            return wheel_dir / wheels[0].name
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    managed = _managed_runtime_wheel(source)
    if managed is not None:
        return managed
    try:
        metadata = distribution("ethos")
        direct_url = json.loads(metadata.read_text("direct_url.json") or "")
        parsed = urlparse(str(direct_url.get("url") or ""))
        wheel = Path(unquote(parsed.path))
    except (AttributeError, OSError, PackageNotFoundError, ValueError) as error:
        _fail("hook_runtime_wheel_provenance_missing", error)
    if parsed.scheme != "file" or not wheel.is_file() or wheel.suffix != ".whl":
        _fail("hook_runtime_wheel_provenance_missing")
    return wheel


def resolve_runtime_project(package_source: Path) -> Path:
    """Resolve the dependency-lock project carried by source or installed data."""
    required = ("pyproject.toml", "uv.lock", "VERSION")
    if all((package_source / name).is_file() for name in required):
        return package_source
    project = Path(__file__).resolve().parents[4] / "data" / "runtime-project"
    if not all((project / name).is_file() for name in required):
        _fail("hook_runtime_packaged_project_missing")
    return project


def resolve_owned_interpreter(source: Path, source_python: Path) -> Path:
    """Resolve one standalone interpreter owned by the materialized runtime."""
    resolved = source_python.resolve()
    if Path(sys.prefix).name == "python" and resolved.is_relative_to(Path(sys.prefix).resolve()):
        runtime = Path(sys.prefix).parent
        if runtime.parent.name == "runtime":
            return resolved
    executable = _uv_executable()
    environment = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    requested = observe_python_facts(source_python)["python_version"]
    command = (executable.as_posix(), "python", "find", "--managed-python", requested)
    completed = subprocess.run(
        command, cwd=source, capture_output=True, text=True, check=False, env=environment
    )
    if completed.returncode:
        installed = subprocess.run(
            (executable.as_posix(), "python", "install", "--no-bin", requested),
            cwd=source,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        if installed.returncode:
            raise ValueError(
                installed.stderr.strip()
                or installed.stdout.strip()
                or "hook_runtime_owned_interpreter_unavailable"
            )
        completed = subprocess.run(
            command, cwd=source, capture_output=True, text=True, check=False, env=environment
        )
    if completed.returncode:
        _fail("hook_runtime_owned_interpreter_unavailable")
    interpreter = Path(completed.stdout.strip()).resolve()
    facts = observe_python_facts(interpreter)
    if not interpreter.is_file() or facts["prefix"] != facts["base_prefix"]:
        _fail("hook_runtime_owned_interpreter_unavailable")
    return interpreter


def run_runtime_tool(source: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the runtime-adjacent uv executable with pinned build inputs."""
    node_root = Path(import_module("nodejs_wheel").__file__).resolve().parent
    completed = subprocess.run(
        (_uv_executable().as_posix(), *args),
        cwd=source,
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "VIRTUAL_ENV": Path(sys.prefix).as_posix(),
            "ETHOS_BUILD_NODE": (
                node_root / "bin" / ("node.exe" if os.name == "nt" else "node")
            ).as_posix(),
            "ETHOS_BUILD_NPM_CLI": (node_root / "lib/node_modules/npm/bin/npm-cli.js").as_posix(),
        },
    )
    if completed.returncode:
        raise ValueError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or "hook_runtime_materialize_failed"
        )
    return completed


def _managed_runtime_wheel(source: Path) -> Path | None:
    prefix = Path(sys.prefix)
    runtime = prefix.parent
    try:
        source.resolve().relative_to(prefix.resolve())
    except ValueError:
        return None
    if prefix.name != "python" or runtime.parent.name != "runtime":
        return None
    selected = require_selected_runtime(runtime)
    package_root = runtime.parent.parent / "packages" / selected.wheel_sha256
    if package_root.is_symlink() or not package_root.is_dir():
        _fail("hook_runtime_wheel_provenance_missing")
    wheels = tuple(
        path
        for path in package_root.glob("ethos-*.whl")
        if path.is_file() and not path.is_symlink()
    )
    if len(wheels) != 1 or file_sha256(wheels[0]) != selected.wheel_sha256:
        _fail("hook_runtime_wheel_provenance_missing")
    return wheels[0]


def _uv_executable() -> Path:
    executable = Path(sys.executable).with_name("uv.exe" if os.name == "nt" else "uv")
    if not executable.is_file():
        _fail("hook_runtime_uv_unavailable")
    return executable
