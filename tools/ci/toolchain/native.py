"""Materialize declared verification tools in a rootless, identity-bound cache."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock
from filelock import Timeout
from packaging.version import Version

from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.native_supply import download_tool
from ethos.adapters.repo.runtime.materialization.native_supply import ensure_native_directory
from ethos.adapters.repo.runtime.materialization.native_supply import materialize_tool
from ethos.adapters.repo.runtime.materialization.native_supply import native_supply_is_offline
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import native_tool_cache
from ethos.adapters.toolchain.mise import run_mise

MISE_RELEASE = "https://github.com/jdx/mise/releases/download/v{version}/{name}"
CI_PROJECTION_POLICY = ".config/checks/ci-projection/policy.toml"
MISE_SYSTEMS = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}
MISE_ARCHITECTURES = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}


def _windows_host() -> bool:
    """Name the official Windows executable with its native suffix."""
    return os.name == "nt"


def mise_executables(root: Path) -> dict[str, str]:
    """Read the bound official executable digest of every supported platform."""
    message = "mise_executable_record_invalid"
    try:
        version = tomllib.loads((root / MISE_CONFIG).read_text())["min_version"]
        record = tomllib.loads((root / CI_PROJECTION_POLICY).read_text())["bootstrap"]
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ValueError(message) from error
    executables = record.get("executables") if isinstance(record, dict) else None
    platforms = {
        f"{system}-{arch}"
        for system in MISE_SYSTEMS.values()
        for arch in MISE_ARCHITECTURES.values()
    }
    if (
        not isinstance(record, dict)
        or record.keys() != {"version", "executables"}
        or record["version"] != version
        or not isinstance(executables, dict)
        or executables.keys() != platforms
        or not all(re.fullmatch(r"[0-9a-f]{64}", str(digest)) for digest in executables.values())
    ):
        raise ValueError(message)
    return {str(target): str(digest) for target, digest in executables.items()}


def _mise_target() -> str:
    """Name this host's official executable platform."""
    system = MISE_SYSTEMS.get(platform.system())
    arch = MISE_ARCHITECTURES.get(platform.machine().lower())
    if system is None or arch is None:
        message = f"mise_platform_unsupported:{platform.system()}-{platform.machine()}"
        raise ValueError(message)
    return f"{system}-{arch}"


def _bound_executable(root: Path, executable: Path) -> None:
    """Accept only the official executable whose digest this repository binds."""
    if (
        hashlib.sha256(executable.read_bytes()).hexdigest()
        != mise_executables(root)[_mise_target()]
    ):
        message = f"mise_executable_digest_mismatch:{executable.name}"
        raise ValueError(message)


def _stage_mise(root: Path, version: str, candidate: Path) -> None:
    """Stage the official executable of this platform and verify its bound digest."""
    name = f"mise-v{version}-{_mise_target()}{'.exe' if _windows_host() else ''}"
    url = MISE_RELEASE.format(version=version, name=name)
    command = ("curl", "-fsSL", "--proto", "=https", "--output", str(candidate), url)
    download_tool(command, root=candidate.parent)
    _bound_executable(root, candidate)
    candidate.chmod(0o755)


def prepare_mise(root: Path) -> Path:
    """Reuse operator supply or stage the official executable before atomic publication."""
    root = root.resolve(strict=True)
    version = tomllib.loads((root / MISE_CONFIG).read_text())["min_version"]

    def verify(executable: Path, *, exact: bool = True) -> None:
        observed = run_command(
            root,
            (str(executable), "--version"),
            timeout=15,
            check=True,
            env={"MISE_SAFE": "1", "MISE_DISABLE_UPDATE_WARNING": "1"},
        )
        if observed.stderr:
            message = f"mise_version_observation_failed:{executable}:{observed.stderr.strip()}"
            raise ValueError(message)
        actual, required = Version(observed.stdout.strip().partition(" ")[0]), Version(version)
        if actual.is_prerelease or (actual != required if exact else actual < required):
            message = (
                f"mise_version_mismatch:{executable}:"
                f"required={'==' if exact else '>='}{required}:observed={actual}"
            )
            raise ValueError(message)

    if installed := shutil.which("mise"):
        executable = Path(installed)
        verify(executable, exact=False)
        return executable
    mise_executables(root)
    home = (
        native_tool_cache(root)
        / "mise"
        / version
        / f"{platform.system()}_{platform.machine()}"
        / "bin"
    )
    ensure_native_directory(home)
    executable = home / ("mise.exe" if _windows_host() else "mise")
    with FileLock(home / ".bootstrap.lock", timeout=30):
        if executable.is_file() and not executable.is_symlink() and os.access(executable, os.X_OK):
            _bound_executable(root, executable)
            verify(executable)
            return executable
        if native_supply_is_offline():
            message = "native_tool_offline_cache_missing:mise"
            raise ValueError(message)
        with TemporaryDirectory(prefix=".bootstrap-", dir=home) as directory:
            candidate = Path(directory) / executable.name
            _stage_mise(root, version, candidate)
            verify(candidate)
            candidate.replace(executable)
    return executable


