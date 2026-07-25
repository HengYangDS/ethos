# ruff: noqa: TC003, FLY002
from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos_core.contracts.system.contracts as system_contracts
from ethos_core.contracts import rules
from ethos_core.contracts.branch.roles import strict_branch_role_policy_from_text
from ethos_core.contracts.package.ontology import workspace_package_config_report
from ethos_core.state.invalid import UNCLASSIFIED
from ethos_core.state.invalid import classify
from ethos_core.state.invalid import invalid_state_categories


def test_system_contracts_report_exposes_missing_invalid_schema_and_validation_gaps(
    tmp_path: Path,
) -> None:
    system = tmp_path / "system"
    system.mkdir()
    (system / "authority.toml").write_text(
        'schema = "system/schemas/authority.json"\n', encoding="utf-8"
    )
    (system / "formats.toml").write_text("not = [\n", encoding="utf-8")
    (system / "routing.toml").write_text(
        'schema = "system/schemas/routing.json"\nvalue = 1\n', encoding="utf-8"
    )
    schema_dir = system / "schemas"
    schema_dir.mkdir()
    (schema_dir / "routing.json").write_text(
        json.dumps({"type": "object", "required": ["missing"]}), encoding="utf-8"
    )

    report = system_contracts.system_contracts_report(tmp_path)

    assert report["ok"] is False
    gaps = report["required_gaps"]
    assert "system_schema_ref_missing:authority:system/schemas/authority.json" in gaps
    assert any(str(gap).startswith("system_contract_invalid:formats:") for gap in gaps)
    assert any("system_contract_schema_violation:routing" in str(gap) for gap in gaps)
    assert "system_contract_missing:tools" in gaps
    assert report["contracts"]["authority"] is True
    assert report["contracts"]["formats"] is False


def test_load_system_contract_returns_payload(tmp_path: Path) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "tools.toml").write_text(
        'schema = "x"\nname = "tools"\n', encoding="utf-8"
    )

    assert system_contracts.load_system_contract(tmp_path, "tools")["name"] == "tools"


def test_strict_branch_role_policy_rejects_unknown_release_mirror() -> None:
    source = """
[branch_roles]
release_branch = "main"
accepted_branch = "dev"
candidate_branch = "candidate/dev"
work_branch_prefix = "work/"
submit_branch_prefix = "submit/"
release_mirror = "unknown"
repository_family_worktrees = false
"""

    with pytest.raises(ValueError, match="branch_roles release_mirror is invalid"):
        strict_branch_role_policy_from_text(source)


def test_workspace_package_config_report_edges(tmp_path: Path) -> None:
    assert workspace_package_config_report(tmp_path)["ok"] is True
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "workspace.toml").write_text("[[package]\n", encoding="utf-8")
    assert str(workspace_package_config_report(tmp_path)["required_gaps"][0]).startswith(
        "workspace_config_invalid_toml:"
    )
    (tmp_path / ".ethos" / "workspace.toml").write_text(
        "\n".join(
            [
                "[[package]]",
                'name = "ethos-kernel"',
                'path = "packages/ethos-kernel"',
                "[[package]]",
                'name = "surprise"',
                'path = "packages/surprise"',
            ]
        ),
        encoding="utf-8",
    )
    gaps = workspace_package_config_report(tmp_path)["required_gaps"]
    assert "workspace_config_retired_product_family:ethos-kernel" in gaps
    assert "workspace_config_missing_target:ethos-core" in gaps
    assert "workspace_config_missing_target:ethos" in gaps
    assert "workspace_config_unexpected_package:surprise" in gaps


def test_rule_attestation_gaps_cover_match_and_mismatch() -> None:
    snapshot = (
        rules.RuleEvalRequest(
            phase="prewrite",
            changed_paths=("README.md",),
            mutation=True,
            actor="agent",
            scope="repo",
        )
        .to_fact_snapshot(head="h1", source_refs=("status",))
        .to_dict()
    )
    evaluation = {
        "head": "h1",
        "digest": "eval-digest",
        "rule_set_digest": "rule-digest",
        "compiled_policy_digest": "policy-digest",
        "fact_snapshot_digest": snapshot["digest"],
        "input_snapshot": snapshot,
        "state": "blocked",
        "required_gaps": ["gap"],
        "required_gates": ["gate"],
    }
    good = rules.RuleAttestation(
        head="h1",
        evaluation_digest="eval-digest",
        rule_set_digest="rule-digest",
        compiled_policy_digest="policy-digest",
        fact_snapshot_digest=snapshot["digest"],
        actor="agent",
        scope="repo",
        runner_identity="ethos-test",
        input=snapshot,
        output={"state": "blocked", "required_gaps": ["gap"], "required_gates": ["gate"]},
    ).to_dict()
    assert rules.rule_attestation_gaps(good, evaluation) == ()

    bad = {
        **good,
        "head": "h2",
        "evaluation_digest": "other",
        "rule_set_digest": "other",
        "compiled_policy_digest": "other",
        "fact_snapshot_digest": "other",
        "runner_identity": "",
        "actor": "other",
        "scope": "other",
        "input": {**snapshot, "digest": "bad"},
        "output": {"state": "ready", "required_gaps": [], "required_gates": []},
    }
    gaps = rules.rule_attestation_gaps(bad, evaluation)
    for expected in (
        "rule_attestation_mismatch:head",
        "rule_attestation_runner_missing",
        "rule_attestation_mismatch:input_digest",
        "rule_attestation_mismatch:input_snapshot",
        "rule_attestation_mismatch:input",
        "rule_attestation_mismatch:actor",
        "rule_attestation_mismatch:scope",
        "rule_attestation_mismatch:output_state",
        "rule_attestation_mismatch:output_required_gaps",
        "rule_attestation_mismatch:output_required_gates",
    ):
        assert expected in gaps

    missing = rules.rule_attestation_gaps(
        {
            "head": "h",
            "evaluation_digest": "d",
            "rule_set_digest": "r",
            "compiled_policy_digest": "p",
            "fact_snapshot_digest": "f",
        },
        {
            "head": "h",
            "digest": "d",
            "rule_set_digest": "r",
            "compiled_policy_digest": "p",
            "fact_snapshot_digest": "f",
        },
    )
    assert "rule_attestation_input_missing" in missing
    assert "rule_attestation_output_missing" in missing


def test_invalid_state_taxonomy_loads_in_order_and_classifies_unknowns() -> None:
    assert invalid_state_categories()[0].id == "authority_gap"
    assert classify("proof_not_proven") == "evidence_missing_or_stale"
    assert classify("completely_new_gap") == UNCLASSIFIED
