"""Native verification tools use digest-bound, non-privileged, bounded supply."""

from __future__ import annotations

import hashlib
import io
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from filelock import Timeout

from tools.ci.toolchain.native import download
from tools.ci.toolchain.native import prepare

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[3]


def _native_supply(
    tmp_path: Path, tool: str, fault: str = "none"
) -> tuple[Callable[[], subprocess.CompletedProcess[str]], Path, Path, bytes]:
    """Run the real materializer with only the external download boundary controlled."""
    repo = tmp_path / "repo"
    scripts = repo / "tools/ci/scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(ROOT / "tools/ci/scripts/download-file.sh", scripts)
    bins = tmp_path / "bin"
    bins.mkdir()
    system = platform.system()
    arch = "arm64" if platform.machine() in {"arm64", "aarch64"} else "x86_64"
    version = "4.1.0" if tool == "scc" else "8.30.1"
    expected = f"scc version {version}" if tool == "scc" else version
    body = f"#!/bin/sh\nprintf '%s\\n' '{'wrong' if fault == 'version' else expected}'\n".encode()
    package = tmp_path / "upstream.tar.gz"
    with tarfile.open(package, "w:gz") as archive:
        entry = tarfile.TarInfo("other" if fault == "missing" else tool)
        entry.size, entry.mode = len(body), 0o755
        if fault == "link":
            entry.type, entry.linkname = tarfile.SYMTYPE, "/outside"
        archive.addfile(entry, io.BytesIO(body) if entry.isfile() else None)
        if fault == "duplicate":
            archive.addfile(entry, io.BytesIO(body))
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    policy = repo / (
        ".config/checks/format/selection.toml"
        if tool == "scc"
        else ".config/checks/secrets/supply.toml"
    )
    policy.parent.mkdir(parents=True)
    key = (
        f"{system}_{arch}"
        if tool == "scc"
        else f"{system.lower()}_{'x64' if arch == 'x86_64' else arch}"
    )
    policy.write_text(
        ("[budget_tool_supply]\n" if tool == "scc" else "")
        + f'version = "{version}"\nrelease_owner = "fixture/{tool}"\n'
        + ("[budget_tool_supply.archive_sha256]\n" if tool == "scc" else "[archive_sha256]\n")
        + f'{key} = "{"0" * 64 if fault == "digest" else digest}"\n'
    )
    transfer_log = tmp_path / "transfer.log"
    (bins / "curl").write_text(
        f"#!{sys.executable}\nimport pathlib, shutil, sys\n"
        f"with pathlib.Path({str(transfer_log)!r}).open('a') as f: f.write('download\\n')\n"
        + (
            "print('transport-down',file=sys.stderr); sys.exit(22)\n"
            if fault == "transport"
            else f"shutil.copyfile({str(package)!r},sys.argv[sys.argv.index('--output')+1])\n"
        )
    )
    for executable in (tool, "apt-get", "sudo", "install"):
        (bins / executable).write_text("#!/bin/sh\necho forbidden-ambient-or-system >&2\nexit 99\n")
    for path in bins.iterdir():
        path.chmod(0o755)
    cache = repo / f"build/runtime/tool-cache/ci-tools/{tool}/{version}/{system}_{arch}"
    cache.mkdir(parents=True)
    executable = cache / tool
    executable.write_text("retained-but-untrusted")
    env = os.environ | {
        "PATH": f"{bins}{os.pathsep}{os.environ['PATH']}",
        "ETHOS_CI_TOOL_CACHE_DIR": "build/runtime/tool-cache/ci-tools",
        "ETHOS_CI_DOWNLOAD_ATTEMPTS": "1",
    }

    def invoke() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/ci/toolchain/native.py"),
                "--root",
                str(repo),
                tool,
            ],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            timeout=25,
            check=False,
        )

    return invoke, executable, package, body


@pytest.mark.parametrize("tool", ["scc", "gitleaks"])
@pytest.mark.parametrize(
    "fault", ["digest", "version", "missing", "link", "duplicate", "transport"]
)
def test_native_tool_supply_rejects_invalid_supply_without_replacement(tmp_path, tool, fault):
    """Invalid external bytes preserve the old executable and remove owned scratch."""
    invoke, executable, _package, _body = _native_supply(tmp_path, tool, fault)

    result = invoke()

    assert result.returncode != 0
    assert result.stderr
    assert executable.read_text() == "retained-but-untrusted"
    assert not list(executable.parent.glob(".prepare-*"))


