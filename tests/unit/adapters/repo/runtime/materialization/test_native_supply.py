"""Locked native supply belongs to the installed product, not a CI-only module."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import platform
import shutil
import sys
import tarfile
import zipfile
from importlib import import_module
from importlib.metadata import Distribution
from pathlib import Path

import pytest

from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.manifest import process_machine


@pytest.fixture
def locked_vale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Declare one exact official identity and controlled archive for each target."""
    monkeypatch.delenv("ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR", raising=False)
    monkeypatch.delenv("ETHOS_CI_TOOL_CACHE_DIR", raising=False)
    root = tmp_path / "product [literal]"
    config = root / ".config/mise"
    config.mkdir(parents=True)
    version = "3.24.0"
    (config / "config.toml").write_text(f'[tools]\n"github:vale-cli/vale" = "{version}"\n')

    def declare(system: str, machine: str, target: str, asset: str):
        monkeypatch.setattr(platform, "system", lambda: system)
        monkeypatch.setattr(platform, "machine", lambda: machine)
        package = tmp_path / asset
        executable = "vale.exe" if system == "Windows" else "vale"
        body = b"locked native executable bytes\n"
        if asset.endswith(".zip"):
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr(executable, body)
                archive.writestr("LICENSE", b"Publisher license\n")
        else:
            with tarfile.open(package, "w:gz") as archive:
                member = tarfile.TarInfo(executable)
                member.size, member.mode = len(body), 0o755
                archive.addfile(member, io.BytesIO(body))
                license_member = tarfile.TarInfo("LICENSE")
                license_member.size = len(b"Publisher license\n")
                archive.addfile(license_member, io.BytesIO(b"Publisher license\n"))
        checksum = hashlib.sha256(package.read_bytes()).hexdigest()
        lock = config / "mise.lock"
        lock.write_text(
            f'lockfile_version = 3\n[[tools."github:vale-cli/vale"]]\n'
            f'version = "{version}"\n'
            f'[tools."github:vale-cli/vale"."platforms.{target}"]\n'
            f'checksum = "sha256:{checksum}"\n'
            f'url = "https://github.com/vale-cli/vale/releases/download/v{version}/{asset}"\n'
        )
        return root, package, body, lock

    return declare


@pytest.mark.parametrize(
    ("system", "machine", "target", "asset"),
    [
        ("Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"),
        ("Darwin", "x86_64", "macos-x64", "vale_3.24.0_macOS_64-bit.tar.gz"),
        ("Linux", "aarch64", "linux-arm64", "vale_3.24.0_Linux_arm64.tar.gz"),
        ("Linux", "x86_64", "linux-x64", "vale_3.24.0_Linux_64-bit.tar.gz"),
        ("Windows", "AMD64", "windows-x64", "vale_3.24.0_Windows_64-bit.zip"),
    ],
)
def test_product_native_supply_reads_locked_platform_without_mutation(
    locked_vale, system: str, machine: str, target: str, asset: str
) -> None:
    """Every admitted platform selects exact archive bytes; no host fallback is needed."""
    root, archive, body, lock = locked_vale(system, machine, target, asset)
    original = {path: path.read_bytes() for path in (archive, lock, lock.parent / "config.toml")}
    supply = import_module("ethos.adapters.repo.runtime.materialization.native_supply").NativeSupply

    selected = supply.read(root, "vale")

    assert selected.backend == "github:vale-cli/vale"
    assert selected.version_output == "vale version 3.24.0"
    assert selected.executable_name == ("vale.exe" if system == "Windows" else "vale")
    assert selected.executable_bytes(archive) == body
    assert {path: path.read_bytes() for path in original} == original
    assert not (root / "build").exists()


def test_locked_supply_rejects_another_release_owner(locked_vale) -> None:
    """A GitHub URL alone cannot stand in for the selected official publisher."""
    root, archive, _body, lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    lock.write_text(
        lock.read_text().replace("github.com/vale-cli/vale/", "github.com/foreign/vale/")
    )
    original = archive.read_bytes()
    supply = import_module("ethos.adapters.repo.runtime.materialization.native_supply").NativeSupply

    with pytest.raises(ValueError, match="native_tool_policy_invalid:vale"):
        supply.read(root, "vale")

    assert archive.read_bytes() == original


