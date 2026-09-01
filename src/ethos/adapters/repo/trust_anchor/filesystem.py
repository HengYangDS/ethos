"""Observe and establish trust-anchor protection through native host authority."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.process import windows_powershell

if TYPE_CHECKING:
    from pathlib import Path

_SYSTEM_SID = "S-1-5-18"
_ADMINISTRATORS_SID = "S-1-5-32-544"
_WINDOWS_OBSERVE = r"""
$ErrorActionPreference = 'Stop'
$path = $env:ETHOS_TRUST_ANCHOR_PATH
$acl = Get-Acl -LiteralPath $path
$current = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$owner = ([System.Security.Principal.NTAccount]$acl.Owner).Translate(
  [System.Security.Principal.SecurityIdentifier]
).Value
$writeMask = [int64](
  [System.Security.AccessControl.FileSystemRights]::WriteData -bor
  [System.Security.AccessControl.FileSystemRights]::AppendData -bor
  [System.Security.AccessControl.FileSystemRights]::WriteExtendedAttributes -bor
  [System.Security.AccessControl.FileSystemRights]::WriteAttributes -bor
  [System.Security.AccessControl.FileSystemRights]::Delete -bor
  [System.Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor
  [System.Security.AccessControl.FileSystemRights]::ChangePermissions -bor
  [System.Security.AccessControl.FileSystemRights]::TakeOwnership
)
$writers = @(
  $acl.Access | Where-Object {
    $_.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Allow -and
    (([int64]$_.FileSystemRights -band $writeMask) -ne 0)
  } | ForEach-Object {
    $_.IdentityReference.Translate(
      [System.Security.Principal.SecurityIdentifier]
    ).Value
  } | Sort-Object -Unique
)
[pscustomobject]@{
  current_sid = $current
  owner_sid = $owner
  write_allow_sids = $writers
} | ConvertTo-Json -Compress
"""
_WINDOWS_PROTECT = r"""
$ErrorActionPreference = 'Stop'
$path = $env:ETHOS_TRUST_ANCHOR_PATH
$acl = Get-Acl -LiteralPath $path
$acl.SetAccessRuleProtection($true, $false)
@($acl.Access) | ForEach-Object { [void]$acl.RemoveAccessRuleSpecific($_) }
$full = [System.Security.AccessControl.FileSystemRights]::FullControl
$allow = [System.Security.AccessControl.AccessControlType]::Allow
$current = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$acl.SetOwner($current)
@($current.Value, 'S-1-5-18', 'S-1-5-32-544') | ForEach-Object {
  $sid = [System.Security.Principal.SecurityIdentifier]::new($_)
  $rule = [System.Security.AccessControl.FileSystemAccessRule]::new($sid, $full, $allow)
  [void]$acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $path -AclObject $acl
"""


def protected_from_untrusted_write(
    path: Path,
    *,
    platform_name: str | None = None,
) -> bool:
    """Return whether the path and parent exclude untrusted write authority."""
    try:
        target = path.resolve(strict=True)
    except OSError:
        return False
    if (platform_name or os.name) != "nt":
        return all(_posix_protected(candidate) for candidate in (target, target.parent))
    return all(_windows_protected(candidate) for candidate in (target, target.parent))


def protect_for_current_identity(path: Path, *, platform_name: str | None = None) -> None:
    """Restrict one trust-anchor file to the current identity and host administrators."""
    if (platform_name or os.name) != "nt":
        path.chmod(0o700 if path.is_dir() else 0o600)
        return
    completed = _run_windows(path, _WINDOWS_PROTECT)
    if completed is None or completed.returncode:
        if completed is None:
            message = "git_object_trust_anchor_protection_failed:native_observer_unavailable"
        else:
            stderr = " ".join(completed.stderr.split())[:512]
            message = (
                "git_object_trust_anchor_protection_failed:"
                f"exit_code={completed.returncode}:stderr={stderr}"
            )
        raise OSError(message)


def _posix_protected(path: Path) -> bool:
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return False
    return mode & 0o022 == 0


def _windows_protected(path: Path) -> bool:
    try:
        completed = _run_windows(path, _WINDOWS_OBSERVE)
    except ProcessExecutionError:
        return False
    if completed is None or completed.returncode:
        return False
    try:
        payload = cast("dict[str, Any]", json.loads(completed.stdout))
        current = str(payload["current_sid"])
        owner = str(payload["owner_sid"])
        writers = {str(value) for value in cast("list[object]", payload["write_allow_sids"])}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return owner == current and writers <= {current, _SYSTEM_SID, _ADMINISTRATORS_SID}


def _run_windows(path: Path, script: str) -> subprocess.CompletedProcess[str] | None:
    try:
        executable = windows_powershell()
    except ProcessExecutionError:
        return None
    try:
        return run_command(
            path.parent,
            (
                executable,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ),
            check=False,
            env={"ETHOS_TRUST_ANCHOR_PATH": str(path)},
            remove_env=("PSModulePath",),
            remove_env_prefixes=("GIT_",),
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return None
