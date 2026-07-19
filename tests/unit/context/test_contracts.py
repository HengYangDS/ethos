from __future__ import annotations

from ethos_core.contracts.context.projection import UNTRUSTED_CONTEXT_LABEL
from ethos_core.contracts.context.projection import context_projection_contract
from ethos_core.contracts.context.projection import context_retrieval_smoke_queries
from ethos_core.contracts.context.projection import default_context_policy


def test_context_projection_contract_is_advisory_only() -> None:
    contract = context_projection_contract()
    policy = default_context_policy()

    assert UNTRUSTED_CONTEXT_LABEL == "UNTRUSTED CONTEXT"
    assert contract["authority"] == "projection"
    assert contract["can_close_required_gaps"] is False
    assert "proof" in policy["forbidden_uses"]
    assert "required_gap_closure" in policy["forbidden_uses"]
    assert policy["privacy_ceiling"] == "repo_local"


def test_context_contract_exposes_retrieval_smoke_queries() -> None:
    fixtures = context_retrieval_smoke_queries()

    assert fixtures
    assert all(item["query"] for item in fixtures)
    assert {
        "docs/architecture/context-projection.md",
        "docs/reference/command-plane.md",
    } <= {path for item in fixtures for path in item["expected_paths"]}
