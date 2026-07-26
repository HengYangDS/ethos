"""Pure declared lifecycle reduction for exact transition requests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict

if TYPE_CHECKING:
    from ethos.contracts.lifecycle.declaration import TransitionPolicy


class LifecycleModel(BaseModel):
    """Strict immutable base for lifecycle facts and declarations."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


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
    unknown_gaps: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """Return whether the transition is admitted."""
        return self.verdict == "pass"

    @property
    def gaps(self) -> tuple[str, ...]:
        """Project the canonical gap field used by command surfaces."""
        return tuple(dict.fromkeys((*self.required_gaps, *self.unknown_gaps)))


def reduce_transition(
    policy: TransitionPolicy,
    request: TransitionRequest,
    facts: TransitionFacts,
) -> TransitionDecision:
    """Reduce one declared transition into pass, block, or unknown."""
    if (
        not request.apply
        and policy.dry_run_commands
        and request.command not in policy.dry_run_commands
    ):
        return TransitionDecision(verdict="pass", state=policy.planned_state)
    request_checks = (
        (
            not request.apply or not policy.authorization_required or request.authorized,
            "authorization_required",
        ),
        (
            not request.apply
            or not policy.expected_head_required
            or request.expect_head is not None,
            "expect_head_required",
        ),
        (
            request.expect_head is None or request.expect_head == facts.current_head,
            policy.head_mismatch_gap,
        ),
        (
            not policy.untracked_gap or facts.current_head != "untracked",
            policy.untracked_gap,
        ),
    )
    gaps = [gap for satisfied, gap in request_checks if not satisfied]
    if policy.required_role and facts.role and facts.role != policy.required_role:
        gaps.append(policy.role_gap)
    elif policy.dirty_gap and facts.dirty:
        gaps.append(policy.dirty_gap)
    gaps.extend(facts.initial_gaps)
    gaps.extend(gap for satisfied, gap in facts.checks if not satisfied)
    if request.apply:
        gaps.extend(facts.evidence_gaps)
    unknown = tuple(dict.fromkeys(gap for gap in facts.unknown_gaps if gap))
    if ordered := tuple(dict.fromkeys(gap for gap in gaps if gap)):
        return TransitionDecision(
            verdict="block",
            state="blocked",
            required_gaps=ordered,
            unknown_gaps=unknown,
        )
    if unknown:
        return TransitionDecision(verdict="unknown", state="unknown", unknown_gaps=unknown)
    state = (
        policy.current_state
        if policy.current_state and facts.current
        else policy.applied_state
        if request.apply
        else policy.planned_state
    )
    return TransitionDecision(verdict="pass", state=state)
