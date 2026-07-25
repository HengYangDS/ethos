from __future__ import annotations

import json
import operator
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

import jsonschema
import pytest

from ethos.contracts.plan import PlanIR
from ethos.contracts.plan import PlanNode
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import ChangeContract
from ethos.contracts.semantic import RepositoryFacts
from ethos.contracts.semantic import apply_amendments
from ethos.contracts.semantic import semantic_schema_documents
from ethos.contracts.system.contracts import load_system_contract
from ethos.contracts.system.contracts import system_contracts_report
from ethos.result import EthosResult


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


def test_terminal_contracts_are_frozen_deterministic_and_schema_shaped() -> None:
    contract = ChangeContract(
        id="change:terminal-kernel",
        intent="Replace parallel semantic owners with one terminal kernel.",
        subjects=("repository:ethos",),
        scope=("src/ethos/contracts/**",),
        invariants=("no_parallel_truth",),
        acceptance=("kernel_contracts_validate",),
        authority_refs=("docs/governance/product-design-contract.md",),
        permissions=("repository.read", "work-lane.write"),
    )
    facts = RepositoryFacts(
        repository="repository:ethos",
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={"branch_role": "work_lane", "dirty": False},
        source_refs=("git:HEAD", "git:tree"),
    )

    assert contract.digest() == ChangeContract.model_validate(contract.model_dump()).digest()
    assert facts.digest() == RepositoryFacts.model_validate(facts.model_dump()).digest()
    assert contract.model_config["frozen"] is True
    assert facts.model_config["frozen"] is True


def test_attestation_content_and_repository_facts_are_deeply_immutable() -> None:
    attestation = Attestation(
        id="attestation:immutable",
        kind="observation",
        issuer="agent:local:task:one",
        subject="change:terminal-kernel",
        issued_at=datetime(2026, 7, 25, tzinfo=UTC),
        content={"nested": {"values": ["one", {"two": True}]}},
    )
    facts = RepositoryFacts(
        repository="repository:ethos",
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={"nested": {"values": ["one", {"two": True}]}},
    )

    assert isinstance(attestation.content, MappingProxyType)
    assert isinstance(attestation.content["nested"], MappingProxyType)
    assert attestation.content["nested"]["values"] == (
        "one",
        MappingProxyType({"two": True}),
    )
    assert isinstance(facts.values, MappingProxyType)
    assert isinstance(facts.values["nested"], MappingProxyType)
    with pytest.raises(TypeError):
        operator.setitem(attestation.content, "new", "forbidden")
    with pytest.raises(TypeError):
        operator.setitem(facts.values["nested"], "new", "forbidden")


def test_attestation_binds_and_validates_its_content_digest() -> None:
    issued_at = datetime(2026, 7, 25, tzinfo=UTC)
    attestation = Attestation(
        id="attestation:digest",
        kind="observation",
        issuer="agent:local:task:one",
        subject="change:terminal-kernel",
        issued_at=issued_at,
        content={"state": "observed", "nested": {"count": 1}},
    )

    assert len(attestation.content_digest) == 64
    assert Attestation.model_validate(attestation.model_dump()).content_digest == (
        attestation.content_digest
    )
    with pytest.raises(ValueError, match="attestation_content_digest_mismatch"):
        Attestation(
            id="attestation:forged",
            kind="observation",
            issuer="agent:local:task:one",
            subject="change:terminal-kernel",
            issued_at=issued_at,
            content={"state": "changed"},
            content_digest=attestation.content_digest,
        )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), b"bytes"])
def test_semantic_json_rejects_values_without_portable_json_meaning(invalid: object) -> None:
    with pytest.raises(TypeError, match="json_value_invalid"):
        Attestation(
            id="attestation:invalid-json",
            kind="observation",
            issuer="agent:local:task:one",
            subject="change:terminal-kernel",
            issued_at=datetime(2026, 7, 25, tzinfo=UTC),
            content={"invalid": invalid},
        )


@pytest.mark.parametrize("invalid", ["scalar", ("array",), {1: "non-string-key"}])
def test_semantic_json_objects_reject_non_object_or_non_string_keys(invalid: object) -> None:
    with pytest.raises(TypeError, match=r"json_object_invalid|json_object_key_invalid"):
        Attestation(
            id="attestation:invalid-object",
            kind="observation",
            issuer="agent:local:task:one",
            subject="change:terminal-kernel",
            issued_at=datetime(2026, 7, 25, tzinfo=UTC),
            content=invalid,
        )


def test_amendment_attestations_fold_in_sequence_and_bind_prior_digest() -> None:
    base = ChangeContract(
        id="change:terminal-kernel",
        intent="Establish the terminal kernel.",
        subjects=("repository:ethos",),
        acceptance=("base",),
    )
    first = Attestation(
        id="attestation:first",
        kind="amendment",
        issuer="agent:local:task:one",
        subject=base.id,
        issued_at=datetime(2026, 7, 25, 1, tzinfo=UTC),
        prior_digest=base.digest(),
        content={"patch": {"acceptance": ["base", "deterministic"]}},
    )
    after_first = apply_amendments(base, (first,))
    second = Attestation(
        id="attestation:second",
        kind="amendment",
        issuer="human:local:shell:owner",
        subject=base.id,
        issued_at=datetime(2026, 7, 25, 2, tzinfo=UTC),
        prior_digest=after_first.digest(),
        content={"patch": {"intent": "Establish the smallest deterministic terminal kernel."}},
    )

    effective = apply_amendments(base, (second, first))

    assert effective.intent == "Establish the smallest deterministic terminal kernel."
    assert effective.acceptance == ("base", "deterministic")
    assert effective.digest() == apply_amendments(base, (first, second)).digest()


