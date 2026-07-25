"""Pure declared lifecycle reduction for exact transition requests."""

from __future__ import annotations

from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

_EFFECT_FIELDS_INVALID = "transition_effect_fields_invalid"


class LifecycleModel(BaseModel):
    """Strict immutable base for lifecycle facts and declarations."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class TransitionDeclaration(LifecycleModel):
    """One declared transition interpreted only by ``reduce_transition``."""

    id: str = Field(min_length=1)
    applied_state: str = Field(min_length=1)
    planned_state: str = "planned"
    current_state: str = ""
    required_role: str = ""
    role_gap: str = ""
    dirty_gap: str = ""
    authorization_required: bool = False
    expected_head_required: bool = False
    head_mismatch_gap: str = "expect_head_mismatch"
    untracked_gap: str = ""
    effect_fields: tuple[str, ...] = Field(default=(), strict=False)
    actor_field: Literal["holder_ref", "target_holder_ref"] | None = None
    blocks_contrary_decision: bool = False

    @field_validator("effect_fields")
    @classmethod
    def compile_effect_fields(cls, fields: tuple[str, ...]) -> tuple[str, ...]:
        if any(not field for field in fields) or len(fields) != len(set(fields)):
            raise ValueError(_EFFECT_FIELDS_INVALID)
        return fields

    @model_validator(mode="after")
    def bind_actor_to_effect(self) -> Self:
        if self.effect_fields and self.actor_field is None:
            raise ValueError(_EFFECT_FIELDS_INVALID)
        if self.actor_field is not None and self.actor_field not in self.effect_fields:
            raise ValueError(_EFFECT_FIELDS_INVALID)
        return self


class TransitionRequest(LifecycleModel):
    """The bounded caller intent supplied to a transition boundary."""

    command: str = ""
    apply: bool = False
    authorized: bool = False
    expect_head: str | None = None

    def to_payload(self) -> dict[str, object]:
        """Project intent without exposing confirmation as reusable authority."""
        return {
            **self.model_dump(exclude={"authorized"}),
            "confirmation_present": self.authorized,
        }


class TransitionFacts(LifecycleModel):
    """Already-observed facts supplied without filesystem, Git, or clock access."""

    current_head: str = ""
    role: str = ""
    dirty: bool = False
    current: bool = False
    initial_gaps: tuple[str, ...] = ()
    checks: tuple[tuple[bool, str], ...] = ()
    evidence_gaps: tuple[str, ...] = ()
    unknown_gaps: tuple[str, ...] = ()


class TransitionDecision(LifecycleModel):
    """Closed lifecycle verdict over one request and fact snapshot."""

    verdict: Literal["pass", "block", "unknown"]
    state: str
    required_gaps: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """Return whether the transition is admitted."""
        return self.verdict == "pass"

    @property
    def gaps(self) -> tuple[str, ...]:
        """Project the canonical gap field used by command surfaces."""
        return self.required_gaps


class LeaseOperationRequest(LifecycleModel):
    """One request shape for every local lease transition."""

    operation: str = Field(min_length=1)
    branch: str
    holder_ref: str
    lease_id: str
    expected_epoch: int | None
    expect_head: str
    expected_expires_at: str = Field(min_length=1)
    expected_payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    apply: bool = False
    ttl_seconds: int = 86_400
    target_holder_ref: str = ""
    offer_id: str = ""
    holder_quiesced: bool = False
    contrary_decision: bool = False


GUARDED_TRANSITION = TransitionDeclaration(id="guarded", applied_state="applying")
WORK_LANE_TRANSITION = TransitionDeclaration(
    id="work_lane",
    applied_state="work_lane_ready",
    planned_state="dry_run",
    required_role="work_lane",
    role_gap="protected_root_mutation",
    dirty_gap="work_lane_dirty",
    authorization_required=True,
    expected_head_required=True,
)
CLOSEOUT_TRANSITION = TransitionDeclaration(
    id="closeout",
    applied_state="closeout_ready",
    planned_state="dry_run",
    current_state="current",
    required_role="accepted_root",
    role_gap="accepted_root_required",
    dirty_gap="accepted_root_dirty",
    authorization_required=True,
    expected_head_required=True,
)
ADOPT_TRANSITION = TransitionDeclaration(
    id="adopt",
    applied_state="applying",
    authorization_required=True,
    expected_head_required=True,
    head_mismatch_gap="expected_head_mismatch",
    untracked_gap="git_repository_missing",
)


def reduce_transition(
    declaration: TransitionDeclaration,
    request: TransitionRequest,
    facts: TransitionFacts,
) -> TransitionDecision:
    """Reduce one declared transition into pass, block, or unknown."""
    if declaration is WORK_LANE_TRANSITION and not request.apply and request.command != "land":
        return TransitionDecision(verdict="pass", state=declaration.planned_state)
    request_checks = (
        (
            not request.apply or not declaration.authorization_required or request.authorized,
            "authorization_required",
        ),
        (
            not request.apply
            or not declaration.expected_head_required
            or request.expect_head is not None,
            "expect_head_required",
        ),
        (
            request.expect_head is None or request.expect_head == facts.current_head,
            declaration.head_mismatch_gap,
        ),
        (
            not declaration.untracked_gap or facts.current_head != "untracked",
            declaration.untracked_gap,
        ),
    )
    gaps = [gap for satisfied, gap in request_checks if not satisfied]
    if declaration.required_role and facts.role and facts.role != declaration.required_role:
        gaps.append(declaration.role_gap)
    elif declaration.dirty_gap and facts.dirty:
        gaps.append(declaration.dirty_gap)
    gaps.extend(facts.initial_gaps)
    gaps.extend(gap for satisfied, gap in facts.checks if not satisfied)
    if request.apply:
        gaps.extend(facts.evidence_gaps)
    if ordered := tuple(dict.fromkeys(gap for gap in gaps if gap)):
        return TransitionDecision(verdict="block", state="blocked", required_gaps=ordered)
    if unknown := tuple(dict.fromkeys(gap for gap in facts.unknown_gaps if gap)):
        return TransitionDecision(verdict="unknown", state="unknown", required_gaps=unknown)
    state = (
        declaration.current_state
        if declaration.current_state and facts.current
        else declaration.applied_state
        if request.apply
        else declaration.planned_state
    )
    return TransitionDecision(verdict="pass", state=state)
