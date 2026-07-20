"""Strict structured and C4 native measurement primitives."""

from __future__ import annotations

import configparser
import json
import math
import re
import tomllib
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from typing import TYPE_CHECKING
from typing import cast
from typing import override

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode
from yaml.nodes import ScalarNode

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Never

    from yaml.nodes import Node

Scalar = str | int | float | bool | None | date | datetime | time
_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\Z")
_BOOL_TAG = "tag:yaml.org,2002:bool"
_FLOAT_TAG = "tag:yaml.org,2002:float"
_INT_TAG = "tag:yaml.org,2002:int"
_NULL_TAG = "tag:yaml.org,2002:null"
_MAP_TAG = "tag:yaml.org,2002:map"
_BOOL_PATTERN = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")
_FLOAT_PATTERN = re.compile(
    r"^(?:"
    r"[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
    r"|[-+]?\.(?:inf|Inf|INF)"
    r"|\.(?:nan|NaN|NAN)"
    r")$"
)
_INT_PATTERN = re.compile(r"^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$")
_NULL_PATTERN = re.compile(r"^(?:null|Null|NULL|~)?$")
_CORE_RESOLVERS = (
    (_NULL_TAG, _NULL_PATTERN, ("", "~", "n", "N")),
    (_BOOL_TAG, _BOOL_PATTERN, tuple("tTfF")),
    (_INT_TAG, _INT_PATTERN, tuple("-+0123456789")),
    (_FLOAT_TAG, _FLOAT_PATTERN, tuple("-+0123456789.")),
)
_ALLOWED_YAML_TAGS = {
    "tag:yaml.org,2002:bool",
    "tag:yaml.org,2002:float",
    "tag:yaml.org,2002:int",
    "tag:yaml.org,2002:map",
    "tag:yaml.org,2002:null",
    "tag:yaml.org,2002:seq",
    "tag:yaml.org,2002:str",
}
_C4_ARITY = {"container": 3, "rel": 3, "system": 2}


@dataclass(frozen=True, slots=True)
class _YamlMapping:
    entries: tuple[tuple[bytes, Scalar, object], ...]


def _raise(error_type: type[Exception], message: str, cause: Exception | None = None) -> Never:
    raise error_type(message) from cause


