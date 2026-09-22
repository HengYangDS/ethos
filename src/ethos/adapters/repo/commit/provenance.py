"""Resolve accepted commit provenance across validated identity-only ref repairs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.commit.signature import completed_signature_repair
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate
from ethos.contracts.plan import git_effect_from_plan

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Attestation


class AcceptedProvenance(NamedTuple):
    """Keep the original proof separate from current coordinates and repair witnesses."""

    plan: TransitionPlan
    attestation: Attestation
    head: str
    previous_head: str
    repair_attestations: tuple[str, ...] = ()

    def projection(self) -> dict[str, object]:
        """Project verified relationships without issuing another Attestation."""
        return {
            "head": self.head,
            "previous_head": self.previous_head,
            "attestation_id": self.attestation.id,
            "plan_digest": self.plan.digest,
            "repair_attestation_ids": list(self.repair_attestations),
        }


def accepted_provenance(
    root: Path, *, accepted_ref: str, candidate_ref: str, head: str
) -> AcceptedProvenance | None:
    """Validate only matching acceptance plans and exact completed ref-repair paths."""
    try:
        _, attestations = read_attestation_set(root)
    except ValueError as error:
        message = "accepted_closeout_effect_invalid"
        raise ValueError(message) from error
    candidates: dict[str, list[Attestation]] = {}
    for attestation in attestations:
        coordinate = _accepted_head(attestation, accepted_ref, candidate_ref)
        if coordinate is not None:
            candidates.setdefault(coordinate, []).append(attestation)
    current = head
    seen: set[str] = set()
    repairs: list[dict[str, object]] = []
    while current not in seen:
        seen.add(current)
        selected = _validated_acceptance(root, candidates.get(current, ()), accepted_ref)
        if selected:
            plan, attestation, previous = selected
            for repair in reversed(repairs):
                mapping = repair["mapping"]
                assert isinstance(mapping, Mapping)
                previous = str(mapping.get(previous, previous))
            return AcceptedProvenance(
                plan,
                attestation,
                head,
                previous,
                tuple(str(repair["attestation_id"]) for repair in reversed(repairs)),
            )
        repair = completed_signature_repair(root, new=current, attestations=attestations)
        if repair is None:
            return None
        refs = repair["refs"]
        assert isinstance(refs, Mapping)
        previous = str(repair["old"])
        if refs.get(accepted_ref) != previous:
            return None
        repairs.append(repair)
        current = previous
    message = "accepted_closeout_effect_ambiguous"
    raise ValueError(message)


def _validated_acceptance(
    root: Path, candidates: Iterable[Attestation], accepted_ref: str
) -> tuple[TransitionPlan, Attestation, str] | None:
    """Require one complete canonical proof among the coordinate-matched records."""
    matches = []
    for attestation in candidates:
        try:
            plan = plan_from_attestation(attestation)
            effect = git_effect_from_plan(plan)
            validate(
                root,
                effect,
                attestation,
                issuer=attestation.verifier,
                plan=plan,
                current_postconditions=False,
            )
        except ValueError:
            continue
        matches.append((plan, attestation, effect.updates[accepted_ref].expected))
    if len(matches) > 1:
        message = "accepted_closeout_effect_ambiguous"
        raise ValueError(message)
    return matches[0] if matches else None


def _accepted_head(attestation: Attestation, accepted_ref: str, candidate_ref: str) -> str | None:
    """Filter immutable envelope coordinates; a match still requires full validation."""
    plan = attestation.payload.body.get("plan")
    if attestation.predicate != "effect:git-ref-update" or not isinstance(plan, Mapping):
        return None
    policy, effect = plan.get("policy"), plan.get("effect")
    if not isinstance(policy, Mapping) or not isinstance(effect, Mapping):
        return None
    if policy.get("transition") != "candidate.accept":
        return None
    updates, assertions = effect.get("updates"), effect.get("assertions")
    if not isinstance(updates, Mapping) or not isinstance(assertions, Mapping):
        return None
    update = updates.get(accepted_ref)
    if not isinstance(update, Mapping):
        return None
    head = update.get("desired")
    return head if isinstance(head, str) and assertions.get(candidate_ref) == head else None
