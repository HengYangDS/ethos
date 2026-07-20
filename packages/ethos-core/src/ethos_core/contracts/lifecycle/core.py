"""Pure, declared lifecycle reduction for exact mutation requests."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

_EFFECT_FIELDS_INVALID = "lease_effect_fields_invalid"


class LifecycleModel(BaseModel):
    """Strict immutable base for lifecycle facts and declarations."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class MutationRequest(LifecycleModel):
    """The bounded intent and confirmation supplied to a mutation boundary."""

    command: str
    apply: bool
    authorized: bool
    expect_head: str | None

    def to_payload(self) -> dict[str, object]:
        """Project intent without performing authorization or mutation."""
        return {
            **self.model_dump(exclude={"authorized"}),
            "confirmation_present": self.authorized,
        }


class MutationEvaluation(LifecycleModel):
    """Pure lifecycle decision; the public contract remains ``AdmissionDecision``."""

    ok: bool
    state: str
    gaps: tuple[str, ...] = ()


class MutationTransition(LifecycleModel):
    """Immutable transition declaration interpreted by ``reduce_mutation``."""

    id: str
    required_role: str
    role_gap: str
    dirty_gap: str
    dry_run_short_circuit: bool = False
    dry_run_checked_commands: tuple[str, ...] = ()
    current_state: str = ""


class MutationFacts(LifecycleModel):
    """Already-observed facts supplied by an imperative adapter to the reducer."""

    role: str = ""
    dirty: bool = False
    healthy_gaps: tuple[str, ...] = ()
    always_gaps: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()
    current: bool = False


class LeaseTransition(LifecycleModel):
    """Immutable operation declaration for the local lease lifecycle."""

    id: str = Field(min_length=1)
    applied_state: str = Field(min_length=1)
    effect_fields: tuple[str, ...] = Field(min_length=1)
    blocks_contrary_decision: bool = False

    @field_validator("effect_fields", mode="before")
    @classmethod
    def compile_effect_fields(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, list | tuple):
            raise TypeError(_EFFECT_FIELDS_INVALID)
        fields: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item:
                raise ValueError(_EFFECT_FIELDS_INVALID)
            fields.append(item)
        if len(fields) != len(set(fields)):
            raise ValueError(_EFFECT_FIELDS_INVALID)
        return tuple(fields)


class LeaseFacts(LifecycleModel):
    """Observed local lease facts supplied to the pure lease reducer."""

    role: str
    current_branch: str
    current_head: str
    branch: str
    holder_ref: str
    target_holder_ref: str
    expect_head: str
    lease_id: str
    expected_epoch: int | None
    ttl_seconds: int
    offer_id: str
    holder_quiesced: bool = False
    contrary_decision: bool = False
    apply: bool
    initial_gaps: tuple[str, ...] = ()


class LeaseOperationRequest(LifecycleModel):
    """One request shape for every same-common-directory lease transition."""

    operation: str = Field(min_length=1)
    branch: str
    holder_ref: str
    lease_id: str
    expected_epoch: int | None
    expect_head: str
    apply: bool = False
    ttl_seconds: int = 86_400
    target_holder_ref: str = ""
    offer_id: str = ""
    holder_quiesced: bool = False
    contrary_decision: bool = False


class GuardedTransition(LifecycleModel):
    """State names for a fact-only transition with no effectful knowledge."""

    id: str
    planned_state: str = "planned"
    applied_state: str = "applying"


WORK_LANE_MUTATION = MutationTransition(
    id="work_lane_mutation",
    required_role="work_lane",
    role_gap="protected_root_mutation",
    dirty_gap="work_lane_dirty",
    dry_run_short_circuit=True,
    dry_run_checked_commands=("land",),
)

CLOSEOUT_MUTATION = MutationTransition(
    id="accepted_closeout",
    required_role="accepted_root",
    role_gap="accepted_root_required",
    dirty_gap="accepted_root_dirty",
    current_state="current",
)

HANDOFF_EXPORT = GuardedTransition(id="handoff_export")
HANDOFF_IMPORT = GuardedTransition(id="handoff_import")
HANDOFF_REVOKE_SOURCE = GuardedTransition(id="handoff_revoke_source")
LANE_RESOLUTION_DECIDE = GuardedTransition(id="lane_resolution_decide")
LANE_RESOLUTION_APPLY = GuardedTransition(id="lane_resolution_apply")


