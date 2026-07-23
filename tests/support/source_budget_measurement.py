"""Test-only direct access to concrete native measurement owners."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos.adapters.repo.source_budget.measurement.native.bounded.core import (
    measure_bounded_resolved,
)
from ethos.adapters.repo.source_budget.measurement.native.identity import resolve_native_provider
from ethos.adapters.repo.source_budget.measurement.native.isolated.core import measure_isolated
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import replay_worker_result
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.metrics import MetricContract
    from ethos_core.contracts.source_budget.metrics import MetricContractSet

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _registry() -> MetricContractSet:
    load = load_metric_contracts(ROOT)
    assert load.required_gaps == ()
    assert load.contracts is not None
    return load.contracts


def worker_request(
    content: bytes,
    contracts: tuple[MetricContract, ...],
    registry: MetricContractSet | None = None,
) -> WorkerRequest:
    """Create one exact child request from canonical provider identity."""
    resolved = resolve_native_provider(contracts, _registry() if registry is None else registry)
    return WorkerRequest.create(
        content=content,
        contracts=resolved.contracts,
        provider_descriptor=resolved.provider_descriptor,
        execution_descriptor=resolved.execution_descriptor,
    )


def measure_isolated_provider(
    content: bytes,
    contracts: tuple[MetricContract, ...],
    registry: MetricContractSet | None = None,
) -> NativeMeasurementLoad:
    """Run one complex provider directly through its child-only engine."""
    try:
        request = worker_request(content, contracts, registry)
        result = measure_isolated(request, content)
    except MemoryError:
        return NativeMeasurementLoad(None, ("source_budget_native_resource_exhausted",))
    except ValueError as exc:
        gap = str(exc)
        return NativeMeasurementLoad(
            None,
            (gap if gap.startswith("source_budget_") else "source_budget_native_contract_invalid",),
        )
    if result.gap is not None:
        return NativeMeasurementLoad(None, (result.gap,))
    return NativeMeasurementLoad(replay_worker_result(request, result), ())


def measure_provider(
    content: bytes,
    contracts: tuple[MetricContract, ...],
    registry: MetricContractSet | None = None,
) -> NativeMeasurementLoad:
    """Run the concrete engine selected by static parser identity."""
    registry = _registry() if registry is None else registry
    try:
        resolved = resolve_native_provider(contracts, registry)
    except MemoryError:
        return NativeMeasurementLoad(None, ("source_budget_native_resource_exhausted",))
    except ValueError as exc:
        gap = str(exc)
        return NativeMeasurementLoad(
            None,
            (gap if gap.startswith("source_budget_") else "source_budget_native_contract_invalid",),
        )
    if resolved.execution_descriptor.execution_mode == "bounded_in_process_v1":
        return measure_bounded_resolved(content, resolved)
    return measure_isolated_provider(content, resolved.contracts, registry)
