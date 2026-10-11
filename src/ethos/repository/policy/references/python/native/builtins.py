"""Builtin names whose lexical lookup selects one qualified native target."""

from __future__ import annotations

NATIVE_BUILTINS = frozenset(
    {
        "getattr",
        "hasattr",
        "__import__",
        "str",
        "exec",
        "eval",
        "tuple",
        "list",
        "len",
        "dict",
        "classmethod",
        "isinstance",
        "int",
        "range",
        "type",
    }
)
