from __future__ import annotations

import importlib
import os
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierManifest
from ethos_core.contracts.source_budget.carriers import classify_carriers
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad
from ethos_core.contracts.source_budget.metrics import metric_provider_resource_contract
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts

if TYPE_CHECKING:
    from types import ModuleType

    import pytest

    from ethos.adapters.repo.source_budget.measurement.native.identity import ResolvedNativeProvider
    from ethos_core.contracts.source_budget.carriers import CarrierInventory
    from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
    from ethos_core.contracts.source_budget.metrics import MetricContract
    from ethos_core.contracts.source_budget.metrics import MetricContractSet

ROOT = Path(__file__).resolve().parents[5]
MEASUREMENT_MODULE = "ethos.adapters.repo.source_budget.measurement.core"
NATIVE_MODULE = "ethos.adapters.repo.source_budget.measurement.router"
NATIVE_IDENTITY_MODULE = "ethos.adapters.repo.source_budget.measurement.native.identity"


@lru_cache(maxsize=1)
def _registry() -> MetricContractSet:
    load = load_metric_contracts(ROOT)
    assert load.contracts is not None
    assert load.required_gaps == ()
    return load.contracts


@lru_cache(maxsize=1)
def _python_identity() -> CarrierIdentity:
    return CarrierIdentity.model_validate(
        {
            "carrier_id": "resource-boundary-python",
            "role": "authored_behavioral_source",
            "scope_id": "test.resource-boundary",
            "disposition": "measure",
            "include": ("*.py",),
            "owner": "tests",
            "metric_profile": "python-source-v2",
        }
    )


def _inventory(paths: tuple[str, ...]) -> CarrierInventory:
    manifest = CarrierManifest.model_validate(
        {
            "schema": "ethos-source-budget-carriers-v2",
            "contract_version": 2,
            "carriers": (_python_identity(),),
        }
    )
    return classify_carriers(paths, manifest)


@lru_cache(maxsize=1)
def _python_contracts() -> tuple[MetricContract, ...]:
    return resolve_metric_contracts(_python_identity(), _registry())


def _contracts(profile: str) -> tuple[MetricContract, ...]:
    return tuple(
        sorted(
            (contract for contract in _registry().contracts if contract.metric_profile == profile),
            key=lambda contract: (contract.metric_id, contract.unit, contract.contract_id),
        )
    )


def _python_limit() -> int:
    _mode, limit, _execution_id, _execution_digest = metric_provider_resource_contract(
        _python_contracts()
    )
    return limit


def _python_comment(size: int) -> bytes:
    assert size >= 2
    content = b"#" + (b"x" * (size - 2)) + b"\n"
    assert len(content) == size
    return content


def _measurement() -> ModuleType:
    return importlib.import_module(MEASUREMENT_MODULE)


def _native() -> ModuleType:
    return importlib.import_module(NATIVE_MODULE)


def test_carrier_resolves_complete_provider_before_open_and_routes_same_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_bytes(b"value = 1\n")
    module = _measurement()
    identity = importlib.import_module(NATIVE_IDENTITY_MODULE)
    real_resolve = identity.resolve_native_provider
    real_open = os.open
    real_read = os.read
    real_route = module.measure_native
    events: list[str] = []
    resolved: list[ResolvedNativeProvider] = []
    routed: list[ResolvedNativeProvider] = []

    def resolve(
        contracts: tuple[MetricContract, ...],
        registry: MetricContractSet,
    ) -> ResolvedNativeProvider:
        events.append("resolve")
        provider = real_resolve(contracts, registry)
        resolved.append(provider)
        assert provider.provider_descriptor["execution"] == (
            provider.execution_descriptor.model_dump(mode="json")
        )
        return provider

    def opened(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        *args: int,
        dir_fd: int | None = None,
    ) -> int:
        events.append("open")
        return real_open(path, flags, *args, dir_fd=dir_fd)

    def read(fd: int, size: int) -> bytes:
        events.append("read")
        return real_read(fd, size)

    def route(
        content: bytes,
        provider: ResolvedNativeProvider,
        registry: MetricContractSet,
    ) -> NativeMeasurementLoad:
        events.append("route")
        routed.append(provider)
        return real_route(content, provider, registry)

    monkeypatch.setattr(module, "resolve_native_provider", resolve, raising=False)
    monkeypatch.setattr(module.os, "open", opened)
    monkeypatch.setattr(module.os, "read", read)
    monkeypatch.setattr(module, "measure_native", route)
    load = module.measure_carrier(tmp_path, _inventory((relative,)).matches[0], _registry())

    assert load.measurement is not None
    assert events[0] == "resolve"
    assert events.index("resolve") < events.index("open") < events.index("read")
    assert events.index("read") < events.index("route")
    assert len(resolved) == 1
    assert routed[0] is resolved[0]


