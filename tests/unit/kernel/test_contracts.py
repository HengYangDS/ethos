from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from ethos_core import models
from ethos_core.contracts.plan import PlanIR
from ethos_core.contracts.plan import PlanNode
from ethos_core.contracts.system.contracts import load_system_contract
from ethos_core.contracts.system.contracts import system_contracts_report
from ethos_core.result import EthosResult


def test_digest_only_claims_reject_semantic_conclusions() -> None:
    assert hasattr(models, "EvidenceClaim")
    with pytest.raises(ValueError, match="digest_only does not permit semantic"):
        models.EvidenceClaim(
            id="claim:overreach",
            change_id="change:example",
            evidence_ids=("evidence:example",),
            binding="semantic truth is proven",
            verifier="digest_only",
        )


def test_core_claim_model_does_not_embed_profile_or_host_policy_terms() -> None:
    policy_terms = "\n".join(getattr(models, "CLAIM_OVERCLAIM_PHRASES", ())).lower()

    assert "adopter-domain storage" not in policy_terms
    assert "hosted ci" not in policy_terms
    assert "remote publication" not in policy_terms
    assert "backend retirement" not in policy_terms


def test_core_claim_model_allows_policy_specific_digest_phrasing() -> None:
    claim = models.EvidenceClaim(
        id="claim:policy-specific",
        change_id="change:example",
        evidence_ids=("evidence:example",),
        binding="hosted CI result and adopter-domain storage parity observation",
        verifier="digest_only",
    )

    assert claim.binding == "hosted CI result and adopter-domain storage parity observation"


def test_digest_only_claims_reject_generic_semantic_overclaim() -> None:
    with pytest.raises(ValueError, match="digest_only does not permit semantic"):
        models.EvidenceClaim(
            id="claim:overreach",
            change_id="change:example",
            evidence_ids=("evidence:example",),
            binding="semantic truth is proven",
            verifier="digest_only",
        )


def test_plan_ir_is_deterministic_and_digest_bound() -> None:
    first = PlanNode(
        id="prove",
        kind="check",
        command=("ethos", "prove", "--json"),
    )
    second = PlanNode(
        id="status",
        kind="check",
        command=("ethos", "status", "--json"),
    )

    plan = PlanIR(nodes=(first, second))
    serialized = plan.to_dict()

    assert [node["id"] for node in serialized["nodes"]] == ["prove", "status"]
    assert plan.digest() == PlanIR(nodes=(second, first)).digest()


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
        "plan-ir.schema.json",
        "evidence.schema.json",
        "proof-run.schema.json",
        "evidence-set.schema.json",
        "provenance.schema.json",
        "chronicle.schema.json",
        "semantic-attestation-receipt.schema.json",
        "evolution.schema.json",
        "docs-registry.schema.json",
        "evolution-ledger.schema.json",
        "gate.schema.json",
        "assistant-projection.schema.json",
        "lane-lease.schema.json",
        "mutation-decision.schema.json",
        "workspace-status.schema.json",
        "authority.schema.json",
        "authority-graph.schema.json",
    }

    assert expected <= {path.name for path in schema_dir.glob("*.schema.json")}


