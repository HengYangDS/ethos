from __future__ import annotations

import hashlib
import json
from typing import Any

from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierInventory
from ethos_core.contracts.source_budget.carriers import CarrierManifest
from ethos_core.contracts.source_budget.carriers import CarrierMatch
from ethos_core.contracts.source_budget.carriers import classify_carrier
from ethos_core.contracts.source_budget.carriers import classify_carriers
from ethos_core.contracts.source_budget.measurements import CarrierMeasurement
from ethos_core.contracts.source_budget.measurements import MeasurementCoordinate
from ethos_core.contracts.source_budget.measurements import MeasurementSnapshot
from ethos_core.contracts.source_budget.measurements import MetricValue
from ethos_core.contracts.source_budget.measurements import NativeMeasurement
from ethos_core.contracts.source_budget.metrics import MetricContract
from ethos_core.contracts.source_budget.metrics import MetricContractSet
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts

RAW_A = "a" * 64
RAW_B = "b" * 64
NORMALIZED = "c" * 64


def _identity(
    *,
    carrier_id: str = "python-source",
    disposition: str = "measure",
    **overrides: Any,
) -> CarrierIdentity:
    metric_profile = overrides.pop("metric_profile", "python-source-v2")
    payload: dict[str, Any] = {
        "carrier_id": carrier_id,
        "role": "authored_behavioral_source",
        "scope_id": "product.python",
        "disposition": disposition,
        "extensions": (".py",),
        "include": ("packages/**",),
        "exclude": (),
        "owner": "ethos-product",
    }
    payload.update(overrides)
    if disposition == "measure":
        payload["metric_profile"] = metric_profile
    else:
        payload["exclusion_reason"] = "reviewed exclusion"
    return CarrierIdentity.model_validate(payload)


def _inventory(
    paths: tuple[str, ...],
    identities: tuple[CarrierIdentity, ...] | None = None,
) -> CarrierInventory:
    manifest = CarrierManifest.model_validate(
        {
            "schema": "ethos-source-budget-carriers-v2",
            "contract_version": 2,
            "carriers": identities or (_identity(),),
        }
    )
    return classify_carriers(paths, manifest)


def _contract(metric_id: str, unit: str) -> MetricContract:
    return MetricContract.model_validate(
        {
            "contract_id": f"python-source-v2:{metric_id}",
            "contract_version": 3,
            "metric_id": metric_id,
            "unit": unit,
            "carrier_role": "authored_behavioral_source",
            "metric_profile": "python-source-v2",
            "parser_id": "python-tokenize",
            "parser_version": "cpython-3.14+ethos-python-lexical-v1",
            "grammar_digest": "2" * 64,
            "normalization_id": "python-source",
            "normalization_version": "1",
            "aggregation": "sum",
            "non_compensable": True,
            "execution_mode": "bounded_in_process_v1",
            "max_carrier_bytes": 65536,
        }
    )


def _contracts() -> tuple[MetricContract, ...]:
    return (
        _contract("lexical_tokens", "lexical_token"),
        _contract("normalized_bytes", "normalized_byte"),
    )


def _contract_set(
    contracts: tuple[MetricContract, ...] | None = None,
) -> MetricContractSet:
    resolved = contracts or _contracts()
    return MetricContractSet.model_validate(
        {
            "schema": "ethos-source-budget-metrics-v3",
            "contract_version": 3,
            "profiles": (
                {
                    "profile_id": "python-source-v2",
                    "carrier_role": "authored_behavioral_source",
                    "required_metric_ids": tuple(item.metric_id for item in resolved),
                },
            ),
            "contracts": resolved,
        }
    )


def _match(
    relative_path: str = "packages/sample.py",
    identity: CarrierIdentity | None = None,
) -> CarrierMatch:
    selected = identity or _identity()
    manifest = CarrierManifest.model_validate(
        {
            "schema": "ethos-source-budget-carriers-v2",
            "contract_version": 2,
            "carriers": (selected,),
        }
    )
    return classify_carrier(relative_path, manifest)


def _value(
    metric_id: str = "lexical_tokens",
    unit: str = "lexical_token",
    value: int = 3,
) -> MetricValue:
    return MetricValue(
        contract_id=f"python-source-v2:{metric_id}",
        metric_id=metric_id,
        unit=unit,
        value=value,
    )


