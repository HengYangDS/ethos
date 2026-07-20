"""Context-bound success admission for measurement load envelopes."""

from __future__ import annotations

from collections.abc import Callable
from types import UnionType
from typing import Annotated
from typing import Literal
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin

from pydantic import BaseModel

type ModelValidator = Callable[[object, type[BaseModel], str], BaseModel]
type Replay = Callable[[BaseModel], BaseModel]


def _load_error(label: str, detail: str) -> ValueError:
    message = f"{label} {detail}"
    return ValueError(message)


class _FinalLoadMeta(type):
    """Reject descendants of direct Load envelopes before class creation."""

    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
        **kwargs: object,
    ) -> _FinalLoadMeta:
        if any(
            isinstance(base, _FinalLoadMeta)
            and any(isinstance(parent, _FinalLoadMeta) for parent in base.__bases__)
            for base in bases
        ):
            message = "measurement load envelopes forbid subclasses"
            raise TypeError(message)
        return cast(
            "_FinalLoadMeta",
            super().__new__(mcls, name, bases, namespace, **kwargs),
        )


class FinalLoad(metaclass=_FinalLoadMeta):
    """Allow only direct load-envelope definitions, never bypass subclasses."""

    __slots__ = ()


def validate_load(
    data: BaseModel | None,
    expected_type: type[BaseModel],
    required_gaps: tuple[str, ...],
    label: str,
    validate: ModelValidator,
) -> BaseModel | None:
    """Return canonical typed success or validate exact built-in failure gaps."""
    validated: BaseModel | None = None
    if data is not None:
        if type(data) is not expected_type or not _canonical_storage(data, expected_type):
            raise _load_error(label, "load requires typed data")
        try:
            validated = validate(data, expected_type, label)
        except ValueError:
            raise _load_error(label, "load requires typed data") from None
    if type(required_gaps) is not tuple:
        raise _load_error(label, "load required gaps must be a tuple")
    if any(type(gap) is not str or not gap for gap in required_gaps):
        raise _load_error(label, "load required gaps must be non-empty strings")
    if required_gaps != tuple(sorted(set(required_gaps))):
        raise _load_error(label, "load required gaps must be unique and stably ordered")
    if data is None and not required_gaps:
        raise _load_error(label, "load requires non-empty required gaps")
    if data is not None and required_gaps:
        raise _load_error(label, "load with data forbids required gaps")
    return validated


def validate_context_load(
    validated: BaseModel | None,
    context: tuple[object | None, ...],
    context_types: tuple[type[BaseModel], ...],
    label: str,
    replay: Replay,
) -> BaseModel | None:
    """Return canonical success after authoritative context replay."""
    if validated is None:
        if any(item is not None for item in context):
            raise _load_error(label, "failure load forbids context")
        return None
    if any(item is None for item in context):
        raise _load_error(label, "success load requires context")
    if any(
        type(item) is not expected or not _canonical_storage(item, expected)
        for item, expected in zip(context, context_types, strict=True)
    ):
        raise _load_error(label, "success load requires typed context")
    try:
        reproduced = replay(validated)
    except (AttributeError, TypeError, ValueError):
        raise _load_error(label, "success context must reproduce data") from None
    if reproduced != validated:
        raise _load_error(label, "success context must reproduce data")
    return validated


def _canonical_storage(value: object, expected: object) -> bool:
    origin = get_origin(expected)
    arguments = get_args(expected)
    if origin is Annotated:
        return _canonical_storage(value, arguments[0])
    if origin in (Union, UnionType):
        return any(_canonical_storage(value, option) for option in arguments)
    if origin is Literal:
        return any(type(value) is type(option) for option in arguments)
    if isinstance(expected, type) and issubclass(expected, BaseModel):
        return _canonical_model_storage(value, expected)
    if origin is tuple:
        return _canonical_tuple_storage(value, arguments[0])
    return type(value) is expected


def _canonical_model_storage(value: object, expected: type[BaseModel]) -> bool:
    if type(value) is not expected:
        return False
    try:
        storage = object.__getattribute__(value, "__dict__")
        extra = object.__getattribute__(value, "__pydantic_extra__")
        private = object.__getattribute__(value, "__pydantic_private__")
        declared_fields = type.__getattribute__(expected, "__pydantic_fields__")
    except AttributeError:
        return False
    if (
        type(storage) is not dict
        or type(declared_fields) is not dict
        or len(storage) != len(declared_fields)
        or any(type(key) is not str or key not in declared_fields for key in storage)
        or extra is not None
        or private is not None
    ):
        return False
    return all(
        _canonical_storage(
            item,
            object.__getattribute__(
                dict.__getitem__(declared_fields, key),
                "annotation",
            ),
        )
        for key, item in dict.items(storage)
    )


def _canonical_tuple_storage(value: object, item_type: object) -> bool:
    if not issubclass(type(value), tuple):
        return False
    items = tuple.__iter__(cast("tuple[object, ...]", value))
    return all(_canonical_storage(item, item_type) for item in items)
