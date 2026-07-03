"""Plan-stage domain reducers — action-graph, rule→gate matching, rule-fact snapshot.

Pure logic fed by adapters (rules config, workspace status) and the kernel (action
graph types). The rule-fact snapshot composes governance facts from lower-layer
reports; all imports flow downward (contracts / repository / adapters), keeping the
surface→domain→... layering acyclic.
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

from ethos.adapters.config import rules_config
from ethos.domain.status import audit_for_root
from ethos.domain.status import status_worktree_gaps
from ethos.domain.status import string_list
from ethos.surface.cli._base import ASSISTANT_TRUTH_BOUNDARY
from ethos_adapters.status import workspace_status
from ethos_assistants.projections import projection_contract
from ethos_contracts.rules import RuleFactSnapshot
from ethos_contracts.rules import stable_digest
from ethos_core.action_graph import ActionGraph
from ethos_core.action_graph import ActionNode
from ethos_repository.claims import claims_report
from ethos_repository.command_registry import command_registry_report

if TYPE_CHECKING:
    from pathlib import Path


def path_matches(path: str, pattern: str) -> bool:
    """Match a path against a rule pattern (supports trailing /** prefix globs)."""
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(path, pattern)


def matching_rule_gates(
    root: Path,
    paths: tuple[str, ...],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Match changed paths against [[rule]] entries → (matched_rules, required_gates)."""
    config = rules_config(root)
    gates = config.get("gates") if isinstance(config.get("gates"), dict) else {}
    matched_rules: list[dict[str, object]] = []
    required_gates: list[dict[str, object]] = []
    rules = config.get("rule") if isinstance(config.get("rule"), list) else []
    for raw_rule in rules:
        if not isinstance(raw_rule, dict):
            continue
        matched_paths = [
            path
            for path in paths
            if any(path_matches(path, pattern) for pattern in string_list(raw_rule.get("paths")))
        ]
        if not matched_paths:
            continue
        rule_gates: list[dict[str, object]] = []
        for gate_id in string_list(raw_rule.get("requires")):
            gate_config = gates.get(gate_id, {}) if isinstance(gates, dict) else {}
            gate = {
                "id": gate_id,
                "command": (
                    str(gate_config.get("command", "")) if isinstance(gate_config, dict) else ""
                ),
                "blocking": gate_config.get("blocking", True) is not False
                if isinstance(gate_config, dict)
                else True,
            }
            rule_gates.append(gate)
            required_gates.append(gate)
        matched_rules.append(
            {
                "id": str(raw_rule.get("id", "")),
                "risk": str(raw_rule.get("risk", "")),
                "matched_paths": matched_paths,
                "required_gates": rule_gates,
                "evidence": string_list(raw_rule.get("evidence")),
            }
        )
    return matched_rules, required_gates


def graph_for_paths(paths: tuple[str, ...]) -> ActionGraph:
    """Build the deterministic status→prove→audit action graph for changed paths."""
    inputs = tuple(sorted(paths)) or ("pyproject.toml",)
    nodes = (
        ActionNode(
            id="status",
            kind="inspection",
            command=("ethos", "status", "--json"),
            inputs=inputs,
            outputs=(),
            policy="required",
        ),
        ActionNode(
            id="prove",
            kind="proof",
            command=("ethos", "prove", "--json"),
            inputs=inputs,
            outputs=("docs/evidence/latest-proof.json",),
            policy="required",
        ),
        ActionNode(
            id="repository-audit",
            kind="governance",
            command=("ethos", "audit", "--json"),
            inputs=inputs,
            outputs=(),
            policy="required",
        ),
    )
    return ActionGraph(nodes=nodes)


def rule_fact(
    *,
    owner: str,
    value: object,
    fresh: bool = True,
    available: bool = True,
) -> dict[str, object]:
    """Build a rule-evaluation fact envelope (owner, freshness, availability, digest)."""
    return {
        "owner": owner,
        "fresh": fresh,
        "available": available,
        "value": value,
        "digest": stable_digest(value),
    }


def unavailable_rule_fact(owner: str, exc: BaseException) -> dict[str, object]:
    """Build a fact marking a source unavailable due to an exception."""
    return rule_fact(
        owner=owner,
        fresh=False,
        available=False,
        value={"error": type(exc).__name__, "message": str(exc)},
    )


def rule_fact_snapshot(
    repo: Path,
    *,
    phase: str,
    head: str,
    changed_paths: tuple[str, ...] = (),
    mutation: bool = False,
    authorized: bool = False,
    actor: str = "local",
    scope: str = "repository",
    status_payload: dict[str, object] | None = None,
    prewrite_report: dict[str, object] | None = None,
    audit_payload: dict[str, object] | None = None,
) -> RuleFactSnapshot:
    """Compose the governance rule-fact snapshot for a phase from lower-layer reports."""
    facts: dict[str, dict[str, object]] = {
        "changed_paths": rule_fact(
            owner="ethos-adapters.status",
            value=list(changed_paths),
        ),
        "mutation": rule_fact(owner="ethos-cli", value=mutation),
        "authorization": rule_fact(owner="ethos-cli", value=authorized),
        "actor": rule_fact(owner="ethos-cli", value=actor),
        "scope": rule_fact(owner="ethos-cli", value=scope),
    }
    source_refs = [
        "ethos-adapters.status",
        "ethos-repository.self-audit",
        "ethos-repository.claims",
        "ethos-repository.command-registry",
        "ethos-assistants.projections",
    ]
    audit_mode = "product"
    try:
        status = status_payload if status_payload is not None else workspace_status(repo)
        facts["worktree"] = rule_fact(
            owner="ethos-adapters.status",
            value={
                "branch": status.get("branch", ""),
                "role": status.get("role", ""),
                "changed_paths": status.get("changed_paths", []),
                "required_gaps": status_worktree_gaps(status),
            },
        )
    except BaseException as exc:  # pragma: no cover - defensive adapter boundary.
        facts["worktree"] = unavailable_rule_fact("ethos-adapters.status", exc)
    if prewrite_report is not None:
        source_refs.append("ethos-adapters.prewrite")
        facts["prewrite"] = rule_fact(
            owner="ethos-adapters.prewrite",
            value={
                "ok": prewrite_report.get("ok", False),
                "role": prewrite_report.get("role", ""),
                "required_gaps": prewrite_report.get("required_gaps", []),
                "paths": prewrite_report.get("paths", []),
            },
        )
    elif phase == "prewrite":
        source_refs.append("ethos-adapters.prewrite")
        facts["prewrite"] = rule_fact(
            owner="ethos-adapters.prewrite",
            value={"required_gaps": ["prewrite_guard_not_supplied"]},
            fresh=False,
            available=False,
        )
    else:
        facts["prewrite"] = rule_fact(
            owner="ethos-adapters.prewrite",
            value={"ok": True, "required_gaps": [], "not_applicable": True},
        )
    try:
        audit = audit_payload if audit_payload is not None else audit_for_root(repo)
        audit_mode = str(audit.get("mode", "product"))
        facts["openspec_state"] = rule_fact(
            owner="ethos-repository.self-audit",
            value=audit.get("openspec", {}),
        )
        facts["host_readiness"] = rule_fact(
            owner="ethos-repository.self-audit",
            value={
                "mode": audit.get("mode", "product"),
                "ok": audit.get("ok", False),
                "required_gaps": audit.get("required_gaps", []),
            },
        )
    except BaseException as exc:  # pragma: no cover - defensive adapter boundary.
        facts["openspec_state"] = unavailable_rule_fact("ethos-repository.self-audit", exc)
        facts["host_readiness"] = unavailable_rule_fact("ethos-repository.self-audit", exc)
    try:
        claims = claims_report(repo)
        claim_gaps = [str(gap) for gap in claims.get("required_gaps", [])]
        if audit_mode == "adopter":
            claim_gaps = [gap for gap in claim_gaps if gap != "claims_missing"]
        claims_ok = bool(claims.get("ok", False)) or not claim_gaps
        facts["claim_state"] = rule_fact(
            owner="ethos-repository.claims",
            value={
                "ok": claims_ok,
                "required_gaps": claim_gaps,
            },
        )
        facts["evidence_freshness"] = rule_fact(
            owner="ethos-repository.claims",
            value={
                "ok": claims_ok,
                "stale": [gap for gap in claim_gaps if "digest" in str(gap)],
            },
        )
    except BaseException as exc:  # pragma: no cover - defensive adapter boundary.
        facts["claim_state"] = unavailable_rule_fact("ethos-repository.claims", exc)
        facts["evidence_freshness"] = unavailable_rule_fact("ethos-repository.claims", exc)
    try:
        command_report = command_registry_report(repo)
        facts["command_registry"] = rule_fact(
            owner="ethos-repository.command-registry",
            value={
                "ok": command_report.get("ok", False),
                "required_gaps": command_report.get("required_gaps", []),
                "public_commands": command_report.get("public_commands", []),
            },
        )
    except BaseException as exc:  # pragma: no cover - defensive adapter boundary.
        facts["command_registry"] = unavailable_rule_fact(
            "ethos-repository.command-registry", exc
        )
    try:
        projection = projection_contract()
        facts["projection_drift"] = rule_fact(
            owner="ethos-assistants.projections",
            value={
                "truth": projection.get("truth", ""),
                "ok": projection.get("truth", "") == ASSISTANT_TRUTH_BOUNDARY,
            },
        )
    except BaseException as exc:  # pragma: no cover - defensive adapter boundary.
        facts["projection_drift"] = unavailable_rule_fact(
            "ethos-assistants.projections", exc
        )
    return RuleFactSnapshot(
        phase=phase,
        head=head,
        facts=facts,
        source_refs=tuple(source_refs),
    )
