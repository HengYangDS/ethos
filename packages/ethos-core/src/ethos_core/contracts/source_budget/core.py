"""Strict lifecycle contract for source-budget policy declarations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Annotated
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

SourceBudgetCategory = Literal[
    "python_product",
    "python_tests",
    "python_tools",
    "python_other",
    "shell",
    "js",
    "toml",
    "yaml",
    "json",
    "ini",
    "jinja",
    "diagram",
    "python_total",
    "global_total",
]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
NonEmptyStr = Annotated[str, Field(min_length=1)]
IsoDate = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
ISO_DATE_LENGTH = 10
ISO_DATE_ERROR = "must be an ISO-8601 calendar date"


class SourceBudgetWave(BaseModel):
    """One registered deletion wave for active temporary source debt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmptyStr
    due_on: IsoDate
    state: Literal["active", "settled"]

    @field_validator("due_on")
    @classmethod
    def validate_due_on(cls, value: str) -> str:
        """Require a machine-readable ISO calendar date."""
        return _iso_date(value)


class SourceBudgetDebtRecord(BaseModel):
    """One auditable temporary allowance and its required deletion outcome."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmptyStr
    owner: NonEmptyStr
    replacement: NonEmptyStr
    deletion_wave: NonEmptyStr
    expiry: IsoDate
    allowance: NonNegativeInt
    expected_net_deletion: PositiveInt
    allowance_by_category: dict[SourceBudgetCategory, NonNegativeInt]

    @field_validator("expiry")
    @classmethod
    def validate_expiry(cls, value: str) -> str:
        """Require a machine-readable ISO calendar date."""
        return _iso_date(value)


class SourceBudgetDebt(BaseModel):
    """The complete temporary-debt ledger used by transition enforcement."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_total: NonNegativeInt
    waves: tuple[SourceBudgetWave, ...]
    records: tuple[SourceBudgetDebtRecord, ...]

    @model_validator(mode="after")
    def validate_lifecycle_bindings(self) -> SourceBudgetDebt:
        """Reject duplicate waves, duplicate records, and dangling wave references."""
        wave_ids = tuple(wave.id for wave in self.waves)
        record_ids = tuple(record.id for record in self.records)
        if len(wave_ids) != len(set(wave_ids)):
            message = "source-budget deletion waves must be unique"
            raise ValueError(message)
        if len(record_ids) != len(set(record_ids)):
            message = "source-budget debt records must be unique"
            raise ValueError(message)
        if unknown := sorted({record.deletion_wave for record in self.records} - set(wave_ids)):
            message = f"source-budget debt references unknown deletion wave: {unknown[0]}"
            raise ValueError(message)
        return self


class SourceBudgetPolicy(BaseModel):
    """Validated source-budget policy loaded from the repository rules table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_head: str = Field(pattern=r"^[a-f0-9]{40,64}$")
    enforcement: Literal["transition", "terminal"]
    baseline: dict[SourceBudgetCategory, NonNegativeInt]
    terminal: dict[SourceBudgetCategory, NonNegativeInt]
    debt: SourceBudgetDebt

    @field_validator("baseline", "terminal")
    @classmethod
    def validate_aggregate_limits(
        cls, value: dict[SourceBudgetCategory, NonNegativeInt]
    ) -> dict[SourceBudgetCategory, NonNegativeInt]:
        """Require the aggregate dimensions that make a policy enforceable."""
        if {"python_total", "global_total"} - set(value):
            message = "source-budget limits require python_total and global_total"
            raise ValueError(message)
        return value


def source_budget_json_schema() -> dict[str, object]:
    """Generate the published source-budget JSON Schema contract."""
    schema = SourceBudgetPolicy.model_json_schema()
    return {
        "$schema": JSON_SCHEMA_DRAFT_2020_12,
        **schema,
        "title": "ETHOS Source Budget Policy",
    }


@dataclass(frozen=True)
class SourceBudgetPolicyLoad:
    """A configuration read that either yields one typed policy or explicit gaps."""

    policy: SourceBudgetPolicy | None
    required_gaps: tuple[str, ...]


def _iso_date(value: str) -> str:
    """Return an exact ISO-8601 calendar date or raise a validation error."""
    if len(value) != ISO_DATE_LENGTH:
        raise ValueError(ISO_DATE_ERROR)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(ISO_DATE_ERROR) from exc
    return value
