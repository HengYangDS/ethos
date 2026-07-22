from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerResult
from ethos_core.contracts.source_budget.measurement.worker.protocol.frame import (
    decode_request_frame,
)
from ethos_core.contracts.source_budget.measurement.worker.protocol.frame import decode_result_frame
from ethos_core.contracts.source_budget.measurement.worker.protocol.frame import (
    encode_request_frame,
)
from ethos_core.contracts.source_budget.measurement.worker.protocol.frame import encode_result_frame
from ethos_core.contracts.source_budget.measurements import NativeMeasurement
from tests.unit.kernel.test_source_budget_worker_protocol_contract import _CONTENT
from tests.unit.kernel.test_source_budget_worker_protocol_contract import _NORMALIZED_DIGEST
from tests.unit.kernel.test_source_budget_worker_protocol_contract import _canonical_json
from tests.unit.kernel.test_source_budget_worker_protocol_contract import _contracts
from tests.unit.kernel.test_source_budget_worker_protocol_contract import _expected_request_payload
from tests.unit.kernel.test_source_budget_worker_protocol_contract import (
    _isolated_execution_descriptor,
)
from tests.unit.kernel.test_source_budget_worker_protocol_contract import _provider_descriptor
from tests.unit.kernel.test_source_budget_worker_protocol_contract import _values

if TYPE_CHECKING:
    from collections.abc import Callable

    from ethos_core.contracts.source_budget.metrics import MetricContract

_REQUEST_MAGIC = b"ESBWREQ1"
_RESULT_MAGIC = b"ESBWRES1"


def _request_result() -> tuple[WorkerRequest, bytes, WorkerResult]:
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
    return request, _CONTENT, WorkerResult.from_measurement(request=request, measurement=native)


def _request_for_contracts(contracts: tuple[MetricContract, ...]) -> WorkerRequest:
    return WorkerRequest.create(
        content=_CONTENT,
        contracts=contracts,
        provider_descriptor=_provider_descriptor(),
        execution_descriptor=_isolated_execution_descriptor(),
    )


def _request_at_header_size(target: int) -> tuple[WorkerRequest, bytes]:
    contracts = _contracts()
    base = _request_for_contracts(contracts)
    base_header = _canonical_json(base.model_dump(mode="json", by_alias=True))
    suffix_length = target - len(base_header)
    assert suffix_length >= 0
    first = contracts[0].model_copy(
        update={"contract_id": contracts[0].contract_id + ("x" * suffix_length)}
    )
    request = _request_for_contracts((first, *contracts[1:]))
    header = _canonical_json(request.model_dump(mode="json", by_alias=True))
    assert len(header) == target
    return request, header


def _result_at_total_size(target: int) -> tuple[WorkerResult, bytes]:
    _request, _content, base_result = _request_result()
    base_payload = _canonical_json(base_result.model_dump(mode="json", by_alias=True))
    suffix_length = target - 12 - len(base_payload)
    assert suffix_length >= 0
    contracts = _contracts()
    contract_id = contracts[0].contract_id + ("x" * suffix_length)
    first_contract = contracts[0].model_copy(update={"contract_id": contract_id})
    adjusted_contracts = (first_contract, *contracts[1:])
    values = _values()
    first_value = values[0].model_copy(update={"contract_id": contract_id})
    request = _request_for_contracts(adjusted_contracts)
    native = NativeMeasurement.create(
        content_sha256=request.content_sha256,
        normalized_digest=_NORMALIZED_DIGEST,
        contracts=adjusted_contracts,
        values=(first_value, *values[1:]),
    )
    result = WorkerResult.from_measurement(request=request, measurement=native)
    payload = _canonical_json(result.model_dump(mode="json", by_alias=True))
    assert 12 + len(payload) == target
    return result, payload


def _resigned_request_header(request: WorkerRequest, content: bytes) -> bytes:
    payload = request.model_dump(mode="json", by_alias=True)
    payload["content_sha256"] = hashlib.sha256(content).hexdigest()
    unsigned = {key: value for key, value in payload.items() if key != "request_digest"}
    payload["request_digest"] = hashlib.sha256(_canonical_json(unsigned)).hexdigest()
    return _canonical_json(payload)


def _raw_request_frame(
    header: bytes,
    content: bytes = _CONTENT,
    *,
    header_length: int | None = None,
    content_length: int | None = None,
) -> bytes:
    return b"".join(
        (
            _REQUEST_MAGIC,
            (len(header) if header_length is None else header_length).to_bytes(4, "big"),
            (len(content) if content_length is None else content_length).to_bytes(4, "big"),
            header,
            content,
        )
    )


