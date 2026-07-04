from __future__ import annotations

import json
from pathlib import Path

import pytest

from ethos_core import models
from ethos_core.action_graph import ActionGraph
from ethos_core.action_graph import ActionNode
from ethos_core.contracts.system_contracts import load_system_contract
from ethos_core.contracts.system_contracts import system_contracts_report
from ethos_core.result import EthosResult


def test_semantic_claims_require_semantic_verifier() -> None:
    assert hasattr(models, "EvidenceClaim")
    with pytest.raises(ValueError, match="semantic claims require semantic verifier"):
        models.EvidenceClaim(
            id="claim:overreach",
            change_id="change:example",
            evidence_ids=("evidence:example",),
            binding="semantic truth is proven",
            verifier="digest_only",
        )


def test_core_claim_model_does_not_embed_profile_or_host_policy_terms() -> None:
    policy_terms = "\n".join(getattr(models, "CLAIM_OVERCLAIM_PHRASES", ())).lower()

    assert "raw/cache" not in policy_terms
    assert "hosted ci" not in policy_terms
    assert "remote publication" not in policy_terms
    assert "backend retirement" not in policy_terms


def test_core_claim_model_allows_policy_specific_digest_phrasing() -> None:
    claim = models.EvidenceClaim(
        id="claim:policy-specific",
        change_id="change:example",
        evidence_ids=("evidence:example",),
        binding="hosted CI verified and adopter raw/cache parity passed",
        verifier="digest_only",
    )

    assert claim.binding == "hosted CI verified and adopter raw/cache parity passed"


def test_digest_only_claims_reject_generic_semantic_overclaim() -> None:
    with pytest.raises(ValueError, match="semantic claims require semantic verifier"):
        models.EvidenceClaim(
            id="claim:overreach",
            change_id="change:example",
            evidence_ids=("evidence:example",),
            binding="semantic truth is proven",
            verifier="digest_only",
        )
def test_action_graph_is_deterministic_and_digest_bound() -> None:
    first = ActionNode(
        id="prove",
        kind="proof",
        command=("ethos", "prove", "--json"),
        inputs=("pyproject.toml", "packages/ethos/src/ethos/cli.py"),
        outputs=("evidence/proof.json",),
        policy="required",
        tool="ethos",
        tool_version="0.1.0",
    )
    second = ActionNode(
        id="status",
        kind="inspection",
        command=("ethos", "status", "--json"),
        inputs=("packages/ethos/src/ethos/cli.py", "pyproject.toml"),
        outputs=(),
        policy="required",
        tool="ethos",
        tool_version="0.1.0",
    )

    graph = ActionGraph(nodes=(first, second))
    serialized = graph.to_dict()

    assert [node["id"] for node in serialized["nodes"]] == ["prove", "status"]
    assert graph.digest() == ActionGraph(nodes=(second, first)).digest()
    assert first.cache_key() != second.cache_key()


def test_action_node_cache_key_binds_metadata() -> None:
    base = ActionNode(
        id="ruff",
        kind="lint",
        command=("ruff", "check", "."),
        metadata={"trust_bearing": False},
    )
    changed = ActionNode(
        id="ruff",
        kind="lint",
        command=("ruff", "check", "."),
        metadata={"trust_bearing": True},
    )

    assert base.cache_key() != changed.cache_key()


def test_result_contract_has_stable_top_level_fields() -> None:
    result = EthosResult(
        command="status",
        ok=True,
        state="ready",
        summary={"branch": "dev"},
        next_actions=("ethos plan --changed",),
    )

    payload = result.to_dict()

    assert tuple(payload) == (
        "schema_version",
        "command",
        "ok",
        "state",
        "summary",
        "diagnostics",
        "required_gaps",
        "next_actions",
        "data",
    )
    json.dumps(payload)


def test_json_schemas_are_declared_for_kernel_protocols() -> None:
    schema_dir = Path("system/schemas/kernel")
    expected = {
        "result.schema.json",
        "claim.schema.json",
        "commit-policy.schema.json",
        "subject.schema.json",
        "commitment.schema.json",
        "change.schema.json",
        "action.schema.json",
        "evidence.schema.json",
        "proof-run.schema.json",
        "evidence-set.schema.json",
        "provenance.schema.json",
        "chronicle.schema.json",
        "evolution.schema.json",
        "docs-registry.schema.json",
        "evolution-ledger.schema.json",
        "gate.schema.json",
        "assistant-projection.schema.json",
        "mutation-decision.schema.json",
        "workspace-status.schema.json",
        "judgment-source.schema.json",
        "authority-graph.schema.json",
    }

    assert expected <= {path.name for path in schema_dir.glob("*.schema.json")}


