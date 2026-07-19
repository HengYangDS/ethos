from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.repository.adoption.practice.selection import selection_ref_gaps
from ethos.repository.adoption.practice.selection import selection_summary
from ethos.repository.policy.schema import validate_schema_instance
from ethos.repository.registry.docs.commands import KNOWN_ETHOS_COMMANDS
from ethos.repository.registry.docs.commands import best_ethos_command_key
from ethos_core.contracts.workflow import CampaignWorkflowDeclaration
from ethos_core.contracts.workflow import load_workflow_contract_declaration

if TYPE_CHECKING:
    from pathlib import Path


def _ledger_path(root: Path) -> Path:
    return root / "evolution" / "ledger.toml"


def _campaigns_root(root: Path) -> Path:
    return root / "evolution" / "campaigns"


def evolution_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    if not path.exists():
        return {"hypotheses": [], "entries": [], "path": path.as_posix()}
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {
            "hypotheses": [],
            "entries": [],
            "path": path.as_posix(),
            "parse_error": str(exc),
        }
    return {
        "hypotheses": payload.get("hypothesis", []),
        "entries": payload.get("entry", []),
        "practice_claims": payload.get("practice_claim", []),
        "candidate_sets": payload.get("candidate_set", []),
        "experiment_protocols": payload.get("experiment_protocol", []),
        "evaluation_records": payload.get("evaluation_record", []),
        "practice_changes": payload.get("practice_change", []),
        "types": payload.get("types", {}),
        "path": path.as_posix(),
    }


def evolution_report(root: Path) -> dict[str, object]:
    ledger = evolution_ledger(root)
    hypotheses = ledger["hypotheses"]
    gaps = [
        f"hypothesis_missing_field:{index}"
        for index, item in enumerate(hypotheses)
        if not item.get("id")
        or not item.get("campaign")
        or not item.get("state")
        or not item.get("owner")
        or not item.get("claim")
        or not item.get("challenge")
        or not item.get("transition")
        or not item.get("proof_refs")
        or not item.get("review_refs")
        or not item.get("decision_refs")
        or not item.get("retirement_conditions")
    ]
    if not hypotheses:
        gaps.append("evolution_hypotheses_missing")
    gaps.extend(_hypothesis_ref_gaps(root, hypotheses))
    gaps.extend(_entry_ref_gaps(root, ledger["entries"]))
    gaps.extend(selection_ref_gaps(root, ledger))
    if ledger.get("parse_error"):
        gaps.append("evolution_ledger_invalid_toml")
    active = [item for item in hypotheses if item.get("state") in {"active", "experimenting"}]
    selection_data = selection_summary(ledger)
    return {
        "ok": not gaps,
        "active_count": len(active),
        "required_gaps": gaps,
        "ledger": ledger,
        "selection": selection_data,
    }


def _hypothesis_ref_gaps(root: Path, hypotheses: list[dict[str, Any]]) -> list[str]:
    gaps: list[str] = []
    for item in hypotheses:
        hypothesis_id = str(item.get("id") or "unnamed")
        proof_refs = item.get("proof_refs", [])
        review_refs = item.get("review_refs", [])
        decision_refs = item.get("decision_refs", [])
        if proof_refs and not isinstance(proof_refs, list):
            gaps.append(f"hypothesis_proof_refs_invalid:{hypothesis_id}")
            proof_refs = []
        if review_refs and not isinstance(review_refs, list):
            gaps.append(f"hypothesis_review_refs_invalid:{hypothesis_id}")
            review_refs = []
        if decision_refs and not isinstance(decision_refs, list):
            gaps.append(f"hypothesis_decision_refs_invalid:{hypothesis_id}")
            decision_refs = []
        for ref in proof_refs:
            ref_text = str(ref)
            if not _proof_ref_resolves(root, ref_text):
                gaps.append(f"hypothesis_proof_ref_unresolved:{hypothesis_id}:{ref_text}")
        for ref in review_refs:
            ref_text = str(ref)
            if not _path_ref_exists(root, ref_text):
                gaps.append(f"hypothesis_review_ref_missing:{hypothesis_id}:{ref_text}")
        for ref in decision_refs:
            ref_text = str(ref)
            if not _path_ref_exists(root, ref_text):
                gaps.append(f"hypothesis_decision_ref_missing:{hypothesis_id}:{ref_text}")
    return gaps


