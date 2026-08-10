"""Immutable package runtime installation for portable Git hooks."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import uuid
from importlib import import_module
from importlib.metadata import PackageNotFoundError
from importlib.metadata import distribution
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlparse

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_launcher


def materialize_hook_runtime(repo: Path, source_python: Path) -> Path:
    """Build and atomically install one wheel-qualified common-dir runtime."""
    source = Path(__file__).resolve().parents[4]
    common = Path(git_common_dir(repo))
    runtime_root = common / "ethos" / "runtime"
    work = runtime_root / f".build-{uuid.uuid4().hex}"
    wheel_dir = work / "wheel"
    try:
        python_abi = _python_abi(source_python)
        wheel = resolve_runtime_wheel(source, wheel_dir)
        wheel_sha256 = _sha256(wheel)
        digest = _runtime_digest(wheel_sha256, python_abi)
        target = runtime_root / digest
        if target.is_dir():
            _require_runtime(target, digest, wheel_sha256, python_abi)
            return target / "venv"
        staging = runtime_root / f".runtime-{digest[:12]}-{uuid.uuid4().hex}"
        try:
            if (source / "pyproject.toml").is_file():
                _run_runtime_tool(
                    source,
                    "venv",
                    "--offline",
                    "--relocatable",
                    "--python",
                    source_python.as_posix(),
                    (staging / "venv").as_posix(),
                )
            else:
                _copy_installed_runtime(staging / "venv", source_python)
            runtime_python = _venv_python(staging / "venv")
            if (source / "pyproject.toml").is_file():
                _run_runtime_tool(
                    source,
                    "pip",
                    "install",
                    "--offline",
                    "--python",
                    runtime_python.as_posix(),
                    wheel.as_posix(),
                )
            _write_manifest(staging, digest, wheel_sha256, python_abi, runtime_python)
            runtime_root.mkdir(parents=True, exist_ok=True)
            try:
                staging.rename(target)
            except FileExistsError:
                _require_runtime(target, digest, wheel_sha256, python_abi)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        _require_runtime(target, digest, wheel_sha256, python_abi)
        return target / "venv"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def require_runtime_wheel_provenance() -> None:
    """Validate that the current package can materialize a source-independent runtime."""
    source = Path(__file__).resolve().parents[4]
    if (source / "pyproject.toml").is_file():
        return
    resolve_runtime_wheel(source, Path())


def resolve_runtime_wheel(source: Path, wheel_dir: Path) -> Path:
    if (source / "pyproject.toml").is_file():
        wheel_dir.parent.mkdir(parents=True)
        _run_runtime_tool(
            source, "build", "--offline", "--wheel", "--out-dir", wheel_dir.as_posix()
        )
        wheels = tuple(wheel_dir.glob("ethos-*.whl"))
        if len(wheels) == 1:
            return wheels[0]
        message = "hook_runtime_wheel_invalid"
        raise ValueError(message)
    try:
        metadata = distribution("ethos")
        payload = json.loads(metadata.read_text("direct_url.json") or "")
        parsed = urlparse(str(payload.get("url") or ""))
        wheel = Path(unquote(parsed.path))
    except (AttributeError, OSError, PackageNotFoundError, ValueError) as error:
        message = "hook_runtime_wheel_provenance_missing"
        raise ValueError(message) from error
    if parsed.scheme != "file" or not wheel.is_file() or wheel.suffix != ".whl":
        message = "hook_runtime_wheel_provenance_missing"
        raise ValueError(message)
    return wheel


def _copy_installed_runtime(target: Path, source_python: Path) -> None:
    prefix = Path(sys.prefix)
    try:
        source_python.relative_to(prefix)
    except ValueError as error:
        message = "hook_runtime_python_prefix_invalid"
        raise ValueError(message) from error
    shutil.copytree(prefix, target, symlinks=True)


def _run_runtime_tool(source: Path, *args: str) -> None:
    """Run the exact project uv tool without PATH runtime selection."""
    executable = Path(sys.executable).with_name("uv.exe" if os.name == "nt" else "uv")
    if not executable.is_file():
        message = "hook_runtime_uv_unavailable"
        raise ValueError(message)
    node_root = Path(import_module("nodejs_wheel").__file__).resolve().parent
    completed = subprocess.run(
        (executable.as_posix(), *args),
        cwd=source,
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "ETHOS_BUILD_NODE": (
                node_root / "bin" / ("node.exe" if os.name == "nt" else "node")
            ).as_posix(),
            "ETHOS_BUILD_NPM_CLI": (node_root / "lib/node_modules/npm/bin/npm-cli.js").as_posix(),
        },
    )
    if completed.returncode:
        message = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "hook_runtime_materialize_failed"
        )
        raise ValueError(message)


def _python_abi(python: Path) -> str:
    completed = subprocess.run(
        (python.as_posix(), "-I", "-c", "import sys; print(sys.implementation.cache_tag or '')"),
        capture_output=True,
        check=False,
        text=True,
    )
    abi = completed.stdout.strip()
    if completed.returncode or not abi:
        message = "hook_runtime_python_abi_invalid"
        raise ValueError(message)
    return abi


def _runtime_digest(wheel_sha256: str, python_abi: str) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "schema_version": 1,
                "wheel_sha256": wheel_sha256,
                "python_abi": python_abi,
                "platform": platform.system().lower(),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _write_manifest(
    runtime: Path,
    digest: str,
    wheel_sha256: str,
    python_abi: str,
    python: Path,
) -> None:
    if not python.is_file():
        message = "hook_runtime_python_missing"
        raise ValueError(message)
    payload = {
        "schema_version": 1,
        "runtime_digest": digest,
        "wheel_sha256": wheel_sha256,
        "python_abi": python_abi,
        "platform": platform.system().lower(),
        "runtime_files": {python.relative_to(runtime).as_posix(): _sha256(python)},
    }
    (runtime / "manifest.json").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )


def _require_runtime(runtime: Path, digest: str, wheel_sha256: str, python_abi: str) -> None:
    manifest = runtime / "manifest.json"
    python = _venv_python(runtime / "venv")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        message = "hook_runtime_manifest_invalid"
        raise ValueError(message) from error
    files = payload.get("runtime_files")
    expected = python.relative_to(runtime).as_posix()
    if (
        payload.get("runtime_digest") != digest
        or payload.get("wheel_sha256") != wheel_sha256
        or payload.get("python_abi") != python_abi
        or payload.get("platform") != platform.system().lower()
        or not isinstance(files, dict)
        or not python.is_file()
        or files.get(expected) != _sha256(python)
    ):
        message = "hook_runtime_manifest_invalid"
        raise ValueError(message)


def runtime_locator(venv: Path) -> str:
    digest = venv.parent.name
    executable = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    return f"../ethos/runtime/{digest}/venv/{executable}"


def replace_launchers(hooks: Path, locator: str) -> None:
    """Replace each launcher atomically; every visible launcher is complete."""
    hooks.mkdir(parents=True, exist_ok=True)
    for name in HOOK_NAMES:
        target = hooks / name
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}")
        try:
            temporary.write_text(hook_launcher(locator, name), encoding="utf-8", newline="\n")
            temporary.chmod(0o755)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