def reduce_mutation(
    request: MutationRequest,
    *,
    current_head: str,
    facts: MutationFacts,
    transition: MutationTransition,
) -> MutationEvaluation:
    """Reduce declarations and observed facts without filesystem, Git, or time access."""
    if (
        transition.dry_run_short_circuit
        and not request.apply
        and request.command not in transition.dry_run_checked_commands
    ):
        return MutationEvaluation(ok=True, state="dry_run")

    gaps = list(_request_gaps(request, current_head=current_head))
    if facts.role != transition.required_role:
        gaps.append(transition.role_gap)
    elif facts.dirty:
        gaps.append(transition.dirty_gap)
    else:
        gaps.extend(facts.healthy_gaps)
    gaps.extend(facts.always_gaps)
    if request.apply:
        gaps.extend(facts.evidence_gaps)
    if gaps:
        return MutationEvaluation(ok=False, state="blocked", gaps=tuple(gaps))
    if transition.current_state and facts.current:
        return MutationEvaluation(ok=True, state=transition.current_state)
    if not request.apply:
        return MutationEvaluation(ok=True, state="dry_run")
    return MutationEvaluation(ok=True, state=f"{request.command}_ready")


def reduce_lease_request(
    transition: LeaseTransition,
    facts: LeaseFacts,
) -> MutationEvaluation:
    """Reduce lease facts into a deterministic planned, applied, or blocked state."""
    effect_values = {
        "holder_ref": facts.holder_ref,
        "target_holder_ref": facts.target_holder_ref,
        "offer_id": facts.offer_id,
        "holder_quiesced": facts.holder_quiesced,
    }
    effect_value_gaps = {
        "holder_ref": "holder_ref_invalid",
        "target_holder_ref": "target_holder_ref_invalid",
        "offer_id": "handoff_offer_id_required",
        "holder_quiesced": "holder_quiescence_confirmation_required",
    }
    checks = (
        (facts.role == "work_lane", "work_lane_required"),
        (facts.current_branch == facts.branch, "lane_branch_mismatch"),
        (bool(facts.expect_head), "expect_head_required"),
        (not facts.expect_head or facts.current_head == facts.expect_head, "expect_head_mismatch"),
        (bool(facts.lease_id), "lease_id_required"),
        (
            "expected_epoch" not in transition.effect_fields
            or (facts.expected_epoch is not None and facts.expected_epoch >= 1),
            "lease_epoch_required",
        ),
        (
            "ttl_seconds" not in transition.effect_fields or facts.ttl_seconds >= 1,
            "lease_ttl_invalid",
        ),
        (
            not transition.blocks_contrary_decision or not facts.contrary_decision,
            "lease_resume_blocked_by_decision",
        ),
        *(
            (
                effect_values[field] not in ("", None, False),
                effect_value_gaps[field],
            )
            for field in transition.effect_fields
            if field in effect_values
        ),
    )
    return _transition_evaluation(
        applied_state=transition.applied_state,
        apply=facts.apply,
        gaps=(*facts.initial_gaps, *(gap for valid, gap in checks if not valid)),
    )


def reduce_guards(
    transition: GuardedTransition,
    *,
    apply: bool,
    initial_gaps: tuple[str, ...] = (),
    prefix_checks: tuple[tuple[bool, str], ...] = (),
    checks: tuple[tuple[bool, str], ...] = (),
) -> MutationEvaluation:
    """Reduce adapter-observed predicates into one deterministic lifecycle verdict."""
    gaps = [
        *(gap for satisfied, gap in prefix_checks if not satisfied),
        *initial_gaps,
        *(gap for satisfied, gap in checks if not satisfied),
    ]
    return _transition_evaluation(
        applied_state=transition.applied_state,
        planned_state=transition.planned_state,
        apply=apply,
        gaps=tuple(gaps),
    )


def _transition_evaluation(
    *,
    applied_state: str,
    apply: bool,
    gaps: tuple[str, ...],
    planned_state: str = "planned",
) -> MutationEvaluation:
    ordered = tuple(dict.fromkeys(gaps))
    return MutationEvaluation(
        ok=not ordered,
        state="blocked" if ordered else applied_state if apply else planned_state,
        gaps=ordered,
    )


def _request_gaps(request: MutationRequest, *, current_head: str) -> tuple[str, ...]:
    gaps: list[str] = []
    if request.apply and not request.authorized:
        gaps.append("authorization_required")
    if request.apply and request.expect_head is None:
        gaps.append("expect_head_required")
    elif request.expect_head is not None and request.expect_head != current_head:
        gaps.append("expect_head_mismatch")
    return tuple(gaps)
