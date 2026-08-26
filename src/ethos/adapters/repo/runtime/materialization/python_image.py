"""Construct one relocatable Python image for an immutable ETHOS runtime."""

from __future__ import annotations

import json
import os
import shutil
from importlib.metadata import distributions
from pathlib import Path
from typing import NoReturn

from ethos.adapters.repo.runtime.materialization.input_resolution import run_runtime_tool
from ethos.adapters.repo.runtime.materialization.python_environment import file_sha256
from ethos.adapters.repo.runtime.materialization.python_environment import observe_python_facts
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_python


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def materialize_python_image(
    target: Path,
    source: Path,
    interpreter: Path,
    wheel: Path,
    work: Path,
    *,
    python_facts: dict[str, str] | None = None,
    locked: bool,
) -> None:
    """Build a relocatable Python image from exact interpreter and wheel inputs."""
    facts = python_facts or observe_python_facts(interpreter)
    home = Path(facts["base_prefix"])
    if facts["prefix"] != facts["base_prefix"] or not interpreter.resolve().is_relative_to(
        home.resolve()
    ):
        _fail("hook_runtime_owned_interpreter_unavailable")
    _copy_python_runtime(home, interpreter, target, facts["python_version"])
    python = runtime_python(target)
    if not python.is_file():
        _fail("hook_runtime_python_missing")
    if locked:
        install_locked_runtime(source, work, python, wheel)
    else:
        _require_package_runtime_source(source, interpreter, wheel, facts)
    _remove_non_runtime_residue(target)
    _rewrite_console_scripts(target)


def install_locked_runtime(source: Path, work: Path, python: Path, wheel: Path) -> None:
    """Install the exact locked dependency closure and wheel into one image."""
    requirements = work / "locked-requirements.txt"
    commands = (
        (
            "export",
            "--locked",
            "--offline",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            requirements.as_posix(),
        ),
        (
            "pip",
            "sync",
            "--offline",
            "--break-system-packages",
            "--require-hashes",
            "--strict",
            "--python",
            python.as_posix(),
            requirements.as_posix(),
        ),
        (
            "pip",
            "install",
            "--offline",
            "--break-system-packages",
            "--no-deps",
            "--python",
            python.as_posix(),
            wheel.as_posix(),
        ),
    )
    for command in commands:
        run_runtime_tool(source, *command)


def render_console_script(name: str) -> str:
    """Render a location-independent console-script launcher."""
    return (
        "#!/bin/sh\n"
        'SCRIPT_DIR=${0%/*}; [ "$SCRIPT_DIR" = "$0" ] && SCRIPT_DIR=.\n'
        'SCRIPT_DIR=$(CDPATH= cd "$SCRIPT_DIR" && pwd)\n'
        'exec "$SCRIPT_DIR/python" -B -I -c '
        "'import sys;from importlib.metadata import entry_points;"
        'name=sys.argv.pop(1);matches=tuple(entry_points(group="console_scripts",name=name));'
        "len(matches)==1 or sys.exit(127);sys.argv[0]=name;sys.exit(matches[0].load()())' "
        f'{json.dumps(name)} "$@"\n'
    )


def _copy_python_runtime(home: Path, interpreter: Path, target: Path, version: str) -> None:
    if home.is_symlink() or not home.is_dir() or interpreter.is_symlink():
        _fail("hook_runtime_owned_interpreter_unavailable")
    target.mkdir(parents=True)
    if os.name == "nt":
        scripts = target / "Scripts"
        scripts.mkdir()
        shutil.copy2(interpreter, scripts / "python.exe")
        _copy_runtime_tree(home / "Lib", target / "Lib")
        if (home / "DLLs").is_dir():
            _copy_runtime_tree(home / "DLLs", target / "DLLs")
        for pattern in ("python*.dll", "vcruntime*.dll"):
            for library in home.glob(pattern):
                _copy_runtime_file(library, target / library.name)
        return
    binary = target / "bin/python"
    binary.parent.mkdir()
    shutil.copy2(interpreter, binary)
    major_minor = ".".join(version.split(".")[:2])
    stdlib = home / "lib" / f"python{major_minor}"
    _copy_runtime_tree(stdlib, target / "lib" / stdlib.name)
    for library in (home / "lib").glob(f"libpython{major_minor}*"):
        if library.is_file():
            _copy_runtime_file(library, target / "lib" / library.name)


