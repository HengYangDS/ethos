"""Every host stages mise from the official executable whose digest the repository binds."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

import tools.ci.toolchain.native as native
from tests.support.architecture import write_reference_source

VERSION = "2026.10.8"


@pytest.fixture(autouse=True)
def without_operator_supply(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reach the staging path without operator supply or an immutable hosted image."""
    for name in ("ETHOS_CI_TOOL_CACHE_DIR", "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("ETHOS_CI_SUPPLY_MANIFEST", raising=False)
    which = native.shutil.which

    def without_operator_mise(name: str, **kwargs: object) -> str | None:
        return None if name == "mise" else which(name, **kwargs)

    monkeypatch.setattr(native.shutil, "which", without_operator_mise)


def _executable(observed: str = VERSION) -> bytes:
    return f"#!{sys.executable}\nprint({f'{observed} {native.mise_target()}'!r})\n".encode()


def _source(root: Path, *, digest: str, executables: bool = True) -> None:
    write_reference_source(root, ".config/mise/config.toml", f'min_version = "{VERSION}"')
    digests = {
        f"{system}-{arch}": "0" * 64
        for system in native.MISE_SYSTEMS.values()
        for arch in native.MISE_ARCHITECTURES.values()
    }
    digests[native.mise_target()] = digest
    rows = "".join(f'{name} = "{bound}"\n' for name, bound in sorted(digests.items()))
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


def test_mise_publishes_only_the_bound_official_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _executable()
    _source(tmp_path, digest=hashlib.sha256(payload).hexdigest())
    requests = _serve(monkeypatch, payload)

    executable = native.prepare_mise(tmp_path)

    assert executable.name == "mise"
    assert executable.read_bytes() == payload
    name = f"mise-v{VERSION}-{native.mise_target()}"
    assert [request[-1] for request in requests] == [
        f"https://github.com/jdx/mise/releases/download/v{VERSION}/{name}"
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
    _source(tmp_path, digest=digest, executables=fault != "unbound")
    if fault == "architecture":
        monkeypatch.setattr(native.platform, "machine", lambda: "riscv64")
    _serve(monkeypatch, payload)

    with pytest.raises(ValueError, match=gap):
        native.prepare_mise(tmp_path)
    assert not [path for path in tmp_path.rglob("mise") if path.is_file()]
    assert not list(tmp_path.rglob(".bootstrap-*"))


def test_supply_failure_reports_the_failure_its_cleanup_masked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A staging cleanup error never hides the bootstrap failure that preceded it."""
    payload = _executable("2026.10.7")
    _source(tmp_path, digest=hashlib.sha256(payload).hexdigest())
    _serve(monkeypatch, payload)

    class LockedStaging(native.TemporaryDirectory):
        def __exit__(self, *details: object) -> None:
            super().__exit__(*details)
            message = "staging directory cleanup refused"
            raise PermissionError(message)

    monkeypatch.setattr(native, "TemporaryDirectory", LockedStaging)
    monkeypatch.setattr(sys, "argv", ["native.py", "--root", str(tmp_path), "--mise"])

    assert native.main() == 1
    error = capsys.readouterr().err
    assert "staging directory cleanup refused" in error
    assert "mise_version_mismatch" in error