def _raw_result_frame(
    payload: bytes,
    *,
    payload_length: int | None = None,
) -> bytes:
    length = len(payload) if payload_length is None else payload_length
    return _RESULT_MAGIC + length.to_bytes(4, "big") + payload


def _duplicate_json_member(payload: object, key: str, value: object) -> bytes:
    encoded = _canonical_json(payload).decode("utf-8")
    member = ":".join(
        (
            json.dumps(key, ensure_ascii=False),
            json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        )
    )
    assert member in encoded
    return encoded.replace(member, f"{member},{member}", 1).encode("utf-8")


def test_frame_decoders_construct_typed_models_from_wire_alone() -> None:
    contracts = _contracts()
    request_payload = _expected_request_payload(contracts)
    request_header = _canonical_json(request_payload)
    raw_request = b"".join(
        (
            _REQUEST_MAGIC,
            len(request_header).to_bytes(4, "big"),
            len(_CONTENT).to_bytes(4, "big"),
            request_header,
            _CONTENT,
        )
    )
    request, content = decode_request_frame(raw_request)
    assert type(request) is WorkerRequest
    assert content == _CONTENT

    native = NativeMeasurement.create(
        content_sha256=request.content_sha256,
        normalized_digest=_NORMALIZED_DIGEST,
        contracts=contracts,
        values=_values(),
    )
    result_payload = {
        "schema": "ethos-source-budget-worker-result-v1",
        "protocol_id": "ethos-source-budget-worker-protocol-v1",
        **{
            name: request_payload[name]
            for name in (
                "content_sha256",
                "resolved_contracts_digest",
                "provider_digest",
                "execution_contract_digest",
                "request_digest",
            )
        },
        "success": {
            "normalized_digest": native.normalized_digest,
            "values": [item.model_dump(mode="json") for item in native.values],
            "measurement_digest": native.measurement_digest,
        },
        "gap": None,
    }
    result_header = _canonical_json(result_payload)
    raw_result = _RESULT_MAGIC + len(result_header).to_bytes(4, "big") + result_header
    result = decode_result_frame(raw_result)
    assert type(result) is WorkerResult
    assert result.model_dump(mode="json", by_alias=True) == result_payload


def test_request_and_result_frames_round_trip_canonical_wire() -> None:
    request, content, result = _request_result()

    request_header = _canonical_json(request.model_dump(mode="json", by_alias=True))
    encoded_request = encode_request_frame(request, content)
    assert encoded_request == b"".join(
        (
            _REQUEST_MAGIC,
            len(request_header).to_bytes(4, "big"),
            len(content).to_bytes(4, "big"),
            request_header,
            content,
        )
    )
    assert decode_request_frame(encoded_request) == (request, content)

    result_payload = _canonical_json(result.model_dump(mode="json", by_alias=True))
    encoded_result = encode_result_frame(result)
    assert encoded_result == b"".join(
        (
            _RESULT_MAGIC,
            len(result_payload).to_bytes(4, "big"),
            result_payload,
        )
    )
    assert decode_result_frame(encoded_result) == result


def test_request_frame_encoder_rejects_content_not_bound_by_request() -> None:
    request, content, _result = _request_result()
    substituted = b"x" * len(content)

    with pytest.raises(ValueError, match=r"content.*digest"):
        encode_request_frame(request, substituted)


@pytest.mark.parametrize("direction", ["request", "result"])
@pytest.mark.parametrize("variant", ["whitespace", "unsorted"])
def test_frame_decoders_reject_noncanonical_json_bytes(direction: str, variant: str) -> None:
    request, content, result = _request_result()
    if direction == "request":
        payload = request.model_dump(mode="json", by_alias=True)
        decoder = decode_request_frame
    else:
        payload = result.model_dump(mode="json", by_alias=True)
        decoder = decode_result_frame
    if variant == "whitespace":
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")
    else:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert json.loads(encoded) == payload
    frame = (
        _raw_request_frame(encoded, content)
        if direction == "request"
        else _raw_result_frame(encoded)
    )

    with pytest.raises(ValueError, match=r"canonical|json"):
        decoder(frame)


