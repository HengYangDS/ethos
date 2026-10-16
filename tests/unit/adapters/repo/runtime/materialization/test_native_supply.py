"""Locked native supply belongs to the installed product, not a CI-only module."""

from __future__ import annotations

import hashlib
import io
import platform
import tarfile
import zipfile
from importlib import import_module
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def locked_vale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Declare one exact official identity and controlled archive for each target."""
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
        else:
            with tarfile.open(package, "w:gz") as archive:
                member = tarfile.TarInfo(executable)
                member.size, member.mode = len(body), 0o755
                archive.addfile(member, io.BytesIO(body))
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
    assert not (root / "build").exists()


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
