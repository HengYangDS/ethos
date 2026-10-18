"""Compiled-policy core: assemble a deterministic RuleSet from config and starter rules."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from pydantic import ValidationError

from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.rules import Rule
from ethos.contracts.rules import RuleSet
from ethos.repository.policy.gates import resolve_gate_declaration
from ethos.repository.policy.gates import resolve_gate_policy
from ethos.repository.policy.rules.config import configured_rules
from ethos.repository.policy.rules.config import load_rules_config
from ethos.repository.policy.rules.config import resolve_profile_stack
from ethos.repository.policy.rules.config import rules_path
from ethos.repository.policy.schema import validate_schema_instance
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path
    from typing import Any

    from ethos.contracts.gates import Gate
    from ethos.repository.policy.gates import ResolvedGatePolicy

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
        contract_ref="docs/governance/skills.md",
        subject="assistant-surface",
        path_globs=(".agents/skills/**",),
        severity="blocking",
        required_gates=("skills",),
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


def _gate_policy(root: Path, *, rules: list[Rule]) -> ResolvedGatePolicy:
    """Observe the selected registry once for native ownership and executable demand."""
    profile = load_repository_profile(root)
    registry_path = profile.declaration.proof.gate_registry if profile.declaration else None
    registry_source = None
    if registry_path:
        path = profile.root / registry_path
        try:
            if not path.is_symlink() and path.resolve(strict=True).is_relative_to(profile.root):
                registry_source = path.read_bytes()
        except (OSError, RuntimeError, ValueError):
            pass  # The native resolver rejects an unavailable declared registry.
    declaration, _profile = resolve_gate_declaration(profile, gate_registry_source=registry_source)
    native_ids = declaration.registry().keys()
    reusable = {
        gate.id
        for gate in load_gate_registry_declaration().gates
        if gate.providers and not gate.command
    }
    product_ids = tuple(
        dict.fromkeys(
            gate_id
            for rule in rules
            for gate_id in rule.required_gates
            if rule in STARTER_RULES or (gate_id not in native_ids and gate_id in reusable)
        )
    )
    requested = tuple(
        dict.fromkeys(
            gate_id
            for rule in rules
            for gate_id in rule.required_gates
            if gate_id in native_ids or gate_id in product_ids
        )
    )
    return resolve_gate_policy(
        profile=profile,
        gate_registry_source=registry_source,
        gate_ids=requested,
        product_gate_ids=product_ids,
    )


def _definitions(registry: Mapping[str, Gate], *, source: str) -> dict[str, dict[str, object]]:
    return {
        gate_id: {
            "id": gate_id,
            "gate_source": source,
            "command": " ".join(gate.command),
            "blocking": gate.policy == "required",
        }
        for gate_id, gate in registry.items()
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
    policy = _gate_policy(root, rules=rules)
    native_registry = policy.registry
    native = _definitions(
        native_registry,
        source="repository" if policy.profile and policy.profile.declaration else "product",
    )
    product_registry = {
        gate.id: gate for gate in policy.gates if gate.id in policy.product_gate_ids
    }
    product = _definitions(product_registry, source="product")
    native_sources = (
        {gate.id: gate for gate in policy.profile.declaration.proof.gates}
        if policy.profile is not None
        and policy.profile.declaration is not None
        and not policy.profile.declaration.proof.gate_registry
        else policy.declaration.registry()
    )
    product_sources = load_gate_registry_declaration().registry()
    gate_definitions_by_id = native | product
    gate_gaps = [
        f"unknown_rule_gate:{rule.id}:{gate_id}"
        for rule in rules
        for gate_id in rule.required_gates
        if gate_id not in gate_definitions_by_id
    ]
    origin_gaps = [
        f"rule_gate_origin_conflict:{rule.id}:{gate_id}"
        for rule in rules
        if rule not in STARTER_RULES
        and policy.profile is not None
        and policy.profile.declaration is not None
        for gate_id in rule.required_gates
        if gate_id in native
        and gate_id in product
        and native_sources[gate_id] != product_sources[gate_id]
    ]
    compile_gaps = [*profile_gaps, *rule_gaps, *gate_gaps, *origin_gaps]
    try:
        rule_set = RuleSet(
            id="ethos-rules",
            profile_layers=tuple(profile_stack),
            rules=tuple(sorted(rules, key=lambda rule: rule.id)),
        )
    except ValidationError as error:
        compile_gaps.extend(
            str(detail.get("ctx", {}).get("error", detail["msg"])) for detail in error.errors()
        )
        rule_set = RuleSet(id="ethos-rules", profile_layers=tuple(profile_stack), rules=())
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
