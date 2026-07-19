"""Typed metric contracts for Budget Contract v2."""

import hashlib
import json
from dataclasses import dataclass
from typing import Annotated
from typing import Literal
from typing import NoReturn
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierRole

NonEmptyStr = Annotated[str, Field(min_length=1)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"

MetricUnit = Literal[
    "lexical_token",
    "semantic_node",
    "normalized_byte",
    "normalized_scalar_byte",
]


def _raise_contract_error(message: str) -> NoReturn:
    """Raise one stable metric-contract validation error."""
    raise ValueError(message)


class MetricProfile(BaseModel):
    """Required metric vector for one carrier role and profile."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: NonEmptyStr
    carrier_role: CarrierRole
    required_metric_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_metric_ids(self) -> Self:
        """Reject duplicate required coordinates."""
        if len(self.required_metric_ids) != len(set(self.required_metric_ids)):
            _raise_contract_error("metric profile required metric ids must be unique")
        return self


class MetricContract(BaseModel):
    """One immutable native metric identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_id: NonEmptyStr
    contract_version: PositiveInt
    metric_id: NonEmptyStr
    unit: MetricUnit
    carrier_role: CarrierRole
    metric_profile: NonEmptyStr
    parser_id: NonEmptyStr
    parser_version: NonEmptyStr
    grammar_digest: Sha256
    normalization_id: NonEmptyStr
    normalization_version: NonEmptyStr
    aggregation: Literal["sum"]
    non_compensable: Literal[True]

    @field_validator("non_compensable", mode="before")
    @classmethod
    def validate_non_compensable(cls, value: object) -> object:
        """Reject truthy coercions; only the boolean singleton is admissible."""
        if value is not True:
            _raise_contract_error("metric contract must be non-compensable")
        return value


def _validate_contract_versions(
    registry_version: int,
    contracts: tuple[MetricContract, ...],
) -> None:
    mismatched = sorted(
        item.contract_id for item in contracts if item.contract_version != registry_version
    )
    if mismatched:
        _raise_contract_error(f"metric contract version mismatches registry:{mismatched[0]}")


class MetricContractSet(BaseModel):
    """Complete immutable profile and metric registry."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_by_alias=True,
        validate_by_name=False,
    )

    schema_id: Literal["ethos-source-budget-metrics-v2"] = Field(alias="schema")
    contract_version: PositiveInt
    profiles: tuple[MetricProfile, ...] = Field(min_length=1)
    contracts: tuple[MetricContract, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_registry(self) -> Self:
        """Reject duplicate, dangling, incomplete, or role-mismatched contracts."""
        _validate_contract_versions(self.contract_version, self.contracts)
        profile_ids = tuple(item.profile_id for item in self.profiles)
        if len(profile_ids) != len(set(profile_ids)):
            _raise_contract_error("metric profile ids must be unique")
        contract_ids = tuple(item.contract_id for item in self.contracts)
        if len(contract_ids) != len(set(contract_ids)):
            _raise_contract_error("metric contract ids must be unique")
        coordinates = tuple(
            (item.metric_profile, item.carrier_role, item.metric_id) for item in self.contracts
        )
        if len(coordinates) != len(set(coordinates)):
            _raise_contract_error("metric contract coordinates must be unique")

        profiles = {item.profile_id: item for item in self.profiles}
        available: dict[str, set[str]] = {item.profile_id: set() for item in self.profiles}
        for contract in self.contracts:
            profile = profiles.get(contract.metric_profile)
            if profile is None:
                _raise_contract_error(
                    f"metric contract references unknown profile:{contract.metric_profile}"
                )
            if profile.carrier_role != contract.carrier_role:
                _raise_contract_error(
                    f"metric contract role mismatches profile:{contract.metric_profile}"
                )
            available[profile.profile_id].add(contract.metric_id)

        for profile in self.profiles:
            required = set(profile.required_metric_ids)
            if missing := sorted(required - available[profile.profile_id]):
                _raise_contract_error(
                    f"metric profile required metric missing:{profile.profile_id}:{missing[0]}"
                )
            if unexpected := sorted(available[profile.profile_id] - required):
                _raise_contract_error(
                    f"metric profile undeclared metric:{profile.profile_id}:{unexpected[0]}"
                )
        return self


@dataclass(frozen=True, slots=True)
class MetricContractSetLoad:
    """A metric registry read that yields typed truth or explicit required gaps."""

    contracts: MetricContractSet | None
    required_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        """Require exactly one of validated contracts or non-empty gaps."""
        if self.contracts is not None and not isinstance(self.contracts, MetricContractSet):
            _raise_contract_error("metric contract load requires typed contracts")
        if not isinstance(self.required_gaps, tuple):
            _raise_contract_error("metric contract load required gaps must be a tuple")
        if any(not isinstance(gap, str) or not gap for gap in self.required_gaps):
            _raise_contract_error("metric contract load required gaps must be non-empty strings")
        if self.required_gaps != tuple(sorted(set(self.required_gaps))):
            _raise_contract_error(
                "metric contract load required gaps must be unique and stably ordered"
            )
        if self.contracts is None and not self.required_gaps:
            _raise_contract_error("metric contract load requires non-empty required gaps")
        if self.contracts is not None and self.required_gaps:
            _raise_contract_error("metric contract load with data forbids required gaps")


def validate_metric_contracts(payload: object) -> MetricContractSet:
    """Validate one metric registry payload."""
    return MetricContractSet.model_validate(payload)


def metric_contracts_json_schema() -> dict[str, object]:
    """Generate the published metric-contract JSON Schema."""
    return {
        "$schema": JSON_SCHEMA_DRAFT_2020_12,
        **MetricContractSet.model_json_schema(by_alias=True),
        "title": "ETHOS Source Budget Metric Contracts",
    }


def metric_contracts_digest(contracts: MetricContractSet) -> str:
    """Return the canonical semantic digest for one metric registry."""
    payload = contracts.model_dump(mode="json", by_alias=True)
    payload["profiles"] = [
        {
            **item.model_dump(mode="json"),
            "required_metric_ids": sorted(item.required_metric_ids),
        }
        for item in sorted(contracts.profiles, key=lambda item: item.profile_id)
    ]
    payload["contracts"] = [
        item.model_dump(mode="json")
        for item in sorted(contracts.contracts, key=lambda item: item.contract_id)
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def resolve_metric_contracts(
    identity: CarrierIdentity,
    contracts: MetricContractSet,
) -> tuple[MetricContract, ...]:
    """Resolve the complete declared metric vector for one measured carrier."""
    if identity.disposition == "exclude":
        return ()
    profile_id = identity.metric_profile
    profile = next(
        (item for item in contracts.profiles if item.profile_id == profile_id),
        None,
    )
    if profile is None or profile.carrier_role != identity.role:
        _raise_contract_error(f"carrier metric profile unresolved:{identity.carrier_id}")
    by_metric = {
        item.metric_id: item
        for item in contracts.contracts
        if item.metric_profile == profile.profile_id and item.carrier_role == profile.carrier_role
    }
    return tuple(by_metric[metric_id] for metric_id in sorted(profile.required_metric_ids))