def _entry_ref_gaps(root: Path, entries: list[dict[str, Any]]) -> list[str]:
    gaps: list[str] = []
    for item in entries:
        entry_id = str(item.get("id") or "unnamed")
        entry_type = str(item.get("type") or "")
        if entry_type == "campaign":
            continue
        evidence_refs = item.get("evidence_refs")
        decision_refs = item.get("decision_refs")
        if not evidence_refs:
            gaps.append(f"entry_evidence_refs_missing:{entry_id}")
        elif not isinstance(evidence_refs, list):
            gaps.append(f"entry_evidence_refs_invalid:{entry_id}")
        else:
            for ref in evidence_refs:
                ref_text = str(ref)
                if not _path_ref_exists(root, ref_text):
                    gaps.append(f"entry_evidence_ref_missing:{entry_id}:{ref_text}")
        if not decision_refs:
            gaps.append(f"entry_decision_refs_missing:{entry_id}")
        elif not isinstance(decision_refs, list):
            gaps.append(f"entry_decision_refs_invalid:{entry_id}")
        else:
            for ref in decision_refs:
                ref_text = str(ref)
                if not _path_ref_exists(root, ref_text):
                    gaps.append(f"entry_decision_ref_missing:{entry_id}:{ref_text}")
    return gaps


def _proof_ref_resolves(root: Path, ref: str) -> bool:
    if _path_like(ref):
        return _path_ref_exists(root, ref)
    if ref.startswith("ethos "):
        return _known_ethos_command_ref(ref)
    return False


def _known_ethos_command_ref(ref: str) -> bool:
    key = best_ethos_command_key(ref)
    return bool(key and (key in KNOWN_ETHOS_COMMANDS))


def _path_like(ref: str) -> bool:
    return "/" in ref or ref.endswith((".md", ".py", ".toml", ".json", ".yml", ".yaml"))


def _path_ref_exists(root: Path, ref: str) -> bool:
    if not ref or ref.startswith("/") or "://" in ref:
        return False
    path = root / ref
    return path.exists()


def campaign_report(root: Path, *, campaign_id: str | None = None) -> dict[str, object]:
    policy = campaign_policy(root)
    campaigns, gaps = _campaign_manifests(root, campaign_id=campaign_id, policy=policy)
    active = [item for item in campaigns if item["state"] in policy.campaign_active_states]
    return {
        "ok": not gaps,
        "campaign_count": len(campaigns),
        "active_count": len(active),
        "required_gaps": gaps,
        "campaigns": campaigns,
    }


