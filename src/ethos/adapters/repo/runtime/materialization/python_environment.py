"""Observed Python and dependency-lock inputs for runtime materialization."""

from __future__ import annotations

import hashlib
import json
import ntpath
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn

from ethos.adapters.repo.runtime.manifest import RuntimeEnvironment
from ethos.adapters.repo.runtime.manifest import runtime_environment

if TYPE_CHECKING:
    from collections.abc import Mapping
    from os import PathLike


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def observe_python_facts(python: Path) -> dict[str, str]:
    """Observe the exact executable, runtime identity, and prefixes of Python."""
    script = (
        "import json,platform,sys,sysconfig;print(json.dumps({"
        "'executable':sys.executable,"
        "'base_executable':getattr(sys,'_base_executable',''),"
        "'python_abi':sys.implementation.cache_tag or '',"
        "'python_version':platform.python_version(),"
        "'python_implementation':sys.implementation.name,"
        "'architecture':platform.machine(),"
        "'python_framework':sysconfig.get_config_var('PYTHONFRAMEWORK') or '',"
        "'prefix':sys.prefix,'base_prefix':sys.base_prefix}))"
    )
    completed = subprocess.run(
        (python.as_posix(), "-B", "-I", "-c", script),
        capture_output=True,
        check=False,
        text=True,
    )
    try:
        facts = {key: str(value) for key, value in json.loads(completed.stdout).items()}
    except (AttributeError, TypeError, ValueError) as error:
        _fail("hook_runtime_python_abi_invalid", error)
    required = (
        "executable",
        "base_executable",
        "python_abi",
        "python_version",
        "python_implementation",
        "architecture",
        "prefix",
        "base_prefix",
    )
    if completed.returncode or not all(facts.get(key) for key in required):
        _fail("hook_runtime_python_abi_invalid")
    return facts


def same_python_path(first: str | PathLike[str], second: str | PathLike[str]) -> bool:
    """Return whether two Python paths identify the same native object."""
    left, right = os.fspath(first), os.fspath(second)
    try:
        if Path(left).samefile(right):
            return True
    except OSError:
        pass
    if os.name == "nt":
        return ntpath.normcase(ntpath.normpath(left)) == ntpath.normcase(ntpath.normpath(right))
    return left == right


def same_python_identity(first: Mapping[str, str], second: Mapping[str, str]) -> bool:
    """Return whether two observations identify the same Python runtime kind."""
    coordinates = ("python_abi", "python_version", "python_implementation", "architecture")
    return all(first.get(key) and first[key] == second.get(key) for key in coordinates)


def python_path_within(path: str | PathLike[str], root: str | PathLike[str]) -> bool:
    """Return whether one Python path belongs to a native path boundary."""
    candidate, boundary = os.fspath(path), os.fspath(root)
    if os.name == "nt":
        candidate = ntpath.normcase(ntpath.normpath(candidate))
        boundary = ntpath.normcase(ntpath.normpath(boundary))
        try:
            return ntpath.commonpath((candidate, boundary)) == boundary
        except ValueError:
            return False
    candidate_path, boundary_path = Path(candidate), Path(boundary)
    if not candidate_path.is_absolute() or not boundary_path.is_absolute():
        return False
    return candidate_path.is_relative_to(boundary_path) or candidate_path.resolve().is_relative_to(
        boundary_path.resolve()
    )


def python_image_source_capable(source: Path, facts: Mapping[str, str]) -> bool:
    """Return whether one direct Python prefix is a copyable native image."""
    try:
        home = Path(facts["base_prefix"])
        version = facts["python_version"]
        if home.is_symlink() or not home.is_dir() or source.is_symlink() or not source.is_file():
            return False
        if os.name == "nt":
            trees = [home / "Lib"]
            dlls = home / "DLLs"
            if dlls.exists() or dlls.is_symlink():
                trees.append(dlls)
            files = tuple(home.glob("python*.dll")) + tuple(home.glob("vcruntime*.dll"))
        else:
            major_minor = ".".join(version.split(".")[:2])
            trees = [home / "lib" / f"python{major_minor}"]
            files = tuple((home / "lib").glob(f"libpython{major_minor}*"))
        return all(_copyable_python_tree(tree) for tree in trees) and all(
            _copyable_python_file(path) for path in files if path.is_file()
        )
    except (KeyError, OSError, RuntimeError, ValueError):
        return False


