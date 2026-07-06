"""Land/publish-stage domain reducers — closeout, submit, intake, publication.

Pure reducers over primitives + adapter reports for the land→publish tail of the
loop. Imports flow downward (adapters/kernel), keeping the surface→domain layering
acyclic.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import ethos
from ethos.adapters.repo import git as _gitio
from ethos.adapters.repo.status import workspace_status
from ethos.domain.campaign_closeout import campaign_closeout_report
from ethos.domain.land_support import acceptable_parity_product_heads
from ethos.domain.land_support import acceptable_parity_target_heads
from ethos.domain.land_support import closeout_next_actions
from ethos.domain.land_support import command_is_executed_proof
from ethos.domain.land_support import intake_projection_report
from ethos.domain.land_support import land_next_actions
from ethos.domain.land_support import local_submit_package
from ethos.domain.land_support import publication_readiness
from ethos.domain.land_support import remote_publication_deferred
from ethos.domain.land_support import repository_audit_after_admission
from ethos.domain.land_support import trust_closeout_package
from ethos_core.contracts.branch_roles import load_branch_role_policy

__all__ = (
    "acceptable_parity_product_heads",
    "acceptable_parity_target_heads",
    "campaign_closeout_report",
    "closeout_audit_root",
    "closeout_bootstrap_package",
    "closeout_next_actions",
    "command_is_executed_proof",
    "intake_projection_report",
    "land_next_actions",
    "local_submit_package",
    "publication_readiness",
    "remote_publication_deferred",
    "repository_audit_after_admission",
    "runner_binding_report",
    "trust_closeout_package",
)


def closeout_audit_root(repo: Path, decision: object) -> Path:
    """Resolve closeout audit root, preserving land.workspace_status patchability."""
    if not getattr(decision, "ok", False):
        return repo
    candidate = workspace_status(repo).get("candidate", {})
    if not isinstance(candidate, dict):
        return repo
    candidate_path = str(candidate.get("worktree_path") or "")
    return Path(candidate_path) if candidate_path else repo


def _runner_source_root(module_path: Path) -> Path:
    """Find the repository source root for a runner module when available."""
    for parent in (module_path.parent, *module_path.parents):
        if (parent / "pyproject.toml").exists() and (
            parent / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
        ).exists():
            return parent
    return module_path.parent


def runner_binding_report(*, accepted_root: Path, audit_root: Path) -> dict[str, object]:
    """Expose which ETHOS source tree provides the current closeout runner."""
    runner_module_path = Path(ethos.__file__).resolve()
    runner_package_root = runner_module_path.parent
    runner_source_root = _runner_source_root(runner_module_path)
    accepted_root_resolved = accepted_root.resolve()
    audit_root_resolved = audit_root.resolve()
    runner_matches_accepted_root = runner_source_root == accepted_root_resolved
    runner_matches_audit_root = runner_source_root == audit_root_resolved
    state = "bound_to_accepted_root" if runner_matches_accepted_root else "external_current_runner"
    return {
        "kind": "closeout_runner_binding",
        "state": state,
        "runner_module_path": runner_module_path.as_posix(),
        "runner_package_root": runner_package_root.as_posix(),
        "runner_source_root": runner_source_root.as_posix(),
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
    status = workspace_status(repo)
    candidate = status.get("candidate") if isinstance(status.get("candidate"), dict) else {}
    accepted_head = _gitio.current_tracked_head(repo)
    expect_head = accepted_head or "<HEAD>"
    command = (
        "ethos land --closeout --apply --authorize "
        f"--expect-head {expect_head} --root {repo.resolve().as_posix()} --json"
    )
    runner_binding = runner_binding_report(accepted_root=repo, audit_root=audit_root)
    candidate_data = cast("dict[str, object]", candidate)
    candidate_head = str(candidate_data.get("head") or "")
    candidate_path = str(candidate_data.get("worktree_path") or "")
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
        "state": "blocked" if required_gaps else "ready",
        "accepted_root": repo.resolve().as_posix(),
        "audit_root": audit_root.resolve().as_posix(),
        "accepted_branch": policy.accepted_branch,
        "candidate_branch": policy.candidate_branch,
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "proof_target": proof_target,
        "blocking": bool(required_gaps),
        "required_gaps": list(required_gaps),
        "command": command,
        "required_order": [
            "run closeout command with a current ETHOS runner",
            "bind --root to the clean accepted_root checkout",
            "audit the configured candidate worktree before accepted-root movement",
            "prove the configured candidate head before accepted-root movement",
            "fast-forward accepted_root from candidate only after proof and lifecycle gates pass",
            "defer remote push until remote publication is available",
        ],
        "next_action": "run closeout with a current ETHOS runner against accepted_root",
    }