def test_json_schemas_are_valid_json_documents() -> None:
    for path in Path("system/schemas/kernel").glob("*.schema.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["title"].startswith("ETHOS")


def test_plan_ir_schema_accepts_the_python_projection() -> None:
    schema = json.loads(Path("system/schemas/kernel/plan-ir.schema.json").read_text())
    plan = PlanIR(
        nodes=(
            PlanNode(
                id="land",
                kind="effect",
                command=("ethos", "land"),
            ),
        )
    )

    jsonschema.Draft202012Validator(schema).validate(plan.to_dict())


def test_system_contracts_all_load() -> None:
    report = system_contracts_report(Path())

    assert report["ok"] is True, report["required_gaps"]
    contracts = report["contracts"]
    assert isinstance(contracts, dict)
    # Every declared system-tier contract is present and parseable — system/ is
    # load-bearing, not inert prose (the parsimony invariant: derive rather than store twice).
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
    from ethos_core.contracts.system.contracts import system_contracts_report

    report = system_contracts_report(Path())

    # Every declared schema= ref now resolves AND the contract validates against it —
    # no decorative schema references.
    assert report["ok"] is True, report["required_gaps"]
    assert not any("schema_ref_missing" in g for g in report["required_gaps"])
    assert not any("schema_violation" in g for g in report["required_gaps"])


def test_system_contract_schema_violation_blocks() -> None:
    from ethos_core.contracts.system.contracts import _schema_validation_gaps

    schema_path = Path("system/schemas/contracts/authority.schema.json")
    # An authority contract missing its required `order` violates the schema.
    gaps = _schema_validation_gaps("authority", {"schema": str(schema_path)}, schema_path)

    assert any("schema_violation" in g for g in gaps)


def test_authority_does_not_own_downstream_node_duties() -> None:
    """Authority is the authority-order anchor — it must NOT own lifecycle, evidence,
    or history (those belong to Change / Claim / Chronicle). Pins the head-of-chain
    boundary so it cannot silently absorb a sibling node's duty."""
    from dataclasses import fields

    from ethos_core.models import Authority

    field_names = {f.name for f in fields(Authority)}
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
    assert not leaked, f"Authority must not own downstream duties: {leaked}"


def test_governance_context_uses_authority_as_only_kernel_head() -> None:
    """The current governance truth uses Authority only.

    No superseded head model, payload key, schema, or chain term remains as a
    compatibility surface.
    """
    from ethos.repository.context import governance_context
    from ethos_core import models
    from ethos_core.kernel import KERNEL_CHAIN

    context = governance_context(Path.cwd(), profile="product")

    assert KERNEL_CHAIN[0] == "Authority"
    assert context["kernel_chain"][0] == "Authority"
    assert "authority" in context
    assert context["authority"]["order_ref"] == "system/authority.toml"
    assert "user_instruction" in context["authority"]["policy_refs"]
    old_prefix = "Judgment"
    assert not hasattr(models, f"{old_prefix}Source")


def test_superseded_authority_head_name_has_no_current_truth_surface() -> None:
    """The former head-node vocabulary must not re-enter current truth surfaces.

    This is a drift guard, not a compatibility layer: old vocabulary can be
    reconstructed only inside the test expression, and repository files must not
    carry it as code, schema, payload key, filename, heading, or prose phrase.
    """
    import re

    old_entity_pattern = re.compile(r"judg(?:e)?ment[ _-]*source", re.IGNORECASE)
    scanned_roots = (
        Path("packages"),
        Path("system"),
        Path("docs"),
        Path("openspec/specs"),
        Path("README.md"),
    )
    offenders: list[str] = []
    for root in scanned_roots:
        paths = root.rglob("*") if root.is_dir() else (root,)
        for path in paths:
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if old_entity_pattern.search(path.as_posix()) or old_entity_pattern.search(text):
                offenders.append(path.as_posix())

    assert offenders == []


def test_governance_context_head_is_a_real_authority_with_authority() -> None:
    """The governed-repository context must anchor on a real Authority carrying
    the authority order (not an inline dict) — the chain's production constructor."""
    from ethos.repository.context import governance_context
    from ethos.repository.registry.commands import PUBLIC_WORKFLOW_COMMANDS

    context = governance_context(Path.cwd(), profile="product")
    assert context["kernel_chain"][0] == "Authority"
    assert context["authority"]["order_ref"] == "system/authority.toml"
    # The authority order is surfaced (head-of-chain hole filled).
    assert "user_instruction" in context["authority"]["policy_refs"]
    assert context["subject"]["kind"] == "repository"
    assert context["shared_commands"] == list(PUBLIC_WORKFLOW_COMMANDS)
    assert context["transition_commands"] == list(PUBLIC_WORKFLOW_COMMANDS)


def test_kernel_nodes_do_not_own_forbidden_downstream_duties() -> None:
    """Each kernel-chain node owns exactly one duty. This pins the must-not-own
    boundary for the nodes that have a live typed model, so a future field addition
    that lets one node absorb a sibling's duty fails a test rather than drifting
    silently. Commitment/Change/Evidence/Chronicle are represented by name in
    KERNEL_CHAIN (no typed shadow), so only the three constructed nodes are pinned."""
    from dataclasses import fields

    from ethos_core import models

    forbidden_per_node = {
        # Authority: authority anchor only — no downstream lifecycle/evidence.
        "Authority": {"state", "lifecycle", "transition", "evidence_ids", "verifier"},
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


def test_workflow_transitions_bind_to_invalid_state_taxonomy() -> None:
    from ethos_core.state.invalid import NODE_ORDER

    contract = load_system_contract(Path(), "workflows")
    states = set(contract["lifecycle"]["states"])
    guards = set(contract["guards"])
    transitions = contract["transition"]

    assert transitions
    for transition in transitions:
        assert transition["from"] in states
        assert transition["to"] in states
        assert transition["guard"] in guards
        assert transition["invalid_state"] in NODE_ORDER
        assert transition["invalid_state"] in transition["invalid_states"]
        assert set(transition["invalid_states"]).issubset(set(NODE_ORDER))
    assert {
        invalid_state
        for transition in transitions
        for invalid_state in transition["invalid_states"]
    } >= {
        "subject_ambiguous",
        "change_unbounded",
        "evidence_missing_or_stale",
        "claim_unbound_or_overreaching",
        "chronicle_missing",
        "substrate_untrusted",
    }


def test_load_system_contract_uses_product_resource_for_workflows_when_root_lacks_contract(
    tmp_path,
):
    contract = load_system_contract(tmp_path, "workflows")

    assert contract["runtime"]["truth_boundary"] == "derived_repository_projection"
    assert contract["node"]


def test_load_system_contract_keeps_non_resource_contracts_fail_closed(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_system_contract(tmp_path, "authority")
