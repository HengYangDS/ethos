"""Canonical descriptor for the future source-budget worker protocol."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Literal
from typing import Self
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import SerializeAsAny
from pydantic import field_validator
from pydantic import model_validator

import ethos_core.contracts.source_budget.measurement.canonical as canonical

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.measurement.execution import ExecutionDescriptor
    from ethos_core.contracts.source_budget.measurements import MetricValue
    from ethos_core.contracts.source_budget.measurements import NativeMeasurement
    from ethos_core.contracts.source_budget.metrics import MetricContract

WORKER_PROTOCOL_ID = "ethos-source-budget-worker-protocol-v1"
_REQUEST_SCHEMA = "ethos-source-budget-worker-request-v1"
_RESULT_SCHEMA = "ethos-source-budget-worker-result-v1"
_SHA256_PATTERN = r"^[a-f0-9]{64}$"
_Sha256 = Annotated[str, Field(pattern=_SHA256_PATTERN)]


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
            raise ValueError("worker protocol descriptor integers must be exact")
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
        raise ValueError("worker protocol descriptor must be canonical")
    expected_fields = set(WorkerProtocolDescriptor.model_fields)
    if set(vars(descriptor)) != expected_fields or descriptor.model_fields_set != expected_fields:
        raise ValueError("worker protocol descriptor must be canonical")
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
    contracts: tuple[SerializeAsAny[BaseModel], ...] = Field(min_length=1)
    content_sha256: _Sha256
    resolved_contracts_digest: _Sha256
    provider_digest: _Sha256
    execution_contract_digest: _Sha256
    request_digest: _Sha256

    @field_validator("contracts", mode="before")
    @classmethod
    def _validate_contracts(cls, values: object) -> object:
        """Materialize typed metric contracts from canonical wire objects."""
        from ethos_core.contracts.source_budget.metrics import MetricContract

        return tuple(
            item if type(item) is MetricContract else MetricContract.model_validate(item)
            for item in cast("list[object] | tuple[object, ...]", values)
        )

    @model_validator(mode="after")
    def _validate_contract_digests(self) -> Self:
        """Require all contract-owned request digests to match typed contracts."""
        contracts = cast("tuple[MetricContract, ...]", self.contracts)
        if self.resolved_contracts_digest != canonical.resolved_model_digest(contracts):
            raise ValueError("worker request resolved contracts digest mismatch")
        if {item.grammar_digest for item in contracts} != {self.provider_digest}:
            raise ValueError("worker request provider digest mismatch")
        from ethos_core.contracts.source_budget.metrics import metric_provider_resource_contract

        execution = metric_provider_resource_contract(contracts)
        if execution[0] != "isolated_worker_v1" or execution[3] != self.execution_contract_digest:
            raise ValueError("worker request execution contract digest mismatch")
        unsigned = self.model_dump(
            mode="json",
            by_alias=True,
            exclude={"request_digest"},
        )
        if self.request_digest != _canonical_sha256(unsigned):
            raise ValueError("worker request digest mismatch")
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
            raise ValueError("worker request content must be canonical bytes")
        if type(contracts) is not tuple or not contracts:
            raise ValueError("worker request contracts must be a non-empty canonical tuple")
        from ethos_core.contracts.source_budget.metrics import MetricContract
        from ethos_core.contracts.source_budget.metrics import metric_provider_resource_contract

        if any(type(item) is not MetricContract for item in contracts):
            raise ValueError("worker request contracts must be canonical")
        expected_execution = metric_provider_resource_contract(contracts)
        ordered = tuple(
            sorted(contracts, key=lambda item: (item.metric_id, item.unit, item.contract_id))
        )
        provider_digest = _canonical_sha256(provider_descriptor)
        from ethos_core.contracts.source_budget.measurement.execution import (
            execution_descriptor_digest,
        )

        execution_digest = execution_descriptor_digest(execution_descriptor)
        if execution_descriptor.execution_mode != "isolated_worker_v1":
            raise ValueError("worker request requires an isolated execution descriptor")
        actual_execution = (
            execution_descriptor.execution_mode,
            execution_descriptor.max_carrier_bytes,
            execution_descriptor.execution_contract_id,
            execution_digest,
        )
        if actual_execution != expected_execution:
            raise ValueError("worker request execution descriptor mismatch")
        if len(content) > execution_descriptor.max_carrier_bytes:
            raise ValueError("worker request carrier bytes exceed execution ceiling")
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
            raise ValueError("worker request provider descriptor identity mismatch")
        resolved_digest = canonical.resolved_model_digest(ordered)
        content_digest = hashlib.sha256(content).hexdigest()
        payload: dict[str, object] = {
            "schema": _REQUEST_SCHEMA,
            "protocol_id": WORKER_PROTOCOL_ID,
            "contracts": [item.model_dump(mode="json") for item in ordered],
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
    values: tuple[SerializeAsAny[BaseModel], ...] = Field(min_length=1)
    measurement_digest: _Sha256

    @field_validator("values", mode="before")
    @classmethod
    def _validate_values(cls, values: object) -> object:
        """Materialize typed metric values from canonical wire objects."""
        from ethos_core.contracts.source_budget.measurements import MetricValue

        return tuple(
            item if type(item) is MetricValue else MetricValue.model_validate(item)
            for item in cast("list[object] | tuple[object, ...]", values)
        )


class WorkerResult(BaseModel):
    """One typed worker success bound to its originating request."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )

    schema_id: Literal["ethos-source-budget-worker-result-v1"] = Field(alias="schema")
    protocol_id: Literal["ethos-source-budget-worker-protocol-v1"]
    content_sha256: _Sha256
    resolved_contracts_digest: _Sha256
    provider_digest: _Sha256
    execution_contract_digest: _Sha256
    request_digest: _Sha256
    success: _WorkerSuccess
    gap: Literal[None]

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
            content_sha256=request.content_sha256,
            resolved_contracts_digest=request.resolved_contracts_digest,
            provider_digest=request.provider_digest,
            execution_contract_digest=request.execution_contract_digest,
            request_digest=request.request_digest,
            success=_WorkerSuccess(
                normalized_digest=measurement.normalized_digest,
                values=measurement.values,
                measurement_digest=measurement.measurement_digest,
            ),
            gap=None,
        )


def replay_worker_result(request: WorkerRequest, result: WorkerResult) -> NativeMeasurement:
    """Reconstruct one native measurement from trusted request contracts."""
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
        raise ValueError("worker result request binding mismatch")
    from ethos_core.contracts.source_budget.measurements import NativeMeasurement

    replayed = NativeMeasurement.create(
        content_sha256=request.content_sha256,
        normalized_digest=result.success.normalized_digest,
        contracts=cast("tuple[MetricContract, ...]", request.contracts),
        values=cast("tuple[MetricValue, ...]", result.success.values),
    )
    if replayed.measurement_digest != result.success.measurement_digest:
        raise ValueError("worker result measurement digest mismatch")
    return replayed


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
