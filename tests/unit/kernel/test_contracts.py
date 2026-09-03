from __future__ import annotations

import hashlib
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

import ethos.contracts.semantic as semantic
from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import terminal_schema_documents
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.system.contracts import SYSTEM_CONTRACTS
from ethos.contracts.system.contracts import load_system_contract
from ethos.contracts.system.contracts import schema_validation_gaps
from ethos.contracts.system.contracts import system_contracts_report
from ethos.contracts.value import mutable_json
from tests.support.semantic import commitment_fixture

_PLAN_COMMITMENT = commitment_fixture(id="change:test-plan", acceptance=("acceptance:fixture",))
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
_ISSUED_AT = datetime(2026, 7, 25, tzinfo=UTC)


def _attestation(
    *,
    payload: object,
    verdict: Literal["pass", "block", "unknown"] = "pass",
    advisories: tuple[str, ...] = (),
) -> Attestation:
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "observation:repository",
            "verifier": "agent:local:task:one",
            "subject": "change:terminal-kernel",
            "issued_at": _ISSUED_AT,
            "valid_from": None,
            "valid_until": None,
            "verdict": verdict,
            "payload": {"kind": "observation:repository", "body": payload},
            "relations": (),
            "advisories": advisories,
            "evidence_refs": (),
            "commitment_digest": "a" * 64,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": None,
            "mints_authority": False,
        }
    )


def test_commitment_identity_projection_is_explicit_and_schema_version_bound() -> None:
    commitment = commitment_fixture(
        id="change:terminal-kernel",
        acceptance=("acceptance:base",),
    )

    assert commitment.identity_projection() == {
        "schema_version": 3,
        "id": "change:terminal-kernel",
        "acceptance": ["acceptance:base"],
    }
    assert (
        commitment.digest()
        != commitment_fixture(
            id="change:terminal-kernel",
            acceptance=("acceptance:replacement",),
        ).digest()
    )


def test_system_contracts_report_fails_closed_for_every_carrier_state(tmp_path: Path) -> None:
    system = tmp_path / "system"
    schemas = tmp_path / "schemas"
    system.mkdir()
    schemas.mkdir()
    (system / "formats.toml").write_text("schema = 'schemas/formats.json'\n", encoding="utf-8")
    (system / "routing.toml").write_text("invalid = [\n", encoding="utf-8")
    (system / "surfaces.toml").write_text("schema = 'schemas/missing.json'\n", encoding="utf-8")
    (system / "tools.toml").write_text(
        "schema = 'schemas/tools.json'\nvalue = 1\n", encoding="utf-8"
    )
    (schemas / "formats.json").write_text("not-json", encoding="utf-8")
    (schemas / "tools.json").write_text(
        json.dumps({"type": "object", "required": ["required"]}), encoding="utf-8"
    )

    report = system_contracts_report(tmp_path)

    assert report["contracts"] == {
        "formats": True,
        "routing": False,
        "surfaces": True,
        "tools": True,
        "evidence_boundaries": False,
    }
    gaps = report["required_gaps"]
    assert any(str(gap).startswith("system_schema_unreadable:formats:") for gap in gaps)
    assert any(str(gap).startswith("system_contract_invalid:routing:") for gap in gaps)
    assert "system_schema_ref_missing:surfaces:schemas/missing.json" in gaps
    assert any(str(gap).startswith("system_contract_schema_violation:tools:") for gap in gaps)
    assert "system_contract_missing:evidence_boundaries" in gaps
    assert load_system_contract(tmp_path, "formats") == {"schema": "schemas/formats.json"}


