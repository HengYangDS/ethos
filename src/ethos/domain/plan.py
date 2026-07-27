"""Plan-stage rule-to-gate matching."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence
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
