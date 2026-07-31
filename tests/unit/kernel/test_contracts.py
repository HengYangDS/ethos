from __future__ import annotations

import json
import operator
import re
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Literal

import jsonschema
import pytest
from pydantic import ValidationError

import ethos.contracts.semantic
from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import terminal_schema_documents
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.system.contracts import load_system_contract
from ethos.contracts.system.contracts import system_contracts_report
from ethos.repository.context import repository_context
from ethos.result import EthosResult

_PLAN_INPUTS = {
    "inputs": PlanInputs(commitment="a" * 64, facts="b" * 64, policy="c" * 64),
    "facts": {
        "schema_version": 1,
        "repository": "repository:test",
        "head": "a" * 40,
        "tree": "b" * 40,
        "values": {},
        "source_refs": [],
    },
}
_BASE = {"id": "change:terminal-kernel", "intent": "Base", "subjects": ("repo",)}
_ISSUED_AT = datetime(2026, 7, 25, tzinfo=UTC)


def _contract(**updates: object) -> Commitment:
    return Commitment(**(_BASE | updates))


def _attestation(
    *,
    statement: object,
    verdict: Literal["pass", "block", "unknown"] = "pass",
    advisories: tuple[str, ...] = (),
) -> Attestation:
    return Attestation.issue(
        {
            "predicate": "observation:repository",
            "verifier": "agent:local:task:one",
            "subject": "change:terminal-kernel",
            "issued_at": _ISSUED_AT,
            "verdict": verdict,
            "statement": statement,
            "advisories": advisories,
            "commitment_digest": "a" * 64,
            "facts_digest": "b" * 64,
            "plan_digest": "c" * 64,
            "policy_digest": "d" * 64,
            "effect_digest": "",
        }
    )


def test_transition_plan_is_deterministic_and_digest_bound() -> None:
    prove = PlanNode(id="prove", kind="check", command=("ethos", "prove", "--json"))
    status = PlanNode(id="status", kind="check", command=("ethos", "status", "--json"))
    plan = TransitionPlan.compile(**_PLAN_INPUTS, nodes=(prove, status))
    assert [node["id"] for node in plan.model_dump(mode="json")["nodes"]] == [
        "prove",
        "status",
    ]
    assert plan.digest == TransitionPlan.compile(**_PLAN_INPUTS, nodes=(status, prove)).digest


def test_gate_declaration_compiles_one_stable_transitive_proof_closure() -> None:
    declaration = GateRegistryDeclaration(
        id="test-gates",
        proof_sets=GateProofSets(default=("publish",), full=("publish",)),
        gates=(
            Gate(
                id="publish",
                kind="release",
                command=("publish",),
                depends_on=("test", "lint"),
                registries=("runtime",),
            ),
            Gate(
                id="lint",
                kind="lint",
                command=("lint",),
                depends_on=("compile",),
                registries=("runtime",),
            ),
            Gate(
                id="compile",
                kind="compile",
                command=("compile",),
                registries=("runtime",),
            ),
            Gate(
                id="test",
                kind="test",
                command=("test",),
                depends_on=("compile",),
                registries=("runtime",),
            ),
        ),
    )

    assert tuple(gate.id for gate in declaration.proof_gates()) == (
        "compile",
        "lint",
        "test",
        "publish",
    )
    with pytest.raises(ValueError, match="unknown proof gate"):
        declaration.proof_gates(("missing",))


def test_gate_boundary_rejects_coercion_without_dump_validate_bridges() -> None:
    with pytest.raises(ValidationError):
        Gate(
            id="test",
            kind="test",
            command=("test",),
            registries=("runtime",),
            trust_bearing=1,
        )

    entry = Gate(
        id="test",
        kind="test",
        command=("test",),
        registries=("runtime",),
    )
    assert not hasattr(entry, "descriptor")


def test_terminal_contracts_are_frozen_deterministic_and_schema_shaped() -> None:
    commitment = _contract(
        id="change:terminal-kernel",
        intent="Replace parallel semantic owners with one terminal kernel.",
        subjects=("repository:ethos",),
        scope=("src/ethos/contracts/**",),
        invariants=("no_parallel_truth",),
        acceptance=("kernel_contracts_validate",),
        authority_refs=("docs/governance/product-design-contract.md",),
        permissions=("repository.read", "work-lane.write"),
    )
    facts = Facts(
        repository="repository:ethos",
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={"branch_role": "work_lane", "dirty": False},
        source_refs=("git:HEAD", "git:tree"),
    )
    assert commitment.digest() == Commitment.model_validate(commitment.model_dump()).digest()
    assert facts.digest() == Facts.model_validate(facts.model_dump()).digest()
    assert commitment.model_config["frozen"] is facts.model_config["frozen"] is True