def _campaign_manifests(
    root: Path,
    *,
    campaign_id: str | None,
    policy: CampaignWorkflowDeclaration | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    runtime = policy or campaign_policy(root)
    campaigns_root = _campaigns_root(root)
    if not campaigns_root.exists():
        return [], []
    manifests = sorted(campaigns_root.glob("*/campaign.toml"))
    campaigns: list[dict[str, Any]] = []
    gaps: list[str] = []
    for path in manifests:
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            gaps.append(f"campaign_manifest_invalid_toml:{path.parent.name}")
            continue
        manifest_id = str(payload.get("id") or path.parent.name)
        if campaign_id and manifest_id != campaign_id:
            continue
        validation = validate_schema_instance("campaign.schema.json", payload, root=root)
        validation_gaps = validation.get("required_gaps")
        schema_gaps = validation_gaps if isinstance(validation_gaps, list) else []
        campaign_gaps = [
            f"campaign_manifest_schema_invalid:{manifest_id}:{gap}" for gap in schema_gaps
        ]
        if validation.get("ok") is not True:
            gaps.extend(campaign_gaps)
            continue
        campaign = _campaign_payload(root, path, payload, policy=runtime)
        campaign_gaps.extend(_campaign_required_gaps(root, campaign))
        campaign["required_gaps"] = campaign_gaps
        gaps.extend(campaign_gaps)
        campaigns.append(campaign)
    if campaign_id and not campaigns:
        gaps.append(f"campaign_missing:{campaign_id}")
    return campaigns, gaps


def _campaign_payload(
    root: Path,
    path: Path,
    payload: dict[str, Any],
    *,
    policy: CampaignWorkflowDeclaration | None = None,
) -> dict[str, Any]:
    runtime = policy or campaign_policy(root)
    steps = [_step_payload(item) for item in _list_items(payload.get("step"))]
    publication = payload.get("publication")
    return {
        "id": str(payload["id"]),
        "state": str(payload["state"]),
        "owner": str(payload["owner"]),
        "objective": str(payload["objective"]),
        "claim_id": str(payload["claim_id"]),
        "publication": {
            "mode": str(publication.get("mode") or "") if isinstance(publication, dict) else ""
        },
        "path": path.relative_to(root).as_posix(),
        "steps": steps,
        "step_summary": _step_summary(steps, policy=runtime),
        "lane_topology": _lane_topology(steps, policy=runtime),
    }


def _step_payload(item: dict[str, Any]) -> dict[str, Any]:
    closeout = cast("dict[str, Any]", item["closeout"])
    return {
        "id": str(item["id"]),
        "title": str(item["title"]),
        "state": str(item["state"]),
        "ordinal": int(cast("int", item["ordinal"])),
        "depends_on": [str(value) for value in cast("list[object]", item["depends_on"])],
        "openspec_change": str(item["openspec_change"]),
        "work_lane": str(item["work_lane"]),
        "claim_id": str(item["claim_id"]),
        "closeout": {
            "state": str(closeout["state"]),
            "accepted_head": str(closeout["accepted_head"]),
            "candidate_head": str(closeout["candidate_head"]),
            "evidence": [str(value) for value in cast("list[object]", closeout["evidence"])],
        },
    }


def _lane_topology(
    steps: list[dict[str, Any]], *, policy: CampaignWorkflowDeclaration
) -> dict[str, Any]:
    edges = [
        {
            "from": dependency,
            "to": step["id"],
            "rule": policy.dependency_rule,
        }
        for step in steps
        for dependency in step["depends_on"]
    ]
    active_steps = [
        step["id"]
        for step in steps
        if step["state"] in (*policy.step_execution_states, *policy.step_archived_states)
    ]
    next_planned_step = next(
        (step["id"] for step in steps if step["state"] in policy.step_planned_states),
        "",
    )
    return {
        "kind": policy.topology_kind,
        "mode": policy.topology_mode,
        "step_count": len(steps),
        "active_step": active_steps[0] if len(active_steps) == 1 else "",
        "active_steps": active_steps,
        "next_planned_step": next_planned_step,
        "edges": edges,
    }


def _step_summary(
    steps: list[dict[str, Any]], *, policy: CampaignWorkflowDeclaration
) -> dict[str, int]:
    return {
        "total": len(steps),
        "planned": sum(1 for item in steps if item["state"] in policy.step_planned_states),
        "active": sum(
            1
            for item in steps
            if item["state"] in (*policy.step_execution_states, *policy.step_archived_states)
        ),
        "archive_ready": sum(1 for item in steps if item["state"] == "archive_ready"),
        "closed": sum(
            1
            for item in steps
            if item["state"] in policy.step_terminal_states
            or item["closeout"]["state"] in policy.closeout_terminal_states
        ),
    }


def _openspec_carrier_state(root: Path, change: str) -> str:
    """Classify one campaign carrier by its canonical OpenSpec home."""
    if not change:
        return "missing"
    changes_root = root / "openspec" / "changes"
    active = (changes_root / change).exists()
    archived = any((changes_root / "archive").glob(f"*-{change}"))
    if active and archived:
        return "ambiguous"
    if active:
        return "active"
    if archived:
        return "archived"
    return "missing"


def _campaign_required_gaps(root: Path, campaign: dict[str, Any]) -> list[str]:
    policy = campaign_policy(root)
    gaps: list[str] = []
    steps = campaign["steps"]
    step_by_id = {step["id"]: step for step in steps if step["id"]}
    gaps.extend(
        policy.evaluate(
            scope="campaign",
            facts={"campaign": campaign},
        )
    )
    for index, step in enumerate(steps, start=1):
        expected_dependency = [] if index == 1 else [steps[index - 2]["id"]]
        carrier_state = _openspec_carrier_state(root, step["openspec_change"])
        gaps.extend(
            policy.evaluate(
                scope="step",
                facts={
                    "campaign": campaign,
                    "step": step,
                    "position": index,
                    "expected_dependency": expected_dependency,
                    "carrier": {"state": carrier_state},
                },
            )
        )
        for dependency in step["depends_on"]:
            gaps.extend(
                policy.evaluate(
                    scope="dependency",
                    facts={
                        "campaign": campaign,
                        "step": step,
                        "dependency_id": dependency,
                        "dependency": step_by_id.get(dependency),
                    },
                )
            )
    return gaps


def _list_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def campaign_policy(root: Path) -> CampaignWorkflowDeclaration:
    policy = load_workflow_contract_declaration(root).campaign
    if policy is None:
        msg = "campaign workflow policy missing"
        raise ValueError(msg)
    return policy
