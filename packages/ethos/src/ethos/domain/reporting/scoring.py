from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.gates.ty import ty_gate_report
from ethos.domain.prove import code_size_report
from ethos.domain.source_budget.core import source_budget_report
from ethos.repository.evidence.parity.core import parity_ledger_report
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.coverage import coverage_quality_report
from ethos.repository.policy.docstrings.core import docstring_coverage_report
from ethos.repository.policy.layout.core import module_layout_report
from ethos.repository.registry.standards import standard_adapter_registry
from ethos_core.contracts.context.projection import ASSISTANT_TRUTH_BOUNDARY

if TYPE_CHECKING:
    from pathlib import Path


_HARD_QUALITY_COMMANDS = (
    (True, ("code_size_",), "ethos quality code-size --json"),
    (True, ("coverage_",), "ethos quality coverage --json"),
    (True, ("ty_",), "ethos quality types --json"),
    (
        True,
        ("docstring_", "public_docstring_missing:"),
        "ethos quality docstrings --json",
    ),
    (True, ("module_layout_",), "ethos quality module-layout --json"),
    (True, ("generated_artifact_",), "ethos quality generated-artifacts --json"),
    (
        False,
        ("product-boundary", "product_boundary"),
        "ethos quality product-boundary --json",
    ),
    (False, ("contributor", "identity"), "ethos quality contributor-policy --json"),
)


def adopter_scores(
    audit: dict[str, object],
    projection: dict[str, object],
    context_projection_score: int,
    _playbooks: dict[str, object],
    workflow_runtime: dict[str, object] | None = None,
) -> dict[str, int]:
    return {
        "adopter_governance": int(bool(audit["ok"])),
        "assistant_projection": int(projection["truth"] == ASSISTANT_TRUTH_BOUNDARY),
        "context_projection": context_projection_score,
        "workflow_runtime": int(_workflow_runtime_score(workflow_runtime)),
        "parity_ledger": int(bool(parity_ledger_report()["ok"])),
    }


def _workflow_runtime_score(workflow_runtime: dict[str, object] | None) -> bool:
    if workflow_runtime is None:
        return True
    gaps = cast("list[object]", workflow_runtime.get("required_gaps", []))
    return bool(workflow_runtime.get("ok")) or gaps == [
        "workflow_contract_unavailable:FileNotFoundError"
    ]


def product_scores(
    audit: dict[str, object],
    docs_report: dict[str, object],
    claim_report: dict[str, object],
    command_report: dict[str, object],
    projection: dict[str, object],
    schemas_report: dict[str, object],
    evolution: dict[str, object],
    signature: dict[str, object],
    playbooks: dict[str, object],
    parity_ledger: dict[str, object],
    context_projection_score: int,
    workflow_runtime: dict[str, object] | None = None,
) -> dict[str, int]:
    package_ontology = cast("dict[str, object]", audit["package_ontology"])
    return {
        "package_ontology": int(bool(package_ontology["ok"])),
        "distribution_adapter": int(not package_ontology["adapter_missing"]),
        "docs": int(bool(docs_report["ok"])),
        "schemas": int(bool(cast("dict[str, object]", audit["schemas"])["ok"])),
        "schema_validation": int(bool(schemas_report["ok"])),
        "claims": int(bool(claim_report["ok"])),
        "command_registry": int(bool(command_report["ok"])),
        "standards": int(
            all(
                item["boundary"] and item["fallback"] and item["exit_strategy"]
                for item in standard_adapter_registry().values()
            )
        ),
        "assistant_projection": int(projection["truth"] == ASSISTANT_TRUTH_BOUNDARY),
        "context_projection": context_projection_score,
        "evolution": int(bool(evolution["ok"])),
        "signature_policy": int(bool(signature["ok"])),
        "openspec": int(bool(cast("dict[str, object]", audit["openspec"])["ok"])),
        "playbooks": int(bool(playbooks["ok"])),
        "workflow_runtime": int(bool((workflow_runtime or {"ok": True})["ok"])),
        "parity_ledger": int(bool(parity_ledger["ok"])),
    }


