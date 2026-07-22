from __future__ import annotations

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
def test_frame_decoders_reject_unknown_magic(direction: str) -> None:
    request, content, result = _request_result()
    if direction == "request":
        decoder = decode_request_frame
        frame = encode_request_frame(request, content)
    else:
        decoder = decode_result_frame
        frame = encode_result_frame(result)

    with pytest.raises(ValueError, match="magic"):
        decoder(b"BADMAGIC" + frame[8:])


@pytest.mark.parametrize("direction", ["request", "result"])
def test_frame_decoders_reject_wrong_direction_magic(direction: str) -> None:
    request, content, result = _request_result()
    if direction == "request":
        decoder = decode_request_frame
        frame = encode_request_frame(request, content)
        wrong_magic = _RESULT_MAGIC
    else:
        decoder = decode_result_frame
        frame = encode_result_frame(result)
        wrong_magic = _REQUEST_MAGIC

    with pytest.raises(ValueError, match="magic"):
        decoder(wrong_magic + frame[8:])


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