class _RestrictedYamlLoader(yaml.SafeLoader):
    """SafeLoader variant with YAML 1.2 core scalars and no graph aliases."""

    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self.yaml_implicit_resolvers: dict[str, list[tuple[str, re.Pattern[str]]]] = {}
        for tag, pattern, first_characters in _CORE_RESOLVERS:
            for first in first_characters:
                self.yaml_implicit_resolvers.setdefault(first, []).append((tag, pattern))
        self.yaml_constructors = self.yaml_constructors.copy()
        self.yaml_constructors[_NULL_TAG] = type(self).construct_core_null
        self.yaml_constructors[_BOOL_TAG] = type(self).construct_core_bool
        self.yaml_constructors[_INT_TAG] = type(self).construct_core_int
        self.yaml_constructors[_FLOAT_TAG] = type(self).construct_core_float
        self.yaml_constructors[_MAP_TAG] = type(self).construct_typed_mapping

    @override
    def process_directives(
        self,
    ) -> tuple[tuple[int, int] | None, dict[str, str] | None]:
        directives = super().process_directives()
        if directives[0] not in {None, (1, 2)}:
            _raise(yaml.YAMLError, "yaml version is not admitted")
        return directives

    def construct_core_null(self, node: ScalarNode) -> None:
        value = self.construct_scalar(node)
        if _NULL_PATTERN.fullmatch(value) is None:
            _raise(yaml.YAMLError, "yaml null scalar is invalid")

    def construct_core_bool(self, node: ScalarNode) -> bool:
        value = self.construct_scalar(node)
        if _BOOL_PATTERN.fullmatch(value) is None:
            _raise(yaml.YAMLError, "yaml boolean scalar is invalid")
        return value.lower() == "true"

    def construct_core_int(self, node: ScalarNode) -> int:
        value = self.construct_scalar(node)
        if _INT_PATTERN.fullmatch(value) is None:
            _raise(yaml.YAMLError, "yaml integer scalar is invalid")
        if value.startswith(("0o", "0x")):
            return int(value, 0)
        return int(value, 10)

    def construct_core_float(self, node: ScalarNode) -> float:
        value = self.construct_scalar(node)
        if _FLOAT_PATTERN.fullmatch(value) is None:
            _raise(yaml.YAMLError, "yaml float scalar is invalid")
        lowered = value.lower()
        if lowered.endswith(".inf"):
            return -math.inf if value.startswith("-") else math.inf
        if lowered == ".nan":
            return math.nan
        return float(value)

    def compose_node(self, parent: Node | None, index: object) -> Node:
        if self.check_event(AliasEvent) or self.peek_event().anchor is not None:
            _raise(yaml.YAMLError, "yaml graph aliases and anchors are not admitted")
        node = super().compose_node(parent, index)
        if node.tag not in _ALLOWED_YAML_TAGS:
            _raise(yaml.YAMLError, "yaml tag is not admitted")
        return node

    def construct_typed_mapping(self, node: MappingNode) -> _YamlMapping:
        entries: list[tuple[bytes, Scalar, object]] = []
        seen: set[bytes] = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                _raise(yaml.YAMLError, "yaml mapping key must be scalar")
            key = cast("Scalar", self.construct_object(key_node, deep=True))
            try:
                canonical = _scalar_frame(key)
            except ValueError as exc:
                _raise(yaml.YAMLError, "yaml mapping key is invalid", exc)
            identity = _frame(key_node.tag.encode(), canonical)
            if identity in seen:
                _raise(yaml.YAMLError, "yaml mapping keys must be unique")
            seen.add(identity)
            value = self.construct_object(value_node, deep=True)
            entries.append((identity, key, value))
        return _YamlMapping(tuple(entries))


def measure_structured(provider_id: str, text: str) -> tuple[bytes, int, int]:
    """Parse and canonically frame one strict structured source."""
    try:
        parsed = _parse(provider_id, text)
    except (configparser.Error, yaml.YAMLError) as exc:
        _raise(ValueError, "structured parser rejected input", exc)
    stream, scalar_bytes, nodes = _canonical(parsed)
    return stream, nodes, scalar_bytes


def _parse(provider_id: str, text: str) -> object:
    if provider_id == "toml":
        return tomllib.loads(text)
    if provider_id == "json":
        return json.loads(
            text,
            object_pairs_hook=_json_object,
            parse_constant=_reject_json_constant,
        )
    if provider_id == "yaml":
        return yaml.load(text, Loader=_RestrictedYamlLoader)
    if provider_id == "ini":
        return _parse_ini(text)
    return _parse_c4(text)


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _raise(ValueError, "json object keys must be unique")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    _raise(ValueError, "json non-finite values are not admitted")


def _parse_ini(text: str) -> dict[str, object]:
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.read_string(text)
    result: dict[str, object] = {}
    if parser.defaults():
        result[parser.default_section] = dict(parser.defaults())
    for section in parser.sections():
        result[section] = dict(parser.items(section, raw=True))
    return result


def _parse_c4(text: str) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    for line in text.splitlines():
        tokens = _c4_tokens(line)
        if not tokens:
            continue
        keyword = tokens[0][0].lower()
        arity = _C4_ARITY.get(keyword)
        if arity is None or len(tokens) != arity + 1:
            _raise(ValueError, "c4 record kind or arity is invalid")
        fields = tokens[1:]
        if not _c4_shape(keyword, fields):
            _raise(ValueError, "c4 record quoting is invalid")
        records.append({"kind": keyword, "fields": tuple(value for value, _ in fields)})
    if not records:
        _raise(ValueError, "c4 source requires records")
    return tuple(sorted(records, key=lambda item: json.dumps(item, sort_keys=True)))


