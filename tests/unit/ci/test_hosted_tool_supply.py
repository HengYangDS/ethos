"""Native verification tools use digest-bound, non-privileged, bounded supply."""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import shlex
import shutil
import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock
from unittest.mock import call

import pytest
from filelock import FileLock
from filelock import Timeout

import tools.ci.toolchain.native as native
from ethos.adapters.process import run_command
from tests.support.architecture import isolated_path
from tests.support.architecture import write_reference_source
from tests.support.subprocesses import ready_descendant
from tools.ci.toolchain.native import NativeSupply

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def isolated_supply_cache(monkeypatch):
    """Native fixtures never inherit either runner cache root."""
    monkeypatch.delenv("ETHOS_CI_TOOL_CACHE_DIR", raising=False)
    monkeypatch.delenv("ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR", raising=False)
    monkeypatch.setattr("ethos.adapters.repo.git.git_common_dir", lambda _root: "")


def _native_supply(
    tmp_path: Path, tool: str, fault: str = "none", *, persistent: bool = False
) -> tuple[Callable[..., subprocess.CompletedProcess[str]], Path, Path, bytes]:
    """Run the real materializer with only the external download boundary controlled."""
    repo = tmp_path / "repo"
    scripts = dict.fromkeys(
        (tool, "curl", "apt-get", "sudo", "install"),
        "#!/bin/sh\necho forbidden-ambient-or-system >&2\nexit 99\n",
    )
    system = platform.system()
    arch = "arm64" if platform.machine() in {"arm64", "aarch64"} else "x86_64"
    version = {"scc": "4.1.0", "gitleaks": "8.30.1", "syft": "1.52.0"}[tool]
    outputs = {"scc": f"scc version {version}", "syft": json.dumps({"version": version})}
    expected = outputs.get(tool, version)
    body = f"#!/bin/sh\nprintf '%s\\n' '{'wrong' if fault == 'version' else expected}'\n".encode()
    if fault == "timeout":
        body = b"#!/bin/sh\nexec sleep 15\n"
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
    owner = {"scc": "boyter", "gitleaks": "gitleaks", "syft": "anchore"}[tool]
    backend = f"github:{owner}/{tool}"
    target = f"{'macos' if system == 'Darwin' else 'linux'}-{'x64' if arch == 'x86_64' else arch}"
    (repo / ".config/mise").mkdir(parents=True, exist_ok=True)
    (repo / ".config/mise/config.toml").write_text(f'[tools]\n"{backend}" = "{version}"\n')
    checksum = "0" * 64 if fault == "digest" else digest
    (repo / ".config/mise/mise.lock").write_text(
        f'lockfile_version = 2\n[[tools."{backend}"]]\nversion = "{version}"\n'
        f'[tools."{backend}"."platforms.{target}"]\nchecksum = "sha256:{checksum}"\n'
        f'url = "https://github.com/fixture/{tool}/releases/download/v{version}/fixture.tar.gz"\n'
    )
    transfer_log = tmp_path / "transfer.log"
    scripts["mise"] = (
        f"#!{sys.executable}\nimport os, pathlib, shutil, sys\n"
        f'assert sys.argv[1:] == ["install", "--locked", {backend!r}]\n'
        'assert os.environ["MISE_SAFE"] == os.environ["MISE_LOCKED"] == "1"\n'
        'assert os.environ["MISE_DISABLE_UPDATE_WARNING"] == "1"\n'
        'assert os.environ["MISE_ALWAYS_KEEP_DOWNLOAD"] == "1"\n'
        'assert all((pathlib.Path(".config/mise")/p).is_file() '
        'for p in ("config.toml", "mise.lock"))\n'
        f"with pathlib.Path({str(transfer_log)!r}).open('a') as f: f.write('download\\n')\n"
        + (
            "print('transport-down',file=sys.stderr); sys.exit(22)\n"
            if fault == "transport"
            else (
                'target = pathlib.Path(os.environ["MISE_DATA_DIR"])/"downloads"/"fixture.tar.gz"\n'
                "target.parent.mkdir(parents=True)\n"
                f"shutil.copyfile({str(package)!r}, target)\n"
            )
        )
    )
    home = tmp_path / "supply" if persistent else repo / "build/runtime/tool-cache/ci-tools"
    cache = home / tool / version / f"{system}_{arch}"
    cache.mkdir(parents=True)
    executable = cache / tool
    executable.write_text("retained-but-untrusted")
    if fault == "cache-link":
        retained = tmp_path / "retained"
        cache.rename(retained)
        cache.symlink_to(retained, target_is_directory=True)
    env = isolated_path(tmp_path, scripts)
    env["ETHOS_CI_TOOL_CACHE_DIR"] = "build/runtime/tool-cache/ci-tools"
    env["ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR"] = str(home) if persistent else ""

    command = (sys.executable, "-B", str(ROOT / "tools/ci/toolchain/native.py"))

    def invoke(root: Path = repo) -> subprocess.CompletedProcess[str]:
        return run_command(root, (*command, "--root", str(root), tool), env=env, timeout=25)

    return invoke, executable, package, body


