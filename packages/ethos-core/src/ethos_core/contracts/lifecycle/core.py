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
    dry_run_checked_commands: tuple[str, ...] = ()
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


@dataclass(frozen=True)
class LeaseTransition:
    """Immutable operation declaration for the local lease lifecycle."""

    id: str
    applied_state: str
    requires_epoch: bool = True
    requires_offer: bool = False


@dataclass(frozen=True)
class LeaseFacts:
    """Observed local lease facts supplied to the pure lease reducer."""

    role: str
    current_branch: str
    current_head: str
    branch: str
    expect_head: str
    lease_id: str
    epoch: int | None
    ttl_seconds: int
    offer_id: str
    apply: bool
    initial_gaps: tuple[str, ...] = ()


@dataclass(frozen=True)
class GuardedTransition:
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

LEASE_TRANSITIONS = (
    LeaseTransition(id="normalize", applied_state="normalized", requires_epoch=False),
    LeaseTransition(id="renew", applied_state="renewed"),
    LeaseTransition(id="resume", applied_state="resumed"),
    LeaseTransition(id="handoff_offer", applied_state="handoff_offered"),
    LeaseTransition(
        id="handoff_accept",
        applied_state="handoff_accepted",
        requires_offer=True,
    ),
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


def lease_transition(operation: str) -> LeaseTransition:
    """Resolve one declared lease transition without reaching into adapter state."""
    for transition in LEASE_TRANSITIONS:
        if transition.id == operation:
            return transition
    msg = f"lease_operation_unknown:{operation}"
    raise ValueError(msg)


def reduce_lease_request(
    transition: LeaseTransition,
    facts: LeaseFacts,
) -> MutationEvaluation:
    """Reduce lease facts into a deterministic planned, applied, or blocked state."""
    gaps = list(facts.initial_gaps)
    if facts.role != "work_lane":
        gaps.append("work_lane_required")
    if facts.current_branch != facts.branch:
        gaps.append("lane_branch_mismatch")
    if not facts.expect_head:
        gaps.append("expect_head_required")
    elif facts.current_head != facts.expect_head:
        gaps.append("expect_head_mismatch")
    if not facts.lease_id:
        gaps.append("lease_id_required")
    if transition.requires_epoch and (facts.epoch is None or facts.epoch < 1):
        gaps.append("lease_epoch_required")
    if facts.ttl_seconds < 1:
        gaps.append("lease_ttl_invalid")
    if transition.requires_offer and not facts.offer_id:
        gaps.append("handoff_offer_id_required")
    ordered_gaps = tuple(dict.fromkeys(gaps))
    return MutationEvaluation(
        ok=not ordered_gaps,
        state="blocked" if ordered_gaps else transition.applied_state if facts.apply else "planned",
        gaps=ordered_gaps,
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
    ordered_gaps = tuple(dict.fromkeys(gaps))
    return MutationEvaluation(
        ok=not ordered_gaps,
        state="blocked"
        if ordered_gaps
        else transition.applied_state
        if apply
        else transition.planned_state,
        gaps=ordered_gaps,
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
