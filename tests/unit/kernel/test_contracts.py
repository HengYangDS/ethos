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

from ethos.contracts.plan import PlanIR
from ethos.contracts.plan import PlanNode
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import ChangeContract
from ethos.contracts.semantic import RepositoryFacts
from ethos.contracts.semantic import apply_amendments
from ethos.contracts.semantic import semantic_schema_documents
from ethos.contracts.system.contracts import load_system_contract
from ethos.contracts.system.contracts import schema_validation_gaps
from ethos.contracts.system.contracts import system_contracts_report
from ethos.repository.context import LIFECYCLE_COMMANDS
from ethos.repository.context import governance_context
from ethos.result import EthosResult

_PLAN_INPUTS = {
    "contract_digest": "a" * 64,
    "facts_digest": "b" * 64,
    "policy_digest": "c" * 64,
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


def _contract(**updates: object) -> ChangeContract:
    return ChangeContract(**(_BASE | updates))


def _attestation(
    *,
    content: object,
    verdict: Literal["pass", "block", "unknown"] = "pass",
    advisories: tuple[str, ...] = (),
) -> Attestation:
    return Attestation.issue(
        {
            "kind": "observation",
            "issuer": "agent:local:task:one",
            "subject": "change:terminal-kernel",
            "issued_at": _ISSUED_AT,
            "verdict": verdict,
            "content": content,
            "advisories": advisories,
            "change_contract_digest": "a" * 64,
            "repository_facts_digest": "b" * 64,
            "plan_digest": "c" * 64,
            "policy_digest": "d" * 64,
            "effect_digest": "",
        }
    )


def _amendment(
    base: ChangeContract,
    patch: dict[str, object],
    *,
    issuer: str = "agent:local:task:one",
    issued_at: datetime = _ISSUED_AT,
    change_contract_digest: str | None = None,
    kind: str = "amendment",
    sequence: int = 0,
) -> Attestation:
    return Attestation.issue(
        {
            "kind": kind,
            "issuer": issuer,
            "subject": base.id,
            "issued_at": issued_at,
            "verdict": "pass",
            "sequence": sequence,
            "content": {"patch": patch} if kind == "amendment" else {"state": "seen"},
            "change_contract_digest": base.digest()
            if change_contract_digest is None
            else change_contract_digest,
            "repository_facts_digest": "",
            "plan_digest": "",
            "policy_digest": "",
            "effect_digest": "",
        }
    )


def test_plan_ir_is_deterministic_and_digest_bound() -> None:
    prove = PlanNode(id="prove", kind="check", command=("ethos", "prove", "--json"))
    status = PlanNode(id="status", kind="check", command=("ethos", "status", "--json"))
    plan = PlanIR(**_PLAN_INPUTS, nodes=(prove, status))
    assert [node["id"] for node in plan.to_dict()["nodes"]] == ["prove", "status"]
    assert plan.digest() == PlanIR(**_PLAN_INPUTS, nodes=(status, prove)).digest()


def test_terminal_contracts_are_frozen_deterministic_and_schema_shaped() -> None:
    contract = _contract(
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
    assert contract.model_config["frozen"] is facts.model_config["frozen"] is True


@pytest.mark.parametrize(
    "scope", [("/absolute",), ("docs/../secrets",), (r"docs\\windows",), ("docs/**", "docs/**")]
)
def test_change_contract_rejects_ambiguous_scope(scope: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match=r"change_scope_invalid|change_scope_duplicate"):
        _contract(
            id="change:invalid-scope",
            intent="Reject ambiguous scope.",
            subjects=("repository:test",),
            scope=scope,
        )


def test_repository_facts_digest_ignores_observation_time() -> None:
    facts = RepositoryFacts(
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


def test_attestation_identity_and_serialization_are_content_addressed() -> None:
    first = _attestation(
        content={"z": ["one", {"two": True}], "a": {"nested": "value"}},
        advisories=("non_blocking_note",),
    )
    reordered = _attestation(
        content={"a": {"nested": "value"}, "z": ["one", {"two": True}]},
        advisories=("non_blocking_note",),
    )

    assert len(first.id) == len(first.content_digest) == 64
    assert first.id == reordered.id
    assert first.canonical_json() == reordered.canonical_json()
    assert json.loads(first.canonical_json()) == first.model_dump(mode="json")
    assert first.verdict == "pass"
    assert first.advisories == ("non_blocking_note",)
    assert first.mints_authority is False
    assert (
        _attestation(
            content={"z": ["one", {"two": True}], "a": {"nested": "value"}},
            verdict="unknown",
            advisories=("non_blocking_note",),
        ).id
        != first.id
    )

    forged = first.model_dump(mode="json")
    forged["id"] = "f" * 64
    with pytest.raises(ValueError, match="attestation_identity_mismatch"):
        Attestation.model_validate_json(json.dumps(forged))


def test_attestation_requires_closed_verdict_and_explicit_digest_bindings() -> None:
    attestation = _attestation(content={"state": "observed"})
    payload = attestation.model_dump(mode="json")
    payload["verdict"] = "allow"
    with pytest.raises(ValidationError):
        Attestation.model_validate(payload)

    payload = attestation.model_dump(mode="json")
    payload["repository_facts_digest"] = "not-a-digest"
    with pytest.raises(ValidationError):
        Attestation.model_validate(payload)

    payload = attestation.model_dump(mode="json")
    payload.pop("policy_digest")
    with pytest.raises(ValidationError):
        Attestation.model_validate(payload)


def test_attestation_kind_algebra_is_closed() -> None:
    with pytest.raises(ValidationError):
        Attestation.issue(
            {
                "kind": "claim",
                "issuer": "agent:local:task:one",
                "subject": "change:terminal-kernel",
                "issued_at": _ISSUED_AT,
                "verdict": "pass",
                "content": {"summary": "legacy parallel entity"},
            }
        )


def test_judgment_attestation_requires_basis_and_semantic_binding() -> None:
    with pytest.raises(ValueError, match="attestation_judgment_content_invalid"):
        Attestation.issue(
            {
                "kind": "judgment",
                "issuer": "agent:local:task:one",
                "subject": "capability:context-projection",
                "issued_at": _ISSUED_AT,
                "verdict": "pass",
                "content": {"judgment": "semantic-disposition"},
            }
        )

    attestation = Attestation.issue(
        {
            "kind": "judgment",
            "issuer": "agent:local:task:one",
            "subject": "capability:context-projection",
            "issued_at": _ISSUED_AT,
            "verdict": "pass",
            "content": {
                "judgment": "semantic-disposition",
                "basis": "terminal product boundary",
                "state": "superseded",
            },
            "change_contract_digest": "a" * 64,
        }
    )

    assert attestation.kind == "judgment"


def test_external_assurance_requires_native_evidence_binding() -> None:
    with pytest.raises(ValueError, match="attestation_external_assurance_content_invalid"):
        Attestation.issue(
            {
                "kind": "external-assurance",
                "issuer": "provider:gitlab:project:ethos",
                "subject": "git:commit:" + "a" * 40,
                "issued_at": _ISSUED_AT,
                "verdict": "pass",
                "content": {"provider": "gitlab"},
            }
        )

    attestation = Attestation.issue(
        {
            "kind": "external-assurance",
            "issuer": "provider:gitlab:project:ethos",
            "subject": "git:commit:" + "a" * 40,
            "issued_at": _ISSUED_AT,
            "verdict": "pass",
            "content": {
                "provider": "gitlab",
                "verification_method": "hosted-ci",
                "valid_until": "2026-07-27T00:00:00+00:00",
            },
            "evidence_refs": ("provider:gitlab:pipeline:1",),
            "effect_digest": "a" * 64,
        }
    )

    assert attestation.kind == "external-assurance"


def test_semantic_values_are_immutable_and_digest_bound() -> None:
    issued_at = datetime(2026, 7, 25, tzinfo=UTC)
    attestation = _attestation(content={"nested": {"values": ["one", {"two": True}]}})
    facts = RepositoryFacts(
        repository="repository:ethos",
        head="a" * 40,
        tree="b" * 40,
        observed_at=issued_at,
        values={"nested": {"values": ["one", {"two": True}]}},
    )
    assert isinstance(attestation.content, MappingProxyType)
    assert attestation.content["nested"]["values"] == ("one", MappingProxyType({"two": True}))
    assert isinstance(facts.values, MappingProxyType)
    with pytest.raises(TypeError):
        operator.setitem(attestation.content, "new", "forbidden")
    with pytest.raises(TypeError):
        operator.setitem(facts.values["nested"], "new", "forbidden")
    assert (
        Attestation.model_validate(attestation.model_dump()).content_digest
        == attestation.content_digest
    )
    with pytest.raises(ValueError, match="attestation_content_digest_mismatch"):
        Attestation.model_validate_json(
            json.dumps(attestation.model_dump(mode="json") | {"content": {"state": "changed"}})
        )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), b"bytes"])
