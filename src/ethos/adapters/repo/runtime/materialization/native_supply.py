"""Read locked native release identities and verified executable bytes for every consumer."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import stat
import tarfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ethos.adapters.process import run_command
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import MISE_LOCK
from ethos.adapters.toolchain.mise import native_tool_cache

NATIVE_BACKENDS = {
    "scc": "github:boyter/scc",
    "gitleaks": "github:gitleaks/gitleaks",
    "syft": "github:anchore/syft",
    "vale": "github:vale-cli/vale",
}


@dataclass(frozen=True, slots=True)
class NativeSupply:
    """One product-owned tool identity shared by source, CI and installed consumers."""

    name: str
    backend: str
    version: str
    digest: str
    url: str
    archive: str
    platform: str
    version_argument: str
    version_output: str

    @property
    def executable_name(self) -> str:
        """Use the declared target's native executable suffix, not the caller's host."""
        return self.name + (".exe" if self.platform.startswith("Windows_") else "")

    @classmethod
    def read(cls, root: Path, name: str) -> NativeSupply:
        """Resolve one supported native backend against its exact Mise declaration and lock."""
        system, machine = platform.system(), platform.machine()
        arch = {"aarch64": "arm64", "arm64": "arm64", "amd64": "x86_64", "x86_64": "x86_64"}.get(
            machine.lower()
        )
        family = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(system)
        if family is None or arch is None:
            message = f"native_tool_platform_unsupported:{system}:{machine}"
            raise ValueError(message)
        backend = NATIVE_BACKENDS.get(name)
        if backend is None:
            message = f"native_tool_undeclared:{name}"
            raise ValueError(message)
        target = f"{family}-{'x64' if arch == 'x86_64' else arch}"
        try:
            declarations = tomllib.loads((root / MISE_CONFIG).read_text(encoding="utf-8"))["tools"]
            selected = [key for key in declarations if key.rsplit("/", 1)[-1] == name]
            if selected != [backend]:
                message = f"native_tool_undeclared:{name}"
                raise ValueError(message)
            version = declarations[backend]
            locked = tomllib.loads((root / MISE_LOCK).read_text(encoding="utf-8"))
            records = [row for row in locked["tools"][backend] if row["version"] == version]
            if len(records) != 1 or locked.get("lockfile_version") != 3:
                message = f"native_tool_lock_mismatch:{name}"
                raise ValueError(message)
            material = records[0][f"platforms.{target}"]
            url, checksum = material["url"], material["checksum"]
            parsed = urlsplit(url)
            archive = Path(parsed.path).name
            suffix = ".zip" if system == "Windows" else ".tar.gz"
            publisher = backend.removeprefix("github:")
            if not (
                re.fullmatch(r"\d+\.\d+\.\d+", version)
                and re.fullmatch(r"sha256:[0-9a-f]{64}", checksum)
                and parsed.scheme == "https"
                and parsed.hostname == "github.com"
                and not parsed.username
                and not parsed.password
                and not parsed.query
                and not parsed.fragment
                and parsed.path == f"/{publisher}/releases/download/v{version}/{archive}"
                and archive.endswith(suffix)
            ):
                message = f"native_tool_policy_invalid:{name}"
                raise ValueError(message)
        except (OSError, KeyError, TypeError, AttributeError) as error:
            message = f"native_tool_locked_supply_unavailable:{name}:{target}"
            raise ValueError(message) from error
        argument = "--version" if name in {"scc", "vale"} else "version"
        prefix = {"scc": "scc version ", "vale": "vale version "}.get(name, "")
        return cls(
            name,
            backend,
            version,
            checksum[7:],
            url,
            archive,
            f"{system}_{arch}",
            argument,
            prefix + version,
        )

    def cache(self, root: Path) -> Path:
        """Retain the existing shared Git-common or explicitly bound CI cache ownership."""
        return native_tool_cache(root) / self.name / self.version / self.platform

    def executable_bytes(self, archive: Path) -> bytes:
        """Select one regular native member from the same descriptor that passed hashing."""
        if archive.is_symlink() or archive.is_junction() or not archive.is_file():
            message = f"native_tool_archive_unsafe:{self.name}"
            raise ValueError(message)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(archive, flags), "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                message = f"native_tool_archive_unsafe:{self.name}"
                raise ValueError(message)
            if hashlib.file_digest(stream, "sha256").hexdigest() != self.digest:
                message = f"{self.name}_archive_checksum_mismatch"
                raise ValueError(message)
            stream.seek(0)
            if self.archive.endswith(".zip"):
                with zipfile.ZipFile(stream) as package:
                    matches = [m for m in package.infolist() if m.filename == self.executable_name]
                    if (
                        len(matches) != 1
                        or matches[0].is_dir()
                        or stat.S_IFMT(matches[0].external_attr >> 16) not in {0, stat.S_IFREG}
                    ):
                        message = f"native_tool_archive_executable_invalid:{self.name}"
                        raise ValueError(message)
                    return package.read(matches[0])
            with tarfile.open(fileobj=stream, mode="r:gz") as package:
                matches = [m for m in package if m.name == self.executable_name]
                if len(matches) != 1 or not matches[0].isfile():
                    message = f"native_tool_archive_executable_invalid:{self.name}"
                    raise ValueError(message)
                source = package.extractfile(matches[0])
                if source is None:
                    message = f"native_tool_archive_executable_missing:{self.name}"
                    raise ValueError(message)
                with source:
                    return source.read()

    def verify(self, executable: Path) -> None:
        """Observe the locked native version through the existing bounded process owner."""
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
            message = f"native_tool_executable_version_mismatch:{self.name}"
            raise ValueError(message)