def test_amendment_fold_rejects_digest_break_or_non_amendment_attestation() -> None:
    base = ChangeContract(id="change:terminal-kernel", intent="Base", subjects=("repo",))
    broken = Attestation(
        id="attestation:broken",
        kind="amendment",
        issuer="agent:local:task:one",
        subject=base.id,
        issued_at=datetime(2026, 7, 25, tzinfo=UTC),
        prior_digest="0" * 64,
        content={"patch": {"intent": "Unbound"}},
    )
    observation = Attestation(
        id="attestation:observation",
        kind="observation",
        issuer="agent:local:task:one",
        subject=base.id,
        issued_at=datetime(2026, 7, 25, tzinfo=UTC),
        content={"state": "seen"},
    )

    with pytest.raises(ValueError, match="amendment_prior_digest_mismatch"):
        apply_amendments(base, (broken,))
    with pytest.raises(ValueError, match="attestation_not_amendment"):
        apply_amendments(base, (observation,))


def test_amendment_fold_rejects_unknown_contract_fields() -> None:
    base = ChangeContract(id="change:terminal-kernel", intent="Base", subjects=("repo",))
    amendment = Attestation(
        id="attestation:unknown-field",
        kind="amendment",
        issuer="agent:local:task:one",
        subject=base.id,
        issued_at=datetime(2026, 7, 25, tzinfo=UTC),
        prior_digest=base.digest(),
        content={"patch": {"invented": "parallel ontology"}},
    )

    with pytest.raises(ValueError, match="amendment_field_unknown:invented"):
        apply_amendments(base, (amendment,))


def test_amendment_fold_rejects_ambiguous_equal_sequence() -> None:
    base = ChangeContract(id="change:terminal-kernel", intent="Base", subjects=("repo",))
    issued_at = datetime(2026, 7, 25, tzinfo=UTC)
    first = Attestation(
        id="attestation:first",
        kind="amendment",
        issuer="agent:local:task:one",
        subject=base.id,
        issued_at=issued_at,
        sequence=1,
        prior_digest=base.digest(),
        content={"patch": {"intent": "First"}},
    )
    second = Attestation(
        id="attestation:second",
        kind="amendment",
        issuer="agent:local:task:two",
        subject=base.id,
        issued_at=issued_at,
        sequence=1,
        prior_digest=base.digest(),
        content={"patch": {"intent": "Second"}},
    )

    with pytest.raises(ValueError, match="amendment_order_ambiguous"):
        apply_amendments(base, (second, first))


def test_terminal_semantic_schemas_are_generated_from_python_contracts() -> None:
    generated = semantic_schema_documents()

    assert set(generated) == {
        "change-contract.schema.json",
        "attestation.schema.json",
        "repository-facts.schema.json",
    }
    for name, schema in generated.items():
        path = Path("system/schemas/kernel") / name
        assert json.loads(path.read_text(encoding="utf-8")) == schema
        jsonschema.Draft202012Validator.check_schema(schema)


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
        "verdict",
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
        "change-contract.schema.json",
        "attestation.schema.json",
        "repository-facts.schema.json",
        "claim.schema.json",
        "commit-policy.schema.json",
        "plan-ir.schema.json",
        "proof-run.schema.json",
        "evidence-set.schema.json",
        "provenance.schema.json",
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
    from ethos.contracts.system.contracts import system_contracts_report

    report = system_contracts_report(Path())

    # Every declared schema= ref now resolves AND the contract validates against it —
    # no decorative schema references.
    assert report["ok"] is True, report["required_gaps"]
    assert not any("schema_ref_missing" in g for g in report["required_gaps"])
    assert not any("schema_violation" in g for g in report["required_gaps"])


def test_system_contract_schema_violation_blocks() -> None:
    from ethos.contracts.system.contracts import _schema_validation_gaps

    schema_path = Path("system/schemas/contracts/authority.schema.json")
    # An authority contract missing its required `order` violates the schema.
    gaps = _schema_validation_gaps("authority", {"schema": str(schema_path)}, schema_path)

    assert any("schema_violation" in g for g in gaps)


def test_superseded_authority_head_name_has_no_current_truth_surface() -> None:
    """The former head-node vocabulary must not re-enter current truth surfaces.

    This is a drift guard, not a compatibility layer: old vocabulary can be
    reconstructed only inside the test expression, and repository files must not
    carry it as code, schema, payload key, filename, heading, or prose phrase.
    """
    import re

    old_entity_pattern = re.compile(r"judg(?:e)?ment[ _-]*source", re.IGNORECASE)
    scanned_roots = (
        Path("src"),
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


def test_governance_context_projects_repository_authority_without_shadow_models() -> None:
    from ethos.repository.context import governance_context
    from ethos.repository.registry.commands import PUBLIC_WORKFLOW_COMMANDS

    context = governance_context(Path.cwd(), profile="product")
    assert context["repository"] == str(Path.cwd().resolve())
    assert "user_instruction" in context["authority_refs"]
    assert context["shared_commands"] == list(PUBLIC_WORKFLOW_COMMANDS)
    assert context["transition_commands"] == list(PUBLIC_WORKFLOW_COMMANDS)
    assert context["reader_projection_commands"] == ["ethos status"]


def test_workflow_transitions_bind_to_invalid_state_taxonomy() -> None:
    from ethos.state.invalid import NODE_ORDER

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
