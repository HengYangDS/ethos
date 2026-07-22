from __future__ import annotations

import hashlib
import json
from typing import cast

import pytest

from ethos_core.contracts.source_budget.measurement.execution import ExecutionDescriptor
from ethos_core.contracts.source_budget.measurement.execution import execution_descriptor
from ethos_core.contracts.source_budget.measurement.execution import execution_descriptor_digest
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerResult
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import replay_worker_result
from ethos_core.contracts.source_budget.measurements import MetricValue
from ethos_core.contracts.source_budget.measurements import NativeMeasurement
from ethos_core.contracts.source_budget.metrics import MetricContract

_PROTOCOL_ID = "ethos-source-budget-worker-protocol-v1"
_REQUEST_SCHEMA = "ethos-source-budget-worker-request-v1"
_RESULT_SCHEMA = "ethos-source-budget-worker-result-v1"
_CONTENT = b"first=1; second='two'\n"
_NORMALIZED_DIGEST = hashlib.sha256(b"normalized-python-stream").hexdigest()
_CHILD_WORKER_GAPS = (
    "source_budget_native_carrier_bytes_exceeded",
    "source_budget_native_conformance_mismatch:ini",
    "source_budget_native_conformance_mismatch:jinja",
    "source_budget_native_conformance_mismatch:json",
    "source_budget_native_conformance_mismatch:python",
    "source_budget_native_conformance_mismatch:shell",
    "source_budget_native_conformance_mismatch:toml",
    "source_budget_native_conformance_mismatch:yaml",
    "source_budget_native_contract_invalid",
    "source_budget_native_dependency_major_mismatch:jinja2",
    "source_budget_native_dependency_major_mismatch:pyyaml",
    "source_budget_native_execution_contract_invalid",
    "source_budget_native_parse_failed:ini",
    "source_budget_native_parse_failed:jinja",
    "source_budget_native_parse_failed:json",
    "source_budget_native_parse_failed:python",
    "source_budget_native_parse_failed:shell",
    "source_budget_native_parse_failed:toml",
    "source_budget_native_parse_failed:yaml",
    "source_budget_native_provider_signature_mismatch",
    "source_budget_native_provider_unavailable:ini",
    "source_budget_native_provider_unavailable:jinja",
    "source_budget_native_provider_unavailable:json",
    "source_budget_native_provider_unavailable:python",
    "source_budget_native_provider_unavailable:shell",
    "source_budget_native_provider_unavailable:toml",
    "source_budget_native_provider_unavailable:yaml",
    "source_budget_native_resource_exhausted",
    "source_budget_native_runtime_unsupported",
    "source_budget_native_text_embedded_bom",
    "source_budget_native_text_invalid_utf8",
)
_PARENT_WORKER_GAPS = (
    "source_budget_worker_failed",
    "source_budget_worker_isolation_unsupported",
    "source_budget_worker_output_exceeded",
    "source_budget_worker_protocol_invalid",
    "source_budget_worker_resource_exhausted",
    "source_budget_worker_timeout",
    "source_budget_worker_unavailable",
)


def _canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _domain_digest(kind: str, payload: object) -> str:
    return _sha256({"kind": kind, "schema_version": 1, "payload": payload})


def _isolated_execution_descriptor() -> ExecutionDescriptor:
    return execution_descriptor("isolated_worker_v1", 65536)


def _execution_payload() -> dict[str, object]:
    return _isolated_execution_descriptor().model_dump(mode="json", by_alias=True)


def _provider_descriptor() -> dict[str, object]:
    return {
        "algorithm_rules": [
            "ast-syntax-guard",
            "significant-token-count",
            "type-and-spelling-frames",
        ],
        "canonical_runtime": {"implementation": "CPython", "major": 3, "minor": 14},
        "conformance": {
            "corpus_digest": ("b74bd3249b00e0ff977eb8be46b23497dff54057dbc9fffb1eb2042bf4918921"),
            "expected_output_digest": (
                "ce3459c91f2d4185791ff067dfb52bba4b53930c2c9e8a1b6ffbd1597a561176"
            ),
        },
        "dependencies": {},
        "execution": _execution_payload(),
        "metrics": [
            {"metric_id": "lexical_tokens", "unit": "lexical_token"},
            {"metric_id": "normalized_bytes", "unit": "normalized_byte"},
        ],
        "normalization": {"id": "python-source", "version": "1"},
        "parser": {"id": "python-tokenize", "version": "cpython-3.14+ethos-python-v1"},
        "provider_id": "python",
        "schema": "ethos-source-budget-native-provider-v2",
    }


