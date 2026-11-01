"""Verify native trust-anchor ownership and reject foreign write permissions."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import ethos.adapters.repo.trust_anchor.filesystem as trust_anchor_filesystem
from ethos.adapters.process import run_command
from ethos.adapters.repo.trust_anchor.filesystem import protect_for_current_identity
from ethos.adapters.repo.trust_anchor.filesystem import protected_from_untrusted_write
from ethos.adapters.repo.trust_anchor.verification import trust_anchor
from tools.ci.delivery.acceptance.host_environment import independent_host_environment

_CURRENT = "S-1-5-21-1000"
_FULL = 0x1F01FF
_TRUSTED = ((0, 0, _FULL, _CURRENT), (0, 0, _FULL, "S-1-5-18"), (0, 0, _FULL, "S-1-5-32-544"))


def _anchor(tmp_path: Path) -> Path:
    anchor = tmp_path / "trust/allowed-signers"
    anchor.parent.mkdir()
    anchor.write_text("unchanged")
    return anchor


@pytest.mark.parametrize(
    ("file", "parent", "expected"),
    [
        pytest.param((_CURRENT, _TRUSTED), None, True, id="trusted"),
        pytest.param(
            (_CURRENT, (*_TRUSTED, (0, 0, 0x116, "S-1-5-32-545"))), None, False, id="writer"
        ),
        pytest.param(
            (_CURRENT, (*_TRUSTED, (5, 0, 0x2, "S-1-5-32-545"))), None, False, id="object"
        ),
        pytest.param(
            (_CURRENT, (*_TRUSTED, (0, 0x08, 0x10000000, "S-1-3-0"))), None, True, id="io"
        ),
        pytest.param((_CURRENT, (*_TRUSTED, (1, 0, 0x116, "S-1-5-32-545"))), None, True, id="deny"),
        pytest.param((_CURRENT, (*_TRUSTED, (0, 0, 0x120089, "S-1-1-0"))), None, True, id="reader"),
        pytest.param(("S-1-5-21-2000", _TRUSTED), None, False, id="foreign-owner"),
        pytest.param((_CURRENT, None), None, False, id="null-dacl"),
        pytest.param(
            (_CURRENT, _TRUSTED),
            (_CURRENT, (*_TRUSTED, (0, 0x10, 0x2, "S-1-1-0"))),
            False,
            id="foreign-parent",
        ),
    ],
)
def test_windows_protection_decides_from_owner_and_write_entries(
    tmp_path, monkeypatch, file, parent, expected
):
    """Owner and effective write-like allow entries decide; inherit-only, deny and read do not."""
    facts = {"allowed-signers": file, "trust": parent or file}
    monkeypatch.setattr(trust_anchor_filesystem, "_current_identity", lambda: _CURRENT)
    monkeypatch.setattr(trust_anchor_filesystem, "_security_descriptor", lambda p: facts[p.name])
    assert protected_from_untrusted_write(_anchor(tmp_path), platform_name="nt") is expected


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(
            "missing",
            marks=pytest.mark.skipif(sys.platform == "win32", reason="pywin32 is present"),
        ),
        "native-error",
    ],
)
def test_windows_observation_failure_is_not_an_unprotected_acl(tmp_path, monkeypatch, failure):
    """Public trust admission retains unavailable-observer reasons without accepting."""
    anchor = _anchor(tmp_path)
    if failure == "native-error":

        def refuse(_path: Path) -> object:
            message = "GetNamedSecurityInfo:winerror=5:Access is denied."
            raise OSError(message)

        monkeypatch.setattr(trust_anchor_filesystem, "_current_identity", lambda: _CURRENT)
        monkeypatch.setattr(trust_anchor_filesystem, "_security_descriptor", refuse)
    native = protected_from_untrusted_write
    monkeypatch.setattr(
        "ethos.adapters.repo.trust_anchor.verification.protected_from_untrusted_write",
        lambda path: native(path, platform_name="nt"),
    )
    _resolved, gaps = trust_anchor(tmp_path / "repo", str(anchor))
    reason = {"missing": "native_security_api_missing", "native-error": "winerror=5"}[failure]
    assert len(gaps) == 1
    assert gaps[0].startswith("git_object_trust_anchor_observation_unavailable:")
    assert reason in gaps[0]
    assert anchor.read_text() == "unchanged"


def test_windows_protection_failure_keeps_the_native_reason(tmp_path, monkeypatch):
    """A refused DACL write fails closed with the failed call and its error number."""

    def refuse(_path: Path, _grantees: tuple[str, ...]) -> None:
        message = "SetNamedSecurityInfo:winerror=5:Access is denied."
        raise OSError(message)

    monkeypatch.setattr(trust_anchor_filesystem, "_current_identity", lambda: _CURRENT)
    monkeypatch.setattr(trust_anchor_filesystem, "_grant_exclusive", refuse)
    expected = "git_object_trust_anchor_protection_failed:SetNamedSecurityInfo:winerror=5"
    with pytest.raises(OSError, match=expected):
        protect_for_current_identity(_anchor(tmp_path), platform_name="nt")


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

    isolated, _git = independent_host_environment()
    with patch.dict(os.environ, isolated, clear=True):
        provider = run_command(
            anchor.parent, (sys.executable, "-I", "-c", "import _overlapped"), timeout=10
        )
        assert provider.returncode == 0, provider.stderr
        assert protected_from_untrusted_write(anchor)

    icacls = Path(os.environ["SYSTEMROOT"]) / "System32/icacls.exe"
    grant = (str(icacls), str(anchor), "/grant", f"*{foreign_sid}:W")
    run_command(anchor.parent, grant, check=True, timeout=60)

    with patch.dict(os.environ, isolated, clear=True):
        assert not protected_from_untrusted_write(anchor)
