"""Canonical runtime-bound native source measurement providers."""

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

from ethos.adapters.repo.source_budget.measurement.native.shell.core import shell_tokens
from ethos_core.contracts.source_budget.measurement.execution import execution_descriptor
from ethos_core.contracts.source_budget.measurement.execution import parser_execution_contract
from ethos_core.contracts.source_budget.measurements import MetricValue
from ethos_core.contracts.source_budget.measurements import NativeMeasurement
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad
from ethos_core.contracts.source_budget.metrics import MetricContract

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType
    from typing import Any
    from typing import Literal
    from typing import Never

_CANONICAL_RUNTIME = {"implementation": "CPython", "major": 3, "minor": 14}
_IGNORED_PYTHON_SYMBOL_NAMES = "ENCODING ENDMARKER NL NEWLINE INDENT DEDENT"
_SKIP_PYTHON_TOKENS = {getattr(tokenize, name) for name in _IGNORED_PYTHON_SYMBOL_NAMES.split()}
_STRUCTURED_PROVIDERS = frozenset({"c4", "ini", "json", "toml", "yaml"})
_STRUCTURED_METRICS = (
    ("normalized_scalar_bytes", "normalized_scalar_byte"),
    ("semantic_nodes", "semantic_node"),
)
_LEXICAL_METRICS = (
    ("lexical_tokens", "lexical_token"),
    ("normalized_bytes", "normalized_byte"),
)
_PROVIDER_DEPENDENCIES = {"jinja": {"jinja2": 3}, "yaml": {"pyyaml": 6}}
_STRUCTURED_MODULE = "ethos.adapters.repo.source_budget.measurement.native._structured"
_PROVIDER_PARSERS = {
    "c4": "diagram-contract|cpython-3.14+ethos-c4-v1",
    "ini": "configparser|cpython-3.14+ethos-ini-v1",
    "jinja": "jinja2|cpython-3.14+jinja-3+ethos-jinja-v3",
    "json": "json-stdlib|cpython-3.14+ethos-json-v1",
    "python": "python-tokenize|cpython-3.14+ethos-python-v1",
    "shell": "shell-lexical|cpython-3.14+ethos-shell-v4",
    "toml": "tomllib|cpython-3.14+ethos-toml-v1",
    "utf8-control": "utf8-control|cpython-3.14+ethos-utf8-v1",
    "utf8-footprint": "utf8-footprint|cpython-3.14+ethos-utf8-v1",
    "yaml": "pyyaml-safe|cpython-3.14+pyyaml-6+ethos-yaml-v2",
}
_PROVIDER_RULES = {
    "c4": "finite-c4-record-grammar|quoted-payloads|sorted-records",
    "ini": "strict-duplicates|no-interpolation|canonical-scalars",
    "jinja": (
        "parse-only|keep-trailing-lf|dynamic-ast-units|canonical-dynamic-bytes"
        "|finite-numeric-literals|strict-json|static-data-comment-bytes"
    ),
    "json": "unique-object-keys|finite-numbers|canonical-scalars",
    "python": "ast-syntax-guard|significant-token-count|type-and-spelling-frames",
    "shell": (
        "finite-bash-zsh-lexer|balanced-groups-substitutions|case-keyword-phases"
        "|literal-dollar|arithmetic-and-array-shifts|parameter-literal-shifts"
        "|quoted-backticks|nested-heredocs|comment-delimiter-rejection"
        "|quote-removed-heredoc-word-fragments|heredoc-payloads"
        "|function-definition-headers|line-continuation-command-state"
        "|parameter-expansion-literals|contextual-nested-closers"
        "|resource-exhaustion-classification"
    ),
    "toml": "tomllib-parse|unique-keys|canonical-scalars",
    "utf8-control": "strict-utf8|one-leading-bom|lf-newlines",
    "utf8-footprint": "strict-utf8|one-leading-bom|lf-newlines",
    "yaml": (
        "yaml-1.2-core|complete-core-scalars|strict-core-constructors"
        "|yaml-version-1.2-only|no-implicit-timestamp-merge-value-yaml"
        "|no-alias-graph|safe-tags|tag-canonical-key-identity|typed-key-storage"
    ),
}
_PROVIDER_IDS = tuple(sorted(_PROVIDER_PARSERS))
_CONFORMANCE_CASES = {
    "c4": (b'system ETHOS "Governance"\ncontainer Git "Git" "Refs"\nrel ETHOS Git "uses"\n'),
    "ini": b"[service]\nname=ethos\ncount=2\n",
    "jinja": b'a{#comment#}{{ "payload-value" | upper }}{{ 1e3 }}b\n',
    "json": b'{"name":"ethos","items":[1,true,null]}\n',
    "python": b"first=1; second='two' # comment\n",
    "shell": (
        b"items=(one two)\n"
        b'case "$mode" in\n'
        b"  a|case) echo esac ;;\n"
        b'  nested) case "$other" in x) echo esac ;; esac ;;\n'
        b'  *) echo "$((1 << 2))" "$((8<<-1))" ;;\n'
        b"esac\n"
        b"value=\"$(\n  cat <<'EOF'\nbody\nEOF\n)\"\n"
        b"cat <<\\WORD\nfragment\nWORD\n"
        b"arr[1<<2]=x\n"
        b'joined="pre${value}post"\n'
        b"joined_zsh=${(j:,:)items}\n"
        b"echo ${arr[1<<2]} ${x#<<}\n"
        b'echo "`printf ok`" "\\`literal"\n'
        b"echo $(echo $(date))\n"
        b"echo <(cat <(printf x))\n"
        b"f() { :; }\n"
        b"function g\n{ :; }\n"
        b"if true && \\\n{ :; }\n"
        b"echo { [[\n"
        b"cat <<$'E\\x4fF'\nansi\nEOF\n"
        b'if [[ "${#items[@]}" =~ ^[0-9]+$ ]]; then :; fi\n'
    ),
    "toml": b"name='ethos'\ncount=2\n",
    "utf8-control": b"alpha\r\nbeta\r",
    "utf8-footprint": b"\xef\xbb\xbfalpha\r\nbeta\r",
    "yaml": (
        b"name: ethos\n"
        b"items: [012, 0o7, 1e3, true, null]\n"
        b"legacy_strings: [on, 1:20, 1_000, -0x3A, 0b10, <<, =]\n"
        b"explicit: !!float 12\n"
        b"typed_keys:\n"
        b"  true: bool\n"
        b"  1: int\n"
        b"  1.0: float\n"
        b"  -0.0: negative-zero\n"
        b"  0.0: positive-zero\n"
    ),
}
_EXPECTED_CONFORMANCE_DIGESTS = {
    "c4": "5f8bac5ef288997b60fb1cedaf08790c8ae1adc5c0471a57f36318e10d35735c",
    "ini": "b502516798252b49f65c0a9a0113e1abc12c9e0f90e782fd20a8af11f18eb2fa",
    "jinja": "337d89fad45ac03517fd3b60d090a8d850f60714b11cd894e0aa8bedf4ca068b",
    "json": "9f66c10e9ca91655f6b6efc1a212d1f28b5a17bba80431a671e63838559e1752",
    "python": "ce3459c91f2d4185791ff067dfb52bba4b53930c2c9e8a1b6ffbd1597a561176",
    "shell": "a4d8d0b5590b4c69b298cbceb4655c9c551948fda7781e4be0bc667a90fc03c7",
    "toml": "4e0a08136432076ce5771746128ef9079c8d839b980157104464a93c5129e2e1",
    "utf8-control": "45d13f0f9cd68df46c317ad4d10d720cfdde11e5ab95d062a64b0938398d0e50",
    "utf8-footprint": ("156f5c6465dbf820bdf522220411dbf5f072e53edb3b4866a0e188f4bb92f23d"),
    "yaml": "5f6c7dbff96e3281b4b21968f5c1321f9f12cbe19e7be8db352a67d232ae7327",
}