def _contracts(
    provider_descriptor: dict[str, object] | None = None,
) -> tuple[MetricContract, ...]:
    provider = _provider_descriptor() if provider_descriptor is None else provider_descriptor
    common: dict[str, object] = {
        "contract_version": 4,
        "carrier_role": "authored_behavioral_source",
        "metric_profile": "python-source-v2",
        "parser_id": "python-tokenize",
        "parser_version": "cpython-3.14+ethos-python-v1",
        "grammar_digest": _sha256(provider),
        "normalization_id": "python-source",
        "normalization_version": "1",
        "aggregation": "sum",
        "non_compensable": True,
        "execution_mode": "isolated_worker_v1",
        "max_carrier_bytes": 65536,
        "execution_contract_id": "ethos-source-budget-execution:isolated-worker-v1",
        "execution_contract_digest": _sha256(_execution_payload()),
    }
    return tuple(
        MetricContract.model_validate(common | item)
        for item in (
            {
                "contract_id": "python-source-v2:lexical_tokens",
                "metric_id": "lexical_tokens",
                "unit": "lexical_token",
            },
            {
                "contract_id": "python-source-v2:normalized_bytes",
                "metric_id": "normalized_bytes",
                "unit": "normalized_byte",
            },
        )
    )


def _values() -> tuple[MetricValue, ...]:
    return (
        MetricValue(
            contract_id="python-source-v2:lexical_tokens",
            metric_id="lexical_tokens",
            unit="lexical_token",
            value=7,
        ),
        MetricValue(
            contract_id="python-source-v2:normalized_bytes",
            metric_id="normalized_bytes",
            unit="normalized_byte",
            value=19,
        ),
    )


def _expected_request_payload(contracts: tuple[MetricContract, ...]) -> dict[str, object]:
    contract_payloads = [item.model_dump(mode="json") for item in contracts]
    payload: dict[str, object] = {
        "schema": _REQUEST_SCHEMA,
        "protocol_id": _PROTOCOL_ID,
        "contracts": contract_payloads,
        "content_sha256": hashlib.sha256(_CONTENT).hexdigest(),
        "resolved_contracts_digest": _domain_digest(
            "resolved_metric_contracts",
            contract_payloads,
        ),
        "provider_digest": _sha256(_provider_descriptor()),
        "execution_contract_digest": _sha256(_execution_payload()),
    }
    payload["request_digest"] = _sha256(payload)
    return payload


def _resign_request_payload(payload: dict[str, object]) -> None:
    unsigned = {key: value for key, value in payload.items() if key != "request_digest"}
    payload["request_digest"] = _sha256(unsigned)


def _gap_result_payload() -> tuple[WorkerRequest, dict[str, object]]:
    request = WorkerRequest.create(
        content=_CONTENT,
        contracts=_contracts(),
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )
    result = WorkerResult.from_gap(
        request=request,
        gap="source_budget_native_contract_invalid",
    )
    return request, result.model_dump(mode="python", by_alias=True)


def test_worker_request_create_canonicalizes_contract_order_at_exact_ceiling() -> None:
    content = b"x" * 65536
    contracts = _contracts()
    forward = WorkerRequest.create(
        content=content,
        contracts=contracts,
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )

    reversed_request = WorkerRequest.create(
        content=content,
        contracts=tuple(reversed(contracts)),
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )

    assert reversed_request == forward


@pytest.mark.parametrize("case", ["bytearray", "list", "empty", "item", "forged"])
def test_worker_request_create_rejects_noncanonical_inputs(case: str) -> None:
    content: bytes = _CONTENT
    contracts: tuple[MetricContract, ...] = _contracts()
    if case == "bytearray":
        content = cast("bytes", bytearray(content))
    elif case == "list":
        contracts = cast("tuple[MetricContract, ...]", list(contracts))
    elif case == "empty":
        contracts = ()
    elif case == "item":
        contracts = cast("tuple[MetricContract, ...]", (object(),))
    else:
        contracts = (MetricContract.model_construct(contract_id="forged"),)

    with pytest.raises(ValueError, match=r"bytes|canonical|contracts"):
        WorkerRequest.create(
            content=content,
            contracts=contracts,
            provider_descriptor=_provider_descriptor(),
            execution_descriptor=_isolated_execution_descriptor(),
        )


def test_worker_request_create_rejects_content_above_execution_ceiling() -> None:
    with pytest.raises(ValueError, match=r"bytes|carrier|ceiling"):
        WorkerRequest.create(
            content=b"x" * 65537,
            contracts=_contracts(),
            provider_descriptor=_provider_descriptor(),
            execution_descriptor=_isolated_execution_descriptor(),
        )


