"""Resolve immutable wheel, project, interpreter, and build-tool inputs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import uuid
from importlib.metadata import PackageNotFoundError
from importlib.metadata import distribution
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse

import nodejs_wheel

from ethos.adapters.repo.runtime.materialization.node_package_supply import (
    resolve_node_package_supply,
)
from ethos.adapters.repo.runtime.materialization.python_environment import file_sha256
from ethos.adapters.repo.runtime.materialization.python_environment import observe_python_facts
from ethos.adapters.repo.runtime.materialization.python_environment import same_python_path
from ethos.adapters.repo.runtime.selection import SelectedRuntime
from ethos.adapters.repo.runtime.selection import require_selected_runtime


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def require_runtime_wheel_provenance() -> None:
    """Validate that the current package can supply one provenance-bound wheel."""
    source = Path(__file__).resolve().parents[6]
    if not (source / "pyproject.toml").is_file():
        resolve_runtime_wheel(source, Path())


def resolve_node_executable(
    *,
    package_root: Path | None = None,
    platform_name: str | None = None,
) -> Path:
    """Return the validated Node executable from the locked package supply."""
    root = package_root or Path(str(nodejs_wheel.__file__)).resolve().parent
    platform = platform_name or os.name
    node = root / "node.exe" if platform == "nt" else root / "bin/node"
    if not node.is_file() or (platform != "nt" and not os.access(node, os.X_OK)):
        _fail(f"package-local Node executable is unavailable: {node}")
    return node


def resolve_runtime_wheel(
    source: Path,
    wheel_dir: Path,
    *,
    python: Path | None = None,
) -> Path:
    """Resolve exactly one source-built, managed, or installed wheel."""
    if (source / "pyproject.toml").is_file():
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
                python=python,
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
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
            _fail("hook_runtime_wheel_provenance_missing")
        wheel = Path(urllib.request.url2pathname(parsed.path))
    except (AttributeError, OSError, PackageNotFoundError, ValueError) as error:
        _fail("hook_runtime_wheel_provenance_missing", error)
    if not wheel.is_file() or wheel.suffix != ".whl":
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


def resolve_locked_environment_python(project: Path) -> Path:
    """Return the Python owned by one project's exact root virtual environment."""
    environment = project.resolve() / ".venv"
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    python = environment / relative
    if not python.is_file():
        _fail(f"hook_runtime_locked_environment_invalid:{python}")
    try:
        facts = observe_python_facts(python)
        if not same_python_path(facts["executable"], python) or not same_python_path(
            facts["prefix"], environment
        ):
            _fail(f"hook_runtime_locked_environment_invalid:{python}")
    except (KeyError, OSError, ValueError) as error:
        _fail(f"hook_runtime_locked_environment_invalid:{python}", error)
    return python


def is_selected_runtime_source(source: Path) -> bool:
    """Return whether the invoking package belongs to an immutable selected runtime."""
    return _selected_runtime_source(source) is not None


def run_runtime_tool(
    source: Path,
    *args: str,
    python: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run locked uv through the current authenticated Python interpreter."""
    executable = python or Path(sys.executable)
    prefix = (
        Path(sys.prefix)
        if same_python_path(executable.resolve(), Path(sys.executable).resolve())
        else Path(observe_python_facts(executable)["prefix"])
    )
    environment: dict[str, str] = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "UV_LINK_MODE": "copy",
        "UV_NO_CACHE": "1",
        "UV_OFFLINE": "1",
        "VIRTUAL_ENV": prefix.as_posix(),
    }
    environment.pop("ETHOS_UV_CACHE_DIR", None)
    environment.pop("UV_CACHE_DIR", None)
    if (source / "package-lock.json").is_file():
        environment["ETHOS_NODE_PACKAGE_SUPPLY"] = resolve_node_package_supply(source).as_posix()
    completed = subprocess.run(
        _uv_module_command(executable, *args),
        cwd=source,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    if completed.returncode:
        raise ValueError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or "hook_runtime_materialize_failed"
        )
    return completed


def _managed_runtime_wheel(source: Path) -> Path | None:
    selected = _selected_runtime_source(source)
    if selected is None:
        return None
    runtime = selected.root
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


def _selected_runtime_source(source: Path) -> SelectedRuntime | None:
    prefix = Path(sys.prefix)
    runtime = prefix.parent
    try:
        source.resolve().relative_to(prefix.resolve())
    except ValueError:
        return None
    if prefix.name != "python" or runtime.parent.name != "runtime":
        return None
    return require_selected_runtime(runtime)


def _uv_module_command(python: Path, *arguments: str) -> tuple[str, ...]:
    return (python.as_posix(), "-B", "-I", "-m", "uv", *arguments)