@pytest.mark.parametrize(
    ("system", "machine", "target", "asset"),
    [
        ("Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"),
        ("Windows", "AMD64", "windows-x64", "vale_3.24.0_Windows_64-bit.zip"),
    ],
)
def test_product_projection_retains_native_executable_and_publisher_license(
    locked_vale, tmp_path: Path, system: str, machine: str, target: str, asset: str
) -> None:
    """A distributable native payload contains its executable and original license."""
    root, archive, body, _lock = locked_vale(system, machine, target, asset)
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    selected = owner.NativeSupply.read(root, "vale")
    destination = tmp_path / "payload [literal]"
    original = archive.read_bytes()

    assert selected.project(archive, destination) == destination

    assert {path.name for path in destination.iterdir()} == {selected.executable_name, "LICENSE"}
    assert (destination / selected.executable_name).read_bytes() == body
    assert (destination / "LICENSE").read_bytes() == b"Publisher license\n"
    assert archive.read_bytes() == original


def test_missing_publisher_license_refuses_projection_without_destination(locked_vale, tmp_path):
    """The locked checksum does not waive a complete distributable payload."""
    root, archive, body, lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    with tarfile.open(archive, "w:gz") as package:
        member = tarfile.TarInfo("vale")
        member.size = len(body)
        package.addfile(member, io.BytesIO(body))
    text = lock.read_text()
    checksum = next(line for line in text.splitlines() if line.startswith("checksum = "))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    lock.write_text(text.replace(checksum, f'checksum = "sha256:{digest}"'))
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    destination = tmp_path / "missing-license"

    with pytest.raises(ValueError, match="native_tool_archive_license_invalid:vale"):
        owner.NativeSupply.read(root, "vale").project(archive, destination)

    assert not destination.exists()


def test_package_projection_does_not_require_execution_only_dependencies(
    locked_vale, tmp_path: Path
) -> None:
    """A native artifact build reads locked bytes without loading the mutable installer."""
    system, machine = platform.system(), process_machine()
    targets = {
        ("Darwin", "arm64"): ("macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"),
        ("Darwin", "x86_64"): ("macos-x64", "vale_3.24.0_macOS_64-bit.tar.gz"),
        ("Linux", "aarch64"): ("linux-arm64", "vale_3.24.0_Linux_arm64.tar.gz"),
        ("Linux", "x86_64"): ("linux-x64", "vale_3.24.0_Linux_64-bit.tar.gz"),
        ("Windows", "AMD64"): ("windows-x64", "vale_3.24.0_Windows_64-bit.zip"),
    }
    target, asset = targets[(system, machine)]
    root, archive, body, _lock = locked_vale(system, machine, target, asset)
    product = Path(__file__).resolve().parents[6]
    destination = tmp_path / "build-payload"
    script = f"""
import builtins, sys
from pathlib import Path
sys.path.insert(0, {str(product / "src")!r})
original_import = builtins.__import__
def build_import(name, *args, **kwargs):
    if name == 'filelock':
        raise ModuleNotFoundError('filelock is not a build-system requirement')
    return original_import(name, *args, **kwargs)
builtins.__import__ = build_import
from ethos.adapters.repo.runtime.materialization.native_supply import NativeSupply
supply = NativeSupply.read(Path({str(root)!r}), 'vale')
supply.project(Path({str(archive)!r}), Path({str(destination)!r}))
"""

    result = run_command(tmp_path, (sys.executable, "-B", "-I", "-c", script), timeout=20)

    assert result.returncode == 0, result.stdout + result.stderr
    executable = "vale.exe" if system == "Windows" else "vale"
    assert (destination / executable).read_bytes() == body
    assert (destination / "LICENSE").read_bytes() == b"Publisher license\n"