def test_system_contracts_report_owns_declaration_identity_uniqueness(tmp_path: Path) -> None:
    """One system contract owner distinguishes duplicate and conflicting identities."""
    system = tmp_path / "system"
    schemas = tmp_path / "schemas"
    system.mkdir()
    schemas.mkdir()
    schema = schemas / "permissive.json"
    schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    for name in SYSTEM_CONTRACTS:
        (system / f"{name}.toml").write_text(
            "schema = 'schemas/permissive.json'\n",
            encoding="utf-8",
        )
    (system / "tools.toml").write_text(
        """schema = "schemas/permissive.json"

[[tool]]
concern = "lint"
tool = "ruff"

[[tool]]
concern = "lint"
tool = "ruff"
""",
        encoding="utf-8",
    )
    (system / "surfaces.toml").write_text(
        """schema = "schemas/permissive.json"

[[surface]]
name = "cli"
carrier = "first"

[[surface]]
name = "cli"
carrier = "second"
""",
        encoding="utf-8",
    )

    report = system_contracts_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["declaration_issues"] == [
        {
            "category": "conflict",
            "relation": "owner",
            "kind": "surface",
            "identity": "cli",
            "sources": ["system/surfaces.toml"],
        },
        {
            "category": "duplicate",
            "relation": "owner",
            "kind": "tool",
            "identity": "lint",
            "sources": ["system/tools.toml"],
        },
    ]
    assert report["required_gaps"] == [
        "semantic_owner_conflict:surface:cli:system/surfaces.toml",
        "semantic_owner_duplicate:tool:lint:system/tools.toml",
    ]


def test_system_contract_schema_validation_accepts_a_matching_document(tmp_path: Path) -> None:
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps({"type": "object", "required": ["id"]}), encoding="utf-8")

    assert schema_validation_gaps("sample", {"id": "sample"}, schema) == []
    assert tuple(SYSTEM_CONTRACTS) == (
        "formats",
        "routing",
        "surfaces",
        "tools",
        "evidence_boundaries",
    )


@pytest.mark.parametrize("field", ["campaign", "collaboration", "compatibility", "publication"])
def test_commitment_rejects_process_and_distribution_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        Commitment.model_validate(
            commitment_fixture(
                id="change:terminal-kernel", acceptance=("acceptance:fixture",)
            ).model_dump(mode="python")
            | {field: "retired"}
        )


