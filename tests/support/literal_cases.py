"""Typed loader for pure literal test-case projections."""

from __future__ import annotations

import hashlib
from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict


class _Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Source(_Closed):
    path: str
    kind: Literal["assign", "parametrize"]
    owner: str
    line: int


class _Case(_Closed):
    id: str
    source: _Source
    value: object
    value_sha256: str


class _Cases(_Closed):
    schema_version: Literal[1]
    cases: tuple[_Case, ...]


def _decode(value: object) -> object:
    if value is None or isinstance(value, (bool, float, int, str)):
        return value
    if not isinstance(value, dict) or set(value) != {"items", "type"}:
        message = "literal_case_shape_invalid"
        raise ValueError(message)
    items = value["items"]
    if value["type"] == "dict":
        return {_decode(key): _decode(item) for key, item in items}
    values = [_decode(item) for item in items]
    try:
        return {"tuple": tuple, "list": list, "set": set}[value["type"]](values)
    except (KeyError, TypeError):
        message = "literal_case_shape_invalid"
        raise ValueError(message) from None


@cache
def _cases() -> dict[str, object]:
    path = Path(__file__).parents[1] / "fixtures/literal-cases/cases.json"
    payload = _Cases.model_validate_json(path.read_text(encoding="utf-8"))
    decoded = {case.id: _decode(case.value) for case in payload.cases}
    if len(decoded) != len(payload.cases) or any(
        hashlib.sha256(repr(decoded[case.id]).encode()).hexdigest() != case.value_sha256
        for case in payload.cases
    ):
        message = "literal_case_identity_invalid"
        raise ValueError(message)
    return decoded


def literal_case(key: str) -> object:
    """Return one schema-validated pure literal case by stable owner key."""
    return _cases()[key]
