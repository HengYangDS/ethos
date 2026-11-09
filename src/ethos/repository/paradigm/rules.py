"""Rules binding conformance: the parameters, the profile stack and the rules are its only tables.

The rules readers consult `[paradigm]`, `[profiles]` and `[[rule]]`. The record binding retires an
`[artifacts]` table, and `binding-restatement` names a `[quality]` table that still holds
`code_size`, so each keeps its own gap until its move is done. Any other top-level key is a
declaration that no reader consults; the repair deletes a table as it deletes an unread workspace
table, and a bare value stays reported.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.records import TABLE as RECORD_TABLE

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ethos.contracts.paradigm.declaration import RepositoryParadigm


def rules_binding_gaps(paradigm: RepositoryParadigm, rules: str | None) -> Iterator[ParadigmGap]:
    """Report every top-level key of the rules binding that no reader consults."""
    try:
        declared = tomllib.loads(rules or "")
    except tomllib.TOMLDecodeError:
        return  # The rules readers report a binding that does not parse.
    carrier = paradigm.binding.path("rules")
    for key, value in declared.items():
        if key in paradigm.binding.rules_tables or _moving(key, value):
            continue
        repair = f"remove [{key}]; no reader consults it"
        yield ParadigmGap("rules-binding", f"{carrier}:{key}", repair)


def _moving(key: str, value: object) -> bool:
    """Return whether a table leaves through its own gap: the record binding or a restated size."""
    if not isinstance(value, dict):
        return False
    return key == RECORD_TABLE or (key == "quality" and "code_size" in value)
