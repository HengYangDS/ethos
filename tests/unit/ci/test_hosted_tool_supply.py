"""Native verification tools use digest-bound, non-privileged, bounded supply."""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from filelock import Timeout

import tools.ci.toolchain.environment as ci_environment
import tools.ci.toolchain.native as native
from ethos.adapters.process import run_command
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tools.ci.toolchain.native import NativeSupply
from tools.ci.toolchain.native import download
from tools.ci.toolchain.native import prepare
from tools.ci.toolchain.native import prepare_mise

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("case", ["valid", "inside", "unprotected", "missing"])
def test_ci_trust_projects_only_operator_supplied_protected_anchor(tmp_path, case):
    repo = init_git_repo(tmp_path / "repo")
    trust = (repo if case == "inside" else tmp_path) / "trust"
    trust.mkdir(mode=0o700)
    anchor = trust / "allowed-signers"
    anchor.write_text("operator-controlled public trust\n")
    anchor.chmod(0o666 if case == "unprotected" else 0o600)
    if case == "missing":
        anchor.unlink()
    before = git(repo, "config", "--local", "--list")
    if case != "valid":
        with pytest.raises(ValueError, match="git_object_trust_anchor_"):
            ci_environment.bind_commit_trust(repo, anchor)
        assert git(repo, "config", "--local", "--list") == before
    else:
        ci_environment.bind_commit_trust(repo, anchor)
        assert git(repo, "config", "--local", "--get", "gpg.ssh.allowedSignersFile") == str(anchor)
        first = (repo / ".git/config").read_bytes()
        ci_environment.bind_commit_trust(repo, anchor)
        assert (repo / ".git/config").read_bytes() == first
        assert anchor.read_text() == "operator-controlled public trust\n"