@pytest.mark.parametrize("value", [{"unordered"}, iter(("generated",))])
def test_frozen_tuple_rejects_unordered_or_consumable_iterables(value: object) -> None:
    with pytest.raises((TypeError, ValidationError)):
        Gate(id="test", kind="test", command=value)


def test_only_commitment_and_attestation_have_production_persistence_owners() -> None:
    production = Path("src/ethos")
    forbidden = re.compile(
        r"(?:persist|save|store|write)_(?:facts|transition_plan)"
        r"|(?:Facts|TransitionPlan)\.(?:model_dump_json|canonical_json)\("
    )
    offenders = [
        path.as_posix()
        for path in production.rglob("*.py")
        if forbidden.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []
    assert Path("src/ethos/adapters/mutation/proof_artifacts.py").exists()
    assert Path("src/ethos/adapters/repo/commitment.py").exists()
    assert not Path("src/ethos/adapters/mutation/attestation_projection.py").exists()
    assert "never persisted as truth" in (Facts.__doc__ or "")
    assert "transient" in (TransitionPlan.__doc__ or "")


def test_commitment_identity_projection_is_explicit_and_schema_version_bound() -> None:
    commitment = _contract(risks=("cutover",), hypotheses=("compiler",), dependencies=("git",))

    assert commitment.identity_projection() == {
        "schema_version": 1,
        "id": "change:terminal-kernel",
        "intent": "Base",
        "subjects": ["repo"],
        "scope": [],
        "invariants": [],
        "acceptance": [],
        "risks": ["cutover"],
        "authority_refs": [],
        "permissions": [],
        "hypotheses": ["compiler"],
        "dependencies": ["git"],
    }
    assert commitment.digest() != _contract(risks=("other",)).digest()


@pytest.mark.parametrize("field", ["campaign", "collaboration", "compatibility", "publication"])
def test_commitment_rejects_process_and_distribution_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        _contract(**{field: "retired"})


@pytest.mark.parametrize(
    "scope", [("/absolute",), ("docs/../secrets",), (r"docs\windows",), ("docs/**", "docs/**")]
)
def test_commitment_rejects_ambiguous_scope(scope: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match=r"change_scope_invalid|change_scope_duplicate"):
        _contract(
            id="change:invalid-scope",
            intent="Reject ambiguous scope.",
            subjects=("repository:test",),
            scope=scope,
        )


def test_facts_digest_ignores_observation_time() -> None:
    facts = Facts(
        repository="repository:ethos",
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={"changed_paths": ("src/ethos/result.py",)},
    )
    assert (
        facts.digest()
        == facts.model_copy(update={"observed_at": datetime(2026, 7, 26, tzinfo=UTC)}).digest()
    )


def test_attestation_identity_and_serialization_are_statement_addressed() -> None:
    first = _attestation(
        statement={"z": ["one", {"two": True}], "a": {"nested": "value"}},
        advisories=("non_blocking_note",),
    )
    reordered = _attestation(
        statement={"a": {"nested": "value"}, "z": ["one", {"two": True}]},
        advisories=("non_blocking_note",),
    )

    assert len(first.id) == len(first.statement_digest) == 64
    assert first.id == reordered.id
    assert first.canonical_json() == reordered.canonical_json()
    assert json.loads(first.canonical_json()) == first.model_dump(mode="json")
    assert first.verdict == "pass"
    assert first.advisories == ("non_blocking_note",)
    assert (
        _attestation(
            statement={"z": ["one", {"two": True}], "a": {"nested": "value"}},
            verdict="unknown",
            advisories=("non_blocking_note",),
        ).id
        != first.id
    )

    forged = first.model_dump(mode="json")
    forged["id"] = "f" * 64
    with pytest.raises(ValueError, match="attestation_identity_mismatch"):
        Attestation.model_validate_json(json.dumps(forged))


def test_attestation_requires_closed_verdict_and_at_least_one_binding() -> None:
    attestation = _attestation(statement={"state": "observed"})
    payload = attestation.model_dump(mode="json")
    payload["verdict"] = "pass"
    with pytest.raises(ValidationError):
        Attestation.model_validate(payload)

    payload = attestation.model_dump(mode="json")
    payload["facts_digest"] = "not-a-digest"
    with pytest.raises(ValidationError):
        Attestation.model_validate(payload)

    with pytest.raises(ValueError, match="attestation_binding_missing"):
        Attestation.issue(
            {
                "predicate": "observation:repository",
                "verifier": "agent:local:task:one",
                "subject": "change:terminal-kernel",
                "issued_at": _ISSUED_AT,
                "verdict": "pass",
                "statement": {"state": "observed"},
            }
        )


def test_attestation_predicate_is_open_and_never_amends_a_commitment() -> None:
    attestation = Attestation.issue(
        {
            "predicate": "review:human",
            "verifier": "human:local:owner",
            "subject": "change:terminal-kernel",
            "issued_at": _ISSUED_AT,
            "verdict": "pass",
            "statement": {"decision": "accept"},
            "evidence_refs": ("git:commit:" + "a" * 40,),
        }
    )

    assert attestation.predicate == "review:human"
    assert not hasattr(ethos.contracts.semantic, "apply_amendments")
    assert not hasattr(ethos.contracts.semantic, "effective_intent")
    assert not hasattr(ethos.contracts.semantic, "AttestationKind")
    assert not hasattr(Attestation, "apply_amendments")
    assert not hasattr(attestation, "kind")
    assert not hasattr(attestation, "content")
    assert not hasattr(attestation, "sequence")
    assert not hasattr(attestation, "prior_digest")
    assert not hasattr(attestation, "mints_authority")


def test_semantic_values_are_immutable_and_digest_bound() -> None:
    issued_at = datetime(2026, 7, 25, tzinfo=UTC)
    attestation = _attestation(statement={"nested": {"values": ["one", {"two": True}]}})
    facts = Facts(
        repository="repository:ethos",
        head="a" * 40,
        tree="b" * 40,
        observed_at=issued_at,
        values={"nested": {"values": ["one", {"two": True}]}},
    )
    assert isinstance(attestation.statement, MappingProxyType)
    assert attestation.statement["nested"]["values"] == ("one", MappingProxyType({"two": True}))
    assert isinstance(facts.values, MappingProxyType)
    with pytest.raises(TypeError):
        operator.setitem(attestation.statement, "new", "forbidden")
    with pytest.raises(TypeError):
        operator.setitem(facts.values["nested"], "new", "forbidden")
    assert (
        Attestation.model_validate(attestation.model_dump()).statement_digest
        == attestation.statement_digest
    )
    with pytest.raises(ValueError, match="attestation_statement_digest_mismatch"):
        Attestation.model_validate_json(
            json.dumps(attestation.model_dump(mode="json") | {"statement": {"state": "changed"}})
        )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), b"bytes"])
