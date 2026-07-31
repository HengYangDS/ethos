from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest
from pydantic import ValidationError

from ethos.contracts.authority import AuthorityQuery
from ethos.contracts.authority import AuthorityResolution
from ethos.contracts.authority import CarrierDescriptor
from ethos.contracts.authority import extract_carrier_descriptor
from ethos.contracts.authority import resolve_authority
from ethos.contracts.semantic import Attestation

NOW = datetime(2026, 7, 29, tzinfo=UTC)


def query(*, plane: str = "local") -> AuthorityQuery:
    return AuthorityQuery(
        subject="git:commit:abc",
        predicate="proof:execution",
        scope=("repository",),
        plane=plane,
        validity=NOW,
        context=(("profile", "product"),),
    )


def descriptor(
    role: str,
    *,
    assertion: object = True,
    plane: str = "local",
) -> CarrierDescriptor:
    return CarrierDescriptor(
        role=role,
        query=query(plane=plane),
        assertion=assertion,
        bindings=(("head", "abc"),),
        source=f"{role}:test",
        valid_from=NOW - timedelta(minutes=1),
        valid_until=NOW + timedelta(minutes=1),
    )


def test_five_carrier_roles_extract_without_persistent_registry() -> None:
    for role in ("native", "projection", "adapter", "fact", "history"):
        result = extract_carrier_descriptor(descriptor(role).model_dump())
        assert result.descriptor is not None
        assert result.descriptor.role == role
        assert result.required_gaps == ()


def test_incomplete_or_unknown_carrier_meaning_is_model_gap() -> None:
    assert extract_carrier_descriptor({"role": "native"}).required_gaps == ("model_gap",)
    assert extract_carrier_descriptor(
        descriptor("native").model_dump() | {"role": "registry"}
    ).required_gaps == ("model_gap",)


def test_authority_descriptor_requires_explicit_scope_plane_and_context() -> None:
    incomplete = {"role": "fact", "source": "attestation:test"}
    complete = descriptor("fact").model_dump()

    assert extract_carrier_descriptor(incomplete).required_gaps == ("model_gap",)
    extracted = extract_carrier_descriptor(complete)
    assert extracted.required_gaps == ()
    assert extracted.descriptor is not None
    assert extracted.descriptor.query == query()


def test_projection_adapter_and_history_never_authorize() -> None:
    result = resolve_authority(
        query(),
        tuple(descriptor(role) for role in ("projection", "adapter", "history")),
    )
    assert result.verdict == "unknown"
    assert result.required_gaps == ("unknown_required_fact",)


def test_fact_requires_current_validity() -> None:
    expired = descriptor("fact").model_copy(update={"valid_until": NOW - timedelta(seconds=1)})
    timeless = descriptor("fact").model_copy(update={"valid_from": None, "valid_until": None})

    assert resolve_authority(query(), (expired,)).required_gaps == ("unknown_required_fact",)
    assert resolve_authority(query(), (timeless,)).required_gaps == ("unknown_required_fact",)


def test_equal_meaning_passes_and_contradiction_blocks() -> None:
    first = descriptor("native")
    equal = descriptor("fact").model_copy(update={"bindings": (("head", "different"),)})
    conflict = descriptor("native", assertion=False)

    assert resolve_authority(query(), (first, equal)).verdict == "pass"
    blocked = resolve_authority(query(), (first, conflict))
    assert blocked.verdict == "block"
    assert blocked.required_gaps == ("contradiction",)


def test_attestation_envelope_does_not_imply_authority_meaning() -> None:
    attestation = Attestation.issue(
        {
            "predicate": "experiment:novel",
            "verifier": "agent:test",
            "subject": "git:commit:abc",
            "issued_at": NOW,
            "verdict": "pass",
            "statement": {"scope": ["repository"], "plane": "local", "context": {}},
            "plan_digest": "a" * 64,
        }
    )

    assert attestation.predicate == "experiment:novel"
    assert extract_carrier_descriptor(attestation.model_dump()).required_gaps == ("model_gap",)


def test_different_planes_are_not_globally_ranked() -> None:
    result = resolve_authority(query(), (descriptor("native", plane="hosted"),))

    assert result.verdict == "unknown"
    assert result.descriptors == ()
    assert result.required_gaps == ("unknown_required_fact",)


def test_authority_resolution_rejects_pass_with_required_gaps() -> None:
    with pytest.raises(ValidationError, match="pass_with_required_gaps"):
        AuthorityResolution(verdict="pass", required_gaps=("ambiguous_authority",))
