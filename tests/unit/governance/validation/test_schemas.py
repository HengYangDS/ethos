from __future__ import annotations

import json
import tomllib
from copy import deepcopy
from pathlib import Path

from ethos.repository.policy.coupling.core import coupling_audit_report
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.policy.schema import validate_ethos_result
from ethos.repository.policy.schema import validate_schema_instance
from ethos.result import EthosResult

ROLE_POLICY_SAMPLE = {
    "release_branch": "main",
    "accepted_branch": "dev",
    "candidate_branch": "candidate/dev",
    "work_branch_prefix": "work/",
    "proposal_branch_prefix": "proposal/",
    "release_mirror": "independent",
    "semantic_order": [
        {
            "role": "release_root",
            "kind": "exact_branch",
            "config_key": "release_branch",
            "pattern": "main",
        },
        {
            "role": "accepted_root",
            "kind": "exact_branch",
            "config_key": "accepted_branch",
            "pattern": "dev",
        },
        {
            "role": "candidate",
            "kind": "exact_branch",
            "config_key": "candidate_branch",
            "pattern": "candidate/dev",
        },
        {
            "role": "work_lane",
            "kind": "branch_prefix",
            "config_key": "work_branch_prefix",
            "pattern": "work/*",
        },
        {
            "role": "proposal_lane",
            "kind": "branch_prefix",
            "config_key": "proposal_branch_prefix",
            "pattern": "proposal/*",
        },
    ],
}

_CAMPAIGN_SCHEMA_PAYLOAD = tomllib.loads(
    Path("tests/fixtures/campaign/minimal.toml").read_text(encoding="utf-8")
)


def test_schema_validation_report_covers_all_ethos_schemas() -> None:
    report = schema_validation_report()

    assert report["ok"] is True
    assert report["mode"] == "product"
    assert report["schema_count"] >= 30
    assert report["required_gaps"] == []
    assert report["schemas"]["quality-asset.schema.json"]["ok"] is True
    assert report["schemas"]["quality-gate-plan.schema.json"]["ok"] is True
    assert report["schemas"]["quality-profile.schema.json"]["ok"] is True
    assert report["schemas"]["review-record.schema.json"]["ok"] is True
    assert report["schemas"]["host-capability.schema.json"]["ok"] is True
    assert report["schemas"]["campaign-closeout.schema.json"]["ok"] is True
    assert report["schemas"]["trust-envelope.schema.json"]["ok"] is True
    assert report["schemas"]["promotion-target.schema.json"]["ok"] is True
    assert report["schemas"]["capability-profile.schema.json"]["ok"] is True
    assert report["schemas"]["skill-activation.schema.json"]["ok"] is True
    assert report["schemas"]["skill-registry.schema.json"]["ok"] is True
    assert report["schemas"]["skill-package-manifest.schema.json"]["ok"] is True
    assert report["instances"]["capability-profiles"]["ok"] is True
    assert report["instances"]["evolution-ledger"]["ok"] is True
    assert report["instances"]["docs-registry"]["ok"] is True
    assert report["instances"]["gate-registry"]["ok"] is True
    assert report["instances"]["quality-profile"]["ok"] is True
    assert report["instances"]["quality-gate-plan"]["ok"] is True
    assert report["instances"]["live-skill-activation-contract"]["ok"] is True
    assert report["instances"]["live-skill-registry-contract"]["ok"] is True
    assert report["instances"]["live-skill-package-manifests"]["ok"] is True
    assert report["instances"]["coupling-audit-contract"]["ok"] is True


def test_schema_validation_report_uses_product_schemas_for_adopter_root(
    tmp_path,
) -> None:
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["mode"] == "adopter"
    assert report["ok"] is True
    assert report["schema_count"] >= 24
    assert report["required_gaps"] == []
    assert report["instances"]["docs-registry"]["ok"] is True


