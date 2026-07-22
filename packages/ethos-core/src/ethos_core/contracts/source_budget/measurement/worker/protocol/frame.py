"""Canonical frames for the source-budget worker protocol."""

from __future__ import annotations

import hashlib
import json
import struct
from typing import TYPE_CHECKING

import ethos_core.contracts.source_budget.measurement.worker.protocol.core as core

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
    from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerResult

_DUPLICATE_JSON_ERROR = "worker frame JSON contains duplicate keys"
_INVALID_JSON_ERROR = "worker frame JSON must be valid UTF-8 JSON"
_NONCANONICAL_JSON_ERROR = "worker frame JSON must be canonical"


def encode_request_frame(request: WorkerRequest, content: bytes) -> bytes:
    """Encode one canonical request header followed by exact raw content."""
    if hashlib.sha256(content).hexdigest() != request.content_sha256:
        raise ValueError("worker request frame content digest mismatch")
    descriptor = core.worker_protocol_descriptor()
    header = _canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
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
    header_length, content_length = struct.unpack(">II", frame[8:16])
    header_end = 16 + header_length
    content_end = header_end + content_length
    header = frame[16:header_end]
    _require_canonical_json_bytes(header)
    request = core.WorkerRequest.model_validate_json(header, strict=True)
    content = frame[header_end:content_end]
    return request, content


def encode_result_frame(result: WorkerResult) -> bytes:
    """Encode one canonical typed worker result."""
    descriptor = core.worker_protocol_descriptor()
    payload = _canonical_json_bytes(result.model_dump(mode="json", by_alias=True))
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
    (payload_length,) = struct.unpack(">I", frame[8:12])
    payload_end = 12 + payload_length
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
