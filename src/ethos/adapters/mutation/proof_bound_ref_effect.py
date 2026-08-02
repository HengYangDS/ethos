"""Proof-bound execution of one exact Git ref effect."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import ethos.adapters.repo.git_effect_attestation
from ethos.adapters.admission.ref_intent import clear_ref_intent
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.mutation.proof import proof_evidence_digest
from ethos.adapters.mutation.proof import proof_plan_for_attestation
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_effects import git_effect_attestations
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path


def execute_proof_bound_ref_effect(*, root: Path, plan: TransitionPlan) -> Attestation:
    """Execute one effect while exact proof-bound ref intents are live."""
    effect = git_effect_from_plan(plan)
    operation = str(plan.policy.get("operation") or "")
    bindings = _proof_bindings(root, plan, effect)
    intents = []
    try:
        intents.extend(
            write_ref_intent(
                root=root,
                ref_name=ref_name,
                update=update,
                operation=operation,
                bindings=bindings,
            )
            for ref_name, update in effect.updates.items()
        )
        attestation = execute_git_effect(
            root,
            plan,
            issuer=os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos",
            attestations=git_effect_attestations(root, effect),
        )
        git_effect_attestations(root, effect, attestation)
        return attestation
    finally:
        for intent in intents:
            clear_ref_intent(root, str(intent["nonce"]))


def _proof_bindings(root: Path, plan: TransitionPlan, effect) -> dict[str, str]:
    proof_set = plan.prior_attestations.get("proof_set")
    try:
        proof = Attestation.model_validate_json(
            json.dumps(mutable_json(plan.prior_attestations["proof"]))
        )
        proof_plan_for_attestation(root, proof)
    except (KeyError, TypeError, ValueError) as error:
        message = f"git_effect_prior_proof_invalid:{error}"
        raise ValueError(message) from error
    proof_head = proof.subject.removeprefix("git:commit:")
    if (
        not isinstance(proof_set, str)
        or not proof_set
        or proof_evidence_digest(root, proof_head) != proof_set
    ):
        message = "git_effect_prior_proof_set_mismatch"
        raise ValueError(message)
    if {update.desired for update in effect.updates.values()} != {proof_head}:
        message = "git_effect_prior_proof_head_mismatch"
        raise ValueError(message)
    accepted_payload = plan.prior_attestations.get("accepted_effect")
    if accepted_payload is not None:
        _validate_accepted_effect(root, effect, accepted_payload)
    return {"evidence_digest": proof_set, "gate_policy_digest": proof.policy_digest}


def _validate_accepted_effect(root: Path, effect, payload: object) -> None:
    try:
        accepted = Attestation.model_validate_json(json.dumps(mutable_json(payload)))
        plan = ethos.adapters.repo.git_effect_attestation.plan_from_attestation(accepted)
        accepted_effect = git_effect_from_plan(plan)
        ethos.adapters.repo.git_effect_attestation.validate(
            root,
            accepted_effect,
            accepted,
            issuer=accepted.verifier,
            plan=plan,
        )
    except (TypeError, ValueError) as error:
        message = f"git_effect_prior_accepted_effect_invalid:{error}"
        raise ValueError(message) from error
    accepted_updates = {ref: update.desired for ref, update in accepted_effect.updates.items()}
    if accepted_updates != effect.assertions:
        message = "git_effect_prior_accepted_effect_mismatch"
        raise ValueError(message)
