from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos_core.normalization.core import string_list

if TYPE_CHECKING:
    from pathlib import Path

_ALLOWED_COMMITMENT_EFFECTS = {
    "create_commitment",
    "compose_commitment",
    "refine_commitment",
    "replace_commitment",
    "remove_commitment",
    "reject_commitment",
}
_PRACTICE_CHANGE_EFFECTS = {
    "introduce": "create_commitment",
    "compose": "compose_commitment",
    "refine": "refine_commitment",
    "supersede": "replace_commitment",
    "retire": "remove_commitment",
    "reject": "reject_commitment",
}
_MIN_CANDIDATE_COUNT = 2


def selection_ref_gaps(root: Path, ledger: dict[str, Any]) -> list[str]:
    """Return reference and integrity gaps for practice-claim selection records."""
    context = _selection_context(ledger)
    gaps: list[str] = []
    gaps.extend(_practice_claims_gaps(root, context))
    gaps.extend(_candidate_sets_gaps(root, context))
    gaps.extend(_experiment_protocols_gaps(root, context))
    gaps.extend(_evaluation_records_gaps(root, context))
    gaps.extend(_practice_changes_gaps(root, context))
    return gaps


def selection_summary(ledger: dict[str, Any]) -> dict[str, Any]:
    practice_claims = _list_items(ledger.get("practice_claims"))
    candidate_sets = _list_items(ledger.get("candidate_sets"))
    experiments = _list_items(ledger.get("experiment_protocols"))
    evaluations = _list_items(ledger.get("evaluation_records"))
    practice_changes = _list_items(ledger.get("practice_changes"))
    selected_candidates = [
        str(item.get("selected_candidate"))
        for item in evaluations
        if item.get("selected_candidate")
    ]
    return {
        "practice_claim_count": len(practice_claims),
        "candidate_set_count": len(candidate_sets),
        "experiment_protocol_count": len(experiments),
        "evaluation_record_count": len(evaluations),
        "practice_change_count": len(practice_changes),
        "practice_claims": [
            {
                "id": str(item.get("id") or ""),
                "state": str(item.get("state") or ""),
                "subject": str(item.get("subject") or ""),
                "candidate_set": str(item.get("candidate_set") or ""),
                "evaluation_record": str(item.get("evaluation_record") or ""),
                "commitment_effect": str(item.get("commitment_effect") or ""),
            }
            for item in practice_claims
        ],
        "selected_candidates": selected_candidates,
        "supports_multi_candidate_selection": any(
            len(_list_items(item.get("candidates"))) >= _MIN_CANDIDATE_COUNT
            for item in candidate_sets
        ),
        "supports_practice_lifecycle": bool(practice_changes),
        "practice_change_kinds": sorted(
            {str(item.get("change_kind")) for item in practice_changes if item.get("change_kind")}
        ),
        "commitment_effects": sorted(
            {
                str(item.get("commitment_effect"))
                for item in practice_claims
                if item.get("commitment_effect")
            }
        ),
    }


def _selection_context(ledger: dict[str, Any]) -> dict[str, Any]:
    candidate_sets = _list_items(ledger.get("candidate_sets"))
    experiment_protocols = _list_items(ledger.get("experiment_protocols"))
    evaluation_records = _list_items(ledger.get("evaluation_records"))
    practice_changes = _list_items(ledger.get("practice_changes"))
    return {
        "practice_claims": _list_items(ledger.get("practice_claims")),
        "candidate_sets": candidate_sets,
        "experiment_protocols": experiment_protocols,
        "evaluation_records": evaluation_records,
        "practice_changes": practice_changes,
        "hypothesis_ids": _ids(_list_items(ledger.get("hypotheses"))),
        "candidate_set_ids": _ids(candidate_sets),
        "experiment_ids": _ids(experiment_protocols),
        "evaluation_ids": _ids(evaluation_records),
        "practice_change_ids": _ids(practice_changes),
    }


