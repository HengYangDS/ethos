"""Exact Git effect compilation for linked Work Lane retirement."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from ethos.adapters.mutation.lane_retirement.content import reviewed_content
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.bindings import has_changed_paths
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.retirement import RetirementOperation
from ethos.contracts.semantic import Commitment
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from ethos.contracts.branch.roles import BranchRolePolicy


def linked_retirement_plan(
    control_root: Path,
    lane: dict[str, object],
    *,
    accepted: tuple[str, str],
    authority: dict[str, object],
    mode: Literal["landed", "superseded", "abandon"],
    actor: str,
    worktree_clean: bool,
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
    authority_lease_state = str(authority.get("lease_state") or "unknown")
    transaction_root = (
        Path(authority_path)
        if authority_branch not in {accepted_branch, branch} and Path(authority_path).is_dir()
        else control_root
    )
    execution_branch = authority_branch if transaction_root != control_root else accepted_branch
    execution_head = authority_head if transaction_root != control_root else accepted_head
    retained = cast("dict[str, str]", lane.get("retained_history") or {})
    assertions = {f"refs/heads/{accepted_branch}": accepted_head}
    if authority_branch not in {accepted_branch, branch}:
        assertions[f"refs/heads/{authority_branch}"] = authority_head
    if retained:
        assertions[retained["ref"]] = retained["head"]
    effect = GitEffect(
        updates={
            f"refs/heads/{branch}": GitRefUpdate(expected=expected, desired="0" * len(expected))
        },
        assertions=assertions,
    )
    commitment = None
    if mode == "superseded" and not retained:
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
            "retirement_mode": mode,
            "actor": actor,
            "subject": branch,
            "execution_branch": execution_branch,
            **(
                {"repository_prestate": "absent"}
                if mode in {"landed", "abandon"} or retained
                else {}
            ),
        },
        values={
            "linked_worktree": {
                "path": str(lane.get("path") or ""),
                "clean": worktree_clean,
            },
            **({"retained_history": retained} if retained else {}),
            "target_lease_state": str(lane.get("lease_state") or "unknown"),
            **(
                {
                    "lease_generation": lease_generation(authority_lease),
                    "lease_generation_state": authority_lease_state,
                }
                if authority_lease_state in {"valid", "expired"}
                else {}
            ),
            **(
                {"archive_absorption": lane["archive_absorption"]}
                if lane.get("archive_absorption")
                else {}
            ),
        },
    )


def compile_retirement_operation(
    control_root: Path,
    *,
    mode: Literal["landed", "superseded", "abandon"],
    policy: BranchRolePolicy,
    lane: dict[str, object],
    authority: dict[str, object],
    accepted_head: str,
    reason: str,
    actor: str,
    reason_code: str = "",
    review_content: bool = False,
) -> RetirementOperation:
    """Compile one immutable linked retirement request from admitted facts."""
    recovery_required = bool(lane.get("recovery_required")) or not lane.get("path")
    execution_root, plan = linked_retirement_plan(
        control_root,
        lane,
        accepted=(policy.accepted_branch, accepted_head),
        authority=authority,
        mode=mode,
        actor=actor,
        worktree_clean=recovery_required or not has_changed_paths(Path(str(lane["path"]))),
    )
    branch = str(lane["branch"])
    lease_state = str(lane.get("lease_state") or "missing")
    target_lease = (
        lease_generation({**cast("dict[str, object]", lane.get("lease") or {}), "lane_ref": branch})
        if lease_state != "missing"
        else {}
    )
    return RetirementOperation(
        repository_common_dir=Path(git_common_dir(control_root)).resolve().as_posix(),
        repository_identity=repository_identity(control_root, tree_ref=accepted_head),
        control_root=control_root.resolve().as_posix(),
        execution_root=execution_root.resolve().as_posix(),
        mode=mode,
        branch=branch,
        head=str(lane["head"]),
        tree=current_tree(control_root, str(lane["head"])),
        accepted_branch=policy.accepted_branch,
        accepted_head=accepted_head,
        worktree_path=str(lane.get("path") or ""),
        worktree_initial="unbound" if recovery_required else "linked",
        lease_state=cast("Literal['valid', 'expired', 'missing']", lease_state),
        lease=target_lease,
        authority={
            "kind": "successor" if authority.get("branch") != lane.get("branch") else "owner",
            "actor": actor,
            "branch": str(authority.get("branch") or ""),
            "head": str(authority.get("head") or ""),
        },
        reason={
            "code": reason_code
            or (
                "retained-history"
                if lane.get("retained_history")
                else "accepted-absorption"
                if mode == "landed"
                else "successor-absorption"
            ),
            "summary": reason or f"{mode} Work Lane retirement",
        },
        git_plan=plan.model_dump(mode="json"),
        reviewed_content=reviewed_content(Path(str(lane["path"]))) if review_content else {},
    )
