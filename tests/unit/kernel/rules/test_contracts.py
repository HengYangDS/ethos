from __future__ import annotations

from ethos.repository.policy.schema import validate_schema_instance
from ethos.testing.fixtures import normalized_rule_shadow_fixtures
from ethos.testing.fixtures import rules_conformance_profiles
from ethos_core.contracts.rules import PolicyException
from ethos_core.contracts.rules import Rule
from ethos_core.contracts.rules import RuleAttestation
from ethos_core.contracts.rules import RuleEvalRequest
from ethos_core.contracts.rules import RuleSet


def test_rule_contract_schemas_validate_minimal_payloads() -> None:
    rule = {
        "id": "starter.docs",
        "owner": "ethos",
        "authority_ref": "docs/start/quickstart.md",
        "contract_ref": "docs/start/quickstart.md",
        "path_globs": ["docs/**"],
        "severity": "advisory",
        "required_gates": ["docs-registry"],
        "stop_condition": "docs_registry_drift",
    }
    rule_set = {
        "schema_version": 1,
        "id": "starter",
        "profile_layers": ["generic"],
        "rules": [rule],
    }
    fact_snapshot = (
        RuleEvalRequest(
            phase="plan",
            changed_paths=("docs/index.md",),
        )
        .to_fact_snapshot(head="untracked")
        .to_dict()
    )
    evaluation = {
        "schema_version": 1,
        "state": "allow",
        "head": "untracked",
        "rule_set_digest": "0" * 64,
        "compiled_policy_digest": "0" * 64,
        "source_refs": ["product:starter-rules"],
        "fact_snapshot_digest": fact_snapshot["digest"],
        "input_snapshot": fact_snapshot,
        "decisions": [],
        "obligations": [],
        "required_gates": [],
        "evidence_requirements": [],
        "required_gaps": [],
        "digest": "1" * 64,
    }
    surface_coverage = {
        "ok": True,
        "coverage_tier": "starter",
        "covered_paths": ["docs/index.md"],
        "uncovered_paths": [],
        "matched_rules": [],
        "required_gaps": [],
    }
    rule_report = {
        "ok": True,
        "coverage_ok": True,
        "depth_ok": True,
        "exceptions_ok": True,
        "evidence_freshness_ok": True,
        "drift_ok": True,
        "required_gaps": [],
    }
    policy_exception = PolicyException(
        id="docs-waiver",
        rule_id="starter.docs",
        scope="repository",
        owner="ethos",
        approver="maintainer",
        reason="temporary docs migration",
        evidence_ref="evidence/example.md",
        created_at="2026-07-01",
        expires_at="2026-07-31",
    ).to_dict()
    attestation = RuleAttestation(
        head="untracked",
        evaluation_digest="1" * 64,
        rule_set_digest="0" * 64,
        compiled_policy_digest="0" * 64,
        fact_snapshot_digest=fact_snapshot["digest"],
        actor="local",
        scope="repository",
        runner_identity="ethos",
        input=fact_snapshot,
        output={"state": "allow", "required_gaps": [], "required_gates": []},
    ).to_dict()

    assert validate_schema_instance("rule.schema.json", rule)["ok"] is True
    assert validate_schema_instance("rule-set.schema.json", rule_set)["ok"] is True
    assert validate_schema_instance("rule-evaluation.schema.json", evaluation)["ok"] is True
    assert validate_schema_instance("surface-coverage.schema.json", surface_coverage)["ok"]
    assert validate_schema_instance("rule-report.schema.json", rule_report)["ok"] is True
    assert validate_schema_instance("policy-exception.schema.json", policy_exception)["ok"]
    assert validate_schema_instance("rule-fact-snapshot.schema.json", fact_snapshot)["ok"]
    assert validate_schema_instance("rule-attestation.schema.json", attestation)["ok"]


def test_rule_contract_schema_rejects_missing_owner() -> None:
    payload = {
        "schema_version": 1,
        "id": "bad",
        "profile_layers": ["generic"],
        "rules": [
            {
                "id": "starter.docs",
                "authority_ref": "docs/start/quickstart.md",
                "contract_ref": "docs/start/quickstart.md",
                "path_globs": ["docs/**"],
                "severity": "advisory",
                "required_gates": ["docs-registry"],
                "stop_condition": "docs_registry_drift",
            }
        ],
    }

    validation = validate_schema_instance("rule-set.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_conformance_profiles_include_starter_and_strict_shapes() -> None:
    profiles = rules_conformance_profiles()

    assert {
        "generic",
        "python",
        "monorepo",
        "github",
        "gitlab",
        "legacy-v1",
        "custom",
        "strict",
        "reference-strict",
    } <= set(profiles)
    for profile_name in ("generic", "python", "monorepo", "custom"):
        profile = profiles[profile_name]
        assert profile["strict"] is False
        assert profile["requires_openspec"] is False
        assert profile["requires_hosted_ci"] is False
        assert profile["requires_backlog"] is False
        assert profile["requires_product_openspec_family"] is False
    assert profiles["strict"]["strict"] is True
    assert profiles["python"]["files"][".ethos/rules.toml"].startswith("[profiles]")


def test_normalized_rule_shadow_fixtures_cover_reference_repositories() -> None:
    fixtures = normalized_rule_shadow_fixtures()

    assert {"ethos", "reference-legacy", "sample-effect"} == set(fixtures)
    for fixture in fixtures.values():
        report = fixture["report"]
        stages = fixture["stages"]
        assert {"ok", "profile_stack", "coverage_tier", "required_gap_kinds"} <= set(report)
        assert {
            "contracts-evaluator",
            "pep-no-side-effect",
            "strict-coverage",
        } <= set(stages)
    assert fixtures["reference-legacy"]["report"]["required_gap_kinds"] == ["rule_schema_invalid"]


def test_contract_dataclasses_serialize_to_schema_payloads() -> None:
    rule = Rule(
        id="custom.docs",
        owner="docs-team",
        authority_ref="docs/governance/docs.md",
        contract_ref="docs/governance/docs.md",
        path_globs=("docs/**",),
        severity="advisory",
        required_gates=("docs-registry",),
        stop_condition="docs_gap",
    )
    rule_set = RuleSet(id="custom", profile_layers=("generic",), rules=(rule,))
    request = RuleEvalRequest(phase="plan", changed_paths=("docs/index.md",))

    assert validate_schema_instance("rule-set.schema.json", rule_set.to_dict())["ok"]
    assert request.to_fact_snapshot(head="abc123").to_dict()["facts"]["changed_paths"]["value"] == [
        "docs/index.md"
    ]
