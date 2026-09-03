from __future__ import annotations

import shlex
from pathlib import Path
from typing import Literal
from typing import cast

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_retirement.linked_admission import effect_readiness_gaps
from ethos.adapters.mutation.lane_retirement.linked_admission import landed_gaps
from ethos.adapters.mutation.lane_retirement.linked_admission import leased_successor
from ethos.adapters.mutation.lane_retirement.linked_admission import retirement_target
from ethos.adapters.mutation.lane_retirement.linked_admission import retirement_verdict
from ethos.adapters.mutation.lane_retirement.linked_admission import superseded_gaps
from ethos.adapters.mutation.lane_retirement.linked_effect import linked_retirement_plan
from ethos.adapters.mutation.lane_retirement.observation import output
from ethos.adapters.mutation.lane_retirement.operation import apply_operation
from ethos.adapters.mutation.lane_retirement.operation import persist_operation
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.retirement import LinkedRetirementRequest
from ethos.contracts.retirement import RetirementOperation
from ethos.normalization.coercion import string_sequence


def compile_retirement_operation(
    control_root: Path,
    *,
    mode: Literal["landed", "superseded"],
    policy: BranchRolePolicy,
    lane: dict[str, object],
    authority: dict[str, object],
    accepted_head: str,
    reason: str,
) -> RetirementOperation:
    """Compile one immutable linked retirement request from admitted facts."""
    actor = effects.actor_ref()
    execution_root, plan = linked_retirement_plan(
        control_root,
        lane,
        accepted=(policy.accepted_branch, accepted_head),
        authority=authority,
        mode=mode,
        actor=actor,
        worktree_clean=True,
    )
    branch = str(lane["branch"])
    lease_state = str(lane.get("lease_state") or "missing")
    target_lease = (
        lease_generation({**cast("dict[str, object]", lane.get("lease") or {}), "lane_ref": branch})
        if lease_state != "missing"
        else {}
    )
    recovery_required = bool(lane.get("recovery_required"))
    return RetirementOperation(
        repository_common_dir=Path(git_common_dir(control_root)).resolve().as_posix(),
        repository_identity=repository_identity(control_root, tree_ref=str(lane["head"])),
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
            "code": "accepted-absorption" if mode == "landed" else "successor-absorption",
            "summary": reason or f"{mode} Work Lane retirement",
        },
        git_plan=plan.model_dump(mode="json"),
    )