@pytest.mark.parametrize(
    ("field", "resign", "match"),
    [
        pytest.param("resolved_contracts_digest", "outer", "resolved", id="resolved"),
        pytest.param("provider_digest", "outer", "provider", id="provider"),
        pytest.param("execution_contract_digest", "outer", "execution", id="execution"),
        pytest.param("request_digest", "none", "request digest", id="request"),
    ],
)
def test_worker_request_wire_rejects_digest_drift(
    field: str,
    resign: str,
    match: str,
) -> None:
    request = WorkerRequest.create(
        content=_CONTENT,
        contracts=_contracts(),
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )
    payload = request.model_dump(mode="python", by_alias=True)
    assert WorkerRequest.model_validate(payload) == request

    payload[field] = "f" * 64
    if resign == "outer":
        _resign_request_payload(payload)

    with pytest.raises(ValueError, match=match):
        WorkerRequest.model_validate(payload)


def test_worker_request_wire_rejects_coherent_bounded_contract_tuple() -> None:
    request = WorkerRequest.create(
        content=_CONTENT,
        contracts=_contracts(),
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )
    payload = request.model_dump(mode="python", by_alias=True)
    assert WorkerRequest.model_validate(payload) == request

    bounded_descriptor = execution_descriptor("bounded_in_process_v1", 65536)
    bounded_digest = execution_descriptor_digest(bounded_descriptor)
    bounded_contracts = tuple(
        MetricContract.model_validate(
            item.model_dump(mode="python")
            | {
                "execution_mode": "bounded_in_process_v1",
                "execution_contract_id": bounded_descriptor.execution_contract_id,
                "execution_contract_digest": bounded_digest,
            }
        )
        for item in _contracts()
    )
    contract_payloads = [item.model_dump(mode="json") for item in bounded_contracts]
    payload["contracts"] = contract_payloads
    payload["resolved_contracts_digest"] = _domain_digest(
        "resolved_metric_contracts",
        contract_payloads,
    )
    payload["execution_contract_digest"] = bounded_digest
    _resign_request_payload(payload)

    with pytest.raises(ValueError, match="execution"):
        WorkerRequest.model_validate(payload)


def test_worker_protocol_happy_path_binds_and_replays_typed_results() -> None:
    contracts = _contracts()
    request = WorkerRequest.create(
        content=_CONTENT,
        contracts=contracts,
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )
    expected_request = _expected_request_payload(contracts)
    assert request.model_dump(mode="json", by_alias=True) == expected_request

    native = NativeMeasurement.create(
        content_sha256=expected_request["content_sha256"],
        normalized_digest=_NORMALIZED_DIGEST,
        contracts=contracts,
        values=_values(),
    )
    success = WorkerResult.from_measurement(request=request, measurement=native)
    echoed = {
        name: expected_request[name]
        for name in (
            "content_sha256",
            "resolved_contracts_digest",
            "provider_digest",
            "execution_contract_digest",
            "request_digest",
        )
    }
    assert success.model_dump(mode="json", by_alias=True) == {
        "schema": _RESULT_SCHEMA,
        "protocol_id": _PROTOCOL_ID,
        **echoed,
        "success": {
            "normalized_digest": native.normalized_digest,
            "values": [item.model_dump(mode="json") for item in native.values],
            "measurement_digest": native.measurement_digest,
        },
        "gap": None,
    }
    replayed = replay_worker_result(request, success)
    assert type(replayed) is NativeMeasurement
    assert replayed == native
    assert replayed is not native


def test_worker_result_requires_exact_success_gap_xor() -> None:
    contracts = _contracts()
    request = WorkerRequest.create(
        content=_CONTENT,
        contracts=contracts,
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )
    native = NativeMeasurement.create(
        content_sha256=request.content_sha256,
        normalized_digest=_NORMALIZED_DIGEST,
        contracts=contracts,
        values=_values(),
    )
    success = WorkerResult.from_measurement(request=request, measurement=native)
    assert WorkerResult.model_validate(success.model_dump(mode="python", by_alias=True)) == success

    gap = WorkerResult.from_gap(
        request=request,
        gap="source_budget_native_contract_invalid",
    )
    assert gap.success is None
    assert gap.gap == "source_budget_native_contract_invalid"
    assert WorkerResult.model_validate(gap.model_dump(mode="python", by_alias=True)) == gap
    with pytest.raises(ValueError, match="success"):
        replay_worker_result(request, gap)

    success_payload = success.model_dump(mode="python", by_alias=True)
    gap_payload = gap.model_dump(mode="python", by_alias=True)
    invalid_payloads = (
        gap_payload | {"success": success_payload["success"]},
        gap_payload | {"gap": None},
    )
    for payload in invalid_payloads:
        with pytest.raises(ValueError, match=r"exactly one|success.*gap"):
            WorkerResult.model_validate(payload)


