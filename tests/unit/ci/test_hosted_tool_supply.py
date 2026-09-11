"""Hosted budget tools come from verified supply, not ambient executables."""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[3]


def _budget_supply(
    tmp_path: Path, fault: str
) -> tuple[Callable[[], subprocess.CompletedProcess[str]], Path, Path, bytes]:
    """Bind a real installer to isolated supply and controllable upstream faults."""
    repo = tmp_path / "repo"
    scripts = repo / "tools/ci/scripts"
    scripts.mkdir(parents=True)
    installer = ROOT / "tools/ci/scripts/install-scc.sh"
    assert installer.is_file(), "hosted source-budget has no executable supply owner"
    for name in (installer.name, "download-file.sh"):
        shutil.copy2(ROOT / "tools/ci/scripts" / name, scripts / name)
    bins = tmp_path / "bin"
    bins.mkdir()
    (bins / "python").symlink_to(sys.executable)
    (bins / "git").write_text(f"#!/bin/sh\nprintf '%s\\n' '{repo}'\n")
    (bins / "uname").write_text(
        '#!/bin/sh\nif [ "$1" = -s ]; then echo '
        + ("unsupported" if fault == "platform" else "Linux")
        + "; else echo aarch64; fi\n"
    )
    package = tmp_path / "upstream.tar.gz"
    body = f"#!/bin/sh\necho 'scc version {'0.0.0' if fault == 'version' else '4.1.0'}'\n".encode()
    with tarfile.open(package, "w:gz") as archive:
        entry = tarfile.TarInfo("other" if fault == "missing" else "scc")
        entry.size, entry.mode = len(body), 0o755
        archive.addfile(entry, io.BytesIO(body))
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    policy = repo / ".config/checks/format/selection.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        '[budget_tool_supply]\nversion = "4.1.0"\n'
        "[budget_tool_supply.archive_sha256]\n"
        f'Linux_arm64 = "{"0" * 64 if fault == "digest" else digest}"\n'
    )
    transfer_log = tmp_path / "transfer.log"
    (bins / "curl").write_text(
        f"#!{sys.executable}\nimport pathlib, shutil, sys\n"
        f"pathlib.Path({str(transfer_log)!r}).write_text('download')\n"
        + (
            "print('transport-down',file=sys.stderr); sys.exit(22)\n"
            if fault == "transport"
            else f"shutil.copyfile({str(package)!r},sys.argv[sys.argv.index('--output')+1])\n"
        )
    )
    for path in bins.iterdir():
        if not path.is_symlink():
            path.chmod(0o755)
    cache = repo / "build/runtime/tool-cache/ci-tools/scc/4.1.0/Linux_arm64"
    cache.mkdir(parents=True)
    executable = cache / "scc"
    executable.write_text("retained-but-untrusted")
    env = os.environ | {
        "PATH": f"{bins}{os.pathsep}{os.environ['PATH']}",
        "ETHOS_RUNTIME_BOOTSTRAPPED": "1",
        "ETHOS_CI_TOOL_CACHE_DIR": str(repo / "build/runtime/tool-cache/ci-tools"),
        "ETHOS_CI_DOWNLOAD_ATTEMPTS": "1",
    }

    def invoke() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(scripts / installer.name)],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )

    return invoke, executable, package, body


@pytest.mark.parametrize("fault", ["digest", "version", "missing", "transport", "platform"])
def test_budget_tool_supply_rejects_invalid_supply_without_replacement(tmp_path, fault):
    """A failed supply check preserves the old executable and removes preparation."""
    invoke, executable, _package, _body = _budget_supply(tmp_path, fault)

    result = invoke()

    assert result.returncode != 0
    assert result.stderr
    assert executable.read_text() == "retained-but-untrusted"
    assert not list(executable.parent.glob(".prepare-*"))


def test_budget_tool_supply_reuses_verified_identity_and_repairs_damage(tmp_path):
    """Warm reuse preserves identity, not permission to skip fresh supply validation."""
    invoke, executable, package, body = _budget_supply(tmp_path, "none")
    cache, transfer_log = executable.parent, tmp_path / "transfer.log"
    result = invoke()
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == cache
    assert executable.read_bytes() == body
    transfer_log.unlink()
    executable.write_text("tampered")
    repeated = invoke()
    assert repeated.returncode == 0, repeated.stderr
    assert executable.read_bytes() == body
    assert not transfer_log.exists(), "verified cached archive needs no download"
    identity = executable.stat()
    reused = invoke()
    assert reused.returncode == 0, reused.stderr
    after = executable.stat()
    assert (after.st_ino, after.st_mtime_ns) == (identity.st_ino, identity.st_mtime_ns), (
        "verified unchanged supply must not create another executable identity"
    )
    assert not transfer_log.exists()
    archive_digest = hashlib.sha256(package.read_bytes()).hexdigest()
    for damaged in ("mode", "symlink"):
        if damaged == "mode":
            executable.chmod(0o444)
        else:
            executable.unlink()
            executable.symlink_to(package)
        repaired = invoke()
        assert repaired.returncode == 0, repaired.stderr
        assert not executable.is_symlink()
        assert os.access(executable, os.X_OK)
        assert executable.read_bytes() == body
        assert hashlib.sha256(package.read_bytes()).hexdigest() == archive_digest
    (cache / "scc_Linux_arm64.tar.gz").write_bytes(b"corrupt cached archive")
    rejected = invoke()
    assert rejected.returncode != 0
    assert "scc_archive_checksum_mismatch" in rejected.stderr
    assert executable.read_bytes() == body, "warm reuse cannot bypass archive validation"
    assert not list(cache.glob(".prepare-*")), "preparation owns and removes temporary output"
