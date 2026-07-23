"""Parser-free provider identity for native source measurement."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Never

from pydantic import BaseModel
from pydantic import ValidationError

from ethos_core.contracts.source_budget.measurement.execution import execution_descriptor
from ethos_core.contracts.source_budget.measurement.execution import parser_execution_contract
from ethos_core.contracts.source_budget.metrics import MetricContract
from ethos_core.contracts.source_budget.metrics import admit_resolved_metric_contracts

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.measurement.execution import ExecutionDescriptor
    from ethos_core.contracts.source_budget.metrics import MetricContractSet

_CANONICAL_RUNTIME = {"implementation": "CPython", "major": 3, "minor": 14}
_METRIC_CONTRACT_VERSION = 4
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


BOUNDED_PARSER_IDS = frozenset({"utf8-footprint", "utf8-control", "diagram-contract"})
ISOLATED_PARSER_IDS = frozenset(
    {
        "python-tokenize",
        "json-stdlib",
        "tomllib",
        "pyyaml-safe",
        "configparser",
        "jinja2",
        "shell-lexical",
    }
)
BOUNDED_PROVIDER_IDS = frozenset({"c4", "utf8-control", "utf8-footprint"})
ISOLATED_PROVIDER_IDS = frozenset({"ini", "jinja", "json", "python", "shell", "toml", "yaml"})


@dataclass(frozen=True, slots=True)
class ResolvedNativeProvider:
    """One exact canonical provider and execution resolution."""

    provider_id: str
    contracts: tuple[MetricContract, ...]
    provider_descriptor: dict[str, object]
    execution_descriptor: ExecutionDescriptor


def resolve_native_provider(
    contracts: tuple[MetricContract, ...],
    registry: MetricContractSet,
) -> ResolvedNativeProvider:
    """Resolve one registry-declared contract vector to its static provider."""
    admitted = _admit_contract_storage(contracts)
    try:
        admitted = admit_resolved_metric_contracts(admitted, registry)
    except MemoryError:
        raise
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        _error("source_budget_native_provider_signature_mismatch")
    return _resolve_admitted_provider(admitted)


def admit_resolved_native_provider(
    provider: ResolvedNativeProvider,
    registry: MetricContractSet,
) -> ResolvedNativeProvider:
    """Revalidate one resolved provider without replacing its identity."""
    if type(provider) is not ResolvedNativeProvider:
        _error("source_budget_native_contract_invalid")
    try:
        admitted = _admit_contract_storage(provider.contracts)
        admitted = admit_resolved_metric_contracts(admitted, registry)
        provider_id = _resolved_provider_id(admitted)
        _require_exact_provider_vector(provider_id, admitted)
        parser_id = admitted[0].parser_id
        execution = parser_execution_contract(parser_id)
        expected_execution = execution_descriptor(execution[0], execution[1])
        expected_provider = provider_descriptor(provider_id)
    except (AttributeError, IndexError, KeyError, RuntimeError, TypeError, ValueError):
        _error("source_budget_native_provider_signature_mismatch")
    if (
        type(provider.provider_id) is not str
        or provider.provider_id != provider_id
        or provider.contracts != admitted
        or type(provider.provider_descriptor) is not dict
        or provider.provider_descriptor != expected_provider
        or type(provider.execution_descriptor) is not type(expected_execution)
        or provider.execution_descriptor != expected_execution
    ):
        _error("source_budget_native_provider_signature_mismatch")
    return provider


def revalidate_worker_provider(
    contracts: tuple[MetricContract, ...],
) -> ResolvedNativeProvider:
    """Revalidate the provider signature already bound by a parent request."""
    return _resolve_admitted_provider(_admit_contract_storage(contracts))


def _resolve_admitted_provider(
    admitted: tuple[MetricContract, ...],
) -> ResolvedNativeProvider:
    provider_id = _resolved_provider_id(admitted)
    _require_exact_provider_vector(provider_id, admitted)
    parser_id = admitted[0].parser_id
    execution = parser_execution_contract(parser_id)
    descriptor = execution_descriptor(execution[0], execution[1])
    return ResolvedNativeProvider(
        provider_id=provider_id,
        contracts=admitted,
        provider_descriptor=provider_descriptor(provider_id),
        execution_descriptor=descriptor,
    )


def _resolved_provider_id(contracts: tuple[MetricContract, ...]) -> str:
    try:
        provider_ids = tuple(_provider_id_for_contract(item) for item in contracts)
    except MemoryError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError):
        _error("source_budget_native_contract_invalid")
    provider_id = provider_ids[0]
    if provider_id is None or any(item != provider_id for item in provider_ids):
        _error("source_budget_native_provider_signature_mismatch")
    return provider_id


def _require_exact_provider_vector(
    provider_id: str,
    contracts: tuple[MetricContract, ...],
) -> None:
    try:
        expected_coordinates = tuple(sorted(provider_metrics(provider_id)))
        actual_coordinates = tuple((item.metric_id, item.unit) for item in contracts)
        contract_ids = tuple(item.contract_id for item in contracts)
        profile_count = len({item.metric_profile for item in contracts})
        carrier_role_count = len({item.carrier_role for item in contracts})
    except MemoryError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError):
        _error("source_budget_native_contract_invalid")
    if (
        actual_coordinates != expected_coordinates
        or len(set(contract_ids)) != len(contract_ids)
        or any(item.contract_id != f"{item.metric_profile}:{item.metric_id}" for item in contracts)
        or profile_count != 1
        or carrier_role_count != 1
    ):
        _error("source_budget_native_provider_signature_mismatch")


def provider_descriptor(provider_id: str) -> dict[str, object]:
    """Return the canonical provider descriptor v2 payload."""
    parser_id, parser_version = _PROVIDER_PARSERS[provider_id].split("|")
    normalization_id, normalization_version = provider_normalization(provider_id)
    corpus_digest = hashlib.sha256(_CONFORMANCE_CASES[provider_id]).hexdigest()
    execution_mode, max_carrier_bytes, _, _ = parser_execution_contract(parser_id)
    return {
        "algorithm_rules": _PROVIDER_RULES[provider_id].split("|"),
        "canonical_runtime": dict(_CANONICAL_RUNTIME),
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
            for metric_id, unit in provider_metrics(provider_id)
        ],
        "normalization": {"id": normalization_id, "version": normalization_version},
        "parser": {"id": parser_id, "version": parser_version},
        "provider_id": provider_id,
        "schema": "ethos-source-budget-native-provider-v2",
    }


def provider_grammar_digest(provider_id: str) -> str:
    """Return the canonical provider descriptor SHA-256."""
    return hashlib.sha256(_canonical_json_bytes(provider_descriptor(provider_id))).hexdigest()


def provider_metrics(provider_id: str) -> tuple[tuple[str, str], ...]:
    """Return the complete ordered metric coordinates for one provider."""
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


def provider_normalization(provider_id: str) -> tuple[str, str]:
    """Return the exact normalization identity for one provider."""
    if provider_id in _STRUCTURED_PROVIDERS:
        return "structured-scalars", "1"
    return {
        "jinja": "jinja-dynamic-static",
        "python": "python-source",
        "shell": "shell-source",
    }.get(provider_id, "utf8-newline"), "1"


def provider_conformance_content(provider_id: str) -> bytes:
    """Return the immutable conformance corpus for one provider."""
    return _CONFORMANCE_CASES[provider_id]


def provider_expected_conformance_digest(provider_id: str) -> str:
    """Return the reviewed conformance output digest for one provider."""
    return _EXPECTED_CONFORMANCE_DIGESTS[provider_id]


def provider_dependencies(provider_id: str) -> dict[str, int]:
    """Return exact dependency-major requirements for one provider."""
    return dict(_PROVIDER_DEPENDENCIES.get(provider_id, {}))


def provider_ids() -> tuple[str, ...]:
    """Return all provider ids in canonical order."""
    return _PROVIDER_IDS


def _admit_contract_storage(
    contracts: tuple[MetricContract, ...],
) -> tuple[MetricContract, ...]:
    if type(contracts) is not tuple or not contracts:
        _error("source_budget_native_contract_invalid")
    fields = set(MetricContract.model_fields)
    try:
        if any(
            type(item) is not MetricContract
            or set(vars(item)) != fields
            or item.model_fields_set != fields
            for item in contracts
        ):
            _error("source_budget_native_contract_invalid")
    except MemoryError:
        raise
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        _error("source_budget_native_contract_invalid")
    canonical = _revalidate_contracts(contracts)
    ordered = tuple(
        sorted(canonical, key=lambda item: (item.metric_id, item.unit, item.contract_id))
    )
    if canonical != ordered:
        _error("source_budget_native_contract_invalid")
    return canonical


def _revalidate_contracts(
    contracts: tuple[MetricContract, ...],
) -> tuple[MetricContract, ...]:
    try:
        fields = set(MetricContract.model_fields)
        return tuple(_canonical_contract(_contract_payload(item, fields)) for item in contracts)
    except MemoryError:
        raise
    except ValueError as exc:
        if str(exc) == "source_budget_native_provider_signature_mismatch":
            raise
        _error("source_budget_native_contract_invalid")
    except (AttributeError, KeyError, RuntimeError, TypeError):
        _error("source_budget_native_contract_invalid")


def _contract_payload(
    contract: MetricContract,
    fields: set[str],
) -> dict[str, object]:
    payload = BaseModel.model_dump(
        contract,
        mode="python",
        by_alias=True,
        warnings="error",
    )
    integer_fields = {"contract_version", "max_carrier_bytes"}
    string_fields = fields - integer_fields - {"non_compensable"}
    if (
        set(payload) != fields
        or any(type(payload[field]) is not int for field in integer_fields)
        or type(payload["non_compensable"]) is not bool
        or any(type(payload[field]) is not str for field in string_fields)
    ):
        _error("source_budget_native_contract_invalid")
    return payload


def _canonical_contract(payload: dict[str, object]) -> MetricContract:
    try:
        return MetricContract.model_validate(payload)
    except ValidationError as exc:
        if any(
            error["loc"] == () and "execution identity mismatch" in error["msg"]
            for error in exc.errors()
        ):
            _error("source_budget_native_provider_signature_mismatch")
        raise


def _provider_id_for_contract(contract: MetricContract) -> str | None:
    for provider_id in _PROVIDER_IDS:
        parser_id = _PROVIDER_PARSERS[provider_id].split("|", 1)[0]
        if (
            contract.contract_version == _METRIC_CONTRACT_VERSION
            and contract.aggregation == "sum"
            and contract.non_compensable is True
            and f"{contract.parser_id}|{contract.parser_version}" == _PROVIDER_PARSERS[provider_id]
            and contract.grammar_digest == provider_grammar_digest(provider_id)
            and (contract.normalization_id, contract.normalization_version)
            == provider_normalization(provider_id)
            and (contract.metric_id, contract.unit) in provider_metrics(provider_id)
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


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _error(message: str) -> Never:
    raise ValueError(message)
