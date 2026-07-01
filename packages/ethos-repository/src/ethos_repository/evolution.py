from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def _ledger_path(root: Path) -> Path:
    return root / "docs" / "governance" / "evolution-ledger.toml"


def _campaigns_root(root: Path) -> Path:
    return root / "evolution" / "campaigns"


def evolution_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    if not path.exists():
        return {"hypotheses": []}
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {"hypotheses": [], "parse_error": str(exc)}
    return {"hypotheses": payload.get("hypothesis", [])}


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
    if ledger.get("parse_error"):
        gaps.append("evolution_ledger_invalid_toml")
    active = [item for item in hypotheses if item.get("state") in {"active", "experimenting"}]
    return {
        "ok": not gaps,
        "active_count": len(active),
        "required_gaps": gaps,
        "ledger": ledger,
    }


def campaign_report(root: Path, *, campaign_id: str | None = None) -> dict[str, object]:
    campaigns, gaps = _campaign_manifests(root, campaign_id=campaign_id)
    active = [item for item in campaigns if item["state"] in {"active", "experimenting"}]
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
) -> tuple[list[dict[str, Any]], list[str]]:
    campaigns_root = _campaigns_root(root)
    if not campaigns_root.exists():
        return [], []
    manifests = sorted(campaigns_root.glob("*/campaign.toml"))
    campaigns: list[dict[str, Any]] = []
    gaps: list[str] = []
    for path in manifests:
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            gaps.append(f"campaign_manifest_invalid_toml:{path.parent.name}")
            campaigns.append(
                {
                    "id": path.parent.name,
                    "state": "invalid",
                    "owner": "",
                    "objective": "",
                    "claim_id": "",
                    "path": path.relative_to(root).as_posix(),
                    "steps": [],
                    "step_summary": _step_summary([]),
                    "required_gaps": [str(exc)],
                }
            )
            continue
        campaign = _campaign_payload(root, path, payload)
        if campaign_id and campaign["id"] != campaign_id:
            continue
        campaign_gaps = _campaign_required_gaps(root, campaign)
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
) -> dict[str, Any]:
    steps = [
        _step_payload(item, default_ordinal=index)
        for index, item in enumerate(payload.get("step", []), start=1)
    ]
    campaign = {
        "id": str(payload.get("id") or path.parent.name),
        "state": str(payload.get("state") or "active"),
        "owner": str(payload.get("owner") or ""),
        "objective": str(payload.get("objective") or ""),
        "claim_id": str(payload.get("claim_id") or ""),
        "path": path.relative_to(root).as_posix(),
        "steps": steps,
        "step_summary": _step_summary(steps),
        "lane_topology": _lane_topology(steps),
    }
    return campaign


def _step_payload(item: dict[str, Any], *, default_ordinal: int) -> dict[str, Any]:
    closeout = dict(item.get("closeout") or {})
    raw_ordinal = item.get("ordinal", default_ordinal)
    try:
        ordinal = int(raw_ordinal)
    except (TypeError, ValueError):
        ordinal = 0
    return {
        "id": str(item.get("id") or ""),
        "title": str(item.get("title") or ""),
        "state": str(item.get("state") or "planned"),
        "ordinal": ordinal,
        "depends_on": [str(value) for value in item.get("depends_on", [])],
        "openspec_change": str(item.get("openspec_change") or ""),
        "work_lane": str(item.get("work_lane") or ""),
        "claim_id": str(item.get("claim_id") or ""),
        "closeout": {
            "state": str(closeout.get("state") or "planned"),
            "accepted_head": str(closeout.get("accepted_head") or ""),
            "candidate_head": str(closeout.get("candidate_head") or ""),
            "evidence": [str(value) for value in closeout.get("evidence", [])],
        },
    }


def _lane_topology(steps: list[dict[str, Any]]) -> dict[str, Any]:
    edges = [
        {
            "from": dependency,
            "to": step["id"],
            "rule": "closeout_retired_before_activation",
        }
        for step in steps
        for dependency in step["depends_on"]
    ]
    active_steps = [
        step["id"] for step in steps if step["state"] in {"active", "in_progress", "landed"}
    ]
    next_planned_step = next((step["id"] for step in steps if step["state"] == "planned"), "")
    return {
        "kind": "openspec_lane_sequence",
        "mode": "strict_serial",
        "step_count": len(steps),
        "active_step": active_steps[0] if len(active_steps) == 1 else "",
        "active_steps": active_steps,
        "next_planned_step": next_planned_step,
        "edges": edges,
    }