def test_json_schemas_are_valid_json_documents() -> None:
    for path in Path("system/schemas/kernel").glob("*.schema.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["title"].startswith("ETHOS")


def test_system_contracts_all_load() -> None:
    report = system_contracts_report(Path())

    assert report["ok"] is True, report["required_gaps"]
    contracts = report["contracts"]
    assert isinstance(contracts, dict)
    # Every declared system-tier contract is present and parseable — system/ is
    # load-bearing, not inert prose (tao First Principle #5: derive don't store).
    assert all(contracts.values())
    assert set(contracts) >= {"authority", "evidence_boundaries", "workflows"}


def test_evidence_boundary_contract_exposes_decision_and_boundaries() -> None:
    contract = load_system_contract(Path(), "evidence_boundaries")

    assert contract["decision"]["verdicts"] == ["allow", "block", "defer"]
    assert "verdict" in contract["decision"]["required_fields"]
    # The seven evidence boundaries are declared, not merely documented.
    boundary_ids = {entry["id"] for entry in contract["boundary"]}
    assert {
        "dry_run_not_executed_proof",
        "digest_not_semantic",
        "promotion_not_absolute",
    } <= boundary_ids
    assert contract["truth"]["implies_absolute_correctness"] is False


def test_system_contracts_have_real_validating_schemas() -> None:
    from ethos_core.contracts.system_contracts import system_contracts_report

    report = system_contracts_report(Path())

    # Every declared schema= ref now resolves AND the contract validates against it —
    # no decorative schema references.
    assert report["ok"] is True, report["required_gaps"]
    assert not any("schema_ref_missing" in g for g in report["required_gaps"])
    assert not any("schema_violation" in g for g in report["required_gaps"])


def test_system_contract_schema_violation_blocks() -> None:
    from ethos_core.contracts.system_contracts import _schema_validation_gaps

    schema_path = Path("system/schemas/contracts/authority.schema.json")
    # An authority contract missing its required `order` violates the schema.
    gaps = _schema_validation_gaps(
        "authority", {"schema": str(schema_path)}, schema_path
    )

    assert any("schema_violation" in g for g in gaps)


def test_judgment_source_does_not_own_downstream_node_duties() -> None:
    """JudgmentSource is the authority anchor — it must NOT own lifecycle, evidence,
    or history (those belong to Change / Claim / Chronicle). Pins the head-of-chain
    boundary so it cannot silently absorb a sibling node's duty."""
    from dataclasses import fields

    from ethos_core.models import JudgmentSource

    field_names = {f.name for f in fields(JudgmentSource)}
    forbidden = {
        "state",
        "lifecycle",
        "transition",
        "change_id",
        "evidence_ids",
        "verifier",
        "chronicle",
        "events",
    }
    leaked = field_names & forbidden
    assert not leaked, f"JudgmentSource must not own downstream duties: {leaked}"


def test_governance_context_head_is_a_real_judgment_source_with_authority() -> None:
    """The governed-repository context must anchor on a real JudgmentSource carrying
    the authority order (not an inline dict) — the chain's production constructor."""
    from ethos.repository.context import governance_context

    context = governance_context(Path.cwd(), profile="product")
    assert context["kernel_chain"][0] == "JudgmentSource"
    assert context["judgment_source"]["authority"] == "system/authority.toml"
    # The authority order is surfaced (head-of-chain hole filled).
    assert "user_instruction" in context["judgment_source"]["policy_refs"]
    assert context["subject"]["kind"] == "repository"


def test_kernel_nodes_do_not_own_forbidden_downstream_duties() -> None:
    """Each kernel-chain node owns exactly one duty. This pins the must-not-own
    boundary for the nodes that have a live typed model, so a future field addition
    that lets one node absorb a sibling's duty fails a test rather than drifting
    silently. Commitment/Change/Evidence/Chronicle are represented by name in
    KERNEL_CHAIN (no typed shadow), so only the three constructed nodes are pinned."""
    from dataclasses import fields

    from ethos_core import models

    forbidden_per_node = {
        # JudgmentSource: authority anchor only — no downstream lifecycle/evidence.
        "JudgmentSource": {"state", "lifecycle", "transition", "evidence_ids", "verifier"},
        # Subject: identity+scope only — no state/obligation/authority.
        "Subject": {"state", "lifecycle", "transition", "authority", "evidence_ids"},
        # Claim: verifier-capped binding — does NOT own lifecycle state or a verdict.
        "EvidenceClaim": {"state", "lifecycle", "transition", "verdict", "trust_bearing"},
    }
    for node_name, forbidden in forbidden_per_node.items():
        model = getattr(models, node_name)
        field_names = {f.name for f in fields(model)}
        leaked = field_names & forbidden
        assert not leaked, f"{node_name} must not own downstream duties: {leaked}"
