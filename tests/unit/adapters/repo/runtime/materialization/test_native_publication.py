"""Publishing a qualified native payload outlasts the brief hold Windows keeps on a run image."""

from __future__ import annotations

import hashlib
import io
import platform
import shutil
import tarfile
import time
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


@pytest.mark.parametrize("host", ["windows", "posix"])
def test_publication_retries_only_a_windows_hold_on_the_qualified_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    """Windows may refuse moving a just-run image; elsewhere a refusal is a real failure."""
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
    refusals = [PermissionError(32, "The process cannot access the file")] * 2
    move = Path.replace

    def held(source: Path, target: Path) -> Path:
        if source.name == "vale" and source.parent.name == "payload" and refusals:
            raise refusals.pop()
        return move(source, target)

    monkeypatch.setattr(owner, "_WINDOWS", host == "windows", raising=False)
    monkeypatch.setattr(owner.NativeSupply, "verify", lambda _self, path: verified.append(path))
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(Path, "replace", held)

    if host == "windows":
        assert owner.materialize_tool(root, "vale") == cache
        assert (cache / "vale").read_bytes() == b"qualified executable\n"
        assert (cache / "LICENSE").read_bytes() == b"license\n"
    else:
        with pytest.raises(PermissionError):
            owner.materialize_tool(root, "vale")
        assert not (cache / "vale").exists()
    assert [path.name for path in verified] == ["vale"]
    assert verified[0].parent.name == "payload"
    assert not list(cache.glob(".prepare-*"))
