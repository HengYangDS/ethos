"""Plan-stage domain reducers — PlanIR, rule→gate matching, rule-fact snapshot.

Pure logic fed by adapters (rules config, workspace status) and the kernel (action
graph types). The rule-fact snapshot composes governance facts from lower-layer
reports; all imports flow downward (contracts / repository / adapters), keeping the
surface→domain→... layering acyclic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.status.core import workspace_status
from ethos.assistants.projections import projection_contract
from ethos.contracts.context.projection import ASSISTANT_TRUTH_BOUNDARY
from ethos.contracts.rules import RuleAttestation
from ethos.contracts.rules import RuleFactSnapshot
from ethos.contracts.rules import stable_digest
from ethos.domain.status import audit_for_root
from ethos.domain.status import status_worktree_gaps
from ethos.normalization.core import object_sequence
from ethos.normalization.core import string_mapping
from ethos.normalization.core import string_sequence
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.config import path_matches

if TYPE_CHECKING:
    from pathlib import Path


def matching_rule_gates(
    root: Path,
    paths: tuple[str, ...],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
    """Match paths against compiled rules and resolve their declared gates."""
    compiled = compile_rules(root)
    rules = [
        string_mapping(rule)
        for rule in object_sequence(compiled.get("rules"))
        if isinstance(rule, dict)
    ]
    gate_definitions = {
        gate_id: string_mapping(gate)
        for gate_id, gate in string_mapping(compiled.get("gate_definitions")).items()
        if isinstance(gate, dict)
    }
    matched_rules: list[dict[str, object]] = []
    required_gates: list[dict[str, object]] = []
    seen_gate_ids: set[str] = set()
    for rule in rules:
        patterns = tuple(string_sequence(rule.get("path_globs")))
        matched_paths = [path for path in paths if path_matches(path, patterns)]
        if not matched_paths:
            continue
        rule_gates: list[dict[str, object]] = []
        for gate_name in string_sequence(rule.get("required_gates")):
            gate = gate_definitions.get(gate_name)
            if gate is None:
                continue
            rule_gates.append(gate)
            if gate_name not in seen_gate_ids:
                required_gates.append(gate)
                seen_gate_ids.add(gate_name)
        matched_rules.append(
            {
                "id": str(rule.get("id", "")),
                "subject": str(rule.get("subject", "")),
                "matched_paths": matched_paths,
                "required_gates": rule_gates,
                "evidence_requirements": object_sequence(rule.get("evidence_requirements")),
            }
        )
    return matched_rules, required_gates, string_sequence(compiled.get("compile_gaps"))


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
        "ethos-assistants.projections",
    ]
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
        projection = projection_contract()
        facts["projection_drift"] = rule_fact(
            owner="ethos-assistants.projections",
            value={
                "truth": projection.get("truth", ""),
                "ok": projection.get("truth", "") == ASSISTANT_TRUTH_BOUNDARY,
            },
        )
    except BaseException as exc:  # pragma: no cover - defensive adapter boundary.
        facts["projection_drift"] = unavailable_rule_fact("ethos-assistants.projections", exc)
    return RuleFactSnapshot(
        phase=phase,
        head=head,
        facts=facts,
        source_refs=tuple(source_refs),
    )


def rule_attestation_for_evaluation(
    evaluation: dict[str, object],
    *,
    actor: str,
    scope: str,
) -> dict[str, object]:
    """Build the rule-attestation envelope from a rules evaluation (digest-bound)."""
    attestation = RuleAttestation(
        head=str(evaluation["head"]),
        evaluation_digest=str(evaluation["digest"]),
        rule_set_digest=str(evaluation["rule_set_digest"]),
        compiled_policy_digest=str(evaluation["compiled_policy_digest"]),
        fact_snapshot_digest=str(evaluation["fact_snapshot_digest"]),
        actor=actor,
        scope=scope,
        runner_identity="ethos-cli",
        input=dict(cast("dict[str, object]", evaluation["input_snapshot"])),
        output={
            "state": evaluation["state"],
            "required_gaps": list(cast("list[object]", evaluation["required_gaps"])),
            "required_gates": list(cast("list[object]", evaluation["required_gates"])),
        },
    )
    return attestation.to_dict()
