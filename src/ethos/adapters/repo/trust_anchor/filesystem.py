"""Observe and establish trust-anchor protection through native host authority."""

from __future__ import annotations

import os
import stat
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

_SYSTEM_SID = "S-1-5-18"
_ADMINISTRATORS_SID = "S-1-5-32-544"
# Write or append data, write extended attributes or attributes, delete, delete a child, change
# permissions or owner, and generic write or all.
_WRITE_MASK = 0x500D0156
_INHERIT_ONLY = 0x08
# Access-allowed entries, plain and object. Deny entries only remove authority.
_ALLOW = frozenset({0, 5})
_FILE_ALL_ACCESS = 0x1F01FF
_API_MISSING = "native_security_api_missing"
_UNSUPPORTED_ENTRY = "unsupported_access_entry"

type AccessEntry = tuple[int, int, int, str]
"""One DACL entry: its type, flags, access mask and the grantee's string SID."""


def protected_from_untrusted_write(path: Path, *, platform_name: str | None = None) -> bool:
    """Return whether the path and parent exclude untrusted write authority."""
    try:
        target = path.resolve(strict=True)
    except OSError:
        return False
    if (platform_name or os.name) != "nt":
        return all(_posix_protected(candidate) for candidate in (target, target.parent))
    try:
        current = _current_identity()
        descriptors = [_security_descriptor(candidate) for candidate in (target, target.parent)]
    except OSError as error:
        message = f"git_object_trust_anchor_observation_unavailable:{error}"
        raise ValueError(message) from error
    trusted = {current, _SYSTEM_SID, _ADMINISTRATORS_SID}
    return all(
        owner == current
        and entries is not None
        and {
            grantee
            for kind, flags, mask, grantee in entries
            if kind in _ALLOW and not flags & _INHERIT_ONLY and mask & _WRITE_MASK
        }
        <= trusted
        for owner, entries in descriptors
    )


def protect_for_current_identity(path: Path, *, platform_name: str | None = None) -> None:
    """Restrict one trust-anchor file to the current identity and host administrators."""
    if (platform_name or os.name) != "nt":
        path.chmod(0o700 if path.is_dir() else 0o600)
        return
    try:
        _grant_exclusive(path, (_current_identity(), _SYSTEM_SID, _ADMINISTRATORS_SID))
    except OSError as error:
        message = f"git_object_trust_anchor_protection_failed:{error}"
        raise OSError(message) from error


def _posix_protected(path: Path) -> bool:
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return False
    return mode & 0o022 == 0


def _security_api() -> ModuleType:
    """Import pywin32's security module, which only Windows installs, when a call needs it."""
    try:
        return import_module("win32security")
    except ImportError as error:
        raise OSError(_API_MISSING) from error


def _current_identity() -> str:
    """Return the string SID of the user this process runs as."""
    security = _security_api()
    try:
        process = import_module("win32api").GetCurrentProcess()
        token = security.OpenProcessToken(process, security.TOKEN_QUERY)
        user, _attributes = security.GetTokenInformation(token, security.TokenUser)
        identity = security.ConvertSidToStringSid(user)
    except security.error as error:
        raise OSError(_native_failure(error)) from error
    return identity


def _security_descriptor(path: Path) -> tuple[str, tuple[AccessEntry, ...] | None]:
    """Return a file's owner and DACL entries, or no entries for a null or absent DACL."""
    security = _security_api()
    try:
        descriptor = security.GetNamedSecurityInfo(
            str(path),
            security.SE_FILE_OBJECT,
            security.OWNER_SECURITY_INFORMATION | security.DACL_SECURITY_INFORMATION,
        )
        owner = security.ConvertSidToStringSid(descriptor.GetSecurityDescriptorOwner())
        dacl = descriptor.GetSecurityDescriptorDacl()
        # A plain entry is (header, mask, sid); an object entry holds two GUIDs before its SID.
        # pywin32 packs the mask as a signed 32-bit integer.
        entries = (
            None
            if dacl is None
            else tuple(
                (
                    header[0],
                    header[1],
                    mask & 0xFFFFFFFF,
                    security.ConvertSidToStringSid(rest[-1]),
                )
                for header, mask, *rest in map(dacl.GetAce, range(dacl.GetAceCount()))
            )
        )
    except NotImplementedError as error:
        raise OSError(_UNSUPPORTED_ENTRY) from error
    except security.error as error:
        raise OSError(_native_failure(error)) from error
    return owner, entries


def _grant_exclusive(path: Path, grantees: tuple[str, ...]) -> None:
    """Own a file as the first grantee and protect a DACL of full access for each grantee."""
    security = _security_api()
    try:
        sids = [security.ConvertStringSidToSid(grantee) for grantee in grantees]
        dacl = security.ACL()
        for sid in sids:
            dacl.AddAccessAllowedAce(security.ACL_REVISION, _FILE_ALL_ACCESS, sid)
        security.SetNamedSecurityInfo(
            str(path),
            security.SE_FILE_OBJECT,
            security.OWNER_SECURITY_INFORMATION
            | security.DACL_SECURITY_INFORMATION
            | security.PROTECTED_DACL_SECURITY_INFORMATION,
            sids[0],
            None,
            dacl,
            None,
        )
    except security.error as error:
        raise OSError(_native_failure(error)) from error


def _native_failure(error: Exception) -> str:
    """Name a failed Win32 call by its function, error number and bounded message."""
    funcname, winerror, strerror = (
        getattr(error, name, "") for name in ("funcname", "winerror", "strerror")
    )
    return f"{funcname}:winerror={winerror}:{' '.join(str(strerror).split())[:256]}"