def test_product_materializer_consumes_complete_cached_supply_without_download(
    locked_vale, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same installed owner serves source and CI from exact offline bytes."""
    root, archive, body, _lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    monkeypatch.setenv("ETHOS_CI_TOOL_CACHE_DIR", str(tmp_path / "supply-cache"))
    monkeypatch.setenv("ETHOS_CI_SUPPLY_MANIFEST", "fixture:offline")
    selected = owner.NativeSupply.read(root, "vale")
    cache = selected.cache(root)
    assert cache == tmp_path / "supply-cache/vale/3.24.0/Darwin_arm64"
    cache.mkdir(parents=True)
    shutil.copyfile(archive, cache / selected.archive)
    monkeypatch.setattr(owner.NativeSupply, "verify", lambda _self, _executable: None)

    assert owner.materialize_tool(root, "vale") == cache

    assert (cache / selected.executable_name).read_bytes() == body
    assert (cache / "LICENSE").read_bytes() == b"Publisher license\n"
    assert not list(cache.glob(".prepare-*"))
    assert not (root / "build").exists()


def test_source_consumer_resolves_locked_payload_without_ambient_tool(
    locked_vale, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reading exact prepared supply never installs, repairs or consults PATH."""
    root, archive, body, _lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    monkeypatch.setenv("ETHOS_CI_TOOL_CACHE_DIR", str(tmp_path / "supply-cache"))
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(
        owner, "canonical_resource", lambda relative: root / relative, raising=False
    )
    monkeypatch.setattr(
        owner,
        "packaged_resource",
        lambda relative="": tmp_path / "shipped" / relative,
        raising=False,
    )
    selected = owner.NativeSupply.read(root, "vale")
    cache = selected.cache(root)
    assert cache == tmp_path / "supply-cache/vale/3.24.0/Darwin_arm64"
    cache.mkdir(parents=True)
    shutil.copyfile(archive, cache / selected.archive)
    payload = selected.project(archive, tmp_path / "prepared")
    for member in payload.iterdir():
        member.replace(cache / member.name)
    original = {path: path.read_bytes() for path in cache.iterdir()}

    executable = owner.resolve_native_tool("vale")

    assert executable == cache / "vale"
    assert executable.read_bytes() == body
    assert {path: path.read_bytes() for path in cache.iterdir()} == original
    assert not (root / "build").exists()


@pytest.fixture
def installed_vale(locked_vale, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create a real installed RECORD anchored to one loaded product package."""
    root, archive, body, _lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    resources = import_module("ethos.repository.release.resources")
    prefix = tmp_path / "installed [literal]"
    package = prefix / "ethos"
    shipped = package / "resources"
    shutil.copytree(root / ".config", shipped / ".config")
    (shipped / "pyproject.toml").write_text('[project]\nname = "ethos"\n')
    native = shipped / "native/vale"
    owner.NativeSupply.read(root, "vale").project(archive, native)
    metadata = prefix / "ethos-1.0.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Metadata-Version: 2.1\nName: ethos\nVersion: 1.0.0\n")
    with (metadata / "RECORD").open("w", newline="") as record:
        writer = csv.writer(record)
        for path in sorted(shipped.rglob("*")):
            if path.is_file():
                material = path.read_bytes()
                digest = base64.urlsafe_b64encode(hashlib.sha256(material).digest()).rstrip(b"=")
                writer.writerow(
                    (
                        path.relative_to(prefix).as_posix(),
                        "sha256=" + digest.decode(),
                        len(material),
                    )
                )
    monkeypatch.setattr(resources, "files", lambda _name: package)
    monkeypatch.setattr(
        resources, "distribution", lambda _name: Distribution.at(metadata), raising=False
    )
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("ETHOS_CI_TOOL_CACHE_DIR", str(tmp_path / "foreign-cache"))
    return shipped, native, body


def test_installed_consumer_resolves_record_bound_payload_without_source_cache(installed_vale):
    """The loaded package, not the adopter or an ambient installation, owns execution."""
    shipped, native, body = installed_vale
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    original = {path: path.read_bytes() for path in shipped.rglob("*") if path.is_file()}

    executable = owner.resolve_native_tool("vale")

    assert executable == native / "vale"
    assert executable.read_bytes() == body
    assert {path: path.read_bytes() for path in shipped.rglob("*") if path.is_file()} == original


@pytest.mark.parametrize(
    ("relative", "effect"),
    [
        ("native/vale/vale", "tamper"),
        ("native/vale/LICENSE", "remove"),
        (".config/mise/mise.lock", "tamper"),
    ],
)
def test_installed_consumer_refuses_changed_supply_without_repair(
    installed_vale, relative: str, effect: str
) -> None:
    """An installed file outside its original RECORD is not an accepted substitute."""
    shipped, _native, _body = installed_vale
    path = shipped / relative
    if effect == "tamper":
        path.write_bytes(path.read_bytes() + b"\n# changed\n")
    else:
        path.unlink()
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    original = {path: path.read_bytes() for path in shipped.rglob("*") if path.is_file()}

    with pytest.raises(ValueError, match="product_resource_integrity_invalid"):
        owner.resolve_native_tool("vale")

    assert {path: path.read_bytes() for path in shipped.rglob("*") if path.is_file()} == original


def test_native_archive_consumes_the_verified_descriptor(locked_vale, monkeypatch) -> None:
    """A path replacement after verification cannot change the interpreted bytes."""
    root, archive, body, _lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    replacement = archive.with_name("replacement.tar.gz")
    with tarfile.open(replacement, "w:gz") as package:
        member = tarfile.TarInfo("vale")
        member.size = 7
        package.addfile(member, io.BytesIO(b"foreign"))
    supply = import_module("ethos.adapters.repo.runtime.materialization.native_supply").NativeSupply
    selected = supply.read(root, "vale")
    native_open = tarfile.open

    def replace_path(*args, **kwargs):
        replacement.replace(archive)
        return native_open(*args, **kwargs)

    monkeypatch.setattr(tarfile, "open", replace_path)

    assert selected.executable_bytes(archive) == body


def test_native_zip_requires_one_regular_executable(locked_vale) -> None:
    """A ZIP symlink named as the tool is not an executable member."""
    root, archive, _body, lock = locked_vale(
        "Windows", "AMD64", "windows-x64", "vale_3.24.0_Windows_64-bit.zip"
    )
    with zipfile.ZipFile(archive, "w") as package:
        entry = zipfile.ZipInfo("vale.exe")
        entry.create_system = 3
        entry.external_attr = 0o120777 << 16
        package.writestr(entry, "/outside")
    text = lock.read_text()
    checksum = next(line for line in text.splitlines() if line.startswith("checksum = "))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    lock.write_text(text.replace(checksum, f'checksum = "sha256:{digest}"'))
    original = archive.read_bytes()
    supply = import_module("ethos.adapters.repo.runtime.materialization.native_supply").NativeSupply

    with pytest.raises(ValueError, match="native_tool_archive_executable_invalid:vale"):
        supply.read(root, "vale").executable_bytes(archive)

    assert archive.read_bytes() == original


@pytest.mark.parametrize(
    ("effect", "reason"),
    [
        ("declaration", "native_tool_undeclared:vale"),
        ("lock", "native_tool_lock_mismatch:vale"),
        ("missing", "native_tool_locked_supply_unavailable:vale:macos-arm64"),
        ("platform", "native_tool_platform_unsupported:Unknown:arm64"),
        ("backend", "native_tool_undeclared:unselected"),
    ],
)
def test_native_supply_requires_one_complete_supported_identity(
    locked_vale, monkeypatch, effect, reason
):
    """Unsupported or incomplete identities cannot acquire an ambient substitute."""
    root, archive, _body, lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    if effect == "declaration":
        (lock.parent / "config.toml").write_text("[tools]\n")
    elif effect == "lock":
        lock.write_text(lock.read_text().replace("lockfile_version = 3", "lockfile_version = 2"))
    elif effect == "missing":
        lock.unlink()
    elif effect == "platform":
        monkeypatch.setattr(platform, "system", lambda: "Unknown")
    original = archive.read_bytes()
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    with pytest.raises(ValueError, match=reason):
        owner.NativeSupply.read(root, "unselected" if effect == "backend" else "vale")
    assert archive.read_bytes() == original
    assert not (root / "build").exists()


@pytest.mark.parametrize(
    ("effect", "reason"),
    [
        ("payload", "native_tool_runtime_payload_invalid:vale:vale"),
        ("permission", "native_tool_runtime_executable_unavailable:vale"),
        ("redirect", "native_tool_runtime_path_invalid:vale"),
        ("archive", "vale_archive_checksum_mismatch"),
        ("archive-redirect", "native_tool_archive_unsafe:vale"),
    ],
)
def test_prepared_native_supply_rejects_drift_without_repair(
    locked_vale, tmp_path, monkeypatch, effect, reason
):
    """The source consumer checks locked identity, bytes, path safety and execution permission."""
    root, archive, _body, _lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    monkeypatch.setenv("ETHOS_CI_TOOL_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(owner, "canonical_resource", lambda relative: root / relative)
    monkeypatch.setattr(
        owner, "packaged_resource", lambda relative="": tmp_path / "shipped" / relative
    )
    supply = owner.NativeSupply.read(root, "vale")
    cache = supply.cache(root)
    supply.project(archive, cache)
    cached_archive = cache / supply.archive
    shutil.copyfile(archive, cached_archive)
    executable = cache / supply.executable_name
    if effect == "payload":
        executable.write_bytes(b"unaccepted executable\n")
    elif effect == "archive":
        cached_archive.write_bytes(b"unaccepted archive\n")
    elif effect == "permission":
        monkeypatch.setattr(owner.os, "access", lambda _path, _mode: False)
    else:
        target = executable if effect == "redirect" else cached_archive
        is_symlink = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == target or is_symlink(path))
    original = {path: path.read_bytes() for path in cache.iterdir()}
    with pytest.raises(ValueError, match=reason):
        owner.resolve_native_tool("vale")
    assert {path: path.read_bytes() for path in cache.iterdir()} == original


def test_installed_native_supply_requires_execution_permission(installed_vale, monkeypatch):
    """RECORD integrity does not waive the installed executable's native permission."""
    shipped, _native, _body = installed_vale
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    monkeypatch.setattr(owner.os, "access", lambda _path, _mode: False)
    original = {path: path.read_bytes() for path in shipped.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="native_tool_runtime_executable_unavailable:vale"):
        owner.resolve_native_tool("vale")
    assert {path: path.read_bytes() for path in shipped.rglob("*") if path.is_file()} == original


@pytest.mark.parametrize("boundary", ["lock", "download"])
def test_native_preparation_refuses_unsafe_or_ambiguous_supply(
    locked_vale, tmp_path, monkeypatch, boundary
):
    """A preparation refusal keeps cached originals and disposes its bounded scratch."""
    root, _archive, _body, _lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    monkeypatch.setenv("ETHOS_CI_TOOL_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("ETHOS_CI_SUPPLY_MANIFEST", raising=False)
    supply = owner.NativeSupply.read(root, "vale")
    cache = supply.cache(root)
    cache.mkdir(parents=True)
    if boundary == "lock":
        (cache / ".prepare.lock").mkdir()
    monkeypatch.setattr(owner, "download_tool", lambda *_args, **_kwargs: None)
    reason = (
        "native_tool_cache_path_unsafe"
        if boundary == "lock"
        else "native_tool_download_unresolved:vale"
    )
    with pytest.raises(ValueError, match=reason):
        owner.materialize_tool(root, "vale", mise=tmp_path / "unused-mise")
    assert not (cache / supply.archive).exists()
    assert not (cache / supply.executable_name).exists()
    assert not list(cache.glob(".prepare-*"))


@pytest.mark.parametrize("boundary", ["descriptor", "directory"])
def test_native_projection_rechecks_type_before_read_or_write(
    locked_vale, tmp_path, monkeypatch, boundary
):
    """Path metadata cannot waive a nonregular descriptor or existing file at the parent."""
    root, archive, _body, _lock = locked_vale(
        "Darwin", "arm64", "macos-arm64", "vale_3.24.0_macOS_arm64.tar.gz"
    )
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    parent = tmp_path / "projection-parent"
    destination = parent / "payload"
    if boundary == "directory":
        parent.write_bytes(b"Preserved foreign file.\n")
    original = archive.read_bytes()
    with monkeypatch.context() as scoped:
        if boundary == "descriptor":
            scoped.setattr(owner.stat, "S_ISREG", lambda _mode: False)
            reason = "native_tool_archive_unsafe:vale"
        else:
            reason = "native_tool_cache_path_unsafe"
        with pytest.raises(ValueError, match=reason):
            owner.NativeSupply.read(root, "vale").project(archive, destination)
    assert archive.read_bytes() == original
    assert not destination.exists()
    if boundary == "directory":
        assert parent.read_bytes() == b"Preserved foreign file.\n"


def test_cue_native_supply_preserves_original_archive_layout_and_license(tmp_path, monkeypatch):
    """CUE's native locked asset, not a GitHub shorthand, supplies its real nested payload."""
    root = tmp_path / "product"
    config = root / ".config/mise"
    config.mkdir(parents=True)
    (config / "config.toml").write_text('[tools]\ncue = "0.17.1"\n')
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    archive = tmp_path / "cue_v0.17.1_darwin_arm64.tar.gz"
    with tarfile.open(archive, "w:gz") as package:
        for name, body in (("cue", b"actual native CUE bytes"), ("LICENSE", b"publisher license")):
            entry = tarfile.TarInfo(name)
            entry.size = len(body)
            package.addfile(entry, io.BytesIO(body))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (config / "mise.lock").write_text(
        'lockfile_version = 3\n[[tools.cue]]\nversion = "0.17.1"\nbackend = "aqua:cue-lang/cue"\n'
        '[tools.cue."platforms.macos-arm64"]\n'
        f'checksum = "sha256:{digest}"\n'
        'url = "https://github.com/cue-lang/cue/releases/download/v0.17.1/cue_v0.17.1_darwin_arm64.tar.gz"\n'
    )
    owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")
    supply = owner.NativeSupply.read(root, "cue")
    assert supply.backend == "cue"
    assert supply.payload_bytes(archive) == {
        "cue": b"actual native CUE bytes",
        "LICENSE": b"publisher license",
    }
    assert supply.version_argument == "version"
    assert supply.version_output == "cue version v0.17.1"
