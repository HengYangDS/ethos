"""Pure normalizers for dynamic values crossing typed boundaries."""

from __future__ import annotations


def string_list(value: object, *, drop_empty: bool = False) -> list[str]:
    """Return stringified list values, or an empty list for a non-list value."""
    if not isinstance(value, list):
        return []
    values = [str(item) for item in value]
    return [item for item in values if item] if drop_empty else values


def string_sequence(value: object) -> list[str]:
    """Return stringified list or tuple values, or an empty list otherwise."""
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value]