def test_commitment_rejects_reusable_permissions() -> None:
    with pytest.raises(ValidationError):
        Commitment.model_validate(
            commitment_fixture(
                id="change:terminal-kernel", acceptance=("acceptance:fixture",)
            ).model_dump(mode="python")
            | {"permissions": ("git.ref.compare-and-swap",)}
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


def test_attestation_identity_and_serialization_are_payload_addressed() -> None:
    first = _attestation(
        payload={"z": ["one", {"two": True}], "a": {"nested": "value"}},
        advisories=("non_blocking_note",),
    )
    reordered = _attestation(
        payload={"a": {"nested": "value"}, "z": ["one", {"two": True}]},
        advisories=("non_blocking_note",),
    )

    assert len(first.id) == 64
    assert first.id == reordered.id
    assert first.canonical_json() == reordered.canonical_json()
    assert json.loads(first.canonical_json()) == first.model_dump(mode="json")
    assert first.verdict == "pass"
    assert first.advisories == ("non_blocking_note",)
    assert (
        _attestation(
            payload={"z": ["one", {"two": True}], "a": {"nested": "value"}},
            verdict="unknown",
            advisories=("non_blocking_note",),
        ).id
        != first.id
    )

    forged = first.model_dump(mode="json")
    forged["id"] = "f" * 64
    with pytest.raises(ValueError, match="attestation_identity_mismatch"):
        Attestation.model_validate_json(json.dumps(forged))


def test_attestation_mapping_round_trip_normalizes_fractional_time() -> None:
    issued = datetime(2026, 8, 16, 9, 6, 13, 523640, tzinfo=UTC)
    base = _attestation(payload={"state": "observed"})
    attestation = Attestation.issue(
        base.model_dump(mode="python", exclude={"id"}) | {"issued_at": issued, "valid_from": issued}
    )

    payload = attestation.model_dump(mode="json")

    assert payload["issued_at"] == "2026-08-16T09:06:13.523640Z"
    assert Attestation.model_validate(payload).id == attestation.id
    with pytest.raises(ValueError, match="semantic_json_noncanonical"):
        Attestation.model_validate_json(json.dumps(payload, separators=(",", ":")))


def test_attestation_requires_closed_verdict_and_at_least_one_binding() -> None:
    attestation = _attestation(payload={"required_gaps": ["proof_missing"]}, verdict="block")
    payload = attestation.model_dump(mode="json")
    payload["verdict"] = "pass"
    with pytest.raises(ValueError, match="pass_with_required_gaps"):
        Attestation.model_validate(payload)

    attestation = _attestation(payload={"state": "observed"})
    payload = attestation.model_dump(mode="json")
    payload["facts_digest"] = "not-a-digest"
    with pytest.raises(ValidationError):
        Attestation.model_validate(payload)

    with pytest.raises(ValueError, match="attestation_binding_missing"):
        Attestation.issue(
            {
                "schema_version": 2,
                "predicate": "observation:repository",
                "verifier": "agent:local:task:one",
                "subject": "change:terminal-kernel",
                "issued_at": _ISSUED_AT,
                "valid_from": None,
                "valid_until": None,
                "verdict": "pass",
                "payload": {"kind": "observation:repository", "body": {"state": "observed"}},
                "relations": (),
                "advisories": (),
                "evidence_refs": (),
                "commitment_digest": None,
                "facts_digest": None,
                "plan_digest": None,
                "policy_digest": None,
                "effect_digest": None,
                "mints_authority": False,
            }
        )


def test_semantic_values_are_immutable_and_digest_bound() -> None:
    issued_at = datetime(2026, 7, 25, tzinfo=UTC)
    attestation = _attestation(payload={"nested": {"values": ["one", {"two": True}]}})
    facts = Facts(
        repository="repository:ethos",
        head="a" * 40,
        tree="b" * 40,
        observed_at=issued_at,
        values={"nested": {"values": ["one", {"two": True}]}},
    )
    assert isinstance(attestation.payload.body, MappingProxyType)
    assert attestation.payload.body["nested"]["values"] == (
        "one",
        MappingProxyType({"two": True}),
    )
    assert isinstance(facts.values, MappingProxyType)
    with pytest.raises(TypeError):
        operator.setitem(attestation.payload.body, "new", "forbidden")
    with pytest.raises(TypeError):
        operator.setitem(facts.values["nested"], "new", "forbidden")
    assert Attestation.model_validate(attestation.model_dump()).id == attestation.id
    with pytest.raises(ValueError, match="attestation_identity_mismatch"):
        Attestation.model_validate_json(
            json.dumps(
                attestation.model_dump(mode="json")
                | {"payload": {"kind": "observation:repository", "body": {"state": "changed"}}}
            )
        )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), b"bytes"])
def test_semantic_json_rejects_values_without_portable_json_meaning(invalid: object) -> None:
    with pytest.raises(TypeError, match="json_value_invalid"):
        _attestation(payload={"invalid": invalid})


@pytest.mark.parametrize(
    "invalid",
    ["scalar", ("array",), {1: "non-string-key"}, {"nested": {1: "non-string-key"}}],
)
def test_semantic_json_objects_reject_non_object_or_non_string_keys(invalid: object) -> None:
    with pytest.raises(TypeError, match=r"json_object_invalid|json_object_key_invalid"):
        _attestation(payload=invalid)


