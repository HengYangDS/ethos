"""Canonical descriptor for the future source-budget worker protocol."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated
from typing import Literal
from typing import Self
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import TypeAdapter
from pydantic import field_validator
from pydantic import model_validator

import ethos_core.contracts.source_budget.measurement.canonical as canonical
from ethos_core.contracts.source_budget.carriers import JSON_SCHEMA_DRAFT_2020_12
from ethos_core.contracts.source_budget.measurement.execution import ExecutionDescriptor
from ethos_core.contracts.source_budget.measurement.execution import execution_descriptor_digest
from ethos_core.contracts.source_budget.measurements import MetricValue
from ethos_core.contracts.source_budget.measurements import NativeMeasurement
from ethos_core.contracts.source_budget.metrics import MetricContract
from ethos_core.contracts.source_budget.metrics import metric_provider_resource_contract

WORKER_PROTOCOL_ID = "ethos-source-budget-worker-protocol-v1"
_REQUEST_SCHEMA = "ethos-source-budget-worker-request-v1"
_RESULT_SCHEMA = "ethos-source-budget-worker-result-v1"
_CANONICAL_CONTRACTS_ERROR = "worker request contracts must be canonical"
_CANONICAL_PROTOCOL_DESCRIPTOR_ERROR = "worker protocol descriptor must be canonical"
_CANONICAL_VALUES_ERROR = "worker success values must be canonical"
_EXECUTION_CONTRACT_DIGEST_ERROR = "worker request execution contract digest mismatch"
_EXECUTION_DESCRIPTOR_ERROR = "worker request execution descriptor mismatch"
_ISOLATED_EXECUTION_ERROR = "worker request requires an isolated execution descriptor"
_PROTOCOL_INTEGER_ERROR = "worker protocol descriptor integers must be exact"
_PROVIDER_DIGEST_ERROR = "worker request provider digest mismatch"
_PROVIDER_IDENTITY_ERROR = "worker request provider descriptor identity mismatch"
_REQUEST_BINDING_ERROR = "worker result request binding mismatch"
_REQUEST_CARRIER_CEILING_ERROR = "worker request carrier bytes exceed execution ceiling"
_REQUEST_CONTENT_ERROR = "worker request content must be canonical bytes"
_REQUEST_DIGEST_ERROR = "worker request digest mismatch"
_RESOLVED_CONTRACTS_DIGEST_ERROR = "worker request resolved contracts digest mismatch"
_RESULT_SUCCESS_ERROR = "worker result success is required for replay"
_RESULT_XOR_ERROR = "worker result requires exactly one of success or gap"
_SHA256_PATTERN = r"^[a-f0-9]{64}$"
_Sha256 = Annotated[str, Field(pattern=_SHA256_PATTERN)]
_ChildWorkerGap = Literal[
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
]
_CHILD_WORKER_GAP_ADAPTER: TypeAdapter[_ChildWorkerGap] = TypeAdapter(_ChildWorkerGap)


def admit_child_worker_gap(value: str) -> _ChildWorkerGap:
    """Admit one child gap from the finite worker protocol vocabulary."""
    return _CHILD_WORKER_GAP_ADAPTER.validate_python(value)


def _require_exact_contracts(
    contracts: tuple[MetricContract, ...],
) -> tuple[MetricContract, ...]:
    if (
        type(contracts) is not tuple
        or not contracts
        or any(type(item) is not MetricContract for item in contracts)
    ):
        raise ValueError(_CANONICAL_CONTRACTS_ERROR)
    return contracts


def _require_exact_values(values: tuple[MetricValue, ...]) -> tuple[MetricValue, ...]:
    if (
        type(values) is not tuple
        or not values
        or any(type(item) is not MetricValue for item in values)
    ):
        raise ValueError(_CANONICAL_VALUES_ERROR)
    return values


class WorkerProtocolDescriptor(BaseModel):
    """Immutable identity of the bounded worker wire protocol."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )

    schema_id: Literal["ethos-source-budget-worker-protocol-descriptor-v1"] = Field(alias="schema")
    id: Literal["ethos-source-budget-worker-protocol-v1"]
    request_magic: Literal["ESBWREQ1"]
    result_magic: Literal["ESBWRES1"]
    length_encoding: Literal["u32be"]
    header_max_bytes: Literal[32768]
    stdin_max_bytes: Literal[327680]
    result_max_bytes: Literal[65536]
    canonical_json: Literal["utf8-sort-keys-compact-no-duplicates-v1"]

    @field_validator("header_max_bytes", "stdin_max_bytes", "result_max_bytes", mode="before")
    @classmethod
    def validate_exact_integer(cls, value: object) -> object:
        """Reject equal-but-non-integer wire values."""
        if type(value) is not int:
            raise ValueError(_PROTOCOL_INTEGER_ERROR)
        return value


