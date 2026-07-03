"""Land/publish-stage domain reducers — closeout, submit, intake, publication.

Pure reducers over primitives + adapter reports for the land→publish tail of the
loop. Imports flow downward (adapters/kernel), keeping the surface→domain layering
acyclic.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters import git as _gitio
from ethos_adapters.status import workspace_status
from ethos_contracts.branch_roles import load_branch_role_policy
from ethos_repository.claims import claims_report
from ethos_repository.evolution import campaign_report
from ethos_repository.evolution import evolution_report
from ethos_repository.parity import parity_gaps_report
from ethos_repository.parity import shadow_parity_report
from ethos_repository.release import release_policy_report

if TYPE_CHECKING:
    from ethos_adapters.mutation import MutationDecision
    from ethos_contracts.branch_roles import BranchRolePolicy


def command_is_executed_proof(command: object) -> bool:
    """True when a prove command carries the --execute flag (executed proof)."""
    text = str(command)
    return "prove" in text and "--execute" in text


def remote_publication_deferred() -> dict[str, object]:
    """Describe the deferred remote-publication state (no remote adapter yet)."""
    return {
        "remote_push": "not_performed",
        "state": "deferred",
        "reason": "remote publication adapter unavailable",
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
    if "candidate_base_stale" in gaps:
        return (f"ethos lane refresh-base --apply --authorize --expect-head {current_head} --json",)
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


def local_submit_package(*, branch: str, submit_branch: str) -> dict[str, object]:
    """Plan the local submit-branch package (remote push deferred)."""
    return {
        "kind": "submit_branch_plan",
        "source_branch": branch,
        "submit_branch": submit_branch,
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "blocking": False,
        "required_steps": [
            "land work lane to candidate role",
            "fast-forward accepted root from candidate role",
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
) -> dict[str, object]:
    """Assemble the local publication-readiness package (remote push deferred)."""
    submit_branch = policy.submit_branch_for_source(branch)
    return {
        "mode": "local_readiness",
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "submit_branch": submit_branch,
        "local_submit_package": local_submit_package(
            branch=branch,
            submit_branch=submit_branch,
        ),
        "required_gaps": [] if local_ok else ["local_publish_readiness_blocked"],
        "next_actions": (
            ["create configured submit branch when remote publication is available"]
            if local_ok
            else ["resolve local publish readiness gaps"]
        ),
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
    return {
        "kind": "closeout_bootstrap",
        "state": "blocked" if required_gaps else "ready",
        "accepted_root": repo.resolve().as_posix(),
        "audit_root": audit_root.resolve().as_posix(),
        "accepted_branch": policy.accepted_branch,
        "candidate_branch": policy.candidate_branch,
        "accepted_head": accepted_head,
        "candidate_head": str(candidate.get("head") or ""),
        "blocking": bool(required_gaps),
        "required_gaps": list(required_gaps),
        "command": command,
        "next_action": "run closeout with a current ETHOS runner against accepted_root",
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
        for claim in claims.get("claims", {}).values()
        if isinstance(claim, dict) and claim.get("trust_envelope")
    ]
    envelopes = [
        claim["trust_envelope"]
        for claim in trust_claims
        if isinstance(claim.get("trust_envelope"), dict)
    ]
    envelope_gaps = [
        gap
        for envelope in envelopes
        for gap in envelope.get("required_gaps", [])
        if isinstance(envelope, dict)
    ]
    promotion_ready = bool(envelopes) and not envelope_gaps and all(
        isinstance(envelope.get("promotion"), dict)
        and envelope["promotion"].get("ready") is True
        for envelope in envelopes
    )
    executed_proof_evidence = any(
        command_is_executed_proof(command)
        for envelope in envelopes
        if isinstance(envelope.get("evidence"), dict)
        for command in envelope["evidence"].get("commands", [])
    )
    gaps: list[str] = []
    if not claims.get("ok"):
        gaps.extend(str(gap) for gap in claims.get("required_gaps", []))
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
    """Compute product heads accepted as parity-evidence-current (head + parents)."""
    current_head = _gitio.current_tracked_head(root)
    if not current_head:
        return ()
    accepted = [current_head]
    evidence_path = Path("docs") / "evidence" / "parity" / f"{adopter or 'generic'}-shadow.json"
    last_change = _gitio.git_stdout(
        root, "log", "-1", "--format=%H", "--", evidence_path.as_posix()
    )
    if last_change == current_head:
        parents_line = _gitio.git_stdout(root, "rev-list", "--parents", "-n", "1", current_head)
        accepted.extend(parents_line.split()[1:])
    return tuple(dict.fromkeys(head for head in accepted if head))


def acceptable_parity_target_heads(
    root: Path,
    target: Path | None,
    adopter: str | None,
) -> tuple[str, ...]:
    """Compute target heads accepted as parity-evidence-current for a shadow target."""
    if target is None:
        return ()
    current_head = _gitio.current_tracked_head(target)
    if not current_head:
        return ()
    accepted = [current_head]
    if _gitio.same_git_repository(root, target):
        evidence_path = (
            Path("docs") / "evidence" / "parity" / f"{adopter or 'generic'}-shadow.json"
        )
        last_change = _gitio.git_stdout(
            root, "log", "-1", "--format=%H", "--", evidence_path.as_posix()
        )
        if last_change == current_head:
            parents_line = _gitio.git_stdout(
                target, "rev-list", "--parents", "-n", "1", current_head
            )
            accepted.extend(parents_line.split()[1:])
    return tuple(dict.fromkeys(head for head in accepted if head))


def campaign_closeout_report(
    *,
    repo: Path,
    adopter: str,
    target: Path,
) -> dict[str, object]:
    """Compose the full campaign-closeout report (local readiness + parity + trust)."""
    status_payload = workspace_status(repo)
    claim_report = claims_report(repo)
    intake_projection = intake_projection_report(repo)
    branch = str(status_payload["branch"])
    evolution = evolution_report(repo)
    campaign = campaign_report(repo)
    release = release_policy_report(repo)
    current_target_head = _gitio.current_tracked_head(target)
    current_product_head = _gitio.current_tracked_head(repo)
    acceptable_product_heads = acceptable_parity_product_heads(repo, adopter)
    acceptable_target_heads = acceptable_parity_target_heads(repo, target, adopter)
    parity = parity_gaps_report(
        adopter=adopter,
        root=repo,
        target=target,
        current_target_head=current_target_head,
        current_product_head=current_product_head,
        acceptable_product_heads=acceptable_product_heads,
        acceptable_target_heads=acceptable_target_heads,
    )
    shadow = shadow_parity_report(
        target=target,
        root=repo,
        adopter=adopter,
        current_target_head=current_target_head,
        current_product_head=current_product_head,
        acceptable_product_heads=acceptable_product_heads,
        acceptable_target_heads=acceptable_target_heads,
    )
    local_ready = bool(evolution["ok"]) and bool(release["ok"])
    publication = publication_readiness(
        branch=branch,
        local_ok=local_ready,
        policy=load_branch_role_policy(repo),
    )
    remote_publication = remote_publication_deferred()
    trust_closeout = trust_closeout_package(
        workspace=status_payload,
        claims=claim_report,
    )
    provenance = {
        "shadow_parity": shadow.get("provenance", {}),
        "closeout": {
            "mode": "local_only",
            "remote_state": remote_publication["state"],
        },
    }
    local_closeout = dict(status_payload["closeout_support"])
    local_closeout["kind"] = "local_closeout_plan"
    local_closeout["blocking"] = bool(local_closeout["required_gaps"])

    packages = {
        "local_closeout": local_closeout,
        "trust_closeout": trust_closeout,
        "intake_projection": intake_projection,
        "publication": publication,
        "release": {
            "kind": "release_policy",
            "ok": bool(release["ok"]),
            "version": release["version"],
            "required_gaps": list(release["required_gaps"]),
        },
        "parity": {
            "kind": "parity_backlog",
            "adopter": parity["adopter"],
            "pending_count": len(parity["pending_packages"]),
            "required_gaps": list(parity["required_gaps"]),
            "blocking": False,
        },
        "shadow_parity": shadow["execution_packages"][0],
        "campaign": {
            "kind": "campaign_closeout",
            "ok": bool(campaign["ok"]),
            "active_count": int(campaign["active_count"]),
            "campaign_count": int(campaign["campaign_count"]),
            "required_gaps": list(campaign["required_gaps"]),
            "campaigns": campaign["campaigns"],
        },
    }
    ok = local_ready and bool(campaign["ok"]) and not trust_closeout["required_gaps"]
    return {
        "ok": ok,
        "state": "local_ready" if ok else "gapped",
        "workspace": status_payload,
        "claims": claim_report,
        "intake_projection": intake_projection,
        "evolution": evolution,
        "campaigns": campaign,
        "release": release,
        "parity": parity,
        "shadow_parity": shadow,
        "publication": publication,
        "remote_publication": remote_publication,
        "provenance": provenance,
        "packages": packages,
    }
