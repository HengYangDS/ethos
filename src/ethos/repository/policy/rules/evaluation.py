"""Rules evaluation: turn compiled rules + a fact snapshot into a governance decision."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.contracts.rules import RuleEvalRequest
from ethos.contracts.rules import RuleFactSnapshot
from ethos.contracts.rules import stable_digest
from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.coverage import coverage_report
from ethos.repository.policy.rules.exceptions import policy_exceptions_report

if TYPE_CHECKING:
    from pathlib import Path

VALID_PHASES = {"plan", "prewrite", "prove", "land", "publish"}
REQUIRED_CORE_FACTS = (
    "changed_paths",
    "mutation",
    "authorization",
    "actor",
    "scope",
    "worktree",
    "prewrite",
    "openspec_state",
    "claim_state",
    "evidence_freshness",
    "host_readiness",
    "command_registry",
    "projection_drift",
)
ALWAYS_FAIL_CLOSED_VALUE_FACTS = {
    "claim_state",
    "evidence_freshness",
    "command_registry",
    "projection_drift",
    "openspec_state",
}
PHASED_FAIL_CLOSED_VALUE_FACTS = {
    "host_readiness": {"prove", "land", "publish"},
    "worktree": {"prewrite", "land", "publish"},
    "prewrite": {"prewrite"},
}


def _fact_value(snapshot: RuleFactSnapshot, name: str, default: Any) -> Any:
    fact = snapshot.facts.get(name, {})
    if not isinstance(fact, dict) or fact.get("available") is False:
        return default
    return fact.get("value", default)


def _fact_value_gaps(*, phase: str, name: str, value: Any) -> list[str]:
    phase_closed_facts = PHASED_FAIL_CLOSED_VALUE_FACTS.get(name, set())
    fail_closed = name in ALWAYS_FAIL_CLOSED_VALUE_FACTS or phase in phase_closed_facts
    if not fail_closed or not isinstance(value, dict):
        return []
    gaps: list[str] = []
    if value.get("ok") is False:
        gaps.append(f"fact_not_ok:{name}")
    required_gaps = value.get("required_gaps")
    if isinstance(required_gaps, list):
        gaps.extend(
            f"fact_required_gap:{name}:{gap}"
            for gap in required_gaps
            if isinstance(gap, str) and gap
        )
    stale = value.get("stale")
    if isinstance(stale, list):
        gaps.extend(f"fact_stale_ref:{name}:{ref}" for ref in stale if isinstance(ref, str) and ref)
    return gaps


def fact_gaps(snapshot: RuleFactSnapshot) -> list[str]:
    """Report every governance gap implied by a fact snapshot (missing, stale, fail-closed)."""
    gaps: list[str] = []
    for name in REQUIRED_CORE_FACTS:
        if name not in snapshot.facts:
            gaps.append(f"fact_missing:{name}")
    for name, fact in snapshot.facts.items():
        gaps.extend(_single_fact_gaps(name=name, fact=fact, phase=snapshot.phase))
    return gaps


def _single_fact_gaps(*, name: str, fact: object, phase: str) -> list[str]:
    if not isinstance(fact, dict):
        return [f"fact_malformed:{name}"]
    gaps: list[str] = []
    if not fact.get("owner"):
        gaps.append(f"fact_owner_missing:{name}")
    if fact.get("available") is False:
        gaps.append(f"fact_unavailable:{name}")
    if fact.get("fresh") is False:
        gaps.append(f"fact_stale:{name}")
    value = fact.get("value")
    if isinstance(value, dict):
        if value.get("timeout") is True:
            gaps.append(f"fact_timeout:{name}")
        if value.get("deterministic") is False:
            gaps.append(f"fact_nondeterministic:{name}")
        conflicts = value.get("unresolved_conflicts")
        if isinstance(conflicts, list) and conflicts:
            gaps.append(f"fact_unresolved_conflicts:{name}")
    gaps.extend(_fact_value_gaps(phase=phase, name=name, value=value))
    return gaps


def scope_matches_path(scope: str, path: str) -> bool:
    """Return whether a waiver scope ('repository' or 'path:<prefix>') covers a path."""
    if scope == "repository":
        return True
    if not scope.startswith("path:"):
        return False
    prefix = scope.removeprefix("path:").strip("/")
    if not prefix:
        return False
    normalized = path.strip("/")
    return normalized == prefix or normalized.startswith(f"{prefix}/")


def active_valid_exceptions(exceptions: dict[str, object]) -> list[dict[str, object]]:
    """Return the active, schema-valid policy exceptions from an exceptions report."""
    if exceptions["required_gaps"]:
        return []
    active: list[dict[str, object]] = []
    for item in cast("list[dict[str, object]]", exceptions["exceptions"]):
        if isinstance(item, dict) and item.get("status") == "active":
            active.append(item)
    return active


def match_waiver(
    *,
    rule_id: str,
    path: str,
    exceptions: list[dict[str, object]],
) -> dict[str, object] | None:
    """Return the first active exception whose rule and scope cover this rule/path, if any."""
    for exception in exceptions:
        if exception.get("rule_id") != rule_id:
            continue
        scope = str(exception.get("scope", ""))
        if scope_matches_path(scope, path):
            return exception
    return None


def _obligation(kind: str, obligation_id: str, *, scope: str, actor: str) -> dict[str, object]:
    return {"id": obligation_id, "kind": kind, "scope": scope, "actor": actor, "blocking": True}


def _evaluate_matched_rules(
    matched_rules: list[dict[str, object]],
    *,
    phase: str,
    scope: str,
    actor: str,
    valid_exceptions: list[dict[str, object]],
) -> tuple[list[str], list[dict[str, object]], list[dict[str, object]]]:
    """Fold blocking matched rules into (required gaps, blocking obligations, applied waivers)."""
    required_gaps: list[str] = []
    blocking_obligations: list[dict[str, object]] = []
    waivers_applied: list[dict[str, object]] = []
    for match in matched_rules:
        if not match.get("blocking"):
            continue
        rule_id = str(match.get("rule_id", ""))
        path = str(match.get("path", ""))
        match_gaps: list[str] = []
        if phase != "prove":
            match_gaps.extend(
                f"gate_required:{rule_id}:{gate}"
                for gate in cast("list[object]", match.get("required_gates", []))
            )
        if phase in {"land", "publish"}:
            match_gaps.extend(
                f"evidence_required:{rule_id}:{evidence}"
                for evidence in cast("list[object]", match.get("evidence_requirements", []))
            )
        waiver = None
        if not match.get("non_waivable"):
            waiver = match_waiver(rule_id=rule_id, path=path, exceptions=valid_exceptions)
        if waiver is not None and match_gaps:
            waivers_applied.append(
                {
                    "id": str(waiver.get("id", "")),
                    "rule_id": rule_id,
                    "scope": str(waiver.get("scope", "")),
                    "waived_gaps": list(match_gaps),
                }
            )
            continue
        required_gaps.extend(match_gaps)
        blocking_obligations.extend(
            _obligation("require_gate", str(gate), scope=scope, actor=actor)
            for gate in cast("list[object]", match.get("required_gates", []))
        )
        blocking_obligations.extend(
            _obligation("require_evidence", str(evidence), scope=scope, actor=actor)
            for evidence in cast("list[object]", match.get("evidence_requirements", []))
        )
    return required_gaps, blocking_obligations, waivers_applied


def _obligations_for_gap(gap: str, *, scope: str, actor: str) -> list[dict[str, object]]:
    if gap.startswith("authorization_required"):
        return [_obligation("require_authorization", "authorization", scope=scope, actor=actor)]
    if gap.startswith("gate_required:"):
        return [_obligation("require_gate", gap.split(":", 2)[-1], scope=scope, actor=actor)]
    if gap.startswith("evidence_required:"):
        return [_obligation("require_evidence", gap.split(":", 2)[-1], scope=scope, actor=actor)]
    return []


def rules_evaluation_report(
    root: Path,
    *,
    phase: str = "plan",
    changed_paths: tuple[str, ...] = (),
    mutation: bool = False,
    authorized: bool = False,
    actor: str = "local",
    scope: str = "repository",
    head: str = "untracked",
    fact_snapshot: RuleFactSnapshot | None = None,
    today: str | None = None,
) -> dict[str, object]:
    """Evaluate compiled rules against a fact snapshot into a block/advisory/allow decision."""
    compiled = compile_rules(root)
    request = RuleEvalRequest(
        phase=phase,
        changed_paths=changed_paths,
        mutation=mutation,
        authorized=authorized,
        actor=actor,
        scope=scope,
    )
    snapshot = fact_snapshot or request.to_fact_snapshot(
        head=head,
        source_refs=tuple(str(ref) for ref in cast("list[object]", compiled["source_refs"])),
    )
    mutation = bool(_fact_value(snapshot, "mutation", mutation))
    authorized = bool(_fact_value(snapshot, "authorization", authorized))
    actor = str(_fact_value(snapshot, "actor", actor))
    scope = str(_fact_value(snapshot, "scope", scope))
    snapshot_paths = tuple(str(path) for path in _fact_value(snapshot, "changed_paths", []))
    coverage = coverage_report(root, changed_paths=snapshot_paths)
    check = rules_check_report(root)
    exceptions = policy_exceptions_report(root, today=today)
    required_gaps: list[str] = []
    if phase not in VALID_PHASES:
        required_gaps.append(f"invalid_rule_phase:{phase}")
    required_gaps.extend(str(gap) for gap in cast("list[object]", check["required_gaps"]))
    required_gaps.extend(fact_gaps(snapshot))
    required_gaps.extend(str(gap) for gap in cast("list[object]", coverage["required_gaps"]))
    required_gaps.extend(
        f"policy_exception:{gap}" for gap in cast("list[object]", exceptions["required_gaps"])
    )
    if mutation and phase in {"land", "publish"} and not authorized:
        required_gaps.append("authorization_required")
    valid_exceptions = active_valid_exceptions(exceptions)
    matched_gaps, blocking_obligations, waivers_applied = _evaluate_matched_rules(
        cast("list[dict[str, object]]", coverage["matched_rules"]),
        phase=phase,
        scope=scope,
        actor=actor,
        valid_exceptions=valid_exceptions,
    )
    required_gaps.extend(matched_gaps)
    decisions: list[dict[str, object]] = []
    obligations: list[dict[str, object]] = []
    if required_gaps:
        decisions.append(
            {
                "id": f"{phase}:blocking",
                "decision": "block",
                "required_gaps": list(dict.fromkeys(required_gaps)),
            }
        )
    for gap in required_gaps:
        obligations.extend(_obligations_for_gap(gap, scope=scope, actor=actor))
    obligations.extend(blocking_obligations)
    deduped_gaps = list(dict.fromkeys(required_gaps))
    matched = list(cast("list[dict[str, object]]", coverage["matched_rules"]))
    state = "block" if deduped_gaps else ("advisory" if matched else "allow")
    evaluation_base = {
        "schema_version": 1,
        "state": state,
        "head": snapshot.head,
        "rule_set_digest": compiled["rule_set_digest"],
        "compiled_policy_digest": compiled["compiled_policy_digest"],
        "source_refs": list(cast("list[object]", compiled["source_refs"])),
        "fact_snapshot_digest": snapshot.digest,
        "input_snapshot": snapshot.to_dict(),
        "surface_matches": matched,
        "effective_rules": [
            rule["id"]
            for rule in cast("list[dict[str, object]]", compiled["rules"])
            if isinstance(rule, dict)
        ],
        "decisions": decisions,
        "obligations": list(_dedupe_records(obligations)),
        "required_gates": sorted(
            {
                str(gate)
                for match in matched
                for gate in cast("list[object]", match.get("required_gates", []))
            }
        ),
        "required_gates_detail": required_gate_details(matched),
        "evidence_requirements": sorted(
            {
                str(req)
                for match in matched
                for req in cast("list[object]", match.get("evidence_requirements", []))
            }
        ),
        "stops": [gap.split(":", 1)[0] for gap in deduped_gaps],
        "waivers_applied": waivers_applied,
        "required_gaps": deduped_gaps,
        "next_action_contract": []
        if not deduped_gaps
        else ["ethos rules explain <gap>", "ethos prove --json"],
    }
    return {**evaluation_base, "digest": stable_digest(evaluation_base)}


def required_gate_details(matches: list[dict[str, object]]) -> list[dict[str, object]]:
    """Collect the unique, id-sorted gate-definition details across matched rules."""
    details: dict[str, dict[str, object]] = {}
    for match in matches:
        for gate in cast("list[dict[str, object]]", match.get("required_gates_detail", [])):
            if isinstance(gate, dict) and gate.get("id"):
                details[str(gate["id"])] = dict(gate)
    return [details[key] for key in sorted(details)]


def _dedupe_records(records: list[dict[str, object]]) -> tuple[dict[str, object], ...]:
    deduped: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in records:
        key = stable_digest(record)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return tuple(deduped)
