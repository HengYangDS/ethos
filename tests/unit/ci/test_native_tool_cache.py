"""Share verified native tool bytes across one repository's Git worktrees."""

from __future__ import annotations

import hashlib
import io
import platform
import shutil
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import tools.ci.toolchain.native as native
from ethos.adapters.repo.git import git_common_dir
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from collections.abc import Sequence


@pytest.mark.skipif(platform.system() not in {"Darwin", "Linux"}, reason="native supply target")
def test_linked_worktrees_reuse_one_locked_native_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One Git common-dir owns the cache and lock; sibling roots do not redownload."""
    repo = init_git_repo(tmp_path / "repo")
    backend = "github:gitleaks/gitleaks"
    version = "8.30.1"
    machine = platform.machine()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
    system = "macos" if platform.system() == "Darwin" else "linux"
    target = f"{system}-{'x64' if arch == 'x86_64' else arch}"
    body = b"#!/bin/sh\nprintf '8.30.1\\n'\n"
    package = tmp_path / "fixture.tar.gz"
    with tarfile.open(package, "w:gz") as archive:
        member = tarfile.TarInfo("gitleaks")
        member.size, member.mode = len(body), 0o755
        archive.addfile(member, io.BytesIO(body))
    checksum = hashlib.sha256(package.read_bytes()).hexdigest()
    config = repo / ".config/mise"
    config.mkdir(parents=True)
    (config / "config.toml").write_text(f'[tools]\n"{backend}" = "{version}"\n', encoding="utf-8")
    (config / "mise.lock").write_text(
        f'lockfile_version = 2\n[[tools."{backend}"]]\nversion = "{version}"\n'
        f'[tools."{backend}"."platforms.{target}"]\n'
        f'checksum = "sha256:{checksum}"\n'
        f'url = "https://github.com/fixture/gitleaks/releases/download/v{version}/{package.name}"\n',
        encoding="utf-8",
    )
    commit_fixture(repo, "lock native supply")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
    calls: list[Sequence[str]] = []

    def supply_download(command: tuple[str, ...], *, root: Path, timeout: float = 180) -> None:
        del timeout
        calls.append(command)
        destination = root / "data/downloads" / package.name
        destination.parent.mkdir(parents=True)
        shutil.copyfile(package, destination)

    monkeypatch.setattr(native, "download", supply_download)
    with ThreadPoolExecutor(max_workers=2) as pool:
        caches = tuple(
            pool.map(
                lambda worktree: native.prepare(worktree, "gitleaks", mise=tmp_path / "mise"),
                (repo, linked),
            )
        )
    supply = native.NativeSupply.read(repo, "gitleaks")
    expected = (
        Path(git_common_dir(repo))
        / "ethos/tool-cache/ci-tools/gitleaks"
        / version
        / supply.platform
    )
    assert caches == (expected, expected)
    assert len(calls) == 1
    assert (expected / "gitleaks").read_bytes() == body
    assert supply.executable_bytes(expected / package.name) == body
    assert not (repo / "build/runtime/tool-cache/ci-tools").exists()
    assert not (linked / "build/runtime/tool-cache/ci-tools").exists()
