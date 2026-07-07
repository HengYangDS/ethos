"""Shared land/publish support reducers.

These helpers are imported by both land and campaign closeout so the campaign
surface can stay out of the land module and the domain package remains acyclic.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo import git as _gitio
from ethos.adapters.repo.status import workspace_status
from ethos.repository.evidence.parity import PARITY_RELEVANT_PATHS

if TYPE_CHECKING:
    from ethos.adapters.mutation.core import MutationDecision
    from ethos_core.contracts.branch_roles import BranchRolePolicy


def command_is_executed_proof(command: object) -> bool:
    """True when a prove command carries the --execute flag (executed proof)."""
    text = str(command)
    return "prove" in text and "--execute" in text


def remote_publication_deferred(
    remote_availability: dict[str, object] | None = None,
) -> dict[str, object]:
    """Describe the deferred remote-publication state (no remote adapter success)."""
    availability = remote_availability or {
        "kind": "git_remote_availability",
        "remote": "origin",
        "state": "not_probed",
        "available": False,
        "blocking": False,
        "required_gaps": [],
        "advisory_gaps": [],
    }
    state = str(availability.get("state") or "not_probed")
    reason = (
        "remote unavailable; use local-ci fallback evidence"
        if state in {"unavailable", "unconfigured"}
        else "remote publication adapter unavailable"
    )
    return {
        "remote_push": "not_performed",
        "state": "deferred",
        "reason": reason,
        "availability": availability,
        "fallback": local_ci_fallback_package(remote_availability=availability),
    }


def local_ci_fallback_package(
    remote_availability: dict[str, object] | None = None,
) -> dict[str, object]:
    """Describe local CI fallback evidence without claiming hosted CI success."""
    availability = remote_availability or {
        "kind": "git_remote_availability",
        "remote": "origin",
        "state": "not_probed",
        "available": False,
        "blocking": False,
    }
    return {
        "kind": "local_ci_fallback",
        "evidence_class": "local_fallback",
        "boundary": "local-ci evidence; hosted CI status unclaimed",
        "hosted_ci_status_claimed": False,
        "remote_availability_state": str(availability.get("state") or "not_probed"),
        "command": ".config/ci/scripts/run-local-ci.sh",
        "owner_scripts": [
            ".config/ci/scripts/run-python-lint.sh",
            ".config/ci/scripts/run-config-lint.sh",
            ".config/ci/scripts/run-shell-lint.sh",
            ".config/ci/scripts/run-docstring-coverage.sh",
            ".config/ci/scripts/run-repository-hygiene.sh",
            ".config/ci/scripts/run-python-tests.sh",
        ],
    }


def land_next_actions(
    *,
    ok: bool,
    gaps: tuple[str, ...],
    current_head: str,
) -> tuple[str, ...]:
    """Derive the recommended next commands after a land attempt."""
    if ok:
        return ("ethos publish",)
    if "protected_root_mutation" in gaps:
        return ("ethos land --closeout --json",)
    if "candidate_base_stale" in gaps:
        return (f"ethos lane refresh-base --apply --authorize --expect-head {current_head} --json",)
    return ("ethos prove --json",)


def closeout_next_actions(
    *,
    ok: bool,
    gaps: tuple[str, ...],
    current_head: str,
) -> tuple[str, ...]:
    """Derive recommended next commands after accepted-root closeout."""
    if ok:
        return ("ethos lane retire-landed --branch <work-branch> --expect-head <work-lane-head>",)
    if "candidate_diverged_from_accepted" in gaps:
        return (
            "ethos lane candidate --refresh-from-accepted "
            f"--apply --authorize --expect-head {current_head} --json",
        )
    return ("ethos prove --json",)


def closeout_audit_root(repo: Path, decision: MutationDecision) -> Path:
    """Resolve the root to audit after closeout (candidate worktree when accepted)."""
    if not decision.ok:
        return repo
    candidate = workspace_status(repo).get("candidate", {})
    if not isinstance(candidate, dict):
        return repo
    candidate_path = str(candidate.get("worktree_path") or "")
    return Path(candidate_path) if candidate_path else repo


def repository_audit_after_admission(repo: Path, decision: MutationDecision) -> dict[str, object]:
    """Run the shape audit after admission, or skip when the mutation was blocked."""
    from ethos.domain.status import audit_for_root

    if not decision.ok:
        return {
            "ok": False,
            "state": "skipped",
            "reason": "mutation_admission_blocked",
            "required_gaps": [],
            "root": repo.as_posix(),
        }
    return audit_for_root(repo, openspec_mode="shape")


def local_submit_package(
    *,
    branch: str,
    submit_branch: str,
    remote_availability: dict[str, object] | None = None,
) -> dict[str, object]:
    """Plan the local submit-branch package (remote push deferred)."""
    return {
        "kind": "submit_branch_plan",
        "source_branch": branch,
        "submit_branch": submit_branch,
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "blocking": False,
        "remote_availability": remote_availability or {"state": "not_probed", "available": False},
        "local_ci_fallback": local_ci_fallback_package(
            remote_availability=remote_availability,
        ),
        "required_steps": [
            "land work lane to candidate role",
            "fast-forward accepted root from candidate role",
            "run local-ci fallback when remote publication is unavailable",
            "create configured submit branch when remote publication is available",
        ],
    }


def intake_projection_report(repo: Path) -> dict[str, object]:
    """Project the intake-ledger configuration state (a non-truth projection)."""
    config_path = repo / ".ethos" / "intake.toml"
    gaps: list[str] = []
    provider = "unconfigured"
    configured = False
    if config_path.exists():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            provider = "invalid"
            gaps.append("intake_config_invalid:.ethos/intake.toml")
        else:
            configured_provider = str(config.get("provider") or "").strip()
            if configured_provider:
                provider = configured_provider
                configured = True
            else:
                provider = "invalid"
                gaps.append("intake_provider_missing:.ethos/intake.toml")
    state = "configured" if configured else "invalid" if gaps else "unconfigured"
    return {
        "kind": "intake_projection",
        "state": state,
        "truth_boundary": "projection-evidence",
        "repository_truth": False,
        "provider": provider,
        "configured": configured,
        "expected_config": ".ethos/intake.toml",
        "adapters": ["backlog", "github", "gitlab"],
        "blocking": False,
        "required_gaps": gaps,
    }


def publication_readiness(
    *,
    branch: str,
    local_ok: bool,
    policy: BranchRolePolicy,
    remote_availability: dict[str, object] | None = None,
) -> dict[str, object]:
    """Assemble publication readiness with remote probe and local-ci fallback."""
    submit_branch = policy.submit_branch_for_source(branch)
    availability = remote_availability or {
        "kind": "git_remote_availability",
        "remote": "origin",
        "state": "not_probed",
        "available": False,
        "blocking": False,
        "required_gaps": [],
        "advisory_gaps": [],
    }
    remote_available = availability.get("available") is True
    next_actions = ["resolve local publish readiness gaps"]
    if local_ok and remote_available:
        next_actions = ["create configured submit branch when remote publication is available"]
    elif local_ok:
        next_actions = ["run .config/ci/scripts/run-local-ci.sh as local fallback evidence"]
    return {
        "mode": "local_readiness",
        "remote_push": "not_performed",
        "remote_state": "available" if remote_available else "deferred",
        "remote_availability": availability,
        "fallback_evidence": local_ci_fallback_package(remote_availability=availability),
        "submit_branch": submit_branch,
        "local_submit_package": local_submit_package(
            branch=branch,
            submit_branch=submit_branch,
            remote_availability=availability,
        ),
        "required_gaps": [] if local_ok else ["local_publish_readiness_blocked"],
        "next_actions": next_actions,
    }


def trust_closeout_package(
    *,
    workspace: dict[str, object],
    claims: dict[str, object],
) -> dict[str, object]:
    """Assess trust-claim closeout readiness (promotion + executed-proof evidence)."""
    closeout_support = workspace.get("closeout_support")
    closeout = closeout_support if isinstance(closeout_support, dict) else {}
    trust_claims = [
        claim
        for claim in cast("dict[str, object]", claims.get("claims", {})).values()
        if isinstance(claim, dict) and claim.get("trust_envelope")
    ]
    envelopes = cast(
        "list[dict[str, object]]",
        [
            cast("dict[str, object]", claim)["trust_envelope"]
            for claim in trust_claims
            if isinstance(claim.get("trust_envelope"), dict)
        ],
    )
    envelope_gaps = [
        gap
        for envelope in envelopes
        for gap in cast("list[object]", envelope.get("required_gaps", []))
        if isinstance(envelope, dict)
    ]
    promotion_ready = (
        bool(envelopes)
        and not envelope_gaps
        and all(
            isinstance(envelope.get("promotion"), dict)
            and cast("dict[str, object]", envelope["promotion"]).get("ready") is True
            for envelope in envelopes
        )
    )
    executed_proof_evidence = any(
        command_is_executed_proof(command)
        for envelope in envelopes
        if isinstance(envelope.get("evidence"), dict)
        for command in cast(
            "list[object]",
            cast("dict[str, object]", envelope["evidence"]).get("commands", []),
        )
    )
    gaps: list[str] = []
    if not claims.get("ok"):
        gaps.extend(str(gap) for gap in cast("list[object]", claims.get("required_gaps", [])))
    if not envelopes:
        gaps.append("trust_claim_missing")
    if not promotion_ready:
        gaps.append("promotion_readiness_missing")
    if not executed_proof_evidence:
        gaps.append("executed_proof_missing")
    if (
        workspace.get("role") == "work_lane"
        and closeout.get("supported") is True
        and closeout.get("claim_binding") != "bound"
    ):
        gaps.append(f"work_lane_claim_binding_missing:{workspace.get('branch')}")
    return {
        "kind": "trust_closeout",
        "claim_report_ok": bool(claims.get("ok")),
        "trust_claim_count": len(envelopes),
        "promotion_ready": promotion_ready,
        "executed_proof_evidence": executed_proof_evidence,
        "work_lane": {
            "branch": str(workspace.get("branch") or ""),
            "claim_id": str(closeout.get("claim_id") or ""),
            "claim_binding": str(closeout.get("claim_binding") or "unbound"),
        },
        "blocking": bool(gaps),
        "required_gaps": gaps,
    }


def acceptable_parity_product_heads(root: Path, adopter: str | None) -> tuple[str, ...]:
    """Product heads accepted as parity-evidence-current.

    A recorded product_head is current when nothing under PARITY_RELEVANT_PATHS changed
    between it and HEAD — commits that touched only parity-irrelevant paths do not stale
    the evidence. This removes the shared-evidence-file serialization bottleneck: a lane
    that changes no parity-relevant source need not re-touch the evidence file, and an
    unrelated commit no longer forces a parity re-run.
    """
    current_head = _gitio.current_tracked_head(root)
    if not current_head:
        return ()
    return _gitio.commits_equivalent_over_paths(
        root, current_head, relevant_paths=PARITY_RELEVANT_PATHS
    )


def acceptable_parity_target_heads(
    root: Path,
    target: Path | None,
    adopter: str | None,
) -> tuple[str, ...]:
    """Target heads accepted as parity-evidence-current for a shadow target.

    Same parity-relevant-tree currency as the product heads, evaluated in the target's
    own history — only meaningful when the target shares this repository's history.
    """
    if target is None:
        return ()
    current_head = _gitio.current_tracked_head(target)
    if not current_head:
        return ()
    if not _gitio.same_git_repository(root, target):
        return (current_head,)
    return _gitio.commits_equivalent_over_paths(
        target, current_head, relevant_paths=PARITY_RELEVANT_PATHS
    )
