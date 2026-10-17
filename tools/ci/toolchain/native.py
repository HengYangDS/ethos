"""Materialize declared verification tools in a rootless, identity-bound cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from filelock import FileLock
from filelock import Timeout
from packaging.version import Version

from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.materialization.node.supply import NodeRuntime
from ethos.adapters.repo.runtime.materialization.node.supply import NodeSupply
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import MISE_LOCK
from ethos.adapters.toolchain.mise import mise_executable
from ethos.adapters.toolchain.mise import native_tool_cache
from ethos.adapters.toolchain.mise import run_mise

MISE_RELEASE = "https://github.com/jdx/mise/releases/download/v{version}/{name}"
CI_PROJECTION_POLICY = ".config/checks/ci-projection/policy.toml"
MISE_SYSTEMS = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}
MISE_ARCHITECTURES = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}


@dataclass(frozen=True, slots=True)
class NativeSupply:
    """One tool's native release identity, archive and executable observation."""

    name: str
    backend: str
    version: str
    digest: str
    url: str
    archive: str
    platform: str
    version_argument: str
    version_output: str

    @classmethod
    def read(cls, root: Path, name: str) -> NativeSupply:
        """Resolve the existing tool-native declaration for this supported host."""
        system = platform.system()
        machine = platform.machine()
        arch = {"aarch64": "arm64", "arm64": "arm64", "amd64": "x86_64", "x86_64": "x86_64"}.get(
            machine
        )
        if system not in {"Darwin", "Linux"} or arch is None:
            msg = f"native_tool_platform_unsupported:{system}:{machine}"
            raise ValueError(msg)
        declarations = tomllib.loads((root / MISE_CONFIG).read_text())["tools"]
        selected = [key for key in declarations if key.rsplit("/", 1)[-1] == name]
        if len(selected) != 1 or name not in {"scc", "gitleaks", "syft"}:
            msg = f"native_tool_undeclared:{name}"
            raise ValueError(msg)
        key = selected[0]
        version = declarations[key]
        locked = tomllib.loads((root / MISE_LOCK).read_text())
        records = [row for row in locked["tools"][key] if row["version"] == version]
        target = (
            f"{'macos' if system == 'Darwin' else 'linux'}-{'x64' if arch == 'x86_64' else arch}"
        )
        if len(records) != 1 or locked.get("lockfile_version") != 3:
            msg = f"native_tool_lock_mismatch:{name}"
            raise ValueError(msg)
        material = records[0][f"platforms.{target}"]
        url, checksum = material["url"], material["checksum"]
        parsed = urlsplit(url)
        digest = checksum.removeprefix("sha256:")
        archive = Path(parsed.path).name
        if not (
            re.fullmatch(r"\d+\.\d+\.\d+", version)
            and checksum.startswith("sha256:")
            and re.fullmatch(r"[0-9a-f]{64}", digest)
            and parsed.scheme == "https"
            and parsed.hostname == "github.com"
            and not parsed.username
            and not parsed.password
            and archive.endswith(".tar.gz")
        ):
            msg = f"native_tool_policy_invalid:{name}"
            raise ValueError(msg)
        argument, prefix = ("--version", "scc version ") if name == "scc" else ("version", "")
        return cls(
            name, key, version, digest, url, archive, f"{system}_{arch}", argument, prefix + version
        )

    def executable_bytes(self, archive: Path) -> bytes:
        """Select one regular named member only after exact archive verification."""
        if archive.is_symlink() or not archive.is_file():
            msg = f"native_tool_archive_unsafe:{self.name}"
            raise ValueError(msg)
        with archive.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != self.digest:
                msg = f"{self.name}_archive_checksum_mismatch"
                raise ValueError(msg)
            stream.seek(0)
            with tarfile.open(fileobj=stream, mode="r:gz") as package:
                matches = [member for member in package if member.name == self.name]
                if len(matches) != 1 or not matches[0].isfile():
                    msg = f"native_tool_archive_executable_invalid:{self.name}"
                    raise ValueError(msg)
                source = package.extractfile(matches[0])
                if source is None:
                    msg = f"native_tool_archive_executable_missing:{self.name}"
                    raise ValueError(msg)
                with source:
                    return source.read()

    def verify(self, executable: Path) -> None:
        """Observe the declared native version; bytes or a name alone are insufficient."""
        arguments = (
            (self.version_argument, "-o", "json")
            if self.name == "syft"
            else (self.version_argument,)
        )
        observed = run_command(Path.cwd(), (str(executable), *arguments), timeout=10)
        version = (
            json.loads(observed.stdout).get("version")
            if self.name == "syft"
            else observed.stdout.strip()
        )
        if observed.returncode or observed.stderr or version != self.version_output:
            msg = f"native_tool_executable_version_mismatch:{self.name}"
            raise ValueError(msg)


def _directory(path: Path) -> None:
    """Create only ordinary directories without following cache redirections."""
    for component in (*reversed(path.parents), path):
        if (
            component.is_symlink()
            or component.is_junction()
            or (component.exists() and not component.is_dir())
        ):
            msg = f"native_tool_cache_path_unsafe:{component}"
            raise ValueError(msg)
        component.mkdir(exist_ok=True)


def _windows_host() -> bool:
    """Name the official Windows executable with its native suffix."""
    return os.name == "nt"


