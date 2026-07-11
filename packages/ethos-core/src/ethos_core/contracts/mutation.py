"""Pure, declared lifecycle reduction for exact mutation requests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MutationRequest:
    """The bounded intent and confirmation supplied to a mutation boundary."""

    command: str
    apply: bool
    authorized: bool
    expect_head: str | None

    def to_payload(self) -> dict[str, object]:
        """Project intent without performing authorization or mutation."""
        return {
            "command": self.command,
            "apply": self.apply,
            "confirmation_present": self.authorized,
            "expect_head": self.expect_head,
        }


@dataclass(frozen=True)
class MutationEvaluation:
    """Pure lifecycle decision; the public contract remains ``AdmissionDecision``."""

    ok: bool
    state: str
    gaps: tuple[str, ...] = ()


@dataclass(frozen=True)
class MutationTransition:
    """Immutable transition declaration interpreted by ``reduce_mutation``."""

    id: str
    required_role: str
    role_gap: str
    dirty_gap: str
    dry_run_short_circuit: bool = False
    current_state: str = ""


@dataclass(frozen=True)
class MutationFacts:
    """Already-observed facts supplied by an imperative adapter to the reducer."""

    role: str = ""
    dirty: bool = False
    healthy_gaps: tuple[str, ...] = ()
    always_gaps: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()
    current: bool = False


WORK_LANE_MUTATION = MutationTransition(
    id="work_lane_mutation",
    required_role="work_lane",
    role_gap="protected_root_mutation",
    dirty_gap="work_lane_dirty",
    dry_run_short_circuit=True,
)

CLOSEOUT_MUTATION = MutationTransition(
    id="accepted_closeout",
    required_role="accepted_root",
    role_gap="accepted_root_required",
    dirty_gap="accepted_root_dirty",
    current_state="current",
)


def reduce_mutation(
    request: MutationRequest,
    *,
    current_head: str,
    facts: MutationFacts,
    transition: MutationTransition,
) -> MutationEvaluation:
    """Reduce declarations and observed facts without filesystem, Git, or time access."""
    if transition.dry_run_short_circuit and not request.apply:
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


def _request_gaps(request: MutationRequest, *, current_head: str) -> tuple[str, ...]:
    gaps: list[str] = []
    if request.apply and not request.authorized:
        gaps.append("authorization_required")
    if request.apply and request.expect_head is None:
        gaps.append("expect_head_required")
    elif request.expect_head is not None and request.expect_head != current_head:
        gaps.append("expect_head_mismatch")
    return tuple(gaps)