def worker_protocol_descriptor() -> WorkerProtocolDescriptor:
    """Return the complete worker-protocol descriptor without runtime behavior."""
    return WorkerProtocolDescriptor(
        schema="ethos-source-budget-worker-protocol-descriptor-v1",
        id=WORKER_PROTOCOL_ID,
        request_magic="ESBWREQ1",
        result_magic="ESBWRES1",
        length_encoding="u32be",
        header_max_bytes=32768,
        stdin_max_bytes=327680,
        result_max_bytes=65536,
        canonical_json="utf8-sort-keys-compact-no-duplicates-v1",
    )


def worker_protocol_descriptor_digest(descriptor: WorkerProtocolDescriptor) -> str:
    """Return canonical compact sorted-key JSON SHA-256 for one descriptor."""
    if type(descriptor) is not WorkerProtocolDescriptor:
        raise ValueError(_CANONICAL_PROTOCOL_DESCRIPTOR_ERROR)
    expected_fields = set(WorkerProtocolDescriptor.model_fields)
    if set(vars(descriptor)) != expected_fields or descriptor.model_fields_set != expected_fields:
        raise ValueError(_CANONICAL_PROTOCOL_DESCRIPTOR_ERROR)
    canonical = WorkerProtocolDescriptor.model_validate(descriptor.model_dump(mode="python"))
    encoded = json.dumps(
        canonical.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class WorkerRequest(BaseModel):
    """Path-blind canonical request for one admitted carrier."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )

    schema_id: Literal["ethos-source-budget-worker-request-v1"] = Field(alias="schema")
    protocol_id: Literal["ethos-source-budget-worker-protocol-v1"]
    contracts: tuple[MetricContract, ...] = Field(min_length=1)
    content_sha256: _Sha256
    resolved_contracts_digest: _Sha256
    provider_digest: _Sha256
    execution_contract_digest: _Sha256
    request_digest: _Sha256

    @field_validator("contracts")
    @classmethod
    def _validate_exact_contracts(
        cls,
        contracts: tuple[MetricContract, ...],
    ) -> tuple[MetricContract, ...]:
        """Reject non-canonical metric-contract model instances."""
        return _require_exact_contracts(contracts)

    @model_validator(mode="after")
    def _validate_contract_digests(self) -> Self:
        """Require all contract-owned request digests to match typed contracts."""
        contracts = self.contracts
        if self.resolved_contracts_digest != canonical.resolved_model_digest(contracts):
            raise ValueError(_RESOLVED_CONTRACTS_DIGEST_ERROR)
        if {item.grammar_digest for item in contracts} != {self.provider_digest}:
            raise ValueError(_PROVIDER_DIGEST_ERROR)
        execution = metric_provider_resource_contract(contracts)
        if execution[0] != "isolated_worker_v1" or execution[3] != self.execution_contract_digest:
            raise ValueError(_EXECUTION_CONTRACT_DIGEST_ERROR)
        unsigned = self.model_dump(
            mode="json",
            by_alias=True,
            exclude={"request_digest"},
        )
        if self.request_digest != _canonical_sha256(unsigned):
            raise ValueError(_REQUEST_DIGEST_ERROR)
        return self

    @classmethod
    def create(
        cls,
        *,
        content: bytes,
        contracts: tuple[MetricContract, ...],
        provider_descriptor: dict[str, object],
        execution_descriptor: ExecutionDescriptor,
    ) -> Self:
        """Bind admitted bytes and typed provider/execution descriptors."""
        if type(content) is not bytes:
            raise ValueError(_REQUEST_CONTENT_ERROR)
        _require_exact_contracts(contracts)
        expected_execution = metric_provider_resource_contract(contracts)
        ordered = tuple(
            sorted(contracts, key=lambda item: (item.metric_id, item.unit, item.contract_id))
        )
        provider_digest = _canonical_sha256(provider_descriptor)
        execution_digest = execution_descriptor_digest(execution_descriptor)
        if execution_descriptor.execution_mode != "isolated_worker_v1":
            raise ValueError(_ISOLATED_EXECUTION_ERROR)
        actual_execution = (
            execution_descriptor.execution_mode,
            execution_descriptor.max_carrier_bytes,
            execution_descriptor.execution_contract_id,
            execution_digest,
        )
        if actual_execution != expected_execution:
            raise ValueError(_EXECUTION_DESCRIPTOR_ERROR)
        if len(content) > execution_descriptor.max_carrier_bytes:
            raise ValueError(_REQUEST_CARRIER_CEILING_ERROR)
        first_contract = ordered[0]
        expected_provider_identity = {
            "execution": execution_descriptor.model_dump(mode="json", by_alias=True),
            "parser": {
                "id": first_contract.parser_id,
                "version": first_contract.parser_version,
            },
            "normalization": {
                "id": first_contract.normalization_id,
                "version": first_contract.normalization_version,
            },
            "metrics": [{"metric_id": item.metric_id, "unit": item.unit} for item in ordered],
        }
        if any(
            provider_descriptor.get(field) != expected
            for field, expected in expected_provider_identity.items()
        ):
            raise ValueError(_PROVIDER_IDENTITY_ERROR)
        resolved_digest = canonical.resolved_model_digest(ordered)
        content_digest = hashlib.sha256(content).hexdigest()
        payload: dict[str, object] = {
            "schema": _REQUEST_SCHEMA,
            "protocol_id": WORKER_PROTOCOL_ID,
            "contracts": tuple(item.model_dump(mode="python") for item in ordered),
            "content_sha256": content_digest,
            "resolved_contracts_digest": resolved_digest,
            "provider_digest": provider_digest,
            "execution_contract_digest": execution_digest,
        }
        payload["request_digest"] = _canonical_sha256(payload)
        return cls.model_validate(payload)


class _WorkerSuccess(BaseModel):
    """Typed child output sufficient for trusted parent reconstruction."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    normalized_digest: _Sha256
    values: tuple[MetricValue, ...] = Field(min_length=1)
    measurement_digest: _Sha256

    @field_validator("values")
    @classmethod
    def _validate_exact_values(
        cls,
        values: tuple[MetricValue, ...],
    ) -> tuple[MetricValue, ...]:
        """Reject non-canonical metric-value model instances."""
        return _require_exact_values(values)


def _request_bindings(request: WorkerRequest) -> dict[str, str]:
    """Return the five request digests echoed by every worker result."""
    return {
        "content_sha256": request.content_sha256,
        "resolved_contracts_digest": request.resolved_contracts_digest,
        "provider_digest": request.provider_digest,
        "execution_contract_digest": request.execution_contract_digest,
        "request_digest": request.request_digest,
    }


class WorkerResult(BaseModel):
    """One typed worker success bound to its originating request."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
        json_schema_extra={
            "oneOf": [
                {
                    "properties": {
                        "success": {"not": {"type": "null"}},
                        "gap": {"type": "null"},
                    }
                },
                {
                    "properties": {
                        "success": {"type": "null"},
                        "gap": {"not": {"type": "null"}},
                    }
                },
            ]
        },
    )

    schema_id: Literal["ethos-source-budget-worker-result-v1"] = Field(alias="schema")
    protocol_id: Literal["ethos-source-budget-worker-protocol-v1"]
    content_sha256: _Sha256
    resolved_contracts_digest: _Sha256
    provider_digest: _Sha256
    execution_contract_digest: _Sha256
    request_digest: _Sha256
    success: _WorkerSuccess | None
    gap: _ChildWorkerGap | None

    @model_validator(mode="after")
    def _validate_success_gap_xor(self) -> Self:
        """Require exactly one typed success or admitted child gap."""
        if (self.success is None) == (self.gap is None):
            raise ValueError(_RESULT_XOR_ERROR)
        return self

    @classmethod
    def from_measurement(
        cls,
        *,
        request: WorkerRequest,
        measurement: NativeMeasurement,
    ) -> Self:
        """Return one typed success bound to the request digests."""
        return cls(
            schema=_RESULT_SCHEMA,
            protocol_id=WORKER_PROTOCOL_ID,
            **_request_bindings(request),
            success=_WorkerSuccess(
                normalized_digest=measurement.normalized_digest,
                values=measurement.values,
                measurement_digest=measurement.measurement_digest,
            ),
            gap=None,
        )

    @classmethod
    def from_gap(
        cls,
        *,
        request: WorkerRequest,
        gap: _ChildWorkerGap,
    ) -> Self:
        """Return one typed child gap bound to the request digests."""
        return cls(
            schema=_RESULT_SCHEMA,
            protocol_id=WORKER_PROTOCOL_ID,
            **_request_bindings(request),
            success=None,
            gap=gap,
        )


def _require_canonical_model_storage(
    value: BaseModel,
    model_type: type[BaseModel],
    label: str,
) -> None:
    """Reject forged outer model storage before reading nested values."""
    expected_fields = set(model_type.model_fields)
    if (
        type(value) is not model_type
        or set(vars(value)) != expected_fields
        or value.model_fields_set != expected_fields
    ):
        message = f"worker {label} model storage must be canonical"
        raise ValueError(message)


def _model_payload(value: BaseModel) -> dict[str, object]:
    """Dump one model only after its complete storage has been admitted."""
    return cast(
        "dict[str, object]",
        value.model_dump(mode="python", by_alias=True, warnings="error"),
    )


def replay_worker_result(request: WorkerRequest, result: WorkerResult) -> NativeMeasurement:
    """Reconstruct one native measurement from trusted request contracts."""
    _require_canonical_model_storage(request, WorkerRequest, "request")
    _require_canonical_model_storage(result, WorkerResult, "result")
    _require_exact_contracts(request.contracts)
    stored_success = result.success
    if stored_success is not None:
        _require_canonical_model_storage(stored_success, _WorkerSuccess, "success")
        _require_exact_values(stored_success.values)
    request_payload = _model_payload(request)
    result_payload = _model_payload(result)
    request = WorkerRequest.model_validate(request_payload)
    result = WorkerResult.model_validate(result_payload)
    if (
        result.content_sha256,
        result.resolved_contracts_digest,
        result.provider_digest,
        result.execution_contract_digest,
        result.request_digest,
    ) != (
        request.content_sha256,
        request.resolved_contracts_digest,
        request.provider_digest,
        request.execution_contract_digest,
        request.request_digest,
    ):
        raise ValueError(_REQUEST_BINDING_ERROR)
    success = result.success
    if success is None:
        raise ValueError(_RESULT_SUCCESS_ERROR)
    return NativeMeasurement.model_validate(
        {
            "content_sha256": request.content_sha256,
            "normalized_digest": success.normalized_digest,
            "contracts": request.contracts,
            "resolved_contracts_digest": request.resolved_contracts_digest,
            "values": success.values,
            "measurement_digest": success.measurement_digest,
        }
    )


def worker_protocol_json_schema() -> dict[str, object]:
    """Generate the published worker request/result JSON Schema."""
    schema = TypeAdapter(WorkerRequest | WorkerResult).json_schema(by_alias=True)
    return {
        "$schema": JSON_SCHEMA_DRAFT_2020_12,
        **schema,
        "title": "ETHOS Source Budget Worker Protocol",
    }


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