def test_worker_child_gap_allowlist_is_exact_sorted_and_child_only() -> None:
    assert len(_CHILD_WORKER_GAPS) == 31
    assert len(set(_CHILD_WORKER_GAPS)) == 31
    assert tuple(sorted(_CHILD_WORKER_GAPS)) == _CHILD_WORKER_GAPS
    gap_schema = WorkerResult.model_json_schema(by_alias=True)["properties"]["gap"]
    production_gaps = next(item["enum"] for item in gap_schema["anyOf"] if "enum" in item)
    assert tuple(production_gaps) == _CHILD_WORKER_GAPS

    _request, base = _gap_result_payload()
    for gap in _CHILD_WORKER_GAPS:
        result = WorkerResult.model_validate(base | {"gap": gap})
        assert result.gap == gap

    invalid_gaps = (
        "source_budget_native_parse_failed:c4",
        "source_budget_native_dependency_major_mismatch:jinja",
        "source_budget_worker_timeout",
        "source_budget_native_unknown",
        "source_budget_native_contract_invalid:src/example.py",
    )
    for gap in invalid_gaps:
        with pytest.raises(ValueError, match="gap"):
            WorkerResult.model_validate(base | {"gap": gap})


def test_worker_parent_gap_allowlist_is_exact_sorted_and_disjoint() -> None:
    assert len(_PARENT_WORKER_GAPS) == 7
    assert len(set(_PARENT_WORKER_GAPS)) == 7
    assert tuple(sorted(_PARENT_WORKER_GAPS)) == _PARENT_WORKER_GAPS
    assert set(_PARENT_WORKER_GAPS).isdisjoint(_CHILD_WORKER_GAPS)

    _request, base = _gap_result_payload()
    for gap in _PARENT_WORKER_GAPS:
        with pytest.raises(ValueError, match="gap"):
            WorkerResult.model_validate(base | {"gap": gap})


def test_worker_gap_result_echoes_bindings_and_rejects_sensitive_fields() -> None:
    request, payload = _gap_result_payload()
    assert set(payload) == {
        "schema",
        "protocol_id",
        "content_sha256",
        "resolved_contracts_digest",
        "provider_digest",
        "execution_contract_digest",
        "request_digest",
        "success",
        "gap",
    }
    for field in (
        "content_sha256",
        "resolved_contracts_digest",
        "provider_digest",
        "execution_contract_digest",
        "request_digest",
    ):
        assert payload[field] == getattr(request, field)

    with pytest.raises(ValueError, match=r"extra|forbid"):
        WorkerResult.model_validate(payload | {"path": "sensitive"})


@pytest.mark.parametrize(
    "case",
    [
        "echo-pair",
        "success-gap",
        "result-extra",
        "request-extra",
        "request-subclass",
        "request-fields-set",
        "success-extra",
        "reversed-values",
    ],
)
def test_parent_replay_revalidates_untrusted_model_storage(case: str) -> None:
    contracts = _contracts()
    request = WorkerRequest.create(
        content=_CONTENT,
        contracts=contracts,
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )
    native = NativeMeasurement.create(
        content_sha256=request.content_sha256,
        normalized_digest=_NORMALIZED_DIGEST,
        contracts=contracts,
        values=_values(),
    )
    result = WorkerResult.from_measurement(request=request, measurement=native)
    assert replay_worker_result(request, result) == native

    forged_request = request
    forged_result = result
    match = r"canonical|request|result|values|success|gap"
    if case == "echo-pair":
        forged_request = request.model_copy(update={"provider_digest": "f" * 64})
        forged_result = result.model_copy(update={"provider_digest": "f" * 64})
    elif case == "success-gap":
        forged_result = result.model_copy(update={"gap": "source_budget_native_contract_invalid"})
    elif case == "result-extra":
        forged_result = result.model_copy(update={"path": "src/example.py"})
    elif case == "request-extra":
        forged_request = request.model_copy(update={"path": "src/example.py"})
    elif case == "request-subclass":

        class _ForgedRequest(WorkerRequest):
            pass

        forged_request = _ForgedRequest.model_validate(
            request.model_dump(mode="python", by_alias=True)
        )
    elif case == "request-fields-set":
        forged_request = WorkerRequest.model_construct(
            _fields_set={"request_digest"},
            **request.model_dump(mode="python"),
        )
    elif case == "success-extra":
        assert result.success is not None
        forged_success = result.success.model_copy(update={"path": "src/example.py"})
        forged_result = result.model_copy(update={"success": forged_success})
    else:
        assert result.success is not None
        forged_success = result.success.model_copy(
            update={"values": tuple(reversed(result.success.values))}
        )
        forged_result = result.model_copy(update={"success": forged_success})

    with pytest.raises(ValueError, match=match):
        replay_worker_result(forged_request, forged_result)


