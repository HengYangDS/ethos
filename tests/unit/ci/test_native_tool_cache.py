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

import ethos.adapters.repo.runtime.materialization.native_supply as native_supply
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import process_machine
from ethos.adapters.repo.runtime.materialization.native_supply import NativeSupply
from ethos.adapters.repo.runtime.materialization.node.supply import NodeSupply
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import mise_executable
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.mise_host import outside_ci

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

GITLEAKS_BODY = b"#!/bin/sh\nprintf '8.30.1\\n'\n"


def _locked_gitleaks(root: Path, package: Path) -> None:
    """Lock gitleaks 8.30.1 for this host to one archive that ships it and its license."""
    machine = process_machine()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
    system = "macos" if platform.system() == "Darwin" else "linux"
    target = f"{system}-{'x64' if arch == 'x86_64' else arch}"
    with tarfile.open(package, "w:gz") as archive:
        member = tarfile.TarInfo("gitleaks")
        member.size, member.mode = len(GITLEAKS_BODY), 0o755
        archive.addfile(member, io.BytesIO(GITLEAKS_BODY))
        license_member = tarfile.TarInfo("LICENSE")
        license_member.size = len(b"Publisher license\n")
        archive.addfile(license_member, io.BytesIO(b"Publisher license\n"))
    checksum = hashlib.sha256(package.read_bytes()).hexdigest()
    config = root / ".config/mise"
    config.mkdir(parents=True)
    backend = "github:gitleaks/gitleaks"
    (config / "config.toml").write_text(f'[tools]\n"{backend}" = "8.30.1"\n', encoding="utf-8")
    (config / "mise.lock").write_text(
        f'lockfile_version = 3\n[[tools."{backend}"]]\nversion = "8.30.1"\n'
        f'[tools."{backend}"."platforms.{target}"]\n'
        f'checksum = "sha256:{checksum}"\n'
        f'url = "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/{package.name}"\n',
        encoding="utf-8",
    )


@pytest.mark.skipif(platform.system() not in {"Darwin", "Linux"}, reason="native supply target")
@pytest.mark.parametrize(
    "cache_selector",
    [None, "ETHOS_CI_TOOL_CACHE_DIR", "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR"],
)
def test_linked_worktrees_reuse_one_locked_native_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cache_selector: str | None
) -> None:
    """One Git common-dir owns the cache and lock; sibling roots do not redownload."""
    for name in ("ETHOS_CI_TOOL_CACHE_DIR", "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR"):
        monkeypatch.delenv(name, raising=False)
    if cache_selector is not None:
        monkeypatch.setenv(cache_selector, str(tmp_path / "explicit-cache"))
    repo = init_git_repo(tmp_path / "repo")
    package = tmp_path / "fixture.tar.gz"
    _locked_gitleaks(repo, package)
    commit_fixture(repo, "lock native supply")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
    calls: list[Sequence[str]] = []

    def supply_download(command: tuple[str, ...], *, root: Path, **_options: object) -> None:
        calls.append(command)
        destination = root / "data/downloads" / package.name
        destination.parent.mkdir(parents=True)
        shutil.copyfile(package, destination)

    monkeypatch.setattr(native_supply, "download_tool", supply_download)
    with ThreadPoolExecutor(max_workers=2) as pool:
        caches = tuple(
            pool.map(
                lambda worktree: native_supply.materialize_tool(
                    worktree, "gitleaks", mise=tmp_path / "mise"
                ),
                (repo, linked),
            )
        )
    supply = NativeSupply.read(repo, "gitleaks")
    cache_root = (
        tmp_path / "explicit-cache"
        if cache_selector is not None
        else Path(git_common_dir(repo)) / "ethos/tool-cache/ci-tools"
    )
    expected = cache_root / "gitleaks" / "8.30.1" / supply.platform
    assert caches == (expected, expected)
    assert len(calls) == 1
    assert (expected / "gitleaks").read_bytes() == GITLEAKS_BODY
    assert supply.executable_bytes(expected / package.name) == GITLEAKS_BODY
    assert not (repo / "build/runtime/tool-cache/ci-tools").exists()
    assert not (linked / "build/runtime/tool-cache/ci-tools").exists()
    if cache_selector is not None:
        assert not (Path(git_common_dir(repo)) / "ethos/tool-cache/ci-tools").exists()