def retire_linked_work_lane(
    *,
    root: Path,
    mode: Literal["landed", "superseded"],
    request: LinkedRetirementRequest,
) -> dict[str, object]:
    """Plan or execute one holder-bound linked-lane retirement."""
    repo = repository_root(root)
    status = workspace_status(repo)
    worktrees = cast("list[dict[str, object]]", status["worktrees"])
    policy = load_branch_role_policy(repo)
    branch = (request.branch or "").strip()
    reason = request.reason.strip()
    absorbed_by = request.absorbed_by.strip()
    accepted_head = output(repo, "rev-parse", policy.accepted_branch) or ""
    control_root = effects.control_root(worktrees, repo)
    leases = leases_by_branch(repo)
    lanes, lane = retirement_target(
        repo=repo,
        policy=policy,
        worktrees=worktrees,
        leases=leases,
        request=request,
        mode=mode,
        branch=branch,
        accepted_head=accepted_head,
    )
    successor = (
        leased_successor(
            repo=repo,
            policy=policy,
            worktrees=worktrees,
            leases=leases,
            target_branch=branch,
            absorbed_by=absorbed_by,
            accepted_head=accepted_head,
        )
        if mode == "superseded" and absorbed_by != accepted_head
        else {}
    )
    authority = successor or lane
    gaps = (
        landed_gaps(
            branch=branch,
            request=request,
            lanes=lanes,
        )
        if mode == "landed"
        else superseded_gaps(
            repo=repo,
            policy=policy,
            request=request,
            lane=lane,
            successor=successor,
            accepted_head=accepted_head,
        )
    )
    gaps.extend(
        effect_readiness_gaps(
            repo,
            control_root,
            mode=mode,
            policy=policy,
            lane=lane,
            authority=authority,
            accepted_head=accepted_head,
            required_gaps=gaps,
            apply=request.apply,
        )
    )
    required_gaps = sorted(set(gaps))

    verdict = retirement_verdict(required_gaps)
    if lane:
        lane = {**lane, "retire_ready": not required_gaps, "required_gaps": required_gaps}

    state = "planned" if mode == "landed" else "ready_to_retire_superseded"
    if verdict != "pass":
        state = "blocked" if verdict == "block" else "unknown"

    def mutation(current_gaps: list[str]) -> dict[str, object]:
        required_holder = effects.holder_ref(authority)
        gaps = tuple(sorted(set(current_gaps)))
        current_verdict = retirement_verdict(gaps)
        expected_state = {
            "ref": f"refs/heads/{branch}" if branch else "",
            "head": (request.expect_head or "").strip(),
            "path": (request.path or "").strip(),
            "invocation_holder_ref": effects.actor_ref(),
            "required_holder_ref": required_holder,
            "authority_branch": authority.get("branch", ""),
            "authority_head": authority.get("head", ""),
            "accepted_head": accepted_head,
            "lease": authority.get("lease", {}),
            "target_lease": lane.get("lease", {}),
            **({"absorbed_by": absorbed_by, "reason": reason} if mode == "superseded" else {}),
        }
        decision = admission_decision(
            subject=MutationSubject(
                action=f"lane.retire.{mode}",
                resource=f"refs/heads/{branch}" if branch else "work-lane",
                expected_state=expected_state,
            ),
            verdict=current_verdict,
            basis=DecisionBasis(
                enforcement_boundary=(
                    "sqlite_generation_lock_and_git_ref_transaction"
                    if required_holder
                    else "git_ref_and_worktree_transition"
                ),
                identity_basis="exact_lease_generation" if required_holder else "not_evaluated",
                state_bindings=tuple(expected_state),
                evidence_boundary="current_git_lane_and_lease_observation",
                verifier_provenance="current_runner",
                time_basis="evaluation_time",
            ),
            policy_ref=(
                "openspec/specs/repository-governance/spec.md"
                "#linked-work-lane-retirement-has-one-exact-effect"
                if mode == "landed"
                else "commitment:lane-retire-superseded-admission"
            ),
            required_gaps=gaps,
            why=("ready",) if current_verdict == "pass" else (),
        )
        return mutation_envelope(
            command=f"lane-retire-{mode}",
            apply=request.apply,
            authorized=request.authorize,
            expect_head=request.expect_head,
            decision=decision,
        )

    report: dict[str, object] = {
        "verdict": verdict,
        "state": state,
        "branch": branch,
        "mutation": mutation(required_gaps),
        "required_gaps": required_gaps,
        **({"lanes": lanes} if mode == "landed" else {"lane": lane}),
    }
    report |= _continuation(
        repo,
        mode=mode,
        request=request,
        report=report,
        authority=authority,
    )
    if required_gaps:
        return report
    if not request.apply:
        return report

    operation = compile_retirement_operation(
        cast("Path", control_root),
        mode=mode,
        policy=policy,
        lane=lane,
        authority=authority,
        accepted_head=accepted_head,
        reason=reason,
    )
    receipt = persist_operation(cast("Path", control_root), operation)
    effect = apply_operation(
        cast("Path", control_root),
        operation,
        request_receipt=receipt,
        apply=True,
    )
    effect_gaps = string_sequence(effect.get("required_gaps"))
    return report | effect | {"receipt": receipt, "mutation": mutation(effect_gaps)}


def _continuation(
    repo: Path,
    *,
    mode: Literal["landed", "superseded"],
    request: LinkedRetirementRequest,
    report: dict[str, object],
    authority: dict[str, object],
) -> dict[str, object]:
    """Return the sole public continuation owned by linked retirement."""
    gaps = tuple(string_sequence(report.get("required_gaps")))
    holder = effects.holder_ref(authority)
    if "foreign_work_lane_retire_authority_required" in gaps and holder:
        return {
            "next_action": f"export ETHOS_ACTOR={shlex.quote(holder)}",
            "user_decision_required": True,
        }
    if gaps:
        return {
            "next_action": f"ethos lane status --root {shlex.quote(repo.as_posix())} --json",
            "user_decision_required": "authorization_required" in gaps,
        }
    if request.apply:
        return {
            "next_action": f"ethos status --root {shlex.quote(repo.as_posix())} --json",
            "user_decision_required": False,
        }
    parts = ["ethos", "lane", "retire", mode]
    for option, value in (
        ("--branch", request.branch),
        ("--path", request.path if mode == "superseded" else None),
        ("--expect-head", request.expect_head),
        ("--absorbed-by", request.absorbed_by if mode == "superseded" else None),
        ("--reason", request.reason if mode == "superseded" else None),
    ):
        if value:
            parts.extend((option, shlex.quote(value)))
    parts.extend(("--authorize", "--apply", "--root", shlex.quote(repo.as_posix()), "--json"))
    return {"next_action": " ".join(parts), "user_decision_required": True}