def test_parent_replay_rejects_a_result_bound_to_another_request() -> None:
    contracts = _contracts()
    descriptor = _isolated_execution_descriptor()
    request_a = WorkerRequest.create(
        content=_CONTENT,
        contracts=contracts,
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=descriptor,
    )
    content_b = b"third=3\n"
    request_b = WorkerRequest.create(
        content=content_b,
        contracts=contracts,
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=descriptor,
    )
    native_b = NativeMeasurement.create(
        content_sha256=hashlib.sha256(content_b).hexdigest(),
        normalized_digest=_NORMALIZED_DIGEST,
        contracts=contracts,
        values=_values(),
    )
    result_b = WorkerResult.from_measurement(request=request_b, measurement=native_b)

    with pytest.raises(ValueError, match="request"):
        replay_worker_result(request_a, result_b)


@pytest.mark.parametrize(
    "field",
    [
        "content_sha256",
        "resolved_contracts_digest",
        "provider_digest",
        "execution_contract_digest",
    ],
)
def test_parent_replay_rejects_forged_request_echo(field: str) -> None:
    contracts = _contracts()
    request = WorkerRequest.create(
        content=_CONTENT,
        contracts=contracts,
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )
    native = NativeMeasurement.create(
        content_sha256=request.content_sha256,
        normalized_digest=_NORMALIZED_DIGEST,
        contracts=contracts,
        values=_values(),
    )
    result = WorkerResult.from_measurement(request=request, measurement=native)
    forged = result.model_copy(update={field: "f" * 64})

    with pytest.raises(ValueError, match=r"request.*binding"):
        replay_worker_result(request, forged)


def test_parent_replay_rejects_forged_child_measurement_digest() -> None:
    contracts = _contracts()
    request = WorkerRequest.create(
        content=_CONTENT,
        contracts=contracts,
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )
    native = NativeMeasurement.create(
        content_sha256=request.content_sha256,
        normalized_digest=_NORMALIZED_DIGEST,
        contracts=contracts,
        values=_values(),
    )
    result = WorkerResult.from_measurement(request=request, measurement=native)
    forged_success = result.success.model_copy(update={"measurement_digest": "f" * 64})
    forged_result = result.model_copy(update={"success": forged_success})

    with pytest.raises(ValueError, match=r"measurement.*digest"):
        replay_worker_result(request, forged_result)


@pytest.mark.parametrize("case", ["provider", "execution", "bounded"])
def test_worker_request_rejects_mismatched_authority(case: str) -> None:
    provider = _provider_descriptor()
    descriptor = _isolated_execution_descriptor()
    match = "provider"
    if case == "provider":
        provider["provider_id"] = "forged-python"
    elif case == "execution":
        descriptor = execution_descriptor("isolated_worker_v1", 32768)
        match = "execution"
    else:
        descriptor = execution_descriptor("bounded_in_process_v1", 65536)
        match = "isolated"

    with pytest.raises(ValueError, match=match):
        WorkerRequest.create(
            content=_CONTENT,
            contracts=_contracts(),
            provider_descriptor=provider,
            execution_descriptor=descriptor,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "execution",
            execution_descriptor("isolated_worker_v1", 32768).model_dump(
                mode="json", by_alias=True
            ),
        ),
        (
            "parser",
            {"id": "json-stdlib", "version": "cpython-3.14+ethos-python-v1"},
        ),
        ("normalization", {"id": "structured-scalars", "version": "1"}),
        (
            "metrics",
            [
                {"metric_id": "semantic_nodes", "unit": "semantic_node"},
                {"metric_id": "normalized_bytes", "unit": "normalized_byte"},
            ],
        ),
    ],
)
def test_worker_request_rejects_provider_descriptor_internal_conflict(
    field: str,
    value: object,
) -> None:
    provider = _provider_descriptor()
    provider[field] = value

    with pytest.raises(ValueError, match="provider"):
        WorkerRequest.create(
            content=_CONTENT,
            contracts=_contracts(provider),
            provider_descriptor=provider,
            execution_descriptor=_isolated_execution_descriptor(),
        )
