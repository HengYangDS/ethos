"""Pure fail-closed verdict compilation for Budget Contract v2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING
from typing import Literal
from typing import NoReturn
from typing import Self
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from ethos.domain.source_budget.core import (
    SourceBudgetShadowObservation,  # noqa: TC001, RUF100 - Pydantic resolves this annotation at runtime
)
from ethos_core.contracts.source_budget.carriers import (
    NonEmptyStr,  # noqa: TC001, RUF100 - Pydantic resolves this annotation at runtime
)
from ethos_core.contracts.source_budget.carriers import (
    Sha256,  # noqa: TC001, RUF100 - Pydantic resolves this annotation at runtime
)
from ethos_core.contracts.source_budget.policy.core import BudgetCoordinate
from ethos_core.contracts.source_budget.policy.core import BudgetLimit
from ethos_core.contracts.source_budget.policy.core import BudgetVector
from ethos_core.contracts.source_budget.policy.core import EvaluableSourceBudgetPolicyV2
from ethos_core.contracts.source_budget.policy.core import GitOid
from ethos_core.contracts.source_budget.policy.core import InactiveSourceBudgetPolicyV2
from ethos_core.contracts.source_budget.policy.core import MappedSourceBudgetDebtV2
from ethos_core.contracts.source_budget.policy.core import SourceBudgetPolicyV2
from ethos_core.contracts.source_budget.policy.core import UnmappedSourceBudgetDebtV2

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.metrics import MetricUnit


def _invalid_value(message: str) -> NoReturn:
    raise ValueError(message)


def _invalid_type(message: str) -> NoReturn:
    raise TypeError(message)


class _StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


@dataclass(frozen=True, slots=True)
class _TrustedVectors:
    baseline: BudgetVector | None
    current: BudgetVector | None
    required_gaps: tuple[str, ...]


class MappedDebtReplayBinding(_StrictModel):
    """Reviewed replay identity proving one mapped debt record is not stale."""

    debt_id: NonEmptyStr
    admitted_head: GitOid
    scope_digest: Sha256
    inventory_digest: Sha256
    baseline_snapshot_digest: Sha256
    historical_replay_digest: Sha256


class SourceBudgetVerdictObservations(_StrictModel):
    """All explicit observation inputs required by the pure reducer."""

    baseline: SourceBudgetShadowObservation
    current: SourceBudgetShadowObservation
    debt_replays: tuple[MappedDebtReplayBinding, ...] = ()
    required_gaps: tuple[NonEmptyStr, ...] = ()

    @field_validator("debt_replays", "required_gaps", mode="before")
    @classmethod
    def normalize_sequences(cls, value: object) -> object:
        """Accept serialized arrays while retaining strict typed members."""
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_observations(self) -> Self:
        debt_ids = tuple(item.debt_id for item in self.debt_replays)
        if len(debt_ids) != len(set(debt_ids)):
            _invalid_value("debt replay bindings must be unique")
        if len(self.required_gaps) != len(set(self.required_gaps)):
            _invalid_value("verdict input gaps must be unique")
        return self


class SourceBudgetCoordinateVerdict(_StrictModel):
    """Same-coordinate arithmetic with no cross-axis compensation."""

    coordinate: BudgetCoordinate
    baseline: int = Field(strict=True, ge=0)
    permanent_allocation: int = Field(strict=True, ge=0)
    settled_reduction: int = Field(strict=True, ge=0)
    debt_allowance: int = Field(strict=True, ge=0)
    allowed: int = Field(strict=True, ge=0)
    current: int = Field(strict=True, ge=0)
    terminal: int = Field(strict=True, ge=0)


class SourceBudgetVerdict(_StrictModel):
    """Deterministic Budget Contract v2 decision and supporting arithmetic."""

    ok: bool
    state: Literal["clean", "blocked"]
    policy_state: Literal["inactive", "shadow"]
    enforcement: Literal["transition", "campaign_terminal", "terminal"]
    coordinates: tuple[SourceBudgetCoordinateVerdict, ...]
    terminal_target_met: bool
    active_debt_ids: tuple[str, ...]
    advisory_gaps: tuple[str, ...]
    required_gaps: tuple[str, ...]


def compile_budget_verdict(
    observations: SourceBudgetVerdictObservations,
    policy: SourceBudgetPolicyV2,
    today: date,
) -> SourceBudgetVerdict:
    """Compile one v2 verdict without filesystem, Git, config, environment, or clock IO."""
    if type(observations) is not SourceBudgetVerdictObservations or not isinstance(
        policy, (InactiveSourceBudgetPolicyV2, EvaluableSourceBudgetPolicyV2)
    ):
        _invalid_type("budget verdict requires typed observations and policy")
    if type(today) is not date:
        _invalid_type("budget verdict requires an explicit calendar date")
    if isinstance(policy, InactiveSourceBudgetPolicyV2):
        return _blocked(policy, ("source_budget_v2_policy_inactive",))
    trusted = _trusted_vectors(observations, policy)
    if trusted.required_gaps:
        return _blocked(policy, trusted.required_gaps)
    baseline_vector = cast("BudgetVector", trusted.baseline)
    current_vector = cast("BudgetVector", trusted.current)
    debt_allowance, active_ids, debt_gaps = _active_debt(observations, policy, today)
    if debt_gaps:
        return _blocked(policy, debt_gaps)
    coordinates = _coordinate_results(policy, baseline_vector, current_vector, debt_allowance)
    required, advisory, terminal_overages = _policy_findings(policy, coordinates, active_ids)
    return SourceBudgetVerdict(
        ok=not required,
        state="clean" if not required else "blocked",
        policy_state=policy.state,
        enforcement=policy.enforcement,
        coordinates=coordinates,
        terminal_target_met=not terminal_overages,
        active_debt_ids=active_ids,
        advisory_gaps=advisory,
        required_gaps=required,
    )


def _trusted_vectors(
    observations: SourceBudgetVerdictObservations,
    policy: EvaluableSourceBudgetPolicyV2,
) -> _TrustedVectors:
    gaps = list(observations.required_gaps)
    for label, observation in (
        ("baseline", observations.baseline),
        ("current", observations.current),
    ):
        if gap := _observation_gap(label, observation):
            gaps.append(gap)
    if gaps:
        return _TrustedVectors(None, None, tuple(gaps))
    baseline_vector = _observation_vector(observations.baseline)
    current_vector = _observation_vector(observations.current)
    if baseline_vector is None:
        gaps.append("source_budget_v2_baseline_observation_incomplete")
    if current_vector is None:
        gaps.append("source_budget_v2_current_observation_incomplete")
    if gaps:
        return _TrustedVectors(baseline_vector, current_vector, tuple(gaps))
    baseline_vector = cast("BudgetVector", baseline_vector)
    current_vector = cast("BudgetVector", current_vector)
    if not _baseline_matches(observations.baseline, baseline_vector, policy):
        gaps.append("source_budget_v2_baseline_identity_mismatch")
    if not _current_matches(observations.current, current_vector, policy):
        gaps.append("source_budget_v2_current_identity_mismatch")
    return _TrustedVectors(baseline_vector, current_vector, tuple(gaps))


def _coordinate_results(
    policy: EvaluableSourceBudgetPolicyV2,
    baseline_vector: BudgetVector,
    current_vector: BudgetVector,
    debt_allowance: dict[tuple[str, str], tuple[MetricUnit, int]],
) -> tuple[SourceBudgetCoordinateVerdict, ...]:
    baseline = _values(baseline_vector)
    current = _values(current_vector)
    terminal = _values(policy.terminal)
    allocation = _values(policy.permanent_allocations)
    reduction = _values(policy.settled_reductions)
    return tuple(
        SourceBudgetCoordinateVerdict(
            coordinate=BudgetCoordinate(scope_id=key[0], metric_id=key[1], unit=unit),
            baseline=baseline_value,
            permanent_allocation=allocation.get(key, (unit, 0))[1],
            settled_reduction=reduction.get(key, (unit, 0))[1],
            debt_allowance=debt_allowance.get(key, (unit, 0))[1],
            allowed=baseline_value
            + allocation.get(key, (unit, 0))[1]
            - reduction.get(key, (unit, 0))[1]
            + debt_allowance.get(key, (unit, 0))[1],
            current=current[key][1],
            terminal=terminal[key][1],
        )
        for key, (unit, baseline_value) in baseline.items()
    )


def _policy_findings(
    policy: EvaluableSourceBudgetPolicyV2,
    coordinates: tuple[SourceBudgetCoordinateVerdict, ...],
    active_ids: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    transition = tuple(
        _gap("source_budget_v2_transition_exceeded", item, item.allowed)
        for item in coordinates
        if item.current > item.allowed
    )
    terminal = tuple(
        _gap("source_budget_v2_terminal_exceeded", item, item.terminal)
        for item in coordinates
        if item.current > item.terminal
    )
    required: tuple[str, ...] = ()
    advisory: tuple[str, ...] = ()
    if policy.enforcement == "transition":
        required = transition
    elif policy.enforcement == "campaign_terminal":
        required = terminal
        advisory = tuple(
            item.replace("transition_exceeded", "campaign_growth_overage") for item in transition
        )
    else:
        required = terminal + tuple(
            f"source_budget_v2_terminal_active_debt:{debt_id}" for debt_id in active_ids
        )
    if not required and active_ids:
        advisory += tuple(f"source_budget_v2_debt_active:{debt_id}" for debt_id in active_ids)
    return required, advisory, terminal


def _blocked(
    policy: SourceBudgetPolicyV2,
    gaps: tuple[str, ...],
) -> SourceBudgetVerdict:
    return SourceBudgetVerdict(
        ok=False,
        state="blocked",
        policy_state=policy.state,
        enforcement=policy.enforcement,
        coordinates=(),
        terminal_target_met=False,
        active_debt_ids=(),
        advisory_gaps=(),
        required_gaps=gaps,
    )


def _observation_gap(label: str, observation: SourceBudgetShadowObservation) -> str:
    if (
        observation.comparison_state != "reviewed_observation"
        or observation.required_gaps
        or observation.v2 is None
    ):
        return f"source_budget_v2_{label}_observation_incomplete"
    return ""


def _observation_vector(observation: SourceBudgetShadowObservation) -> BudgetVector | None:
    if observation.v2 is None:
        return None
    try:
        vector = BudgetVector.canonical(
            tuple(
                BudgetLimit(
                    scope_id=item.scope_id,
                    metric_id=item.metric_id,
                    unit=item.unit,
                    value=item.value,
                )
                for item in observation.v2.coordinates
            )
        )
    except (TypeError, ValueError):
        return None
    return vector if vector.vector_digest == observation.v2.vector_digest else None


def _baseline_matches(
    observation: SourceBudgetShadowObservation,
    vector: BudgetVector,
    policy: EvaluableSourceBudgetPolicyV2,
) -> bool:
    if observation.v2 is None:
        return False
    binding = policy.baseline
    return (
        observation.subject.commit_sha == policy.baseline_head == binding.admitted_head
        and observation.v2.manifest_digest == binding.manifest_digest
        and observation.v2.inventory_digest == binding.inventory_digest
        and observation.v2.contract_set_digest == binding.contract_set_digest
        and observation.v2.snapshot_digest == binding.snapshot_digest
        and vector == binding.vector
    )


def _current_matches(
    observation: SourceBudgetShadowObservation,
    vector: BudgetVector,
    policy: EvaluableSourceBudgetPolicyV2,
) -> bool:
    if observation.v2 is None:
        return False
    baseline = policy.baseline
    return (
        observation.v2.manifest_digest == baseline.manifest_digest
        and observation.v2.contract_set_digest == baseline.contract_set_digest
        and _signature(vector) == _signature(baseline.vector)
    )


def _active_debt(
    observations: SourceBudgetVerdictObservations,
    policy: EvaluableSourceBudgetPolicyV2,
    today: date,
) -> tuple[
    dict[tuple[str, str], tuple[MetricUnit, int]],
    tuple[str, ...],
    tuple[str, ...],
]:
    waves = {item.id: item for item in policy.debt.waves}
    replays = {item.debt_id: item for item in observations.debt_replays}
    allowance: dict[tuple[str, str], tuple[MetricUnit, int]] = {}
    active: list[str] = []
    gaps: list[str] = []
    for record in sorted(policy.debt.records, key=lambda item: item.id):
        if isinstance(record, UnmappedSourceBudgetDebtV2):
            gaps.append(f"source_budget_v2_debt_unmapped:{record.id}")
            continue
        wave = waves[record.deletion_wave]
        if date.fromisoformat(record.expiry) < today:
            gaps.append(f"source_budget_v2_debt_expired:{record.id}")
            continue
        if date.fromisoformat(wave.due_on) < today:
            gaps.append(f"source_budget_v2_debt_overdue:{record.id}")
            continue
        replay = replays.get(record.id)
        if wave.state == "settled" or replay is None or not _replay_matches(record, replay):
            gaps.append(f"source_budget_v2_debt_stale:{record.id}")
            continue
        active.append(record.id)
        for key, (unit, value) in _values(record.allowance).items():
            previous = allowance.get(key, (unit, 0))
            allowance[key] = unit, previous[1] + value
    return allowance, tuple(active), tuple(gaps)


def _replay_matches(record: MappedSourceBudgetDebtV2, replay: MappedDebtReplayBinding) -> bool:
    return (
        record.admitted_head == replay.admitted_head
        and record.scope_digest == replay.scope_digest
        and record.inventory_digest == replay.inventory_digest
        and record.baseline_snapshot_digest == replay.baseline_snapshot_digest
        and record.historical_replay_digest == replay.historical_replay_digest
    )


def _values(vector: BudgetVector) -> dict[tuple[str, str], tuple[MetricUnit, int]]:
    return {item.key: (item.unit, item.value) for item in vector.coordinates}


def _signature(vector: BudgetVector) -> tuple[tuple[str, str, str], ...]:
    return tuple((item.scope_id, item.metric_id, item.unit) for item in vector.coordinates)


def _gap(prefix: str, item: SourceBudgetCoordinateVerdict, limit: int) -> str:
    coordinate = item.coordinate
    return f"{prefix}:{coordinate.scope_id}:{coordinate.metric_id}:{item.current}>{limit}"
