"""Edge contracts for source-budget execution and registry trust boundaries."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Never
from typing import cast

import pytest
from pydantic import BaseModel
from pydantic import ValidationError

from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos_core.contracts.source_budget import metrics
from ethos_core.contracts.source_budget.measurement import execution
from ethos_core.contracts.source_budget.measurement.worker import resource
from ethos_core.contracts.source_budget.measurement.worker.protocol import core as protocol

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _registry() -> metrics.MetricContractSet:
    load = load_metric_contracts(ROOT)
    assert load.required_gaps == ()
    assert load.contracts is not None
    return load.contracts


def _contracts(profile_id: str) -> tuple[metrics.MetricContract, ...]:
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


def _exhaust(*_args: object, **_kwargs: object) -> Never:
    raise MemoryError


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: execution.execution_descriptor(cast("Any", "not-admitted"), 1),
            "execution mode is not admitted",
        ),
        (
            lambda: execution.execution_descriptor_digest(cast("Any", object())),
            "execution descriptor must be canonical",
        ),
        (
            lambda: execution.parser_execution_contract("not-admitted"),
            "parser execution is not admitted",
        ),
        (
            lambda: protocol.worker_protocol_descriptor_digest(cast("Any", object())),
            "protocol descriptor must be canonical",
        ),
        (
            lambda: resource.worker_resource_profile_descriptor_digest(cast("Any", object())),
            "resource profile descriptor must be canonical",
        ),
    ],
)
def test_descriptor_owners_reject_unknown_or_non_model_inputs(
    call: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        cast("Any", call)()


@pytest.mark.parametrize("payload", [object(), {}])
def test_registry_validation_rejects_non_registry_shapes(payload: object) -> None:
    with pytest.raises(ValidationError):
        metrics.validate_metric_contracts(payload)


def test_resolved_contract_admission_rejects_empty_unordered_and_mixed_vectors() -> None:
    registry = _registry()
    python = _contracts("python-source-v2")
    control = _contracts("control-source-v2")

    with pytest.raises(ValueError, match="canonical registry context"):
        metrics.admit_resolved_metric_contracts((), registry)
    with pytest.raises(ValueError, match="resolved vector is not canonical"):
        metrics.admit_resolved_metric_contracts(tuple(reversed(python)), registry)

    mixed = tuple(
        sorted(
            (python[0], control[0]),
            key=lambda contract: (contract.metric_id, contract.unit, contract.contract_id),
        )
    )
    with pytest.raises(ValueError, match="resolved vector is not canonical"):
        metrics.admit_resolved_metric_contracts(mixed, registry)


def test_resolved_contract_admission_preserves_memory_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(BaseModel, "model_dump", _exhaust)

    with pytest.raises(MemoryError):
        metrics.admit_resolved_metric_contracts(
            _contracts("python-source-v2"),
            _registry(),
        )


def test_metric_contract_load_rejects_registry_subclasses() -> None:
    class ForgedMetricContractSet(metrics.MetricContractSet):
        pass

    forged = ForgedMetricContractSet.model_validate(
        _registry().model_dump(mode="python", by_alias=True)
    )

    with pytest.raises(ValueError, match="requires typed contracts"):
        metrics.MetricContractSetLoad(forged, ())


def test_provider_resource_contract_rejects_unknown_parser_identity() -> None:
    contract = _contracts("python-source-v2")[0].model_copy(update={"parser_id": "not-admitted"})

    with pytest.raises(ValueError, match="execution parser is not admitted"):
        metrics.metric_provider_resource_contract((contract,))


def test_metric_contract_failure_load_preserves_explicit_gap() -> None:
    load = metrics.MetricContractSetLoad(None, ("source_budget_metric_contracts_missing",))

    assert load.contracts is None
    assert load.required_gaps == ("source_budget_metric_contracts_missing",)
