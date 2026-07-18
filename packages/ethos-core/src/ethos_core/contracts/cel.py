"""Restricted CEL evaluation for immutable declaration facts."""

from __future__ import annotations

from functools import lru_cache
from typing import Any
from typing import cast

import celpy
from celpy.celtypes import BoolType


def evaluate_cel_predicate(
    expression: str,
    *,
    facts: dict[str, object],
    policy: dict[str, object],
    rule: dict[str, object],
) -> bool:
    """Evaluate one declaration-owned CEL boolean over typed fact maps."""
    result = _cel_program(expression).evaluate(
        cast("Any", celpy.json_to_cel({"facts": facts, "policy": policy, "rule": rule}))
    )
    if not isinstance(result, BoolType):
        msg = "CEL predicate must return a boolean"
        raise TypeError(msg)
    return bool(result)


@lru_cache
def _cel_program(expression: str) -> Any:
    """Compile and cache one declaration-owned CEL predicate."""
    environment = celpy.Environment()
    return environment.program(environment.compile(expression))
