from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos.adapters.repo.git as git_adapter
from ethos.adapters.repo.status.core import workspace_status
from ethos.domain.report import scorecard_report
from ethos.repository.context import context_for_root
from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.parity import parity_gaps_report
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.docs.topology import docs_topology_report
from ethos.repository.registry.commands import PUBLIC_WORKFLOW_COMMANDS
from ethos.repository.release.core import release_policy_report

if TYPE_CHECKING:
    from pathlib import Path


PLANNING_LAYERS: tuple[dict[str, object], ...] = (
    {
        "id": "L0-local-state-baseline",
        "requirement": (
            "accepted repository state is clean, local closeout is separate from "
            "remote publication, and foreign lanes stay observe-only"
        ),
        "checks": ("workspace-status", "scorecard"),
    },
    {
        "id": "L1-product-boundary-neutrality",
        "requirement": (
            "active product surfaces stay enterprise-neutral: no hardcoded private "
            "adopter, workstation, personal-author, or session-authority defaults"
        ),
        "checks": ("product-boundary",),
    },
    {
        "id": "L2-semantic-docs-topology",
        "requirement": (
            "documentation truth uses semantic state metadata and governed roots "
            "rather than physical time-state truth buckets"
        ),
        "checks": ("docs-topology",),
    },
    {
        "id": "L3-organization-native-identity",
        "requirement": (
            "contributor authority is role, team, maintainer, bot, service, and "
            "adopter-owner based rather than single-author based"
        ),
        "checks": ("contributor-policy",),
    },
    {
        "id": "L4-shared-command-plane",
        "requirement": (
            "product and adopter repositories use one status/plan/prove/land/publish "
            "command loop with orient/report as read-only projections"
        ),
        "checks": ("governance-context",),
    },
    {
        "id": "L5-profile-and-parity-boundary",
        "requirement": (
            "profile and adapter differences do not create a second command plane, "
            "and generic parity is clean before closeout claims"
        ),
        "checks": ("generic-parity",),
    },
    {
        "id": "L6-release-distribution-boundary",
        "requirement": (
            "distribution manifests publish only neutral launcher assets and separate "
            "local readiness from remote publication"
        ),
        "checks": ("release-policy", "generated-artifacts"),
    },
    {
        "id": "L7-enterprise-operability",
        "requirement": (
            "reporting exposes hard quality floors instead of hiding product-boundary "
            "or identity gaps behind scorecards"
        ),
        "checks": ("scorecard",),
    },
    {
        "id": "L8-self-improvement-loop",
        "requirement": (
            "late failures are folded into executable quality gates, evidence, claims, "
            "and chronicle rather than remaining chat guidance"
        ),
        "checks": ("claim-carriers",),
    },
)


CLOSURE_CLAIMS: tuple[str, ...] = (
    "enterprise-product-boundary-20260709",
    "native-docs-topology",
    "isomorphic-governance-context-envelope",
)


def enterprise_readiness_report(root: Path) -> dict[str, object]:
    """Aggregate the enterprise-neutrality completion plan into executable checks."""
    status = workspace_status(root)
    scorecard = scorecard_report(root)
    product_boundary = product_boundary_report(root)
    docs_topology = docs_topology_report(root)
    contributor_policy = contributor_policy_report(root)
    generated_artifacts = generated_artifact_topology_report(root)
    release_policy = release_policy_report(root)
    current_head = git_adapter.current_tracked_head(root)
    parity = parity_gaps_report(
        adopter="generic",
        root=root,
        target=root,
        current_product_head=current_head,
        current_target_head=current_head,
        acceptable_product_heads=(current_head,),
        acceptable_target_heads=(current_head,),
    )
    claims = claims_report(root, current_head=current_head)
    governance_context = context_for_root(root)
    checks: dict[str, dict[str, object]] = {
        "workspace-status": _workspace_status_check(status),
        "scorecard": _scorecard_check(scorecard),
        "product-boundary": _simple_report_check(product_boundary),
        "docs-topology": _simple_report_check(docs_topology),
        "contributor-policy": _simple_report_check(contributor_policy),
        "generated-artifacts": _simple_report_check(generated_artifacts),
        "release-policy": _simple_report_check(release_policy),
        "generic-parity": _simple_report_check(parity),
        "governance-context": _governance_context_check(governance_context),
        "claim-carriers": _claim_carrier_check(root, claims),
    }
    layer_results = [_layer_result(layer, checks) for layer in PLANNING_LAYERS]
    required_gaps = _dedupe(
        gap for result in layer_results for gap in cast("list[str]", result["required_gaps"])
    )
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "summary": {
            "layer_count": len(layer_results),
            "closed_layer_count": sum(1 for layer in layer_results if layer["ok"]),
            "gap_count": len(required_gaps),
            "local_closeout_boundary": "remote publication not required by this gate",
        },
        "required_gaps": required_gaps,
        "layers": layer_results,
        "checks": checks,
        "closure_claims": list(CLOSURE_CLAIMS),
        "boundary": {
            "remote_publication": "separate_deferred_state",
            "foreign_work_lanes": "observe_only_without_handoff_or_break_glass",
            "private_adopters": "profile_or_evidence_boundary_only",
            "identity_model": "external_role_policy",
            "docs_truth": "HEAD_authority_evidence_claims_not_time_state_roots",
            "command_plane": list(PUBLIC_WORKFLOW_COMMANDS),
        },
    }


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    return {}