@pytest.mark.parametrize("tool", ["scc", "gitleaks", "syft"])
@pytest.mark.parametrize(
    "fault",
    ["digest", "version", "timeout", "missing", "link", "duplicate", "transport", "cache-link"],
)
def test_native_tool_supply_rejects_invalid_supply_without_replacement(tmp_path, tool, fault):
    """Invalid external bytes preserve the old executable and remove owned scratch."""
    invoke, executable, package, _body = _native_supply(tmp_path, tool, fault)

    assert (result := invoke()).returncode != 0
    assert result.stderr
    if fault == "transport":
        assert "transport-down" in result.stderr
    if fault == "cache-link":
        assert "cache_path_unsafe" in result.stderr
        assert executable.parent.is_symlink()
        assert not (tmp_path / "transfer.log").exists()
    assert executable.read_text() == "retained-but-untrusted"
    assert not list(executable.parent.glob(".prepare-*"))
    assert [p.read_bytes() for p in executable.parent.glob("*.tar.gz")] == (
        [package.read_bytes()] if fault in {"version", "timeout"} else []
    )
    if fault == "version":
        assert invoke().returncode != 0
        assert (tmp_path / "transfer.log").read_text() == "download\n"


@pytest.mark.parametrize("tool", ["scc", "gitleaks", "syft"])
@pytest.mark.parametrize("persistent", [False, True])
def test_native_supply_converges_concurrently_reuses_identity_and_repairs_damage(
    tmp_path, tool, persistent
):
    """A poisoned ambient PATH cannot replace declared supply or require global install."""
    invoke, executable, package, body = _native_supply(tmp_path, tool, persistent=persistent)
    transfer = tmp_path / "transfer.log"
    current_root = tmp_path / "repo"
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = tuple(pool.map(lambda _: invoke(), range(3)))
    for result in results:
        assert result.returncode == 0, result.stderr
        assert Path(result.stdout.strip()) == executable.parent
    identity = executable.stat()
    assert invoke().returncode == 0
    current = executable.stat()
    assert (current.st_ino, current.st_mtime_ns) == (identity.st_ino, identity.st_mtime_ns)
    assert executable.read_bytes() == body
    assert transfer.read_text() == "download\n"
    if persistent:
        relocated = tmp_path / "fresh-checkout"
        shutil.copytree(tmp_path / "repo", relocated)
        shutil.rmtree(tmp_path / "repo")
        assert invoke(relocated).returncode == 0
        assert transfer.read_text() == "download\n"
        current_root = relocated
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
        repaired = invoke(current_root)
        assert repaired.returncode == 0, repaired.stderr
        assert not executable.is_symlink()
        assert os.access(executable, os.X_OK)
        assert executable.read_bytes() == body
        assert hashlib.sha256(package.read_bytes()).hexdigest() == archive_digest
    (archive,) = executable.parent.glob("*.tar.gz")
    archive.write_bytes(b"corrupt cached archive")
    rejected = invoke(current_root)
    assert rejected.returncode != 0
    assert "archive_checksum_mismatch" in rejected.stderr
    assert executable.read_bytes() == body
    assert not list(executable.parent.glob(".prepare-*"))


