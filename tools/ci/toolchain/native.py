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
from ethos.adapters.toolchain.mise import mise_executable
from ethos.adapters.toolchain.mise import native_tool_cache
from ethos.adapters.toolchain.mise import run_mise

MISE_RELEASE = "https://github.com/jdx/mise/releases/download/v{version}/{name}"
CI_PROJECTION_POLICY = ".config/checks/ci-projection/policy.toml"
WINDOWS_MISE_ARCHITECTURES = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}


def _windows_host() -> bool:
    """Select the official Windows executable instead of the POSIX shell installer."""
    return os.name == "nt"


def render_mise_installer(root: Path) -> str:
    """Project the native installer with one semantics-preserving lint normalization."""
    version = tomllib.loads((root / MISE_CONFIG).read_text())["min_version"]
    generated = run_command(
        root,
        (str(mise_executable()), "generate", "install-script", "--version", version),
        timeout=30,
        check=True,
    ).stdout
    # Match a literal tilde with a character class rather than quoted expansion syntax.
    source = generated.replace('"~/"*)', "[~]/*)")
    formatter = Path(sys.executable).parent / ("shfmt.exe" if os.name == "nt" else "shfmt")
    return run_command(root, (str(formatter),), stdin=source, timeout=15, check=True).stdout


def validate_mise_installer(root: Path) -> bytes:
    """Read locked bootstrap bytes without network, caches or candidate execution."""
    message = "mise_bootstrap_drift"
    target = root / "tools/ci/scripts/mise-install.sh"
    if not target.is_file() or target.is_symlink() or target.is_junction():
        raise ValueError(message)
    try:
        version = tomllib.loads((root / MISE_CONFIG).read_text())["min_version"]
        record = tomllib.loads((root / CI_PROJECTION_POLICY).read_text())["bootstrap"]
        content = target.read_bytes()
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ValueError(message) from error
    windows = record.get("windows") if isinstance(record, dict) else None
    if (
        not isinstance(record, dict)
        or record.keys() != {"version", "sha256", "windows"}
        or record["version"] != version
        or record["sha256"] != hashlib.sha256(content).hexdigest()
        or not isinstance(windows, dict)
        or windows.keys() != set(WINDOWS_MISE_ARCHITECTURES.values())
        or not all(re.fullmatch(r"[0-9a-f]{64}", str(digest)) for digest in windows.values())
    ):
        raise ValueError(message)
    return content


def _stage_windows_mise(root: Path, version: str, candidate: Path) -> None:
    """Stage the bound official executable; the shell installer supports only Linux and macOS."""
    arch = WINDOWS_MISE_ARCHITECTURES.get(platform.machine().lower())
    if arch is None:
        message = f"mise_windows_architecture_unsupported:{platform.machine()}"
        raise ValueError(message)
    record = tomllib.loads((root / CI_PROJECTION_POLICY).read_text())["bootstrap"]
    name = f"mise-v{version}-windows-{arch}.exe"
    url = MISE_RELEASE.format(version=version, name=name)
    command = ("curl", "-fsSL", "--proto", "=https", "--output", str(candidate), url)
    download_tool(command, root=candidate.parent)
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != record["windows"][arch]:
        message = f"mise_windows_executable_digest_mismatch:{name}"
        raise ValueError(message)


def prepare_mise(root: Path) -> Path:
    """Reuse operator supply or stage the native installer before atomic publication."""
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
    content = validate_mise_installer(root)
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
            verify(executable)
            return executable
        if native_supply_is_offline():
            message = "native_tool_offline_cache_missing:mise"
            raise ValueError(message)
        with TemporaryDirectory(prefix=".bootstrap-", dir=home) as directory:
            isolated = Path(directory)
            candidate = isolated / executable.name
            if _windows_host():
                _stage_windows_mise(root, version, candidate)
                verify(candidate)
                candidate.replace(executable)
                return executable
            installer = isolated / "mise-install.sh"
            installer.write_bytes(content)
            result = run_command(
                root,
                ("bash", str(installer), "--version"),
                timeout=180,
                remove_env_prefixes=("MISE_",),
                env={
                    "MISE_SAFE": "1",
                    "MISE_DISABLE_UPDATE_WARNING": "1",
                    "MISE_VERSION": version,
                    "MISE_INSTALL_PATH": str(candidate),
                    "MISE_INSTALL_FROM_GITHUB": "1",
                    "MISE_INSTALL_EXT": "tar.gz",
                    "TMPDIR": str(isolated),
                },
            )
            sys.stderr.write(result.stdout + result.stderr)
            result.check_returncode()
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


def require_cached_mise_tools(root: Path, mise: Path) -> None:
    """Reject an incomplete immutable image before mise can attempt a download."""
    for name in ("cue", "actionlint"):
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
    """Prepare declared tools online or verify the image's existing supply."""
    go_version = declared_go_version(root)
    if native_supply_is_offline():
        require_cached_mise_tools(root, mise)
    else:
        result = run_mise(
            root,
            ("install", "--locked", "cue", "github:rhysd/actionlint")
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
    parser.add_argument("--render-installer", action="store_true")
    parser.add_argument("tools", nargs="*", choices=("scc", "gitleaks", "syft", "vale", "node"))
    arguments = parser.parse_args()
    try:
        if arguments.render_installer:
            sys.stdout.write(render_mise_installer(arguments.root))
            return 0
        mise = prepare_mise(arguments.root) if arguments.mise else None
        paths: list[Path] = []
        if mise is not None:
            paths.extend(mise_tool_paths(arguments.root, mise))
        paths.extend(
            materialize_tool(arguments.root, tool, mise=mise)
            for tool in dict.fromkeys(arguments.tools)
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
