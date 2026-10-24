"""Read locked native release identities and verified executable bytes for every consumer."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import stat
import sys
import tarfile
import tomllib
import zipfile
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.materialization.node.supply import NodeRuntime
from ethos.adapters.repo.runtime.materialization.node.supply import NodeSupply
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import MISE_LOCK
from ethos.adapters.toolchain.mise import mise_executable
from ethos.adapters.toolchain.mise import native_tool_cache
from ethos.repository.release.resources import canonical_resource
from ethos.repository.release.resources import packaged_resource
from ethos.repository.release.resources import require_packaged_resource

NATIVE_BACKENDS = {
    "cue": "cue",
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
            publisher = "cue-lang/cue" if name == "cue" else backend.removeprefix("github:")
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
        prefix = {"cue": "cue version v", "scc": "scc version ", "vale": "vale version "}.get(
            name, ""
        )
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
        return self._archive_members(archive, (self.executable_name,))[self.executable_name]

    def payload_bytes(self, archive: Path) -> dict[str, bytes]:
        """Read the complete distributable payload through the sole archive verifier."""
        return self._archive_members(archive, (self.executable_name, "LICENSE"))

    def project(self, archive: Path, destination: Path) -> Path:
        """Project the complete verified executable and original publisher license."""
        members = self.payload_bytes(archive)
        ensure_native_directory(destination.parent)
        destination.mkdir()
        for name, body in members.items():
            target = destination / name
            with target.open("xb") as output:
                output.write(body)
            target.chmod(0o755 if name == self.executable_name else 0o644)
        return destination

    def _archive_members(self, archive: Path, names: tuple[str, ...]) -> dict[str, bytes]:
        """Validate every selected member before creating any output path."""
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
                    return {name: _zip_member(package, name, self.name) for name in names}
            with tarfile.open(fileobj=stream, mode="r:gz") as package:
                return {name: _tar_member(package, name, self.name) for name in names}

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
            else observed.stdout.splitlines()[0]
            if self.name == "cue" and observed.stdout
            else observed.stdout.strip()
        )
        if observed.returncode or observed.stderr or version != self.version_output:
            message = f"native_tool_executable_version_mismatch:{self.name}"
            raise ValueError(message)


def _zip_member(package: zipfile.ZipFile, name: str, tool: str) -> bytes:
    matches = [item for item in package.infolist() if item.filename == name]
    if (
        len(matches) != 1
        or matches[0].is_dir()
        or stat.S_IFMT(matches[0].external_attr >> 16) not in {0, stat.S_IFREG}
    ):
        kind = "license" if name == "LICENSE" else "executable"
        message = f"native_tool_archive_{kind}_invalid:{tool}"
        raise ValueError(message)
    return package.read(matches[0])


def _tar_member(package: tarfile.TarFile, name: str, tool: str) -> bytes:
    matches = [item for item in package.getmembers() if item.name == name]
    kind = "license" if name == "LICENSE" else "executable"
    if len(matches) != 1 or not matches[0].isfile():
        message = f"native_tool_archive_{kind}_invalid:{tool}"
        raise ValueError(message)
    source = package.extractfile(matches[0])
    if source is None:
        message = f"native_tool_archive_{kind}_missing:{tool}"
        raise ValueError(message)
    with source:
        return source.read()


def resolve_native_tool(name: str) -> Path:
    """Read prepared product supply without installing, repairing or consulting PATH."""
    project = canonical_resource("pyproject.toml").parent
    if project == packaged_resource():
        for relative in (MISE_CONFIG, MISE_LOCK):
            require_packaged_resource(relative)
        supply = NativeSupply.read(project, name)
        executable = require_packaged_resource(f"native/{name}/{supply.executable_name}")
        require_packaged_resource(f"native/{name}/LICENSE")
        if not os.access(executable, os.X_OK):
            message = f"native_tool_runtime_executable_unavailable:{name}"
            raise ValueError(message)
        return executable
    supply = NativeSupply.read(project, name)
    root = supply.cache(project)
    expected = supply.payload_bytes(root / supply.archive)
    for member, body in expected.items():
        path = root / member
        for component in (path, *path.parents):
            if component.is_symlink() or component.is_junction():
                message = f"native_tool_runtime_path_invalid:{name}"
                raise ValueError(message)
        if not path.is_file() or path.read_bytes() != body:
            message = f"native_tool_runtime_payload_invalid:{name}:{member}"
            raise ValueError(message)
    executable = root / supply.executable_name
    if not os.access(executable, os.X_OK):
        message = f"native_tool_runtime_executable_unavailable:{name}"
        raise ValueError(message)
    return executable


def ensure_native_directory(path: Path) -> None:
    """Create only ordinary supply directories without following redirections."""
    for component in (*reversed(path.parents), path):
        if (
            component.is_symlink()
            or component.is_junction()
            or (component.exists() and not component.is_dir())
        ):
            message = f"native_tool_cache_path_unsafe:{component}"
            raise ValueError(message)
        component.mkdir(exist_ok=True)


def native_supply_is_offline() -> bool:
    """Manifest-bound hosted inputs may be verified, never downloaded or replaced."""
    return bool(os.environ.get("ETHOS_CI_SUPPLY_MANIFEST"))


def download_tool(command: tuple[str, ...], *, root: Path, timeout: float = 180) -> None:
    """Run the native provisioner through the existing bounded process owner."""
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
            "MISE_STATE_DIR": str(root / "state"),
            "MISE_GLOBAL_CONFIG_FILE": str(root / "absent-global.toml"),
            "MISE_SYSTEM_CONFIG_DIR": str(root / "absent-system"),
        },
    )
    sys.stderr.write(result.stdout + result.stderr)
    result.check_returncode()


def materialize_tool(
    root: Path, name: str, *, lock_timeout: float = 30, mise: Path | None = None
) -> Path:
    """Converge the sole product-owned native supply for source, CI and packaging."""
    root = root.resolve(strict=True)
    supply = NodeSupply.read(root) if name == "node" else NativeSupply.read(root, name)
    cache = supply.cache(root)
    ensure_native_directory(cache)
    lock = cache / ".prepare.lock"
    if lock.is_symlink() or (lock.exists() and not lock.is_file()):
        message = f"native_tool_cache_path_unsafe:{lock}"
        raise ValueError(message)
    with import_module("filelock").FileLock(lock, timeout=lock_timeout):
        ensure_native_directory(cache)
        archive = cache / supply.archive
        with TemporaryDirectory(prefix=".prepare-", dir=cache) as scratch:
            selected = archive
            if not archive.exists() and not archive.is_symlink():
                if native_supply_is_offline():
                    message = f"native_tool_offline_cache_missing:{name}"
                    raise ValueError(message)
                isolated = Path(scratch)
                for source in (MISE_CONFIG, MISE_LOCK):
                    target_config = isolated / source
                    target_config.parent.mkdir(parents=True, exist_ok=True)
                    target_config.write_bytes((root / source).read_bytes())
                download_tool(
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
                    message = f"native_tool_download_unresolved:{name}"
                    raise ValueError(message)
                selected = candidates[0]
            if isinstance(supply, NodeSupply):
                return _materialize_node(supply, selected, cache, Path(scratch))
            _materialize_native(supply, selected, cache, Path(scratch))
    return cache


def _materialize_native(supply: NativeSupply, archive: Path, cache: Path, scratch: Path) -> None:
    """Publish only a complete, version-qualified native payload."""
    prepared = supply.project(archive, scratch / "payload")
    expected_archive = cache / supply.archive
    if archive != expected_archive:
        archive.replace(expected_archive)
    members = tuple(prepared.iterdir())
    intact = all(
        not (cache / member.name).is_symlink()
        and not (cache / member.name).is_junction()
        and (cache / member.name).is_file()
        and (cache / member.name).read_bytes() == member.read_bytes()
        for member in members
    ) and os.access(cache / supply.executable_name, os.X_OK)
    if intact:
        supply.verify(cache / supply.executable_name)
    else:
        supply.verify(prepared / supply.executable_name)
        for member in members:
            member.replace(cache / member.name)


def _materialize_node(supply: NodeSupply, archive: Path, cache: Path, scratch: Path) -> Path:
    """Preserve complete Node cache identity, native version checks and shared ownership."""
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
