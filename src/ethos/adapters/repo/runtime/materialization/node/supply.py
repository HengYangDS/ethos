"""Bind native Node build inputs to the existing exact Mise tool lock."""

from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import stat
import tarfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from pathlib import PureWindowsPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import BinaryIO
from urllib.parse import urlsplit

from ethos.adapters.repo.runtime.manifest import process_machine
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import MISE_LOCK
from ethos.adapters.toolchain.mise import native_tool_cache


@dataclass(frozen=True, slots=True)
class NodeRuntime:
    """Contained executable and npm CLI from one complete native distribution."""

    executable: Path
    npm: Path

    @classmethod
    def read(cls, root: Path, *, windows: bool, npm_root: Path | None = None) -> NodeRuntime:
        """Reject redirected runtime components before any consumer executes them."""
        if not windows and platform.system() == "Linux":
            _require_linux_host()
        node = root / ("node.exe" if windows else "bin/node")
        module = npm_root or root / ("node_modules/npm" if windows else "lib/node_modules/npm")
        npm = module / "bin/npm-cli.js"
        for path, boundary in ((node, root), (npm, module if npm_root else root)):
            for component in (path, *path.parents):
                if not component.is_relative_to(boundary):
                    break
                if component.is_symlink() or component.is_junction():
                    message = "native_node_runtime_path_invalid"
                    raise ValueError(message)
        if not node.is_file() or (not windows and not os.access(node, os.X_OK)):
            message = f"package-local Node executable is unavailable: {node}"
            raise ValueError(message)
        if not npm.is_file():
            message = f"package-local npm CLI is unavailable: {npm}"
            raise ValueError(message)
        return cls(node, npm)


def _require_linux_host() -> None:
    """Official GNU Node is not a musl binary or a manylinux certification."""
    libc, version = platform.libc_ver()
    if libc != "glibc" or tuple(int(part) for part in version.split(".")[:2]) < (2, 28):
        message = "native_node_requires_glibc_2_28"
        raise ValueError(message)


def _extract_native_archive(stream: BinaryIO, destination: Path, *, zipped: bool) -> None:
    """Use native safe extraction with an explicit portable member envelope."""
    if zipped:
        with zipfile.ZipFile(stream) as source:
            if any(
                Path(name).is_absolute()
                or ".." in Path(name).parts
                or PureWindowsPath(name).drive
                or "\\" in name
                for name in source.namelist()
            ):
                message = "native_node_archive_members_invalid"
                raise ValueError(message)
            source.extractall(destination)
    else:
        with tarfile.open(fileobj=stream) as source:
            source.extractall(destination, filter="data")


def _retain_native_payload(root: Path, *, windows: bool, bootstrap_npm: bool) -> None:
    """Separate the first-install build seed from the shipped Node-only payload."""
    retained = {"node.exe", "LICENSE"} if windows else {"bin", "LICENSE"}
    if bootstrap_npm:
        retained.add("node_modules" if windows else "lib")
    elif not windows:
        for path in (root / "bin").iterdir():
            if path.name != "node":
                path.unlink()
    for path in root.iterdir():
        if path.name not in retained:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()


@dataclass(frozen=True, slots=True)
class NodeSupply:
    """One official stable archive's exact platform, identity and wheel compatibility."""

    version: str
    target: str
    url: str
    sha256: str
    archive: str
    tag: str

    @classmethod
    def read(cls, root: Path) -> NodeSupply:
        """Read the exact native tool record; unsupported hosts have no fallback."""
        platforms = {
            "Darwin": ("macos", "darwin", "macosx_14_0"),
            "Linux": ("linux", "linux", "linux"),
            "Windows": ("windows", "win", "win"),
        }
        architectures = {"aarch64": "arm64", "arm64": "arm64", "amd64": "x64", "x86_64": "x64"}
        try:
            family, upstream, wheel = platforms[platform.system()]
            if family == "linux":
                _require_linux_host()
            arch = architectures[process_machine().lower()]
            version = tomllib.loads((root / MISE_CONFIG).read_text())["tools"]["node"]
            if not isinstance(version, str) or re.fullmatch(r"\d+\.\d+\.\d+", version) is None:
                message = "native_node_version_invalid"
                raise ValueError(message)
            lock = tomllib.loads((root / MISE_LOCK).read_text())
            records = [row for row in lock["tools"]["node"] if row["version"] == version]
            if lock["lockfile_version"] != 3 or len(records) != 1:
                message = "native_node_lock_mismatch"
                raise ValueError(message)
            target = f"{family}-{arch}"
            material = records[0][f"platforms.{target}"]
            url, checksum = material["url"], material["checksum"]
            parsed = urlsplit(url)
            archive = Path(parsed.path).name
            prefix = f"node-v{version}-{upstream}-{arch}"
            if (
                parsed.scheme != "https"
                or parsed.hostname != "nodejs.org"
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.path != f"/dist/v{version}/{archive}"
                or archive not in {f"{prefix}.tar.gz", f"{prefix}.tar.xz", f"{prefix}.zip"}
                or re.fullmatch(r"sha256:[a-f0-9]{64}", checksum) is None
            ):
                message = "native_node_archive_identity_invalid"
                raise ValueError(message)
            tag_arch = "amd64" if family == "windows" and arch == "x64" else arch
            if family != "windows" and arch == "x64":
                tag_arch = "x86_64"
            if family == "linux" and arch == "arm64":
                tag_arch = "aarch64"
            return cls(version, target, url, checksum[7:], archive, f"py3-none-{wheel}_{tag_arch}")
        except (OSError, KeyError, TypeError, AttributeError) as error:
            message = "native_node_locked_supply_unavailable"
            raise ValueError(message) from error

    def cache(self, root: Path) -> Path:
        """Use the native cache owner, shared across source worktrees."""
        return native_tool_cache(root) / "node" / self.version / self.target

    def project(self, archive: Path, destination: Path, *, bootstrap_npm: bool = True) -> Path:
        """Project Node, its complete bundled modules and license, not unused SDK headers."""
        if archive.is_symlink() or archive.is_junction() or not archive.is_file():
            message = "native_node_archive_unavailable"
            raise ValueError(message)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(archive, flags), "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                message = "native_node_archive_unavailable"
                raise ValueError(message)
            if hashlib.file_digest(stream, "sha256").hexdigest() != self.sha256:
                message = "native_node_archive_checksum_mismatch"
                raise ValueError(message)
            stream.seek(0)
            destination.mkdir()
            _extract_native_archive(stream, destination, zipped=archive.suffix == ".zip")
        roots = tuple(destination.iterdir())
        expected_root = re.sub(r"\.(?:tar\.(?:gz|xz)|zip)$", "", self.archive)
        if (
            len(roots) != 1
            or roots[0].name != expected_root
            or not roots[0].is_dir()
            or roots[0].is_symlink()
            or roots[0].is_junction()
        ):
            message = "native_node_archive_root_invalid"
            raise ValueError(message)
        root = roots[0]
        NodeRuntime.read(root, windows=self.target.startswith("windows-"))
        if not (root / "LICENSE").is_file():
            message = "native_node_archive_runtime_incomplete"
            raise ValueError(message)
        _retain_native_payload(
            root, windows=self.target.startswith("windows-"), bootstrap_npm=bootstrap_npm
        )
        return root

    def installed_root(self, root: Path) -> Path:
        """Select the existing verified build cache, never adopter or ambient Node."""
        return self.cache(root) / "runtime"
