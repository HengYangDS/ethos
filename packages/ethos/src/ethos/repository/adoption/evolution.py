"""Evolution ledger, campaign, and candidate read models."""

# ruff: noqa: E501 - the source-budget closeout keeps equivalent envelopes compact.

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

# fmt: off

_LEDGER_TABLES = (("hypotheses", "hypothesis"), ("entries", "entry"), ("practice_claims", "practice_claim"), ("candidate_sets", "candidate_set"), ("experiment_protocols", "experiment_protocol"), ("evaluation_records", "evaluation_record"), ("practice_changes", "practice_change"), ("types", "types"))
_HYPOTHESIS_FIELDS = ("id", "campaign", "state", "owner", "claim", "challenge", "transition", "proof_refs", "review_refs", "decision_refs", "retirement_conditions")
_CAMPAIGN_FIELDS = ("id", "state", "owner", "objective", "claim_id")
_STEP_FIELDS = ("id", "title", "openspec_change", "work_lane", "claim_id")
_CLOSED_STATES, _EXECUTION_STATES = {"closed", "retired"}, {"active", "in_progress", "landed"}


def _ledger_path(root: Path) -> Path:
    return root / "evolution" / "ledger.toml"


def _campaigns_root(root: Path) -> Path:
    return root / "evolution" / "campaigns"


def evolution_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    empty = {"hypotheses": [], "entries": [], "path": path.as_posix()}
    if not path.exists():
        return empty
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {**empty, "parse_error": str(exc)}
    defaults: dict[str, object] = {"types": {}}
    return {**{name: payload.get(table, defaults.get(name, [])) for name, table in _LEDGER_TABLES}, "path": path.as_posix()}


def evolution_report(root: Path) -> dict[str, object]:
    ledger = evolution_ledger(root)
    hypotheses = ledger["hypotheses"]
    gaps = [f"hypothesis_missing_field:{index}" for index, item in enumerate(hypotheses) if any(not item.get(field) for field in _HYPOTHESIS_FIELDS)]
    if not hypotheses:
        gaps.append("evolution_hypotheses_missing")
    gaps.extend(_hypothesis_ref_gaps(root, hypotheses))
    gaps.extend(_entry_ref_gaps(root, ledger["entries"]))
    gaps.extend(selection_ref_gaps(root, ledger))
    if ledger.get("parse_error"):
        gaps.append("evolution_ledger_invalid_toml")
    active = [item for item in hypotheses if item.get("state") in {"active", "experimenting"}]
    return {"ok": not gaps, "active_count": len(active), "required_gaps": gaps, "ledger": ledger, "selection": selection_summary(ledger)}


def _hypothesis_ref_gaps(root: Path, hypotheses: list[dict[str, Any]]) -> list[str]:
    gaps: list[str] = []
    specs = (("proof_refs", "proof_refs_invalid", "proof_ref_unresolved", _proof_ref_resolves), ("review_refs", "review_refs_invalid", "review_ref_missing", _path_ref_exists), ("decision_refs", "decision_refs_invalid", "decision_ref_missing", _path_ref_exists))
    for item in hypotheses:
        item_id = str(item.get("id") or "unnamed")
        refs_by_field = {}
        for field, invalid, _, _ in specs:
            refs = item.get(field, [])
            if refs and not isinstance(refs, list):
                gaps.append(f"hypothesis_{invalid}:{item_id}")
                refs = []
            refs_by_field[field] = refs
        for field, _, unresolved, resolves in specs:
            gaps.extend(f"hypothesis_{unresolved}:{item_id}:{ref}" for value in refs_by_field[field] if not resolves(root, ref := str(value)))
    return gaps


def _entry_ref_gaps(root: Path, entries: list[dict[str, Any]]) -> list[str]:
    gaps: list[str] = []
    for item in entries:
        if str(item.get("type") or "") == "campaign":
            continue
        item_id = str(item.get("id") or "unnamed")
        for field, kind in (("evidence_refs", "evidence"), ("decision_refs", "decision")):
            refs = item.get(field)
            if not refs:
                gaps.append(f"entry_{kind}_refs_missing:{item_id}")
            elif not isinstance(refs, list):
                gaps.append(f"entry_{kind}_refs_invalid:{item_id}")
            else:
                gaps.extend(f"entry_{kind}_ref_missing:{item_id}:{ref}" for value in refs if not _path_ref_exists(root, ref := str(value)))
    return gaps