@pytest.mark.parametrize(("system", "machine"), [("Windows", "AMD64"), ("Linux", "unknown")])
def test_native_supply_rejects_unsupported_targets_before_creating_cache(
    tmp_path, monkeypatch, system, machine
):
    """Unsupported targets cannot inherit another platform's executable identity."""
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(platform, "machine", lambda: machine)
    with pytest.raises(ValueError, match="native_tool_platform_unsupported"):
        native.prepare(tmp_path, "gitleaks")
    assert not (tmp_path / "build").exists()


def test_native_supply_lock_timeout_preserves_bytes_and_scratch(tmp_path):
    """A contending caller has a bounded wait, not permission to bypass the writer."""
    _invoke, executable, _package, _body = _native_supply(tmp_path, "scc")
    with FileLock(executable.parent / ".prepare.lock"), pytest.raises(Timeout):
        native.prepare(tmp_path / "repo", "scc", lock_timeout=0.01)
    assert executable.read_text() == "retained-but-untrusted"
    assert not list(executable.parent.glob(".prepare-*"))
    assert not (tmp_path / "transfer.log").exists()


def _bootstrap_source(root: Path, script: str, version: str = "2026.9.11") -> Path:
    """Materialize one locked native input; each caller owns its mutable fixture."""
    write_reference_source(root, ".config/mise/config.toml", f'min_version = "{version}"')
    write_reference_source(root, ".config/mise/mise.lock", "lockfile_version = 2")
    installer = root / "tools/ci/scripts/mise-install.sh"
    write_reference_source(root, "tools/ci/scripts/mise-install.sh", script)
    write_reference_source(
        root,
        ".config/checks/ci/templates.toml",
        f'[bootstrap]\nversion = "{version}"\n'
        f'sha256 = "{hashlib.sha256(installer.read_bytes()).hexdigest()}"\n',
    )
    return installer


def test_mise_version_observation_disables_nonsemantic_update_notices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A newer upstream release must not make a pinned tool appear invalid."""
    _bootstrap_source(tmp_path, "exit 99\n")
    executable = tmp_path / "mise"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        'print("2026.9.11 linux-arm64")\n'
        'if os.environ.get("MISE_DISABLE_UPDATE_WARNING") != "1":\n'
        '    print("mise WARN newer version available", file=sys.stderr)\n'
    )
    executable.chmod(0o755)
    monkeypatch.delenv("MISE_DISABLE_UPDATE_WARNING", raising=False)
    monkeypatch.setattr(native.shutil, "which", lambda _name: str(executable))

    assert native.prepare_mise(tmp_path) == executable


def test_manifest_bound_mise_supply_does_not_download_on_a_cold_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hosted immutable image must contain mise before the job starts."""
    _bootstrap_source(tmp_path, "exit 99\n")
    monkeypatch.setenv("ETHOS_CI_SUPPLY_MANIFEST", "/opt/ethos-supply/input.sha256")
    monkeypatch.setattr(native.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        native,
        "run_command",
        lambda *_args, **_kwargs: pytest.fail("hosted job attempted a network bootstrap"),
    )

    with pytest.raises(ValueError, match="native_tool_offline_cache_missing:mise"):
        native.prepare_mise(tmp_path)