def _practice_claims_gaps(root: Path, context: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for item in _list_items(context.get("practice_claims")):
        item_id = _item_id(item)
        gaps.extend(
            _required_string_gaps(
                item,
                item_id,
                "practice_claim",
                (
                    "owner",
                    "subject",
                    "question",
                    "claim",
                    "boundary",
                    "incumbent_relation",
                ),
            )
        )
        gaps.extend(_required_list_gaps(item, item_id, "practice_claim", ("falsifiers",)))
        effect = str(item.get("commitment_effect") or "")
        if not effect:
            gaps.append(f"practice_claim_commitment_effect_missing:{item_id}")
        elif effect not in _ALLOWED_COMMITMENT_EFFECTS:
            gaps.append(f"practice_claim_commitment_effect_invalid:{item_id}:{effect}")
        gaps.extend(_practice_claim_link_gaps(item, item_id, context))
        gaps.extend(
            _path_refs_gaps(
                root, item_id, "practice_claim_commitment", item.get("commitment_targets")
            )
        )
        gaps.extend(
            _path_refs_gaps(root, item_id, "practice_claim_evidence", item.get("evidence_refs"))
        )
        gaps.extend(
            _path_refs_gaps(root, item_id, "practice_claim_decision", item.get("decision_refs"))
        )
    return gaps


def _practice_claim_link_gaps(
    item: dict[str, Any], item_id: str, context: dict[str, Any]
) -> list[str]:
    gaps: list[str] = []
    gaps.extend(
        _linked_id_gap(
            item, item_id, "candidate_set", context["candidate_set_ids"], "practice_claim"
        )
    )
    gaps.extend(
        _linked_id_gap(
            item, item_id, "experiment_protocol", context["experiment_ids"], "practice_claim"
        )
    )
    gaps.extend(
        _linked_id_gap(
            item, item_id, "evaluation_record", context["evaluation_ids"], "practice_claim"
        )
    )
    practice_change_refs = string_list(item.get("practice_changes"), drop_empty=True)
    if not practice_change_refs:
        gaps.append(f"practice_claim_practice_changes_missing:{item_id}")
    gaps.extend(
        f"practice_claim_practice_change_missing:{item_id}:{ref}"
        for ref in practice_change_refs
        if ref not in context["practice_change_ids"]
    )
    return gaps


def _candidate_sets_gaps(root: Path, context: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for item in _list_items(context.get("candidate_sets")):
        item_id = _item_id(item)
        candidates = _list_items(item.get("candidates"))
        if len(candidates) < _MIN_CANDIDATE_COUNT:
            gaps.append(f"candidate_set_too_small:{item_id}")
        if item.get("selection_policy") != "evidence_weighted_candidate_comparison":
            gaps.append(f"candidate_set_selection_policy_invalid:{item_id}")
        gaps.extend(
            _path_refs_gaps(root, item_id, "candidate_set_decision", item.get("decision_refs"))
        )
        gaps.extend(_candidate_items_gaps(root, item_id, candidates, context["hypothesis_ids"]))
    return gaps


def _candidate_items_gaps(
    root: Path, candidate_set_id: str, candidates: list[dict[str, Any]], hypotheses: set[str]
) -> list[str]:
    gaps: list[str] = []
    for candidate in candidates:
        candidate_id = _item_id(candidate)
        hypothesis_ref = str(candidate.get("hypothesis_ref") or "")
        if hypothesis_ref and hypothesis_ref not in hypotheses:
            gaps.append(
                f"candidate_hypothesis_ref_missing:{candidate_set_id}:{candidate_id}:"
                f"{hypothesis_ref}"
            )
        gaps.extend(
            _path_refs_gaps(
                root,
                f"{candidate_set_id}:{candidate_id}",
                "candidate_evidence",
                candidate.get("evidence_refs"),
            )
        )
    return gaps


def _experiment_protocols_gaps(root: Path, context: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for item in _list_items(context.get("experiment_protocols")):
        item_id = _item_id(item)
        gaps.extend(
            _linked_id_gap(
                item, item_id, "candidate_set", context["candidate_set_ids"], "experiment"
            )
        )
        gaps.extend(_hypothesis_link_gaps(item, item_id, context["hypothesis_ids"]))
        gaps.extend(
            _required_list_gaps(
                item,
                item_id,
                "experiment",
                ("variables", "controls", "metrics", "stop_conditions", "failure_conditions"),
            )
        )
        gaps.extend(
            _path_refs_gaps(root, item_id, "experiment_evidence", item.get("evidence_refs"))
        )
    return gaps


def _evaluation_records_gaps(root: Path, context: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for item in _list_items(context.get("evaluation_records")):
        item_id = _item_id(item)
        gaps.extend(
            _linked_id_gap(
                item, item_id, "candidate_set", context["candidate_set_ids"], "evaluation"
            )
        )
        gaps.extend(
            _linked_id_gap(
                item, item_id, "experiment_protocol", context["experiment_ids"], "evaluation"
            )
        )
        gaps.extend(_evaluation_selection_gaps(item, item_id))
        gaps.extend(
            _path_refs_gaps(root, item_id, "evaluation_evidence", item.get("evidence_refs"))
        )
        gaps.extend(
            _path_refs_gaps(root, item_id, "evaluation_decision", item.get("decision_refs"))
        )
    return gaps


def _evaluation_selection_gaps(item: dict[str, Any], item_id: str) -> list[str]:
    gaps: list[str] = []
    selected = str(item.get("selected_candidate") or "")
    rejected = string_list(item.get("rejected_candidates"), drop_empty=True)
    if not selected:
        gaps.append(f"evaluation_selected_candidate_missing:{item_id}")
    if not rejected:
        gaps.append(f"evaluation_rejected_candidates_missing:{item_id}")
    if selected and selected in rejected:
        gaps.append(f"evaluation_selected_candidate_also_rejected:{item_id}:{selected}")
    if not _list_items(item.get("metric_results")):
        gaps.append(f"evaluation_metric_results_missing:{item_id}")
    return gaps


def _practice_changes_gaps(root: Path, context: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for item in _list_items(context.get("practice_changes")):
        item_id = _item_id(item)
        change_kind = str(item.get("change_kind") or "")
        gaps.extend(
            _required_string_gaps(
                item,
                item_id,
                "practice_change",
                ("practice", "carrier_kind", "summary", "boundary"),
            )
        )
        gaps.extend(_incumbent_fate_gaps(item, item_id, change_kind))
        gaps.extend(_practice_change_commitment_effect_gaps(item, item_id, change_kind))
        gaps.extend(
            _path_refs_gaps(root, item_id, "practice_change_evidence", item.get("evidence_refs"))
        )
        gaps.extend(
            _path_refs_gaps(root, item_id, "practice_change_decision", item.get("decision_refs"))
        )
    return gaps


def _practice_change_commitment_effect_gaps(
    item: dict[str, Any], item_id: str, change_kind: str
) -> list[str]:
    effect = str(item.get("commitment_effect") or "")
    if not effect:
        return [f"practice_change_commitment_effect_missing:{item_id}"]
    expected = _PRACTICE_CHANGE_EFFECTS.get(change_kind)
    if expected and effect != expected:
        return [
            f"practice_change_commitment_effect_mismatch:{item_id}:{change_kind}:{effect}:"
            f"{expected}"
        ]
    if effect not in _ALLOWED_COMMITMENT_EFFECTS:
        return [f"practice_change_commitment_effect_invalid:{item_id}:{effect}"]
    return []


def _incumbent_fate_gaps(item: dict[str, Any], item_id: str, change_kind: str) -> list[str]:
    gaps: list[str] = []
    if change_kind in {"supersede", "retire"}:
        if not string_list(item.get("incumbents"), drop_empty=True):
            gaps.append(f"practice_change_incumbents_missing:{item_id}")
        if not string_list(item.get("retirement_conditions"), drop_empty=True):
            gaps.append(f"practice_change_retirement_conditions_missing:{item_id}")
    if change_kind == "introduce" and string_list(item.get("incumbents"), drop_empty=True):
        gaps.append(f"practice_change_introduce_has_incumbents:{item_id}")
    return gaps


def _hypothesis_link_gaps(item: dict[str, Any], item_id: str, hypotheses: set[str]) -> list[str]:
    return [
        f"experiment_hypothesis_ref_missing:{item_id}:{hypothesis_ref}"
        for hypothesis_ref in string_list(item.get("hypothesis_refs"), drop_empty=True)
        if hypothesis_ref not in hypotheses
    ]


def _linked_id_gap(
    item: dict[str, Any], item_id: str, field: str, known_ids: set[str], prefix: str
) -> list[str]:
    ref = str(item.get(field) or "")
    if ref and ref not in known_ids:
        return [f"{prefix}_{field}_missing:{item_id}:{ref}"]
    return []


def _required_string_gaps(
    item: dict[str, Any], item_id: str, prefix: str, fields: tuple[str, ...]
) -> list[str]:
    return [
        f"{prefix}_{field}_missing:{item_id}" for field in fields if not str(item.get(field) or "")
    ]


def _required_list_gaps(
    item: dict[str, Any], item_id: str, prefix: str, fields: tuple[str, ...]
) -> list[str]:
    return [
        f"{prefix}_{field}_missing:{item_id}"
        for field in fields
        if not string_list(item.get(field), drop_empty=True)
    ]


def _path_refs_gaps(root: Path, owner_id: str, prefix: str, refs: Any) -> list[str]:
    if not refs:
        return [f"{prefix}_refs_missing:{owner_id}"]
    if not isinstance(refs, list):
        return [f"{prefix}_refs_invalid:{owner_id}"]
    gaps: list[str] = []
    for ref in refs:
        ref_text = str(ref)
        if not _path_ref_exists(root, ref_text):
            gaps.append(f"{prefix}_ref_missing:{owner_id}:{ref_text}")
    return gaps


def _path_ref_exists(root: Path, ref: str) -> bool:
    if not ref or ref.startswith("/") or "://" in ref:
        return False
    return (root / ref).exists()


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("id")) for item in items if item.get("id")}


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or "unnamed")


def _list_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
