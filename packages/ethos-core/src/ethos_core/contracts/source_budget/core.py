"""Strict lifecycle contract for source-budget policy declarations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Annotated
from typing import Literal
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import TypeAdapter
from pydantic import field_validator
from pydantic import model_validator

from ethos_core.contracts.source_budget.policy.core import source_budget_v2_json_schema

NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
NonEmptyStr = Annotated[str, Field(min_length=1)]
IsoDate = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
JSON_SCHEMA_DRAFT_2020_12 = _SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_TITLE = "ETHOS Source Budget Policy"
_REQUIRED_AGGREGATES = {"python_total", "global_total"}
ISO_DATE_LENGTH = _ISO_DATE_LENGTH = len("YYYY-MM-DD")
ISO_DATE_ERROR = _ISO_DATE_ERROR = "must be an ISO-8601 calendar date"


class _SourceBudgetModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("due_on", "expiry", check_fields=False)
    @classmethod
    def validate_due_on(cls, value: str) -> str:
        """Require a machine-readable ISO calendar date."""
        if len(value) != _ISO_DATE_LENGTH:
            raise ValueError(_ISO_DATE_ERROR)
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(_ISO_DATE_ERROR) from exc
        return value


class SourceBudgetWave(_SourceBudgetModel):
    """One registered deletion wave for active temporary source debt."""

    id: NonEmptyStr
    due_on: IsoDate
    state: Literal["active", "settled"]


class SourceBudgetCarrier(_SourceBudgetModel):
    """One declaration-owned source carrier classifier and line metric."""

    category: NonEmptyStr
    extensions: tuple[NonEmptyStr, ...] = Field(min_length=1)
    paths: tuple[NonEmptyStr, ...] = ()
    measure: Literal["python_ast", "lines"] = "lines"
    comment_prefixes: tuple[str, ...] = ()
    comment_wrappers: tuple[tuple[str, str], ...] = ()


class SourceBudgetTaxonomy(_SourceBudgetModel):
    """One format-registry-owned executable carrier taxonomy."""

    carrier: tuple[SourceBudgetCarrier, ...] = Field(min_length=1)
    aggregates: dict[str, tuple[NonEmptyStr, ...]]

    @model_validator(mode="after")
    def validate_taxonomy(self) -> SourceBudgetTaxonomy:
        unknown = set().union(*self.aggregates.values()) - {item.category for item in self.carrier}
        if unknown:
            message = f"source-budget aggregate member unknown: {min(unknown)}"
            raise ValueError(message)
        return self


class SourceBudgetDebtRecord(_SourceBudgetModel):
    """One auditable temporary allowance and its required deletion outcome."""

    id: NonEmptyStr
    owner: NonEmptyStr
    replacement: NonEmptyStr
    deletion_wave: NonEmptyStr
    expiry: IsoDate
    allowance: NonNegativeInt
    expected_net_deletion: PositiveInt
    allowance_by_category: dict[str, NonNegativeInt]

    @classmethod
    def validate_expiry(cls, value: str) -> str:
        """Validate expiry through the shared ISO calendar-date contract."""
        return cls.validate_due_on(value)


class SourceBudgetDebt(_SourceBudgetModel):
    """The complete temporary-debt ledger used by transition enforcement."""

    maximum_total: NonNegativeInt
    waves: tuple[SourceBudgetWave, ...]
    records: tuple[SourceBudgetDebtRecord, ...]

    @model_validator(mode="after")
    def validate_lifecycle_bindings(self) -> SourceBudgetDebt:
        wave_ids = tuple(wave.id for wave in self.waves)
        record_ids = tuple(record.id for record in self.records)
        pairs = ((wave_ids, "deletion waves"), (record_ids, "debt records"))
        for values, label in pairs:
            if len(values) != len(set(values)):
                message = f"source-budget {label} must be unique"
                raise ValueError(message)
        unknown = {record.deletion_wave for record in self.records} - set(wave_ids)
        if unknown:
            message = f"source-budget debt references unknown deletion wave: {min(unknown)}"
            raise ValueError(message)
        return self


class SourceBudgetPolicyBase(_SourceBudgetModel):
    """Validated source-budget policy loaded from the repository rules table."""

    baseline_head: str = Field(pattern=r"^[a-f0-9]{40,64}$")
    baseline: dict[str, NonNegativeInt]
    terminal: dict[str, NonNegativeInt]
    debt: SourceBudgetDebt

    @model_validator(mode="after")
    def validate_taxonomy(self) -> SourceBudgetPolicyBase:
        for name in ("baseline", "terminal"):
            if not getattr(self, name).keys() >= _REQUIRED_AGGREGATES:
                message = f"source-budget {name} must include required aggregates"
                raise ValueError(message)
        return self


class SourceBudgetCampaignPolicy(SourceBudgetPolicyBase):
    enforcement: Literal["campaign_terminal"]
    campaign_id: NonEmptyStr


class SourceBudgetStandalonePolicy(SourceBudgetPolicyBase):
    enforcement: Literal["transition", "terminal"]


type SourceBudgetPolicy = Annotated[
    SourceBudgetCampaignPolicy | SourceBudgetStandalonePolicy,
    Field(discriminator="enforcement"),
]
SourceBudgetPolicyAdapter = _POLICY_ADAPTER = TypeAdapter(SourceBudgetPolicy)


def source_budget_json_schema() -> dict[str, object]:
    """Compose the unchanged v1 union and strict v2 union into one schema."""
    v1 = _POLICY_ADAPTER.json_schema()
    v2 = source_budget_v2_json_schema()
    definitions = cast("dict[str, object]", v1.pop("$defs", {}))
    definitions.update(cast("dict[str, object]", v2.pop("$defs", {})))
    v2.pop("title", None)
    return {
        "$schema": _SCHEMA_DRAFT,
        "$defs": definitions,
        "oneOf": [v1, v2],
        "title": _SCHEMA_TITLE,
    }


@dataclass(frozen=True, slots=True)
class SourceBudgetPolicyLoad:
    """A configuration read that either yields one typed policy or explicit gaps."""

    policy: SourceBudgetPolicy | None
    required_gaps: tuple[str, ...]


def validate_source_budget_policy(payload: object) -> SourceBudgetPolicy:
    """Validate a source-budget policy through its typed contract."""
    return _POLICY_ADAPTER.validate_python(payload)


def validate_source_budget_taxonomy(payload: object) -> SourceBudgetTaxonomy:
    """Validate the carrier taxonomy compiled from format selection."""
    return SourceBudgetTaxonomy.model_validate(payload)
