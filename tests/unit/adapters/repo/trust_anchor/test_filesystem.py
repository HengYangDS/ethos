from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.trust_anchor.filesystem as trust_anchor_filesystem
from ethos.adapters.repo.trust_anchor.filesystem import protect_for_current_identity
from ethos.adapters.repo.trust_anchor.filesystem import protected_from_untrusted_write

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


def test_windows_protection_accepts_only_trusted_write_authorities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = "S-1-5-21-1000"
    _fake_powershell(
        tmp_path,
        {
            "current_sid": current,
            "owner_sid": current,
            "write_allow_sids": [current, "S-1-5-18", "S-1-5-32-544"],
        },
    )
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    parent = tmp_path / "trust"
    parent.mkdir()
    anchor = parent / "allowed-signers"
    anchor.write_text("trusted\n", encoding="utf-8")

    assert protected_from_untrusted_write(anchor, platform_name="nt")


def test_windows_protection_rejects_foreign_write_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = "S-1-5-21-1000"
    _fake_powershell(
        tmp_path,
        {
            "current_sid": current,
            "owner_sid": current,
            "write_allow_sids": [current, "S-1-5-32-545"],
        },
    )
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    parent = tmp_path / "trust"
    parent.mkdir()
    anchor = parent / "allowed-signers"
    anchor.write_text("untrusted\n", encoding="utf-8")

    assert not protected_from_untrusted_write(anchor, platform_name="nt")


def test_windows_protection_rejects_foreign_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = "S-1-5-21-1000"
    _fake_powershell(
        tmp_path,
        {
            "current_sid": current,
            "owner_sid": "S-1-5-21-2000",
            "write_allow_sids": [current],
        },
    )
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    parent = tmp_path / "trust"
    parent.mkdir()
    anchor = parent / "allowed-signers"
    anchor.write_text("untrusted\n", encoding="utf-8")

    assert not protected_from_untrusted_write(anchor, platform_name="nt")


def test_windows_protection_fails_closed_without_native_observer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    parent = tmp_path / "trust"
    parent.mkdir()
    anchor = parent / "allowed-signers"
    anchor.write_text("unknown\n", encoding="utf-8")

    assert not protected_from_untrusted_write(anchor, platform_name="nt")


def test_windows_protection_failure_preserves_native_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_powershell(tmp_path, {})
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    target = tmp_path / "trust"
    target.mkdir()
    monkeypatch.setattr(
        trust_anchor_filesystem,
        "run_command",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=("powershell.exe",),
            returncode=5,
            stdout="",
            stderr="Set-Acl: Access is denied.\n",
        ),
    )

    with pytest.raises(
        OSError,
        match=(
            "git_object_trust_anchor_protection_failed:"
            "exit_code=5:stderr=Set-Acl: Access is denied\\."
        ),
    ):
        protect_for_current_identity(target, platform_name="nt")


def test_windows_native_process_rebuilds_its_module_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_powershell(tmp_path, {})
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path))
    target = tmp_path / "trust"
    target.mkdir()
    observed: dict[str, object] = {}

    def capture_run_command(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs)
        return subprocess.CompletedProcess(("powershell.exe",), 0, "", "")

    monkeypatch.setattr(trust_anchor_filesystem, "run_command", capture_run_command)

    protect_for_current_identity(target, platform_name="nt")

    assert observed["remove_env"] == ("PSModulePath",)


def test_posix_protection_preserves_directory_traversal(tmp_path: Path) -> None:
    parent = tmp_path / "trust"
    parent.mkdir()
    anchor = parent / "allowed-signers"
    anchor.write_text("trusted\n", encoding="utf-8")

    protect_for_current_identity(parent, platform_name="posix")
    protect_for_current_identity(anchor, platform_name="posix")

    assert parent.stat().st_mode & 0o777 == 0o700
    assert anchor.stat().st_mode & 0o777 == 0o600
    assert protected_from_untrusted_write(anchor, platform_name="posix")


@pytest.mark.skipif(os.name != "nt", reason="requires the Windows ACL authority")
def test_windows_native_acl_protection_rejects_foreign_writer(tmp_path: Path) -> None:
    parent = tmp_path / "trust"
    parent.mkdir()
    anchor = parent / "allowed-signers"
    anchor.write_text("trusted\n", encoding="utf-8")
    protect_for_current_identity(parent)
    protect_for_current_identity(anchor)

    assert protected_from_untrusted_write(anchor)

    subprocess.run(
        (
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "$acl=Get-Acl -LiteralPath $env:ETHOS_TRUST_ANCHOR_PATH;"
                "$sid=[System.Security.Principal.SecurityIdentifier]::new('S-1-5-32-545');"
                "$rule=New-Object System.Security.AccessControl.FileSystemAccessRule("
                "$sid,'Write','Allow');"
                "[void]$acl.AddAccessRule($rule);"
                "Set-Acl -LiteralPath $env:ETHOS_TRUST_ANCHOR_PATH -AclObject $acl"
            ),
        ),
        check=True,
        capture_output=True,
        env={**os.environ, "ETHOS_TRUST_ANCHOR_PATH": str(anchor)},
        text=True,
    )

    assert not protected_from_untrusted_write(anchor)