type _AdmittedNativeRequest = tuple[str, tuple[MetricContract, ...]]


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


def measure_native(
    content: bytes,
    contracts: tuple[MetricContract, ...],
) -> NativeMeasurementLoad:
    """Measure exact bytes through one fully matched native provider."""
    try:
        admitted = _admit_native_request(content, contracts)
        if isinstance(admitted, NativeMeasurementLoad):
            return admitted
        provider_id, contracts = admitted
        if gaps := _startup_conformance():
            return NativeMeasurementLoad(None, gaps)
        return _measure_admitted_native(content, contracts, provider_id)
    except MemoryError:
        return _failure("source_budget_native_resource_exhausted")


def _admit_native_request(
    content: bytes,
    contracts: tuple[MetricContract, ...],
) -> _AdmittedNativeRequest | NativeMeasurementLoad:
    try:
        if type(content) is not bytes or type(contracts) is not tuple or not contracts:
            _raise(_ProviderError, "source_budget_native_contract_invalid")
        if any(type(item) is not MetricContract for item in contracts):
            _raise(_ProviderError, "source_budget_native_contract_invalid")
        provider_ids = tuple(_provider_id_for_contract(item) for item in contracts)
        provider_id = provider_ids[0]
        if provider_id is None or any(item != provider_id for item in provider_ids):
            _raise(_ProviderError, "source_budget_native_provider_signature_mismatch")
        contracts = tuple(
            MetricContract.model_validate(item.model_dump(mode="python")) for item in contracts
        )
        expected_coordinates = set(_provider_metrics(provider_id))
        actual_coordinates = {(item.metric_id, item.unit) for item in contracts}
        if actual_coordinates != expected_coordinates:
            _raise(_ProviderError, "source_budget_native_provider_signature_mismatch")
    except _ProviderError as exc:
        return _failure(str(exc))
    except MemoryError:
        return _failure("source_budget_native_resource_exhausted")
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        return _failure("source_budget_native_contract_invalid")
    return provider_id, contracts


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


