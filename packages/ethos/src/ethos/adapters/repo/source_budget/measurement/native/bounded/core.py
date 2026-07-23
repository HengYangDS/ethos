"""Bounded UTF-8, control, and C4 native measurement."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic import ValidationError

from ethos.adapters.repo.source_budget.measurement.native.canonical import canonical_value
from ethos.adapters.repo.source_budget.measurement.native.identity import BOUNDED_PARSER_IDS
from ethos.adapters.repo.source_budget.measurement.native.identity import BOUNDED_PROVIDER_IDS
from ethos.adapters.repo.source_budget.measurement.native.identity import ResolvedNativeProvider
from ethos.adapters.repo.source_budget.measurement.native.identity import (
    provider_conformance_content,
)
from ethos.adapters.repo.source_budget.measurement.native.identity import (
    provider_expected_conformance_digest,
)
from ethos.adapters.repo.source_budget.measurement.native.identity import resolve_native_provider
from ethos_core.contracts.source_budget.measurements import MetricValue
from ethos_core.contracts.source_budget.measurements import NativeMeasurement
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad

if TYPE_CHECKING:
    from typing import Literal
    from typing import Never

    from ethos_core.contracts.source_budget.metrics import MetricContract
    from ethos_core.contracts.source_budget.metrics import MetricContractSet

_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\Z")
_C4_ARITY = {"container": 3, "rel": 3, "system": 2}


class _ProviderError(ValueError):
    pass


class _ProviderBoundary:
    def __init__(self, gap: str) -> None:
        self.gap = gap

    def __enter__(self) -> None:
        return None

    def __exit__(self, _t: object, error: BaseException | None, _tb: object) -> Literal[False]:
        if isinstance(error, (MemoryError, RecursionError)):
            _raise(_ProviderError, "source_budget_native_resource_exhausted", error)
        if isinstance(error, Exception) and not isinstance(error, _ProviderError):
            _raise(_ProviderError, self.gap, error)
        return False


def measure_bounded(
    content: bytes,
    contracts: tuple[MetricContract, ...],
    registry: MetricContractSet,
) -> NativeMeasurementLoad:
    """Measure exact bytes through one admitted bounded provider."""
    try:
        return _measure_validated(content, contracts, registry)
    except MemoryError:
        return _failure("source_budget_native_resource_exhausted")
    except ValueError as exc:
        gap = str(exc)
        if gap.startswith("source_budget_"):
            return _failure(gap)
        return _failure("source_budget_native_contract_invalid")
    except (AttributeError, KeyError, TypeError, ValidationError):
        return _failure("source_budget_native_contract_invalid")


def measure_bounded_resolved(
    content: bytes,
    provider: ResolvedNativeProvider,
) -> NativeMeasurementLoad:
    """Measure through the exact provider already admitted by the parent router."""
    return _measure_resolved(content, provider)


def _measure_validated(
    content: bytes,
    contracts: tuple[MetricContract, ...],
    registry: MetricContractSet,
) -> NativeMeasurementLoad:
    if type(content) is not bytes:
        return _failure("source_budget_native_contract_invalid")
    resolved = resolve_native_provider(contracts, registry)
    return _measure_resolved(content, resolved)


def _measure_resolved(
    content: bytes,
    resolved: ResolvedNativeProvider,
) -> NativeMeasurementLoad:
    if type(content) is not bytes or type(resolved) is not ResolvedNativeProvider:
        return _failure("source_budget_native_contract_invalid")
    parser_id = resolved.contracts[0].parser_id
    if (
        parser_id not in BOUNDED_PARSER_IDS
        or resolved.provider_id not in BOUNDED_PROVIDER_IDS
        or resolved.execution_descriptor.execution_mode != "bounded_in_process_v1"
    ):
        return _failure("source_budget_native_execution_contract_invalid")
    if len(content) > resolved.execution_descriptor.max_carrier_bytes:
        return _failure("source_budget_native_carrier_bytes_exceeded")
    if gaps := _startup_conformance(resolved.provider_id):
        return NativeMeasurementLoad(None, gaps)
    return _measure_admitted(content, resolved.contracts, resolved.provider_id)


def _measure_admitted(
    content: bytes,
    contracts: tuple[MetricContract, ...],
    provider_id: str,
) -> NativeMeasurementLoad:
    try:
        text = _normalize_text(content)
        stream, measured = _measure_provider(provider_id, text)
        values = tuple(
            MetricValue(
                contract_id=contract.contract_id,
                metric_id=contract.metric_id,
                unit=contract.unit,
                value=measured[(contract.metric_id, contract.unit)],
            )
            for contract in contracts
        )
        measurement = NativeMeasurement.create(
            content_sha256=hashlib.sha256(content).hexdigest(),
            normalized_digest=hashlib.sha256(stream).hexdigest(),
            contracts=contracts,
            values=values,
        )
    except _ProviderError as exc:
        return _failure(str(exc))
    except MemoryError:
        return _failure("source_budget_native_resource_exhausted")
    except (KeyError, TypeError, ValueError, ValidationError):
        return _failure("source_budget_native_contract_invalid")
    return NativeMeasurementLoad(measurement, ())


def _runtime_identity() -> tuple[str, int, int]:
    version = sys.version_info
    return platform.python_implementation(), version.major, version.minor


@lru_cache(maxsize=len(BOUNDED_PROVIDER_IDS))
def _startup_conformance(provider_id: str) -> tuple[str, ...]:
    if _runtime_identity() != ("CPython", 3, 14):
        return ("source_budget_native_runtime_unsupported",)
    gap = _conformance_gap(provider_id)
    return () if gap is None else (gap,)


def _conformance_gap(provider_id: str) -> str | None:
    mismatch = f"source_budget_native_conformance_mismatch:{provider_id}"
    try:
        with _ProviderBoundary(mismatch):
            observed = _conformance_output_digest(provider_id)
    except _ProviderError as exc:
        gap = str(exc)
        return gap if "resource_exhausted" in gap else mismatch
    expected = provider_expected_conformance_digest(provider_id)
    return None if observed == expected else mismatch


def _conformance_output_digest(provider_id: str) -> str:
    text = _normalize_text(provider_conformance_content(provider_id))
    stream, measured = _measure_provider(provider_id, text)
    payload = {
        "metrics": [
            {"metric_id": metric_id, "unit": unit, "value": value}
            for (metric_id, unit), value in sorted(measured.items())
        ],
        "normalized_stream_hex": stream.hex(),
        "provider_id": provider_id,
    }
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _normalize_text(content: bytes) -> str:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        _raise(_ProviderError, "source_budget_native_text_invalid_utf8", exc)
    text = text.removeprefix("\ufeff")
    if "\ufeff" in text:
        _raise(_ProviderError, "source_budget_native_text_embedded_bom")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _measure_provider(
    provider_id: str,
    text: str,
) -> tuple[bytes, dict[tuple[str, str], int]]:
    with _ProviderBoundary(f"source_budget_native_parse_failed:{provider_id}"):
        if provider_id in {"utf8-control", "utf8-footprint"}:
            stream = text.encode()
            return stream, {("normalized_bytes", "normalized_byte"): len(stream)}
        if provider_id != "c4":
            _raise(ValueError, "bounded provider is not admitted")
        stream, scalar_bytes, nodes = canonical_value(_parse_c4(text))
        return stream, {
            ("normalized_scalar_bytes", "normalized_scalar_byte"): scalar_bytes,
            ("semantic_nodes", "semantic_node"): nodes,
        }


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
    return _raise(ValueError, "c4 quoted field is unterminated")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _failure(gap: str) -> NativeMeasurementLoad:
    return NativeMeasurementLoad(None, (gap,))


def _raise(error_type: type[Exception], message: str, cause: Exception | None = None) -> Never:
    raise error_type(message) from cause