def test_schema_validation_adopter_partial_schemas_do_not_replace_product_contracts(
    tmp_path,
) -> None:
    schema_dir = tmp_path / "system" / "schemas" / "kernel"
    schema_dir.mkdir(parents=True)
    (schema_dir / "custom.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["mode"] == "adopter"
    assert report["ok"] is True
    assert report["schema_count"] >= 24
    assert report["instances"]["docs-registry"]["ok"] is True


def test_schema_validation_keeps_adopter_capability_profiles_advisory(
    tmp_path,
) -> None:
    (tmp_path / "docs").mkdir()
    profile_dir = tmp_path / "openspec" / "specs" / "legacy-family"
    profile_dir.mkdir(parents=True)
    (profile_dir / "capability.toml").write_text(
        'family = "legacy-family"\n'
        'owner_object = "legacy-kernel"\n'
        'primary_invariant = "legacy repository owns its own capability profile"\n'
        'routing_question = "Is this adopter capability in scope?"\n'
        'decision_axes = ["adopter_metadata"]\n'
        "\n"
        "[boundary_rules]\n"
        'legacy = "legacy adopter profile shape remains adopter-owned metadata"\n',
        encoding="utf-8",
    )

    report = schema_validation_report(tmp_path)
    profiles = report["instances"]["capability-profiles"]

    assert report["mode"] == "adopter"
    assert report["ok"] is True
    assert profiles["ok"] is True
    assert profiles["required_gaps"] == []
    assert profiles["advisory_gaps"]
    assert "openspec/specs/legacy-family/capability.toml" in profiles["advisory_gaps"][0]


def test_result_payload_validates_against_schema() -> None:
    result = EthosResult(command="status", ok=True, state="ready").to_dict()

    validation = validate_ethos_result(result)

    assert validation["ok"] is True
    json.dumps(validation)


def test_result_payload_accepts_governed_repository_context() -> None:
    result = EthosResult(
        command="status",
        ok=True,
        state="ready",
        governance_context={
            "contract": "governed_repository",
            "profile": "generic",
            "authority": {"id": "repository-authority"},
            "subject": {
                "id": "/workspace/repo",
                "kind": "repository",
                "name": "repo",
                "owner": "ethos",
                "metadata": {},
            },
            "single_kernel": True,
            "kernel_chain": [
                "Authority",
                "Subject",
                "Commitment",
                "Change",
                "Evidence",
                "Claim",
                "Chronicle",
            ],
            "shared_commands": [
                "ethos status",
                "ethos plan",
                "ethos prove",
                "ethos land",
                "ethos publish",
            ],
            "transition_commands": [
                "ethos status",
                "ethos plan",
                "ethos prove",
                "ethos land",
                "ethos publish",
            ],
            "truth_boundary": "repository",
            "profile_boundary": "profile_or_adapter",
        },
    ).to_dict()

    validation = validate_ethos_result(result)

    assert validation["ok"] is True
    json.dumps(validation)


def test_gate_schema_accepts_quality_descriptor_fields() -> None:
    payload = {
        "id": "markdown-links",
        "kind": "docs",
        "command": ["lychee", "--offline", "docs"],
        "policy": "required",
        "profile": "product",
        "toolchain": "quality-adapter",
        "asset_classes": ["markdown-docs"],
        "dimensions": ["links", "anchors"],
        "execution_mode": "adapter",
        "evidence_class": "diagnostic",
        "trust_bearing": False,
        "tool_adapter": "lychee",
        "writes_files": False,
        "network_policy": "offline",
        "version_source": "adopter-toolchain",
        "depends_on": [],
    }

    validation = validate_schema_instance("gate.schema.json", payload)

    assert validation["ok"] is True


def test_campaign_schema_accepts_lane_closeout_steps() -> None:
    assert validate_schema_instance("campaign.schema.json", _CAMPAIGN_SCHEMA_PAYLOAD)["ok"]


def test_campaign_schema_rejects_unknown_publication_mode() -> None:
    payload = deepcopy(_CAMPAIGN_SCHEMA_PAYLOAD)
    payload["publication"] = {"mode": "per_change"}

    validation = validate_schema_instance("campaign.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"] == ["'campaign_terminal' was expected"]


def test_campaign_schema_accepts_archive_ready_preland_step() -> None:
    payload = deepcopy(_CAMPAIGN_SCHEMA_PAYLOAD)
    payload["step"][0]["state"] = "archive_ready"

    assert validate_schema_instance("campaign.schema.json", payload)["ok"] is True


def test_evolution_ledger_schema_requires_structural_entry_refs() -> None:
    payload = {
        "hypothesis": [
            {
                "id": "sample-hypothesis",
                "campaign": "sample",
                "state": "active",
                "owner": "ethos-maintainers",
                "claim": "claim",
                "challenge": "challenge",
                "transition": "shape -> canonize",
                "proof_refs": ["ethos quality evidence-freshness --json"],
                "review_refs": ["tests/unit/governance/test_evolution_ledger.py"],
                "decision_refs": ["docs/governance/evolution-campaign.md"],
                "retirement_conditions": ["refs resolve"],
            }
        ],
        "entry": [
            {
                "id": "structural-entry",
                "type": "experiment",
                "state": "accepted",
                "summary": "A structural evolution record.",
            }
        ],
    }

    validation = validate_schema_instance("evolution-ledger.schema.json", payload)

    assert validation["ok"] is False
    assert any("evidence_refs" in gap for gap in validation["required_gaps"])
    assert any("decision_refs" in gap for gap in validation["required_gaps"])


def test_evolution_ledger_schema_allows_campaign_entries_without_refs() -> None:
    payload = {
        "hypothesis": [
            {
                "id": "sample-hypothesis",
                "campaign": "sample",
                "state": "active",
                "owner": "ethos-maintainers",
                "claim": "claim",
                "challenge": "challenge",
                "transition": "shape -> canonize",
                "proof_refs": ["ethos quality evidence-freshness --json"],
                "review_refs": ["tests/unit/governance/test_evolution_ledger.py"],
                "decision_refs": ["docs/governance/evolution-campaign.md"],
                "retirement_conditions": ["refs resolve"],
            }
        ],
        "entry": [
            {
                "id": "campaign-entry",
                "type": "campaign",
                "state": "active",
                "summary": "A campaign container.",
            }
        ],
    }

    validation = validate_schema_instance("evolution-ledger.schema.json", payload)

    assert validation["ok"] is True


def test_proof_run_schema_uses_trust_bearing_lattice() -> None:
    payload = {
        "action_id": "proof-policy",
        "command": ["ethos", "quality", "proof-policy", "--json"],
        "exit_code": 0,
        "stdout": "{}",
        "stderr": "",
        "state": "proven",
        "evidence_class": "proof",
        "verdict": "passed",
        "trust_bearing": True,
        "diagnostics": [],
        "governance_ref": "",
    }

    validation = validate_schema_instance("proof-run.schema.json", payload)

    assert validation["ok"] is True


def test_proof_run_schema_rejects_proven_without_trust_bearing() -> None:
    payload = {
        "action_id": "claims",
        "command": ["ethos", "quality", "claims", "--json"],
        "exit_code": 0,
        "stdout": "{}",
        "stderr": "",
        "state": "proven",
        "evidence_class": "contract",
        "verdict": "passed",
        "trust_bearing": False,
        "diagnostics": [],
        "governance_ref": "",
    }

    validation = validate_schema_instance("proof-run.schema.json", payload)

    assert validation["ok"] is False


def test_proof_run_schema_rejects_trust_bearing_non_proven_state() -> None:
    payload = {
        "action_id": "claims",
        "command": ["ethos", "quality", "claims", "--json"],
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "state": "planned",
        "evidence_class": "contract",
        "verdict": "not_run",
        "trust_bearing": True,
        "diagnostics": [],
        "governance_ref": "",
    }

    validation = validate_schema_instance("proof-run.schema.json", payload)

    assert validation["ok"] is False


def test_waived_proof_run_schema_requires_governance_reference() -> None:
    payload = {
        "action_id": "waiver",
        "command": ["ethos", "prove"],
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "state": "accepted-risk",
        "evidence_class": "proof",
        "verdict": "accepted",
        "trust_bearing": False,
        "diagnostics": [],
        "governance_ref": "",
    }

    validation = validate_schema_instance("proof-run.schema.json", payload)

    assert validation["ok"] is False


def test_trust_envelope_contract_requires_complete_carriers() -> None:
    valid = {
        "claim_id": "sample-trust",
        "state": "active",
        "boundary": {"owner": "repository", "scope": "governance"},
        "evidence": {
            "dated": "evidence/sample.md",
            "digest_trusted": True,
        },
        "carriers": {
            "openspec": "openspec/changes/sample-change",
        },
        "fallback": "stop promotion and keep prior contract",
        "kill_signal": "required lifecycle carrier missing",
        "promotion": {
            "targets": [
                {
                    "kind": "source",
                    "path": "src/ethos/repository/evidence/claims.py",
                },
                {
                    "kind": "openspec",
                    "path": "openspec/specs/repository-governance/spec.md",
                },
            ],
            "ready": True,
        },
        "required_gaps": [],
    }

    assert validate_schema_instance("trust-envelope.schema.json", valid)["ok"] is True

    malformed = {
        "claim_id": "sample-trust",
        "state": "active",
        "boundary": {"owner": "repository"},
        "evidence": {"dated": "evidence/sample.md"},
        "carriers": {},
        "promotion": {"targets": []},
        "required_gaps": ["sample-trust:carriers.openspec_missing"],
    }

    validation = validate_schema_instance("trust-envelope.schema.json", malformed)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_promotion_target_contract_rejects_provider_paths() -> None:
    valid = {
        "kind": "evidence",
        "path": "evidence/sample.md",
        "description": "dated evidence promoted into repository truth",
    }

    assert validate_schema_instance("promotion-target.schema.json", valid)["ok"] is True

    validation = validate_schema_instance(
        "promotion-target.schema.json",
        {"kind": "gitlab", "path": "https://example.invalid/merge_requests/1"},
    )

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_capability_profile_contract_validates_boundary_and_proof_metadata() -> None:
    valid = {
        "family": "ethos-repository",
        "owner": {
            "package": "ethos-repository",
            "scope": "repository lifecycle governance",
        },
        "primary_invariant": "repository truth is promoted through claims and evidence",
        "routing_question": "Does this change alter repository trust admission?",
        "decision_axes": ["lifecycle", "surface", "authority"],
        "boundary_rules": [
            "OpenSpec records are specification carriers, not truth owners",
            "adopter-specific terms stay in profiles or evidence",
        ],
        "recommended_facets": {
            "lifecycle": ["authoring", "validation", "archive"],
            "surface": ["docs", "openspec", "schema"],
            "authority": ["docs", "openspec", "claim", "evidence"],
        },
        "proof_profile": {
            "default_command": "ethos prove --json",
            "executed_command": "ethos prove --execute --json",
            "required_gates": ["claims", "schemas"],
        },
    }

    assert validate_schema_instance("capability-profile.schema.json", valid)["ok"] is True

    validation = validate_schema_instance(
        "capability-profile.schema.json",
        {
            "family": "ethos-repository",
            "owner": {"package": "ethos-repository"},
            "proof_profile": {"default_command": "ethos prove --json"},
        },
    )

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_coupling_audit_payload_validates_binding_registry_contract() -> None:
    validation = validate_schema_instance(
        "coupling-audit.schema.json",
        coupling_audit_report(Path.cwd()),
    )

    assert validation["ok"] is True
    json.dumps(validation)


def test_coupling_audit_schema_rejects_ui_projection_fields() -> None:
    payload = coupling_audit_report(Path.cwd())
    payload["binding_registry"][0]["open_label"] = "Open Worktree"

    validation = validate_schema_instance("coupling-audit.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_schema_instance_validation_reports_data_gaps() -> None:
    validation = validate_schema_instance(
        "evolution-ledger.schema.json",
        {"hypothesis": [{"id": "x", "campaign": "c", "state": "active"}]},
    )

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_schema_validation_uses_product_schemas_for_adopter_without_local_schemas(
    tmp_path,
) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "project.toml").write_text("[meta]\nname = 'sample'\n", encoding="utf-8")
    (tmp_path / "docs" / "current").mkdir(parents=True)
    (tmp_path / "docs" / "current" / "README.md").write_text(
        "---\nsubject: docs:governance\nrole: reference\nstate: canonical\nrelations: test\n---\n"
        "# Governance Docs\n",
        encoding="utf-8",
    )

    report = schema_validation_report(tmp_path)

    assert report["ok"] is True
    assert report["mode"] == "adopter"
    assert report["schema_count"] >= 19
    assert report["instances"]["docs-registry"]["ok"] is True