def _dependency_majors() -> dict[str, int]:
    result: dict[str, int] = {}
    for dependency, provider_id, module_name in (
        ("jinja2", "jinja", "jinja2"),
        ("pyyaml", "yaml", "yaml"),
    ):
        module = _provider_module(provider_id, module_name)
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
    return None if observed == _EXPECTED_CONFORMANCE_DIGESTS[provider_id] else mismatch


@lru_cache(maxsize=1)
def _startup_conformance() -> tuple[str, ...]:
    if _runtime_identity() != ("CPython", 3, 14):
        return ("source_budget_native_runtime_unsupported",)
    expected_dependencies = {"jinja2": 3, "pyyaml": 6}
    try:
        observed = _dependency_majors()
    except _ProviderError as exc:
        return (str(exc),)
    for dependency in sorted(expected_dependencies):
        if observed.get(dependency) != expected_dependencies[dependency]:
            return (f"source_budget_native_dependency_major_mismatch:{dependency}",)
    return tuple(
        sorted(
            {
                gap
                for provider_id in _PROVIDER_IDS
                if (gap := _conformance_gap(provider_id)) is not None
            }
        )
    )


def _provider_metrics(provider_id: str) -> tuple[tuple[str, str], ...]:
    if provider_id in _STRUCTURED_PROVIDERS:
        return _STRUCTURED_METRICS
    if provider_id in {"python", "shell"}:
        return _LEXICAL_METRICS
    if provider_id == "jinja":
        return (
            ("template_dynamic_bytes", "template_dynamic_byte"),
            ("template_dynamic_units", "template_dynamic_unit"),
            ("template_static_bytes", "template_static_byte"),
        )
    return (("normalized_bytes", "normalized_byte"),)