def test_semantic_json_rejects_values_without_portable_json_meaning(invalid: object) -> None:
    with pytest.raises(TypeError, match="json_value_invalid"):
        _attestation(content={"invalid": invalid})


@pytest.mark.parametrize(
    "invalid",
    ["scalar", ("array",), {1: "non-string-key"}, {"nested": {1: "non-string-key"}}],
)
def test_semantic_json_objects_reject_non_object_or_non_string_keys(invalid: object) -> None:
    with pytest.raises(TypeError, match=r"json_object_invalid|json_object_key_invalid"):
        _attestation(content=invalid)


def test_amendments_fold_in_order_and_require_authorized_fields() -> None:
    base = _contract(acceptance=("base",))
    authority = {"agent:local:task:one": ("acceptance",), "human:local:shell:owner": ("intent",)}
    first = _amendment(
        base,
        {"acceptance": ["base", "deterministic"]},
        issued_at=datetime(2026, 7, 25, 1, tzinfo=UTC),
    )
    after_first = apply_amendments(base, (first,), issuer_permissions=authority)
    second = _amendment(
        after_first,
        {"intent": "Establish the smallest deterministic terminal kernel."},
        issuer="human:local:shell:owner",
        issued_at=datetime(2026, 7, 25, 2, tzinfo=UTC),
    )
    effective = apply_amendments(base, (second, first), issuer_permissions=authority)
    assert (effective.intent, effective.acceptance) == (
        "Establish the smallest deterministic terminal kernel.",
        ("base", "deterministic"),
    )
    assert (
        effective.digest()
        == apply_amendments(base, (first, second), issuer_permissions=authority).digest()
    )


