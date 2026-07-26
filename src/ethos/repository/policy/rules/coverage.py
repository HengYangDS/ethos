"""Coverage reporting: match changed paths against compiled rules."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.config import path_matches

if TYPE_CHECKING:
    from pathlib import Path


def coverage_report(root: Path, *, changed_paths: tuple[str, ...] = ()) -> dict[str, object]:
    """Report which changed paths are covered by compiled rules."""
    compiled = compile_rules(root)
    covered_paths: list[str] = []
    uncovered_paths: list[str] = []
    matched_rules: list[dict[str, object]] = []
    gate_definitions = {
        str(gate_id): dict(gate)
        for gate_id, gate in cast("dict[str, object]", compiled["gate_definitions"]).items()
        if isinstance(gate, dict)
    }
    rules = [
        rule
        for rule in cast("list[dict[str, object]]", compiled["rules"])
        if isinstance(rule, dict)
    ]
    for path in changed_paths:
        matching_rules = [
            rule
            for rule in rules
            if path_matches(
                path, [str(pattern) for pattern in cast("list[object]", rule.get("path_globs", []))]
            )
        ]
        if matching_rules:
            covered_paths.append(path)
            for rule in matching_rules:
                matched_rules.append(
                    {
                        "path": path,
                        "rule_id": rule["id"],
                        "owner": rule["owner"],
                        "subject": rule.get("subject", ""),
                        "authority_ref": rule["authority_ref"],
                        "contract_ref": rule["contract_ref"],
                        "severity": rule["severity"],
                        "required_gates": list(
                            cast("list[object]", rule.get("required_gates", []))
                        ),
                        "required_gates_detail": [
                            gate_definitions[str(gate)]
                            for gate in cast("list[object]", rule.get("required_gates", []))
                            if str(gate) in gate_definitions
                        ],
                        "evidence_requirements": list(
                            cast("list[object]", rule.get("evidence_requirements", []))
                        ),
                        "blocking": rule.get("severity") == "blocking",
                        "stop_condition": rule["stop_condition"],
                        "non_waivable": bool(rule.get("non_waivable", False)),
                    }
                )
        else:
            uncovered_paths.append(path)
    required_gaps = [f"rules_uncovered_path:{path}" for path in uncovered_paths]
    return {
        "ok": not required_gaps,
        "coverage_tier": compiled["coverage_tier"],
        "covered_paths": covered_paths,
        "uncovered_paths": uncovered_paths,
        "matched_rules": matched_rules,
        "required_gaps": required_gaps,
        "next_action_contract": []
        if not required_gaps
        else ["repair .ethos/rules.toml", "ethos rules explain <path>"],
    }
