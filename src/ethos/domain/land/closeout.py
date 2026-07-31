"""Land and accepted-root closeout reducers.

This module owns land-stage lifecycle decisions, runner binding, and repository
audit handoff. Publication, evidence freshness, intake projection, and trust
closeout live in sibling semantic modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos
import ethos.adapters.repo.git as git_adapter
import ethos.domain.status
from ethos.adapters.repo.runtime.binding import runner_source_root
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from ethos.adapters.mutation.decision import MutationDecision
    from ethos.contracts.verdict import Verdict


def closeout_audit_root(repo: Path, decision: MutationDecision) -> Path:
    """Resolve closeout audit root, preserving land.workspace_status patchability."""
    if decision.verdict != "pass":
        return repo
    candidate = workspace_status(repo, include_foreign_path_scope=False).get("candidate", {})
    if not isinstance(candidate, dict):
        return repo
    candidate_path = str(candidate.get("worktree_path") or "")
    return Path(candidate_path) if candidate_path else repo


def runner_binding_report(*, accepted_root: Path, audit_root: Path) -> dict[str, object]:
    """Expose which ETHOS source tree provides the current closeout runner."""
    runner_module_path = Path(ethos.__file__).resolve()
    runner_package_root = runner_module_path.parent
    source_root = runner_source_root(runner_module_path)
    accepted_root_resolved = accepted_root.resolve()
    audit_root_resolved = audit_root.resolve()
    runner_matches_accepted_root = source_root == accepted_root_resolved
    runner_matches_audit_root = source_root == audit_root_resolved
    state = "bound_to_accepted_root" if runner_matches_accepted_root else "external_current_runner"
    return {
        "kind": "closeout_runner_binding",
        "state": state,
        "runner_module_path": runner_module_path.as_posix(),
        "runner_package_root": runner_package_root.as_posix(),
        "runner_source_root": source_root.as_posix(),
        "accepted_root": accepted_root_resolved.as_posix(),
        "audit_root": audit_root_resolved.as_posix(),
        "runner_matches_accepted_root": runner_matches_accepted_root,
        "runner_matches_audit_root": runner_matches_audit_root,
        "advisory_gaps": []
        if runner_matches_accepted_root
        else ["closeout_runner_source_differs_from_accepted_root"],
    }


def closeout_bootstrap_package(
    *,
    repo: Path,
    audit_root: Path,
    required_gaps: tuple[str, ...],
) -> dict[str, object]:
    """Build the closeout bootstrap package (command to run against accepted_root)."""
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo, include_foreign_path_scope=False)
    candidate = status.get("candidate") if isinstance(status.get("candidate"), dict) else {}
    accepted_head = git_adapter.current_tracked_head(repo)
    expect_head = accepted_head or "<HEAD>"
    command = (
        "ethos land --closeout --apply --authorize "
        f"--expect-head {expect_head} --root {repo.resolve().as_posix()} --json"
    )
    runner_binding = runner_binding_report(accepted_root=repo, audit_root=audit_root)
    candidate_data = cast("dict[str, object]", candidate)
    candidate_head = str(candidate_data.get("head") or "")
    candidate_path = str(candidate_data.get("worktree_path") or "")
    already_current = bool(accepted_head and candidate_head == accepted_head)
    proof_target_root = Path(candidate_path).resolve() if candidate_path else audit_root.resolve()
    proof_target = {
        "kind": "closeout_proof_target",
        "role": "candidate",
        "root": proof_target_root.as_posix(),
        "head": candidate_head,
        "reason": "accepted-root closeout promotes the candidate head",
    }
    return {
        "kind": "closeout_bootstrap",
        "mode": "maintainer_break_glass_local",
        "runner_mode": "current_runner_with_explicit_accepted_root",
        "remote_state": "deferred",
        "remote_push": "not_performed",
        "uses_current_runner": True,
        "runner_binding": runner_binding,
        "runner_module_path": runner_binding["runner_module_path"],
        "runner_package_root": runner_binding["runner_package_root"],
        "runner_source_root": runner_binding["runner_source_root"],
        "runner_matches_accepted_root": runner_binding["runner_matches_accepted_root"],
        "runner_matches_audit_root": runner_binding["runner_matches_audit_root"],
        "runner_advisories": runner_binding["advisory_gaps"],
        "state": "blocked" if required_gaps else "current" if already_current else "ready",
        "accepted_root": repo.resolve().as_posix(),
        "audit_root": audit_root.resolve().as_posix(),
        "accepted_branch": policy.accepted_branch,
        "candidate_branch": policy.candidate_branch,
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "proof_target": proof_target,
        "independent_verification": {
            "required": "independent_verification_receipt_required" in required_gaps,
            "proof_floor_id": "ethos:control-replacement:v1",
            "receipt_option": "--independent-verification-receipt <absolute-path>",
            "trust_boundary": "protected-provider",
            "mints_authority": False,
        },
        "blocking": bool(required_gaps),
        "required_gaps": list(required_gaps),
        "command": command,
        "required_order": [
            "run closeout command with a current ETHOS runner",
            "bind --root to the clean accepted_root checkout",
            "audit the configured candidate worktree before accepted-root movement",
            "prove the configured candidate head before accepted-root movement",
            "for a control replacement, obtain the exact protected-provider signed receipt",
            "fast-forward accepted_root from candidate only after proof and lifecycle gates pass",
            "defer remote push until remote publication is available",
        ],
        "next_action": "ethos publish"
        if already_current and not required_gaps
        else "run closeout with a current ETHOS runner against accepted_root",
    }


def land_next_actions(
    *,
    verdict: Verdict,
    gaps: tuple[str, ...],
    current_head: str,
) -> tuple[str, ...]:
    """Derive the recommended next commands after a land attempt."""
    if verdict == "pass":
        return ("ethos publish",)
    if "protected_root_mutation" in gaps:
        return ("ethos land --closeout --json",)
    if "candidate_base_stale" in gaps:
        return (f"ethos lane refresh-base --apply --authorize --expect-head {current_head} --json",)
    active_carriers = tuple(
        gap
        for gap in gaps
        if gap.startswith("openspec_active_change_unarchived:") and gap.endswith(":work_lane")
    )
    if active_carriers:
        return tuple(
            f"openspec archive {gap.split(':', 2)[1]} --yes --json" for gap in active_carriers
        )
    if "proof_not_proven" in gaps:
        return (f"ethos prove --execute --expect-head {current_head} --json",)
    return ("ethos prove --json",)


def closeout_next_actions(
    *,
    verdict: Verdict,
    gaps: tuple[str, ...],
    current_head: str,
    state: str = "",
) -> tuple[str, ...]:
    """Derive recommended next commands after accepted-root closeout."""
    if verdict == "pass" and state == "current":
        return ("ethos publish",)
    if verdict == "pass":
        return ("ethos lane retire landed --branch <work-branch> --expect-head <work-lane-head>",)
    if "candidate_diverged_from_accepted" in gaps:
        return (
            (
                "ethos lane candidate --refresh-from-accepted "
                f"--apply --authorize --expect-head {current_head} --json"
            ),
        )
    if "independent_verification_receipt_required" in gaps:
        return (
            (
                "obtain the signed receipt described by "
                "data.control_replacement.verification_request, then rerun ethos land --closeout "
                "--independent-verification-receipt <absolute-path> --json"
            ),
        )
    return ("ethos prove --json",)


def repository_audit_after_admission(repo: Path, decision: MutationDecision) -> dict[str, object]:
    """Run the shape audit after admission, or skip when mutation was blocked."""
    if decision.verdict != "pass":
        return {
            "verdict": "block",
            "state": "skipped",
            "reason": "mutation_admission_blocked",
            "required_gaps": [],
            "root": repo.as_posix(),
        }
    return ethos.domain.status.audit_for_root(repo, openspec_mode="shape")
