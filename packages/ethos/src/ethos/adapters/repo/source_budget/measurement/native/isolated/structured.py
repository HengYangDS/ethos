"""Strict INI, JSON, TOML, and YAML measurement primitives."""

from __future__ import annotations

import configparser
import json
import math
import re
import tomllib
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

from ethos.adapters.repo.source_budget.measurement.native.canonical import CanonicalMappingValue
from ethos.adapters.repo.source_budget.measurement.native.canonical import canonical_value
from ethos.adapters.repo.source_budget.measurement.native.canonical import frame
from ethos.adapters.repo.source_budget.measurement.native.canonical import scalar_frame

if TYPE_CHECKING:
    from typing import Never

    from yaml.nodes import Node

Scalar = str | int | float | bool | None | date | datetime | time
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

    def construct_typed_mapping(self, node: MappingNode) -> CanonicalMappingValue:
        entries: list[tuple[object, object]] = []
        seen: set[bytes] = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                _raise(yaml.YAMLError, "yaml mapping key must be scalar")
            key = cast("Scalar", self.construct_object(key_node, deep=True))
            try:
                canonical = scalar_frame(key)
            except ValueError as exc:
                _raise(yaml.YAMLError, "yaml mapping key is invalid", exc)
            identity = frame(key_node.tag.encode(), canonical)
            if identity in seen:
                _raise(yaml.YAMLError, "yaml mapping keys must be unique")
            seen.add(identity)
            value = self.construct_object(value_node, deep=True)
            entries.append((key, value))
        return CanonicalMappingValue(tuple(entries))


def measure_structured(provider_id: str, text: str) -> tuple[bytes, int, int]:
    """Parse and canonically frame one strict structured source."""
    try:
        parsed = _parse(provider_id, text)
    except (configparser.Error, yaml.YAMLError) as exc:
        _raise(ValueError, "structured parser rejected input", exc)
    stream, scalar_bytes, nodes = canonical_value(parsed)
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
    return _raise(ValueError, "structured provider is not admitted")


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