def test_semantic_json_rejects_values_without_portable_json_meaning(invalid: object) -> None:
    with pytest.raises(TypeError, match="json_value_invalid"):
        _attestation(statement={"invalid": invalid})


@pytest.mark.parametrize(
    "invalid",
    ["scalar", ("array",), {1: "non-string-key"}, {"nested": {1: "non-string-key"}}],
)
def test_semantic_json_objects_reject_non_object_or_non_string_keys(invalid: object) -> None:
    with pytest.raises(TypeError, match=r"json_object_invalid|json_object_key_invalid"):
        _attestation(statement=invalid)


def test_schema_surfaces_are_generated_declared_and_valid() -> None:
    schema_docs = Path("docs/architecture/schema-validation.md").read_text(encoding="utf-8")
    generated = terminal_schema_documents()
    assert "typed variants" not in schema_docs
    assert "open-predicate statement" in schema_docs
    assert "evidence bindings" in schema_docs
    assert set(generated) == {
        "commitment.schema.json",
        "attestation.schema.json",
        "facts.schema.json",
        "transition-plan.schema.json",
    }
    commitment_schema = generated["commitment.schema.json"]
    assert commitment_schema["properties"]["schema_version"]["const"] == 1
    assert not {"campaign", "collaboration", "compatibility", "publication"} & set(
        commitment_schema["properties"]
    )
    attestation_schema = generated["attestation.schema.json"]
    assert {
        "id",
        "predicate",
        "statement",
        "statement_digest",
        "verifier",
        "verdict",
        "commitment_digest",
        "facts_digest",
        "plan_digest",
        "policy_digest",
        "effect_digest",
    } <= set(attestation_schema["required"])
    assert attestation_schema["properties"]["verdict"]["enum"] == [
        "pass",
        "block",
        "unknown",
    ]
    assert "enum" not in attestation_schema["properties"]["predicate"]
    assert "allOf" not in attestation_schema
    assert not {"kind", "content", "sequence", "mints_authority"} & set(
        attestation_schema["properties"]
    )
    schema_dir = Path("system/schemas/kernel")
    expected = {
        "result.schema.json",
        *generated,
        "commit-policy.schema.json",
        "provenance.schema.json",
        "docs-registry.schema.json",
        "gate.schema.json",
        "assistant-projection.schema.json",
        "lane-lease.schema.json",
        "mutation-decision.schema.json",
        "workspace-status.schema.json",
    }
    paths = tuple(schema_dir.glob("*.schema.json"))
    assert expected <= {path.name for path in paths}
    for path in paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["title"].startswith("ETHOS")
        jsonschema.Draft202012Validator.check_schema(schema)
        if path.name in generated:
            assert schema == generated[path.name]
    workspace_schema = json.loads(
        (schema_dir / "workspace-status.schema.json").read_text(encoding="utf-8")
    )
    serialized_workspace_schema = json.dumps(workspace_schema, sort_keys=True)
    assert "claim_id" not in serialized_workspace_schema
    assert "claim_binding" not in serialized_workspace_schema
    assert "contract_binding" not in serialized_workspace_schema
    assert "closeoutResidueLane" not in workspace_schema["$defs"]
    for retired_field in (
        "closeout_disposition",
        "residue_state",
        "closeout_residue_count",
        "dirty_closeout_residue_count",
        "closeout_residue_lanes",
    ):
        assert retired_field not in serialized_workspace_schema
    for definition in (
        "branchBinding",
        "closeoutSupport",
        "foreignWorkLane",
        "unboundWorkLaneRef",
    ):
        properties = workspace_schema["$defs"][definition]["properties"]
        assert {
            "base_commitment_digest",
            "commitment_binding",
            "lease_state",
        } <= set(properties)
    assert workspace_schema["$defs"]["foreignWorkLane"]["properties"]["lease_state"]["enum"] == [
        "valid",
        "expired",
        "unknown",
        "missing",
    ]
    plan = TransitionPlan.compile(
        **_PLAN_INPUTS, nodes=(PlanNode(id="land", kind="effect", command=("ethos", "land")),)
    )
    assert plan.model_dump(mode="json")["inputs"]["commitment"] == "a" * 64
    assert set(generated["transition-plan.schema.json"]["required"]) == {
        "schema_version",
        "inputs",
        "permissions",
        "facts",
        "nodes",
        "verdict",
        "required_gaps",
        "digest",
    }


