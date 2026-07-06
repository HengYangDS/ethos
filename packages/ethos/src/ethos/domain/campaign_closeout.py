from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo import git as _gitio
from ethos.adapters.repo.status import workspace_status
from ethos.domain.land_support import acceptable_parity_product_heads
from ethos.domain.land_support import acceptable_parity_target_heads
from ethos.domain.land_support import intake_projection_report
from ethos.domain.land_support import publication_readiness
from ethos.domain.land_support import remote_publication_deferred
from ethos.domain.land_support import trust_closeout_package
from ethos.repository.adoption.evolution import campaign_report
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.parity import parity_gaps_report
from ethos.repository.evidence.parity import shadow_parity_report
from ethos.repository.release.core import release_policy_report
from ethos_core.contracts.branch_roles import load_branch_role_policy

if TYPE_CHECKING:
    from pathlib import Path


def campaign_closeout_report(
    *,
    repo: Path,
    adopter: str,
    target: Path,
) -> dict[str, object]:
    """Compose the full campaign-closeout report (local readiness + parity + trust)."""
    status_payload = workspace_status(repo)
    claim_report = claims_report(repo, current_head=_gitio.current_tracked_head(repo))
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
    local_closeout = dict(cast("dict[str, object]", status_payload["closeout_support"]))
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
            "pending_count": len(cast("list[object]", parity["pending_packages"])),
            "required_gaps": list(cast("list[object]", parity["required_gaps"])),
            "blocking": False,
        },
        "shadow_parity": cast("list[object]", shadow["execution_packages"])[0],
        "campaign": {
            "kind": "campaign_closeout",
            "ok": bool(campaign["ok"]),
            "active_count": int(cast("int", campaign["active_count"])),
            "campaign_count": int(cast("int", campaign["campaign_count"])),
            "required_gaps": list(cast("list[object]", campaign["required_gaps"])),
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
