"""Verify native trust-anchor ownership and reject foreign write permissions."""

from __future__ import annotations

import json
import os
import subprocess
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.trust_anchor.filesystem as trust_anchor_filesystem
from ethos.adapters.process import run_command
from ethos.adapters.process import windows_powershell
from ethos.adapters.repo.trust_anchor.filesystem import protect_for_current_identity
from ethos.adapters.repo.trust_anchor.filesystem import protected_from_untrusted_write
from ethos.adapters.repo.trust_anchor.verification import trust_anchor

if TYPE_CHECKING:
    from pathlib import Path


def _fake_powershell(tmp_path: Path, payload: dict[str, object]) -> Path:
    executable = tmp_path / "System32/WindowsPowerShell/v1.0/powershell.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text(
        f"#!/bin/sh\nprintf '%s\\n' '{json.dumps(payload, separators=(',', ':'))}'\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def _anchor(tmp_path: Path) -> Path:
    anchor = tmp_path / "trust/allowed-signers"
    anchor.parent.mkdir()
    anchor.write_text("unchanged")
    return anchor


@pytest.mark.parametrize(
    ("owner", "writers", "expected"),
    [
        ("S-1-5-21-1000", ["S-1-5-21-1000", "S-1-5-18", "S-1-5-32-544"], True),
        ("S-1-5-21-1000", ["S-1-5-21-1000", "S-1-5-32-545"], False),
        ("S-1-5-21-2000", ["S-1-5-21-1000"], False),
    ],
)
def test_windows_protection_distinguishes_owner_and_write_authority(
    tmp_path, monkeypatch, owner, writers, expected
):
    """Real payload consumers distinguish safe ACLs from foreign owner or writer."""
    _fake_powershell(
        tmp_path,
        {
            "current_sid": "S-1-5-21-1000",
            "owner_sid": owner,
            "write_allow_sids": writers,
        },
    )
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    anchor = _anchor(tmp_path)
    assert protected_from_untrusted_write(anchor, platform_name="nt") is expected


@pytest.mark.parametrize(
    "failure", ["missing", "root-missing", "native-error", "malformed", "creation"]
)
def test_windows_observation_failure_is_not_an_unprotected_acl(tmp_path, monkeypatch, failure):
    """Public trust admission retains unavailable-observer reasons without accepting."""
    anchor = _anchor(tmp_path)
    executable = _fake_powershell(tmp_path, {})
    if failure == "missing":
        executable.unlink()
    elif failure == "creation":
        executable.write_bytes(b"invalid executable")
    elif failure == "native-error":
        executable.write_text("#!/bin/sh\necho 'Get-Acl: module unavailable' >&2\nexit 7\n")
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    if failure == "root-missing":
        monkeypatch.delenv("SYSTEMROOT")
    native = protected_from_untrusted_write
    monkeypatch.setattr(
        "ethos.adapters.repo.trust_anchor.verification.protected_from_untrusted_write",
        lambda path: native(path, platform_name="nt"),
    )
    _resolved, gaps = trust_anchor(tmp_path / "repo", str(anchor))
    assert len(gaps) == 1
    assert gaps[0].startswith("git_object_trust_anchor_observation_unavailable")
    if failure in {"missing", "root-missing"}:
        assert {"missing": "native_executable_missing", "root-missing": "system_root_missing"}[
            failure
        ] in gaps[0]
    if failure == "native-error":
        assert "exit_code=7" in gaps[0]
        assert "module unavailable" in gaps[0]
    assert anchor.read_text() == "unchanged"


@pytest.mark.parametrize("native_exit", [0, 5, None])
def test_windows_protection_preserves_native_result_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native_exit: int | None
) -> None:
    _fake_powershell(tmp_path, {})
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    target = tmp_path / "trust"
    target.mkdir()
    observed: dict[str, object] = {}

    def capture_run_command(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs)
        if native_exit is None:
            raise subprocess.TimeoutExpired(("powershell.exe",), 30)
        return subprocess.CompletedProcess(
            ("powershell.exe",),
            native_exit,
            "",
            "Set-Acl: Access is denied.\n" if native_exit else "",
        )

    monkeypatch.setattr(trust_anchor_filesystem, "run_command", capture_run_command)
    reason = "timeout" if native_exit is None else "exit_code=5:stderr=Set-Acl: Access is denied\\."
    with (
        pytest.raises(OSError, match=f"git_object_trust_anchor_protection_failed:{reason}")
        if native_exit != 0
        else nullcontext()
    ):
        protect_for_current_identity(target, platform_name="nt")
    assert observed["remove_env"] == ("PSModulePath",)


def test_posix_protection_preserves_directory_traversal(tmp_path: Path) -> None:
    anchor = _anchor(tmp_path)

    protect_for_current_identity(anchor.parent, platform_name="posix")
    protect_for_current_identity(anchor, platform_name="posix")

    assert anchor.parent.stat().st_mode & 0o777 == 0o700
    assert anchor.stat().st_mode & 0o777 == 0o600
    assert protected_from_untrusted_write(anchor, platform_name="posix")


@pytest.mark.skipif(os.name != "nt", reason="requires the Windows ACL authority")
@pytest.mark.parametrize(
    "foreign_sid", ["S-1-5-32-545", "S-1-5-21-123456789-123456789-123456789-54321"]
)
def test_windows_native_acl_protection_rejects_foreign_writer(
    tmp_path: Path, foreign_sid: str
) -> None:
    anchor = _anchor(tmp_path)
    protect_for_current_identity(anchor.parent)
    protect_for_current_identity(anchor)

    assert protected_from_untrusted_write(anchor)

    run_command(
        anchor.parent,
        (
            windows_powershell(),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "$acl=Get-Acl -LiteralPath $env:ETHOS_TRUST_ANCHOR_PATH;"
                f"$sid=[System.Security.Principal.SecurityIdentifier]::new('{foreign_sid}');"
                "$rule=New-Object System.Security.AccessControl.FileSystemAccessRule("
                "$sid,'Write','Allow');"
                "[void]$acl.AddAccessRule($rule);"
                "Set-Acl -LiteralPath $env:ETHOS_TRUST_ANCHOR_PATH -AclObject $acl"
            ),
        ),
        check=True,
        env={**os.environ, "ETHOS_TRUST_ANCHOR_PATH": str(anchor)},
    )

    assert not protected_from_untrusted_write(anchor)
