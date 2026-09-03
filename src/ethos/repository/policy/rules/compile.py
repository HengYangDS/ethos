"""Compiled-policy core: assemble a deterministic RuleSet from config and starter rules."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.contracts.rules import Rule
from ethos.contracts.rules import RuleSet
from ethos.repository.policy.gates import resolve_gate_policy
from ethos.repository.policy.rules.config import configured_rules
from ethos.repository.policy.rules.config import load_rules_config
from ethos.repository.policy.rules.config import resolve_profile_stack
from ethos.repository.policy.rules.config import rules_path
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

STRICT_PROFILE = "strict"
STARTER_RULES: tuple[Rule, ...] = (
    Rule(
        id="starter.docs",
        version=1,
        owner="ethos",
        profile_layers=("generic",),
        authority_ref="docs/guides/quickstart.md",
        contract_ref="docs/governance/docs-registry.md",
        subject="docs",
        path_globs=(
            "docs/**",
            "README.md",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "distributions/**/README.md",
        ),
        severity="advisory",
        required_gates=("docs-registry",),
        stop_condition="docs_registry_drift",
    ),
    Rule(
        id="starter.python",
        version=1,
        owner="ethos",
        profile_layers=("python",),
        authority_ref="pyproject.toml",
        contract_ref="pyproject.toml",
        subject="source",
        path_globs=("src/**/*.py", "tests/**/*.py"),
        severity="advisory",
        required_gates=("unit-architecture",),
        stop_condition="python_test_gap",
    ),
    Rule(
        id="starter.schemas",
        version=1,
        owner="ethos",
        profile_layers=("generic",),
        authority_ref="system/schemas/kernel",
        contract_ref="docs/governance/product-design-contract.md",
        subject="schema",
        path_globs=("schemas/**",),
        severity="advisory",
        required_gates=("schemas",),
        stop_condition="schema_contract_gap",
    ),
    Rule(
        id="starter.governance",
        version=1,
        owner="ethos",
        profile_layers=("generic",),
        authority_ref=".ethos/rules.toml",
        contract_ref="docs/governance/product-design-contract.md",
        subject="governance",
        path_globs=(
            ".ethos/**",
            ".agents/skills/**",
            "rules/**",
            "openspec/**",
        ),
        severity="blocking",
        required_gates=("schemas",),
        stop_condition="governance_rule_gap",
        non_waivable=True,
    ),
    Rule(
        id="starter.assistant-surfaces",
        version=1,
        owner="ethos",
        profile_layers=("generic",),
        authority_ref=".agents/skills/activation.toml",
        contract_ref="docs/governance/playbooks-and-skills.md",
        subject="assistant-surface",
        path_globs=(".agents/skills/**",),
        severity="blocking",
        required_gates=("playbooks-v2",),
        stop_condition="assistant_surface_projection_gap",
        non_waivable=True,
    ),
    Rule(
        id="starter.tooling",
        version=1,
        owner="ethos",
        profile_layers=("generic",),
        authority_ref="pyproject.toml",
        contract_ref="docs/governance/product-design-contract.md",
        subject="tooling",
        path_globs=("pyproject.toml", "uv.lock"),
        severity="advisory",
        required_gates=("schemas",),
        stop_condition="tooling_contract_gap",
    ),
)


def _rule_schema_gaps(rule: dict[str, Any]) -> list[str]:
    validation = validate_schema_instance("rule.schema.json", rule)
    if validation["verdict"] == "pass":
        return []
    return [str(gap) for gap in cast("list[object]", validation["required_gaps"])]


def gate_definitions() -> dict[str, dict[str, object]]:
    """Return executable gates from the repository's single registry owner."""
    return {
        gate_id: {
            "id": gate_id,
            "command": " ".join(gate.command),
            "blocking": gate.policy == "required",
        }
        for gate_id, gate in resolve_gate_policy().registry.items()
    }


def _rule_active_for_profiles(rule: Rule, profile_stack: list[str]) -> bool:
    if not rule.profile_layers:
        return True
    active = set(profile_stack)
    return bool(active.intersection(rule.profile_layers))


def _rules_as_contracts(
    root: Path,
    config: dict[str, Any],
    profile_stack: list[str],
) -> tuple[list[Rule], list[str]]:
    gaps: list[str] = []
    rules: list[Rule] = [
        rule for rule in STARTER_RULES if _rule_active_for_profiles(rule, profile_stack)
    ]
    for raw_rule in configured_rules(root, config=config):
        rule_id = str(raw_rule.get("id", ""))
        schema_gaps = _rule_schema_gaps(raw_rule)
        if schema_gaps:
            gaps.extend(
                f"rule_schema_invalid:{rule_id or '<missing>'}:{gap}" for gap in schema_gaps
            )
            continue
        rule = Rule.model_validate(raw_rule)
        if _rule_active_for_profiles(rule, profile_stack):
            rules.append(rule)
    return rules, gaps


def compile_rules(root: Path) -> dict[str, object]:
    """Compile the deterministic rule set for a repository root."""
    config = load_rules_config(root)
    profile_stack, profile_gaps = resolve_profile_stack(config)
    rules, rule_gaps = _rules_as_contracts(root, config, profile_stack)
    gate_definitions_by_id = gate_definitions()
    gate_gaps = [
        f"unknown_rule_gate:{rule.id}:{gate_id}"
        for rule in rules
        for gate_id in rule.required_gates
        if gate_id not in gate_definitions_by_id
    ]
    compile_gaps = [*profile_gaps, *rule_gaps, *gate_gaps]
    rule_set = RuleSet(
        id="ethos-rules",
        profile_layers=tuple(profile_stack),
        rules=tuple(sorted(rules, key=lambda rule: rule.id)),
    )
    rule_set_payload = rule_set.model_dump(mode="json")
    source_refs = ["product:starter-rules"]
    if rules_path(root).exists():
        source_refs.append(".ethos/rules.toml")
    return {
        "schema_version": 1,
        "profile_stack": profile_stack,
        "coverage_tier": "strict" if STRICT_PROFILE in profile_stack else "starter",
        "rules": rule_set_payload["rules"],
        "source_refs": source_refs,
        "compile_gaps": compile_gaps,
        "gate_definitions": gate_definitions_by_id,
    }
