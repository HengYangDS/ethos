"""Admit candidate acceptance against the incumbent branch policy."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.accepted.promotion as accepted
import ethos.adapters.mutation.remediation.guidance as remediation
from ethos.adapters.mutation.decision import evaluate_closeout_mutation
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.workspace import integration_coordinates
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_release_text

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


def candidate_to_accepted(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
    candidate_head: str | None = None,
    control_replacement_receipt: dict[str, object] | None = None,
    apply: bool = True,
    identity_transition: bool = False,
    completed_effect: Attestation | None = None,
) -> dict[str, object]:
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    try:
        policy = accepted_transition_policy(root, current_head)
    except (TypeError, ValueError):
        return {
            "verdict": "block",
            "state": "blocked",
            "branch": "",
            "head": current_head,
            "required_gaps": ["accepted_policy_unavailable"],
        }
    decision = evaluate_closeout_mutation(
        apply=apply,
        authorized=authorized,
        expect_head=expect_head,
        root=root,
        current_head=current_head,
        completed_effect=completed_effect,
    )
    if decision.verdict != "pass":
        return {
            **accepted.accepted_payload(policy, current_head),
            "state": "blocked",
            "required_gaps": list(decision.required_gaps),
            "remediation": remediation.remediation_for_gaps(decision.required_gaps),
        }
    status = integration_coordinates(root, policy=policy)
    candidate = cast("dict[str, object]", status["candidate"])
    observed_candidate_head = str(candidate["head"])
    if candidate_head is not None and observed_candidate_head != candidate_head:
        gaps = ["candidate_head_changed_after_control_replacement_check"]
        return {
            **accepted.accepted_payload(policy, current_head),
            "candidate_head": observed_candidate_head,
            "verified_candidate_head": candidate_head,
            "required_gaps": gaps,
            "remediation": remediation.remediation_for_gaps(gaps),
        }
    candidate_head = candidate_head or observed_candidate_head
    if current := accepted.current_acceptance(
        root=root,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
        status=status,
        expected_head=expect_head,
    ):
        if apply and current.get("state") == "accepted_materialization_pending":
            return accepted.recover_current_acceptance(
                root=root,
                policy=policy,
                current_head=current_head,
                status=status,
                current=current,
            )
        return current
    return accepted.promote_candidate(
        root=root,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
        status=status,
        control_replacement_receipt=control_replacement_receipt,
        apply=apply,
        identity_transition=identity_transition,
    )


def accepted_transition_policy(root: Path, head: str) -> BranchRolePolicy:
    """Read the incumbent policy; use defaults only for a provably absent carrier."""
    if release := committed_file_text(root, head, ".ethos/release.toml"):
        return strict_branch_role_policy_from_release_text(release)
    present = run_git(
        root,
        "ls-tree",
        "--name-only",
        head,
        "--",
        ".ethos/release.toml",
        check=False,
    )
    if present.returncode or present.stdout.strip():
        message = "accepted transition policy is unreadable"
        raise ValueError(message)
    return BranchRolePolicy()
