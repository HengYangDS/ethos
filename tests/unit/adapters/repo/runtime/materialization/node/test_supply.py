"""Keep native Node identity, bytes, platform and extraction within one contract."""

from __future__ import annotations

import hashlib
import io
import platform
import sysconfig
import tarfile
import zipfile
from typing import TYPE_CHECKING

import pytest
import tomli_w

from ethos.adapters.repo.runtime.materialization.node.supply import NodeRuntime
from ethos.adapters.repo.runtime.materialization.node.supply import NodeSupply
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import MISE_LOCK

if TYPE_CHECKING:
    from pathlib import Path


def _archive(path: Path, prefix: str, *, licensed: bool = True) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        for name, data, mode in (
            ("bin/node", b"native Node bytes", 0o755),
            ("lib/node_modules/npm/bin/npm-cli.js", b"npm CLI", 0o644),
            *((("LICENSE", b"license", 0o644),) if licensed else ()),
        ):
            member = tarfile.TarInfo(f"{prefix}/{name}")
            member.size, member.mode = len(data), mode
            archive.addfile(member, io.BytesIO(data))
    return path


def test_project_requires_the_exact_locked_archive_root(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "node-v26.10.0-darwin-arm64.tar.gz", "foreign-root")
    supply = NodeSupply(
        "26.10.0",
        "macos-arm64",
        "",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
        archive.name,
        "py3-none-macosx_14_0_arm64",
    )
    with pytest.raises(ValueError, match="native_node_archive_root_invalid"):
        supply.project(archive, tmp_path / "native")


def test_project_does_not_reopen_a_verified_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefix = "node-v26.10.0-darwin-arm64"
    archive = _archive(tmp_path / f"{prefix}.tar.gz", prefix)
    replacement = _archive(tmp_path / "foreign.tar.gz", "foreign-root")
    supply = NodeSupply(
        "26.10.0",
        "macos-arm64",
        "",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
        archive.name,
        "py3-none-macosx_14_0_arm64",
    )
    original = tarfile.open

    def open_archive(*args: object, **kwargs: object):
        replacement.replace(archive)
        return original(*args, **kwargs)

    monkeypatch.setattr(tarfile, "open", open_archive)
    native = supply.project(archive, tmp_path / "native")
    assert native.name == prefix
    assert (native / "bin/node").read_bytes() == b"native Node bytes"


def test_installed_node_projection_does_not_carry_the_bootstrap_package_manager(
    tmp_path: Path,
) -> None:
    """The package lock supplies npm once; the native projection supplies only Node."""
    prefix = "node-v26.10.0-darwin-arm64"
    archive = _archive(tmp_path / f"{prefix}.tar.gz", prefix)
    supply = NodeSupply(
        "26.10.0",
        "macos-arm64",
        "",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
        archive.name,
        "py3-none-macosx_14_0_arm64",
    )

    native = supply.project(archive, tmp_path / "native", bootstrap_npm=False)

    assert (native / "bin/node").read_bytes() == b"native Node bytes"
    assert (native / "LICENSE").is_file()
    assert not (native / "lib").exists()


def _supply(
    archive: Path, *, target: str = "macos-arm64", checksum: str | None = None
) -> NodeSupply:
    digest = checksum or hashlib.sha256(archive.read_bytes()).hexdigest()
    return NodeSupply("26.10.0", target, "", digest, archive.name, "py3-none-fixture")


def _locked_supply(
    root: Path, *, version: object = "26.10.0", lockfile_version: int = 3, scheme: str = "https"
) -> Path:
    """Write the exact Mise tool declaration and lock shape the supply owner reads."""
    record: dict[str, object] = {"version": "26.10.0", "backend": "core:node"}
    for target, upstream, suffix in (
        ("linux-x64", "linux-x64", "tar.gz"),
        ("linux-arm64", "linux-arm64", "tar.xz"),
        ("macos-x64", "darwin-x64", "tar.gz"),
        ("windows-x64", "win-x64", "zip"),
    ):
        archive = f"node-v26.10.0-{upstream}.{suffix}"
        record[f"platforms.{target}"] = {
            "checksum": "sha256:" + "a" * 64,
            "url": f"{scheme}://nodejs.org/dist/v26.10.0/{archive}",
        }
    (root / MISE_CONFIG).parent.mkdir(parents=True, exist_ok=True)
    (root / MISE_CONFIG).write_text(tomli_w.dumps({"tools": {"node": version}}))
    (root / MISE_LOCK).write_text(
        tomli_w.dumps({"lockfile_version": lockfile_version, "tools": {"node": [record]}})
    )
    return root


def _host(
    monkeypatch: pytest.MonkeyPatch, system: str, machine: str, libc: tuple[str, str]
) -> None:
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(platform, "machine", lambda: machine)
    monkeypatch.setattr(platform, "libc_ver", lambda: libc)