def _proof_ref_resolves(root: Path, ref: str) -> bool:
    return (_path_like(ref) and _path_ref_exists(root, ref)) or (ref.startswith("ethos ") and _known_ethos_command_ref(ref))


def _known_ethos_command_ref(ref: str) -> bool:
    key = best_ethos_command_key(ref)
    return bool(key and key in KNOWN_ETHOS_COMMANDS)


def _path_like(ref: str) -> bool:
    return "/" in ref or ref.endswith((".md", ".py", ".toml", ".json", ".yml", ".yaml"))


def _path_ref_exists(root: Path, ref: str) -> bool:
    return bool(ref and not ref.startswith("/") and "://" not in ref and (root / ref).exists())


def campaign_report(root: Path, *, campaign_id: str | None = None) -> dict[str, object]:
    policy = campaign_policy(root)
    campaigns, gaps = _campaign_manifests(root, campaign_id=campaign_id, policy=policy)
    active = [item for item in campaigns if item["state"] in policy.campaign_active_states]
    return {"ok": not gaps, "campaign_count": len(campaigns), "active_count": len(active), "required_gaps": gaps, "campaigns": campaigns}


def _campaign_manifests(root: Path, *, campaign_id: str | None, policy: CampaignWorkflowDeclaration | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    runtime, campaigns_root = policy or campaign_policy(root), _campaigns_root(root)
    if not campaigns_root.exists():
        return [], []
    campaigns: list[dict[str, Any]] = []
    gaps: list[str] = []
    for path in sorted(campaigns_root.glob("*/campaign.toml")):
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            gaps.append(f"campaign_manifest_invalid_toml:{path.parent.name}")
            continue
        manifest_id = str(payload.get("id") or path.parent.name)
        if campaign_id and manifest_id != campaign_id:
            continue
        validation = validate_schema_instance("campaign.schema.json", payload, root=root)
        raw_schema_gaps = validation.get("required_gaps")
        schema_gaps = raw_schema_gaps if isinstance(raw_schema_gaps, list) else []
        campaign_gaps = [f"campaign_manifest_schema_invalid:{manifest_id}:{gap}" for gap in schema_gaps]
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


def _campaign_payload(root: Path, path: Path, payload: dict[str, Any], *, policy: CampaignWorkflowDeclaration | None = None) -> dict[str, Any]:
    runtime = policy or campaign_policy(root)
    steps = [_step_payload(item) for item in _list_items(payload.get("step"))]
    publication = payload.get("publication")
    return {"id": str(payload["id"]), "state": str(payload["state"]), "owner": str(payload["owner"]), "objective": str(payload["objective"]), "claim_id": str(payload["claim_id"]), "publication": {"mode": str(publication.get("mode") or "") if isinstance(publication, dict) else ""}, "path": path.relative_to(root).as_posix(), "steps": steps, "step_summary": _step_summary(steps, policy=runtime), "lane_topology": _lane_topology(steps, policy=runtime)}


def _step_payload(item: dict[str, Any], *, default_ordinal: int | None = None) -> dict[str, Any]:
    """Project a schema-admitted step while retaining the legacy helper fallback."""
    closeout = dict(item.get("closeout") or {})
    try:
        ordinal = int(cast("int | str", item.get("ordinal", default_ordinal or 0)))
    except (TypeError, ValueError):
        ordinal = 0
    return {**{field: str(item.get(field) or default) for field, default in (("id", ""), ("title", ""), ("state", "planned"))}, "ordinal": ordinal, "depends_on": [str(value) for value in item.get("depends_on", [])], **{field: str(item.get(field) or "") for field in ("openspec_change", "work_lane", "claim_id")}, "closeout": {**{field: str(closeout.get(field) or default) for field, default in (("state", "planned"), ("accepted_head", ""), ("candidate_head", ""))}, "evidence": [str(value) for value in closeout.get("evidence", [])]}}


def _lane_topology(steps: list[dict[str, Any]], *, policy: CampaignWorkflowDeclaration | None = None) -> dict[str, Any]:
    active_states = set(policy.step_execution_states) | set(policy.step_archived_states) if policy else _EXECUTION_STATES | {"archive_ready"}
    planned_states = set(policy.step_planned_states) if policy else {"planned"}
    active = [step["id"] for step in steps if step["state"] in active_states]
    return {"kind": policy.topology_kind if policy else "openspec_lane_sequence", "mode": policy.topology_mode if policy else "strict_serial", "step_count": len(steps), "active_step": active[0] if len(active) == 1 else "", "active_steps": active, "next_planned_step": next((step["id"] for step in steps if step["state"] in planned_states), ""), "edges": [{"from": dependency, "to": step["id"], "rule": policy.dependency_rule if policy else "closeout_retired_before_activation"} for step in steps for dependency in step["depends_on"]]}


def _step_summary(steps: list[dict[str, Any]], *, policy: CampaignWorkflowDeclaration | None = None) -> dict[str, int]:
    planned = set(policy.step_planned_states) if policy else {"planned"}
    active = set(policy.step_execution_states) | set(policy.step_archived_states) if policy else {"active", "in_progress"}
    terminal, closeout_terminal = (set(policy.step_terminal_states), set(policy.closeout_terminal_states)) if policy else (_CLOSED_STATES, _CLOSED_STATES)
    return {"total": len(steps), "planned": sum(item["state"] in planned for item in steps), "active": sum(item["state"] in active for item in steps), "archive_ready": sum(item["state"] == "archive_ready" for item in steps), "closed": sum(item["state"] in terminal or item["closeout"]["state"] in closeout_terminal for item in steps)}


def _openspec_carrier_state(root: Path, change: str) -> str:
    """Classify one campaign carrier by its canonical OpenSpec home."""
    if not change:
        return "missing"
    changes_root = root / "openspec" / "changes"
    active = (changes_root / change).exists()
    archived = any((changes_root / "archive").glob(f"*-{change}"))
    return "ambiguous" if active and archived else "active" if active else "archived" if archived else "missing"


def _campaign_required_gaps(root: Path, campaign: dict[str, Any]) -> list[str]:
    policy, steps = campaign_policy(root), campaign["steps"]
    gaps = policy.evaluate("campaign", facts={"campaign": campaign})
    step_by_id = {step["id"]: step for step in steps if step["id"]}
    shape_prefixes = ("campaign_step_ordinal_invalid:", "campaign_step_dependency_not_serial:")
    for index, step in enumerate(steps, start=1):
        expected = [] if index == 1 else [steps[index - 2]["id"]]
        facts = {"campaign": campaign, "step": step, "position": index, "expected_dependency": expected, "carrier": {"state": _openspec_carrier_state(root, step["openspec_change"])}}
        step_gaps = policy.evaluate("step", facts=facts)
        gaps.extend(gap for gap in step_gaps if gap.startswith(shape_prefixes))
        for dependency in step["depends_on"]:
            gaps.extend(policy.evaluate("dependency", facts={"campaign": campaign, "step": step, "dependency_id": dependency, "dependency": step_by_id.get(dependency)}))
        gaps.extend(gap for gap in step_gaps if not gap.startswith(shape_prefixes))
    return gaps


def _campaign_step_gaps(root: Path, campaign_id: str, steps: list[dict[str, Any]], step_by_id: dict[str, dict[str, Any]], index: int, step: dict[str, Any]) -> list[str]:  # noqa: PLR0912, PLR0913, RUF100 - retained helper compatibility
    step_id = step["id"] or "unnamed"
    gaps = [f"campaign_step_{field}_missing:{campaign_id}:{step_id}" for field in _STEP_FIELDS if not step[field]]
    if step["ordinal"] != index:
        gaps.append(f"campaign_step_ordinal_invalid:{campaign_id}:{step_id}")
    if step["depends_on"] != ([] if index == 1 else [steps[index - 2]["id"]]):
        gaps.append(f"campaign_step_dependency_not_serial:{campaign_id}:{step_id}")
    for dependency in step["depends_on"]:
        dependency_step = step_by_id.get(dependency)
        if dependency_step is None:
            gaps.append(f"campaign_step_dependency_missing:{campaign_id}:{step_id}:{dependency}")
        elif step["state"] != "planned" and dependency_step["closeout"]["state"] != "retired":
            gaps.append(f"campaign_step_dependency_not_retired:{campaign_id}:{step_id}:{dependency}")
    closeout = step["closeout"]
    terminal_step, terminal_closeout = step["state"] in _CLOSED_STATES, closeout["state"] in _CLOSED_STATES
    if terminal_step and not terminal_closeout:
        gaps.append(f"campaign_step_closeout_state_incomplete:{campaign_id}:{step_id}")
    if terminal_closeout:
        if not closeout["accepted_head"] or not closeout["candidate_head"]:
            gaps.append(f"campaign_step_closeout_head_missing:{campaign_id}:{step_id}")
        if not closeout["evidence"]:
            gaps.append(f"campaign_step_closeout_evidence_missing:{campaign_id}:{step_id}")
    for condition, gap in ((step["state"] in _EXECUTION_STATES and terminal_closeout, "execution_closeout_terminal"), (step["state"] == "archive_ready" and terminal_closeout, "archive_ready_closeout_terminal"), (terminal_closeout and not terminal_step, "terminal_closeout_nonterminal")):
        if condition:
            gaps.append(f"campaign_step_{gap}:{campaign_id}:{step_id}")
    carrier = _openspec_carrier_state(root, step["openspec_change"])
    carrier_gap = "openspec_ambiguous" if carrier == "ambiguous" else "archive_ready_openspec_not_archived" if step["state"] == "archive_ready" and carrier != "archived" else "active_openspec_archived" if step["state"] in _EXECUTION_STATES and carrier == "archived" else "terminal_openspec_not_archived" if terminal_step and carrier != "archived" else ""
    if carrier_gap:
        gaps.append(f"campaign_step_{carrier_gap}:{campaign_id}:{step_id}")
    if (step["state"] != "planned" or closeout["state"] != "planned") and step["openspec_change"] and carrier == "missing":
        gaps.append(f"campaign_step_openspec_missing:{campaign_id}:{step_id}")
    return gaps


def evolution_candidates(root: Path) -> dict[str, object]:
    """Return candidate mechanisms from the evolution ledger plus audit-signal fallbacks."""
    ledger = evolution_ledger(root)
    candidate_sets = _list_items(ledger.get("candidate_sets"))
    candidates = []
    for candidate_set in candidate_sets:
        for candidate in _list_items(candidate_set.get("candidates")):
            candidates.append({"id": str(candidate.get("id") or ""), "candidate_set": str(candidate_set.get("id") or ""), "campaign": str(candidate_set.get("question") or ""), "state": str(candidate_set.get("state") or ""), "owner": str(candidate_set.get("owner") or ""), "claim": str(candidate.get("summary") or ""), "challenge": str(candidate.get("risk") or ""), "transition": str(candidate.get("authority_fit") or ""), "proof_refs": [str(value) for value in candidate.get("evidence_refs", [])], "review_refs": [], "decision_refs": [str(value) for value in candidate_set.get("decision_refs", [])], "retirement_conditions": [str(candidate_set.get("retirement_policy") or "")]})
    candidates.extend(_audit_signal_candidates())
    return {"ok": True, "candidate_set_count": len(candidate_sets), "candidates": candidates}


def _audit_signal_candidates() -> list[dict[str, Any]]:
    return [
        {"id": "release-readiness-ratchet", "campaign": "ethos-release-hardening", "state": "ready", "owner": "ethos-maintainers", "claim": "Release readiness should keep gaining deterministic checks.", "challenge": "A clean report can still hide unmodeled ecosystem drift.", "transition": "observe -> shape", "proof_refs": ["ethos quality release-policy --json"], "review_refs": ["tests/unit/test_release_policy_and_attestation.py"], "decision_refs": ["docs/governance/release-governance.md"], "retirement_conditions": ["release policy emits no advisory gaps"]},
        {"id": "asset-quality-kernel", "campaign": "ethos-asset-quality-kernel", "state": "ready", "owner": "ethos-maintainers", "claim": "Quality and determinism require a first-class product package.", "challenge": "CLI quality commands without a semantic home create low-cohesion design.", "transition": "shape -> canonize", "proof_refs": ["ethos quality asset-policy --json"], "review_refs": ["tests/unit/test_quality_kernel.py"], "decision_refs": ["docs/architecture/package-ontology.md"], "retirement_conditions": ["ethos-quality owns quality semantics and repository consumes them"]},
    ]


def _list_items(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def campaign_policy(root: Path) -> CampaignWorkflowDeclaration:
    policy = load_workflow_contract_declaration(root).campaign
    if policy is None:
        raise ValueError("campaign workflow policy missing")
    return policy