def test_native_router_uses_pre_resolved_provider_without_reconstructing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    identity = importlib.import_module(NATIVE_IDENTITY_MODULE)
    resolved = identity.resolve_native_provider(_python_contracts(), _registry())
    reconstruction_calls = 0
    requests: list[WorkerRequest] = []

    def reconstruct(*_args: object) -> object:
        nonlocal reconstruction_calls
        reconstruction_calls += 1
        return resolved

    def supervisor(request: WorkerRequest, content: bytes) -> NativeMeasurementLoad:
        assert content == b"pass\n"
        requests.append(request)
        return NativeMeasurementLoad(None, ("source_budget_worker_unavailable",))

    monkeypatch.setattr(identity, "resolve_native_provider", reconstruct)
    monkeypatch.setattr(module, "run_isolated_worker", supervisor)
    load = module.measure_native(b"pass\n", resolved, _registry())

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_worker_unavailable",)
    assert reconstruction_calls == 0
    assert len(requests) == 1
    assert requests[0].contracts == resolved.contracts
    assert requests[0].provider_digest == resolved.contracts[0].grammar_digest
    assert requests[0].execution_contract_digest == resolved.contracts[0].execution_contract_digest


def test_native_router_passes_same_pre_resolved_provider_to_bounded_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    identity = importlib.import_module(NATIVE_IDENTITY_MODULE)
    bounded_module = importlib.import_module(
        "ethos.adapters.repo.source_budget.measurement.native.bounded.core"
    )
    resolved = identity.resolve_native_provider(_contracts("control-source-v2"), _registry())
    reconstruction_calls = 0
    routed: list[ResolvedNativeProvider] = []

    def reconstruct(*_args: object) -> object:
        nonlocal reconstruction_calls
        reconstruction_calls += 1
        return resolved

    def bounded(
        content: bytes,
        provider: ResolvedNativeProvider,
    ) -> NativeMeasurementLoad:
        assert content == b"ethos\n"
        routed.append(provider)
        return NativeMeasurementLoad(None, ("source_budget_native_runtime_unsupported",))

    monkeypatch.setattr(bounded_module, "resolve_native_provider", reconstruct)
    monkeypatch.setattr(module, "measure_bounded_resolved", bounded)
    load = module.measure_native(b"ethos\n", resolved, _registry())

    assert load.required_gaps == ("source_budget_native_runtime_unsupported",)
    assert reconstruction_calls == 0
    assert routed == [resolved]
    assert routed[0] is resolved


def test_native_router_rejects_forged_resolved_provider_before_any_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    identity = importlib.import_module(NATIVE_IDENTITY_MODULE)
    canonical = identity.resolve_native_provider(_python_contracts(), _registry())
    bounded = identity.resolve_native_provider(_contracts("control-source-v2"), _registry())
    engine_calls = 0

    class ForgedResolvedNativeProvider(identity.ResolvedNativeProvider):
        pass

    class ForgedProviderId(str):
        __slots__ = ()

    def engine(*_args: object) -> NativeMeasurementLoad:
        nonlocal engine_calls
        engine_calls += 1
        return NativeMeasurementLoad(None, ("unexpected",))

    monkeypatch.setattr(module, "measure_bounded_resolved", engine)
    monkeypatch.setattr(module, "run_isolated_worker", engine)
    forged = (
        replace(canonical, provider_id="utf8-control"),
        replace(canonical, provider_id=ForgedProviderId(canonical.provider_id)),
        replace(canonical, provider_descriptor=bounded.provider_descriptor),
        replace(canonical, execution_descriptor=bounded.execution_descriptor),
        replace(canonical, contracts=()),
        ForgedResolvedNativeProvider(
            provider_id=canonical.provider_id,
            contracts=canonical.contracts,
            provider_descriptor=canonical.provider_descriptor,
            execution_descriptor=canonical.execution_descriptor,
        ),
    )

    for provider in forged:
        load = module.measure_native(b"pass\n", provider, _registry())
        assert load.measurement is None
        assert load.required_gaps in {
            ("source_budget_native_contract_invalid",),
            ("source_budget_native_provider_signature_mismatch",),
        }

    assert engine_calls == 0


