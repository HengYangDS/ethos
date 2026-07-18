from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.adoption.practice.selection import selection_ref_gaps
from ethos.repository.adoption.practice.selection import selection_summary
from ethos.repository.registry.docs.commands import KNOWN_ETHOS_COMMANDS
from ethos.repository.registry.docs.commands import best_ethos_command_key

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
    return {
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
        step["id"]
        for step in steps
        if step["state"] in {"active", "in_progress", "landed", "archive_ready"}
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
        "archive_ready": sum(1 for item in steps if item["state"] == "archive_ready"),
        "closed": sum(
            1
            for item in steps
            if item["state"] in closed_states or item["closeout"]["state"] in closed_states
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
    steps = campaign["steps"]
    gaps = _campaign_metadata_gaps(campaign, steps)
    step_by_id = {step["id"]: step for step in steps if step["id"]}
    for index, step in enumerate(steps, start=1):
        gaps.extend(_campaign_step_gaps(root, campaign["id"], steps, step_by_id, index, step))
    return gaps


def _campaign_metadata_gaps(campaign: dict[str, Any], steps: list[dict[str, Any]]) -> list[str]:
    gaps = [
        f"campaign_{field}_missing:{campaign['id']}"
        for field in ("id", "state", "owner", "objective", "claim_id")
        if not campaign[field]
    ]
    step_by_id = {step["id"]: step for step in steps if step["id"]}
    if len(step_by_id) != len([step for step in steps if step["id"]]):
        gaps.append(f"campaign_step_id_duplicate:{campaign['id']}")
    if len(campaign["lane_topology"]["active_steps"]) > 1:
        gaps.append(f"campaign_active_step_not_serial:{campaign['id']}")
    return gaps


def _campaign_step_gaps(
    root: Path,
    campaign_id: str,
    steps: list[dict[str, Any]],
    step_by_id: dict[str, dict[str, Any]],
    index: int,
    step: dict[str, Any],
) -> list[str]:
    step_id = step["id"] or "unnamed"
    gaps = _campaign_step_shape_gaps(campaign_id, steps, index, step, step_id)
    gaps.extend(_campaign_step_dependency_gaps(campaign_id, step, step_id, step_by_id))
    gaps.extend(_campaign_step_closeout_gaps(campaign_id, step, step_id))
    gaps.extend(_campaign_step_carrier_gaps(root, campaign_id, step, step_id))
    return gaps


def _campaign_step_shape_gaps(
    campaign_id: str,
    steps: list[dict[str, Any]],
    index: int,
    step: dict[str, Any],
    step_id: str,
) -> list[str]:
    gaps = [
        f"campaign_step_{field}_missing:{campaign_id}:{step_id}"
        for field in ("id", "title", "openspec_change", "work_lane", "claim_id")
        if not step[field]
    ]
    if step["ordinal"] != index:
        gaps.append(f"campaign_step_ordinal_invalid:{campaign_id}:{step_id}")
    expected_dependency = [] if index == 1 else [steps[index - 2]["id"]]
    if step["depends_on"] != expected_dependency:
        gaps.append(f"campaign_step_dependency_not_serial:{campaign_id}:{step_id}")
    return gaps


def _campaign_step_dependency_gaps(
    campaign_id: str,
    step: dict[str, Any],
    step_id: str,
    step_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    gaps: list[str] = []
    for dependency in step["depends_on"]:
        dependency_step = step_by_id.get(dependency)
        if dependency_step is None:
            gaps.append(f"campaign_step_dependency_missing:{campaign_id}:{step_id}:{dependency}")
        elif step["state"] != "planned" and dependency_step["closeout"]["state"] != "retired":
            gaps.append(
                f"campaign_step_dependency_not_retired:{campaign_id}:{step_id}:{dependency}"
            )
    return gaps


def _campaign_step_closeout_gaps(
    campaign_id: str,
    step: dict[str, Any],
    step_id: str,
) -> list[str]:
    terminal_step = step["state"] in {"closed", "retired"}
    terminal_closeout = step["closeout"]["state"] in {"closed", "retired"}
    gaps: list[str] = []
    if terminal_step and not terminal_closeout:
        gaps.append(f"campaign_step_closeout_state_incomplete:{campaign_id}:{step_id}")
    if terminal_closeout:
        closeout = step["closeout"]
        if not closeout["accepted_head"] or not closeout["candidate_head"]:
            gaps.append(f"campaign_step_closeout_head_missing:{campaign_id}:{step_id}")
        if not closeout["evidence"]:
            gaps.append(f"campaign_step_closeout_evidence_missing:{campaign_id}:{step_id}")
    if step["state"] in {"active", "in_progress", "landed"} and terminal_closeout:
        gaps.append(f"campaign_step_execution_closeout_terminal:{campaign_id}:{step_id}")
    if step["state"] == "archive_ready" and terminal_closeout:
        gaps.append(f"campaign_step_archive_ready_closeout_terminal:{campaign_id}:{step_id}")
    if terminal_closeout and not terminal_step:
        gaps.append(f"campaign_step_terminal_closeout_nonterminal:{campaign_id}:{step_id}")
    return gaps


def _campaign_step_carrier_gaps(
    root: Path,
    campaign_id: str,
    step: dict[str, Any],
    step_id: str,
) -> list[str]:
    change = step["openspec_change"]
    carrier_state = _openspec_carrier_state(root, change)
    execution_step = step["state"] in {"active", "in_progress", "landed"}
    archive_ready_step = step["state"] == "archive_ready"
    terminal_step = step["state"] in {"closed", "retired"}
    gaps: list[str] = []
    if carrier_state == "ambiguous":
        gaps.append(f"campaign_step_openspec_ambiguous:{campaign_id}:{step_id}")
    elif archive_ready_step and carrier_state != "archived":
        gaps.append(f"campaign_step_archive_ready_openspec_not_archived:{campaign_id}:{step_id}")
    elif execution_step and carrier_state == "archived":
        gaps.append(f"campaign_step_active_openspec_archived:{campaign_id}:{step_id}")
    elif terminal_step and carrier_state != "archived":
        gaps.append(f"campaign_step_terminal_openspec_not_archived:{campaign_id}:{step_id}")
    if (
        (step["state"] != "planned" or step["closeout"]["state"] != "planned")
        and change
        and carrier_state == "missing"
    ):
        gaps.append(f"campaign_step_openspec_missing:{campaign_id}:{step_id}")
    return gaps


def evolution_candidates(root: Path) -> dict[str, object]:
    """Return candidate mechanisms from the evolution ledger plus audit-signal fallbacks."""
    ledger = evolution_ledger(root)
    ledger_candidates: list[dict[str, Any]] = []
    for candidate_set in _list_items(ledger.get("candidate_sets")):
        for candidate in _list_items(candidate_set.get("candidates")):
            ledger_candidates.append(
                {
                    "id": str(candidate.get("id") or ""),
                    "candidate_set": str(candidate_set.get("id") or ""),
                    "campaign": str(candidate_set.get("question") or ""),
                    "state": str(candidate_set.get("state") or ""),
                    "owner": str(candidate_set.get("owner") or ""),
                    "claim": str(candidate.get("summary") or ""),
                    "challenge": str(candidate.get("risk") or ""),
                    "transition": str(candidate.get("authority_fit") or ""),
                    "proof_refs": [str(value) for value in candidate.get("evidence_refs", [])],
                    "review_refs": [],
                    "decision_refs": [
                        str(value) for value in candidate_set.get("decision_refs", [])
                    ],
                    "retirement_conditions": [str(candidate_set.get("retirement_policy") or "")],
                }
            )
    candidates = ledger_candidates + _audit_signal_candidates()
    return {
        "ok": True,
        "candidate_set_count": len(_list_items(ledger.get("candidate_sets"))),
        "candidates": candidates,
    }


def _audit_signal_candidates() -> list[dict[str, Any]]:
    return [
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
        },
    ]


def _list_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