def _copy_runtime_tree(source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_dir():
        _fail("hook_runtime_owned_interpreter_unavailable")
    root = source.resolve()
    for path in source.rglob("*"):
        if path.is_symlink():
            try:
                link = path.readlink()
                if link.is_absolute():
                    _fail("hook_runtime_python_symlink_invalid")
                path.resolve(strict=True).relative_to(root)
            except (OSError, RuntimeError, ValueError) as error:
                _fail("hook_runtime_python_symlink_invalid", error)
    shutil.copytree(
        source,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "ensurepip",
            "idlelib",
            "test",
            "tests",
            "tkinter",
            "turtledemo",
            "venv",
        ),
    )


def _copy_runtime_file(source: Path, target: Path) -> None:
    try:
        if source.is_symlink():
            link = source.readlink()
            if link.is_absolute():
                _fail("hook_runtime_python_symlink_invalid")
            resolved = source.resolve(strict=True)
            resolved.relative_to(source.parent.resolve())
        else:
            resolved = source
    except (OSError, RuntimeError, ValueError) as error:
        _fail("hook_runtime_python_symlink_invalid", error)
    if not resolved.is_file():
        _fail("hook_runtime_python_symlink_invalid")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolved, target)


def _remove_non_runtime_residue(runtime: Path) -> None:
    for path in sorted(runtime.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.name == "__pycache__" and path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.suffix == ".pyc" and path.is_file() and not path.is_symlink():
            path.unlink()


def console_script_entries(python: Path) -> dict[str, str]:
    """Discover the unique console-script entries installed in one image."""
    site_packages = (
        python.parent.parent / "Lib/site-packages"
        if os.name == "nt"
        else next(iter((python.parent.parent / "lib").glob("python*/site-packages")), None)
    )
    if site_packages is None or not site_packages.is_dir():
        _fail("hook_runtime_entrypoint_missing")
    entries: dict[str, str] = {}
    for package in distributions(path=[site_packages.as_posix()]):
        for entry in package.entry_points:
            if entry.group != "console_scripts":
                continue
            name = entry.name
            if (
                not name
                or Path(name).name != name
                or "/" in name
                or "\\" in name
                or name in entries
            ):
                _fail("hook_runtime_console_script_invalid")
            entries[name] = entry.value
    return entries


def _rewrite_console_scripts(runtime: Path) -> None:
    python = runtime_python(runtime)
    scripts = python.parent
    entries = console_script_entries(python)
    if "ethos" not in entries:
        _fail("hook_runtime_entrypoint_missing")
    if os.name == "nt":
        return
    for path in scripts.iterdir():
        if path == python:
            continue
        if path.is_symlink() or path.is_dir():
            _fail("hook_runtime_console_script_invalid")
        try:
            is_script = path.read_bytes().startswith(b"#!")
        except OSError as error:
            _fail("hook_runtime_console_script_invalid", error)
        if is_script:
            path.unlink()
    for name in sorted(entries):
        script = scripts / name
        if script.exists():
            _fail("hook_runtime_console_script_invalid")
        script.write_text(render_console_script(name), encoding="utf-8", newline="\n")
        script.chmod(0o755)


def _require_package_runtime_source(
    source: Path,
    interpreter: Path,
    wheel: Path,
    python_facts: dict[str, str],
) -> None:
    runtime = Path(python_facts["prefix"]).parent
    selected = require_selected_runtime(runtime)
    if selected.python.resolve() != interpreter.resolve():
        _fail("hook_runtime_package_interpreter_stale")
    if selected.wheel_sha256 != file_sha256(wheel):
        _fail("hook_runtime_package_wheel_stale")
    if selected.dependency_lock_sha256 != file_sha256(source / "uv.lock"):
        _fail("hook_runtime_package_lock_stale")