def _copyable_python_tree(source: Path) -> bool:
    """Validate the symlink closure of one native Python directory tree."""
    if source.is_symlink() or not source.is_dir():
        return False
    root = source.resolve()
    for path in source.rglob("*"):
        if not path.is_symlink():
            continue
        link = path.readlink()
        if link.is_absolute() or not path.resolve(strict=True).is_relative_to(root):
            return False
    return True


def _copyable_python_file(source: Path) -> bool:
    """Validate one native runtime file or prefix-relative symlink."""
    if not source.is_symlink():
        return source.is_file()
    link = source.readlink()
    return (
        not link.is_absolute()
        and source.resolve(strict=True).is_relative_to(source.parent.resolve())
        and source.resolve(strict=True).is_file()
    )


def require_python_image_source(invoked_python: Path) -> dict[str, str]:
    """Return one installed, congruent source for a relocatable Python image."""
    invoked = observe_python_facts(invoked_python)
    coordinates = ("executable", "base_executable", "prefix", "base_prefix")
    if not invoked_python.is_absolute() or not all(
        Path(invoked[key]).is_absolute() for key in coordinates
    ):
        _fail("hook_runtime_interpreter_source_unavailable")
    if not same_python_path(
        Path(invoked["executable"]).resolve(),
        invoked_python.resolve(),
    ) or not python_path_within(invoked["executable"], invoked["prefix"]):
        _fail("hook_runtime_interpreter_source_unavailable")
    base = Path(invoked["base_executable"]).resolve()
    if source_facts := _admitted_python_image_source(base, invoked):
        return source_facts
    for candidate in _installed_python_candidates(invoked_python, invoked):
        source = candidate.resolve()
        if source == base:
            continue
        source_facts = _admitted_python_image_source(source, invoked)
        if source_facts is not None:
            return source_facts
    _fail("hook_runtime_interpreter_source_unavailable")


def _admitted_python_image_source(
    source: Path,
    invoked: Mapping[str, str],
) -> dict[str, str] | None:
    """Admit one direct, congruent interpreter with a copyable native layout."""
    coordinates = ("executable", "base_executable", "prefix", "base_prefix")
    if not source.is_file():
        return None
    try:
        source_facts = observe_python_facts(source)
        if not all(Path(source_facts[key]).is_absolute() for key in coordinates):
            return None
        base_prefix = Path(source_facts["base_prefix"]).resolve()
        if (
            not same_python_path(Path(source_facts["executable"]).resolve(), source)
            or not same_python_path(Path(source_facts["base_executable"]).resolve(), source)
            or not same_python_path(source_facts["prefix"], source_facts["base_prefix"])
            or not python_path_within(source, base_prefix)
            or not same_python_identity(source_facts, invoked)
            or source_facts.get("python_framework", "")
            or not python_image_source_capable(source, source_facts)
        ):
            return None
    except (KeyError, OSError, ValueError):
        return None
    return source_facts


def _installed_python_candidates(
    invoked_python: Path,
    invoked: Mapping[str, str],
) -> tuple[Path, ...]:
    """Enumerate installed Python candidates without provisioning or network access."""
    environment: dict[str, str] = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "UV_NO_CACHE": "1",
        "UV_OFFLINE": "1",
        "UV_PYTHON_DOWNLOADS": "never",
    }
    environment.pop("VIRTUAL_ENV", None)
    command = (
        invoked_python.as_posix(),
        "-B",
        "-I",
        "-m",
        "uv",
        "python",
        "list",
        "--only-installed",
        "--output-format",
        "json",
        "--no-python-downloads",
        "--offline",
        "--no-config",
        invoked["python_version"],
    )
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            env=environment,
        )
        rows = json.loads(completed.stdout)
    except (OSError, TypeError, ValueError):
        return ()
    if completed.returncode or not isinstance(rows, list):
        return ()
    candidates: set[Path] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            return ()
        candidate = Path(row["path"])
        if candidate.is_absolute():
            candidates.add(candidate.resolve())
    return tuple(sorted(candidates, key=lambda path: path.as_posix()))


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of one exact materialization input."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observe_runtime_environment(
    source: Path,
    interpreter: Path,
    *,
    python_facts: dict[str, str] | None = None,
) -> RuntimeEnvironment:
    """Bind runtime environment identity to Python facts and the dependency lock."""
    facts = python_facts or observe_python_facts(interpreter)
    return runtime_environment(
        python_abi=facts["python_abi"],
        python_version=facts["python_version"],
        python_implementation=facts["python_implementation"],
        dependency_lock_sha256=file_sha256(source / "uv.lock"),
        architecture_name=facts["architecture"],
    )
