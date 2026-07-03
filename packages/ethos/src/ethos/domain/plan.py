"""Plan-stage domain reducers — action-graph construction and rule→gate matching.

Pure logic fed by adapters (rules config) and the kernel (action graph types).
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

from ethos.adapters.config import rules_config
from ethos.domain.status import string_list
from ethos_contracts.rules import stable_digest
from ethos_core.action_graph import ActionGraph
from ethos_core.action_graph import ActionNode

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