@pytest.mark.parametrize("direction", ["request", "result"])
def test_frame_decoders_reject_invalid_utf8_json(direction: str) -> None:
    decoder = decode_request_frame if direction == "request" else decode_result_frame
    frame = _raw_request_frame(b"\xff") if direction == "request" else _raw_result_frame(b"\xff")

    with pytest.raises(ValueError, match=r"(?i)json|unicode|utf"):
        decoder(frame)


@pytest.mark.parametrize("direction", ["request", "result"])
@pytest.mark.parametrize("scope", ["top", "nested"])
def test_frame_decoders_reject_duplicate_json_keys(direction: str, scope: str) -> None:
    request, content, result = _request_result()
    nested = scope == "nested"
    if direction == "request":
        payload = request.model_dump(mode="json", by_alias=True)
        nested_value = payload["contracts"][0]["contract_id"]
        duplicated = _duplicate_json_member(
            payload,
            "contract_id" if nested else "schema",
            nested_value if nested else payload["schema"],
        )
        frame = _raw_request_frame(duplicated, content)
        decoder = decode_request_frame
    else:
        payload = result.model_dump(mode="json", by_alias=True)
        nested_value = payload["success"]["values"][0]["contract_id"]
        duplicated = _duplicate_json_member(
            payload,
            "contract_id" if nested else "schema",
            nested_value if nested else payload["schema"],
        )
        frame = _raw_result_frame(duplicated)
        decoder = decode_result_frame
    assert json.loads(duplicated) == payload

    with pytest.raises(ValueError, match=r"duplicate|canonical|json"):
        decoder(frame)


@pytest.mark.parametrize("case", ["header-truncated", "content-truncated", "content-overclaim"])
def test_request_decoder_rejects_truncation_and_overclaim(case: str) -> None:
    request, content, _result = _request_result()
    header = _canonical_json(request.model_dump(mode="json", by_alias=True))
    if case == "header-truncated":
        frame = _raw_request_frame(header[:-1], content, header_length=len(header))
    elif case == "content-truncated":
        frame = _raw_request_frame(header, content[:-1], content_length=len(content))
    else:
        frame = _raw_request_frame(header, content, content_length=len(content) + 1)

    with pytest.raises(ValueError, match=r"length|truncated|frame|json"):
        decode_request_frame(frame)


@pytest.mark.parametrize("case", ["payload-truncated", "payload-overclaim"])
def test_result_decoder_rejects_truncation_and_overclaim(case: str) -> None:
    _request, _content, result = _request_result()
    payload = _canonical_json(result.model_dump(mode="json", by_alias=True))
    if case == "payload-truncated":
        frame = _raw_result_frame(payload[:-1], payload_length=len(payload))
    else:
        frame = _raw_result_frame(payload, payload_length=len(payload) + 1)

    with pytest.raises(ValueError, match=r"length|truncated|frame|json"):
        decode_result_frame(frame)


@pytest.mark.parametrize("direction", ["request", "result"])
def test_frame_decoders_reject_trailing_bytes(direction: str) -> None:
    request, content, result = _request_result()
    if direction == "request":
        decoder = decode_request_frame
        frame = encode_request_frame(request, content)
    else:
        decoder = decode_result_frame
        frame = encode_result_frame(result)

    with pytest.raises(ValueError, match=r"length|trailing|frame"):
        decoder(frame + b"x")


def test_result_decoder_rejects_a_second_complete_response() -> None:
    _request, _content, result = _request_result()
    frame = encode_result_frame(result)

    with pytest.raises(ValueError, match=r"length|trailing|frame"):
        decode_result_frame(frame + frame)


@pytest.mark.parametrize(
    ("direction", "replacement_magic"),
    [
        ("request", b"BADMAGIC"),
        ("request", _RESULT_MAGIC),
        ("request", b"ESBWREQ2"),
        ("result", b"BADMAGIC"),
        ("result", _REQUEST_MAGIC),
        ("result", b"ESBWRES2"),
    ],
)
def test_frame_decoders_require_exact_direction_magic_and_version(
    direction: str,
    replacement_magic: bytes,
) -> None:
    request, content, result = _request_result()
    if direction == "request":
        decoder = decode_request_frame
        frame = encode_request_frame(request, content)
    else:
        decoder = decode_result_frame
        frame = encode_result_frame(result)

    with pytest.raises(ValueError, match="magic"):
        decoder(replacement_magic + frame[8:])