def _provider_normalization(provider_id: str) -> tuple[str, str]:
    if provider_id in _STRUCTURED_PROVIDERS:
        return "structured-scalars", "1"
    return {
        "jinja": "jinja-dynamic-static",
        "python": "python-source",
        "shell": "shell-source",
    }.get(provider_id, "utf8-newline"), "1"


def _provider_descriptor(provider_id: str) -> dict[str, object]:
    parser_id, parser_version = _PROVIDER_PARSERS[provider_id].split("|")
    normalization_id, normalization_version = _provider_normalization(provider_id)
    corpus_digest = hashlib.sha256(_CONFORMANCE_CASES[provider_id]).hexdigest()
    execution_mode, max_carrier_bytes, _, _ = parser_execution_contract(parser_id)
    return {
        "algorithm_rules": _PROVIDER_RULES[provider_id].split("|"),
        "canonical_runtime": _CANONICAL_RUNTIME,
        "conformance": {
            "corpus_digest": corpus_digest,
            "expected_output_digest": _EXPECTED_CONFORMANCE_DIGESTS[provider_id],
        },
        "dependencies": dict(_PROVIDER_DEPENDENCIES.get(provider_id, {})),
        "execution": execution_descriptor(execution_mode, max_carrier_bytes).model_dump(
            mode="json"
        ),
        "metrics": [
            {"metric_id": metric_id, "unit": unit}
            for metric_id, unit in _provider_metrics(provider_id)
        ],
        "normalization": {"id": normalization_id, "version": normalization_version},
        "parser": {"id": parser_id, "version": parser_version},
        "provider_id": provider_id,
        "schema": "ethos-source-budget-native-provider-v2",
    }


def _provider_grammar_digest(provider_id: str) -> str:
    encoded = _canonical_json_bytes(_provider_descriptor(provider_id))
    return hashlib.sha256(encoded).hexdigest()


def _provider_id_for_contract(contract: MetricContract) -> str | None:
    for provider_id in _PROVIDER_IDS:
        parser_id = _PROVIDER_PARSERS[provider_id].split("|", 1)[0]
        if (
            f"{contract.parser_id}|{contract.parser_version}" == _PROVIDER_PARSERS[provider_id]
            and contract.grammar_digest == _provider_grammar_digest(provider_id)
            and (contract.normalization_id, contract.normalization_version)
            == _provider_normalization(provider_id)
            and (contract.metric_id, contract.unit) in _provider_metrics(provider_id)
            and (
                contract.execution_mode,
                contract.max_carrier_bytes,
                contract.execution_contract_id,
                contract.execution_contract_digest,
            )
            == parser_execution_contract(parser_id)
        ):
            return provider_id
    return None


def _conformance_output_digest(provider_id: str) -> str:
    text = _normalize_text(_CONFORMANCE_CASES[provider_id])
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


def _measure_provider(provider_id: str, text: str) -> tuple[bytes, dict[tuple[str, str], int]]:
    with _ProviderBoundary(f"source_budget_native_parse_failed:{provider_id}"):
        if provider_id in {"utf8-control", "utf8-footprint"}:
            stream = text.encode()
            return stream, {("normalized_bytes", "normalized_byte"): len(stream)}
        if provider_id == "python":
            return _measure_python(text)
        if provider_id == "jinja":
            return _measure_jinja(text)
        if provider_id == "shell":
            return _measure_lexical(shell_tokens(text))
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
    stream = b"".join(_frame(kind.encode(), spelling.encode("utf-8")) for kind, spelling in tokens)
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
        _frame(kind.encode(), value.encode("utf-8")) for kind, value in static_tokens
    )
    stream = _frame(b"dynamic", dynamic_payload) + _frame(b"static", static_payload)
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


def _frame(label: bytes, payload: bytes) -> bytes:
    return label + b":" + str(len(payload)).encode() + b":" + payload


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
