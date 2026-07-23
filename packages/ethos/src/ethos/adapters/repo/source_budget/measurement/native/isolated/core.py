"""Child-only complex native source measurement engine."""

from __future__ import annotations

import ast
import hashlib
import importlib
import io
import json
import math
import platform
import sys
import tokenize
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic import ValidationError

from ethos.adapters.repo.source_budget.measurement.native.canonical import frame
from ethos.adapters.repo.source_budget.measurement.native.identity import ISOLATED_PARSER_IDS
from ethos.adapters.repo.source_budget.measurement.native.identity import ISOLATED_PROVIDER_IDS
from ethos.adapters.repo.source_budget.measurement.native.identity import (
    provider_conformance_content,
)
from ethos.adapters.repo.source_budget.measurement.native.identity import provider_dependencies
from ethos.adapters.repo.source_budget.measurement.native.identity import (
    provider_expected_conformance_digest,
)
from ethos.adapters.repo.source_budget.measurement.native.identity import revalidate_worker_provider
from ethos.adapters.repo.source_budget.measurement.native.shell.core import shell_tokens
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerResult
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import (
    admit_child_worker_gap,
)
from ethos_core.contracts.source_budget.measurements import MetricValue
from ethos_core.contracts.source_budget.measurements import NativeMeasurement
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType
    from typing import Any
    from typing import Literal
    from typing import Never

    from ethos_core.contracts.source_budget.metrics import MetricContract

_IGNORED_PYTHON_SYMBOL_NAMES = "ENCODING ENDMARKER NL NEWLINE INDENT DEDENT"
_SKIP_PYTHON_TOKENS = {getattr(tokenize, name) for name in _IGNORED_PYTHON_SYMBOL_NAMES.split()}
_STRUCTURED_MODULE = "ethos.adapters.repo.source_budget.measurement.native.isolated.structured"


class _ProviderError(ValueError):
    """Stable native-provider failure."""


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


def _raise(error_type: type[Exception], message: str, cause: Exception | None = None) -> Never:
    raise error_type(message) from cause


def _provider_module(provider_id: str, module_name: str) -> ModuleType:
    with _ProviderBoundary(f"source_budget_native_provider_unavailable:{provider_id}"):
        return importlib.import_module(module_name)


def measure_isolated(request: WorkerRequest, content: bytes) -> WorkerResult:
    """Measure one exact complex provider request inside the isolated child."""
    canonical_request = _canonicalize_worker_request(request)
    try:
        provider_id = _admit_worker_request(canonical_request, content)
    except MemoryError:
        return WorkerResult.from_gap(
            request=canonical_request,
            gap="source_budget_native_resource_exhausted",
        )
    except _ProviderError as exc:
        return WorkerResult.from_gap(
            request=canonical_request,
            gap=admit_child_worker_gap(str(exc)),
        )
    if gaps := _startup_conformance(provider_id):
        return WorkerResult.from_gap(
            request=canonical_request,
            gap=admit_child_worker_gap(gaps[0]),
        )
    load = _measure_admitted_native(
        content,
        canonical_request.contracts,
        provider_id,
    )
    if load.measurement is None:
        return WorkerResult.from_gap(
            request=canonical_request,
            gap=admit_child_worker_gap(load.required_gaps[0]),
        )
    return WorkerResult.from_measurement(
        request=canonical_request,
        measurement=load.measurement,
    )


def _canonicalize_worker_request(request: WorkerRequest) -> WorkerRequest:
    if type(request) is not WorkerRequest:
        _raise(_ProviderError, "source_budget_native_contract_invalid")
    fields = set(WorkerRequest.model_fields)
    try:
        if set(vars(request)) != fields or request.model_fields_set != fields:
            _raise(_ProviderError, "source_budget_native_contract_invalid")
        return WorkerRequest.model_validate(
            request.model_dump(mode="python", by_alias=True, warnings="error")
        )
    except MemoryError:
        raise
    except _ProviderError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError) as exc:
        _raise(_ProviderError, "source_budget_native_contract_invalid", exc)


def _admit_worker_request(request: WorkerRequest, content: bytes) -> str:
    if type(content) is not bytes:
        _raise(_ProviderError, "source_budget_native_contract_invalid")
    try:
        resolved = revalidate_worker_provider(request.contracts)
    except MemoryError:
        raise
    except ValueError as exc:
        gap = str(exc)
        _raise(
            _ProviderError,
            gap if gap.startswith("source_budget_") else "source_budget_native_contract_invalid",
            exc,
        )
    except (AttributeError, KeyError, TypeError, ValidationError) as exc:
        _raise(_ProviderError, "source_budget_native_contract_invalid", exc)
    if (
        request.contracts[0].parser_id not in ISOLATED_PARSER_IDS
        or resolved.provider_id not in ISOLATED_PROVIDER_IDS
        or resolved.execution_descriptor.execution_mode != "isolated_worker_v1"
    ):
        _raise(_ProviderError, "source_budget_native_execution_contract_invalid")
    if len(content) > resolved.execution_descriptor.max_carrier_bytes:
        _raise(_ProviderError, "source_budget_native_carrier_bytes_exceeded")
    expected = WorkerRequest.create(
        content=content,
        contracts=resolved.contracts,
        provider_descriptor=resolved.provider_descriptor,
        execution_descriptor=resolved.execution_descriptor,
    )
    if request != expected:
        _raise(_ProviderError, "source_budget_native_contract_invalid")
    return resolved.provider_id


