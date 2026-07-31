from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest
from pydantic import ValidationError

from ethos.contracts.authority import AuthorityQuery
from ethos.contracts.authority import AuthorityResolution
from ethos.contracts.authority import CarrierDescriptor
from ethos.contracts.authority import resolve_authority

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
    declared_authority: bool = True,
) -> CarrierDescriptor:
    return CarrierDescriptor(
        role=role,
        declared_authority=declared_authority,
        query=query(plane=plane),
        assertion=assertion,
        bindings=(("head", "abc"),),
        source=f"{role}:test",
        valid_from=NOW - timedelta(minutes=1),
        valid_until=NOW + timedelta(minutes=1),
    )


def test_projection_adapter_and_history_never_authorize() -> None:
    result = resolve_authority(
        query(),
        tuple(descriptor(role) for role in ("projection", "adapter", "history")),
    )
    assert result.verdict == "unknown"
    assert result.required_gaps == ("unknown_required_fact",)


def test_role_without_declared_authority_never_authorizes() -> None:
    for role in ("native", "fact"):
        result = resolve_authority(
            query(),
            (descriptor(role, declared_authority=False),),
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


def test_authority_meaning_is_independent_of_mapping_order() -> None:
    first = descriptor("native", assertion={"a": 1, "b": 2})
    reordered = descriptor("fact", assertion={"b": 2, "a": 1})

    assert resolve_authority(query(), (first, reordered)).verdict == "pass"


def test_different_planes_are_not_globally_ranked() -> None:
    result = resolve_authority(query(), (descriptor("native", plane="hosted"),))

    assert result.verdict == "unknown"
    assert result.descriptors == ()
    assert result.required_gaps == ("unknown_required_fact",)


def test_authority_resolution_rejects_pass_with_required_gaps() -> None:
    with pytest.raises(ValidationError, match="pass_with_required_gaps"):
        AuthorityResolution(verdict="pass", required_gaps=("ambiguous_authority",))


def test_carrier_assertion_is_deeply_immutable() -> None:
    carrier = descriptor("native", assertion={"nested": {"value": True}})

    with pytest.raises(TypeError):
        carrier.assertion["nested"]["value"] = False
