"""Immutable package runtime installation for portable Git hooks."""

from __future__ import annotations

import hashlib
import json
import os
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
from typing import TYPE_CHECKING
from urllib.parse import unquote
from urllib.parse import urlparse

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_generation_digest
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.runtime.manifest import RuntimeEnvironment
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.adapters.repo.runtime.manifest import runtime_environment_projection
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_entrypoint
from ethos.adapters.repo.runtime.selection import runtime_python
from ethos.adapters.repo.runtime.supply import ImmutablePackageSupply
from ethos.adapters.repo.runtime.supply import LockedSourceSupply
from ethos.adapters.repo.runtime.supply import runtime_supply
from ethos.adapters.repo.runtime.transition import execute_runtime_identity_transition
from ethos.adapters.repo.runtime.transition import materialize_release_wheel
from ethos.repository.release.admission import accepted_release_candidate
from ethos.repository.release.admission import accepted_runtime_candidate

if TYPE_CHECKING:
    from ethos.repository.release.identity import BuildIdentity


@dataclass(frozen=True, slots=True)
class _RuntimeWheel:
    path: Path
    sha256: str
    build: BuildIdentity


def materialize_hook_runtime(
    repo: Path,
    source_python: Path,
    *,
    expected_build: BuildIdentity,
    build_source: Path | None = None,
) -> Path:
    """Build and atomically install one wheel-qualified common-dir runtime."""
    package_source = build_source or Path(__file__).resolve().parents[4]
    project = build_source or _runtime_project(package_source)
    supply_mode = "locked-source" if project == package_source else "immutable-package"
    common = Path(git_common_dir(repo))
    ethos_root = common / "ethos"
    if ethos_root.is_symlink():
        message = "hook_runtime_root_invalid"
        raise ValueError(message)
    runtime_root = ethos_root / "runtime"
    work = runtime_root / f".build-{uuid.uuid4().hex}"
    wheel_dir = work / "wheel"
    try:
        wheel = _runtime_wheel(
            package_source,
            wheel_dir,
            repo=repo,
            expected_build=expected_build,
        )
        supply = runtime_supply(
            mode=supply_mode,
            source=project,
            wheel=wheel.path,
            interpreter=_owned_runtime_interpreter(package_source, source_python),
        )
        environment = _runtime_environment(supply)
        digest = _runtime_digest(
            wheel_sha256=wheel.sha256,
            python_abi=environment.python_abi,
            build=wheel.build,
            python_version=environment.python_version,
            python_implementation=environment.python_implementation,
            dependency_lock_sha256=environment.dependency_lock_sha256,
        )
        release = accepted_release_candidate(wheel.build, wheel_sha256=wheel.sha256)
        accepted_runtime = accepted_runtime_candidate(
            release,
            runtime_digest=digest,
            python_abi=environment.python_abi,
            platform=environment.platform,
        )

        def materialize() -> Path:
            return _materialize_runtime_directory(
                supply,
                work,
                runtime_root,
                wheel,
                digest=digest,
                environment=environment,
            )

        def post_observe(target: Path):
            selected = require_selected_runtime(
                target,
                expected_build=wheel.build,
                expected_digest=digest,
                expected_wheel_sha256=wheel.sha256,
                expected_python_abi=environment.python_abi,
            )
            observed_release = accepted_release_candidate(
                selected.build,
                wheel_sha256=selected.wheel_sha256,
            )
            return accepted_runtime_candidate(
                observed_release,
                runtime_digest=selected.digest,
                python_abi=selected.python_abi,
                platform=environment.platform,
            )

        target = execute_runtime_identity_transition(
            repo,
            accepted_runtime,
            materialize=materialize,
            post_observe=post_observe,
        )
        return target / "python"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _materialize_runtime_directory(
    supply: LockedSourceSupply | ImmutablePackageSupply,
    work: Path,
    runtime_root: Path,
    wheel: _RuntimeWheel,
    *,
    digest: str,
    environment: RuntimeEnvironment,
) -> Path:
    """Create or validate one immutable runtime directory."""
    target = runtime_root / digest
    if target.is_dir():
        require_runtime(target, digest, wheel.sha256, environment.python_abi, wheel.build)
        return target
    staging = runtime_root / f".runtime-{digest[:12]}-{uuid.uuid4().hex}"
    try:
        python_home = staging / "python"
        materialize_runtime_python(python_home, supply, work)
        runtime_python_path = runtime_python(python_home)
        write_runtime_manifest(
            staging,
            digest,
            wheel.sha256,
            environment,
            wheel.build,
            runtime_python_path,
        )
        runtime_root.mkdir(parents=True, exist_ok=True)
        try:
            staging.rename(target)
        except FileExistsError:
            require_runtime(target, digest, wheel.sha256, environment.python_abi, wheel.build)
        else:
            try:
                finalize_runtime(target, digest, wheel.sha256, wheel.build, environment)
            except (OSError, ValueError):
                shutil.rmtree(target, ignore_errors=True)
                raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def materialize_runtime_python(
    target: Path,
    supply: LockedSourceSupply | ImmutablePackageSupply,
    work: Path,
) -> None:
    """Materialize one owned standalone interpreter home from an explicit supply."""
    copy_python_home(supply.interpreter, target)
    python = runtime_python(target)
    if not python.is_file():
        message = "hook_runtime_python_missing"
        raise ValueError(message)
    if isinstance(supply, LockedSourceSupply):
        install_locked_runtime(supply.source, work, python, supply.wheel)
    else:
        _require_package_runtime_source(supply)