def test_native_router_defense_rejects_mismatched_admission_before_engines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    identity = importlib.import_module(NATIVE_IDENTITY_MODULE)
    isolated = identity.resolve_native_provider(_python_contracts(), _registry())
    bounded = identity.resolve_native_provider(_contracts("control-source-v2"), _registry())
    engine_calls = 0

    def engine(*_args: object) -> NativeMeasurementLoad:
        nonlocal engine_calls
        engine_calls += 1
        return NativeMeasurementLoad(None, ("unexpected",))

    def admit(
        provider: ResolvedNativeProvider,
        registry: MetricContractSet,
    ) -> ResolvedNativeProvider:
        assert registry is _registry()
        return provider

    monkeypatch.setattr(module, "admit_resolved_native_provider", admit)
    monkeypatch.setattr(module, "measure_bounded_resolved", engine)
    monkeypatch.setattr(module, "run_isolated_worker", engine)
    mismatched = (
        replace(bounded, provider_id=isolated.provider_id),
        replace(isolated, execution_descriptor=bounded.execution_descriptor),
    )

    for provider in mismatched:
        load = module.measure_native(b"pass\n", provider, _registry())
        assert load.measurement is None
        assert load.required_gaps == ("source_budget_native_execution_contract_invalid",)

    assert engine_calls == 0


def test_carrier_rejects_initial_limit_plus_one_before_any_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "oversize.py"
    limit = _python_limit()
    (tmp_path / relative).write_bytes(_python_comment(limit + 1))
    module = _measurement()
    real_read = os.read
    reads = 0

    def read(fd: int, size: int) -> bytes:
        nonlocal reads
        reads += 1
        return real_read(fd, size)

    monkeypatch.setattr(module.os, "read", read)
    load = module.measure_carrier(tmp_path, _inventory((relative,)).matches[0], _registry())

    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_carrier_bytes_exceeded:{relative}",)
    assert reads == 0


def test_carrier_growth_after_stat_uses_one_size_probe_and_changed_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "growing.py"
    limit = _python_limit()
    path = tmp_path / relative
    path.write_bytes(_python_comment(limit - 8))
    module = _measurement()
    real_read = os.read
    appended = False
    probed = 0

    def grow(fd: int, size: int) -> bytes:
        nonlocal appended, probed
        if not appended:
            appended = True
            with path.open("ab") as stream:
                stream.write(_python_comment(limit + 16))
        chunk = real_read(fd, size)
        probed += len(chunk)
        return chunk

    monkeypatch.setattr(module.os, "read", grow)
    load = module.measure_carrier(tmp_path, _inventory((relative,)).matches[0], _registry())

    assert load.measurement is None
    assert load.required_gaps == (f"source_budget_measurement_object_changed:{relative}",)
    assert appended is True
    assert probed == limit - 7


def test_direct_native_oversize_rejects_before_conformance_decode_or_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    identity = importlib.import_module(NATIVE_IDENTITY_MODULE)
    provider = identity.resolve_native_provider(_python_contracts(), _registry())
    calls = {"bounded": 0, "supervisor": 0}

    def bounded(*_args: object):
        calls["bounded"] += 1
        return object()

    def supervisor(*_args: object):
        calls["supervisor"] += 1
        return object()

    monkeypatch.setattr(module, "measure_bounded_resolved", bounded)
    monkeypatch.setattr(module, "run_isolated_worker", supervisor)
    load = module.measure_native(_python_comment(_python_limit() + 1), provider, _registry())

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_carrier_bytes_exceeded",)
    assert calls == {"bounded": 0, "supervisor": 0}


def test_direct_native_rejects_homogeneous_forged_provider_resource_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    identity = importlib.import_module(NATIVE_IDENTITY_MODULE)
    canonical = identity.resolve_native_provider(_python_contracts(), _registry())
    supervisor_calls = 0

    def supervisor(*_args: object):
        nonlocal supervisor_calls
        supervisor_calls += 1
        return object()

    limit = _python_limit()
    forged = tuple(
        contract.model_copy(update={"max_carrier_bytes": limit // 2})
        for contract in _python_contracts()
    )
    monkeypatch.setattr(module, "run_isolated_worker", supervisor)
    provider = replace(canonical, contracts=forged)
    load = module.measure_native(b"pass\n", provider, _registry())

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_provider_signature_mismatch",)
    assert supervisor_calls == 0


def test_snapshot_discards_valid_measurement_when_one_carrier_is_oversize(
    tmp_path: Path,
) -> None:
    good = "good.py"
    oversize = "oversize.py"
    (tmp_path / good).write_bytes(b"value = 1\n")
    (tmp_path / oversize).write_bytes(_python_comment(_python_limit() + 1))

    load = _measurement().measure_snapshot(
        tmp_path,
        _inventory((good, oversize)),
        _registry(),
    )

    assert load.snapshot is None
    assert load.required_gaps == (f"source_budget_measurement_carrier_bytes_exceeded:{oversize}",)
