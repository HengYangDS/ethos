"""Explain a rules target: a gap, a rule id, or a path."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.coverage import coverage_report
from ethos.repository.policy.rules.exceptions import minimal_rule_skeleton

if TYPE_CHECKING:
    from pathlib import Path


def explain_rules_target(root: Path, target: str) -> dict[str, object]:
    """Explain a target as a gap, a rule id, or a path, with a next-action contract."""
    compiled = compile_rules(root)
    rules = [rule for rule in cast("list[object]", compiled["rules"]) if isinstance(rule, dict)]
    if ":" in target:
        path = target.split(":", 1)[1]
        return {
            "target": target,
            "kind": "gap",
            "meaning": (
                "Rules gaps identify missing coverage, evidence, authorization, or valid policy."
            ),
            "matched_rules": [],
            "next_action_contract": [
                "ethos rules coverage --changed-path <path>",
                "ethos rules migrate --apply",
            ],
            "minimal_rule_skeleton": minimal_rule_skeleton(path),
        }
    for rule in rules:
        if rule.get("id") == target:
            return {
                "target": target,
                "kind": "rule",
                "rule": rule,
                "matched_rules": [],
                "next_action_contract": ["ethos rules coverage --changed-path <path>"],
                "minimal_rule_skeleton": {},
            }
    coverage = coverage_report(root, changed_paths=(target,))
    return {
        "target": target,
        "kind": "path",
        "matched_rules": coverage["matched_rules"],
        "coverage": coverage,
        "next_action_contract": coverage["next_action_contract"]
        or ["ethos rules coverage --changed-path <path>"],
        "minimal_rule_skeleton": {} if coverage["matched_rules"] else minimal_rule_skeleton(target),
    }