def _step_summary(steps: list[dict[str, Any]]) -> dict[str, int]:
    closed_states = {"closed", "retired"}
    return {
        "total": len(steps),
        "planned": sum(1 for item in steps if item["state"] == "planned"),
        "active": sum(1 for item in steps if item["state"] in {"active", "in_progress"}),
        "closed": sum(
            1
            for item in steps
            if item["state"] in closed_states or item["closeout"]["state"] in closed_states
        ),
    }


def _campaign_required_gaps(root: Path, campaign: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for field in ("id", "state", "owner", "objective", "claim_id"):
        if not campaign[field]:
            gaps.append(f"campaign_{field}_missing:{campaign['id']}")
    steps = campaign["steps"]
    step_by_id = {step["id"]: step for step in steps if step["id"]}
    if len(step_by_id) != len([step for step in steps if step["id"]]):
        gaps.append(f"campaign_step_id_duplicate:{campaign['id']}")
    if len(campaign["lane_topology"]["active_steps"]) > 1:
        gaps.append(f"campaign_active_step_not_serial:{campaign['id']}")
    for index, step in enumerate(steps, start=1):
        step_id = step["id"] or "unnamed"
        for field in ("id", "title", "openspec_change", "work_lane", "claim_id"):
            if not step[field]:
                gaps.append(f"campaign_step_{field}_missing:{campaign['id']}:{step_id}")
        if step["ordinal"] != index:
            gaps.append(f"campaign_step_ordinal_invalid:{campaign['id']}:{step_id}")
        expected_dependency = [] if index == 1 else [steps[index - 2]["id"]]
        if step["depends_on"] != expected_dependency:
            gaps.append(f"campaign_step_dependency_not_serial:{campaign['id']}:{step_id}")
        for dependency in step["depends_on"]:
            dependency_step = step_by_id.get(dependency)
            if dependency_step is None:
                gaps.append(
                    f"campaign_step_dependency_missing:{campaign['id']}:{step_id}:{dependency}"
                )
                continue
            if step["state"] != "planned" and dependency_step["closeout"]["state"] != "retired":
                gaps.append(
                    f"campaign_step_dependency_not_retired:{campaign['id']}:{step_id}:{dependency}"
                )
        if step["state"] in {"closed", "retired"} and step["closeout"]["state"] not in {
            "closed",
            "retired",
        }:
            gaps.append(f"campaign_step_closeout_state_incomplete:{campaign['id']}:{step_id}")
        if step["closeout"]["state"] in {"closed", "retired"}:
            closeout = step["closeout"]
            if not closeout["accepted_head"] or not closeout["candidate_head"]:
                gaps.append(f"campaign_step_closeout_head_missing:{campaign['id']}:{step_id}")
            if not closeout["evidence"]:
                gaps.append(f"campaign_step_closeout_evidence_missing:{campaign['id']}:{step_id}")
        change = step["openspec_change"]
        needs_existing_carrier = (
            step["state"] != "planned" or step["closeout"]["state"] != "planned"
        )
        if needs_existing_carrier and change and not (
            root / "openspec" / "changes" / change
        ).exists() and not any((root / "openspec" / "changes" / "archive").glob(f"*-{change}")):
            gaps.append(f"campaign_step_openspec_missing:{campaign['id']}:{step_id}")
    return gaps


def evolution_candidates(root: Path) -> dict[str, object]:
    candidates = [
        {
            "id": "release-readiness-ratchet",
            "campaign": "ethos-release-hardening",
            "state": "ready",
            "owner": "ethos-maintainers",
            "claim": "Release readiness should keep gaining deterministic checks.",
            "challenge": "A clean report can still hide unmodeled ecosystem drift.",
            "transition": "observe -> shape",
            "proof_refs": ["ethos quality release-policy --json"],
            "review_refs": ["tests/unit/test_release_policy_and_attestation.py"],
            "decision_refs": ["docs/governance/release-governance.md"],
            "retirement_conditions": ["release policy emits no advisory gaps"],
        },
        {
            "id": "asset-quality-kernel",
            "campaign": "ethos-asset-quality-kernel",
            "state": "ready",
            "owner": "ethos-maintainers",
            "claim": "Quality and determinism require a first-class product package.",
            "challenge": "CLI quality commands without a semantic home create low-cohesion design.",
            "transition": "shape -> canonize",
            "proof_refs": ["ethos quality asset-policy --json"],
            "review_refs": ["tests/unit/test_quality_kernel.py"],
            "decision_refs": ["docs/architecture/package-ontology.md"],
            "retirement_conditions": [
                "ethos-quality owns quality semantics and repository consumes them"
            ],
        }
    ]
    return {"ok": True, "candidates": candidates}
