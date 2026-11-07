"""Hexadecimal identities, checked one way: SHA-256 digests and Git object IDs."""

from __future__ import annotations

HEX_DIGITS = frozenset("0123456789abcdef")


def is_hex(value: object, *lengths: int) -> bool:
    """Return whether a value is lowercase hexadecimal of one of the given lengths."""
    return isinstance(value, str) and len(value) in lengths and not set(value) - HEX_DIGITS


def is_sha256_hex(value: object) -> bool:
    """Return whether a value is a SHA-256 digest in 64 lowercase hexadecimal characters."""
    return is_hex(value, 64)


def is_object_id(value: object) -> bool:
    """Return whether a value is a SHA-1 or SHA-256 Git object ID."""
    return is_hex(value, 40, 64)