def declared_go_version(root: Path) -> str | None:
    """Read the one project declaration without inferring an ambient Go tool."""
    declared = tomllib.loads((root / MISE_CONFIG).read_text()).get("tools", {})
    version = declared.get("go")
    if version is not None and not isinstance(version, str):
        msg = "native_tool_policy_invalid:go"
        raise ValueError(msg)
    return version


def locked_go_bin(root: Path, mise: Path, version: str) -> Path:
    """Expose Go and gofmt only from mise's installed, locked toolchain."""
    selected = run_mise(root, ("which", "go"), executable=mise)
    if selected.returncode or selected.stderr:
        msg = (
            "native_tool_offline_cache_missing:go"
            if native_supply_is_offline()
            else f"native_tool_supply_unavailable:go:{selected.stderr.strip()}"
        )
        raise ValueError(msg)
    go = Path(selected.stdout.strip())
    gofmt = go.with_name(f"gofmt{go.suffix}")
    if not (
        go.is_absolute()
        and go.is_file()
        and gofmt.is_file()
        and os.access(go, os.X_OK)
        and os.access(gofmt, os.X_OK)
    ):
        msg = "native_tool_executable_unavailable:go"
        raise ValueError(msg)
    observed = run_command(root, (str(go), "version"), timeout=10, env={"GOTOOLCHAIN": "local"})
    if (
        observed.returncode
        or observed.stderr
        or not observed.stdout.startswith(f"go version go{version} ")
    ):
        msg = "native_tool_executable_version_mismatch:go"
        raise ValueError(msg)
    return go.parent


def require_cached_mise_tools(root: Path, mise: Path, declared: tuple[str, ...] = ()) -> None:
    """Reject an incomplete immutable image before mise can attempt a download."""
    for name in ("cue", "actionlint", *declared):
        selected = run_mise(root, ("which", name), executable=mise)
        executable = Path(selected.stdout.strip())
        if (
            selected.returncode
            or selected.stderr
            or not (executable.is_absolute() and executable.is_file())
        ):
            msg = f"native_tool_offline_cache_missing:{name}"
            raise ValueError(msg)


def mise_tool_paths(root: Path, mise: Path) -> list[Path]:
    """Prepare declared tools online or verify the image's existing supply.

    Shared quality checks resolve a declared Node through mise; the Node that
    `materialize_tool` places in the tool cache serves the product runtime and npm.
    """
    go_version = declared_go_version(root)
    tools = tomllib.loads((root / MISE_CONFIG).read_text()).get("tools", {})
    node = ("node",) if "node" in tools else ()
    if native_supply_is_offline():
        require_cached_mise_tools(root, mise, node)
    else:
        result = run_mise(
            root,
            ("install", "--locked", "cue", "github:rhysd/actionlint", *node)
            + (("go",) if go_version is not None else ()),
            executable=mise,
            timeout=300,
        )
        sys.stderr.write(result.stdout + result.stderr)
        result.check_returncode()
    node = materialize_tool(root, "node", mise=mise)
    return [node] + ([locked_go_bin(root, mise, go_version)] if go_version is not None else [])


def main() -> int:
    """Emit only the exact tool PATH; failures remain nonzero diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--mise", action="store_true")
    parser.add_argument(
        "tools", nargs="*", choices=("scc", "gitleaks", "syft", "vale", "cue", "node")
    )
    arguments = parser.parse_args()
    try:
        mise = prepare_mise(arguments.root) if arguments.mise else None
        paths: list[Path] = []
        if mise is not None:
            paths.extend(mise_tool_paths(arguments.root, mise))
        paths.extend(
            materialize_tool(arguments.root, tool, mise=mise)
            for tool in dict.fromkeys((*arguments.tools, *(("cue",) if mise is not None else ())))
        )
        if mise is not None:
            paths.append(mise.parent)
        if not paths:
            parser.error("select --mise or at least one tool")
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        tarfile.TarError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
        Timeout,
    ) as error:
        if isinstance(error, subprocess.TimeoutExpired):
            for output in (error.stdout, error.stderr):
                if output:
                    sys.stderr.write(
                        output.decode("utf-8", errors="replace")
                        if isinstance(output, bytes)
                        else output
                    )
        print(f"native_tool_supply_failed:{_failure_chain(error)}", file=sys.stderr)
        return 1
    print(os.pathsep.join(str(path) for path in paths))
    return 0


def _failure_chain(error: BaseException) -> str:
    """Name a failure with the earlier failures it wrapped or masked, newest first."""
    chain = [error]
    while True:
        current = chain[-1]
        earlier = current.__cause__ or (
            None if current.__suppress_context__ else current.__context__
        )
        if earlier is None or earlier in chain:
            return " <- ".join(str(item) for item in chain)
        chain.append(earlier)


if __name__ == "__main__":
    raise SystemExit(main())