def test_manifest_bound_native_tool_supply_does_not_download_on_a_cold_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hosted job must not repair an incomplete image over the network."""
    _invoke, executable, _archive, _body = _native_supply(tmp_path, "scc")
    monkeypatch.setenv("ETHOS_CI_SUPPLY_MANIFEST", "/opt/ethos-supply/input.sha256")
    monkeypatch.setattr(
        native,
        "download",
        lambda *_args, **_kwargs: pytest.fail("hosted job attempted a network download"),
    )

    with pytest.raises(ValueError, match="native_tool_offline_cache_missing:scc"):
        native.prepare(tmp_path / "repo", "scc")
    assert executable.read_text() == "retained-but-untrusted"
    assert not list(executable.parent.glob(".prepare-*"))


@pytest.mark.parametrize("startup_delay", [0, 0.75])
@pytest.mark.parametrize("boundary", ["download", "verify", "bootstrap"])
def test_native_supply_timeout_drains_descendants_before_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, startup_delay: float, boundary: str
) -> None:
    """Supply failure reports retain each native stream after draining owned children."""
    late = tmp_path / "late"

    def after_ready(_process, options):
        options["timeout"] = 0.5

    with ready_descendant(monkeypatch, after_ready) as (handshake, closed):
        child = handshake + f"; from pathlib import Path; Path({str(late)!r}).write_text('escaped')"
        executable = tmp_path / "tool"
        executable.write_text(
            f"#!{sys.executable}\nimport subprocess, sys, time\n"
            f"time.sleep({startup_delay})\n"
            "print('partial-native-output', flush=True)\n"
            "print('partial-native-error', file=sys.stderr, flush=True)\n"
            f"subprocess.Popen([sys.executable, '-c', {child!r}], "
            "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()\n"
        )
        executable.chmod(0o755)

        def execute():
            if boundary == "download":
                return native.download((str(executable),), root=tmp_path, timeout=0.5)
            if boundary == "verify":
                return NativeSupply.read(ROOT, "scc").verify(executable)
            _bootstrap_source(tmp_path, f"exec {shlex.quote(str(executable))}\n")
            monkeypatch.setattr(native.shutil, "which", lambda _name: None)
            return native.prepare_mise(tmp_path)

        monkeypatch.setattr(sys, "argv", ["native", "--root", str(tmp_path), "scc"])
        monkeypatch.setattr(native, "prepare", lambda *_args, **_kwargs: execute())
        assert native.main() == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "native_tool_supply_failed" in captured.err
        assert "partial-native-output" in captured.err
        assert "partial-native-error" in captured.err
        assert closed()
    assert not late.exists()
    assert not list(tmp_path.rglob(".bootstrap-*"))


@pytest.mark.parametrize("source", ["bootstrap", "operator", "cache", "persistent-cache"])
@pytest.mark.parametrize(
    "fault", ["none", "failure", "wrong-version", "warning", "drift", "older", "newer", "preview"]
)
def test_mise_bootstrap_is_bounded_and_preserves_existing_supply(
    tmp_path, monkeypatch, source, fault
):
    """Operator supply meets the minimum; owned bootstrap retains its exact identity."""
    version = "2026.9.11"
    observed = {
        "wrong-version": "wrong",
        "older": "2026.9.10",
        "newer": "2026.10.1",
        "preview": "2026.10.1-dev",
    }.get(fault, version)
    body = f"#!/bin/sh\necho {observed}\n"
    if fault == "warning":
        body += "echo unapproved-warning >&2\n"
    installer = _bootstrap_source(
        tmp_path,
        'mkdir -p "$(dirname "$MISE_INSTALL_PATH")"\n'
        f'printf %s {shlex.quote(body)} >"$MISE_INSTALL_PATH"\n'
        'chmod +x "$MISE_INSTALL_PATH"\n'
        + ("echo bootstrap-failed >&2; exit 23\n" if fault == "failure" else ""),
    )
    if fault == "drift":
        installer.write_text("echo FORBIDDEN >UNAPPROVED\nexit 0\n")
    home = tmp_path / "build/runtime/tool-cache/ci-tools"
    if source == "persistent-cache":
        home, source = tmp_path / "supply", "cache"
        monkeypatch.setenv("ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR", str(home))
    target = home / "mise" / version / f"{platform.system()}_{platform.machine()}" / "bin/mise"
    target.parent.mkdir(parents=True)
    target.write_text("retained" if source == "bootstrap" else body)
    target.chmod(0o600 if source == "bootstrap" else 0o700)
    monkeypatch.setattr(
        native.shutil, "which", lambda _name: str(target) if source == "operator" else None
    )
    before = target.read_bytes()
    accepted = (
        fault == "none"
        or (source == "operator" and fault in {"newer", "failure", "drift"})
        or (source == "cache" and fault == "failure")
    )
    prepared = Mock(return_value=target.parent)
    monkeypatch.setattr(native, "prepare", prepared)
    monkeypatch.setattr(sys, "argv", ["native", "--root", str(tmp_path), "--mise", "scc"])
    assert native.main() == (0 if accepted else 1)
    expected = [call(tmp_path, "scc", mise=target)] if accepted else []
    assert prepared.call_args_list == expected
    assert target.read_bytes() == (body.encode() if accepted else before)
    assert not list(target.parent.glob(".bootstrap-*"))

    assert not (tmp_path / "UNAPPROVED").exists()
