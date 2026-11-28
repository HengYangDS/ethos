"""Publishing a qualified native payload fails when the host refuses to move its executable."""

from __future__ import annotations

import hashlib
import io
import platform
import shutil
import tarfile
from importlib import import_module
from pathlib import Path

import pytest

owner = import_module("ethos.adapters.repo.runtime.materialization.native_supply")


def _locked_vale(root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Declare one locked Vale archive for this host and return the archive."""
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    archive = root.parent / "vale_3.24.0_macOS_arm64.tar.gz"
    with tarfile.open(archive, "w:gz") as package:
        for name, body in (("vale", b"qualified executable\n"), ("LICENSE", b"license\n")):
            member = tarfile.TarInfo(name)
            member.size, member.mode = len(body), 0o755
            package.addfile(member, io.BytesIO(body))
    config = root / ".config/mise"
    config.mkdir(parents=True)
    (config / "config.toml").write_text('[tools]\n"github:vale-cli/vale" = "3.24.0"\n')
    (config / "mise.lock").write_text(
        'lockfile_version = 3\n[[tools."github:vale-cli/vale"]]\nversion = "3.24.0"\n'
        '[tools."github:vale-cli/vale"."platforms.macos-arm64"]\n'
        f'checksum = "sha256:{hashlib.sha256(archive.read_bytes()).hexdigest()}"\n'
        'url = "https://github.com/vale-cli/vale/releases/download/v3.24.0/'
        f'{archive.name}"\n'
    )
    return archive


def test_publication_fails_when_the_host_refuses_to_move_the_qualified_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refused move is a real failure: no executable is published and no scratch is left."""
    root = tmp_path / "product"
    archive = _locked_vale(root, monkeypatch)
    monkeypatch.setenv("ETHOS_CI_TOOL_CACHE_DIR", str(tmp_path / "supply-cache"))
    monkeypatch.setenv("ETHOS_CI_SUPPLY_MANIFEST", "fixture:offline")
    monkeypatch.delenv("ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR", raising=False)
    supply = owner.NativeSupply.read(root, "vale")
    cache = supply.cache(root)
    cache.mkdir(parents=True)
    shutil.copyfile(archive, cache / supply.archive)
    verified: list[Path] = []
    move = Path.replace

    def refused(source: Path, target: Path) -> Path:
        if source.name == "vale" and source.parent.name == "payload":
            raise PermissionError(source)
        return move(source, target)

    monkeypatch.setattr(owner.NativeSupply, "verify", lambda _self, path: verified.append(path))
    monkeypatch.setattr(Path, "replace", refused)

    with pytest.raises(PermissionError):
        owner.materialize_tool(root, "vale")
    assert not (cache / "vale").exists()
    assert [path.name for path in verified] == ["vale"]
    assert verified[0].parent.name == "payload"
    assert not list(cache.glob(".prepare-*"))
