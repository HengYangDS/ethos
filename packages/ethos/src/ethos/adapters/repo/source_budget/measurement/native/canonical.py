"""Parser-free canonical scalar and container framing."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from typing import TYPE_CHECKING
from typing import Never
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class CanonicalMappingValue:
    """One mapping that preserves typed source-key identity until framing."""

    entries: tuple[tuple[object, object], ...]


def canonical_value(value: object) -> tuple[bytes, int, int]:
    """Return canonical stream, scalar bytes, and semantic node count."""
    if isinstance(value, CanonicalMappingValue):
        return _canonical_mapping(value.entries)
    if isinstance(value, dict):
        return _canonical_mapping(value.items())
    if isinstance(value, (list, tuple)):
        children = tuple(canonical_value(item) for item in value)
        return (
            frame(b"seq", b"".join(frame(b"item", item[0]) for item in children)),
            sum(item[1] for item in children),
            1 + sum(item[2] for item in children),
        )
    scalar = scalar_frame(value)
    return frame(b"scalar", scalar), len(scalar), 1


def scalar_frame(value: object) -> bytes:
    """Return one exact typed scalar frame."""
    if value is None:
        label, payload = b"null", b""
    elif type(value) is bool:
        label, payload = b"bool", b"true" if value else b"false"
    elif type(value) is int:
        label, payload = b"int", str(value).encode()
    elif type(value) is float:
        if not math.isfinite(value):
            _raise(ValueError, "non-finite structured scalar is not admitted")
        label, payload = b"float", value.hex().encode()
    elif type(value) is str:
        label, payload = b"str", value.encode("utf-8")
    elif type(value) in {date, datetime, time}:
        label = type(value).__name__.encode()
        payload = cast("date | datetime | time", value).isoformat().encode()
    else:
        return _raise(ValueError, "structured scalar type is not admitted")
    return frame(label, payload)


def frame(label: bytes, payload: bytes) -> bytes:
    """Return one deterministic length-prefixed byte frame."""
    return label + b":" + str(len(payload)).encode() + b":" + payload


def _canonical_mapping(entries: Iterable[tuple[object, object]]) -> tuple[bytes, int, int]:
    framed: list[tuple[bytes, bytes, int, int]] = []
    for key, child in entries:
        key_frame = scalar_frame(key)
        child_stream, child_bytes, child_nodes = canonical_value(child)
        entry = frame(b"key", key_frame) + frame(b"value", child_stream)
        framed.append((key_frame, entry, len(key_frame) + child_bytes, child_nodes + 1))
    framed.sort(key=lambda item: item[0])
    return (
        frame(b"map", b"".join(item[1] for item in framed)),
        sum(item[2] for item in framed),
        1 + sum(item[3] for item in framed),
    )


def _raise(error_type: type[Exception], message: str) -> Never:
    raise error_type(message)
