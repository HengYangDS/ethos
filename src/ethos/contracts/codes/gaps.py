"""The registered gap vocabulary as data, read without a model or a transport dependency."""

from __future__ import annotations

import re
import tomllib
from functools import lru_cache
from importlib import resources
from typing import TypedDict

_CODE = re.compile(r"[a-z][a-z0-9_]*\Z")


class GapRecord(TypedDict, total=False):
    """One registered code: its owner package and the facts its row states."""

    owner: str
    detail: str
    meaning: str
    repair: str
    reserved: bool


def gap_code(gap: str) -> str:
    """Return the code of one gap: the text before its first colon."""
    return gap.partition(":")[0]


def code_shaped(code: str) -> bool:
    """Whether a gap's code is a code rather than prose or a printed value.

    A code is a lowercase identifier of letters, digits and underscores. A message, a rendered
    list or mapping, and a bare word like `gap` that labels a message are none of them codes.
    """
    return bool(_CODE.fullmatch(code)) and code != "gap"


@lru_cache(maxsize=1)
def _registry() -> tuple[dict[str, GapRecord], dict[str, str]]:
    """Read the packaged table once: its code rows and its family prefixes."""
    text = resources.files(__package__).joinpath("gaps.toml").read_text(encoding="utf-8")
    table = tomllib.loads(text)
    prefixes = table.pop("family", {})
    return table, prefixes


def records() -> dict[str, GapRecord]:
    """Return a copy of every registered code row by code, families excluded."""
    return {code: row.copy() for code, row in _registry()[0].items()}


def families() -> dict[str, str]:
    """Return every family prefix that registers the codes it begins."""
    return dict(_registry()[1])


def registered(code: str) -> bool:
    """Whether one code is registered, as a row or as a member of a family prefix."""
    rows, prefixes = _registry()
    return code in rows or any(code.startswith(prefix) for prefix in prefixes)


def record(code: str) -> GapRecord | None:
    """Return a copy of one code's row, or None if it has none; a family has no single row."""
    found = _registry()[0].get(code)
    return found.copy() if found is not None else None


def repair_for(gap: str) -> str:
    """Return the fixed next step a gap's row states, or the empty string."""
    found = record(gap_code(gap))
    return str(found.get("repair", "")) if found else ""