def _native(
    *,
    content_sha256: str = RAW_A,
    contracts: tuple[MetricContract, ...] | None = None,
    values: tuple[MetricValue, ...] | None = None,
) -> NativeMeasurement:
    resolved_contracts = _contracts() if contracts is None else contracts
    metric_values = (
        (_value(), _value("normalized_bytes", "normalized_byte", 17)) if values is None else values
    )
    return NativeMeasurement.create(
        content_sha256=content_sha256,
        normalized_digest=NORMALIZED,
        contracts=resolved_contracts,
        values=metric_values,
    )


def _carrier(
    *,
    relative_path: str = "packages/sample.py",
    identity: CarrierIdentity | None = None,
    native: NativeMeasurement | None = None,
    contracts: MetricContractSet | None = None,
) -> CarrierMeasurement:
    selected = identity or _identity()
    registry = contracts or _contract_set()
    return CarrierMeasurement.create(
        match=_match(relative_path, selected),
        contracts=registry,
        native=native or _native(contracts=resolve_metric_contracts(selected, registry)),
    )


def _snapshot(
    measurements: tuple[CarrierMeasurement, ...] | None = None,
    *,
    inventory: CarrierInventory | None = None,
    contracts: MetricContractSet | None = None,
) -> MeasurementSnapshot:
    registry = contracts or _contract_set()
    measured = (_carrier(contracts=registry),) if measurements is None else measurements
    if inventory is None:
        identities = {item.identity.carrier_id: item.identity for item in measured}
        inventory = _inventory(
            tuple(item.relative_path for item in measured),
            tuple(identities[key] for key in sorted(identities)),
        )
    return MeasurementSnapshot.from_inventory(
        inventory=inventory,
        contracts=registry,
        measurements=measured,
    )


def _resolved_digest(contracts: tuple[MetricContract, ...]) -> str:
    return _canonical_digest(
        "resolved_metric_contracts",
        [item.model_dump(mode="json") for item in contracts],
    )


def _native_digest(
    *,
    content_sha256: str,
    normalized_digest: str,
    resolved_contracts_digest: str,
    values: tuple[MetricValue, ...],
) -> str:
    return _canonical_digest(
        "native_measurement",
        {
            "content_sha256": content_sha256,
            "normalized_digest": normalized_digest,
            "resolved_contracts_digest": resolved_contracts_digest,
            "values": [item.model_dump(mode="json") for item in values],
        },
    )


def _carrier_digest(
    *,
    relative_path: str,
    identity: CarrierIdentity,
    contract_set_digest: str,
    native: NativeMeasurement,
) -> str:
    payload = identity.model_dump(mode="json")
    for field in ("extensions", "include", "exclude"):
        payload[field] = sorted(payload[field])
    return _canonical_digest(
        "carrier_measurement",
        {
            "relative_path": relative_path,
            "identity": payload,
            "contract_set_digest": contract_set_digest,
            "native_measurement_digest": native.measurement_digest,
        },
    )


def _vector_digest(coordinates: tuple[MeasurementCoordinate, ...]) -> str:
    return _canonical_digest(
        "measurement_vector",
        [item.model_dump(mode="json") for item in coordinates],
    )


def _snapshot_digest(
    *,
    manifest_digest: str,
    inventory_digest: str,
    contract_set_digest: str,
    measurements: tuple[CarrierMeasurement, ...],
    coordinates: tuple[MeasurementCoordinate, ...],
) -> str:
    return _canonical_digest(
        "measurement_snapshot",
        {
            "manifest_digest": manifest_digest,
            "inventory_digest": inventory_digest,
            "contract_set_digest": contract_set_digest,
            "measurements": [
                {
                    "relative_path": item.relative_path,
                    "measurement_digest": item.measurement_digest,
                }
                for item in measurements
            ],
            "coordinates": [item.model_dump(mode="json") for item in coordinates],
            "vector_digest": _vector_digest(coordinates),
        },
    )


def _canonical_digest(kind: str, payload: object) -> str:
    encoded = json.dumps(
        {"kind": kind, "schema_version": 1, "payload": payload},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
