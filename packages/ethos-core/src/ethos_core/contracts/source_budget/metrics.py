"""Typed metric contracts for Budget Contract v2."""

import typing as t
from dataclasses import dataclass

import pydantic as p

import ethos_core.contracts.source_budget.carriers as carrier

MetricUnit = t.Literal[
    "lexical_token",
    "semantic_node",
    "normalized_byte",
    "normalized_scalar_byte",
    "template_dynamic_unit",
    "template_static_byte",
]


_P = "metric profile "
_L = "metric contract load "
_C = "metric contract "
err, unique = carrier.err, carrier.unique


class MetricProfile(carrier.FrozenContract):
    """Required metric vector for one carrier role and profile."""

    profile_id: carrier.NonEmptyStr
    carrier_role: carrier.CarrierRole
    required_metric_ids: tuple[carrier.NonEmptyStr, ...] = p.Field(min_length=1)

    def model_post_init(self, _context: t.Any) -> None:
        """Reject duplicate required coordinates."""
        unique(self.required_metric_ids) or err(_P + "required metric ids must be unique")


class MetricContract(carrier.FrozenContract):
    """One immutable native metric identity."""

    contract_id: carrier.NonEmptyStr
    contract_version: carrier.PositiveInt
    metric_id: carrier.NonEmptyStr
    unit: MetricUnit
    carrier_role: carrier.CarrierRole
    metric_profile: carrier.NonEmptyStr
    parser_id: carrier.NonEmptyStr
    parser_version: carrier.NonEmptyStr
    grammar_digest: carrier.Sha256
    normalization_id: carrier.NonEmptyStr
    normalization_version: carrier.NonEmptyStr
    aggregation: t.Literal["sum"]
    non_compensable: t.Literal[True]

    @p.field_validator("non_compensable", mode="before")
    @classmethod
    def validate_non_compensable(cls, value: object) -> object:
        """Reject truthy coercions; only the boolean singleton is admissible."""
        value is True or err(_C + "must be non-compensable")
        return value


class MetricContractSet(carrier._Registry):
    """Complete immutable profile and metric registry."""

    schema_id: t.Literal["ethos-source-budget-metrics-v2"] = p.Field(alias="schema")
    contract_version: carrier.PositiveInt
    profiles: tuple[MetricProfile, ...] = p.Field(min_length=1)
    contracts: tuple[MetricContract, ...] = p.Field(min_length=1)

    def model_post_init(self, _context: t.Any) -> None:
        """Reject duplicate, dangling, incomplete, or role-mismatched contracts."""
        ps, cs = self.profiles, self.contracts
        mismatched = sorted(
            c.contract_id for c in cs if c.contract_version != self.contract_version
        )
        not mismatched or err(f"{_C}version mismatches registry:{mismatched[0]}")
        profiles = {p.profile_id: p for p in ps}
        len(profiles) == len(ps) or err(_P + "ids must be unique")
        contract_ids = tuple(c.contract_id for c in cs)
        unique(contract_ids) or err(_C + "ids must be unique")
        coordinates = tuple((c.metric_profile, c.carrier_role, c.metric_id) for c in cs)
        unique(coordinates) or err(_C + "coordinates must be unique")
        available: dict[str, set[str]] = {p.profile_id: set() for p in ps}
        for contract in cs:
            profile = profiles.get(contract.metric_profile)
            if profile is None:
                err(f"{_C}references unknown profile:{contract.metric_profile}")
            profile.carrier_role == contract.carrier_role or err(
                f"{_C}role mismatches profile:{contract.metric_profile}"
            )
            available[profile.profile_id].add(contract.metric_id)
        for profile in ps:
            required = set(profile.required_metric_ids)
            not (missing := sorted(required - available[profile.profile_id])) or err(
                f"{_P}required metric missing:{profile.profile_id}:{missing[0]}"
            )
            not (unexpected := sorted(available[profile.profile_id] - required)) or err(
                f"{_P}undeclared metric:{profile.profile_id}:{unexpected[0]}"
            )


@dataclass(frozen=True, slots=True)
class MetricContractSetLoad:
    """A metric registry read that yields typed truth or explicit required gaps."""

    contracts: MetricContractSet | None
    required_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        """Require exactly one of validated contracts or non-empty gaps."""
        carrier._load_envelope(
            self.contracts,
            MetricContractSet,
            self.required_gaps,
            _L,
            "requires typed contracts",
        )


def validate_metric_contracts(payload: object) -> MetricContractSet:
    """Validate one metric registry payload."""
    return MetricContractSet.model_validate(payload)


def metric_contracts_json_schema() -> dict[str, object]:
    """Generate the published metric-contract JSON Schema."""
    return carrier._json_schema(MetricContractSet, "ETHOS Source Budget Metric Contracts")


def metric_contracts_digest(contracts: MetricContractSet) -> str:
    """Return the canonical semantic digest for one metric registry."""
    payload = contracts.model_dump(mode="json", by_alias=True)
    for profile in payload["profiles"]:
        profile["required_metric_ids"].sort()
    payload["profiles"].sort(key=lambda item: item["profile_id"])
    payload["contracts"].sort(key=lambda item: item["contract_id"])
    return carrier._digest(payload)


def resolve_metric_contracts(
    identity: carrier.CarrierIdentity, contracts: MetricContractSet
) -> tuple[MetricContract, ...]:
    """Resolve the complete declared metric vector for one measured carrier."""
    if identity.disposition == "exclude":
        return ()
    profile_id = identity.metric_profile
    profile = next((item for item in contracts.profiles if item.profile_id == profile_id), None)
    if profile is None or profile.carrier_role != identity.role:
        err(f"carrier metric profile unresolved:{identity.carrier_id}")
    return tuple(
        next(
            item
            for item in contracts.contracts
            if item.metric_profile == profile.profile_id and item.metric_id == metric_id
        )
        for metric_id in sorted(profile.required_metric_ids)
    )