def _c4_shape(keyword: str, fields: list[tuple[str, bool]]) -> bool:
    values = [value for value, _quoted in fields]
    quoted = [item for _value, item in fields]
    if keyword == "system":
        return bool(_ID.fullmatch(values[0])) and quoted == [False, True]
    if keyword == "container":
        return bool(_ID.fullmatch(values[0])) and quoted == [False, True, True]
    return all(_ID.fullmatch(value) for value in values[:2]) and quoted == [
        False,
        False,
        True,
    ]


def _c4_tokens(line: str) -> list[tuple[str, bool]]:
    tokens: list[tuple[str, bool]] = []
    index = 0
    while index < len(line):
        if line[index].isspace():
            index += 1
            continue
        if line[index] == "#":
            break
        if line[index] == '"':
            value, index = _c4_quoted(line, index)
            tokens.append((value, True))
            continue
        end = index
        while end < len(line) and not line[end].isspace() and line[end] != "#":
            if line[end] == '"':
                _raise(ValueError, "c4 quoting must start a field")
            end += 1
        tokens.append((line[index:end], False))
        index = end
    return tokens


def _c4_quoted(line: str, index: int) -> tuple[str, int]:
    output: list[str] = []
    index += 1
    while index < len(line):
        char = line[index]
        if char == '"':
            return "".join(output), index + 1
        if char == "\\":
            index += 1
            if index >= len(line):
                break
            output.append({"n": "\n", "r": "\r", "t": "\t"}.get(line[index], line[index]))
        else:
            output.append(char)
        index += 1
    _raise(ValueError, "c4 quoted field is unterminated")


def _canonical(value: object) -> tuple[bytes, int, int]:
    if isinstance(value, _YamlMapping):
        return _canonical_mapping((key, child) for _identity, key, child in value.entries)
    if isinstance(value, dict):
        return _canonical_mapping(value.items())
    if isinstance(value, (list, tuple)):
        children = tuple(_canonical(item) for item in value)
        return (
            _frame(b"seq", b"".join(_frame(b"item", item[0]) for item in children)),
            sum(item[1] for item in children),
            1 + sum(item[2] for item in children),
        )
    scalar = _scalar_frame(value)
    return _frame(b"scalar", scalar), len(scalar), 1


def _canonical_mapping(entries: Iterable[tuple[object, object]]) -> tuple[bytes, int, int]:
    framed: list[tuple[bytes, bytes, int, int]] = []
    for key, child in entries:
        key_frame = _scalar_frame(key)
        child_stream, child_bytes, child_nodes = _canonical(child)
        entry = _frame(b"key", key_frame) + _frame(b"value", child_stream)
        framed.append((key_frame, entry, len(key_frame) + child_bytes, child_nodes + 1))
    framed.sort(key=lambda item: item[0])
    return (
        _frame(b"map", b"".join(item[1] for item in framed)),
        sum(item[2] for item in framed),
        1 + sum(item[3] for item in framed),
    )


def _scalar_frame(value: object) -> bytes:
    if value is None:
        return _frame(b"null", b"")
    if type(value) is bool:
        return _frame(b"bool", b"true" if value else b"false")
    if type(value) is int:
        return _frame(b"int", str(value).encode())
    if type(value) is float:
        if not math.isfinite(value):
            _raise(ValueError, "non-finite structured scalar is not admitted")
        return _frame(b"float", value.hex().encode())
    if type(value) is str:
        return _frame(b"str", value.encode("utf-8"))
    if type(value) in {date, datetime, time}:
        return _frame(
            type(value).__name__.encode(),
            cast("date | datetime | time", value).isoformat().encode(),
        )
    _raise(ValueError, "structured scalar type is not admitted")


def _frame(label: bytes, payload: bytes) -> bytes:
    return label + b":" + str(len(payload)).encode() + b":" + payload