@pytest.mark.parametrize(
    ("system", "machine", "libc", "target", "tag"),
    [
        ("Linux", "x86_64", ("glibc", "2.31"), "linux-x64", "py3-none-linux_x86_64"),
        ("Linux", "aarch64", ("glibc", "2.28"), "linux-arm64", "py3-none-linux_aarch64"),
        ("Darwin", "x86_64", ("", ""), "macos-x64", "py3-none-macosx_14_0_x86_64"),
        ("Windows", "AMD64", ("", ""), "windows-x64", "py3-none-win_amd64"),
    ],
)
def test_locked_supply_selects_one_exact_platform_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    machine: str,
    libc: tuple[str, str],
    target: str,
    tag: str,
) -> None:
    """Each supported host reads only its own locked official archive and wheel tag."""
    _host(monkeypatch, system, machine, libc)
    supply = NodeSupply.read(_locked_supply(tmp_path))
    assert (supply.target, supply.tag, supply.sha256) == (target, tag, "a" * 64)


def test_an_emulated_x64_interpreter_reads_the_x64_archive_and_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows on Arm reports ARM64, while its emulated x64 interpreter installs only win_amd64."""
    _host(monkeypatch, "Windows", "ARM64", ("", ""))
    monkeypatch.setattr(sysconfig, "get_platform", lambda: "win-amd64")
    supply = NodeSupply.read(_locked_supply(tmp_path))
    assert (supply.target, supply.tag) == ("windows-x64", "py3-none-win_amd64")


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("musl", "native_node_requires_glibc_2_28"),
        ("old-glibc", "native_node_requires_glibc_2_28"),
        ("host", "native_node_locked_supply_unavailable"),
        ("version", "native_node_version_invalid"),
        ("lock", "native_node_lock_mismatch"),
        ("url", "native_node_archive_identity_invalid"),
        ("missing", "native_node_locked_supply_unavailable"),
    ],
)
def test_locked_supply_has_no_fallback_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, message: str
) -> None:
    """Unsupported hosts and inexact lock records fail before any download or extraction."""
    libc = {"musl": ("musl", "1.2"), "old-glibc": ("glibc", "2.17")}.get(fault, ("glibc", "2.31"))
    _host(monkeypatch, "FreeBSD" if fault == "host" else "Linux", "x86_64", libc)
    root = _locked_supply(
        tmp_path,
        version="lts" if fault == "version" else "26.10.0",
        lockfile_version=2 if fault == "lock" else 3,
        scheme="http" if fault == "url" else "https",
    )
    if fault == "missing":
        (root / MISE_LOCK).unlink()
    with pytest.raises(ValueError, match=message):
        NodeSupply.read(root)


def test_linux_runtime_read_requires_a_supported_glibc_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Official GNU Node is never executed on an unsupported Linux libc."""
    _host(monkeypatch, "Linux", "x86_64", ("musl", "1.2"))
    with pytest.raises(ValueError, match="native_node_requires_glibc_2_28"):
        NodeRuntime.read(tmp_path, windows=False)


@pytest.mark.parametrize("fault", ["missing", "checksum"])
def test_archive_bytes_are_verified_before_members_are_read(tmp_path: Path, fault: str) -> None:
    """Absent or altered official bytes never reach extraction."""
    prefix = "node-v26.10.0-darwin-arm64"
    archive = _archive(tmp_path / f"{prefix}.tar.gz", prefix)
    supply = _supply(archive, checksum="0" * 64 if fault == "checksum" else None)
    if fault == "missing":
        archive.unlink()
    message = "native_node_archive_unavailable" if fault == "missing" else "checksum_mismatch"
    with pytest.raises(ValueError, match=message):
        supply.project(archive, tmp_path / "native")
    assert not (tmp_path / "native").exists()


def test_projection_requires_the_complete_licensed_runtime(tmp_path: Path) -> None:
    """A runtime without its license is not the complete official distribution."""
    prefix = "node-v26.10.0-darwin-arm64"
    archive = _archive(tmp_path / f"{prefix}.tar.gz", prefix, licensed=False)
    with pytest.raises(ValueError, match="native_node_archive_runtime_incomplete"):
        _supply(archive).project(archive, tmp_path / "native")


def _windows_archive(path: Path, prefix: str, *extra: str) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name in ("node.exe", "node_modules/npm/bin/npm-cli.js", "LICENSE", "README.md"):
            archive.writestr(f"{prefix}/{name}", name)
        for name in extra:
            archive.writestr(name, name)
    return path


def test_windows_projection_keeps_only_the_native_node_payload(tmp_path: Path) -> None:
    """The Windows archive projects Node and its license without the bootstrap npm."""
    prefix = "node-v26.10.0-win-x64"
    archive = _windows_archive(tmp_path / f"{prefix}.zip", prefix)
    native = _supply(archive, target="windows-x64").project(
        archive, tmp_path / "native", bootstrap_npm=False
    )
    assert sorted(path.name for path in native.iterdir()) == ["LICENSE", "node.exe"]


@pytest.mark.parametrize("member", ["node-v26.10.0-win-x64/../escape.txt", "C:/escape.txt", "a\\b"])
def test_windows_archive_members_stay_inside_the_destination(tmp_path: Path, member: str) -> None:
    """Escaping, drive-qualified or backslash members are refused before extraction."""
    prefix = "node-v26.10.0-win-x64"
    archive = _windows_archive(tmp_path / f"{prefix}.zip", prefix, member)
    with pytest.raises(ValueError, match="native_node_archive_members_invalid"):
        _supply(archive, target="windows-x64").project(archive, tmp_path / "native")
    assert not (tmp_path / "escape.txt").exists()