@pytest.mark.parametrize("operation", ["encode", "decode"])
@pytest.mark.parametrize("size", [32767, 32768, 32769])
def test_request_codec_enforces_exact_header_max_bytes(operation: str, size: int) -> None:
    request, header = _request_at_header_size(size)
    raw = _raw_request_frame(header)
    if size <= 32768:
        if operation == "encode":
            assert encode_request_frame(request, _CONTENT) == raw
        else:
            assert decode_request_frame(raw) == (request, _CONTENT)
    elif operation == "encode":
        with pytest.raises(ValueError, match=r"header|limit|max"):
            encode_request_frame(request, _CONTENT)
    else:
        with pytest.raises(ValueError, match=r"header|limit|max"):
            decode_request_frame(raw)


@pytest.mark.parametrize("total", [327679, 327680, 327681])
def test_request_decoder_enforces_total_stdin_max_before_json_parse(total: int) -> None:
    header = b"x"
    content = b"x" * (total - 17)
    frame = _raw_request_frame(header, content)
    assert len(frame) == total
    if total <= 327680:
        with pytest.raises(ValueError, match=r"(?i)json|canonical"):
            decode_request_frame(frame)
    else:
        with pytest.raises(ValueError, match=r"stdin|limit|max"):
            decode_request_frame(frame)


@pytest.mark.parametrize("total", [327679, 327680, 327681])
def test_request_encoder_enforces_total_stdin_max(total: int) -> None:
    request, _header = _request_at_header_size(32768)
    content = b"x" * (total - 16 - 32768)
    oversized_request = WorkerRequest.model_validate_json(
        _resigned_request_header(request, content)
    )
    assert 16 + len(_resigned_request_header(request, content)) + len(content) == total
    if total <= 327680:
        with pytest.raises(ValueError, match=r"carrier|ceiling|limit"):
            encode_request_frame(oversized_request, content)
    else:
        with pytest.raises(ValueError, match=r"stdin|limit|max"):
            encode_request_frame(oversized_request, content)


@pytest.mark.parametrize("operation", ["encode", "decode"])
@pytest.mark.parametrize("total", [65535, 65536, 65537])
def test_result_codec_enforces_exact_total_max_bytes(operation: str, total: int) -> None:
    result, payload = _result_at_total_size(total)
    raw = _raw_result_frame(payload)
    if total <= 65536:
        if operation == "encode":
            assert encode_result_frame(result) == raw
        else:
            assert decode_result_frame(raw) == result
    elif operation == "encode":
        with pytest.raises(ValueError, match=r"result|limit|max"):
            encode_result_frame(result)
    else:
        with pytest.raises(ValueError, match=r"result|limit|max"):
            decode_result_frame(raw)


def test_request_decoder_revalidates_content_digest() -> None:
    request, content, _result = _request_result()
    frame = encode_request_frame(request, content)
    substituted = b"x" * len(content)

    with pytest.raises(ValueError, match=r"content.*digest"):
        decode_request_frame(frame[: -len(content)] + substituted)


def test_request_encoder_revalidates_execution_ceiling() -> None:
    request, _content, _result = _request_result()
    content = b"x" * 65537
    oversized_request = WorkerRequest.model_validate_json(
        _resigned_request_header(request, content)
    )

    with pytest.raises(ValueError, match=r"carrier|ceiling|limit"):
        encode_request_frame(oversized_request, content)


@pytest.mark.parametrize("size", [65536, 65537])
def test_request_decoder_revalidates_execution_ceiling(size: int) -> None:
    request, _content, _result = _request_result()
    content = b"x" * size
    frame = _raw_request_frame(_resigned_request_header(request, content), content)
    if size == 65536:
        decoded_request, decoded_content = decode_request_frame(frame)
        assert decoded_request.content_sha256 == hashlib.sha256(content).hexdigest()
        assert decoded_content == content
    else:
        with pytest.raises(ValueError, match=r"carrier|ceiling|limit"):
            decode_request_frame(frame)


@pytest.mark.parametrize(
    ("decoder", "short_frame"),
    [
        (decode_request_frame, _REQUEST_MAGIC + (b"\0" * 7)),
        (decode_result_frame, _RESULT_MAGIC + (b"\0" * 3)),
    ],
)
def test_frame_decoders_reject_short_prefix_as_value_error(
    decoder: Callable[[bytes], object],
    short_frame: bytes,
) -> None:
    with pytest.raises(ValueError, match=r"prefix|truncated|length"):
        decoder(short_frame)
