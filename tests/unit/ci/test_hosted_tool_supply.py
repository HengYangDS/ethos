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

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("fault", ["none", "digest", "version", "missing", "transport", "platform"])
def test_budget_tool_supply_checks_bytes_before_replacing_executable(
    tmp_path: Path, fault: str
) -> None:
    """Invalid supply cannot replace a retained executable; valid supply repairs it."""
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
    result = subprocess.run(
        ["bash", str(scripts / installer.name)],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    if fault != "none":
        assert result.returncode != 0
        assert result.stderr
        assert executable.read_text() == "retained-but-untrusted"
    else:
        assert result.returncode == 0, result.stderr
        assert Path(result.stdout.strip()) == cache
        assert executable.read_bytes() == body
        assert (
            subprocess.check_output([str(executable), "--version"]).strip() == b"scc version 4.1.0"
        )
        transfer_log.unlink()
        executable.write_text("tampered")
        repeated = subprocess.run(
            ["bash", str(scripts / installer.name)],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        assert repeated.returncode == 0, repeated.stderr
        assert executable.read_bytes() == body
        assert not transfer_log.exists(), "verified cached archive needs no download"
    assert not list(cache.glob(".prepare-*")), "preparation owns and removes temporary output"
