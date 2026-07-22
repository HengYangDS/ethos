"""Pure execution descriptors for Budget Contract v2 measurement."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos_core.contracts.source_budget.measurement.worker.resource import (
    WORKER_RESOURCE_PROFILE_ID,
)
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    worker_resource_profile_descriptor,
)
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    worker_resource_profile_descriptor_digest,
)

BOUNDED_EXECUTION_CONTRACT_ID = "ethos-source-budget-execution:bounded-in-process-v1"
ISOLATED_EXECUTION_CONTRACT_ID = "ethos-source-budget-execution:isolated-worker-v1"
ExecutionMode = Literal["bounded_in_process_v1", "isolated_worker_v1"]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]

_PARSER_EXECUTION: dict[str, tuple[ExecutionMode, int]] = {
    "utf8-footprint": ("bounded_in_process_v1", 262144),
    "utf8-control": ("bounded_in_process_v1", 32768),
    "diagram-contract": ("bounded_in_process_v1", 32768),
    "python-tokenize": ("isolated_worker_v1", 65536),
    "json-stdlib": ("isolated_worker_v1", 32768),
    "tomllib": ("isolated_worker_v1", 32768),
    "pyyaml-safe": ("isolated_worker_v1", 32768),
    "configparser": ("isolated_worker_v1", 32768),
    "jinja2": ("isolated_worker_v1", 32768),
    "shell-lexical": ("isolated_worker_v1", 32768),
}


def _worker_protocol_reference() -> tuple[str, str]:
    """Resolve the protocol identity lazily to keep schema imports acyclic."""
    import ethos_core.contracts.source_budget.measurement.worker.protocol.core as protocol

    descriptor = protocol.worker_protocol_descriptor()
    return protocol.WORKER_PROTOCOL_ID, protocol.worker_protocol_descriptor_digest(descriptor)


class DescriptorReference(BaseModel):
    """One exact id/digest reference from an isolated execution descriptor."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    id: str = Field(min_length=1)
    digest: Sha256


class BoundedExecutionDescriptor(BaseModel):
    """Parameterised identity for reviewed in-process linear providers."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )

    schema_id: Literal["ethos-source-budget-execution-descriptor-v1"] = Field(alias="schema")
    execution_contract_id: Literal["ethos-source-budget-execution:bounded-in-process-v1"]
    execution_mode: Literal["bounded_in_process_v1"]
    max_carrier_bytes: PositiveInt


class IsolatedExecutionDescriptor(BaseModel):
    """Parameterised identity for future one-shot isolated providers."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )

    schema_id: Literal["ethos-source-budget-execution-descriptor-v1"] = Field(alias="schema")
    execution_contract_id: Literal["ethos-source-budget-execution:isolated-worker-v1"]
    execution_mode: Literal["isolated_worker_v1"]
    max_carrier_bytes: PositiveInt
    worker_protocol: DescriptorReference
    resource_profile: DescriptorReference

    @model_validator(mode="after")
    def validate_descriptor_references(self) -> IsolatedExecutionDescriptor:
        """Require the exact repository-owned protocol and resource identities."""
        expected_protocol = _worker_protocol_reference()
        actual_protocol = self.worker_protocol.id, self.worker_protocol.digest
        if actual_protocol != expected_protocol:
            raise ValueError("source-budget execution descriptor worker protocol mismatch")
        resource = worker_resource_profile_descriptor()
        expected_resource = (
            WORKER_RESOURCE_PROFILE_ID,
            worker_resource_profile_descriptor_digest(resource),
        )
        actual_resource = self.resource_profile.id, self.resource_profile.digest
        if actual_resource != expected_resource:
            raise ValueError("source-budget execution descriptor resource profile mismatch")
        return self


ExecutionDescriptor = BoundedExecutionDescriptor | IsolatedExecutionDescriptor
ExecutionContract = tuple[ExecutionMode, int, str, str]


def execution_descriptor(mode: ExecutionMode, ceiling: int) -> ExecutionDescriptor:
    """Return the exact parameterised descriptor for one admitted execution mode."""
    if mode == "bounded_in_process_v1":
        return BoundedExecutionDescriptor(
            schema="ethos-source-budget-execution-descriptor-v1",
            execution_contract_id=BOUNDED_EXECUTION_CONTRACT_ID,
            execution_mode=mode,
            max_carrier_bytes=ceiling,
        )
    if mode == "isolated_worker_v1":
        protocol_id, protocol_digest = _worker_protocol_reference()
        resource = worker_resource_profile_descriptor()
        return IsolatedExecutionDescriptor(
            schema="ethos-source-budget-execution-descriptor-v1",
            execution_contract_id=ISOLATED_EXECUTION_CONTRACT_ID,
            execution_mode=mode,
            max_carrier_bytes=ceiling,
            worker_protocol=DescriptorReference(
                id=protocol_id,
                digest=protocol_digest,
            ),
            resource_profile=DescriptorReference(
                id=WORKER_RESOURCE_PROFILE_ID,
                digest=worker_resource_profile_descriptor_digest(resource),
            ),
        )
    raise ValueError("source-budget execution mode is not admitted")


def execution_descriptor_digest(descriptor: ExecutionDescriptor) -> str:
    """Return canonical compact sorted-key JSON SHA-256 for one descriptor."""
    descriptor_type: type[BoundedExecutionDescriptor] | type[IsolatedExecutionDescriptor]
    if type(descriptor) is BoundedExecutionDescriptor:
        descriptor_type = BoundedExecutionDescriptor
    elif type(descriptor) is IsolatedExecutionDescriptor:
        descriptor_type = IsolatedExecutionDescriptor
    else:
        raise ValueError("source-budget execution descriptor must be canonical")
    expected_fields = set(descriptor_type.model_fields)
    if set(vars(descriptor)) != expected_fields or descriptor.model_fields_set != expected_fields:
        raise ValueError("source-budget execution descriptor must be canonical")
    if type(descriptor) is IsolatedExecutionDescriptor:
        reference_fields = set(DescriptorReference.model_fields)
        references = descriptor.worker_protocol, descriptor.resource_profile
        if any(
            type(reference) is not DescriptorReference
            or set(vars(reference)) != reference_fields
            or reference.model_fields_set != reference_fields
            for reference in references
        ):
            raise ValueError("source-budget execution descriptor must be canonical")
    canonical = descriptor_type.model_validate(descriptor.model_dump(mode="python"))
    encoded = json.dumps(
        canonical.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parser_execution_contract(parser_id: str) -> ExecutionContract:
    """Return the repository-owned static execution tuple for one parser id."""
    try:
        mode, ceiling = _PARSER_EXECUTION[parser_id]
    except (KeyError, TypeError):
        raise ValueError("source-budget parser execution is not admitted") from None
    descriptor = execution_descriptor(mode, ceiling)
    return (
        mode,
        ceiling,
        descriptor.execution_contract_id,
        execution_descriptor_digest(descriptor),
    )
