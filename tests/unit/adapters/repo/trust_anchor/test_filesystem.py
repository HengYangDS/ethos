"""Verify trust-anchor protection by permission bits and reject foreign write permissions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.trust_anchor.filesystem import protect_for_current_identity
from ethos.adapters.repo.trust_anchor.filesystem import protected_from_untrusted_write

if TYPE_CHECKING:
    from pathlib import Path


def _anchor(tmp_path: Path) -> Path:
    anchor = tmp_path / "trust/allowed-signers"
    anchor.parent.mkdir()
    anchor.write_text("unchanged")
    return anchor


def test_protection_preserves_directory_traversal(tmp_path: Path) -> None:
    anchor = _anchor(tmp_path)

    protect_for_current_identity(anchor.parent)
    protect_for_current_identity(anchor)

    assert anchor.parent.stat().st_mode & 0o777 == 0o700
    assert anchor.stat().st_mode & 0o777 == 0o600
    assert protected_from_untrusted_write(anchor)


@pytest.mark.parametrize("writable", ["file", "parent"])
def test_a_group_or_other_writer_makes_the_anchor_untrusted(tmp_path: Path, writable: str) -> None:
    anchor = _anchor(tmp_path)
    protect_for_current_identity(anchor.parent)
    protect_for_current_identity(anchor)
    (anchor if writable == "file" else anchor.parent).chmod(0o620 if writable == "file" else 0o720)

    assert not protected_from_untrusted_write(anchor)


def test_an_absent_anchor_is_not_protected(tmp_path: Path) -> None:
    assert not protected_from_untrusted_write(tmp_path / "absent")


def test_a_failed_protection_keeps_the_host_reason(tmp_path: Path) -> None:
    with pytest.raises(OSError, match=r"^git_object_trust_anchor_protection_failed:No such file"):
        protect_for_current_identity(tmp_path / "absent")
