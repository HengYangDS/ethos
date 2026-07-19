from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git_adapter
from ethos.adapters.repo.status.core import workspace_status
from ethos.domain.land.intake.core import intake_projection_report
from ethos.domain.land.parity.core import acceptable_parity_product_heads
from ethos.domain.land.parity.core import acceptable_parity_target_heads
from ethos.domain.land.publication import local_ci_fallback_package
from ethos.domain.land.publication import publication_readiness
from ethos.domain.land.publication import remote_publication_deferred
from ethos.domain.land.trust.core import trust_closeout_package
from ethos.domain.source_budget.core import source_budget_report
from ethos.repository.adoption.evolution import campaign_policy
from ethos.repository.adoption.evolution import campaign_report
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.context import is_product_root
from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.parity.core import parity_gaps_report
from ethos.repository.evidence.parity.core import shadow_parity_report
from ethos.repository.release.core import release_policy_report
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.policy.cel import evaluate_cel_gap_groups
from ethos_core.contracts.policy.cel import evaluate_cel_value

if TYPE_CHECKING:
    from pathlib import Path


def campaign_closeout_report(
    *,
    repo: Path,
    adopter: str,
    target: Path,
    campaign_id: str | None = None,
) -> dict[str, object]:
    """Compose the full campaign-closeout report (local readiness + parity + trust)."""
    status_payload = workspace_status(repo)
    claim_report = claims_report(
        repo,
        current_head=git_adapter.current_tracked_head(repo),
        adopter_mode=not is_product_root(repo),
    )
    intake_projection = intake_projection_report(repo)
    branch = str(status_payload["branch"])
    evolution = evolution_report(repo)
    campaign = campaign_report(repo, campaign_id=campaign_id)
    repository_campaign = campaign_report(repo)
    campaign_publication = campaign_publication_report(repo, campaigns=repository_campaign)
    campaign["publication"] = campaign_publication
    release = release_policy_report(repo)
    current_target_head = git_adapter.current_tracked_head(target)
    current_product_head = git_adapter.current_tracked_head(repo)
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
    local_ci_fallback = local_ci_fallback_package(
        root=repo,
        current_head=current_product_head,
    )
    publication = publication_readiness(
        branch=branch,
        local_ok=local_ready,
        policy=load_branch_role_policy(repo),
        local_ci_fallback=local_ci_fallback,
    )
    remote_publication = remote_publication_deferred(root=repo)
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
            "requested_campaign": campaign_id or "",
            "ok": bool(campaign["ok"]),
            "active_count": int(cast("int", campaign["active_count"])),
            "campaign_count": int(cast("int", campaign["campaign_count"])),
            "required_gaps": list(cast("list[object]", campaign["required_gaps"])),
            "campaigns": campaign["campaigns"],
            "publication": campaign_publication,
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
        "requested_campaign": campaign_id or "",
    }


def campaign_publication_report(
    repo: Path,
    *,
    campaigns: dict[str, object] | None = None,
) -> dict[str, object]:
    """Project whether declared campaigns permit the terminal remote publication."""
    report = campaigns or campaign_report(repo)
    policy = campaign_policy(repo)
    campaign_items = cast("list[dict[str, object]]", report["campaigns"])
    terminal_campaigns = [
        item
        for item in campaign_items
        if cast("dict[str, object]", item["publication"])["mode"]
        == policy.publication_terminal_mode
    ]

    budget = source_budget_report(repo)
    policy_facts = policy.model_dump(
        mode="json",
        exclude={"rules", "publication", "publication_projection"},
    )
    facts: dict[str, object] = {
        "report": report,
        "campaigns": terminal_campaigns,
        "budget": budget,
    }
    facts["required_gaps"] = [
        *policy.evaluate("publication", facts=facts),
        *evaluate_cel_gap_groups(
            policy.publication.gap_groups,
            facts=facts,
            policy=policy_facts,
        ),
    ]
    return cast(
        "dict[str, object]",
        evaluate_cel_value(
            policy.publication_projection,
            facts=facts,
            policy=policy_facts,
            rule={},
        ),
    )
