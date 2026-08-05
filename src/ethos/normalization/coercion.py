"""Pure normalizers for dynamic values crossing typed boundaries."""

from __future__ import annotations

import fnmatch


def string_list(value: object, *, drop_empty: bool = False) -> list[str]:
    """Return stringified list values, or an empty list for a non-list value."""
    if not isinstance(value, list):
        return []
    values = [str(item) for item in value]
    return [item for item in values if item] if drop_empty else values


def string_sequence(value: object, *, drop_empty: bool = False) -> list[str]:
    """Return stringified list or tuple values, or an empty list otherwise."""
    if not isinstance(value, list | tuple):
        return []
    values = [str(item) for item in value]
    return [item for item in values if item] if drop_empty else values


def object_sequence(value: object) -> list[object]:
    """Return list or tuple members as objects, or an empty list otherwise."""
    if not isinstance(value, list | tuple):
        return []
    return list(value)


def string_mapping(value: object) -> dict[str, object]:
    """Return a string-keyed mapping projection, or an empty mapping otherwise."""
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def integer(value: object, *, default: int = 0) -> int:
    """Return an integer value without accepting booleans or arbitrary scalars."""
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def repository_path_matches(path: str, pattern: str) -> bool:
    """Match one repository-relative path against a recursive glob."""
    if pattern == "**":
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return fnmatch.fnmatchcase(path, prefix) or fnmatch.fnmatchcase(path, f"{prefix}/*")
    return fnmatch.fnmatchcase(path, pattern)
