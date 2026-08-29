"""Exact Git effect compilation for linked Work Lane retirement."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Commitment
from ethos.contracts.value import mutable_json


def linked_retirement_plan(
    control_root: Path,
    lane: dict[str, object],
    *,
    accepted: tuple[str, str],
    authority: dict[str, object],
):
    """Compile the exact linked-lane deletion used by readiness and apply."""
    accepted_branch, accepted_head = accepted
    authority_branch = str(authority.get("branch") or "")
    authority_head = str(authority.get("head") or "")
    authority_path = str(authority.get("path") or "")
    authority_lease = {
        **cast("dict[str, object]", authority.get("lease") or {}),
        "lane_ref": authority_branch,
    }
    branch, expected = (str(lane.get(key) or "") for key in ("branch", "head"))
    transaction_root = (
        Path(authority_path)
        if authority_branch not in {accepted_branch, branch} and Path(authority_path).is_dir()
        else control_root
    )
    execution_branch = authority_branch if transaction_root != control_root else accepted_branch
    execution_head = authority_head if transaction_root != control_root else accepted_head
    assertions = {f"refs/heads/{accepted_branch}": accepted_head}
    if authority_branch not in {accepted_branch, branch}:
        assertions[f"refs/heads/{authority_branch}"] = authority_head
    effect = GitEffect(
        updates={
            f"refs/heads/{branch}": GitRefUpdate(expected=expected, desired="0" * len(expected))
        },
        assertions=assertions,
    )
    proof = proof_attestation(transaction_root, execution_head)
    if proof is None:
        msg = "proof_not_proven"
        raise ValueError(msg)
    commitment_payload = plan_from_statement(proof).commitment
    if commitment_payload is None:
        msg = "proof_commitment_missing"
        raise ValueError(msg)
    commitment = Commitment.model_validate(mutable_json(commitment_payload), strict=False)
    return transaction_root, compile_observed_git_effect(
        transaction_root,
        commitment,
        effect,
        head=execution_head,
        prior_attestations={},
        policy={
            "operation": "lane.retire",
            "retirement_kind": "linked-lane",
            "branch": branch,
            "accepted_branch": accepted_branch,
            "accepted_head": accepted_head,
            "authority_branch": authority_branch,
            "authority_head": authority_head,
            "execution_branch": execution_branch,
        },
        values={
            "retired_head": expected,
            "lease_generation": lease_generation(authority_lease),
            **(
                {"archive_absorption": lane["archive_absorption"]}
                if lane.get("archive_absorption")
                else {}
            ),
        },
    )
