from __future__ import annotations

import typing as t
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pytest

from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos.adapters.repo.source_budget.measurement import router
from ethos.adapters.repo.source_budget.measurement.native import identity
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad
from ethos_core.contracts.source_budget.metrics import MetricContract
from ethos_core.contracts.source_budget.metrics import MetricContractSet
from ethos_core.contracts.source_budget.metrics import MetricProfile

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CONTENT = {
    "control-source-v2": b"ethos\r\n",
    "python-source-v2": b"value = 1\n",
}


class _TargetedRaisingSlot:
    def __init__(self, original: object, target: object, error: Exception) -> None:
        self.original = original
        self.target = target
        self.error = error

    def __get__(self, instance: object, owner: type | None = None) -> object:
        if instance is None:
            return self
        if instance is self.target:
            raise self.error
        return t.cast("t.Any", self.original).__get__(instance, owner)

    def __set__(self, instance: object, value: object) -> None:
        t.cast("t.Any", self.original).__set__(instance, value)


@lru_cache(maxsize=1)
def _registry() -> MetricContractSet:
    load = load_metric_contracts(ROOT)
    assert load.required_gaps == ()
    assert load.contracts is not None
    return load.contracts


def _contracts(profile: str) -> tuple[MetricContract, ...]:
    return tuple(
        sorted(
            (item for item in _registry().contracts if item.metric_profile == profile),
            key=lambda item: (item.metric_id, item.unit, item.contract_id),
        )
    )


@pytest.mark.parametrize(
    ("profile", "field", "value"),
    [
        ("control-source-v2", "metric_profile", "unknown-profile"),
        ("control-source-v2", "carrier_role", "documentation"),
        ("python-source-v2", "metric_profile", "unknown-profile"),
        ("python-source-v2", "carrier_role", "documentation"),
    ],
)
def test_unknown_profile_or_wrong_role_is_rejected_before_any_engine(
    monkeypatch: pytest.MonkeyPatch,
    profile: str,
    field: str,
    value: str,
) -> None:
    contracts = _contracts(profile)
    canonical = identity.resolve_native_provider(contracts, _registry())
    forged = tuple(
        item.model_copy(
            update={
                field: value,
                **(
                    {"contract_id": f"{value}:{item.metric_id}"}
                    if field == "metric_profile"
                    else {}
                ),
            }
        )
        for item in contracts
    )
    calls = {"bounded": 0, "supervisor": 0}

    def bounded(*_args: object) -> NativeMeasurementLoad:
        calls["bounded"] += 1
        return NativeMeasurementLoad(None, ("unexpected",))

    def supervisor(*_args: object) -> NativeMeasurementLoad:
        calls["supervisor"] += 1
        return NativeMeasurementLoad(None, ("unexpected",))

    monkeypatch.setattr(router, "measure_bounded_resolved", bounded)
    monkeypatch.setattr(router, "run_isolated_worker", supervisor)
    provider = replace(canonical, contracts=forged)
    load = router.measure_native(SAMPLE_CONTENT[profile], provider, _registry())

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_native_provider_signature_mismatch",)
    assert calls == {"bounded": 0, "supervisor": 0}


def test_registry_context_accepts_a_declared_adopter_profile() -> None:
    registry = _registry()
    base = _contracts("control-source-v2")[0]
    profile_id = "adopter-control-v2"
    profile = MetricProfile(
        profile_id=profile_id,
        carrier_role="documentation",
        required_metric_ids=("normalized_bytes",),
    )
    contract = MetricContract.model_validate(
        base.model_dump(mode="python")
        | {
            "contract_id": f"{profile_id}:normalized_bytes",
            "carrier_role": "documentation",
            "metric_profile": profile_id,
        }
    )
    extended = MetricContractSet.model_validate(
        {
            "schema": registry.schema_id,
            "contract_version": registry.contract_version,
            "profiles": (*registry.profiles, profile),
            "contracts": (*registry.contracts, contract),
        }
    )

    resolved = identity.resolve_native_provider((contract,), extended)

    assert resolved.provider_id == "utf8-control"
    assert resolved.contracts == (contract,)


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError])
def test_supervisor_replay_exceptions_are_protocol_invalid_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    original = NativeMeasurementLoad.measurement
    error = error_type("SENSITIVE")
    forged = NativeMeasurementLoad(None, ("source_budget_worker_unavailable",))
    contracts = _contracts("python-source-v2")
    provider = identity.resolve_native_provider(contracts, _registry())
    calls = {"bounded": 0, "supervisor": 0}

    def bounded(*_args: object) -> NativeMeasurementLoad:
        calls["bounded"] += 1
        return NativeMeasurementLoad(None, ("unexpected",))

    def supervisor(*_args: object) -> NativeMeasurementLoad:
        calls["supervisor"] += 1
        return forged

    monkeypatch.setattr(
        NativeMeasurementLoad,
        "measurement",
        _TargetedRaisingSlot(original, forged, error),
    )
    monkeypatch.setattr(router, "measure_bounded_resolved", bounded)
    monkeypatch.setattr(router, "run_isolated_worker", supervisor)
    load = router.measure_native(b"value = 1\n", provider, _registry())

    assert load.measurement is None
    assert load.required_gaps == ("source_budget_worker_protocol_invalid",)
    assert calls == {"bounded": 0, "supervisor": 1}
    monkeypatch.setattr(
        router, "run_isolated_worker", lambda *_args: (_ for _ in ()).throw(MemoryError("parent"))
    )
    parent = router.measure_native(b"value = 1\n", provider, _registry())
    assert parent.required_gaps == ("source_budget_worker_failed",)
    monkeypatch.setattr(
        NativeMeasurementLoad,
        "measurement",
        _TargetedRaisingSlot(original, forged, MemoryError("replay")),
    )
    monkeypatch.setattr(router, "run_isolated_worker", supervisor)
    replay = router.measure_native(b"value = 1\n", provider, _registry())
    assert replay.required_gaps == ("source_budget_worker_failed",)