@pytest.mark.parametrize(
    ("patch", "authority", "error", "change_contract_digest", "kind"),
    [
        ({"intent": "Changed"}, None, "amendment_authority_missing", None, "amendment"),
        (
            {"intent": "Unbound"},
            None,
            "amendment_change_contract_digest_mismatch",
            "0" * 64,
            "amendment",
        ),
        ({"intent": "Ignored"}, None, "attestation_not_amendment", None, "observation"),
        (
            {"invented": "parallel ontology"},
            {"agent:local:task:one": ("invented",)},
            "amendment_field_unknown:invented",
            None,
            "amendment",
        ),
        (
            {"permissions": ["repository.write"]},
            {"authority:maintainer": ("intent",)},
            "amendment_issuer_unauthorized",
            None,
            "amendment",
        ),
        (
            {"permissions": ["repository.write"]},
            {"authority:maintainer": ("intent",)},
            "amendment_field_unauthorized:permissions",
            None,
            "amendment-authority",
        ),
    ],
)
def test_amendments_fail_closed_for_invalid_authority(
    patch: dict[str, object],
    authority: dict[str, tuple[str, ...]] | None,
    error: str,
    change_contract_digest: str | None,
    kind: str,
) -> None:
    base = _contract(authority_refs=("authority:maintainer",))
    if kind == "amendment-authority":
        amendment = _amendment(base, patch, issuer="authority:maintainer")
    else:
        amendment = _amendment(
            base,
            patch,
            change_contract_digest=change_contract_digest,
            kind=kind,
        )
    with pytest.raises(ValueError, match=error):
        apply_amendments(base, (amendment,), issuer_permissions=authority)


def test_amendment_fold_rejects_ambiguous_equal_sequence() -> None:
    base = _contract()
    issued_at = datetime(2026, 7, 25, tzinfo=UTC)
    first = _amendment(base, {"intent": "First"}, issued_at=issued_at, sequence=1)
    second = _amendment(
        base,
        {"intent": "Second"},
        issuer="agent:local:task:two",
        issued_at=issued_at,
        sequence=1,
    )
    with pytest.raises(ValueError, match="amendment_order_ambiguous"):
        apply_amendments(base, (second, first))


def test_amendment_fold_rejects_duplicate_attestation_identity() -> None:
    base = _contract()
    amendment = _amendment(base, {"intent": "Changed"})

    with pytest.raises(ValueError, match="attestation_duplicate"):
        apply_amendments(
            base,
            (amendment, amendment),
            issuer_permissions={"agent:local:task:one": ("intent",)},
        )


