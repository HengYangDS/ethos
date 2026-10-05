"""Keep native Node identity, bytes, platform and extraction within one contract."""

from __future__ import annotations

import hashlib
import io
import tarfile
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.runtime.materialization.node.supply import NodeSupply

if TYPE_CHECKING:
    from pathlib import Path


def _archive(path: Path, prefix: str) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        for name, data, mode in (
            ("bin/node", b"native Node bytes", 0o755),
            ("lib/node_modules/npm/bin/npm-cli.js", b"npm CLI", 0o644),
            ("LICENSE", b"license", 0o644),
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