@pytest.fixture(scope="module")
def bootstrap_tools(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Reuse immutable executables while each native bootstrap owns its case state."""
    tools = tmp_path_factory.mktemp("bootstrap-tools")
    bodies = {
        "with-python-runtime": '[ "$1" != -- ] || shift\nexec "$@"\n',
        "uname": 'printf "%s\\n" "$FIXTURE_SYSTEM"\n',
        "uv": (
            'printf "%s\\n" "$*" >>../uv.log\n'
            'case "$*" in\n'
            '  --version) printf "uv 0.12.10\\n" ;;\n'
            '  run*) cat >/dev/null; printf "0.12.10\\n" ;;\n'
            '  "python install --no-bin 3.14.7") : >../native-image ;;\n'
            '  "sync --locked --group dev") ;;\n'
            "  *) exit 2 ;;\nesac\n"
        ),
        "npx": "exit 0\n",
        "apt-get": 'printf "%s\\n" "$*" >>../apt-get.log\n',
        "ssh-keygen": "exit 0\n",
        "ldconfig": "printf 'libatomic.so.1\\n'\n",
        "openspec": "printf '1.12.0\\n'\n",
        "python": (
            f'[ "$1 $2" != "-B -" ] || exec {shlex.quote(sys.executable)} "$@"\n'
            'case "$*" in\n'
            "  *toolchain/native.py*) printf 'mise-prepared\\n' >>../mise.log; "
            "printf '/fixture/mise/bin\\n' ;;\n"
            "  *platform.python_version*) printf '3.14.7\\n' ;;\n"
            "  '-B -I -') cat >/dev/null\n"
            '    [ "$FIXTURE_IMAGE_STATE" = available ] || [ -f ../native-image ] ;;\n'
            "  *) exit 2 ;;\nesac\n"
        ),
    }
    for name, body in bodies.items():
        path = tools / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o555)
    return tools


@pytest.mark.parametrize("anchor_state", ["absent", "declared"])
@pytest.mark.parametrize(
    ("system", "image_state"),
    [("Linux", "available"), ("Darwin", "missing"), ("Darwin", "available")],
)
def test_python_bootstrap_supplies_platform_prerequisites(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    anchor_state: str,
    system: str,
    image_state: str,
    bootstrap_tools: Path,
) -> None:
    monkeypatch.setenv("ETHOS_COMMIT_TRUST_ANCHOR", str(tmp_path / "ambient-unknown-anchor"))
    repo = init_git_repo(tmp_path / "repo")
    script_dir = repo / "tools/ci/scripts"
    script_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "tools/ci/scripts/bootstrap-python.sh", script_dir)
    (script_dir / "with-python-runtime.sh").symlink_to(bootstrap_tools / "with-python-runtime")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for source in bootstrap_tools.iterdir():
        if source.name not in {"ssh-keygen", "ldconfig"} or system == "Linux":
            (fake_bin / source.name).symlink_to(source)
            assert (fake_bin / source.name).samefile(source)
            assert not source.stat().st_mode & 0o222
    for name in ("awk", "cat", "dirname", "grep", "git"):
        executable = shutil.which(name)
        assert executable is not None, name
        (fake_bin / name).symlink_to(executable)
    openspec = repo / "node_modules/.bin/openspec"
    openspec.parent.mkdir(parents=True)
    openspec.symlink_to(bootstrap_tools / "openspec")
    (repo / ".venv/bin").mkdir(parents=True)
    (repo / ".venv/bin/python").symlink_to(bootstrap_tools / "python")
    (repo / "pyproject.toml").write_text(
        '[dependency-groups]\ndev = ["uv>=0.12.10"]\n', encoding="utf-8"
    )
    environment = {
        "PATH": str(fake_bin),
        "FIXTURE_SYSTEM": system,
        "FIXTURE_IMAGE_STATE": image_state,
        "PYTHONPATH": str(ROOT),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    anchor = tmp_path / "trust/allowed-signers"
    anchor.parent.mkdir(mode=0o700)
    anchor.write_text("fixture-controlled public trust\n")
    anchor.chmod(0o600)
    if anchor_state == "declared":
        environment["ETHOS_COMMIT_TRUST_ANCHOR"] = str(anchor)

    result = run_command(
        repo,
        ("/bin/bash", str(script_dir / "bootstrap-python.sh")),
        env=environment,
        inherit_environment=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    settings = git(repo, "config", "--local", "--list")
    assert (f"gpg.ssh.allowedsignersfile={anchor}" in settings) == (anchor_state == "declared")
    assert "ambient-unknown-anchor" not in settings
    assert anchor.read_text() == "fixture-controlled public trust\n"
    apt_log, uv_log = tmp_path / "apt-get.log", tmp_path / "uv.log"
    observed_apt = apt_log.read_text().splitlines() if apt_log.exists() else None
    assert observed_apt == (
        ["update", "install -y --no-install-recommends procps lsof util-linux"]
        if system == "Linux"
        else None
    )
    assert (tmp_path / "mise.log").read_text() == "mise-prepared\n"
    observed_uv = uv_log.read_text(encoding="utf-8").splitlines()
    if image_state == "missing":
        assert observed_uv.index("sync --locked --group dev") < observed_uv.index(
            "python install --no-bin 3.14.7"
        )
        assert (tmp_path / "native-image").is_file()
    else:
        assert not any(command.startswith("python install ") for command in observed_uv)


def _native_supply(
    tmp_path: Path, tool: str, fault: str = "none"
) -> tuple[Callable[[], subprocess.CompletedProcess[str]], Path, Path, bytes]:
    """Run the real materializer with only the external download boundary controlled."""
    repo = tmp_path / "repo"
    repo.mkdir()
    bins = tmp_path / "bin"
    bins.mkdir()
    system = platform.system()
    arch = "arm64" if platform.machine() in {"arm64", "aarch64"} else "x86_64"
    version = {"scc": "4.1.0", "gitleaks": "8.30.1", "syft": "1.52.0"}[tool]
    expected = f"scc version {version}" if tool == "scc" else version
    if tool == "syft":
        expected = json.dumps({"version": version})
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
    backend = (
        f"github:{ {'scc': 'boyter', 'gitleaks': 'gitleaks', 'syft': 'anchore'}[tool] }/{tool}"
    )
    target = f"{'macos' if system == 'Darwin' else 'linux'}-{'x64' if arch == 'x86_64' else arch}"
    (repo / "mise.toml").write_text(f'[tools]\n"{backend}" = "{version}"\n')
    checksum = "0" * 64 if fault == "digest" else digest
    (repo / "mise.lock").write_text(
        f'lockfile_version = 2\n[[tools."{backend}"]]\nversion = "{version}"\n'
        f'[tools."{backend}"."platforms.{target}"]\nchecksum = "sha256:{checksum}"\n'
        f'url = "https://github.com/fixture/{tool}/releases/download/v{version}/fixture.tar.gz"\n'
    )
    transfer_log = tmp_path / "transfer.log"
    (bins / "mise").write_text(
        f"#!{sys.executable}\nimport os, pathlib, shutil, sys\n"
        'assert sys.argv[1:3] == ["install", "--locked"]\n'
        f"assert sys.argv[3] == {backend!r}\n"
        'assert os.environ["MISE_SAFE"] == os.environ["MISE_LOCKED"] == "1"\n'
        'assert os.environ["MISE_ALWAYS_KEEP_DOWNLOAD"] == "1"\n'
        'assert pathlib.Path("mise.toml").is_file() and pathlib.Path("mise.lock").is_file()\n'
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
    for executable in (tool, "curl", "apt-get", "sudo", "install"):
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

    command = (sys.executable, "-B", str(ROOT / "tools/ci/toolchain/native.py"))

    def invoke() -> subprocess.CompletedProcess[str]:
        return run_command(repo, (*command, "--root", str(repo), tool), env=env, timeout=25)

    return invoke, executable, package, body


@pytest.mark.parametrize("tool", ["scc", "gitleaks", "syft"])
@pytest.mark.parametrize(
    "fault", ["digest", "version", "timeout", "missing", "link", "duplicate", "transport"]
)
def test_native_tool_supply_rejects_invalid_supply_without_replacement(tmp_path, tool, fault):
    """Invalid external bytes preserve the old executable and remove owned scratch."""
    invoke, executable, package, _body = _native_supply(tmp_path, tool, fault)

    result = invoke()

    assert result.returncode != 0
    assert result.stderr
    if fault == "transport":
        assert "transport-down" in result.stderr
    assert executable.read_text() == "retained-but-untrusted"
    assert not list(executable.parent.glob(".prepare-*"))
    assert [p.read_bytes() for p in executable.parent.glob("*.tar.gz")] == (
        [package.read_bytes()] if fault in {"version", "timeout"} else []
    )
    if fault == "version":
        assert invoke().returncode != 0
        assert (tmp_path / "transfer.log").read_text() == "download\n"


@pytest.mark.parametrize("tool", ["scc", "gitleaks", "syft"])
def test_native_supply_is_rootless_reuses_identity_and_repairs_damage(tmp_path, tool):
    """A poisoned ambient PATH cannot replace declared supply or require global install."""
    invoke, executable, package, body = _native_supply(tmp_path, tool)
    transfer = tmp_path / "transfer.log"
    identity = None
    for _ in range(2):
        result = invoke()
        assert result.returncode == 0, result.stderr
        assert Path(result.stdout.strip()) == executable.parent
        assert executable.read_bytes() == body
        current = executable.stat()
        current_identity = (current.st_ino, current.st_mtime_ns)
        assert identity is None or current_identity == identity
        identity = current_identity
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
    (archive,) = executable.parent.glob("*.tar.gz")
    archive.write_bytes(b"corrupt cached archive")
    rejected = invoke()
    assert rejected.returncode != 0
    assert "archive_checksum_mismatch" in rejected.stderr
    assert executable.read_bytes() == body
    assert not list(executable.parent.glob(".prepare-*"))


@pytest.mark.parametrize("tool", ["scc", "gitleaks", "syft"])
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


@pytest.mark.parametrize("tool", ["scc", "gitleaks", "syft"])
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


@pytest.mark.parametrize("startup_delay", [0, 0.75])
@pytest.mark.parametrize("boundary", ["download", "verify", "bootstrap"])
def test_native_supply_timeout_drains_descendants_before_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, startup_delay: float, boundary: str
) -> None:
    """Transport and executable observation own descendants until timeout cleanup."""
    late = tmp_path / "late"
    native_communicate = subprocess.Popen.communicate
    connection = None
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(10)
        child = (
            "import pathlib, socket; "
            f"s = socket.create_connection({listener.getsockname()!r}, timeout=10); "
            "s.settimeout(None); s.sendall(b'R'); s.recv(1); "
            f"pathlib.Path({str(late)!r}).write_text('escaped')"
        )
        executable = tmp_path / "tool"
        executable.write_text(
            f"#!{sys.executable}\nimport subprocess, sys, time\n"
            f"time.sleep({startup_delay})\n"
            f"subprocess.Popen([sys.executable, '-c', {child!r}], "
            "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()\n"
        )
        executable.chmod(0o755)

        def after_readiness(process, *args, **kwargs):
            nonlocal connection
            if kwargs.get("timeout") is not None and connection is None:
                connection, _ = listener.accept()
                connection.settimeout(2)
                assert connection.recv(1) == b"R"
                kwargs["timeout"] = 0.5
            return native_communicate(process, *args, **kwargs)

        monkeypatch.setattr(subprocess.Popen, "communicate", after_readiness)

        def execute():
            if boundary == "download":
                return download((str(executable),), root=tmp_path, timeout=0.5)
            if boundary == "verify":
                return NativeSupply.read(ROOT, "scc").verify(executable)
            (tmp_path / "mise.toml").write_text('min_version = "2026.9.11"\n')
            installer = tmp_path / ".config/ci/mise-install.sh"
            installer.parent.mkdir(parents=True)
            installer.write_text(f"exec {shlex.quote(str(executable))}\n")
            monkeypatch.setattr(native.shutil, "which", lambda _name: None)
            return prepare_mise(tmp_path)

        try:
            with pytest.raises(subprocess.TimeoutExpired):
                execute()
            assert connection is not None
            assert connection.recv(1) == b""
        finally:
            if connection is not None:
                connection.close()
    assert not late.exists()
    assert not list(tmp_path.rglob(".bootstrap-*"))


@pytest.mark.parametrize("fault", ["none", "failure", "wrong-version", "warning"])
def test_mise_bootstrap_is_bounded_and_preserves_existing_supply(tmp_path, monkeypatch, fault):
    """Missing native mise uses only the selected installer and preserves failed targets."""
    version = "2026.9.11"
    (tmp_path / "mise.toml").write_text(f'min_version = "{version}"\n')
    installer = tmp_path / ".config/ci/mise-install.sh"
    installer.parent.mkdir(parents=True)
    body = f"#!/bin/sh\necho {'wrong' if fault == 'wrong-version' else version}\n"
    if fault == "warning":
        body += "echo unapproved-warning >&2\n"
    installer.write_text(
        'mkdir -p "$(dirname "$MISE_INSTALL_PATH")"\n'
        f'printf %s {shlex.quote(body)} >"$MISE_INSTALL_PATH"\n'
        'chmod +x "$MISE_INSTALL_PATH"\n'
        + ("echo bootstrap-failed >&2; exit 23\n" if fault == "failure" else "")
    )
    monkeypatch.setattr(native.shutil, "which", lambda _name: None)
    target = tmp_path / "build/runtime/tool-cache/mise/bin/mise"
    target.parent.mkdir(parents=True)
    target.write_text("retained")
    if fault == "none":
        assert prepare_mise(tmp_path) == target
        assert (
            run_command(tmp_path, (str(target), "--version"), timeout=5).stdout.strip() == version
        )
    else:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            prepare_mise(tmp_path)
        assert target.read_text() == "retained"
    assert not list(target.parent.glob(".bootstrap-*"))
