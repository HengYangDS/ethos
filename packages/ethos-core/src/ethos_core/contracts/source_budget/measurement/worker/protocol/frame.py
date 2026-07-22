"""Canonical frames for the source-budget worker protocol."""

from __future__ import annotations

import hashlib
import json
import struct
from typing import TYPE_CHECKING

import ethos_core.contracts.source_budget.measurement.worker.protocol.core as core
from ethos_core.contracts.source_budget.metrics import metric_provider_resource_contract

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
    from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerResult

_DUPLICATE_JSON_ERROR = "worker frame JSON contains duplicate keys"
_CONTENT_DIGEST_ERROR = "worker request frame content digest mismatch"
_INVALID_JSON_ERROR = "worker frame JSON must be valid UTF-8 JSON"
_NONCANONICAL_JSON_ERROR = "worker frame JSON must be canonical"


def encode_request_frame(request: WorkerRequest, content: bytes) -> bytes:
    """Encode one canonical request header followed by exact raw content."""
    if hashlib.sha256(content).hexdigest() != request.content_sha256:
        raise ValueError(_CONTENT_DIGEST_ERROR)
    descriptor = core.worker_protocol_descriptor()
    header = _canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
    _require_at_most(len(header), descriptor.header_max_bytes, "request header")
    _require_at_most(16 + len(header) + len(content), descriptor.stdin_max_bytes, "request stdin")
    _require_execution_ceiling(request, content)
    return b"".join(
        (
            descriptor.request_magic.encode("ascii"),
            struct.pack(">II", len(header), len(content)),
            header,
            content,
        )
    )


def decode_request_frame(frame: bytes) -> tuple[WorkerRequest, bytes]:
    """Decode one request and cross-check prefix length and raw content SHA."""
    if len(frame) < 16:
        raise ValueError("worker request frame prefix is truncated")
    descriptor = core.worker_protocol_descriptor()
    if frame[:8] != descriptor.request_magic.encode("ascii"):
        raise ValueError("worker request frame magic mismatch")
    _require_at_most(len(frame), descriptor.stdin_max_bytes, "request stdin")
    header_length, content_length = struct.unpack(">II", frame[8:16])
    _require_at_most(header_length, descriptor.header_max_bytes, "request header")
    header_end = 16 + header_length
    content_end = header_end + content_length
    _require_exact_frame_length(frame, content_end, "request")
    header = frame[16:header_end]
    _require_canonical_json_bytes(header)
    request = core.WorkerRequest.model_validate_json(header, strict=True)
    content = frame[header_end:content_end]
    if hashlib.sha256(content).hexdigest() != request.content_sha256:
        raise ValueError(_CONTENT_DIGEST_ERROR)
    _require_execution_ceiling(request, content)
    return request, content


def encode_result_frame(result: WorkerResult) -> bytes:
    """Encode one canonical typed worker result."""
    descriptor = core.worker_protocol_descriptor()
    payload = _canonical_json_bytes(result.model_dump(mode="json", by_alias=True))
    _require_at_most(12 + len(payload), descriptor.result_max_bytes, "result frame")
    return b"".join(
        (
            descriptor.result_magic.encode("ascii"),
            struct.pack(">I", len(payload)),
            payload,
        )
    )


def decode_result_frame(frame: bytes) -> WorkerResult:
    """Decode one exact typed worker result."""
    if len(frame) < 12:
        raise ValueError("worker result frame prefix is truncated")
    descriptor = core.worker_protocol_descriptor()
    if frame[:8] != descriptor.result_magic.encode("ascii"):
        raise ValueError("worker result frame magic mismatch")
    _require_at_most(len(frame), descriptor.result_max_bytes, "result frame")
    (payload_length,) = struct.unpack(">I", frame[8:12])
    payload_end = 12 + payload_length
    _require_exact_frame_length(frame, payload_end, "result")
    payload = frame[12:payload_end]
    _require_canonical_json_bytes(payload)
    return core.WorkerResult.model_validate_json(payload, strict=True)


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(_DUPLICATE_JSON_ERROR)
        payload[key] = value
    return payload


def _require_exact_frame_length(frame: bytes, expected: int, label: str) -> None:
    if len(frame) != expected:
        message = f"worker {label} frame length mismatch"
        raise ValueError(message)


def _require_at_most(actual: int, maximum: int, label: str) -> None:
    if actual > maximum:
        message = f"worker {label} exceeds maximum"
        raise ValueError(message)


def _require_execution_ceiling(request: WorkerRequest, content: bytes) -> None:
    execution = metric_provider_resource_contract(request.contracts)
    if len(content) > execution[1]:
        message = "worker request frame content exceeds execution ceiling"
        raise ValueError(message)


def _require_canonical_json_bytes(encoded: bytes) -> None:
    try:
        payload = json.loads(encoded, object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(_INVALID_JSON_ERROR) from error
    if _canonical_json_bytes(payload) != encoded:
        raise ValueError(_NONCANONICAL_JSON_ERROR)


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
