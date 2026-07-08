from __future__ import annotations

from pathlib import Path

from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.check import rules_layer_report
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.coverage import coverage_report
from ethos.repository.policy.rules.evaluation import rules_evaluation_report
from ethos.repository.policy.rules.exceptions import policy_exceptions_report
from ethos.repository.policy.rules.exceptions import rules_docs_manifest_report
from ethos.repository.policy.rules.migration import migrate_legacy_rules
from ethos.repository.policy.schema import validate_schema_instance
from ethos.testing.fixtures import normalized_rule_shadow_fixtures
from ethos.testing.fixtures import rules_conformance_profiles
from ethos_core.contracts.rules import PolicyException
from ethos_core.contracts.rules import Rule
from ethos_core.contracts.rules import RuleAttestation
from ethos_core.contracts.rules import RuleEvalRequest
from ethos_core.contracts.rules import RuleFactSnapshot
from ethos_core.contracts.rules import RuleSet
from ethos_core.contracts.rules import rule_attestation_gaps


def _complete_snapshot(
    *,
    phase: str = "plan",
    changed_paths: tuple[str, ...] = (),
    mutation: bool = False,
    authorized: bool = False,
) -> RuleFactSnapshot:
    return RuleFactSnapshot(
        phase=phase,
        head="untracked",
        facts={
            "changed_paths": {
                "owner": "ethos-adapters",
                "fresh": True,
                "available": True,
                "value": list(changed_paths),
            },
            "mutation": {
                "owner": "ethos-cli",
                "fresh": True,
                "available": True,
                "value": mutation,
            },
            "authorization": {
                "owner": "ethos-cli",
                "fresh": True,
                "available": True,
                "value": authorized,
            },
            "actor": {
                "owner": "ethos-cli",
                "fresh": True,
                "available": True,
                "value": "local",
            },
            "scope": {
                "owner": "ethos-cli",
                "fresh": True,
                "available": True,
                "value": "repository",
            },
            "worktree": {
                "owner": "ethos-adapters.status",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "prewrite": {
                "owner": "ethos-adapters.prewrite",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "openspec_state": {
                "owner": "ethos-repository.self-audit",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "claim_state": {
                "owner": "ethos-repository.claims",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "evidence_freshness": {
                "owner": "ethos-repository.claims",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "stale": []},
            },
            "host_readiness": {
                "owner": "ethos-repository.self-audit",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "command_registry": {
                "owner": "ethos-repository.command-registry",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
            "projection_drift": {
                "owner": "ethos-assistants.projections",
                "fresh": True,
                "available": True,
                "value": {"ok": True, "required_gaps": []},
            },
        },
    )


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


def test_rules_check_passes_for_starter_profile(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        '[profiles]\nactive = ["generic"]\n',
        encoding="utf-8",
    )

    report = rules_check_report(tmp_path)

    assert report["ok"] is True
    assert report["coverage_tier"] == "starter"
    assert report["required_gaps"] == []
    assert report["profile_stack"] == ["generic"]


def test_rules_check_blocks_malformed_and_invalid_config(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    rules_path.write_text('[profiles\nactive = ["generic"]\n', encoding="utf-8")

    malformed = rules_check_report(tmp_path)

    assert malformed["ok"] is False
    assert "rules_config_parse_error" in malformed["required_gaps"][0]

    rules_path.write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "bad"
path_globs = []
severity = "fatal"
required_gates = []
authority_ref = ".ethos/rules.toml"
contract_ref = ".ethos/rules.toml"
stop_condition = "bad_rule"
""".lstrip(),
        encoding="utf-8",
    )

    invalid = rules_check_report(tmp_path)

    assert invalid["ok"] is False
    assert any(gap.startswith("rule_schema_invalid:bad:") for gap in invalid["required_gaps"])


def test_legacy_v1_rules_normalize_to_canonical_rule_ir(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[[rule]]
id = "legacy.docs"
risk = "docs_drift"
paths = ["docs/**"]
requires = ["docs-registry"]
evidence = ["docs evidence"]
""".lstrip(),
        encoding="utf-8",
    )

    compiled = compile_rules(tmp_path)
    coverage = coverage_report(tmp_path, changed_paths=("docs/index.md",))

    assert not [
        gap for gap in compiled["compile_gaps"] if str(gap).startswith("rule_schema_invalid")
    ]
    legacy_rule = next(rule for rule in compiled["rules"] if rule["id"] == "legacy.docs")
    assert legacy_rule["owner"] == "repo-local"
    assert legacy_rule["authority_ref"] == ".ethos/rules.toml"
    assert legacy_rule["contract_ref"] == ".ethos/rules.toml"
    assert legacy_rule["subject"] == "docs_drift"
    assert legacy_rule["severity"] == "advisory"
    assert legacy_rule["stop_condition"] == "docs_drift"
    assert legacy_rule["path_globs"] == ["docs/**"]
    assert legacy_rule["required_gates"] == ["docs-registry"]
    assert legacy_rule["evidence_requirements"] == ["docs evidence"]
    assert any(match["rule_id"] == "legacy.docs" for match in coverage["matched_rules"])


def test_compile_rules_is_deterministic(tmp_path: Path) -> None:
    first = compile_rules(tmp_path)
    second = compile_rules(tmp_path)

    assert first["compiled_policy_digest"] == second["compiled_policy_digest"]
    assert first["rule_set_digest"] == second["rule_set_digest"]
    assert first["rules"]


def test_coverage_report_names_uncovered_paths(tmp_path: Path) -> None:
    report = coverage_report(tmp_path, changed_paths=("unknown/file.xyz",))

    assert report["ok"] is False
    assert report["uncovered_paths"] == ["unknown/file.xyz"]
    assert report["next_action_contract"]
    assert "ethos rules migrate --dry-run" not in report["next_action_contract"]


def test_starter_docs_cover_package_and_distribution_readmes(tmp_path: Path) -> None:
    report = coverage_report(
        tmp_path,
        changed_paths=(
            "packages/ethos-core/README.md",
            "distributions/npm/README.md",
        ),
    )

    assert report["ok"] is True
    assert report["uncovered_paths"] == []
    assert {match["rule_id"] for match in report["matched_rules"]} == {"starter.docs"}


def test_rule_evaluation_blocks_missing_authorization_for_publish(tmp_path: Path) -> None:
    report = rules_evaluation_report(
        tmp_path,
        phase="publish",
        changed_paths=(),
        mutation=True,
        authorized=False,
    )

    assert report["state"] == "block"
    assert "authorization_required" in report["required_gaps"]
    assert report["decisions"][0]["decision"] == "block"


def test_rule_evaluation_uses_authorization_fact_over_arguments(tmp_path: Path) -> None:
    snapshot = _complete_snapshot(phase="publish", mutation=True, authorized=False)

    report = rules_evaluation_report(
        tmp_path,
        phase="publish",
        mutation=True,
        authorized=True,
        fact_snapshot=snapshot,
    )

    assert report["state"] == "block"
    assert "authorization_required" in report["required_gaps"]


def test_rule_evaluation_uses_fact_snapshot_and_fail_closed_inputs(tmp_path: Path) -> None:
    missing_fact = RuleFactSnapshot(
        phase="plan",
        head="untracked",
        facts={
            "changed_paths": {
                "owner": "ethos-adapters",
                "fresh": True,
                "available": False,
                "value": [],
            }
        },
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        fact_snapshot=missing_fact,
    )

    assert report["state"] == "block"
    assert report["fact_snapshot_digest"] == missing_fact.digest
    assert "fact_unavailable:changed_paths" in report["required_gaps"]
    assert report["source_refs"]


def test_rule_evaluation_blocks_incomplete_fact_snapshot(tmp_path: Path) -> None:
    snapshot = RuleFactSnapshot(phase="plan", head="untracked", facts={})

    report = rules_evaluation_report(tmp_path, phase="plan", fact_snapshot=snapshot)

    assert report["state"] == "block"
    assert "fact_missing:changed_paths" in report["required_gaps"]
    assert "fact_missing:prewrite" in report["required_gaps"]


def test_rule_eval_request_snapshot_requires_prewrite_source_fact(
    tmp_path: Path,
) -> None:
    snapshot = RuleEvalRequest(
        phase="publish",
        changed_paths=("README.md",),
        mutation=True,
        authorized=True,
    ).to_fact_snapshot(head="abc123")

    report = rules_evaluation_report(tmp_path, phase="publish", fact_snapshot=snapshot)

    assert "prewrite" in snapshot.facts
    assert "fact_unavailable:prewrite" in report["required_gaps"]


def test_rule_evaluation_blocks_timeout_nondeterminism_and_conflicts(
    tmp_path: Path,
) -> None:
    snapshot = RuleFactSnapshot(
        phase="plan",
        head="untracked",
        facts={
            "changed_paths": {
                "owner": "ethos-adapters",
                "fresh": True,
                "available": True,
                "value": [],
            },
            "adapter": {
                "owner": "ethos-adapters",
                "fresh": False,
                "available": False,
                "value": {"timeout": True},
            },
            "compiler": {
                "owner": "ethos-repository",
                "fresh": True,
                "available": True,
                "value": {"deterministic": False},
            },
            "merge": {
                "owner": "ethos-repository",
                "fresh": True,
                "available": True,
                "value": {"unresolved_conflicts": ["rules/a.toml"]},
            },
        },
    )

    report = rules_evaluation_report(tmp_path, phase="plan", fact_snapshot=snapshot)

    assert report["state"] == "block"
    assert "fact_unavailable:adapter" in report["required_gaps"]
    assert "fact_stale:adapter" in report["required_gaps"]
    assert "fact_timeout:adapter" in report["required_gaps"]
    assert "fact_nondeterministic:compiler" in report["required_gaps"]
    assert "fact_unresolved_conflicts:merge" in report["required_gaps"]


def test_rule_evaluation_blocks_embedded_source_fact_gaps(tmp_path: Path) -> None:
    snapshot = RuleFactSnapshot(
        phase="prove",
        head="untracked",
        facts={
            "changed_paths": {
                "owner": "ethos-adapters",
                "fresh": True,
                "available": True,
                "value": [],
            },
            "claim_state": {
                "owner": "ethos-repository.claims",
                "fresh": True,
                "available": True,
                "value": {
                    "ok": False,
                    "required_gaps": ["claim_digest_mismatch:rules"],
                },
            },
            "evidence_freshness": {
                "owner": "ethos-repository.claims",
                "fresh": True,
                "available": True,
                "value": {
                    "ok": False,
                    "stale": ["evidence/rules.md"],
                },
            },
        },
    )

    report = rules_evaluation_report(tmp_path, phase="prove", fact_snapshot=snapshot)

    assert report["state"] == "block"
    assert "fact_required_gap:claim_state:claim_digest_mismatch:rules" in report["required_gaps"]
    assert "fact_not_ok:evidence_freshness" in report["required_gaps"]
    assert "fact_stale_ref:evidence_freshness:evidence/rules.md" in report["required_gaps"]


def test_rule_evaluation_blocks_worktree_gaps_for_publish(tmp_path: Path) -> None:
    snapshot = _complete_snapshot(phase="publish")
    snapshot.facts["worktree"]["value"] = {
        "ok": False,
        "required_gaps": ["protected_root_mutation"],
    }

    report = rules_evaluation_report(tmp_path, phase="publish", fact_snapshot=snapshot)

    assert report["state"] == "block"
    assert "fact_required_gap:worktree:protected_root_mutation" in report["required_gaps"]


def test_inactive_profile_rule_does_not_affect_generic_evaluation(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "strict.docs"
owner = "docs-team"
profile_layers = ["strict"]
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["notes/**"]
severity = "blocking"
required_gates = ["docs-registry"]
stop_condition = "strict_docs_gap"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        changed_paths=("notes/todo.md",),
        fact_snapshot=_complete_snapshot(changed_paths=("notes/todo.md",)),
    )

    assert "strict.docs" not in report["effective_rules"]
    assert "rules_uncovered_path:notes/todo.md" in report["required_gaps"]
    assert not any("strict.docs" in gap for gap in report["required_gaps"])


def test_blocking_rule_required_gate_is_enforced(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "custom.docs"
owner = "docs-team"
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["notes/**"]
severity = "blocking"
required_gates = ["docs-registry"]
stop_condition = "docs_gap"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        changed_paths=("notes/todo.md",),
        fact_snapshot=_complete_snapshot(changed_paths=("notes/todo.md",)),
    )

    assert report["state"] == "block"
    assert "gate_required:custom.docs:docs-registry" in report["required_gaps"]
    assert {
        "id": "docs-registry",
        "kind": "require_gate",
        "scope": "repository",
        "actor": "local",
        "blocking": True,
    } in report["obligations"]
    assert validate_schema_instance("rule-evaluation.schema.json", report)["ok"]


def test_rule_layer_does_not_hide_depth_or_exception_gaps(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["strict"]
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_layer_report(tmp_path)

    assert report["ok"] is False
    assert report["depth_ok"] is False
    assert set(report["depth_tiers"]) == {
        "subject",
        "contract",
        "transition",
        "evidence",
        "stop",
    }
    assert report["depth_tiers"]["subject"] is True
    assert report["depth_tiers"]["contract"] is False
    assert "rules_strict_subject_coverage_missing" in report["required_gaps"]


def test_rules_docs_manifest_reports_missing_rule_doc_refs(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "custom.docs"
owner = "docs-team"
authority_ref = "docs/missing-authority.md"
contract_ref = "docs/missing-contract.md"
path_globs = ["docs/**"]
severity = "advisory"
required_gates = []
stop_condition = "docs_missing"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_docs_manifest_report(tmp_path)
    layer = rules_layer_report(tmp_path)

    assert report["ok"] is False
    assert report["generated_from"] == "compiled-rules"
    assert "missing_doc_ref:docs/missing-authority.md" in report["required_gaps"]
    assert layer["docs_manifest_ok"] is False
    assert "rules_docs_manifest:missing_doc_ref:docs/missing-contract.md" in layer["required_gaps"]


def test_policy_exceptions_validate_required_owner_scope_ttl_and_digest(tmp_path: Path) -> None:
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        """
[[exception]]
id = "expired"
rule_id = "starter.docs"
scope = "repository"
owner = "ethos"
approver = "maintainer"
reason = "temporary"
evidence_ref = "evidence/example.md"
created_at = "2026-01-01"
expires_at = "2026-01-03"
status = "active"
max_ttl = "1d"
digest = "0"
""".lstrip(),
        encoding="utf-8",
    )

    report = policy_exceptions_report(tmp_path, today="2026-07-01")

    assert report["ok"] is False
    assert "policy_exception_expired:expired" in report["required_gaps"]
    assert "policy_exception_digest_mismatch:expired" in report["required_gaps"]
    assert "policy_exception_ttl_exceeded:expired" in report["required_gaps"]
    assert (
        "policy_exception_evidence_missing:expired:evidence/example.md" in report["required_gaps"]
    )


def test_policy_exceptions_block_invalid_dates_and_non_waivable_rules(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence" / "example.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("evidence\n", encoding="utf-8")
    invalid_date = PolicyException(
        id="invalid-date",
        rule_id="starter.docs",
        scope="repository",
        owner="ethos",
        approver="maintainer",
        reason="temporary",
        evidence_ref="evidence/example.md",
        created_at="2026-07-01",
        expires_at="never",
    ).to_dict()
    non_waivable = PolicyException(
        id="non-waivable",
        rule_id="starter.governance",
        scope="repository",
        owner="ethos",
        approver="maintainer",
        reason="temporary",
        evidence_ref="evidence/example.md",
        created_at="2026-07-01",
        expires_at="2026-07-31",
    ).to_dict()
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        f"""
[[exception]]
id = "invalid-date"
rule_id = "starter.docs"
scope = "repository"
owner = "ethos"
approver = "maintainer"
reason = "temporary"
evidence_ref = "evidence/example.md"
created_at = "2026-07-01"
expires_at = "never"
status = "active"
digest = "{invalid_date["digest"]}"

[[exception]]
id = "non-waivable"
rule_id = "starter.governance"
scope = "repository"
owner = "ethos"
approver = "maintainer"
reason = "temporary"
evidence_ref = "evidence/example.md"
created_at = "2026-07-01"
expires_at = "2026-07-02"
status = "active"
digest = "{non_waivable["digest"]}"
""".lstrip(),
        encoding="utf-8",
    )

    report = policy_exceptions_report(tmp_path, today="2026-07-01")

    assert report["ok"] is False
    assert "policy_exception_date_invalid:invalid-date:expires_at" in report["required_gaps"]
    assert (
        "policy_exception_non_waivable_rule:non-waivable:starter.governance"
        in report["required_gaps"]
    )


def test_policy_exceptions_block_empty_path_scope(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence" / "example.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("evidence\n", encoding="utf-8")
    invalid_scope = PolicyException(
        id="empty-path",
        rule_id="starter.docs",
        scope="path:",
        owner="ethos",
        approver="maintainer",
        reason="temporary",
        evidence_ref="evidence/example.md",
        created_at="2026-07-01",
        expires_at="2026-07-31",
    ).to_dict()
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        f"""
[[exception]]
id = "empty-path"
rule_id = "starter.docs"
scope = "path:"
owner = "ethos"
approver = "maintainer"
reason = "temporary"
evidence_ref = "evidence/example.md"
created_at = "2026-07-01"
expires_at = "2026-07-02"
status = "active"
digest = "{invalid_scope["digest"]}"
""".lstrip(),
        encoding="utf-8",
    )

    report = policy_exceptions_report(tmp_path, today="2026-07-01")

    assert report["ok"] is False
    assert "policy_exception_scope_invalid:empty-path" in report["required_gaps"]


def test_valid_policy_exception_waives_scoped_blocking_rule(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "custom.docs"
owner = "docs-team"
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["notes/**"]
severity = "blocking"
required_gates = ["docs-registry"]
stop_condition = "docs_gap"
""".lstrip(),
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence" / "exception.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("temporary waiver\n", encoding="utf-8")
    waiver = PolicyException(
        id="docs-waiver",
        rule_id="custom.docs",
        scope="path:notes/",
        owner="docs-team",
        approver="maintainer",
        reason="temporary docs gate migration",
        evidence_ref="evidence/exception.md",
        created_at="2026-07-01",
        expires_at="2026-07-31",
    ).to_dict()
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        f"""
[[exception]]
id = "docs-waiver"
rule_id = "custom.docs"
scope = "path:notes/"
owner = "docs-team"
approver = "maintainer"
reason = "temporary docs gate migration"
evidence_ref = "evidence/exception.md"
created_at = "2026-07-01"
expires_at = "2026-07-31"
status = "active"
digest = "{waiver["digest"]}"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        changed_paths=("notes/todo.md",),
        fact_snapshot=_complete_snapshot(changed_paths=("notes/todo.md",)),
    )

    assert report["state"] == "advisory"
    assert "gate_required:custom.docs:docs-registry" not in report["required_gaps"]
    assert report["waivers_applied"] == [
        {
            "id": "docs-waiver",
            "rule_id": "custom.docs",
            "scope": "path:notes/",
            "waived_gaps": ["gate_required:custom.docs:docs-registry"],
        }
    ]
    assert validate_schema_instance("rule-evaluation.schema.json", report)["ok"]


def test_policy_exception_path_scope_respects_path_boundaries(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "custom.docs"
owner = "docs-team"
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["docs2/**"]
severity = "blocking"
required_gates = ["docs-registry"]
stop_condition = "docs_gap"
""".lstrip(),
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence" / "exception.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("temporary waiver\n", encoding="utf-8")
    waiver = PolicyException(
        id="docs-waiver",
        rule_id="custom.docs",
        scope="path:docs",
        owner="docs-team",
        approver="maintainer",
        reason="temporary docs gate migration",
        evidence_ref="evidence/exception.md",
        created_at="2026-07-01",
        expires_at="2026-07-02",
    ).to_dict()
    exceptions = tmp_path / "rules" / "ethos" / "policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text(
        f"""
[[exception]]
id = "docs-waiver"
rule_id = "custom.docs"
scope = "path:docs"
owner = "docs-team"
approver = "maintainer"
reason = "temporary docs gate migration"
evidence_ref = "evidence/exception.md"
created_at = "2026-07-01"
expires_at = "2026-07-31"
status = "active"
digest = "{waiver["digest"]}"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        changed_paths=("docs2/a.md",),
        fact_snapshot=_complete_snapshot(changed_paths=("docs2/a.md",)),
    )

    assert report["state"] == "block"
    assert report["waivers_applied"] == []
    assert "gate_required:custom.docs:docs-registry" in report["required_gaps"]


def test_legacy_rules_migration_is_dry_run(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        '[formats]\nuser_config = "TOML"\n',
        encoding="utf-8",
    )

    report = migrate_legacy_rules(tmp_path)

    assert report["ok"] is True
    assert report["legacy_detected"] is True
    assert report["applied"] is False
    assert (
        "ethos rules migrate --apply --authorize --expect-head <git-head>" in report["next_actions"]
    )


def test_v2_rules_with_gate_definitions_are_not_legacy(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[gates.custom]
command = "ethos quality schemas --json"
blocking = true
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_check_report(tmp_path)

    assert report["legacy"]["legacy_detected"] is False
    assert report["legacy"]["has_v2_rules"] is True


def test_legacy_rules_migration_preserves_rule_semantics(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    rules_path.write_text(
        """
[[rule]]
id = "legacy.docs"
risk = "docs_drift"
paths = ["docs/**"]
requires = ["docs-registry"]
evidence = ["docs evidence"]
""".lstrip(),
        encoding="utf-8",
    )

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is True
    assert report["legacy_detected"] is True
    assert report["applied"] is True
    assert report["target"]["rule"]
    written = rules_path.read_text(encoding="utf-8")
    assert 'id = "legacy.docs"' in written
    assert 'path_globs = ["docs/**"]' in written
    assert 'required_gates = ["docs-registry"]' in written


def test_legacy_rules_migration_preserves_profiles_and_custom_gates(
    tmp_path: Path,
) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    rules_path.write_text(
        """
[profiles]
active = ["python"]

[gates.unit]
command = "uv run pytest -q"
blocking = true

[[rule]]
id = "legacy.src"
risk = "source_regression"
paths = ["src/**"]
requires = ["unit"]
evidence = ["unit test output"]
""".lstrip(),
        encoding="utf-8",
    )
    before = rules_check_report(tmp_path)
    assert before["ok"] is True

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is True
    assert report["target"]["profiles"]["active"] == ["generic", "python"]
    assert report["target"]["gates"]["unit"]["command"] == "uv run pytest -q"
    written = rules_path.read_text(encoding="utf-8")
    assert "[gates.unit]" in written
    assert 'command = "uv run pytest -q"' in written
    assert "blocking = true" in written
    after = rules_check_report(tmp_path)
    assert after["ok"] is True
    assert "unknown_rule_gate:legacy.src:unit" not in after["required_gaps"]


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


def test_rule_attestation_verifier_detects_tampering() -> None:
    evaluation = rules_evaluation_report(Path(), phase="plan", head="abc123")
    attestation = RuleAttestation(
        head=str(evaluation["head"]),
        evaluation_digest=str(evaluation["digest"]),
        rule_set_digest=str(evaluation["rule_set_digest"]),
        compiled_policy_digest=str(evaluation["compiled_policy_digest"]),
        fact_snapshot_digest=str(evaluation["fact_snapshot_digest"]),
        actor="local",
        scope="repository",
        runner_identity="ethos",
        input=dict(evaluation["input_snapshot"]),
        output={
            "state": evaluation["state"],
            "required_gaps": evaluation["required_gaps"],
            "required_gates": evaluation["required_gates"],
        },
    ).to_dict()

    assert rule_attestation_gaps(attestation, evaluation) == ()

    tampered = {**attestation, "evaluation_digest": "0" * 64, "head": "stale"}

    assert rule_attestation_gaps(tampered, evaluation) == (
        "rule_attestation_mismatch:head",
        "rule_attestation_mismatch:evaluation_digest",
    )

    tampered_input = {
        **attestation,
        "input": {**dict(attestation["input"]), "phase": "publish"},
    }
    assert "rule_attestation_mismatch:input_digest" in rule_attestation_gaps(
        tampered_input,
        evaluation,
    )

    tampered_output = {
        **attestation,
        "output": {
            **dict(attestation["output"]),
            "required_gaps": ["hidden"],
        },
    }
    assert "rule_attestation_mismatch:output_required_gaps" in rule_attestation_gaps(
        tampered_output,
        evaluation,
    )
