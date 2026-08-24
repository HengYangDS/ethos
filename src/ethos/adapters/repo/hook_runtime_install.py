"""Immutable package runtime installation for portable Git hooks."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import uuid
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import PackageNotFoundError
from importlib.metadata import distribution
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlparse

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_generation_digest
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.source_identity import RuntimeSourceIdentity
from ethos.adapters.repo.hook.source_identity import wheel_source_identity
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_entrypoint
from ethos.adapters.repo.runtime.selection import runtime_python
from ethos.adapters.store.content_addressed import write_content_addressed


@dataclass(frozen=True, slots=True)
class _RuntimeWheel:
    path: Path
    sha256: str
    source: RuntimeSourceIdentity


def materialize_hook_runtime(
    repo: Path,
    source_python: Path,
    *,
    expected_source: RuntimeSourceIdentity,
) -> Path:
    """Build and atomically install one wheel-qualified common-dir runtime."""
    source = Path(__file__).resolve().parents[4]
    common = Path(git_common_dir(repo))
    ethos_root = common / "ethos"
    if ethos_root.is_symlink():
        message = "hook_runtime_root_invalid"
        raise ValueError(message)
    runtime_root = ethos_root / "runtime"
    work = runtime_root / f".build-{uuid.uuid4().hex}"
    wheel_dir = work / "wheel"
    try:
        python_abi = _python_abi(source_python)
        wheel = _runtime_wheel(
            source,
            wheel_dir,
            common=common,
            expected_source=expected_source,
        )
        digest = _runtime_digest(wheel.sha256, python_abi, wheel.source)
        target = runtime_root / digest
        if target.is_dir():
            require_runtime(target, digest, wheel.sha256, python_abi, wheel.source)
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
            runtime_python_path = runtime_python(staging / "venv")
            if (source / "pyproject.toml").is_file():
                requirements = work / "locked-requirements.txt"
                _run_runtime_tool(
                    source,
                    "export",
                    "--locked",
                    "--offline",
                    "--no-dev",
                    "--no-emit-project",
                    "--format",
                    "requirements-txt",
                    "--output-file",
                    requirements.as_posix(),
                )
                _run_runtime_tool(
                    source,
                    "pip",
                    "install",
                    "--offline",
                    "--no-deps",
                    "--python",
                    runtime_python_path.as_posix(),
                    "--requirements",
                    requirements.as_posix(),
                    wheel.path.as_posix(),
                )
            write_runtime_manifest(
                staging,
                digest,
                wheel.sha256,
                python_abi,
                wheel.source,
                runtime_python_path,
            )
            runtime_root.mkdir(parents=True, exist_ok=True)
            try:
                staging.rename(target)
            except FileExistsError:
                require_runtime(target, digest, wheel.sha256, python_abi, wheel.source)
            else:
                try:
                    finalize_runtime(
                        target,
                        digest,
                        wheel.sha256,
                        python_abi,
                        wheel.source,
                    )
                except (OSError, ValueError):
                    shutil.rmtree(target, ignore_errors=True)
                    raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        require_runtime(target, digest, wheel.sha256, python_abi, wheel.source)
        return target / "venv"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _runtime_wheel(
    source: Path,
    wheel_dir: Path,
    *,
    common: Path,
    expected_source: RuntimeSourceIdentity,
) -> _RuntimeWheel:
    wheel = resolve_runtime_wheel(source, wheel_dir)
    sha256 = _sha256(wheel)
    source_identity = wheel_source_identity(wheel)
    if source_identity != expected_source:
        message = "hook_runtime_wheel_source_identity_stale"
        raise ValueError(message)
    durable = write_content_addressed(
        common / "ethos" / "packages" / sha256 / wheel.name,
        wheel.read_bytes(),
        collision="hook_runtime_wheel_digest_collision",
    )
    return _RuntimeWheel(path=durable, sha256=sha256, source=source_identity)


def require_runtime_wheel_provenance() -> None:
    """Validate that the current package can materialize a source-independent runtime."""
    source = Path(__file__).resolve().parents[4]
    if (source / "pyproject.toml").is_file():
        return
    resolve_runtime_wheel(source, Path())


def resolve_runtime_wheel(source: Path, wheel_dir: Path) -> Path:
    if (source / "pyproject.toml").is_file():
        wheel_dir.parent.mkdir(parents=True, exist_ok=True)
        if wheel_dir.exists():
            message = "hook_runtime_wheel_invalid"
            raise ValueError(message)
        staging = wheel_dir.parent / f".{wheel_dir.name}-{uuid.uuid4().hex}"
        try:
            _run_runtime_tool(
                source,
                "build",
                "--offline",
                "--wheel",
                "--out-dir",
                staging.as_posix(),
            )
            wheels = tuple(staging.glob("ethos-*.whl"))
            if len(wheels) != 1:
                message = "hook_runtime_wheel_invalid"
                raise ValueError(message)
            staging.rename(wheel_dir)
            return wheel_dir / wheels[0].name
        finally:
            shutil.rmtree(staging, ignore_errors=True)
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
    # A virtual environment commonly links its interpreter back to the host
    # installation.  Preserving that link would make the supposedly immutable
    # runtime depend on (and permit writes through to) the host interpreter.
    shutil.copytree(prefix, target, symlinks=False)


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


def _runtime_digest(
    wheel_sha256: str,
    python_abi: str,
    source_identity: RuntimeSourceIdentity,
) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "schema_version": 2,
                "wheel_sha256": wheel_sha256,
                "python_abi": python_abi,
                "platform": platform.system().lower(),
                "source_commit": source_identity.commit,
                "source_tree": source_identity.tree,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def write_runtime_manifest(
    runtime: Path,
    digest: str,
    wheel_sha256: str,
    python_abi: str,
    source_identity: RuntimeSourceIdentity,
    python: Path,
) -> None:
    if not python.is_file():
        message = "hook_runtime_python_missing"
        raise ValueError(message)
    entrypoint = runtime_entrypoint(python.parent.parent)
    if not entrypoint.is_file():
        message = "hook_runtime_entrypoint_missing"
        raise ValueError(message)
    payload = {
        "schema_version": 2,
        "runtime_digest": digest,
        "wheel_sha256": wheel_sha256,
        "python_abi": python_abi,
        "platform": platform.system().lower(),
        "source_commit": source_identity.commit,
        "source_tree": source_identity.tree,
        "runtime_files": {
            path.relative_to(runtime).as_posix(): _sha256(path) for path in (python, entrypoint)
        },
    }
    (runtime / "manifest.json").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )


def require_runtime(
    runtime: Path,
    digest: str,
    wheel_sha256: str,
    python_abi: str,
    source_identity: RuntimeSourceIdentity,
) -> None:
    require_selected_runtime(
        runtime,
        expected_source=source_identity,
        expected_digest=digest,
        expected_wheel_sha256=wheel_sha256,
        expected_python_abi=python_abi,
    )


def _rewrite_runtime_entrypoint(runtime: Path) -> None:
    if os.name == "nt":
        return
    entrypoint = runtime_entrypoint(runtime / "venv")
    python = runtime_python(runtime / "venv")
    try:
        lines = entrypoint.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeError) as error:
        message = "hook_runtime_entrypoint_invalid"
        raise ValueError(message) from error
    if not lines:
        message = "hook_runtime_entrypoint_invalid"
        raise ValueError(message)
    lines[0] = f"#!{python}\n"
    entrypoint.write_text("".join(lines), encoding="utf-8", newline="\n")
    entrypoint.chmod(0o755)


def finalize_runtime(
    runtime: Path,
    digest: str,
    wheel_sha256: str,
    python_abi: str,
    source_identity: RuntimeSourceIdentity,
) -> None:
    _rewrite_runtime_entrypoint(runtime)
    python = runtime_python(runtime / "venv")
    write_runtime_manifest(runtime, digest, wheel_sha256, python_abi, source_identity, python)
    require_runtime(runtime, digest, wheel_sha256, python_abi, source_identity)
    completed = subprocess.run(
        (runtime_entrypoint(runtime / "venv"), "--version"),
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode or not completed.stdout.strip():
        message = "hook_runtime_entrypoint_smoke_failed"
        raise ValueError(message)


def materialize_hook_launchers(generations: Path) -> Path:
    """Materialize or repair one immutable content-addressed hook generation."""
    if generations.parent.is_symlink() or generations.is_symlink():
        message = "hook_generation_root_invalid"
        raise ValueError(message)
    expected = {name: hook_launcher(name) for name in HOOK_NAMES}
    digest = hook_generation_digest(expected)
    target = generations / digest
    if target.is_symlink():
        message = "hook_launcher_projection_invalid"
        raise ValueError(message)
    if target.is_dir():
        try:
            _require_launcher_projection(target, expected)
        except ValueError:
            return _replace_launcher_projection(generations, target, expected)
        return target
    return _replace_launcher_projection(generations, target, expected)


def _replace_launcher_projection(
    generations: Path,
    target: Path,
    expected: dict[str, str],
) -> Path:
    """Atomically replace one missing or drifted generated hook projection."""
    generations.mkdir(parents=True, exist_ok=True)
    staging = generations / f".generation-{target.name[:12]}-{uuid.uuid4().hex}"
    backup: Path | None = None
    try:
        staging.mkdir()
        for name, content in expected.items():
            launcher = staging / name
            launcher.write_text(content, encoding="utf-8", newline="\n")
            launcher.chmod(0o755)
        _require_launcher_projection(staging, expected)
        if target.is_dir():
            backup = generations / f".replaced-{target.name[:12]}-{uuid.uuid4().hex}"
            target.rename(backup)
        try:
            staging.rename(target)
        except OSError:
            if backup is not None and not target.exists():
                backup.rename(target)
            elif not target.is_dir():
                raise
        _require_launcher_projection(target, expected)
    except (OSError, ValueError):
        _restore_launcher_projection(target, backup)
        raise
    else:
        if backup is not None:
            shutil.rmtree(backup)
        return target
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _restore_launcher_projection(target: Path, backup: Path | None) -> None:
    """Restore the exact prior generated projection after replacement failure."""
    if backup is None or not backup.is_dir():
        return
    if target.is_dir():
        shutil.rmtree(target)
    elif target.exists() or target.is_symlink():
        target.unlink()
    backup.rename(target)


def _require_launcher_projection(hooks: Path, expected: dict[str, str]) -> None:
    try:
        names = {path.name for path in hooks.iterdir()}
        valid = (
            not hooks.is_symlink()
            and names == expected.keys()
            and all(
                not (path := hooks / name).is_symlink()
                and path.is_file()
                and path.read_bytes() == content.encode()
                and (os.name == "nt" or stat.S_IMODE(path.stat().st_mode) == 0o755)
                for name, content in expected.items()
            )
        )
    except OSError as error:
        message = "hook_launcher_projection_invalid"
        raise ValueError(message) from error
    if not valid:
        message = "hook_launcher_projection_invalid"
        raise ValueError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
