"""Reusable immutable value annotations for portable contracts."""

from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated
from typing import Any
from typing import TypeVar

from pydantic import AfterValidator
from pydantic import BeforeValidator
from pydantic import PlainSerializer
from pydantic import WithJsonSchema

T = TypeVar("T")
_FROZEN_TUPLE_INVALID = "frozen_tuple_invalid"
_JSON_OBJECT_INVALID = "json_object_invalid"
_JSON_OBJECT_KEY_INVALID = "json_object_key_invalid"
_JSON_VALUE_INVALID = "json_value_invalid"


def frozen_tuple(value: object) -> tuple[object, ...]:
    """Accept only ordered array carriers and freeze them as one tuple."""
    if not isinstance(value, tuple | list):
        raise TypeError(_FROZEN_TUPLE_INVALID)
    return tuple(value)


FrozenTuple = Annotated[tuple[T, ...], BeforeValidator(frozen_tuple)]


def mutable_json(value: object) -> object:
    """Return the portable mutable JSON projection of an immutable value."""
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError(_JSON_OBJECT_KEY_INVALID)
        return {key: mutable_json(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [mutable_json(item) for item in value]
    return value


def _immutable_json(value: object) -> object:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError(_JSON_OBJECT_KEY_INVALID)
        return MappingProxyType({key: _immutable_json(item) for key, item in value.items()})
    if isinstance(value, tuple | list):
        return tuple(_immutable_json(item) for item in value)
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError(_JSON_VALUE_INVALID)


def _immutable_json_object(value: object) -> object:
    if not isinstance(value, Mapping):
        raise TypeError(_JSON_OBJECT_INVALID)
    return _immutable_json(value)


JsonObject = Annotated[
    Any,
    BeforeValidator(_immutable_json_object),
    PlainSerializer(mutable_json, return_type=Any, when_used="always"),
    WithJsonSchema({"type": "object", "additionalProperties": {}}),
]
JsonValue = Annotated[
    Any,
    BeforeValidator(_immutable_json),
    PlainSerializer(mutable_json, return_type=Any, when_used="always"),
    WithJsonSchema({}),
]


def frozen_mapping[T](value: Mapping[str, T]) -> Mapping[str, T]:
    """Copy one mapping into a read-only process value."""
    return MappingProxyType(dict(value))


FrozenMapping = Annotated[
    Mapping[str, T],
    AfterValidator(frozen_mapping),
    PlainSerializer(dict, return_type=dict),
]