@pytest.fixture
def linked_node_supply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path, bytes]:
    """Declare one exact archive shared by two independent Git worktrees."""
    for name in ("ETHOS_CI_TOOL_CACHE_DIR", "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR"):
        monkeypatch.delenv(name, raising=False)
    repo = init_git_repo(tmp_path / "repo")
    version = "26.10.0"
    arch = "arm64" if process_machine() in {"arm64", "aarch64"} else "x64"
    family = "macos" if platform.system() == "Darwin" else "linux"
    upstream = "darwin" if family == "macos" else family
    prefix = f"node-v{version}-{upstream}-{arch}"
    package = tmp_path / f"{prefix}.tar.gz"
    body = f"#!/bin/sh\nprintf 'v{version}\\n'\n".encode()
    members = {
        "bin/node": (body, 0o755),
        "lib/node_modules/npm/bin/npm-cli.js": (b"// bundled npm\n", 0o644),
        "LICENSE": (b"Node license\n", 0o644),
        "include/unused.h": (b"unused SDK\n", 0o644),
    }
    with tarfile.open(package, "w:gz") as archive:
        for path, (content, mode) in members.items():
            member = tarfile.TarInfo(f"{prefix}/{path}")
            member.size, member.mode = len(content), mode
            archive.addfile(member, io.BytesIO(content))
    checksum = hashlib.sha256(package.read_bytes()).hexdigest()
    config = repo / ".config/mise"
    config.mkdir(parents=True)
    (config / "config.toml").write_text(f'[tools]\nnode = "{version}"\n')
    (config / "mise.lock").write_text(
        f'lockfile_version = 3\n[[tools.node]]\nversion = "{version}"\n'
        f'[tools.node."platforms.{family}-{arch}"]\n'
        f'checksum = "sha256:{checksum}"\n'
        f'url = "https://nodejs.org/dist/v{version}/{package.name}"\n'
    )
    commit_fixture(repo, "lock native Node supply")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
    return repo, linked, package, body


@pytest.mark.skipif(platform.system() not in {"Darwin", "Linux"}, reason="native supply target")
def test_linked_worktrees_prepare_one_complete_node_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    linked_node_supply: tuple[Path, Path, Path, bytes],
) -> None:
    """One verified cache serves both roots and refuses drift before execution."""
    repo, linked, package, body = linked_node_supply
    calls: list[tuple[str, ...]] = []

    def download(command: tuple[str, ...], *, root: Path, **_options: object) -> None:
        calls.append(command)
        target = root / "data/downloads" / package.name
        target.parent.mkdir(parents=True)
        shutil.copyfile(package, target)

    monkeypatch.setattr(native_supply, "download_tool", download)
    with ThreadPoolExecutor(max_workers=2) as pool:
        paths = tuple(
            pool.map(
                lambda root: native_supply.materialize_tool(root, "node", mise=tmp_path / "mise"),
                (repo, linked),
            )
        )
    supply = NodeSupply.read(repo)
    runtime = supply.cache(repo) / "runtime"
    assert paths == (runtime / "bin", runtime / "bin")
    assert len(calls) == 1
    assert (runtime / "bin/node").read_bytes() == body
    assert (runtime / "lib/node_modules/npm/bin/npm-cli.js").is_file()
    assert not (runtime / "include").exists()
    assert supply.installed_root(repo) == runtime
    assert not list(supply.cache(repo).glob(".prepare-*"))
    monkeypatch.setenv("ETHOS_CI_SUPPLY_MANIFEST", str(tmp_path / "immutable-inputs"))
    assert native_supply.materialize_tool(repo, "node") == runtime / "bin"
    assert len(calls) == 1
    npm = runtime / "lib/node_modules/npm/bin/npm-cli.js"
    npm.write_bytes(b"untrusted npm bytes\n")
    monkeypatch.setattr(
        native_supply,
        "run_command",
        lambda *_args, **_kwargs: pytest.fail("unverified runtime executed"),
    )
    with pytest.raises(ValueError, match="native_node_cached_runtime_invalid"):
        native_supply.materialize_tool(repo, "node")
    assert npm.read_bytes() == b"untrusted npm bytes\n"
    assert not list(supply.cache(repo).glob(".prepare-*"))


@pytest.mark.skipif(platform.system() not in {"Darwin", "Linux"}, reason="native supply target")
@pytest.mark.parametrize("trusted", [False, True])
def test_provisioning_carries_only_native_trust_to_its_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, trusted: bool
) -> None:
    """A safe-mode copy's lock counts only when trusted, so the root's own trust goes along."""
    state, absent = tmp_path / "host-state", tmp_path / "host-config"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("MISE_GLOBAL_CONFIG_FILE", str(absent / "config.toml"))
    monkeypatch.setenv("MISE_SYSTEM_CONFIG_DIR", str(absent))
    monkeypatch.setenv("ETHOS_CI_TOOL_CACHE_DIR", str(tmp_path / "cache"))
    for name in ("MISE_STATE_DIR", "MISE_TRUSTED_CONFIG_PATHS", "MISE_PARANOID"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("ETHOS_CI_SUPPLY_MANIFEST", raising=False)
    repo, package = tmp_path / "repo", tmp_path / "fixture.tar.gz"
    _locked_gitleaks(repo, package)
    mise = mise_executable()
    if trusted:
        run_command(repo, (str(mise), "trust"), timeout=30, check=True)
    else:
        outside_ci(monkeypatch, repo)
    carried: list[Mapping[str, str]] = []

    def download(_command: tuple[str, ...], *, root: Path, **options: object) -> None:
        trust = options.get("trust") or {}
        assert isinstance(trust, dict)
        carried.append({name: value.replace(str(root), "<copy>") for name, value in trust.items()})
        (root / "data/downloads").mkdir(parents=True)
        shutil.copyfile(package, root / "data/downloads" / package.name)

    monkeypatch.setattr(native_supply, "download_tool", download)
    native_supply.materialize_tool(repo, "gitleaks", mise=mise)
    assert carried == [{"MISE_TRUSTED_CONFIG_PATHS": f"<copy>/{MISE_CONFIG}"} if trusted else {}]
