# ruff: noqa: INP001

from __future__ import annotations

import importlib
import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierManifest
from ethos_core.contracts.source_budget.carriers import classify_carriers
from ethos_core.contracts.source_budget.metrics import metric_provider_resource_contract
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts

if TYPE_CHECKING:
    from types import ModuleType

    import pytest

    from ethos_core.contracts.source_budget.carriers import CarrierInventory
    from ethos_core.contracts.source_budget.metrics import MetricContract
    from ethos_core.contracts.source_budget.metrics import MetricContractSet

ROOT = Path(__file__).resolve().parents[5]
MEASUREMENT_MODULE = "ethos.adapters.repo.source_budget.measurement.core"
NATIVE_MODULE = "ethos.adapters.repo.source_budget.measurement.native.core"


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


def _python_limit() -> int:
    _mode, limit = metric_provider_resource_contract(_python_contracts())
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


def test_carrier_resolves_provider_resource_contract_before_first_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "sample.py"
    (tmp_path / relative).write_bytes(b"value = 1\n")
    module = _measurement()
    real_resolve = module.resolve_metric_contracts
    real_read = os.read
    events: list[str] = []

    def resolve(*args: object):
        events.append("resolve")
        return real_resolve(*args)

    def read(fd: int, size: int) -> bytes:
        events.append("read")
        return real_read(fd, size)

    monkeypatch.setattr(module, "resolve_metric_contracts", resolve)
    monkeypatch.setattr(module.os, "read", read)
    load = module.measure_carrier(tmp_path, _inventory((relative,)).matches[0], _registry())

    assert load.measurement is not None
    assert events[0] == "resolve"
    assert "read" in events


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


def test_carrier_growth_beyond_limit_uses_bounded_probe_and_size_gap(
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
    assert load.required_gaps == (f"source_budget_measurement_carrier_bytes_exceeded:{relative}",)
    assert appended is True
    assert probed <= limit + 1


def test_direct_native_oversize_rejects_before_conformance_decode_or_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    calls = {"conformance": 0, "decode": 0, "provider": 0}
    real_normalize = module._normalize_text
    real_provider = module._measure_provider

    def conformance() -> tuple[str, ...]:
        calls["conformance"] += 1
        return ()

    def normalize(content: bytes) -> str:
        calls["decode"] += 1
        return real_normalize(content)

    def provider(provider_id: str, text: str):
        calls["provider"] += 1
        return real_provider(provider_id, text)

    monkeypatch.setattr(module, "_startup_conformance", conformance)
    monkeypatch.setattr(module, "_normalize_text", normalize)
    monkeypatch.setattr(module, "_measure_provider", provider)
    load = module.measure_native(_python_comment(_python_limit() + 1), _python_contracts())

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_carrier_bytes_exceeded",)
    assert calls == {"conformance": 0, "decode": 0, "provider": 0}


def test_direct_native_rejects_homogeneous_forged_provider_resource_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _native()
    startup_calls = 0

    def conformance() -> tuple[str, ...]:
        nonlocal startup_calls
        startup_calls += 1
        return ()

    limit = _python_limit()
    forged = tuple(
        contract.model_copy(update={"max_carrier_bytes": limit // 2})
        for contract in _python_contracts()
    )
    monkeypatch.setattr(module, "_startup_conformance", conformance)
    load = module.measure_native(b"pass\n", forged)

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_provider_signature_mismatch",)
    assert startup_calls == 0


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