def test_result_contract_has_stable_top_level_fields() -> None:
    payload = EthosResult(
        command="status",
        verdict="pass",
        state="ready",
        summary={"branch": "dev"},
        next_actions=("ethos plan --changed",),
    ).to_dict()
    assert tuple(payload) == (
        "schema_version",
        "command",
        "verdict",
        "state",
        "summary",
        "diagnostics",
        "required_gaps",
        "next_actions",
        "data",
    )
    json.dumps(payload)


def test_system_contracts_load_validate_and_fail_closed() -> None:
    report = system_contracts_report(Path())
    assert report["verdict"] == "pass", report["required_gaps"]
    assert all(report["contracts"].values())
    assert set(report["contracts"]) >= {"formats", "evidence_boundaries"}
    assert not any(
        "schema_ref_missing" in gap or "schema_violation" in gap for gap in report["required_gaps"]
    )
    contract = load_system_contract(Path(), "evidence_boundaries")
    assert contract["decision"]["verdicts"] == ["pass", "block", "unknown"]
    assert "verdict" in contract["decision"]["required_fields"]
    assert {"dry_run_not_executed_proof", "digest_not_semantic", "promotion_not_absolute"} <= {
        entry["id"] for entry in contract["boundary"]
    }
    assert contract["truth"]["implies_absolute_correctness"] is False
    with pytest.raises(FileNotFoundError):
        load_system_contract(Path("/tmp"), "formats")


def test_superseded_authority_head_name_has_no_current_truth_surface() -> None:
    old_entity_pattern = re.compile(r"judg(?:e)?ment[ _-]*source", re.IGNORECASE)
    offenders = [
        path.as_posix()
        for root in (
            Path("src"),
            Path("system"),
            Path("docs"),
            Path("openspec/specs"),
            Path("README.md"),
        )
        for path in (root.rglob("*") if root.is_dir() else (root,))
        if path.is_file() and _matches_old_entity(path, old_entity_pattern)
    ]
    assert offenders == []


def _matches_old_entity(path: Path, pattern: re.Pattern[str]) -> bool:
    try:
        return bool(
            pattern.search(path.as_posix()) or pattern.search(path.read_text(encoding="utf-8"))
        )
    except UnicodeDecodeError:
        return False


def test_governance_context_projects_repository_profile_without_shadow_models() -> None:
    context = repository_context(Path.cwd())
    assert context["repository"] == str(Path.cwd().resolve())
    assert "authority" not in context
    assert "authority_refs" not in context
    assert "shared_commands" not in context
    assert "transition_commands" not in context
    assert context["reader_projection_commands"] == ["ethos status"]


def test_adopter_governance_context_uses_its_repository_profile(tmp_path: Path) -> None:
    context = repository_context(tmp_path)

    assert context["repository"] == str(tmp_path.resolve())
    assert context["profile"] == "unbound"
    assert "authority" not in context
