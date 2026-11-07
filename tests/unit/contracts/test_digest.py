"""Hexadecimal identities are checked one way: lowercase digits of the declared lengths."""

from __future__ import annotations

import pytest

from ethos.contracts.digest import is_object_id
from ethos.contracts.digest import is_sha256_hex


@pytest.mark.parametrize(
    ("value", "sha256", "object_id"),
    [
        ("a" * 64, True, True),
        ("0" * 40, False, True),
        ("A" * 64, False, False),
        ("a" * 63, False, False),
        ("g" * 64, False, False),
        (b"a" * 64, False, False),
        (None, False, False),
    ],
)
def test_hex_identities_accept_only_lowercase_digits_of_their_lengths(
    value: object, *, sha256: bool, object_id: bool
) -> None:
    """A SHA-256 digest has 64 digits; a Git object ID has 40 or 64."""
    assert (is_sha256_hex(value), is_object_id(value)) == (sha256, object_id)