def copy_python_home(interpreter: Path, target: Path) -> None:
    """Copy one standalone interpreter home without following host-external links."""
    facts = python_facts(interpreter)
    home = Path(facts["base_prefix"])
    if facts["prefix"] != facts["base_prefix"] or not interpreter.resolve().is_relative_to(
        home.resolve()
    ):
        message = "hook_runtime_owned_interpreter_unavailable"
        raise ValueError(message)
    shutil.copytree(home, target, symlinks=True)


def _require_package_runtime_source(supply: ImmutablePackageSupply) -> None:
    """Require package-only installation to copy a previously verified runtime."""
    prefix = Path(python_facts(supply.interpreter)["prefix"])
    runtime = prefix.parent
    selected = require_selected_runtime(runtime)
    if selected.python.resolve() != supply.interpreter.resolve():
        message = "hook_runtime_package_interpreter_stale"
        raise ValueError(message)
    if selected.wheel_sha256 != _sha256(supply.wheel):
        message = "hook_runtime_package_wheel_stale"
        raise ValueError(message)
    if selected.dependency_lock_sha256 != _sha256(supply.source / "uv.lock"):
        message = "hook_runtime_package_lock_stale"
        raise ValueError(message)


def install_locked_runtime(
    source: Path,
    work: Path,
    python: Path,
    wheel: Path,
) -> None:
    """Install the production lock and exact wheel into an owned Python home."""
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
        "sync",
        "--offline",
        "--break-system-packages",
        "--require-hashes",
        "--strict",
        "--python",
        python.as_posix(),
        requirements.as_posix(),
    )
    _run_runtime_tool(
        source,
        "pip",
        "install",
        "--offline",
        "--break-system-packages",
        "--no-deps",
        "--python",
        python.as_posix(),
        wheel.as_posix(),
    )


def _runtime_wheel(
    source: Path,
    wheel_dir: Path,
    *,
    repo: Path,
    expected_build: BuildIdentity,
) -> _RuntimeWheel:
    wheel = resolve_runtime_wheel(source, wheel_dir)
    artifact = materialize_release_wheel(
        repo,
        wheel,
        expected_build=expected_build,
        collision="hook_runtime_wheel_digest_collision",
    )
    return _RuntimeWheel(
        path=artifact.path,
        sha256=artifact.sha256,
        build=artifact.build,
    )


def require_runtime_wheel_provenance() -> None:
    """Validate that the current package can materialize a source-independent runtime."""
    source = Path(__file__).resolve().parents[4]
    if (source / "pyproject.toml").is_file():
        return
    resolve_runtime_wheel(source, Path())


def resolve_runtime_wheel(source: Path, wheel_dir: Path) -> Path:
    if (source / "pyproject.toml").is_file():
        _run_runtime_tool(source, "sync", "--locked", "--offline", "--check", "--active")
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
                "--no-build-isolation",
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
    managed_wheel = _managed_runtime_wheel(source)
    if managed_wheel is not None:
        return managed_wheel
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


def _managed_runtime_wheel(source: Path) -> Path | None:
    """Resolve the wheel bound by the current Git-common immutable runtime."""
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
        message = "hook_runtime_wheel_provenance_missing"
        raise ValueError(message)
    wheels = tuple(
        path
        for path in package_root.glob("ethos-*.whl")
        if path.is_file() and not path.is_symlink()
    )
    if len(wheels) != 1 or _sha256(wheels[0]) != selected.wheel_sha256:
        message = "hook_runtime_wheel_provenance_missing"
        raise ValueError(message)
    return wheels[0]


def _runtime_project(package_source: Path) -> Path:
    """Resolve the one available lock-bearing source or packaged projection."""
    required = ("pyproject.toml", "uv.lock", "VERSION")
    if all((package_source / name).is_file() for name in required):
        return package_source
    project = Path(__file__).resolve().parents[2] / "data" / "runtime-project"
    if not all((project / name).is_file() for name in required):
        message = "hook_runtime_packaged_project_missing"
        raise ValueError(message)
    return project


