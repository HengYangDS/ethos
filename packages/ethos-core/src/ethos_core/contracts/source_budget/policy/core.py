"""Strict vector policy and temporary-debt contracts for Budget Contract v2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Annotated
from typing import Literal
from typing import NoReturn
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import TypeAdapter
from pydantic import field_validator
from pydantic import model_validator

import ethos_core.contracts.source_budget.measurement.canonical as canonical
from ethos_core.contracts.source_budget.carriers import (
    NonEmptyStr,  # noqa: TC001, RUF100 - Pydantic resolves this annotation at runtime
)
from ethos_core.contracts.source_budget.carriers import (
    Sha256,  # noqa: TC001, RUF100 - Pydantic resolves this annotation at runtime
)
from ethos_core.contracts.source_budget.measurements import MeasurementCoordinate
from ethos_core.contracts.source_budget.metrics import (
    MetricUnit,  # noqa: TC001, RUF100 - Pydantic resolves this annotation at runtime
)

_GIT_OID = r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$"
_ISO_DATE = r"^\d{4}-\d{2}-\d{2}$"
_ISO_DATE_ERROR = "must be an ISO-8601 calendar date"
_SCHEMA_TITLE = "ETHOS Source Budget Policy v2"
_MISSING_BINDINGS = Literal[
    "admitted_head",
    "scope_digest",
    "inventory_digest",
    "baseline_snapshot",
    "historical_replay",
]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
IsoDate = Annotated[str, Field(pattern=_ISO_DATE)]
GitOid = Annotated[str, Field(pattern=_GIT_OID)]


def _invalid(message: str, *, cause: Exception | None = None) -> NoReturn:
    if cause is None:
        raise ValueError(message)
    raise ValueError(message) from cause


class _StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, populate_by_name=True)

    @field_validator("due_on", "expiry", check_fields=False)
    @classmethod
    def validate_calendar_date(cls, value: str) -> str:
        """Require an exact ISO-8601 calendar date."""
        try:
            date.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            _invalid(_ISO_DATE_ERROR, cause=exc)
        return value


class BudgetCoordinate(_StrictModel):
    """One non-compensating policy axis and its bound metric unit."""

    scope_id: NonEmptyStr
    metric_id: NonEmptyStr
    unit: MetricUnit

    @property
    def key(self) -> tuple[str, str]:
        """Return the semantic key whose unit may never be converted."""
        return self.scope_id, self.metric_id


class BudgetLimit(BudgetCoordinate):
    """One non-negative value on a Budget Contract v2 coordinate."""

    value: NonNegativeInt

    @property
    def coordinate(self) -> BudgetCoordinate:
        """Project the coordinate identity without its value."""
        return BudgetCoordinate(scope_id=self.scope_id, metric_id=self.metric_id, unit=self.unit)


class BudgetVector(_StrictModel):
    """Canonical ordered coordinate values bound to the native vector digest."""

    coordinates: tuple[BudgetLimit, ...] = ()
    vector_digest: Sha256

    @field_validator("coordinates", mode="before")
    @classmethod
    def normalize_coordinate_container(cls, value: object) -> object:
        """Accept JSON/TOML arrays while retaining strict typed members."""
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_vector(self) -> Self:
        keys = tuple(item.key for item in self.coordinates)
        if len(keys) != len(set(keys)):
            _invalid("budget vector coordinate keys must be unique")
        order = tuple((item.scope_id, item.metric_id, item.unit) for item in self.coordinates)
        if order != tuple(sorted(order)):
            _invalid("budget vector coordinates must be unique and stably ordered")
        if self.vector_digest != _vector_digest(self.coordinates):
            _invalid("budget vector digest must match canonical content")
        return self

    @classmethod
    def canonical(cls, coordinates: tuple[BudgetLimit, ...]) -> BudgetVector:
        """Revalidate, sort, and digest one canonical vector."""
        if type(coordinates) is not tuple:
            _invalid("budget vector canonical input must be a tuple")
        validated = tuple(
            BudgetLimit.model_validate(item.model_dump(mode="python")) for item in coordinates
        )
        ordered = tuple(
            sorted(validated, key=lambda item: (item.scope_id, item.metric_id, item.unit))
        )
        keys = tuple(item.key for item in ordered)
        if len(keys) != len(set(keys)):
            _invalid("budget vector coordinate keys must be unique")
        return cls(coordinates=ordered, vector_digest=_vector_digest(ordered))


class BudgetBaselineBinding(_StrictModel):
    """Immutable replay and vector identity for the admitted baseline."""

    admitted_head: GitOid
    manifest_digest: Sha256
    inventory_digest: Sha256
    contract_set_digest: Sha256
    snapshot_digest: Sha256
    vector: BudgetVector


class SourceBudgetWaveV2(_StrictModel):
    """One governed deletion wave for mapped or unmapped temporary debt."""

    id: NonEmptyStr
    due_on: IsoDate
    state: Literal["active", "settled"]


class _DebtBase(_StrictModel):
    id: NonEmptyStr
    origin_change: NonEmptyStr
    owner: NonEmptyStr
    replacement: NonEmptyStr
    deletion_wave: NonEmptyStr
    expiry: IsoDate


class MappedSourceBudgetDebtV2(_DebtBase):
    """Temporary allowance with complete historical and scope bindings."""

    mapping_state: Literal["mapped"]
    admitted_head: GitOid
    scope_digest: Sha256
    inventory_digest: Sha256
    baseline_snapshot_digest: Sha256
    historical_replay_digest: Sha256
    allowance: BudgetVector
    expected_deletion: BudgetVector

    @model_validator(mode="after")
    def validate_expected_deletion(self) -> Self:
        allowance = _vector_map(self.allowance)
        expected = _vector_map(self.expected_deletion)
        if set(expected) != set(allowance):
            _invalid("mapped debt expected deletion coordinates must match allowance")
        if any(expected[key][1] < value for key, (_, value) in allowance.items()):
            _invalid("mapped debt expected deletion must cover allowance")
        return self


class UnmappedSourceBudgetDebtV2(_DebtBase):
    """Historical debt that carries no allowance until all bindings exist."""

    mapping_state: Literal["unmapped"]
    missing_bindings: tuple[_MISSING_BINDINGS, ...] = Field(min_length=1)

    @field_validator("missing_bindings", mode="before")
    @classmethod
    def normalize_missing_bindings(cls, value: object) -> object:
        """Accept TOML arrays without accepting duplicate missing facts."""
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_missing_bindings(self) -> Self:
        if len(self.missing_bindings) != len(set(self.missing_bindings)):
            _invalid("unmapped debt missing bindings must be unique")
        return self


type SourceBudgetDebtRecordV2 = Annotated[
    MappedSourceBudgetDebtV2 | UnmappedSourceBudgetDebtV2,
    Field(discriminator="mapping_state"),
]
_DEBT_ADAPTER = TypeAdapter(SourceBudgetDebtRecordV2)


class SourceBudgetDebtLedgerV2(_StrictModel):
    """Complete v2 temporary-debt inventory with explicit mapping state."""

    waves: tuple[SourceBudgetWaveV2, ...] = ()
    records: tuple[SourceBudgetDebtRecordV2, ...] = ()

    @field_validator("waves", "records", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> object:
        """Accept TOML arrays and leave all scalar validation strict."""
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_ledger(self) -> Self:
        wave_ids = tuple(item.id for item in self.waves)
        record_ids = tuple(item.id for item in self.records)
        if len(wave_ids) != len(set(wave_ids)):
            _invalid("source-budget v2 deletion waves must be unique")
        if len(record_ids) != len(set(record_ids)):
            _invalid("source-budget v2 debt records must be unique")
        unknown = {item.deletion_wave for item in self.records} - set(wave_ids)
        if unknown:
            message = f"source-budget v2 debt references unknown wave: {min(unknown)}"
            _invalid(message)
        return self


class _PolicyBase(_StrictModel):
    schema_id: Literal["ethos-source-budget-policy-v2"] = Field(alias="schema")
    contract_version: Literal[2]
    baseline_head: GitOid
    debt: SourceBudgetDebtLedgerV2


class InactiveSourceBudgetPolicyV2(_PolicyBase):
    """Repository declaration used while immutable v2 baseline evidence is absent."""

    state: Literal["inactive"]
    enforcement: Literal["campaign_terminal"]
    campaign_id: NonEmptyStr


class EvaluableSourceBudgetPolicyV2(_PolicyBase):
    """Complete shadow policy that can be evaluated without becoming authoritative."""

    state: Literal["shadow"]
    enforcement: Literal["transition", "campaign_terminal", "terminal"]
    campaign_id: NonEmptyStr | None = None
    baseline: BudgetBaselineBinding
    terminal: BudgetVector
    permanent_allocations: BudgetVector
    settled_reductions: BudgetVector

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        if self.baseline.admitted_head != self.baseline_head:
            _invalid("budget baseline admitted HEAD must match policy baseline HEAD")
        if (self.enforcement == "campaign_terminal") != (self.campaign_id is not None):
            _invalid("campaign-terminal policy requires exactly one campaign id")
        baseline = _vector_map(self.baseline.vector)
        terminal = _vector_map(self.terminal)
        if _coordinate_signature(baseline) != _coordinate_signature(terminal):
            _invalid("budget baseline and terminal coordinates must match")
        allocation = _vector_map(self.permanent_allocations)
        reduction = _vector_map(self.settled_reductions)
        _require_subset("permanent allocation", allocation, baseline)
        _require_subset("settled reduction", reduction, baseline)
        for key, (unit, value) in reduction.items():
            available = baseline[key][1] + allocation.get(key, (unit, 0))[1]
            if value > available:
                message = f"settled reduction underflows coordinate:{key[0]}:{key[1]}"
                _invalid(message)
        for record in self.debt.records:
            if isinstance(record, MappedSourceBudgetDebtV2):
                _require_subset("mapped debt allowance", _vector_map(record.allowance), baseline)
                _require_subset(
                    "mapped debt expected deletion",
                    _vector_map(record.expected_deletion),
                    baseline,
                )
        return self


type SourceBudgetPolicyV2 = Annotated[
    InactiveSourceBudgetPolicyV2 | EvaluableSourceBudgetPolicyV2,
    Field(discriminator="state"),
]
SourceBudgetPolicyV2Adapter = _POLICY_ADAPTER = TypeAdapter(SourceBudgetPolicyV2)


@dataclass(frozen=True, slots=True)
class SourceBudgetPolicyV2Load:
    """A v2 config read yielding one typed policy or explicit required gaps."""

    policy: SourceBudgetPolicyV2 | None
    required_gaps: tuple[str, ...]


def validate_source_budget_policy_v2(payload: object) -> SourceBudgetPolicyV2:
    """Validate a Budget Contract v2 policy through its discriminated union."""
    return _POLICY_ADAPTER.validate_python(payload)


def source_budget_v2_json_schema() -> dict[str, object]:
    """Generate the standalone Budget Contract v2 JSON Schema branch."""
    return {**_POLICY_ADAPTER.json_schema(), "title": _SCHEMA_TITLE}


def _vector_digest(coordinates: tuple[BudgetLimit, ...]) -> str:
    native = tuple(
        MeasurementCoordinate(
            scope_id=item.scope_id,
            metric_id=item.metric_id,
            unit=item.unit,
            value=item.value,
        )
        for item in coordinates
    )
    return canonical.vector_model_digest(native)


def _vector_map(vector: BudgetVector) -> dict[tuple[str, str], tuple[str, int]]:
    return {item.key: (item.unit, item.value) for item in vector.coordinates}


def _coordinate_signature(
    values: dict[tuple[str, str], tuple[str, int]],
) -> dict[tuple[str, str], str]:
    return {key: unit for key, (unit, _) in values.items()}


def _require_subset(
    label: str,
    values: dict[tuple[str, str], tuple[str, int]],
    baseline: dict[tuple[str, str], tuple[str, int]],
) -> None:
    for key, (unit, _) in values.items():
        if key not in baseline or baseline[key][0] != unit:
            message = f"{label} coordinate must be a baseline subset:{key[0]}:{key[1]}"
            _invalid(message)