def _object_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _string_list(value: object) -> list[str]:
    return [str(item) for item in _object_list(value)]


def _int_field(mapping: dict[str, object], key: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _workspace_status_check(status: dict[str, object]) -> dict[str, object]:
    coordination = _mapping(status.get("coordination"))
    required_gaps = _string_list(status.get("required_gaps"))
    if coordination.get("blocking"):
        required_gaps.append("enterprise_readiness_coordination_blocking")
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": required_gaps,
        "summary": {
            "role": status.get("role"),
            "dirty": status.get("dirty"),
            "coordination_blocking": coordination.get("blocking", False),
            "foreign_work_lane_count": len(_object_list(status.get("foreign_work_lanes"))),
        },
    }


def _scorecard_check(scorecard: dict[str, object]) -> dict[str, object]:
    summary = _mapping(scorecard.get("summary"))
    required_gaps = _string_list(scorecard.get("required_gaps"))
    parity_pending_count = _int_field(summary, "parity_pending_count")
    governance_gap_count = _int_field(summary, "governance_gap_count")
    if parity_pending_count:
        required_gaps.append(f"enterprise_readiness_parity_pending:{parity_pending_count}")
    if governance_gap_count:
        required_gaps.append(f"enterprise_readiness_governance_gaps:{governance_gap_count}")
    return {
        "ok": bool(scorecard.get("ok")) and not required_gaps,
        "state": "clean" if bool(scorecard.get("ok")) and not required_gaps else "blocked",
        "required_gaps": required_gaps,
        "summary": summary,
    }


def _simple_report_check(report: dict[str, object]) -> dict[str, object]:
    required_gaps = _string_list(report.get("required_gaps"))
    return {
        "ok": bool(report.get("ok")) and not required_gaps,
        "state": str(report.get("state") or ("clean" if not required_gaps else "blocked")),
        "required_gaps": required_gaps,
        "summary": _mapping(report.get("summary")),
    }


def _governance_context_check(context: dict[str, object]) -> dict[str, object]:
    required_gaps: list[str] = []
    subject = _mapping(context.get("subject"))
    if context.get("single_kernel") is not True:
        required_gaps.append("enterprise_readiness_single_kernel_missing")
    if subject.get("kind") != "repository":
        required_gaps.append("enterprise_readiness_subject_not_repository")
    transition = _string_list(context.get("transition_commands"))
    expected = list(PUBLIC_WORKFLOW_COMMANDS)
    if transition != expected:
        required_gaps.append("enterprise_readiness_transition_commands_mismatch")
    if "ethos orient" not in _string_list(context.get("reader_view_commands")):
        required_gaps.append("enterprise_readiness_orient_reader_view_missing")
    if "ethos report" not in _string_list(context.get("scorecard_commands")):
        required_gaps.append("enterprise_readiness_report_scorecard_missing")
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": required_gaps,
        "summary": {
            "profile": context.get("profile"),
            "single_kernel": context.get("single_kernel"),
            "subject_kind": subject.get("kind"),
        },
    }


def _claim_carrier_check(root: Path, claims: dict[str, object]) -> dict[str, object]:
    missing = [
        claim
        for claim in CLOSURE_CLAIMS
        if not (root / "evidence" / "claims" / f"{claim}.toml").exists()
    ]
    required_gaps = [f"enterprise_readiness_claim_missing:{claim}" for claim in missing]
    required_gaps.extend(_string_list(claims.get("required_gaps")))
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": required_gaps,
        "summary": {
            "closure_claim_count": len(CLOSURE_CLAIMS),
            "missing_closure_claim_count": len(missing),
            "claim_gap_count": len(_string_list(claims.get("required_gaps"))),
        },
    }


def _layer_result(
    layer: dict[str, object], checks: dict[str, dict[str, object]]
) -> dict[str, object]:
    check_ids = tuple(str(item) for item in cast("tuple[object, ...]", layer["checks"]))
    gaps = _dedupe(
        gap
        for check_id in check_ids
        for gap in cast("list[str]", checks[check_id]["required_gaps"])
    )
    return {
        "id": layer["id"],
        "ok": not gaps,
        "requirement": layer["requirement"],
        "checks": list(check_ids),
        "required_gaps": gaps,
    }


def _dedupe(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value)
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result