def _owned_runtime_interpreter(source: Path, source_python: Path) -> Path:
    """Resolve a relocatable uv-managed interpreter, never a host or venv prefix."""
    resolved = source_python.resolve()
    if Path(sys.prefix).name == "python" and resolved.is_relative_to(Path(sys.prefix).resolve()):
        runtime = Path(sys.prefix).parent
        if runtime.parent.name == "runtime":
            return resolved
    executable = Path(sys.executable).with_name("uv.exe" if os.name == "nt" else "uv")
    if not executable.is_file():
        message = "hook_runtime_uv_unavailable"
        raise ValueError(message)
    environment = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    requested = python_facts(source_python)["python_version"]
    command = (executable.as_posix(), "python", "find", "--managed-python", requested)
    completed = subprocess.run(
        command,
        cwd=source,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
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
            message = (
                installed.stderr.strip()
                or installed.stdout.strip()
                or "hook_runtime_owned_interpreter_unavailable"
            )
            raise ValueError(message)
        completed = subprocess.run(
            command,
            cwd=source,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
    if completed.returncode:
        message = "hook_runtime_owned_interpreter_unavailable"
        raise ValueError(message)
    interpreter = Path(completed.stdout.strip()).resolve()
    facts = python_facts(interpreter)
    if not interpreter.is_file() or facts["prefix"] != facts["base_prefix"]:
        message = "hook_runtime_owned_interpreter_unavailable"
        raise ValueError(message)
    return interpreter


def _run_runtime_tool(source: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
            "VIRTUAL_ENV": Path(sys.prefix).as_posix(),
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
    return completed


def python_facts(python: Path) -> dict[str, str]:
    script = (
        "import json,platform,sys; "
        "print(json.dumps({"
        "'python_abi':sys.implementation.cache_tag or '',"
        "'python_version':platform.python_version(),"
        "'python_implementation':sys.implementation.name,"
        "'prefix':sys.prefix,'base_prefix':sys.base_prefix}))"
    )
    completed = subprocess.run(
        (
            python.as_posix(),
            "-I",
            "-c",
            script,
        ),
        capture_output=True,
        check=False,
        text=True,
    )
    try:
        payload = json.loads(completed.stdout)
        facts = {key: str(value) for key, value in payload.items()}
    except (TypeError, ValueError) as error:
        message = "hook_runtime_python_abi_invalid"
        raise ValueError(message) from error
    if completed.returncode or not all(
        facts.get(key)
        for key in (
            "python_abi",
            "python_version",
            "python_implementation",
            "prefix",
            "base_prefix",
        )
    ):
        message = "hook_runtime_python_abi_invalid"
        raise ValueError(message)
    return facts


def _runtime_environment(
    supply: LockedSourceSupply | ImmutablePackageSupply,
) -> RuntimeEnvironment:
    facts = python_facts(supply.interpreter)
    return runtime_environment(
        python_abi=facts["python_abi"],
        python_version=facts["python_version"],
        python_implementation=facts["python_implementation"],
        dependency_lock_sha256=_sha256(supply.source / "uv.lock"),
    )


def _runtime_digest(
    wheel_sha256: str,
    python_abi: str,
    build: BuildIdentity,
    python_version: str,
    python_implementation: str,
    dependency_lock_sha256: str,
) -> str:
    return runtime_digest(
        wheel_sha256=wheel_sha256,
        build=build,
        environment=runtime_environment(
            python_abi=python_abi,
            python_version=python_version,
            python_implementation=python_implementation,
            dependency_lock_sha256=dependency_lock_sha256,
        ),
    )


def write_runtime_manifest(
    runtime: Path,
    digest: str,
    wheel_sha256: str,
    environment: RuntimeEnvironment,
    build: BuildIdentity,
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
        "schema_version": 4,
        "runtime_digest": digest,
        "wheel_sha256": wheel_sha256,
        **runtime_environment_projection(environment),
        **{key: value for key, value in build.projection().items() if key != "schema_version"},
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
    build: BuildIdentity,
) -> None:
    require_selected_runtime(
        runtime,
        expected_build=build,
        expected_digest=digest,
        expected_wheel_sha256=wheel_sha256,
        expected_python_abi=python_abi,
    )


def rewrite_runtime_entrypoint(runtime: Path) -> None:
    if os.name == "nt":
        return
    entrypoint = runtime_entrypoint(runtime / "python")
    python = runtime_python(runtime / "python")
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
    build: BuildIdentity,
    environment: RuntimeEnvironment,
) -> None:
    rewrite_runtime_entrypoint(runtime)
    python = runtime_python(runtime / "python")
    write_runtime_manifest(runtime, digest, wheel_sha256, environment, build, python)
    require_runtime(runtime, digest, wheel_sha256, environment.python_abi, build)
    facts = python_facts(python)
    expected_prefix = (runtime / "python").resolve().as_posix()
    if facts["prefix"] != expected_prefix or facts["base_prefix"] != expected_prefix:
        message = "hook_runtime_python_not_relocatable"
        raise ValueError(message)
    completed = subprocess.run(
        (runtime_entrypoint(runtime / "python"), "--version"),
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