@pytest.mark.parametrize("tool", ["scc", "gitleaks"])
def test_native_supply_is_rootless_reuses_identity_and_repairs_damage(tmp_path, tool):
    """A poisoned ambient PATH cannot replace declared supply or require global install."""
    invoke, executable, package, body = _native_supply(tmp_path, tool)
    result = invoke()

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == executable.parent
    assert executable.read_bytes() == body
    transfer = tmp_path / "transfer.log"
    assert transfer.read_text() == "download\n"
    identity = executable.stat()
    repeated = invoke()
    assert repeated.returncode == 0, repeated.stderr
    assert (executable.stat().st_ino, executable.stat().st_mtime_ns) == (
        identity.st_ino,
        identity.st_mtime_ns,
    )
    assert transfer.read_text() == "download\n"
    archive_digest = hashlib.sha256(package.read_bytes()).hexdigest()
    for damage in ("bytes", "mode", "symlink", "absent"):
        if damage == "bytes":
            executable.write_text("tampered")
        elif damage == "mode":
            executable.chmod(0o444)
        else:
            executable.unlink()
            if damage == "symlink":
                executable.symlink_to(package)
        repaired = invoke()
        assert repaired.returncode == 0, repaired.stderr
        assert not executable.is_symlink()
        assert os.access(executable, os.X_OK)
        assert executable.read_bytes() == body
        assert hashlib.sha256(package.read_bytes()).hexdigest() == archive_digest
    archives = list(executable.parent.glob("*.tar.gz"))
    assert len(archives) == 1
    archives[0].write_bytes(b"corrupt cached archive")
    rejected = invoke()
    assert rejected.returncode != 0
    assert "archive_checksum_mismatch" in rejected.stderr
    assert executable.read_bytes() == body
    assert not list(executable.parent.glob(".prepare-*"))


@pytest.mark.parametrize("tool", ["scc", "gitleaks"])
def test_concurrent_native_supply_converges_without_extra_downloads(tmp_path, tool):
    """One identity has one cache effect despite concurrent independent callers."""
    invoke, executable, _package, body = _native_supply(tmp_path, tool)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = tuple(pool.map(lambda _: invoke(), range(3)))
    assert all(result.returncode == 0 for result in results), [r.stderr for r in results]
    assert {result.stdout.strip() for result in results} == {str(executable.parent)}
    assert executable.read_bytes() == body
    assert (tmp_path / "transfer.log").read_text() == "download\n"
    assert len(list(executable.parent.glob("*.tar.gz"))) == 1
    assert not list(executable.parent.glob(".prepare-*"))


@pytest.mark.parametrize("tool", ["scc", "gitleaks"])
def test_native_supply_rejects_a_linked_cache_without_changing_its_target(tmp_path, tool):
    """The controlled path cannot follow a symbolic cache redirect."""
    invoke, executable, _package, _body = _native_supply(tmp_path, tool)
    cache = executable.parent
    retained = tmp_path / "retained"
    cache.rename(retained)
    cache.symlink_to(retained, target_is_directory=True)

    result = invoke()

    assert result.returncode != 0
    assert "cache_path_unsafe" in result.stderr
    assert (retained / tool).read_text() == "retained-but-untrusted"
    assert not (tmp_path / "transfer.log").exists()


@pytest.mark.parametrize(("system", "machine"), [("Windows", "AMD64"), ("Linux", "unknown")])
def test_native_supply_rejects_unsupported_targets_before_creating_cache(
    tmp_path, monkeypatch, system, machine
):
    """Unsupported targets cannot inherit another platform's executable identity."""
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(platform, "machine", lambda: machine)
    with pytest.raises(ValueError, match="native_tool_platform_unsupported"):
        prepare(tmp_path, "gitleaks")
    assert not (tmp_path / "build").exists()


def test_native_supply_lock_timeout_preserves_prior_bytes_and_creates_no_scratch(tmp_path):
    """A contending caller has a bounded wait, not permission to bypass the writer."""
    _invoke, executable, _package, _body = _native_supply(tmp_path, "scc")
    with FileLock(executable.parent / ".prepare.lock"), pytest.raises(Timeout):
        prepare(tmp_path / "repo", "scc", lock_timeout=0.01)
    assert executable.read_text() == "retained-but-untrusted"
    assert not list(executable.parent.glob(".prepare-*"))
    assert not (tmp_path / "transfer.log").exists()


def test_native_supply_timeout_drains_download_descendants_before_cleanup(tmp_path):
    """Timed-out transport cannot outlive its cache lock or recreate scratch."""
    ready, late = tmp_path / "ready", tmp_path / "late"
    child = (
        "import pathlib, time; "
        f"pathlib.Path({str(ready)!r}).write_text('ready'); "
        f"time.sleep(1); pathlib.Path({str(late)!r}).write_text('escaped')"
    )
    parent = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(10)"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        download((sys.executable, "-c", parent), root=tmp_path, timeout=0.5)
    assert ready.read_text() == "ready"
    time.sleep(1.1)
    assert not late.exists()
