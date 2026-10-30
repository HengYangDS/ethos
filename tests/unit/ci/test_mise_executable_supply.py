"""Every host stages mise from the official executable whose digest the repository binds."""

from __future__ import annotations

import hashlib
import sys
import sysconfig
from pathlib import Path

import pytest

import tools.ci.toolchain.native as native
from tests.support.architecture import write_reference_source

VERSION = "2026.10.8"


@pytest.fixture(autouse=True)
def windows_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Select the Windows branch without operator supply or an immutable hosted image."""
    for name in ("ETHOS_CI_TOOL_CACHE_DIR", "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("ETHOS_CI_SUPPLY_MANIFEST", raising=False)
    monkeypatch.setattr(native, "_windows_host", lambda: True)
    monkeypatch.setattr(native.platform, "system", lambda: "Windows")
    which = native.shutil.which

    def without_operator_mise(name: str, **kwargs: object) -> str | None:
        return None if name == "mise" else which(name, **kwargs)

    monkeypatch.setattr(native.shutil, "which", without_operator_mise)
    monkeypatch.setattr(native.platform, "machine", lambda: "AMD64")


def _executable(observed: str = VERSION) -> bytes:
    return f"#!{sys.executable}\nprint({f'{observed} windows-x64'!r})\n".encode()


def _source(root: Path, *, x64: str, executables: bool = True) -> None:
    write_reference_source(root, ".config/mise/config.toml", f'min_version = "{VERSION}"')
    digests = {
        f"{system}-{arch}": "0" * 64
        for system in native.MISE_SYSTEMS.values()
        for arch in native.MISE_ARCHITECTURES.values()
    }
    digests["windows-x64"] = x64
    rows = "".join(f'{name} = "{digest}"\n' for name, digest in sorted(digests.items()))
    table = f"[bootstrap.executables]\n{rows}" if executables else ""
    write_reference_source(
        root,
        ".config/checks/ci-projection/policy.toml",
        f'[bootstrap]\nversion = "{VERSION}"\n{table}',
    )


def _serve(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> list[tuple[str, ...]]:
    requests: list[tuple[str, ...]] = []

    def download(command: tuple[str, ...], *, root: Path) -> None:
        requests.append(command)
        target = Path(command[command.index("--output") + 1])
        assert target.parent == root
        target.write_bytes(payload)
        target.chmod(0o755)

    monkeypatch.setattr(native, "download_tool", download)
    return requests


@pytest.mark.parametrize("cpu", ["AMD64", "ARM64"])
def test_mise_publishes_only_the_bound_official_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cpu: str
) -> None:
    payload = _executable()
    _source(tmp_path, x64=hashlib.sha256(payload).hexdigest())
    requests = _serve(monkeypatch, payload)
    # Windows on Arm reports its CPU; the emulated x64 interpreter still runs the x64 executable.
    monkeypatch.setattr(native.platform, "machine", lambda: cpu)
    monkeypatch.setattr(sysconfig, "get_platform", lambda: "win-amd64")

    executable = native.prepare_mise(tmp_path)

    assert executable.name == "mise.exe"
    assert executable.read_bytes() == payload
    assert [request[-1] for request in requests] == [
        f"https://github.com/jdx/mise/releases/download/v{VERSION}/mise-v{VERSION}-windows-x64.exe"
    ]
    assert native.prepare_mise(tmp_path) == executable
    assert len(requests) == 1
    assert not list(executable.parent.glob(".bootstrap-*"))


@pytest.mark.parametrize(
    ("fault", "gap"),
    [
        ("digest", "mise_executable_digest_mismatch"),
        ("version", "mise_version_mismatch"),
        ("architecture", "mise_platform_unsupported"),
        ("unbound", "mise_executable_record_invalid"),
    ],
)
def test_mise_rejects_unbound_or_unexpected_supply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, gap: str
) -> None:
    payload = _executable("2026.10.7" if fault == "version" else VERSION)
    digest = "f" * 64 if fault == "digest" else hashlib.sha256(payload).hexdigest()
    _source(tmp_path, x64=digest, executables=fault != "unbound")
    if fault == "architecture":
        monkeypatch.setattr(native.platform, "machine", lambda: "riscv64")
    _serve(monkeypatch, payload)

    with pytest.raises(ValueError, match=gap):
        native.prepare_mise(tmp_path)
    assert not list(tmp_path.rglob("mise.exe"))
    assert not list(tmp_path.rglob(".bootstrap-*"))


def test_supply_failure_reports_the_failure_its_cleanup_masked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A staging cleanup error never hides the bootstrap failure that preceded it."""
    payload = _executable("2026.10.7")
    _source(tmp_path, x64=hashlib.sha256(payload).hexdigest())
    _serve(monkeypatch, payload)

    class LockedStaging(native.TemporaryDirectory):
        def __exit__(self, *details: object) -> None:
            super().__exit__(*details)
            message = "[WinError 32] The process cannot access the file: 'mise.exe'"
            raise PermissionError(message)

    monkeypatch.setattr(native, "TemporaryDirectory", LockedStaging)
    monkeypatch.setattr(sys, "argv", ["native.py", "--root", str(tmp_path), "--mise"])

    assert native.main() == 1
    error = capsys.readouterr().err
    assert "WinError 32" in error
    assert "mise_version_mismatch" in error