@pytest.mark.parametrize(
    ("factory", "expected_digest"),
    [
        pytest.param(
            lambda value: commitment_fixture(
                id="change:digest-matrix",
                acceptance=(f"acceptance:{value}",),
            ),
            lambda model: hashlib.sha256(
                b"ethos.commitment.v3\0" + model.canonical_json().encode()
            ).hexdigest(),
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
            lambda model: canonical_json_digest(
                model.model_dump(mode="json", exclude={"observed_at"})
            ),
            id="facts",
        ),
        pytest.param(
            lambda value: _attestation(payload={"value": value}),
            lambda model: hashlib.sha256(
                b"ethos.attestation.v2\0" + model.canonical_json(exclude_id=True).encode()
            ).hexdigest(),
            id="attestation",
        ),
    ],
)
def test_semantic_digest_matrix_binds_each_canonical_identity(factory, expected_digest) -> None:
    first = factory("first")
    repeated = factory("first")
    changed = factory("second")

    assert first.digest() == repeated.digest()
    assert first.digest() != changed.digest()
    expected = expected_digest(first)
    assert first.digest() == expected
    if isinstance(first, Attestation):
        assert first.digest() == first.id


@pytest.mark.parametrize(
    ("factory", "field", "replacement", "error"),
    [
        pytest.param(
            lambda: _attestation(payload={"state": "observed"}),
            "payload",
            {"kind": "observation:repository", "body": {"state": "tampered"}},
            "attestation_identity_mismatch",
            id="attestation-payload",
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


def test_canonical_json_bytes_use_utf16_key_order_and_utf8_strings() -> None:
    canonical_json_bytes = getattr(semantic, "canonical_json_bytes", None)
    assert callable(canonical_json_bytes)
    value = MappingProxyType(
        {
            "\ue000": "bmp",
            "\U00010000": "astral",
            "label": "café",
        }
    )
    expected = b'{"label":"caf\xc3\xa9","\xf0\x90\x80\x80":"astral","\xee\x80\x80":"bmp"}'

    assert canonical_json_bytes(value) == expected
    assert canonical_json_digest(value) == hashlib.sha256(expected).hexdigest()


@pytest.mark.parametrize(
    ("invalid", "error"),
    [
        pytest.param(1.5, "semantic_json_value_invalid", id="float"),
        pytest.param("\ud800", "semantic_string_surrogate_invalid", id="surrogate"),
        pytest.param(9_007_199_254_740_992, "semantic_integer_out_of_range", id="integer"),
    ],
)
def test_canonical_json_digest_rejects_values_outside_closed_grammar(
    invalid: object, error: str
) -> None:
    with pytest.raises((TypeError, ValueError), match=error):
        canonical_json_digest({"value": invalid})


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
    assert commitment["properties"]["schema_version"]["const"] == 3
    assert set(commitment["required"]) == set(commitment["properties"])
    assert set(commitment["properties"]) == {"schema_version", "id", "acceptance"}
    assert all("default" not in field for field in commitment["properties"].values())
    assert not {"campaign", "collaboration", "compatibility", "publication"} & set(
        commitment["properties"]
    )
    structurally_valid = commitment_fixture(
        id="change:schema-projection",
        acceptance=("acceptance:fixture",),
    ).model_dump(mode="json")
    assert list(jsonschema.Draft202012Validator(commitment).iter_errors(structurally_valid)) == []
    attestation = generated["attestation.schema.json"]
    assert set(attestation["required"]) == set(attestation["properties"])
    assert all("default" not in field for field in attestation["properties"].values())
    assert {"payload", "relations"} <= set(attestation["properties"])
    assert not {"statement", "statement_digest"} & set(attestation["properties"])
    assert attestation["properties"]["mints_authority"]["const"] is False
    assert attestation["properties"]["verdict"]["enum"] == ["pass", "block", "unknown"]
    assert "enum" not in attestation["properties"]["predicate"]
    plan = generated["transition-plan.schema.json"]
    assert set(plan["required"]) == {
        "schema_version",
        "inputs",
        "request",
        "authority",
        "commitment",
        "prior_attestations",
        "policy",
        "effect",
        "facts",
        "nodes",
        "compensations",
        "postconditions",
        "verdict",
        "required_gaps",
        "continuation",
        "digest",
    }
