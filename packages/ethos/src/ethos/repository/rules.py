from __future__ import annotations

import fnmatch
import tomllib
from datetime import date
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.gates import gate_registry
from ethos.repository.schema_validation import validate_schema_instance
from ethos_core.contracts.rules import PolicyException
from ethos_core.contracts.rules import Rule
from ethos_core.contracts.rules import RuleEvalRequest
from ethos_core.contracts.rules import RuleFactSnapshot
from ethos_core.contracts.rules import RuleSet
from ethos_core.contracts.rules import stable_digest

if TYPE_CHECKING:
    from pathlib import Path

VALID_PHASES = {"plan", "prewrite", "prove", "land", "publish"}
STRICT_PROFILE = "strict"
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

STARTER_RULES: tuple[Rule, ...] = (
    Rule(
        id="starter.docs",
        version=1,
        owner="ethos",
        profile_layers=("generic",),
        authority_ref="docs/start/quickstart.md",
        contract_ref="docs/governance/docs-registry.md",
        subject="docs",
        path_globs=(
            "docs/**",
            "README.md",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "packages/*/README.md",
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
        contract_ref="docs/architecture/package-ontology.md",
        subject="source",
        path_globs=("packages/**/*.py", "tests/**/*.py", "src/**/*.py"),
        severity="advisory",
        required_gates=("unit-architecture",),
        stop_condition="python_test_gap",
    ),
    Rule(
        id="starter.schemas",
        version=1,
        owner="ethos",
        profile_layers=("generic",),
        authority_ref="schemas/ethos",
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
        path_globs=(".ethos/**", ".agents/skills/**", "claims/**", "rules/**", "openspec/**"),
        severity="blocking",
        required_gates=("schemas",),
        evidence_requirements=("rule-evaluation",),
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
        evidence_requirements=("rule-evaluation",),
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
        path_globs=("pyproject.toml", "packages/*/pyproject.toml", "uv.lock"),
        severity="advisory",
        required_gates=("schemas",),
        stop_condition="tooling_contract_gap",
    ),
)


def _rules_path(root: Path) -> Path:
    return root / ".ethos" / "rules.toml"


def _load_rules_config(root: Path) -> dict[str, Any]:
    path = _rules_path(root)
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {"_parse_error": str(exc)}


def _normalize_profile(profile: str) -> str:
    if profile == "python-package":
        return "python"
    return profile


def _profile_stack(root: Path) -> list[str]:
    config = _load_rules_config(root)
    profiles = config.get("profiles")
    if isinstance(profiles, dict) and isinstance(profiles.get("active"), list):
        normalized = [_normalize_profile(str(item)) for item in profiles["active"]]
        stack = list(dict.fromkeys(normalized)) or ["generic"]
        if "generic" not in stack:
            stack.insert(0, "generic")
        return stack
    workspace = root / ".ethos" / "workspace.toml"
    if workspace.exists():
        return ["generic"]
    return ["generic"]


def _configured_rules(root: Path) -> list[dict[str, Any]]:
    config = _load_rules_config(root)
    rules = config.get("rule")
    if not isinstance(rules, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in rules:
        if not isinstance(item, dict):
            normalized.append({"id": "", "_invalid": "rule_not_table"})
            continue
        legacy_rule = _is_legacy_rule_item(item)
        path_globs = item.get("path_globs", item.get("paths"))
        required_gates = item.get("required_gates", item.get("requires"))
        evidence_requirements = item.get("evidence_requirements", item.get("evidence", []))
        payload: dict[str, Any] = {}
        for key in (
            "id",
            "owner",
            "authority_ref",
            "contract_ref",
            "subject",
            "severity",
            "stop_condition",
        ):
            if key in item:
                payload[key] = item[key]
        if legacy_rule:
            rule_id = str(item.get("id") or "legacy-rule")
            risk = str(item.get("risk") or rule_id.replace(".", "_"))
            payload.setdefault("id", rule_id)
            payload.setdefault("owner", "repo-local")
            payload.setdefault("authority_ref", ".ethos/rules.toml")
            payload.setdefault("contract_ref", ".ethos/rules.toml")
            payload.setdefault("subject", risk)
            payload.setdefault("severity", "advisory")
            payload.setdefault("stop_condition", risk)
        raw_version = item.get("version", 1)
        payload["version"] = int(raw_version) if str(raw_version).isdigit() else raw_version
        payload["profile_layers"] = (
            [str(layer) for layer in item.get("profile_layers", [])]
            if isinstance(item.get("profile_layers"), list)
            else []
        )
        if isinstance(path_globs, list):
            payload["path_globs"] = [str(path) for path in path_globs]
        if isinstance(required_gates, list):
            payload["required_gates"] = [str(gate) for gate in required_gates]
        if isinstance(evidence_requirements, list) and evidence_requirements:
            payload["evidence_requirements"] = [str(req) for req in evidence_requirements]
        if "non_waivable" in item:
            payload["non_waivable"] = bool(item["non_waivable"])
        normalized.append(payload)
    return normalized


def _is_legacy_rule_item(item: dict[str, Any]) -> bool:
    return bool({"risk", "paths", "requires", "evidence"}.intersection(item))


def _rule_schema_gaps(rule: dict[str, Any]) -> list[str]:
    validation = validate_schema_instance("rule.schema.json", rule)
    return [str(gap) for gap in validation["required_gaps"]] if not validation["ok"] else []


def _gate_definitions(root: Path) -> dict[str, dict[str, object]]:
    definitions = {
        gate_id: {
            "id": gate_id,
            "command": " ".join(gate.command),
            "blocking": gate.policy == "required",
        }
        for gate_id, gate in gate_registry().items()
    }
    config = _load_rules_config(root)
    configured = config.get("gates") if isinstance(config.get("gates"), dict) else {}
    for gate_id, gate in configured.items():
        if not isinstance(gate, dict):
            continue
        definitions[str(gate_id)] = {
            "id": str(gate_id),
            "command": str(gate.get("command", "")),
            "blocking": gate.get("blocking", True) is not False,
        }
    return definitions


def _rule_active_for_profiles(rule: Rule, profile_stack: list[str]) -> bool:
    if not rule.profile_layers:
        return True
    active = set(profile_stack)
    return bool(active.intersection(rule.profile_layers))


def _rules_as_contracts(root: Path, profile_stack: list[str]) -> tuple[list[Rule], list[str]]:
    gaps: list[str] = []
    rules: list[Rule] = [
        rule for rule in STARTER_RULES if _rule_active_for_profiles(rule, profile_stack)
    ]
    for raw_rule in _configured_rules(root):
        rule_id = str(raw_rule.get("id", ""))
        schema_gaps = _rule_schema_gaps(raw_rule)
        if schema_gaps:
            gaps.extend(
                f"rule_schema_invalid:{rule_id or '<missing>'}:{gap}" for gap in schema_gaps
            )
            continue
        rule = Rule(
            id=str(raw_rule["id"]),
            version=int(raw_rule.get("version", 1)),
            owner=str(raw_rule["owner"]),
            profile_layers=tuple(str(layer) for layer in raw_rule.get("profile_layers", [])),
            authority_ref=str(raw_rule["authority_ref"]),
            contract_ref=str(raw_rule["contract_ref"]),
            subject=str(raw_rule.get("subject", "")),
            path_globs=tuple(str(path) for path in raw_rule["path_globs"]),
            severity=str(raw_rule["severity"]),
            required_gates=tuple(str(gate) for gate in raw_rule["required_gates"]),
            evidence_requirements=tuple(
                str(req) for req in raw_rule.get("evidence_requirements", [])
            ),
            stop_condition=str(raw_rule["stop_condition"]),
            non_waivable=bool(raw_rule.get("non_waivable", False)),
        )
        if _rule_active_for_profiles(rule, profile_stack):
            rules.append(rule)
    return rules, gaps


def compile_rules(root: Path) -> dict[str, object]:
    profile_stack = _profile_stack(root)
    rules, compile_gaps = _rules_as_contracts(root, profile_stack)
    rule_set = RuleSet(
        id="ethos-rules",
        profile_layers=tuple(profile_stack),
        rules=tuple(sorted(rules, key=lambda rule: rule.id)),
    )
    rule_set_payload = rule_set.to_dict()
    rule_set_digest = rule_set.digest
    source_refs = ["product:starter-rules"]
    if _rules_path(root).exists():
        source_refs.append(".ethos/rules.toml")
    compiled_policy = {
        "rule_set_digest": rule_set_digest,
        "profiles": profile_stack,
        "source_refs": source_refs,
    }
    return {
        "schema_version": 1,
        "profile_stack": profile_stack,
        "coverage_tier": "strict" if STRICT_PROFILE in profile_stack else "starter",
        "rules": rule_set_payload["rules"],
        "rule_set_digest": rule_set_digest,
        "compiled_policy_digest": stable_digest(compiled_policy),
        "source_refs": source_refs,
        "compile_gaps": compile_gaps,
        "gate_definitions": _gate_definitions(root),
    }


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def coverage_report(root: Path, *, changed_paths: tuple[str, ...] = ()) -> dict[str, object]:
    compiled = compile_rules(root)
    covered_paths: list[str] = []
    uncovered_paths: list[str] = []
    matched_rules: list[dict[str, object]] = []
    gate_definitions = {
        str(gate_id): dict(gate)
        for gate_id, gate in dict(compiled["gate_definitions"]).items()
        if isinstance(gate, dict)
    }
    rules = [rule for rule in compiled["rules"] if isinstance(rule, dict)]
    for path in changed_paths:
        path_matches = [
            rule
            for rule in rules
            if _matches(path, [str(pattern) for pattern in rule.get("path_globs", [])])
        ]
        if path_matches:
            covered_paths.append(path)
            for rule in path_matches:
                matched_rules.append(
                    {
                        "path": path,
                        "rule_id": rule["id"],
                        "owner": rule["owner"],
                        "subject": rule.get("subject", ""),
                        "authority_ref": rule["authority_ref"],
                        "contract_ref": rule["contract_ref"],
                        "severity": rule["severity"],
                        "required_gates": list(rule.get("required_gates", [])),
                        "required_gates_detail": [
                            gate_definitions.get(
                                str(gate),
                                {"id": str(gate), "command": "", "blocking": True},
                            )
                            for gate in rule.get("required_gates", [])
                        ],
                        "evidence_requirements": list(rule.get("evidence_requirements", [])),
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
        else ["ethos rules explain <path>", "ethos rules migrate --apply"],
    }


def rules_check_report(root: Path) -> dict[str, object]:
    config = _load_rules_config(root)
    compiled = compile_rules(root)
    legacy = _legacy_state(root)
    required_gaps: list[str] = []
    if "_parse_error" in config:
        required_gaps.append(f"rules_config_parse_error:{config['_parse_error']}")
    required_gaps.extend(str(gap) for gap in compiled["compile_gaps"])
    rule_ids: set[str] = set()
    gate_definitions = dict(compiled["gate_definitions"])
    for rule in compiled["rules"]:
        if not isinstance(rule, dict):
            continue
        rule_id = str(rule.get("id", ""))
        if rule_id in rule_ids:
            required_gaps.append(f"duplicate_rule_id:{rule_id}")
        rule_ids.add(rule_id)
        if not rule.get("owner"):
            required_gaps.append(f"rule_missing_owner:{rule_id}")
        for gate in rule.get("required_gates", []):
            if str(gate) not in gate_definitions:
                required_gaps.append(f"unknown_rule_gate:{rule_id}:{gate}")
    return {
        "ok": not required_gaps,
        "profile_stack": compiled["profile_stack"],
        "coverage_tier": compiled["coverage_tier"],
        "strict_enabled_source": "profile" if compiled["coverage_tier"] == "strict" else "",
        "resolved_rules": [rule["id"] for rule in compiled["rules"] if isinstance(rule, dict)],
        "rule_set_digest": compiled["rule_set_digest"],
        "compiled_policy_digest": compiled["compiled_policy_digest"],
        "source_refs": compiled["source_refs"],
        "legacy": legacy,
        "required_gaps": required_gaps,
        "next_action_contract": []
        if not required_gaps
        else ["ethos rules explain <gap>", "ethos rules migrate --apply"],
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


def _fact_gaps(snapshot: RuleFactSnapshot) -> list[str]:
    gaps: list[str] = []
    for name in REQUIRED_CORE_FACTS:
        if name not in snapshot.facts:
            gaps.append(f"fact_missing:{name}")
    for name, fact in snapshot.facts.items():
        if not isinstance(fact, dict):
            gaps.append(f"fact_malformed:{name}")
            continue
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
        gaps.extend(_fact_value_gaps(phase=snapshot.phase, name=name, value=value))
    return gaps


def _scope_matches_path(scope: str, path: str) -> bool:
    if scope == "repository":
        return True
    if not scope.startswith("path:"):
        return False
    prefix = scope.removeprefix("path:").strip("/")
    if not prefix:
        return False
    normalized = path.strip("/")
    return normalized == prefix or normalized.startswith(f"{prefix}/")


def _active_valid_exceptions(exceptions: dict[str, object]) -> list[dict[str, object]]:
    if exceptions["required_gaps"]:
        return []
    active: list[dict[str, object]] = []
    for item in exceptions["exceptions"]:
        if isinstance(item, dict) and item.get("status") == "active":
            active.append(item)
    return active


def _match_waiver(
    *,
    rule_id: str,
    path: str,
    exceptions: list[dict[str, object]],
) -> dict[str, object] | None:
    for exception in exceptions:
        if exception.get("rule_id") != rule_id:
            continue
        scope = str(exception.get("scope", ""))
        if _scope_matches_path(scope, path):
            return exception
    return None


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
) -> dict[str, object]:
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
        source_refs=tuple(str(ref) for ref in compiled["source_refs"]),
    )
    mutation = bool(_fact_value(snapshot, "mutation", mutation))
    authorized = bool(_fact_value(snapshot, "authorization", authorized))
    actor = str(_fact_value(snapshot, "actor", actor))
    scope = str(_fact_value(snapshot, "scope", scope))
    snapshot_paths = tuple(str(path) for path in _fact_value(snapshot, "changed_paths", []))
    coverage = coverage_report(root, changed_paths=snapshot_paths)
    check = rules_check_report(root)
    exceptions = policy_exceptions_report(root)
    required_gaps: list[str] = []
    waivers_applied: list[dict[str, object]] = []
    if phase not in VALID_PHASES:
        required_gaps.append(f"invalid_rule_phase:{phase}")
    required_gaps.extend(str(gap) for gap in check["required_gaps"])
    required_gaps.extend(_fact_gaps(snapshot))
    required_gaps.extend(str(gap) for gap in coverage["required_gaps"])
    required_gaps.extend(f"policy_exception:{gap}" for gap in exceptions["required_gaps"])
    if mutation and phase in {"land", "publish"} and not authorized:
        required_gaps.append("authorization_required")
    valid_exceptions = _active_valid_exceptions(exceptions)
    blocking_obligations: list[dict[str, object]] = []
    for match in coverage["matched_rules"]:
        if not match.get("blocking"):
            continue
        rule_id = str(match.get("rule_id", ""))
        path = str(match.get("path", ""))
        match_gaps: list[str] = []
        if phase != "prove":
            match_gaps.extend(
                f"gate_required:{rule_id}:{gate}" for gate in match.get("required_gates", [])
            )
        if phase in {"land", "publish"}:
            match_gaps.extend(
                f"evidence_required:{rule_id}:{evidence}"
                for evidence in match.get("evidence_requirements", [])
            )
        waiver = None
        if not match.get("non_waivable"):
            waiver = _match_waiver(rule_id=rule_id, path=path, exceptions=valid_exceptions)
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
        for gate in match.get("required_gates", []):
            blocking_obligations.append(
                {
                    "id": str(gate),
                    "kind": "require_gate",
                    "scope": scope,
                    "actor": actor,
                    "blocking": True,
                }
            )
        for evidence in match.get("evidence_requirements", []):
            blocking_obligations.append(
                {
                    "id": str(evidence),
                    "kind": "require_evidence",
                    "scope": scope,
                    "actor": actor,
                    "blocking": True,
                }
            )
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
        if gap.startswith("authorization_required"):
            obligations.append(
                {
                    "id": "authorization",
                    "kind": "require_authorization",
                    "scope": scope,
                    "actor": actor,
                    "blocking": True,
                }
            )
        if gap.startswith("gate_required:"):
            parts = gap.split(":", 2)
            obligations.append(
                {
                    "id": parts[-1],
                    "kind": "require_gate",
                    "scope": scope,
                    "actor": actor,
                    "blocking": True,
                }
            )
        if gap.startswith("evidence_required:"):
            parts = gap.split(":", 2)
            obligations.append(
                {
                    "id": parts[-1],
                    "kind": "require_evidence",
                    "scope": scope,
                    "actor": actor,
                    "blocking": True,
                }
            )
    obligations.extend(blocking_obligations)
    deduped_gaps = list(dict.fromkeys(required_gaps))
    matched = list(coverage["matched_rules"])
    state = "block" if deduped_gaps else ("advisory" if matched else "allow")
    evaluation_base = {
        "schema_version": 1,
        "state": state,
        "head": snapshot.head,
        "rule_set_digest": compiled["rule_set_digest"],
        "compiled_policy_digest": compiled["compiled_policy_digest"],
        "source_refs": list(compiled["source_refs"]),
        "fact_snapshot_digest": snapshot.digest,
        "input_snapshot": snapshot.to_dict(),
        "surface_matches": matched,
        "effective_rules": [rule["id"] for rule in compiled["rules"] if isinstance(rule, dict)],
        "decisions": decisions,
        "obligations": list(_dedupe_records(obligations)),
        "required_gates": sorted(
            {str(gate) for match in matched for gate in match.get("required_gates", [])}
        ),
        "required_gates_detail": _required_gate_details(matched),
        "evidence_requirements": sorted(
            {str(req) for match in matched for req in match.get("evidence_requirements", [])}
        ),
        "stops": [gap.split(":", 1)[0] for gap in deduped_gaps],
        "waivers_applied": waivers_applied,
        "required_gaps": deduped_gaps,
        "next_action_contract": []
        if not deduped_gaps
        else ["ethos rules explain <gap>", "ethos prove --json"],
    }
    return {**evaluation_base, "digest": stable_digest(evaluation_base)}


def _required_gate_details(matches: list[dict[str, object]]) -> list[dict[str, object]]:
    details: dict[str, dict[str, object]] = {}
    for match in matches:
        for gate in match.get("required_gates_detail", []):
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


def rules_layer_report(root: Path) -> dict[str, object]:
    check = rules_check_report(root)
    exceptions = policy_exceptions_report(root)
    docs_manifest = rules_docs_manifest_report(root)
    required_gaps = list(check["required_gaps"])
    required_gaps.extend(f"policy_exception:{gap}" for gap in exceptions["required_gaps"])
    required_gaps.extend(f"rules_docs_manifest:{gap}" for gap in docs_manifest["required_gaps"])
    strict = check["coverage_tier"] == "strict"
    subjects = {
        str(rule.get("subject", ""))
        for rule in compile_rules(root)["rules"]
        if isinstance(rule, dict)
    }
    depth_tiers = {
        "subject": any(subjects),
        "contract": "contract" in subjects,
        "transition": "transition" in subjects,
        "evidence": "evidence" in subjects,
        "stop": "stop" in subjects,
    }
    depth_gaps: list[str] = []
    if strict:
        missing = sorted(
            subject
            for subject in ("contract", "transition", "evidence", "stop")
            if not depth_tiers[subject]
        )
        if missing:
            depth_gaps.append("rules_strict_subject_coverage_missing")
            depth_gaps.extend(f"rules_strict_missing_subject:{subject}" for subject in missing)
    required_gaps.extend(depth_gaps)
    coverage_ok = not check["required_gaps"]
    depth_ok = not depth_gaps
    exceptions_ok = bool(exceptions["ok"])
    docs_manifest_ok = bool(docs_manifest["ok"])
    evidence_freshness_ok = not any("evidence" in gap for gap in required_gaps)
    drift_ok = not any("digest_mismatch" in gap for gap in required_gaps)
    return {
        "ok": (
            coverage_ok
            and depth_ok
            and exceptions_ok
            and docs_manifest_ok
            and evidence_freshness_ok
            and drift_ok
        ),
        "coverage_ok": coverage_ok,
        "depth_ok": depth_ok,
        "exceptions_ok": exceptions_ok,
        "docs_manifest_ok": docs_manifest_ok,
        "evidence_freshness_ok": evidence_freshness_ok,
        "drift_ok": drift_ok,
        "strict": strict,
        "depth_tiers": depth_tiers,
        "required_gaps": list(dict.fromkeys(required_gaps)),
        "check": check,
        "exceptions": exceptions,
        "docs_manifest": docs_manifest,
    }


def _legacy_state(root: Path) -> dict[str, object]:
    config = _load_rules_config(root)
    if not config:
        return {"legacy_detected": False}
    legacy_keys = {"formats", "artifacts", "determinism", "standards", "gates"}
    rules = config.get("rule")
    legacy_rule_items = isinstance(rules, list) and any(
        isinstance(item, dict) and _is_legacy_rule_item(item) for item in rules
    )
    has_v2_rules = isinstance(config.get("profiles"), dict) or (
        isinstance(rules, list) and not legacy_rule_items
    )
    return {
        "legacy_detected": (
            legacy_rule_items or (bool(legacy_keys.intersection(config)) and not has_v2_rules)
        ),
        "has_v2_rules": has_v2_rules,
        "legacy_rule_items": legacy_rule_items,
    }


def migrate_legacy_rules(root: Path, *, apply: bool = False) -> dict[str, object]:
    legacy = _legacy_state(root)
    target_profiles = {"active": _profile_stack(root)}
    target_gates = _configured_gate_tables(root)
    target_rules = _configured_rules(root)
    target_text = _rules_toml_text(
        target_rules,
        profiles=target_profiles,
        gates=target_gates,
    )
    target: dict[str, object] = {"profiles": target_profiles, "rule": target_rules}
    if target_gates:
        target["gates"] = target_gates
    if apply and legacy["legacy_detected"]:
        path = _rules_path(root)
        path.write_text(target_text, encoding="utf-8")
    return {
        "ok": True,
        "legacy_detected": bool(legacy["legacy_detected"]),
        "applied": bool(apply and legacy["legacy_detected"]),
        "target": target,
        "target_text": target_text,
        "required_gaps": [],
        "next_actions": (
            ["ethos rules migrate --apply --authorize --expect-head <git-head>"]
            if legacy["legacy_detected"] and not apply
            else []
        ),
    }


def _configured_gate_tables(root: Path) -> dict[str, dict[str, object]]:
    config = _load_rules_config(root)
    configured = config.get("gates") if isinstance(config.get("gates"), dict) else {}
    gates: dict[str, dict[str, object]] = {}
    for gate_id, gate in configured.items():
        if not isinstance(gate, dict):
            continue
        payload: dict[str, object] = {}
        if "command" in gate:
            payload["command"] = str(gate["command"])
        if "blocking" in gate:
            payload["blocking"] = gate["blocking"] is not False
        if payload:
            gates[str(gate_id)] = payload
    return gates


def _rules_toml_text(
    rules: list[dict[str, Any]],
    *,
    profiles: dict[str, object] | None = None,
    gates: dict[str, dict[str, object]] | None = None,
) -> str:
    active_profiles = (
        profiles.get("active")
        if isinstance(profiles, dict) and isinstance(profiles.get("active"), list)
        else ["generic"]
    )
    lines = ["[profiles]", f"active = {_toml_string_array(active_profiles)}", ""]
    for gate_id, gate in sorted((gates or {}).items()):
        lines.append(f"[gates.{_toml_table_key(gate_id)}]")
        for key in ("command", "blocking"):
            if key in gate:
                lines.append(f"{key} = {_toml_value(gate[key])}")
        lines.append("")
    for rule in rules:
        if not rule.get("id"):
            continue
        lines.append("[[rule]]")
        for key in (
            "id",
            "owner",
            "authority_ref",
            "contract_ref",
            "subject",
            "severity",
            "stop_condition",
        ):
            value = rule.get(key)
            if isinstance(value, str) and value:
                lines.append(f'{key} = "{_toml_escape(value)}"')
        version = rule.get("version")
        if isinstance(version, int) and version != 1:
            lines.append(f"version = {version}")
        for key in (
            "profile_layers",
            "path_globs",
            "required_gates",
            "evidence_requirements",
        ):
            value = rule.get(key)
            if isinstance(value, list):
                lines.append(f"{key} = {_toml_string_array(value)}")
        if "non_waivable" in rule:
            lines.append(f"non_waivable = {str(bool(rule['non_waivable'])).lower()}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _toml_string_array(values: list[Any]) -> str:
    return "[" + ", ".join(f'"{_toml_escape(str(value))}"' for value in values) + "]"


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return _toml_string_array(value)
    return f'"{_toml_escape(str(value))}"'


def _toml_table_key(value: str) -> str:
    if value.replace("_", "-").replace("-", "").isalnum():
        return value
    return f'"{_toml_escape(value)}"'


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _exceptions_path(root: Path) -> Path:
    return root / "rules" / "ethos" / "policy-exceptions.toml"


def policy_exceptions_report(root: Path, *, today: str | None = None) -> dict[str, object]:
    path = _exceptions_path(root)
    if not path.exists():
        return {
            "ok": True,
            "owner": "rules/ethos/policy-exceptions.toml",
            "exceptions": [],
            "required_gaps": [],
        }
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {
            "ok": False,
            "owner": "rules/ethos/policy-exceptions.toml",
            "exceptions": [],
            "required_gaps": [f"policy_exception_parse_error:{exc}"],
        }
    exceptions = payload.get("exception", [])
    if not isinstance(exceptions, list):
        exceptions = []
    known_rules = {
        str(rule.get("id")): rule
        for rule in compile_rules(root)["rules"]
        if isinstance(rule, dict) and rule.get("id")
    }
    known_rule_ids = set(known_rules)
    today_date = _date_or_none(today or date.today().isoformat())
    normalized: list[dict[str, object]] = []
    gaps: list[str] = []
    for item in exceptions:
        if not isinstance(item, dict):
            gaps.append("policy_exception_malformed")
            continue
        record = {
            "id": str(item.get("id", "")),
            "rule_id": str(item.get("rule_id", "")),
            "scope": str(item.get("scope", "")),
            "owner": str(item.get("owner", "")),
            "approver": str(item.get("approver", "")),
            "reason": str(item.get("reason", "")),
            "evidence_ref": str(item.get("evidence_ref", "")),
            "created_at": str(item.get("created_at", "")),
            "expires_at": str(item.get("expires_at", "")),
            "status": str(item.get("status", "")),
            "digest": str(item.get("digest", "")),
        }
        if item.get("max_ttl"):
            record["max_ttl"] = str(item["max_ttl"])
        validation = validate_schema_instance("policy-exception.schema.json", record)
        if not validation["ok"]:
            gaps.extend(
                f"policy_exception_schema_invalid:{record['id']}:{gap}"
                for gap in validation["required_gaps"]
            )
        expected = PolicyException(
            id=str(record["id"]),
            rule_id=str(record["rule_id"]),
            scope=str(record["scope"]),
            owner=str(record["owner"]),
            approver=str(record["approver"]),
            reason=str(record["reason"]),
            evidence_ref=str(record["evidence_ref"]),
            created_at=str(record["created_at"]),
            expires_at=str(record["expires_at"]),
            status=str(record["status"]),
            max_ttl=str(record.get("max_ttl", "")),
        ).to_dict()["digest"]
        if record["digest"] != expected:
            gaps.append(f"policy_exception_digest_mismatch:{record['id']}")
        if record["rule_id"] not in known_rule_ids:
            gaps.append(f"policy_exception_unknown_rule:{record['id']}:{record['rule_id']}")
        elif bool(known_rules[str(record["rule_id"])].get("non_waivable", False)):
            gaps.append(f"policy_exception_non_waivable_rule:{record['id']}:{record['rule_id']}")
        scope_value = str(record["scope"])
        if (scope_value != "repository" and not scope_value.startswith("path:")) or (
            scope_value.startswith("path:") and not scope_value.removeprefix("path:").strip("/")
        ):
            gaps.append(f"policy_exception_scope_invalid:{record['id']}")
        evidence_ref = str(record["evidence_ref"])
        if evidence_ref and not (root / evidence_ref).exists():
            gaps.append(f"policy_exception_evidence_missing:{record['id']}:{evidence_ref}")
        created_at = _date_or_none(str(record["created_at"]))
        expires_at = _date_or_none(str(record["expires_at"]))
        if created_at is None:
            gaps.append(f"policy_exception_date_invalid:{record['id']}:created_at")
        if expires_at is None:
            gaps.append(f"policy_exception_date_invalid:{record['id']}:expires_at")
        max_ttl = str(record.get("max_ttl", ""))
        if max_ttl:
            ttl_days = _ttl_days_or_none(max_ttl)
            if ttl_days is None:
                gaps.append(f"policy_exception_ttl_invalid:{record['id']}")
            elif (
                created_at is not None
                and expires_at is not None
                and (expires_at - created_at).days > ttl_days
            ):
                gaps.append(f"policy_exception_ttl_exceeded:{record['id']}")
        if (
            record["status"] == "active"
            and expires_at is not None
            and today_date is not None
            and expires_at < today_date
        ):
            gaps.append(f"policy_exception_expired:{record['id']}")
        normalized.append({**record, "expected_digest": expected})
    return {
        "ok": not gaps,
        "owner": "rules/ethos/policy-exceptions.toml",
        "exceptions": normalized,
        "required_gaps": list(dict.fromkeys(gaps)),
    }


def rules_docs_manifest_report(root: Path) -> dict[str, object]:
    product_root = _is_product_root(root)
    refs = sorted(
        {
            str(ref)
            for rule in compile_rules(root)["rules"]
            if isinstance(rule, dict) and (product_root or rule.get("owner") != "ethos")
            for ref in (rule.get("authority_ref"), rule.get("contract_ref"))
            if isinstance(ref, str) and ref.endswith(".md")
        }
    )
    missing = [ref for ref in refs if not (root / ref).exists()]
    return {
        "ok": not missing,
        "generated_from": "compiled-rules",
        "refs": refs,
        "missing": missing,
        "required_gaps": [f"missing_doc_ref:{ref}" for ref in missing],
    }


def _is_product_root(root: Path) -> bool:
    return (root / "packages" / "ethos" / "README.md").exists() and (
        root / "schemas" / "ethos"
    ).exists()


def explain_rules_target(root: Path, target: str) -> dict[str, object]:
    compiled = compile_rules(root)
    rules = [rule for rule in compiled["rules"] if isinstance(rule, dict)]
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
            "minimal_rule_skeleton": _minimal_rule_skeleton(path),
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
        "minimal_rule_skeleton": {}
        if coverage["matched_rules"]
        else _minimal_rule_skeleton(target),
    }


def _date_or_none(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _ttl_days_or_none(value: str) -> int | None:
    if not value.endswith("d"):
        return None
    raw = value.removesuffix("d")
    if not raw.isdigit():
        return None
    return int(raw)


def _minimal_rule_skeleton(path: str) -> dict[str, object]:
    return {
        "id": "custom.example",
        "owner": "team",
        "authority_ref": "docs/governance/example.md",
        "contract_ref": "docs/governance/example.md",
        "path_globs": [path] if path else [],
        "severity": "advisory",
        "required_gates": [],
        "stop_condition": "custom_rule_gap",
    }