def _measure_admitted_native(
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


def _failure(gap: str) -> NativeMeasurementLoad:
    return NativeMeasurementLoad(None, (gap,))


def _runtime_identity() -> tuple[str, int, int]:
    version = sys.version_info
    return platform.python_implementation(), version.major, version.minor


def _dependency_majors(provider_id: str) -> dict[str, int]:
    result: dict[str, int] = {}
    modules = {"jinja2": "jinja2", "pyyaml": "yaml"}
    for dependency in provider_dependencies(provider_id):
        module = _provider_module(provider_id, modules[dependency])
        with _ProviderBoundary(f"source_budget_native_provider_unavailable:{provider_id}"):
            result[dependency] = int(module.__version__.split(".", 1)[0])
    return result


def _conformance_gap(provider_id: str) -> str | None:
    mismatch = f"source_budget_native_conformance_mismatch:{provider_id}"
    try:
        with _ProviderBoundary(mismatch):
            observed = _conformance_output_digest(provider_id)
    except _ProviderError as exc:
        gap = str(exc)
        return gap if "provider_unavailable" in gap or "resource_exhausted" in gap else mismatch
    return None if observed == provider_expected_conformance_digest(provider_id) else mismatch


@lru_cache(maxsize=len(ISOLATED_PROVIDER_IDS))
def _startup_conformance(provider_id: str) -> tuple[str, ...]:
    if _runtime_identity() != ("CPython", 3, 14):
        return ("source_budget_native_runtime_unsupported",)
    expected_dependencies = provider_dependencies(provider_id)
    try:
        observed = _dependency_majors(provider_id)
    except MemoryError:
        return ("source_budget_native_resource_exhausted",)
    except _ProviderError as exc:
        return (str(exc),)
    for dependency in sorted(expected_dependencies):
        if observed.get(dependency) != expected_dependencies[dependency]:
            return (f"source_budget_native_dependency_major_mismatch:{dependency}",)
    gap = _conformance_gap(provider_id)
    return () if gap is None else (gap,)


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
        if provider_id == "python":
            return _measure_python(text)
        if provider_id == "jinja":
            return _measure_jinja(text)
        if provider_id == "shell":
            return _measure_lexical(shell_tokens(text))
        if provider_id not in {"ini", "json", "toml", "yaml"}:
            _raise(ValueError, "isolated provider is not admitted")
        module = _provider_module(provider_id, _STRUCTURED_MODULE)
        stream, nodes_count, scalar_bytes = module.measure_structured(provider_id, text)
        return stream, {
            ("normalized_scalar_bytes", "normalized_scalar_byte"): scalar_bytes,
            ("semantic_nodes", "semantic_node"): nodes_count,
        }


def _measure_python(text: str) -> tuple[bytes, dict[tuple[str, str], int]]:
    ast.parse(text, mode="exec", feature_version=(3, 14))
    tokens = tuple(tokenize.generate_tokens(io.StringIO(text).readline))
    if any(token.type == tokenize.ERRORTOKEN for token in tokens):
        _raise(ValueError, "python tokenizer error")
    significant = [
        (tokenize.tok_name[token.type], token.string)
        for token in tokens
        if token.type not in _SKIP_PYTHON_TOKENS
    ]
    return _measure_lexical(significant)


def _measure_lexical(
    tokens: Sequence[tuple[str, str]],
) -> tuple[bytes, dict[tuple[str, str], int]]:
    stream = b"".join(frame(kind.encode(), spelling.encode("utf-8")) for kind, spelling in tokens)
    return stream, {
        ("lexical_tokens", "lexical_token"): len(tokens),
        ("normalized_bytes", "normalized_byte"): len(stream),
    }


def _measure_jinja(text: str) -> tuple[bytes, dict[tuple[str, str], int]]:
    jinja = _provider_module("jinja", "jinja2")
    environment = jinja.Environment(autoescape=False, keep_trailing_newline=True, extensions=())
    try:
        root = environment.parse(text)
    except jinja.TemplateError as exc:
        _raise(ValueError, "jinja parser rejected input", exc)
    nodes = jinja.nodes
    dynamic_count = sum(
        not isinstance(item, nodes.TemplateData) for item in root.find_all(nodes.Node)
    )
    dynamic_payload = _canonical_json_bytes(_jinja_value(root, nodes))
    static_tokens = tuple(
        (kind, value) for _line, kind, value in environment.lex(text) if kind in {"data", "comment"}
    )
    static_payload = b"".join(
        frame(kind.encode(), value.encode("utf-8")) for kind, value in static_tokens
    )
    stream = frame(b"dynamic", dynamic_payload) + frame(b"static", static_payload)
    return stream, {
        ("template_dynamic_bytes", "template_dynamic_byte"): len(dynamic_payload),
        ("template_dynamic_units", "template_dynamic_unit"): dynamic_count,
        ("template_static_bytes", "template_static_byte"): sum(
            len(value.encode("utf-8")) for _kind, value in static_tokens
        ),
    }


def _jinja_value(value: object, nodes: Any) -> object:
    if isinstance(value, nodes.Node):
        return {
            "fields": {
                name: _jinja_value(getattr(value, name), nodes)
                for name in value.fields
                if not (isinstance(value, nodes.TemplateData) and name == "data")
            },
            "node": type(value).__name__,
        }
    if isinstance(value, (list, tuple)):
        return [_jinja_value(item, nodes) for item in value]
    if type(value) is float:
        if not math.isfinite(value):
            _raise(ValueError, "non-finite jinja AST field")
        return value
    if value is None or type(value) in {bool, int, str}:
        return value
    _raise(ValueError, "unsupported jinja AST field")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
