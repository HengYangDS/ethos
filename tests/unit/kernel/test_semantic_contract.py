from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from typing import Any

import pytest
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from pydantic import ValidationError

from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from tests.support.semantic import commitment_fixture

_JSON_SCALAR = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-9_007_199_254_740_991, max_value=9_007_199_254_740_991)
    | st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=24)
)
_JSON_OBJECT = st.recursive(
    _JSON_SCALAR,
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(
            st.text(alphabet=st.characters(blacklist_categories=("Cs",)), min_size=1, max_size=12),
            children,
            max_size=4,
        )
    ),
    max_leaves=12,
).map(lambda value: value if isinstance(value, dict) else {"value": value})


def _attestation_payload() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "predicate": "observation:repository",
        "verifier": "agent:codex:task:model-promotion",
        "subject": "change:model-promotion-successor",
        "issued_at": datetime(2026, 8, 14, 12, 34, 56, 123400, tzinfo=UTC),
        "valid_from": None,
        "valid_until": None,
        "verdict": "pass",
        "payload": {
            "kind": "input:feedback",
            "body": {
                "occurrence": {"ordinal": 1, "source": "conversation:task"},
                "text": "Preserve this occurrence.",
            },
        },
        "relations": [
            {
                "kind": "relation:selected-for",
                "target_kind": "semantic:commitment",
                "target_id": "change:model-promotion-successor",
                "attributes": {},
            }
        ],
        "advisories": [],
        "evidence_refs": ["evidence:conversation:one"],
        "commitment_digest": "1" * 64,
        "facts_digest": None,
        "plan_digest": None,
        "policy_digest": None,
        "effect_digest": None,
        "mints_authority": False,
    }


def _commitment_payload() -> dict[str, Any]:
    return commitment_fixture(
        id="change:model-promotion-successor",
        acceptance=("selected_input_is_bound",),
    ).model_dump(mode="python")


def test_commitment_runtime_validation_matrix() -> None:
    payload = _commitment_payload()
    for field in payload:
        with pytest.raises(ValidationError):
            Commitment.model_validate(
                {key: value for key, value in payload.items() if key != field}
            )

    invalid = (
        ({"id": " "}, "string_pattern_mismatch"),
        ({"acceptance": []}, "commitment_string_value_invalid"),
        ({"acceptance": [" "]}, "commitment_string_value_invalid"),
        ({"scope": ["src/**"]}, None),
    )
    for update, error in invalid:
        with pytest.raises((TypeError, ValidationError), match=error):
            Commitment.model_validate(payload | update)

    acceptance = ["acceptance:\ue000", "acceptance:\U00010000"]
    ordered = Commitment.model_validate(payload | {"acceptance": acceptance})
    reordered = Commitment.model_validate(payload | {"acceptance": list(reversed(acceptance))})
    assert reordered == ordered
    assert reordered.digest() == ordered.digest()


def test_attestation_invalid_field_and_relation_matrix() -> None:
    payload = _attestation_payload()
    ordered = Attestation.issue(payload | {"advisories": ["advisory:one", "advisory:two"]})
    assert ordered == Attestation.issue(payload | {"advisories": ["advisory:two", "advisory:one"]})
    missing = {key: value for key, value in payload.items() if key != "facts_digest"}
    duplicate = dict(payload["relations"][0], attributes={"different": True})
    invalid = (
        (missing, None),
        (payload | {"mints_authority": True}, None),
        (
            payload | {"relations": [*payload["relations"], duplicate]},
            "attestation_relation_identity_duplicate",
        ),
        (payload | {"verifier": " "}, "commitment_string_value_invalid"),
        (payload | {"evidence_refs": [" "]}, "commitment_string_value_invalid"),
    )
    for candidate, error in invalid:
        with pytest.raises(ValidationError, match=error):
            Attestation.issue(candidate)


@pytest.mark.parametrize(
    ("raw", "strict", "error"),
    [
        (b'{"schema_version":2,"schema_version":2}', None, "semantic_object_key_duplicate"),
        (lambda value: b" " + value, None, "semantic_json_noncanonical"),
        (lambda value: value + b"\n", False, "semantic_json_noncanonical"),
        (
            lambda value: value.replace(b'"schema_version":3', b'"schema_version":3.5'),
            None,
            "semantic_json_value_invalid",
        ),
    ],
)
def test_semantic_json_reader_negative_matrix(raw, strict, error: str) -> None:
    canonical = Commitment.model_validate(_commitment_payload()).canonical_json().encode()
    candidate = raw(canonical) if callable(raw) else raw
    kwargs = {} if strict is None else {"strict": strict}
    with pytest.raises(ValueError, match=error):
        Commitment.model_validate_json(candidate, **kwargs)


@settings(max_examples=40, deadline=None)
@given(body=_JSON_OBJECT)
def test_attestation_unknown_payload_round_trips_without_authority(body: object) -> None:
    issued = Attestation.issue(
        _attestation_payload() | {"payload": {"kind": "input:future-feedback", "body": body}}
    )
    restored = Attestation.model_validate_json(issued.canonical_json())

    assert restored == issued
    assert restored.id == issued.id
    assert restored.payload.kind == "input:future-feedback"
    assert restored.relations[0].kind == "relation:selected-for"
    assert restored.mints_authority is False


def test_semantic_contract_golden_vectors_are_exact_in_source_wheel_and_sdist() -> None:
    root = __import__("pathlib").Path(__file__).parents[3]
    vector_path = root / "tests/fixtures/semantic-contract/vectors.json"
    source_bytes = vector_path.read_bytes()
    vectors = json.loads(source_bytes)
    assert vectors["schema_version"] == 1
    commitment_vector, attestation_vector = vectors["commitment"], vectors["attestation"]
    commitment = Commitment.model_validate_json(commitment_vector["canonical_json"])
    attestation = Attestation.model_validate_json(attestation_vector["carrier_json"])

    assert (commitment.canonical_json(), commitment.digest()) == (
        commitment_vector["canonical_json"],
        commitment_vector["digest"],
    )
    assert (attestation.canonical_json(exclude_id=True), attestation.id) == (
        attestation_vector["canonical_json_without_id"],
        attestation_vector["id"],
    )
    assert json.loads(source_bytes) == vectors
