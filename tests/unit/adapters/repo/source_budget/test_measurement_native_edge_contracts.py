"""Edge contracts for native source-budget routing and provider boundaries."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Never
from typing import cast

import pytest

from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos.adapters.repo.source_budget.measurement import core as measurement
from ethos.adapters.repo.source_budget.measurement import router
from ethos.adapters.repo.source_budget.measurement.native import identity
from ethos.adapters.repo.source_budget.measurement.native.bounded import core as bounded
from ethos.adapters.repo.source_budget.measurement.native.isolated import core as isolated
from ethos.adapters.repo.source_budget.measurement.native.isolated import structured
from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierManifest
from ethos_core.contracts.source_budget.carriers import classify_carriers
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.metrics import MetricContract
    from ethos_core.contracts.source_budget.metrics import MetricContractSet

ROOT = Path(__file__).resolve().parents[5]


@lru_cache(maxsize=1)
def _registry() -> MetricContractSet:
    load = load_metric_contracts(ROOT)
    assert load.required_gaps == ()
    assert load.contracts is not None
    return load.contracts


def _contracts(profile_id: str) -> tuple[MetricContract, ...]:
    return tuple(
        sorted(
            (
                contract
                for contract in _registry().contracts
                if contract.metric_profile == profile_id
            ),
            key=lambda contract: (contract.metric_id, contract.unit, contract.contract_id),
        )
    )


def _worker_request(
    profile_id: str = "python-source-v2",
    content: bytes = b"value = 1\n",
) -> WorkerRequest:
    resolved = identity.resolve_native_provider(_contracts(profile_id), _registry())
    return WorkerRequest.create(
        content=content,
        contracts=resolved.contracts,
        provider_descriptor=resolved.provider_descriptor,
        execution_descriptor=resolved.execution_descriptor,
    )


def _raise(error: BaseException) -> Never:
    raise error


def _member(module: object, name: str) -> Any:
    return vars(module)[name]


@pytest.mark.parametrize(
    ("error", "expected_gap"),
    [
        (MemoryError(), "source_budget_native_resource_exhausted"),
        (ValueError("opaque"), "source_budget_native_contract_invalid"),
        (AttributeError("opaque"), "source_budget_native_contract_invalid"),
    ],
)
def test_bounded_outer_boundary_maps_untrusted_failures(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
    expected_gap: str,
) -> None:
    monkeypatch.setattr(bounded, "_measure_validated", lambda *_args: _raise(error))

    load = bounded.measure_bounded(b"x", _contracts("control-source-v2"), _registry())

    assert load.measurement is None
    assert load.required_gaps == (expected_gap,)


def test_bounded_validation_rejects_non_bytes_oversize_and_conformance_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contracts = _contracts("control-source-v2")
    invalid = bounded.measure_bounded(cast("Any", "x"), contracts, _registry())
    oversize = bounded.measure_bounded(b"x" * 32769, contracts, _registry())
    monkeypatch.setattr(
        bounded,
        "_startup_conformance",
        lambda _provider_id: ("source_budget_native_conformance_mismatch:utf8-control",),
    )
    mismatch = bounded.measure_bounded(b"x", contracts, _registry())

    assert invalid.required_gaps == ("source_budget_native_contract_invalid",)
    assert oversize.required_gaps == ("source_budget_native_carrier_bytes_exceeded",)
    assert mismatch.required_gaps == ("source_budget_native_conformance_mismatch:utf8-control",)


def test_pre_resolved_bounded_rejects_non_exact_content_and_provider() -> None:
    resolved = identity.resolve_native_provider(_contracts("control-source-v2"), _registry())

    class ForgedResolvedNativeProvider(identity.ResolvedNativeProvider):
        pass

    forged = ForgedResolvedNativeProvider(
        provider_id=resolved.provider_id,
        contracts=resolved.contracts,
        provider_descriptor=resolved.provider_descriptor,
        execution_descriptor=resolved.execution_descriptor,
    )
    invalid_content = bounded.measure_bounded_resolved(cast("Any", "x"), resolved)
    invalid_provider = bounded.measure_bounded_resolved(b"x", forged)

    assert invalid_content.required_gaps == ("source_budget_native_contract_invalid",)
    assert invalid_provider.required_gaps == ("source_budget_native_contract_invalid",)


@pytest.mark.parametrize(
    ("operation", "expected_gap"),
    [
        (lambda: _raise(MemoryError()), "source_budget_native_resource_exhausted"),
        (lambda: (b"stream", {}), "source_budget_native_contract_invalid"),
    ],
)
def test_bounded_measurement_maps_inner_resource_and_shape_failures(
    monkeypatch: pytest.MonkeyPatch,
    operation: object,
    expected_gap: str,
) -> None:
    monkeypatch.setattr(bounded, "_startup_conformance", lambda _provider_id: ())
    monkeypatch.setattr(bounded, "_measure_provider", lambda *_args: cast("Any", operation)())

    load = bounded.measure_bounded(b"x", _contracts("control-source-v2"), _registry())

    assert load.measurement is None
    assert load.required_gaps == (expected_gap,)


def test_bounded_conformance_maps_resource_exhaustion_at_provider_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bounded,
        "_conformance_output_digest",
        lambda _provider_id: _raise(MemoryError()),
    )

    conformance_gap = _member(bounded, "_conformance_gap")
    assert conformance_gap("utf8-control") == "source_budget_native_resource_exhausted"


def test_bounded_runtime_and_provider_vocabulary_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    startup_conformance = _member(bounded, "_startup_conformance")
    startup_conformance.cache_clear()
    monkeypatch.setattr(bounded, "_runtime_identity", lambda: ("PyPy", 3, 14))
    try:
        assert startup_conformance("utf8-control") == ("source_budget_native_runtime_unsupported",)
    finally:
        startup_conformance.cache_clear()

    measure_provider = _member(bounded, "_measure_provider")
    with pytest.raises(ValueError, match="source_budget_native_parse_failed:not-admitted"):
        measure_provider("not-admitted", "")


def test_identity_preserves_memory_exhaustion_from_registry_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        identity,
        "admit_resolved_metric_contracts",
        lambda *_args: _raise(MemoryError()),
    )

    with pytest.raises(MemoryError):
        identity.resolve_native_provider(_contracts("python-source-v2"), _registry())


def test_identity_rejects_unmatched_and_faulting_provider_signatures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged = tuple(
        contract.model_copy(update={"parser_version": "not-admitted"})
        for contract in _contracts("python-source-v2")
    )
    with pytest.raises(ValueError, match="provider_signature_mismatch"):
        identity.revalidate_worker_provider(forged)

    monkeypatch.setattr(
        identity,
        "_provider_id_for_contract",
        lambda _contract: _raise(AttributeError("opaque")),
    )
    with pytest.raises(ValueError, match="native_contract_invalid"):
        identity.revalidate_worker_provider(_contracts("python-source-v2"))


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (MemoryError(), None),
        (KeyError("opaque"), "native_contract_invalid"),
    ],
)
def test_identity_provider_vector_preserves_resource_and_maps_shape_failures(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
    message: str | None,
) -> None:
    monkeypatch.setattr(identity, "_resolved_provider_id", lambda _contracts: "python")
    monkeypatch.setattr(
        identity,
        "provider_metrics",
        lambda _provider_id: _raise(error),
    )

    expected = MemoryError if message is None else ValueError
    with pytest.raises(expected, match=message):
        identity.revalidate_worker_provider(_contracts("python-source-v2"))


def test_identity_provider_vector_requires_exact_coordinates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(identity, "_resolved_provider_id", lambda _contracts: "python")
    monkeypatch.setattr(
        identity,
        "provider_metrics",
        lambda _provider_id: (("unexpected", "normalized_byte"),),
    )

    with pytest.raises(ValueError, match="provider_signature_mismatch"):
        identity.revalidate_worker_provider(_contracts("python-source-v2"))


@pytest.mark.parametrize(
    ("target", "error", "expected"),
    [
        ("vars", MemoryError(), MemoryError),
        ("_contract_payload", MemoryError(), MemoryError),
        ("_contract_payload", TypeError("opaque"), ValueError),
    ],
)
def test_identity_storage_and_revalidation_are_exception_total(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    error: BaseException,
    expected: type[BaseException],
) -> None:
    monkeypatch.setattr(identity, target, lambda *_args: _raise(error), raising=False)

    with pytest.raises(expected):
        identity.revalidate_worker_provider(_contracts("python-source-v2"))


def test_identity_maps_non_execution_contract_validation_failure() -> None:
    forged = tuple(
        contract.model_copy(update={"aggregation": "not-sum"})
        for contract in _contracts("python-source-v2")
    )

    with pytest.raises(ValueError, match="native_contract_invalid"):
        identity.revalidate_worker_provider(forged)


def test_isolated_measurement_maps_admission_memory_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _worker_request()
    monkeypatch.setattr(
        isolated,
        "_admit_worker_request",
        lambda *_args: _raise(MemoryError()),
    )

    result = isolated.measure_isolated(request, b"value = 1\n")

    assert result.gap == "source_budget_native_resource_exhausted"


def test_isolated_request_canonicalization_rejects_wrong_type_and_storage() -> None:
    with pytest.raises(ValueError, match="native_contract_invalid"):
        isolated.measure_isolated(cast("Any", object()), b"")

    forged = _worker_request().model_copy(update={"unexpected": True})
    with pytest.raises(ValueError, match="native_contract_invalid"):
        isolated.measure_isolated(forged, b"value = 1\n")


@pytest.mark.parametrize(
    ("error", "expected"),
    [(MemoryError(), MemoryError), (TypeError("opaque"), ValueError)],
)
def test_isolated_request_canonicalization_is_exception_total(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
    expected: type[BaseException],
) -> None:
    request = _worker_request()
    monkeypatch.setattr(
        isolated.WorkerRequest,
        "model_validate",
        lambda *_args, **_kwargs: _raise(error),
    )

    with pytest.raises(expected):
        isolated.measure_isolated(request, b"value = 1\n")


@pytest.mark.parametrize(
    ("error", "expected_gap"),
    [
        (MemoryError(), "source_budget_native_resource_exhausted"),
        (
            ValueError("source_budget_native_provider_signature_mismatch"),
            "source_budget_native_provider_signature_mismatch",
        ),
        (ValueError("opaque"), "source_budget_native_contract_invalid"),
        (AttributeError("opaque"), "source_budget_native_contract_invalid"),
    ],
)
def test_isolated_provider_revalidation_maps_untrusted_failures(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
    expected_gap: str,
) -> None:
    request = _worker_request()
    monkeypatch.setattr(
        isolated,
        "revalidate_worker_provider",
        lambda _contracts: _raise(error),
    )

    result = isolated.measure_isolated(request, b"value = 1\n")

    assert result.gap == expected_gap


def test_isolated_admission_rejects_non_bytes_and_non_isolated_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _worker_request()
    non_bytes = isolated.measure_isolated(request, cast("Any", "value = 1"))
    assert non_bytes.gap == "source_budget_native_contract_invalid"

    resolved = identity.revalidate_worker_provider(request.contracts)
    monkeypatch.setattr(
        isolated,
        "revalidate_worker_provider",
        lambda _contracts: replace(resolved, provider_id="utf8-control"),
    )
    wrong_execution = isolated.measure_isolated(request, b"value = 1\n")
    assert wrong_execution.gap == "source_budget_native_execution_contract_invalid"


def test_isolated_text_and_provider_vocabulary_fail_closed() -> None:
    normalize_text = _member(isolated, "_normalize_text")
    measure_provider = _member(isolated, "_measure_provider")
    with pytest.raises(ValueError, match="source_budget_native_text_embedded_bom"):
        normalize_text(b"a\xef\xbb\xbfb")
    with pytest.raises(ValueError, match="source_budget_native_parse_failed:not-admitted"):
        measure_provider("not-admitted", "")
    with pytest.raises(ValueError, match="structured provider is not admitted"):
        structured.measure_structured("not-admitted", "")


@pytest.mark.parametrize("error", [ValueError("opaque"), AttributeError("opaque")])
def test_router_outer_boundary_maps_untrusted_failures(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    contracts = _contracts("control-source-v2")
    provider = identity.resolve_native_provider(contracts, _registry())
    monkeypatch.setattr(router, "_measure_admitted_route", lambda *_args: _raise(error))

    load = router.measure_native(b"x", provider, _registry())

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_contract_invalid",)


def test_resolved_provider_parser_partition_is_total_disjoint_and_mode_bound() -> None:
    registry = _registry()
    bounded = identity.BOUNDED_PARSER_IDS
    isolated_parsers = identity.ISOLATED_PARSER_IDS
    observed: set[str] = set()

    assert bounded.isdisjoint(isolated_parsers)
    for profile_id in sorted({contract.metric_profile for contract in registry.contracts}):
        resolved = identity.resolve_native_provider(_contracts(profile_id), registry)
        parser_id = resolved.contracts[0].parser_id
        observed.add(parser_id)
        assert (parser_id in bounded) == (
            resolved.execution_descriptor.execution_mode == "bounded_in_process_v1"
        )
        assert (parser_id in isolated_parsers) == (
            resolved.execution_descriptor.execution_mode == "isolated_worker_v1"
        )

    assert observed == bounded | isolated_parsers


def test_router_supervisor_gap_replay_requires_one_admitted_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"value = 1\n"
    contracts = _contracts("python-source-v2")
    provider = identity.resolve_native_provider(contracts, _registry())
    multiple = NativeMeasurementLoad(None, ("a", "b"))
    monkeypatch.setattr(router, "run_isolated_worker", lambda *_args: multiple)
    invalid = router.measure_native(content, provider, _registry())

    child = NativeMeasurementLoad(None, ("source_budget_native_contract_invalid",))
    monkeypatch.setattr(router, "run_isolated_worker", lambda *_args: child)
    replayed = router.measure_native(content, provider, _registry())

    assert invalid.required_gaps == ("source_budget_worker_protocol_invalid",)
    assert replayed == child


def test_exact_carrier_read_uses_one_bounded_read_and_returns_that_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"abc"
    calls: list[tuple[int, int]] = []

    def read(fd: int, amount: int) -> bytes:
        calls.append((fd, amount))
        if len(calls) != 1:
            pytest.fail("carrier bytes must come from exactly one os.read")
        return payload

    monkeypatch.setattr(measurement.os, "read", read)
    read_exact = _member(measurement, "_read_exact")

    content = read_exact(41, len(payload), 8)

    assert content is payload
    assert calls == [(41, len(payload) + 1)]


@pytest.mark.parametrize(
    ("expected_size", "limit", "payload", "error_name"),
    [
        (3, 3, b"abcd", "_CarrierBytesExceededError"),
        (3, 8, b"abcd", "_ObjectChangedError"),
    ],
)
def test_exact_carrier_read_checks_limit_before_size_drift(
    monkeypatch: pytest.MonkeyPatch,
    expected_size: int,
    limit: int,
    payload: bytes,
    error_name: str,
) -> None:
    calls: list[tuple[int, int]] = []

    def read(fd: int, amount: int) -> bytes:
        calls.append((fd, amount))
        return payload

    monkeypatch.setattr(measurement.os, "read", read)
    read_exact = _member(measurement, "_read_exact")
    error_type = _member(measurement, error_name)

    with pytest.raises(error_type):
        read_exact(43, expected_size, limit)

    assert calls == [(43, min(expected_size + 1, limit + 1))]


def test_carrier_measurement_maps_contract_resolution_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_bytes(b"value = 1\n")
    carrier = CarrierIdentity.model_validate(
        {
            "carrier_id": "native-edge-python",
            "role": "authored_behavioral_source",
            "scope_id": "test.native-edge",
            "disposition": "measure",
            "include": ("*.py",),
            "owner": "tests",
            "metric_profile": "python-source-v2",
        }
    )
    manifest = CarrierManifest.model_validate(
        {
            "schema": "ethos-source-budget-carriers-v2",
            "contract_version": 2,
            "carriers": (carrier,),
        }
    )
    match = classify_carriers((relative,), manifest).matches[0]
    monkeypatch.setattr(
        measurement,
        "resolve_metric_contracts",
        lambda *_args: _raise(ValueError("opaque")),
    )

    load = measurement.measure_carrier(tmp_path, match, _registry())

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_measurement_contract_invalid:sample.py",)
