"""Canonical descriptor for the future source-budget worker protocol."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

WORKER_PROTOCOL_ID = "ethos-source-budget-worker-protocol-v1"


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
