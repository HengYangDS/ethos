"""Static keys and literal mappings for executable coupling aliases."""

from __future__ import annotations

import ast


def alias_key(reference: ast.expr) -> str | None:
    """Return a stable key for a statically addressable name, member, or item."""
    if isinstance(reference, ast.Name):
        return reference.id
    if isinstance(reference, ast.Attribute):
        parent = alias_key(reference.value)
        return f"{parent}.{reference.attr}" if parent is not None else None
    if isinstance(reference, ast.Subscript):
        parent = alias_key(reference.value)
        key = literal_subscript_key(reference.slice)
        return f"{parent}[{key}]" if parent is not None and key is not None else None
    return None


def literal_subscript_key(node: ast.expr | None) -> str | None:
    """Return the stable representation of one literal subscript key."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, bytes)):
        return repr(node.value)
    return None


def static_mapping_entries(value: ast.expr) -> tuple[tuple[tuple[str, ...], ast.expr], ...]:
    """Return every statically-addressable leaf of a literal mapping expression."""
    entries: list[tuple[tuple[str, ...], ast.expr]] = []
    for key, item in static_mapping_items(value):
        entries.append(((key,), item))
        for path, nested in static_mapping_entries(item):
            entries.append(((key, *path), nested))
    return tuple(entries)


def static_mapping_items(reference: ast.expr) -> tuple[tuple[str, ast.expr], ...]:
    """Return literal key/value pairs from a dictionary-shaped expression."""
    if isinstance(reference, ast.Dict):
        return tuple(
            (key, value)
            for key_node, value in zip(reference.keys, reference.values, strict=True)
            if value is not None and (key := literal_subscript_key(key_node)) is not None
        )
    if (
        isinstance(reference, ast.Call)
        and isinstance(reference.func, ast.Name)
        and reference.func.id == "dict"
        and not reference.args
        and all(keyword.arg is not None for keyword in reference.keywords)
    ):
        return tuple((repr(keyword.arg), keyword.value) for keyword in reference.keywords)
    return ()
