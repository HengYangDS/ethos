"""Immutable measurement contracts for Budget Contract v2."""

from __future__ import annotations

from dataclasses import InitVar
from dataclasses import dataclass
from dataclasses import field
from typing import Annotated
from typing import NoReturn
from typing import Self
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictStr
from pydantic import TypeAdapter
from pydantic import ValidationError
from pydantic import field_validator
from pydantic import model_validator

import ethos_core.contracts.source_budget.measurement.admission as admission
import ethos_core.contracts.source_budget.measurement.canonical as canonical
from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierInventory
from ethos_core.contracts.source_budget.carriers import CarrierManifest
from ethos_core.contracts.source_budget.carriers import CarrierMatch
from ethos_core.contracts.source_budget.carriers import classify_carrier
from ethos_core.contracts.source_budget.metrics import MetricContract
from ethos_core.contracts.source_budget.metrics import MetricContractSet
from ethos_core.contracts.source_budget.metrics import MetricUnit
from ethos_core.contracts.source_budget.metrics import metric_contracts_digest
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts

NonEmptyStr = Annotated[StrictStr, Field(min_length=1)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
Sha256 = Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")]
_SHA256_ADAPTER = TypeAdapter(Sha256)


def _error(message: str) -> NoReturn:
    raise ValueError(message)


def _invalid(message: str, value: object) -> NoReturn:
    title = "MeasurementContract"
    raise ValidationError.from_exception_data(
        title,
        [
            {
                "type": "value_error",
                "loc": (),
                "input": value,
                "ctx": {"error": ValueError(message)},
            }
        ],
    )


class MetricValue(BaseModel):
    """One non-compensating native metric result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_id: NonEmptyStr
    metric_id: NonEmptyStr
    unit: MetricUnit
    value: NonNegativeInt


class NativeMeasurement(BaseModel):
    """One exact-byte native provider result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content_sha256: Sha256
    normalized_digest: Sha256
    contracts: tuple[MetricContract, ...] = Field(min_length=1)
    resolved_contracts_digest: Sha256
    values: tuple[MetricValue, ...] = Field(min_length=1)
    measurement_digest: Sha256

    @field_validator("contracts", mode="before")
    @classmethod
    def revalidate_contracts(cls, values: object) -> object:
        return _validated_items(values, MetricContract, "metric contract")

    @field_validator("values", mode="before")
    @classmethod
    def revalidate_values(cls, values: object) -> object:
        return _validated_items(values, MetricValue, "metric value")

    @model_validator(mode="after")
    def validate_measurement(self) -> Self:
        declared = _native_contract_coordinates(self.contracts)
        resolved_digest = canonical.resolved_model_digest(self.contracts)
        if self.resolved_contracts_digest != resolved_digest:
            _error("native measurement resolved-contracts digest must match contracts")
        value_keys = tuple(_item_key(item) for item in self.values)
        if value_keys != tuple(sorted(value_keys)):
            _error("native measurement values must be stably ordered")
        value_coordinates = tuple((item.metric_id, item.unit) for item in self.values)
        if len(value_coordinates) != len(set(value_coordinates)):
            _error("native measurement metric coordinates must be unique")
        value_contract_ids = tuple(item.contract_id for item in self.values)
        if len(value_contract_ids) != len(set(value_contract_ids)):
            _error("native measurement contract ids must be unique")
        measured = {(item.contract_id, item.metric_id, item.unit) for item in self.values}
        if measured != declared:
            _error("native measurement requires the complete declared contract vector")
        if self.measurement_digest != canonical.native_model_digest(
            self.content_sha256,
            self.normalized_digest,
            self.resolved_contracts_digest,
            self.values,
        ):
            _error("native measurement digest must match canonical content")
        return self

    @classmethod
    def create(
        cls,
        *,
        content_sha256: str,
        normalized_digest: str,
        contracts: tuple[MetricContract, ...],
        values: tuple[MetricValue, ...],
    ) -> Self:
        content = _SHA256_ADAPTER.validate_python(content_sha256)
        normalized = _SHA256_ADAPTER.validate_python(normalized_digest)
        resolved_contracts = cast(
            "tuple[MetricContract, ...]",
            _validated_items(contracts, MetricContract, "metric contract"),
        )
        metric_values = cast(
            "tuple[MetricValue, ...]",
            _validated_items(values, MetricValue, "metric value"),
        )
        ordered_contracts = tuple(sorted(resolved_contracts, key=_item_key))
        ordered_values = tuple(sorted(metric_values, key=_item_key))
        resolved_digest = canonical.resolved_model_digest(ordered_contracts)
        return cls(
            content_sha256=content,
            normalized_digest=normalized,
            contracts=ordered_contracts,
            resolved_contracts_digest=resolved_digest,
            values=ordered_values,
            measurement_digest=canonical.native_model_digest(
                content,
                normalized,
                resolved_digest,
                ordered_values,
            ),
        )


class CarrierMeasurement(BaseModel):
    """One descriptor-bound measured carrier observation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relative_path: NonEmptyStr
    identity: CarrierIdentity
    contract_set_digest: Sha256
    native: NativeMeasurement
    measurement_digest: Sha256

    @field_validator("identity", mode="before")
    @classmethod
    def revalidate_identity(cls, value: object) -> object:
        return _validated_model(value, CarrierIdentity, "carrier identity")

    @field_validator("native", mode="before")
    @classmethod
    def revalidate_native(cls, value: object) -> object:
        return _validated_model(value, NativeMeasurement, "native measurement")

    @model_validator(mode="after")
    def validate_measurement(self) -> Self:
        if not canonical.is_valid_relative_path(self.relative_path):
            _error("carrier measurement requires a canonical relative path")
        if self.identity.disposition != "measure":
            _error("carrier measurement requires a measured carrier identity")
        if not _identity_matches_path(self.relative_path, self.identity):
            _error("carrier measurement path must match the complete carrier identity")
        domains = {(item.carrier_role, item.metric_profile) for item in self.native.contracts}
        if domains != {(self.identity.role, self.identity.metric_profile)}:
            _error("carrier measurement identity must match native contracts")
        if self.measurement_digest != canonical.carrier_model_digest(
            self.relative_path,
            self.identity,
            self.contract_set_digest,
            self.native,
        ):
            _error("carrier measurement digest must match canonical content")
        return self

    @classmethod
    def create(
        cls,
        *,
        match: CarrierMatch,
        contracts: MetricContractSet,
        native: NativeMeasurement,
    ) -> Self:
        carrier_match = cast(
            "CarrierMatch",
            _validated_model(match, CarrierMatch, "classified carrier match"),
        )
        contract_set = cast(
            "MetricContractSet",
            _validated_model(contracts, MetricContractSet, "metric contract set"),
        )
        native_result = cast(
            "NativeMeasurement",
            _validated_model(native, NativeMeasurement, "native measurement"),
        )
        if (
            carrier_match.state != "classified"
            or carrier_match.identity is None
            or carrier_match.required_gaps
        ):
            _invalid("carrier measurement requires a classified match", match)
        _require_resolved_native(
            carrier_match.identity,
            contract_set,
            native_result,
            native,
            "carrier measurement",
        )
        contract_digest = metric_contracts_digest(contract_set)
        return cls(
            relative_path=carrier_match.relative_path,
            identity=carrier_match.identity,
            contract_set_digest=contract_digest,
            native=native_result,
            measurement_digest=canonical.carrier_model_digest(
                carrier_match.relative_path,
                carrier_match.identity,
                contract_digest,
                native_result,
            ),
        )


class MeasurementCoordinate(BaseModel):
    """One scope-native non-compensating snapshot coordinate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scope_id: NonEmptyStr
    metric_id: NonEmptyStr
    unit: MetricUnit
    value: NonNegativeInt


class MeasurementSnapshot(BaseModel):
    """Deterministic aggregate over one complete carrier inventory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_digest: Sha256
    inventory_digest: Sha256
    contract_set_digest: Sha256
    measurements: tuple[CarrierMeasurement, ...] = ()
    coordinates: tuple[MeasurementCoordinate, ...] = ()
    vector_digest: Sha256
    snapshot_digest: Sha256

    @field_validator("measurements", mode="before")
    @classmethod
    def revalidate_measurements(cls, values: object) -> object:
        return _validated_items(values, CarrierMeasurement, "carrier measurement")

    @field_validator("coordinates", mode="before")
    @classmethod
    def revalidate_coordinates(cls, values: object) -> object:
        return _validated_items(values, MeasurementCoordinate, "measurement coordinate")

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        paths = tuple(item.relative_path for item in self.measurements)
        if paths != tuple(sorted(set(paths))):
            _error("measurement snapshot carriers must be unique and stably ordered")
        if any(item.contract_set_digest != self.contract_set_digest for item in self.measurements):
            _error("measurement snapshot contract-set digest must match carriers")
        expected_coordinates = _aggregate_measurements(self.measurements)
        if self.coordinates != expected_coordinates:
            _error("measurement snapshot aggregated coordinates must be exact")
        if self.vector_digest != canonical.vector_model_digest(self.coordinates):
            _error("measurement snapshot vector digest must match coordinates")
        if self.snapshot_digest != canonical.snapshot_model_digest(
            self.manifest_digest,
            self.inventory_digest,
            self.contract_set_digest,
            self.measurements,
            self.coordinates,
        ):
            _error("measurement snapshot digest must match canonical content")
        return self

    @classmethod
    def from_inventory(
        cls,
        *,
        inventory: CarrierInventory,
        contracts: MetricContractSet,
        measurements: tuple[CarrierMeasurement, ...],
    ) -> Self:
        source_inventory = cast(
            "CarrierInventory",
            _validated_model(inventory, CarrierInventory, "carrier inventory"),
        )
        contract_set = cast(
            "MetricContractSet",
            _validated_model(contracts, MetricContractSet, "metric contract set"),
        )
        measured = cast(
            "tuple[CarrierMeasurement, ...]",
            _validated_items(measurements, CarrierMeasurement, "carrier measurement"),
        )
        if source_inventory.required_gaps:
            _invalid(
                "measurement snapshot requires a gap-free carrier inventory",
                inventory,
            )
        ordered = tuple(sorted(measured, key=lambda item: item.relative_path))
        classified = tuple(item for item in source_inventory.matches if item.state == "classified")
        expected = tuple((item.relative_path, item.identity) for item in classified)
        actual = tuple((item.relative_path, item.identity) for item in ordered)
        if actual != expected:
            _invalid(
                "measurement snapshot measurements must equal the classified inventory",
                measurements,
            )
        contract_digest = metric_contracts_digest(contract_set)
        if any(item.contract_set_digest != contract_digest for item in ordered):
            _invalid(
                "measurement snapshot contract set must match every carrier",
                contracts,
            )
        for item in ordered:
            _require_resolved_native(
                item.identity,
                contract_set,
                item.native,
                item,
                "measurement snapshot carrier",
            )
        coordinates = _aggregate_measurements(ordered)
        vector_digest = canonical.vector_model_digest(coordinates)
        return cls(
            manifest_digest=source_inventory.manifest_digest,
            inventory_digest=source_inventory.inventory_digest,
            contract_set_digest=contract_digest,
            measurements=ordered,
            coordinates=coordinates,
            vector_digest=vector_digest,
            snapshot_digest=canonical.snapshot_model_digest(
                source_inventory.manifest_digest,
                source_inventory.inventory_digest,
                contract_digest,
                ordered,
                coordinates,
            ),
        )


@dataclass(frozen=True, slots=True)
class NativeMeasurementLoad(admission.FinalLoad):
    measurement: NativeMeasurement | None
    required_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        label = "native measurement"
        validated = admission.validate_load(
            self.measurement,
            NativeMeasurement,
            self.required_gaps,
            label,
            _validated_model,
        )
        object.__setattr__(self, "measurement", validated)


@dataclass(frozen=True, slots=True)
class CarrierMeasurementLoad(admission.FinalLoad):
    measurement: CarrierMeasurement | None
    required_gaps: tuple[str, ...]
    match: InitVar[CarrierMatch | None] = field(default=None, kw_only=True)
    contracts: InitVar[MetricContractSet | None] = field(default=None, kw_only=True)

    def __post_init__(
        self,
        match: CarrierMatch | None,
        contracts: MetricContractSet | None,
    ) -> None:
        label = "carrier measurement"
        validated = admission.validate_load(
            self.measurement,
            CarrierMeasurement,
            self.required_gaps,
            label,
            _validated_model,
        )
        validated = admission.validate_context_load(
            validated,
            (match, contracts),
            (CarrierMatch, MetricContractSet),
            label,
            lambda data: CarrierMeasurement.create(
                match=cast("CarrierMatch", match),
                contracts=cast("MetricContractSet", contracts),
                native=cast("CarrierMeasurement", data).native,
            ),
        )
        object.__setattr__(self, "measurement", validated)


@dataclass(frozen=True, slots=True)
class MeasurementSnapshotLoad(admission.FinalLoad):
    snapshot: MeasurementSnapshot | None
    required_gaps: tuple[str, ...]
    inventory: InitVar[CarrierInventory | None] = field(default=None, kw_only=True)
    contracts: InitVar[MetricContractSet | None] = field(default=None, kw_only=True)

    def __post_init__(
        self,
        inventory: CarrierInventory | None,
        contracts: MetricContractSet | None,
    ) -> None:
        label = "measurement snapshot"
        validated = admission.validate_load(
            self.snapshot,
            MeasurementSnapshot,
            self.required_gaps,
            label,
            _validated_model,
        )
        validated = admission.validate_context_load(
            validated,
            (inventory, contracts),
            (CarrierInventory, MetricContractSet),
            label,
            lambda data: MeasurementSnapshot.from_inventory(
                inventory=cast("CarrierInventory", inventory),
                contracts=cast("MetricContractSet", contracts),
                measurements=cast("MeasurementSnapshot", data).measurements,
            ),
        )
        object.__setattr__(self, "snapshot", validated)


def _native_contract_coordinates(
    contracts: tuple[MetricContract, ...],
) -> set[tuple[str, str, MetricUnit]]:
    contract_keys = tuple(_item_key(item) for item in contracts)
    if contract_keys != tuple(sorted(contract_keys)):
        _error("native measurement contracts must be stably ordered")
    contract_ids = tuple(item.contract_id for item in contracts)
    if len(contract_ids) != len(set(contract_ids)):
        _error("native measurement contract ids must be unique")
    coordinates = tuple((item.metric_id, item.unit) for item in contracts)
    if len(coordinates) != len(set(coordinates)):
        _error("native measurement contract coordinates must be unique")
    domains = {(item.carrier_role, item.metric_profile) for item in contracts}
    if len(domains) != 1:
        _error("native measurement contracts must share one carrier role and metric profile")
    return {(item.contract_id, item.metric_id, item.unit) for item in contracts}


def _aggregate_measurements(
    measurements: tuple[CarrierMeasurement, ...],
) -> tuple[MeasurementCoordinate, ...]:
    totals: dict[tuple[str, str, MetricUnit], int] = {}
    for measurement in measurements:
        for value in measurement.native.values:
            key = (measurement.identity.scope_id, value.metric_id, value.unit)
            totals[key] = totals.get(key, 0) + value.value
    return tuple(
        MeasurementCoordinate(
            scope_id=scope_id,
            metric_id=metric_id,
            unit=unit,
            value=totals[(scope_id, metric_id, unit)],
        )
        for scope_id, metric_id, unit in sorted(totals)
    )


def _validated_items(
    values: object,
    expected_type: type[BaseModel],
    label: str,
) -> tuple[BaseModel, ...]:
    if not isinstance(values, (list, tuple)):
        _invalid(f"measurement contract requires a typed {label} tuple", values)
    return tuple(_validated_model(value, expected_type, label) for value in values)


def _validated_model(
    value: object,
    expected_type: type[BaseModel],
    label: str,
) -> BaseModel:
    is_model = isinstance(value, BaseModel)
    if is_model and type(value) is not expected_type:
        _invalid(f"measurement contract requires typed {label}", value)
    try:
        payload: object = (
            BaseModel.model_dump(value, mode="python", by_alias=True, warnings="error")
            if is_model
            else value
        )
        validated = expected_type.model_validate(payload)
    except (AttributeError, TypeError, ValueError):
        _invalid(f"measurement contract requires typed {label}", value)
    return validated


def _identity_matches_path(relative_path: str, identity: CarrierIdentity) -> bool:
    manifest = CarrierManifest.model_validate(
        {
            "schema": "ethos-source-budget-carriers-v2",
            "contract_version": 2,
            "carriers": (identity,),
        }
    )
    match = classify_carrier(relative_path, manifest)
    return match.state == "classified" and match.identity == identity


def _require_resolved_native(
    identity: CarrierIdentity,
    contracts: MetricContractSet,
    native: NativeMeasurement,
    value: object,
    label: str,
) -> None:
    try:
        expected = resolve_metric_contracts(identity, contracts)
    except ValueError:
        _invalid(f"{label} requires a classified identity resolution", value)
    if native.contracts != expected:
        _invalid(
            f"{label} native contracts must equal the classified identity resolution",
            value,
        )


def _item_key(item: MetricContract | MetricValue) -> tuple[str, str, str]:
    return (item.metric_id, item.unit, item.contract_id)