def test_schema_surfaces_are_generated_declared_and_valid() -> None:
    generated = semantic_schema_documents()
    assert set(generated) == {
        "change-contract.schema.json",
        "attestation.schema.json",
        "repository-facts.schema.json",
    }
    attestation_schema = generated["attestation.schema.json"]
    assert {
        "id",
        "verdict",
        "change_contract_digest",
        "repository_facts_digest",
        "plan_digest",
        "policy_digest",
        "effect_digest",
        "content_digest",
    } <= set(attestation_schema["required"])
    assert attestation_schema["properties"]["verdict"]["enum"] == [
        "pass",
        "block",
        "unknown",
    ]
    assert attestation_schema["properties"]["kind"]["enum"] == [
        "observation",
        "judgment",
        "proof",
        "effect",
        "external-assurance",
        "amendment",
    ]
    assert {
        clause["if"]["properties"]["kind"]["const"] for clause in attestation_schema["allOf"]
    } == set(attestation_schema["properties"]["kind"]["enum"])
    schema_dir = Path("system/schemas/kernel")
    expected = {
        "result.schema.json",
        *generated,
        "commit-policy.schema.json",
        "plan-ir.schema.json",
        "provenance.schema.json",
        "docs-registry.schema.json",
        "gate.schema.json",
        "assistant-projection.schema.json",
        "lane-lease.schema.json",
        "mutation-decision.schema.json",
        "workspace-status.schema.json",
        "authority.schema.json",
        "authority-graph.schema.json",
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
    for definition in (
        "branchBinding",
        "closeoutSupport",
        "foreignWorkLane",
        "unboundWorkLaneRef",
    ):
        properties = workspace_schema["$defs"][definition]["properties"]
        assert {
            "base_change_contract_digest",
            "contract_binding",
            "lease_state",
        } <= set(properties)
    assert workspace_schema["$defs"]["foreignWorkLane"]["properties"]["lease_state"]["enum"] == [
        "valid",
        "expired",
        "unknown",
        "missing",
    ]
    plan = PlanIR(
        **_PLAN_INPUTS, nodes=(PlanNode(id="land", kind="effect", command=("ethos", "land")),)
    )
    jsonschema.Draft202012Validator(
        json.loads((schema_dir / "plan-ir.schema.json").read_text())
    ).validate(plan.to_dict())


def test_result_contract_has_stable_top_level_fields() -> None:
    payload = EthosResult(
        command="status",
        ok=True,
        state="ready",
        summary={"branch": "dev"},
        next_actions=("ethos plan --changed",),
    ).to_dict()
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


def test_system_contracts_load_validate_and_fail_closed() -> None:
    report = system_contracts_report(Path())
    assert report["ok"] is True, report["required_gaps"]
    assert all(report["contracts"].values())
    assert set(report["contracts"]) >= {"authority", "evidence_boundaries", "lifecycle"}
    assert not any(
        "schema_ref_missing" in gap or "schema_violation" in gap for gap in report["required_gaps"]
    )
    contract = load_system_contract(Path(), "evidence_boundaries")
    assert contract["decision"]["verdicts"] == ["allow", "block", "defer"]
    assert "verdict" in contract["decision"]["required_fields"]
    assert {"dry_run_not_executed_proof", "digest_not_semantic", "promotion_not_absolute"} <= {
        entry["id"] for entry in contract["boundary"]
    }
    assert contract["truth"]["implies_absolute_correctness"] is False
    assert any(
        "schema_violation" in gap
        for gap in schema_validation_gaps(
            "authority",
            {"schema": "system/schemas/contracts/authority.schema.json"},
            Path("system/schemas/contracts/authority.schema.json"),
        )
    )
    assert load_system_contract(Path("/tmp"), "lifecycle")["node"]
    with pytest.raises(FileNotFoundError):
        load_system_contract(Path("/tmp"), "authority")


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


def test_governance_context_projects_repository_authority_without_shadow_models() -> None:
    context = governance_context(Path.cwd(), profile="product")
    assert context["repository"] == str(Path.cwd().resolve())
    assert "user_instruction" in context["authority_refs"]
    assert context["shared_commands"] == context["transition_commands"] == list(LIFECYCLE_COMMANDS)
    assert context["reader_projection_commands"] == ["ethos status"]
