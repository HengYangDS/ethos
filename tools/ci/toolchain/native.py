"""Materialize declared verification tools in a rootless, identity-bound cache."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import signal
import subprocess
import sys
import tarfile
import tomllib
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock
from filelock import Timeout


@dataclass(frozen=True, slots=True)
class NativeSupply:
    """One tool's native release identity, archive and executable observation."""

    name: str
    version: str
    digest: str
    release: str
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
        if name == "scc":
            source = root / ".config/checks/format/selection.toml"
            policy = tomllib.loads(source.read_text(encoding="utf-8"))["budget_tool_supply"]
            key = f"{system}_{arch}"
            archive = f"scc_{key}.tar.gz"
            argument, prefix = "--version", "scc version "
        elif name == "gitleaks":
            source = root / ".config/checks/secrets/supply.toml"
            policy = tomllib.loads(source.read_text(encoding="utf-8"))
            key = f"{system.lower()}_{'x64' if arch == 'x86_64' else arch}"
            archive = f"gitleaks_{policy['version']}_{key}.tar.gz"
            argument, prefix = "version", ""
        else:
            msg = f"native_tool_undeclared:{name}"
            raise ValueError(msg)
        version, digest, release = (
            policy["version"],
            policy["archive_sha256"][key],
            policy["release_owner"],
        )
        if not all(isinstance(value, str) for value in (version, digest, release)) or not (
            re.fullmatch(r"\d+\.\d+\.\d+", version)
            and re.fullmatch(r"[0-9a-f]{64}", digest)
            and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", release)
        ):
            msg = f"native_tool_policy_invalid:{name}"
            raise ValueError(msg)
        return cls(
            name, version, digest, release, archive, f"{system}_{arch}", argument, prefix + version
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
        observed = subprocess.run(
            [str(executable), self.version_argument],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if observed.returncode or observed.stderr or observed.stdout.strip() != self.version_output:
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


def download(command: tuple[str, ...], *, root: Path, timeout: float = 180) -> None:
    """Drain the entire owned transport process group before releasing its cache."""
    with subprocess.Popen(command, cwd=root, stdout=sys.stderr, start_new_session=True) as process:
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        if code:
            raise subprocess.CalledProcessError(code, command)


def prepare(root: Path, name: str, *, lock_timeout: float = 30) -> Path:
    """Converge one declared identity without privileged writes or duplicate effects."""
    root = root.resolve(strict=True)
    supply = NativeSupply.read(root, name)
    home = Path(os.environ.get("ETHOS_CI_TOOL_CACHE_DIR", "build/runtime/tool-cache/ci-tools"))
    home = home if home.is_absolute() else root / home
    cache = home / name / supply.version / supply.platform
    _directory(cache)
    lock = cache / ".prepare.lock"
    if lock.is_symlink() or (lock.exists() and not lock.is_file()):
        msg = f"native_tool_cache_path_unsafe:{lock}"
        raise ValueError(msg)
    with FileLock(lock, timeout=lock_timeout):
        _directory(cache)
        archive, target = cache / supply.archive, cache / name
        with TemporaryDirectory(prefix=".prepare-", dir=cache) as scratch:
            staged_archive = Path(scratch) / supply.archive
            selected = archive
            if not archive.exists() and not archive.is_symlink():
                selected = staged_archive
                download(
                    (
                        "bash",
                        str(root / "tools/ci/scripts/download-file.sh"),
                        f"https://github.com/{supply.release}/releases/download/v{supply.version}/{supply.archive}",
                        str(selected),
                    ),
                    root=root,
                )
            expected = supply.executable_bytes(selected)
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
            if selected == staged_archive:
                staged_archive.replace(archive)
    return cache


def main() -> int:
    """Emit only the exact tool PATH; failures remain nonzero diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("tools", nargs="+", choices=("scc", "gitleaks"))
    arguments = parser.parse_args()
    try:
        paths = [prepare(arguments.root, tool) for tool in dict.fromkeys(arguments.tools)]
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        tarfile.TarError,
        subprocess.SubprocessError,
        Timeout,
    ) as error:
        print(f"native_tool_supply_failed:{error}", file=sys.stderr)
        return 1
    print(os.pathsep.join(str(path) for path in paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
