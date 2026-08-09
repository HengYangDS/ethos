from __future__ import annotations

import json
import operator
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Literal

import jsonschema
import pytest
from pydantic import ValidationError

from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import terminal_schema_documents
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json

_PLAN_COMMITMENT = Commitment(
    id="change:test-plan",
    intent="Exercise one transition plan.",
    subjects=("repository:test",),
)
_PLAN_FACTS = Facts(
    repository="repository:test",
    head="a" * 40,
    tree="b" * 40,
    observed_at=datetime(2026, 7, 25, tzinfo=UTC),
    values={},
)
_PLAN_POLICY = {"name": "test"}
_PLAN_EFFECT = {"operation": "test"}
_PLAN_INPUTS = {
    "inputs": PlanInputs(
        commitment=_PLAN_COMMITMENT.digest(),
        facts=_PLAN_FACTS.digest(),
        policy=canonical_json_digest(_PLAN_POLICY),
        effect=canonical_json_digest(_PLAN_EFFECT),
    ),
    "closure": {
        "commitment": _PLAN_COMMITMENT.identity_projection(),
        "prior_attestations": {},
        "policy": _PLAN_POLICY,
        "effect": _PLAN_EFFECT,
    },
    "facts": _PLAN_FACTS.model_dump(mode="json", exclude={"observed_at"}),
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


@pytest.mark.parametrize(
    ("factory", "projection"),
    [
        pytest.param(
            lambda value: Commitment(
                id="change:digest-matrix",
                intent="Bind commitment identity.",
                subjects=("repository:test",),
                risks=(str(value),),
            ),
            lambda model: model.identity_projection(),
            id="commitment",
        ),
        pytest.param(
            lambda value: Facts(
                repository="repository:test",
                head="a" * 40,
                tree="b" * 40,
                observed_at=_ISSUED_AT,
                values={"value": value},
            ),
            lambda model: model.model_dump(mode="json", exclude={"observed_at"}),
            id="facts",
        ),
        pytest.param(
            lambda value: _attestation(statement={"value": value}),
            lambda model: model.model_dump(mode="json", exclude={"id"}),
            id="attestation",
        ),
    ],
)
def test_semantic_digest_matrix_binds_each_canonical_identity(factory, projection) -> None:
    first = factory("first")
    repeated = factory("first")
    changed = factory("second")

    assert first.digest() == repeated.digest()
    assert first.digest() != changed.digest()
    assert first.digest() == canonical_json_digest(projection(first))


@pytest.mark.parametrize(
    ("factory", "field", "replacement", "error"),
    [
        pytest.param(
            lambda: _attestation(statement={"state": "observed"}),
            "statement",
            {"state": "tampered"},
            "attestation_statement_digest_mismatch",
            id="attestation-statement",
        ),
        pytest.param(
            lambda: TransitionPlan.compile(**_PLAN_INPUTS),
            "effect",
            {"operation": "tampered"},
            "transition_plan_closure_mismatch",
            id="plan-effect",
        ),
        pytest.param(
            lambda: TransitionPlan.compile(**_PLAN_INPUTS),
            "digest",
            "f" * 64,
            "transition_plan_digest_mismatch",
            id="plan-digest",
        ),
    ],
)
def test_digest_bound_contract_matrix_rejects_tampering(
    factory, field: str, replacement: object, error: str
) -> None:
    model = factory()
    payload = model.model_dump()
    payload[field] = replacement

    with pytest.raises(ValueError, match=error):
        type(model).model_validate(payload)


def test_canonical_value_algebra_is_provider_neutral_and_recursive() -> None:
    value = MappingProxyType(
        {
            "z": (MappingProxyType({"nested": True}),),
            "a": MappingProxyType({"items": ("one", 2, None)}),
        }
    )

    assert mutable_json(value) == {
        "z": [{"nested": True}],
        "a": {"items": ["one", 2, None]},
    }
    assert json.loads(json.dumps(mutable_json(value))) == mutable_json(value)


def test_schema_surfaces_are_generated_declared_and_valid() -> None:
    generated = terminal_schema_documents()
    expected = {
        "commitment.schema.json": Commitment,
        "attestation.schema.json": Attestation,
        "facts.schema.json": Facts,
        "transition-plan.schema.json": TransitionPlan,
    }

    assert set(generated) == set(expected)
    for name, model in expected.items():
        schema = generated[name]
        persisted = json.loads((Path("system/schemas/kernel") / name).read_text(encoding="utf-8"))
        assert schema == persisted
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["title"] == f"ETHOS {model.__name__}"
        jsonschema.Draft202012Validator.check_schema(schema)

    commitment = generated["commitment.schema.json"]
    assert commitment["properties"]["schema_version"]["const"] == 1
    assert not {"campaign", "collaboration", "compatibility", "publication"} & set(
        commitment["properties"]
    )
    attestation = generated["attestation.schema.json"]
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
    } <= set(attestation["required"])
    assert attestation["properties"]["verdict"]["enum"] == ["pass", "block", "unknown"]
    assert "enum" not in attestation["properties"]["predicate"]
    assert not {"kind", "content", "sequence", "mints_authority"} & set(attestation["properties"])
    plan = generated["transition-plan.schema.json"]
    assert set(plan["required"]) == {
        "schema_version",
        "inputs",
        "commitment",
        "prior_attestations",
        "policy",
        "effect",
        "permissions",
        "facts",
        "nodes",
        "verdict",
        "required_gaps",
        "digest",
    }
