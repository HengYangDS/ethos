"""Static parser-identity router for native source measurement."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from ethos.adapters.repo.source_budget.measurement.native.bounded.core import (
    measure_bounded_resolved,
)
from ethos.adapters.repo.source_budget.measurement.native.identity import BOUNDED_PARSER_IDS
from ethos.adapters.repo.source_budget.measurement.native.identity import BOUNDED_PROVIDER_IDS
from ethos.adapters.repo.source_budget.measurement.native.identity import ISOLATED_PARSER_IDS
from ethos.adapters.repo.source_budget.measurement.native.identity import ISOLATED_PROVIDER_IDS
from ethos.adapters.repo.source_budget.measurement.native.identity import ResolvedNativeProvider
from ethos.adapters.repo.source_budget.measurement.native.identity import (
    admit_resolved_native_provider,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.core import run_isolated_worker
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import (
    admit_child_worker_gap,
)
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.measurements import NativeMeasurement
    from ethos_core.contracts.source_budget.metrics import MetricContractSet

_PARENT_WORKER_GAPS = frozenset(
    {
        "source_budget_worker_unavailable",
        "source_budget_worker_isolation_unsupported",
        "source_budget_worker_timeout",
        "source_budget_worker_resource_exhausted",
        "source_budget_worker_output_exceeded",
        "source_budget_worker_protocol_invalid",
        "source_budget_worker_failed",
    }
)
_SUPERVISOR_TRUST_BOUNDARY_FAILURES = (Exception,)


def measure_native(
    content: bytes,
    provider: ResolvedNativeProvider,
    registry: MetricContractSet,
) -> NativeMeasurementLoad:
    """Route exact bytes by descriptor-owned parser identity only."""
    try:
        return _measure_admitted_route(content, provider, registry)
    except MemoryError:
        return _failure("source_budget_native_resource_exhausted")
    except ValueError as exc:
        gap = str(exc)
        if gap.startswith("source_budget_native_"):
            return _failure(gap)
        return _failure("source_budget_native_contract_invalid")
    except (AttributeError, IndexError, KeyError, TypeError, ValidationError):
        return _failure("source_budget_native_contract_invalid")


def _measure_admitted_route(
    content: bytes,
    provider: ResolvedNativeProvider,
    registry: MetricContractSet,
) -> NativeMeasurementLoad:
    if type(content) is not bytes:
        return _failure("source_budget_native_contract_invalid")
    resolved = admit_resolved_native_provider(provider, registry)
    if len(content) > resolved.execution_descriptor.max_carrier_bytes:
        return _failure("source_budget_native_carrier_bytes_exceeded")
    parser_id = resolved.contracts[0].parser_id
    if parser_id in BOUNDED_PARSER_IDS:
        if (
            resolved.provider_id not in BOUNDED_PROVIDER_IDS
            or resolved.execution_descriptor.execution_mode != "bounded_in_process_v1"
        ):
            return _failure("source_budget_native_execution_contract_invalid")
        return measure_bounded_resolved(content, resolved)
    if (
        parser_id not in ISOLATED_PARSER_IDS
        or resolved.provider_id not in ISOLATED_PROVIDER_IDS
        or resolved.execution_descriptor.execution_mode != "isolated_worker_v1"
    ):
        return _failure("source_budget_native_execution_contract_invalid")
    request = WorkerRequest.create(
        content=content,
        contracts=resolved.contracts,
        provider_descriptor=resolved.provider_descriptor,
        execution_descriptor=resolved.execution_descriptor,
    )
    return _run_supervisor(request, content)


def _run_supervisor(request: WorkerRequest, content: bytes) -> NativeMeasurementLoad:
    try:
        load = run_isolated_worker(request, content)
    except MemoryError:
        return _failure("source_budget_worker_failed")
    except _SUPERVISOR_TRUST_BOUNDARY_FAILURES:
        return _failure("source_budget_worker_failed")
    return _replay_supervisor_load(request, load)


def _replay_supervisor_load(
    request: WorkerRequest,
    load: NativeMeasurementLoad,
) -> NativeMeasurementLoad:
    if type(load) is not NativeMeasurementLoad:
        return _failure("source_budget_worker_protocol_invalid")
    try:
        canonical = NativeMeasurementLoad(load.measurement, load.required_gaps)
        if canonical.measurement is None:
            return _replay_supervisor_gap(canonical)
        return _replay_supervisor_measurement(request, canonical.measurement)
    except MemoryError:
        return _failure("source_budget_worker_failed")
    except _SUPERVISOR_TRUST_BOUNDARY_FAILURES:
        return _failure("source_budget_worker_protocol_invalid")


def _replay_supervisor_gap(
    load: NativeMeasurementLoad,
) -> NativeMeasurementLoad:
    if len(load.required_gaps) != 1:
        return _failure("source_budget_worker_protocol_invalid")
    gap = load.required_gaps[0]
    if gap not in _PARENT_WORKER_GAPS:
        admit_child_worker_gap(gap)
    return load


def _replay_supervisor_measurement(
    request: WorkerRequest,
    measurement: NativeMeasurement,
) -> NativeMeasurementLoad:
    if (
        measurement.content_sha256 != request.content_sha256
        or measurement.contracts != request.contracts
        or measurement.resolved_contracts_digest != request.resolved_contracts_digest
    ):
        return _failure("source_budget_worker_protocol_invalid")
    return NativeMeasurementLoad(measurement, ())


def _failure(gap: str) -> NativeMeasurementLoad:
    return NativeMeasurementLoad(None, (gap,))
