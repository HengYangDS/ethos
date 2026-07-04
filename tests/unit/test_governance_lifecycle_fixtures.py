from __future__ import annotations

from ethos.repository.schema_validation import validate_schema_instance
from ethos.testing.fixtures import complete_governance_lifecycle
from ethos.testing.fixtures import malformed_governance_lifecycle
from ethos.testing.fixtures import reference_adopter_profile_fixture


def test_complete_governance_lifecycle_fixture_validates_contracts() -> None:
    fixture = complete_governance_lifecycle()

    assert fixture["required_gaps"] == []
    assert (
        validate_schema_instance(
            "trust-envelope.schema.json",
            fixture["trust_envelope"],
        )["ok"]
        is True
    )
    assert (
        validate_schema_instance(
            "capability-profile.schema.json",
            fixture["capability_profile"],
        )["ok"]
        is True
    )
    for target in fixture["trust_envelope"]["promotion"]["targets"]:
        assert validate_schema_instance("promotion-target.schema.json", target)["ok"] is True


def test_malformed_governance_lifecycle_fixture_names_required_gaps() -> None:
    fixture = malformed_governance_lifecycle()

    assert fixture["required_gaps"] == [
        "openspec_claim_binding_missing:sample-change",
        "promotion_target_missing:sample-trust:docs/evidence/missing.md",
        "executed_proof_missing",
        "malformed_openspec_carrier:sample-change",
    ]
    assert fixture["trust_envelope"]["required_gaps"]


def test_reference_adopter_profile_fixture_keeps_terms_outside_product_core() -> None:
    fixture = reference_adopter_profile_fixture()

    assert fixture["boundary"] == "adopter-profile-only"
    assert fixture["profile_terms"] == ["raw/cache parity", "domain cache contract"]
    assert fixture["core_product_terms"] == []