def hard_quality_floor_report(repo: Path) -> dict[str, object]:
    """Return product hard quality gates that the scorecard must not hide."""
    gate_reports = {
        "python-size": code_size_report(repo),
        "source-budget": source_budget_report(repo),
        "coverage": coverage_quality_report(repo),
        "types": ty_gate_report(repo),
        "docstrings": docstring_coverage_report(repo),
        "module-layout": module_layout_report(repo),
        "generated-artifacts": generated_artifact_topology_report(repo),
        "product-boundary": product_boundary_report(repo),
        "contributor-policy": contributor_policy_report(repo),
    }
    required_gaps: list[str] = []
    for report in gate_reports.values():
        required_gaps.extend(cast("list[str]", report["required_gaps"]))
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "gate_ids": list(gate_reports),
        "required_gaps": required_gaps,
        "gates": gate_reports,
    }


def global_compression_report(repo: Path) -> dict[str, object]:
    """Expose source-budget debt without treating it as local change correctness."""
    report = source_budget_report(repo)
    return {
        "ok": bool(report["ok"]),
        "state": str(report["state"]),
        "gate_ids": ["source-budget"],
        "required_gaps": list(cast("list[str]", report["required_gaps"])),
        "gates": {"source-budget": report},
    }


def adopter_quality_floor_report() -> dict[str, object]:
    """Return the adopter report boundary; adopter gates remain profile-owned."""
    return {
        "ok": True,
        "state": "profile_deferred",
        "gate_ids": [],
        "required_gaps": [],
        "gates": {},
        "boundary": "adopter_profile_quality_floor",
    }


def terminal_control(
    *,
    result_required_gaps: tuple[str, ...],
    hard_quality_gap_count: int,
    stage_gates: dict[str, object],
) -> str:
    if result_required_gaps or hard_quality_gap_count:
        return "partial"
    if any(value is False for value in stage_gates.values() if isinstance(value, bool)):
        return "partial"
    return "closed_loop"


def scorecard_next_actions(
    *,
    parity_pending_count: int,
    hard_quality_floor: dict[str, object],
    coordination_required_gaps: tuple[str, ...] = (),
    playbooks: dict[str, object] | None = None,
) -> tuple[str, ...]:
    """Return bounded next actions for report without hiding hard quality gaps."""
    quality_gaps = cast("list[str]", hard_quality_floor["required_gaps"])
    if quality_gaps:
        return _hard_quality_next_actions(quality_gaps)
    if coordination_required_gaps:
        return ("ethos orient --json", "ethos lane status --json")
    if parity_pending_count:
        return ("ethos parity gaps --adopter <adopter>",)
    if playbooks and playbooks.get("ok") is not True:
        return ("ethos playbooks check --mode v2-strict --json",)
    return ("ethos prove --full",)


def _hard_quality_next_actions(quality_gaps: list[str]) -> tuple[str, ...]:
    """Route hard quality gaps to the narrowest standalone quality command."""
    commands = tuple(
        command
        for prefixes, tokens, command in _HARD_QUALITY_COMMANDS
        if any(
            gap.startswith(tokens) if prefixes else any(token in gap for token in tokens)
            for gap in quality_gaps
        )
    )
    return commands or ("ethos quality --json",)


def first_hour(*, product_profile: bool, required_gaps: tuple[str, ...]) -> dict[str, object]:
    if product_profile:
        return {}
    evidence_gap_count = len(required_gaps)
    readiness = "local_readiness" if evidence_gap_count == 0 else "blocked"
    return {
        "proof_status": "ready" if evidence_gap_count == 0 else "gapped",
        "evidence_gap_count": evidence_gap_count,
        "land_readiness": readiness,
        "publish_readiness": readiness,
        "hosted_ci_truth": "external-evidence",
        "next_action": "ethos prove" if evidence_gap_count == 0 else "resolve evidence gaps",
    }
