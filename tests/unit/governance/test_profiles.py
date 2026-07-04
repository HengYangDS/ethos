from __future__ import annotations

from ethos.repository.policy.schema import validate_schema_instance
from ethos.repository.registry.profiles import governance_profile_report


def test_self_and_product_profiles_are_isomorphic() -> None:
    report = governance_profile_report()

    product = report["profiles"]["product-adopter"]
    self_profile = report["profiles"]["self-governance"]

    assert report["ok"] is True
    assert report["isomorphic"] is True
    assert product["capability_graph"] == self_profile["capability_graph"]
    assert product["run_steps"] == self_profile["run_steps"]
    assert product["truth_sources"] == self_profile["truth_sources"]
    assert product["advisory_projections"] == self_profile["advisory_projections"]
    assert product["kernel_chain"] == self_profile["kernel_chain"]
    assert product["trust_lifecycle"] == self_profile["trust_lifecycle"]
    assert report["shared_kernel"]["kernel_chain"] == [
        "JudgmentSource",
        "Subject",
        "Commitment",
        "Change",
        "Evidence",
        "Claim",
        "Chronicle",
    ]
    assert report["shared_kernel"]["trust_lifecycle"] == [
        "Claim",
        "Boundary",
        "Carrier",
        "Evidence",
        "Decision",
        "Promotion",
    ]
    assert report["allowed_differences"] == [
        "authority_binding",
        "profile_config",
        "adapter_binding",
        "strictness",
        "rollout",
    ]


def test_campaign_committee_profile_requires_four_roles_and_consensus() -> None:
    report = governance_profile_report()
    committee = report["committee"]

    assert committee["role_count"] == 4
    assert {role["id"] for role in committee["roles"]} == {
        "architecture-governance",
        "security-source-verification",
        "cli-mcp-api-contracts",
        "retrieval-storage-eval",
    }
    assert committee["consensus_gate"]["required"] is True
    assert committee["consensus_gate"]["blocking_findings_must_be_resolved"] is True


def test_governance_profile_report_validates_against_schema() -> None:
    validation = validate_schema_instance(
        "governance-profile.schema.json",
        governance_profile_report(),
    )

    assert validation["ok"] is True
