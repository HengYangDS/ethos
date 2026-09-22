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
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import MISE_LOCK
from ethos.adapters.toolchain.mise import mise_executable
from ethos.adapters.toolchain.mise import run_mise


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
        if len(records) != 1 or locked.get("lockfile_version") != 2:
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


def _cache_root(root: Path) -> Path:
    """Select the declared persistent store independently of disposable checkouts."""
    home = Path(
        os.environ.get("ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR")
        or os.environ.get("ETHOS_CI_TOOL_CACHE_DIR", "build/runtime/tool-cache/ci-tools")
    )
    return home if home.is_absolute() else root / home


def render_mise_installer(root: Path) -> str:
    """Project the native installer with one semantics-preserving lint normalization."""
    version = tomllib.loads((root / MISE_CONFIG).read_text())["min_version"]
    generated = run_command(
        root,
        (str(mise_executable(root)), "generate", "install-script", "--version", version),
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
    target = root / ".config/ci/mise-install.sh"
    if not target.is_file() or target.is_symlink() or target.is_junction():
        raise ValueError(message)
    try:
        version = tomllib.loads((root / MISE_CONFIG).read_text())["min_version"]
        record = tomllib.loads((root / ".config/checks/ci/templates.toml").read_text())["bootstrap"]
        content = target.read_bytes()
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ValueError(message) from error
    if (
        not isinstance(record, dict)
        or record.keys() != {"version", "sha256"}
        or record["version"] != version
        or record["sha256"] != hashlib.sha256(content).hexdigest()
    ):
        raise ValueError(message)
    return content


def prepare_mise(root: Path) -> Path:
    """Reuse operator supply or stage the native installer before atomic publication."""
    root = root.resolve(strict=True)
    version = tomllib.loads((root / MISE_CONFIG).read_text())["min_version"]

    def verify(executable: Path, *, exact: bool = True) -> None:
        observed = run_command(
            root, (str(executable), "--version"), timeout=15, check=True, env={"MISE_SAFE": "1"}
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
        _cache_root(root) / "mise" / version / f"{platform.system()}_{platform.machine()}" / "bin"
    )
    _directory(home)
    executable = home / "mise"
    with FileLock(home / ".bootstrap.lock", timeout=30):
        if executable.is_file() and not executable.is_symlink() and os.access(executable, os.X_OK):
            verify(executable)
            return executable
        with TemporaryDirectory(prefix=".bootstrap-", dir=home) as directory:
            isolated = Path(directory)
            candidate = isolated / "mise"
            installer = isolated / "mise-install.sh"
            installer.write_bytes(content)
            result = run_command(
                root,
                ("bash", str(installer), "--version"),
                timeout=180,
                remove_env_prefixes=("MISE_",),
                env={
                    "MISE_SAFE": "1",
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


def download(command: tuple[str, ...], *, root: Path, timeout: float = 180) -> None:
    """Run native provisioning through the shared bounded process owner."""
    result = run_command(
        root,
        command,
        timeout=timeout,
        remove_env_prefixes=("MISE_",),
        env={
            "MISE_SAFE": "1",
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


def prepare(root: Path, name: str, *, lock_timeout: float = 30) -> Path:
    """Converge one declared identity without privileged writes or duplicate effects."""
    root = root.resolve(strict=True)
    supply = NativeSupply.read(root, name)
    cache = _cache_root(root) / name / supply.version / supply.platform
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
                isolated = Path(scratch)
                for source in (MISE_CONFIG, MISE_LOCK):
                    target_config = isolated / source
                    target_config.parent.mkdir(parents=True, exist_ok=True)
                    target_config.write_bytes((root / source).read_bytes())
                download(
                    (str(mise_executable(root)), "install", "--locked", supply.backend),
                    root=isolated,
                )
                candidates = list((isolated / "data/downloads").rglob(supply.archive))
                if len(candidates) != 1:
                    msg = f"native_tool_download_unresolved:{supply.name}"
                    raise ValueError(msg)
                selected = candidates[0]
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


def main() -> int:
    """Emit only the exact tool PATH; failures remain nonzero diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--mise", action="store_true")
    parser.add_argument("--render-installer", action="store_true")
    parser.add_argument("tools", nargs="*", choices=("scc", "gitleaks", "syft"))
    arguments = parser.parse_args()
    try:
        if arguments.render_installer:
            sys.stdout.write(render_mise_installer(arguments.root))
            return 0
        paths = []
        if arguments.mise:
            paths.append(prepare_mise(arguments.root).parent)
            result = run_mise(
                arguments.root,
                ("install", "--locked", "cue", "github:rhysd/actionlint"),
                timeout=180,
            )
            sys.stderr.write(result.stdout + result.stderr)
            result.check_returncode()
        paths.extend(prepare(arguments.root, tool) for tool in dict.fromkeys(arguments.tools))
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
        print(f"native_tool_supply_failed:{error}", file=sys.stderr)
        return 1
    print(os.pathsep.join(str(path) for path in paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