def _immutable_hosted_supply() -> bool:
    """Hosted image jobs may verify cached tools but never download replacements."""
    return bool(os.environ.get("ETHOS_CI_SUPPLY_MANIFEST"))


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
    download(command, root=candidate.parent)
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
    _directory(home)
    executable = home / ("mise.exe" if _windows_host() else "mise")
    with FileLock(home / ".bootstrap.lock", timeout=30):
        if executable.is_file() and not executable.is_symlink() and os.access(executable, os.X_OK):
            _bound_executable(root, executable)
            verify(executable)
            return executable
        if _immutable_hosted_supply():
            message = "native_tool_offline_cache_missing:mise"
            raise ValueError(message)
        with TemporaryDirectory(prefix=".bootstrap-", dir=home) as directory:
            candidate = Path(directory) / executable.name
            _stage_mise(root, version, candidate)
            verify(candidate)
            candidate.replace(executable)
    return executable


def download(command: tuple[str, ...], *, root: Path, timeout: float = 180) -> None:
    """Run native provisioning through the shared bounded process owner."""
    result = run_command(
        root,
        command,
        timeout=timeout,
        remove_env_prefixes=("MISE_",),
        env={
            "MISE_SAFE": "1",
            "MISE_DISABLE_UPDATE_WARNING": "1",
            "MISE_LOCKED": "1",
            "MISE_YES": "0",
            "MISE_ALWAYS_KEEP_DOWNLOAD": "1",
            "MISE_DATA_DIR": str(root / "data"),
            "MISE_CACHE_DIR": str(root / "cache"),
            "MISE_GLOBAL_CONFIG_FILE": str(root / "absent-global.toml"),
            "MISE_SYSTEM_CONFIG_DIR": str(root / "absent-system"),
        },
    )
    sys.stderr.write(result.stdout + result.stderr)
    result.check_returncode()


def prepare(root: Path, name: str, *, lock_timeout: float = 30, mise: Path | None = None) -> Path:
    """Converge one declared identity without privileged writes or duplicate effects."""
    root = root.resolve(strict=True)
    supply = NodeSupply.read(root) if name == "node" else NativeSupply.read(root, name)
    cache = (
        supply.cache(root)
        if isinstance(supply, NodeSupply)
        else native_tool_cache(root) / name / supply.version / supply.platform
    )
    _directory(cache)
    lock = cache / ".prepare.lock"
    if lock.is_symlink() or (lock.exists() and not lock.is_file()):
        msg = f"native_tool_cache_path_unsafe:{lock}"
        raise ValueError(msg)
    with FileLock(lock, timeout=lock_timeout):
        _directory(cache)
        archive, target = cache / supply.archive, cache / name
        with TemporaryDirectory(prefix=".prepare-", dir=cache) as scratch:
            selected = archive
            if not archive.exists() and not archive.is_symlink():
                if _immutable_hosted_supply():
                    message = f"native_tool_offline_cache_missing:{name}"
                    raise ValueError(message)
                isolated = Path(scratch)
                for source in (MISE_CONFIG, MISE_LOCK):
                    target_config = isolated / source
                    target_config.parent.mkdir(parents=True, exist_ok=True)
                    target_config.write_bytes((root / source).read_bytes())
                download(
                    (
                        str(mise or mise_executable()),
                        "install",
                        "--locked",
                        "node" if isinstance(supply, NodeSupply) else supply.backend,
                    ),
                    root=isolated,
                )
                candidates = list((isolated / "data/downloads").rglob(supply.archive))
                if len(candidates) != 1:
                    msg = f"native_tool_download_unresolved:{name}"
                    raise ValueError(msg)
                selected = candidates[0]
            if isinstance(supply, NodeSupply):
                return _prepare_node(supply, selected, cache, Path(scratch))
            expected = supply.executable_bytes(selected)
            if selected != archive:
                selected.replace(archive)
            if (
                not target.is_symlink()
                and target.is_file()
                and os.access(target, os.X_OK)
                and target.read_bytes() == expected
            ):
                supply.verify(target)
            else:
                prepared = Path(scratch) / name
                prepared.write_bytes(expected)
                prepared.chmod(0o755)
                supply.verify(prepared)
                prepared.replace(target)
    return cache


def _prepare_node(supply: NodeSupply, archive: Path, cache: Path, scratch: Path) -> Path:
    """Compare complete retained bytes before native execution and atomic publication."""
    prepared = supply.project(archive, scratch / "native")
    expected_archive = cache / supply.archive
    if archive != expected_archive:
        archive.replace(expected_archive)
    runtime = cache / "runtime"
    if runtime.is_symlink() or runtime.is_junction():
        message = f"native_tool_cache_path_unsafe:{runtime}"
        raise ValueError(message)
    if runtime.exists():
        if runtime_file_inventory(runtime) != runtime_file_inventory(prepared):
            message = "native_node_cached_runtime_invalid"
            raise ValueError(message)
    else:
        prepared.replace(runtime)
    executable = NodeRuntime.read(runtime, windows=supply.target.startswith("windows-")).executable
    observed = run_command(scratch, (str(executable), "--version"), timeout=15)
    if observed.returncode or observed.stderr or observed.stdout.strip() != f"v{supply.version}":
        message = "native_node_cached_runtime_invalid"
        raise ValueError(message)
    return executable.parent


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
            if _immutable_hosted_supply()
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
    if _immutable_hosted_supply():
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
    node = prepare(root, "node", mise=mise)
    return [node] + ([locked_go_bin(root, mise, go_version)] if go_version is not None else [])


def main() -> int:
    """Emit only the exact tool PATH; failures remain nonzero diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--mise", action="store_true")
    parser.add_argument("tools", nargs="*", choices=("scc", "gitleaks", "syft", "node"))
    arguments = parser.parse_args()
    try:
        mise = prepare_mise(arguments.root) if arguments.mise else None
        paths: list[Path] = []
        if mise is not None:
            paths.extend(mise_tool_paths(arguments.root, mise))
        paths.extend(
            prepare(arguments.root, tool, mise=mise) for tool in dict.fromkeys(arguments.tools)
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
