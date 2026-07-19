from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierManifest
from ethos_core.contracts.source_budget.carriers import carrier_manifest_digest
from ethos_core.contracts.source_budget.carriers import carrier_manifest_json_schema
from ethos_core.contracts.source_budget.carriers import classify_carrier


def _identity(
    carrier_id: str,
    **overrides: object,
) -> CarrierIdentity:
    payload: dict[str, object] = {
        "carrier_id": carrier_id,
        "role": "authored_behavioral_source",
        "scope_id": "product.python",
        "disposition": "measure",
        "metric_profile": "python-source-v2",
        "extensions": (),
        "include": (),
        "exclude": (),
        "owner": "ethos-quality",
        "exclusion_reason": None,
    }
    payload.update(overrides)
    return CarrierIdentity.model_validate(payload)


def _manifest(*carriers: CarrierIdentity) -> CarrierManifest:
    return CarrierManifest(
        schema="ethos-source-budget-carriers-v2",
        contract_version=2,
        carriers=carriers,
    )


def test_carrier_identity_is_frozen_and_forbids_unknown_fields() -> None:
    identity = _identity("python-product", include=("packages/**",), extensions=(".py",))

    with pytest.raises(ValidationError):
        identity.carrier_id = "mutable"  # type: ignore[misc]

    payload = identity.model_dump()
    payload["priority"] = 1
    with pytest.raises(ValidationError, match="priority"):
        CarrierIdentity.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("include", ("/absolute/**",)),
        ("include", ("../outside/**",)),
        ("include", (r"packages\\**\\*.py",)),
        ("extensions", ("py",)),
        ("extensions", (".PY",)),
    ],
)
def test_carrier_identity_rejects_non_posix_or_non_normalized_matchers(
    field: str,
    value: tuple[str, ...],
) -> None:
    payload = _identity(
        "python-product",
        include=("packages/**",),
        extensions=(".py",),
    ).model_dump()
    payload[field] = value

    with pytest.raises(ValidationError):
        CarrierIdentity.model_validate(payload)


@pytest.mark.parametrize(
    ("disposition", "metric_profile", "exclusion_reason"),
    [
        ("measure", None, None),
        ("measure", "python-source-v2", "not allowed"),
        ("exclude", "python-source-v2", "generated"),
        ("exclude", None, None),
    ],
)
def test_carrier_identity_rejects_invalid_measure_exclusion_combinations(
    disposition: str,
    metric_profile: str | None,
    exclusion_reason: str | None,
) -> None:
    payload = _identity(
        "candidate",
        include=("packages/**",),
        extensions=(".py",),
    ).model_dump()
    payload.update(
        disposition=disposition,
        metric_profile=metric_profile,
        exclusion_reason=exclusion_reason,
    )

    with pytest.raises(ValidationError):
        CarrierIdentity.model_validate(payload)


def test_carrier_manifest_rejects_duplicate_ids_and_matcher_identities() -> None:
    first = _identity("first", include=("packages/**",), extensions=(".py",))
    duplicate_id = _identity("first", include=("tools/**",), extensions=(".py",))
    with pytest.raises(ValidationError, match="carrier ids"):
        _manifest(first, duplicate_id)

    duplicate_matcher = _identity("second", include=("packages/**",), extensions=(".py",))
    with pytest.raises(ValidationError, match="matcher"):
        _manifest(first, duplicate_matcher)


def test_carrier_classification_is_exact_one_and_explicit_for_exclusions() -> None:
    measured = _identity("python-product", include=("packages/**",), extensions=(".py",))
    excluded = _identity(
        "lockfiles",
        include=("vendor/**",),
        extensions=(".lock",),
        role="vendor_or_lock",
        scope_id="vendor.lock",
        disposition="exclude",
        metric_profile=None,
        exclusion_reason="Dependency resolution is governed separately.",
    )
    manifest = _manifest(measured, excluded)

    match = classify_carrier("packages/ethos/src/ethos/core.py", manifest)
    assert match.state == "classified"
    assert match.identity == measured
    assert match.matched_carrier_ids == ("python-product",)
    assert match.required_gaps == ()

    match = classify_carrier("vendor/dependencies.lock", manifest)
    assert match.state == "excluded"
    assert match.identity == excluded
    assert match.matched_carrier_ids == ("lockfiles",)
    assert match.required_gaps == ()


def test_carrier_classification_fails_closed_for_zero_multiple_and_unsupported() -> None:
    python = _identity("python", include=("packages/**",), extensions=(".py",))
    markdown = _identity(
        "docs",
        include=("docs/**",),
        extensions=(".md",),
        role="documentation",
        scope_id="documentation",
        metric_profile="documentation-v2",
    )
    overlapping = _identity(
        "python-overlap",
        include=("packages/ethos/**",),
        extensions=(".py",),
    )
    manifest = _manifest(python, markdown, overlapping)

    ambiguous = classify_carrier("packages/ethos/core.py", manifest)
    assert ambiguous.state == "ambiguous"
    assert ambiguous.identity is None
    assert ambiguous.matched_carrier_ids == ("python", "python-overlap")
    assert ambiguous.required_gaps == (
        "source_budget_carrier_ambiguous:packages/ethos/core.py:python,python-overlap",
    )

    unclassified = classify_carrier("README.md", manifest)
    assert unclassified.state == "unclassified"
    assert unclassified.identity is None
    assert unclassified.required_gaps == ("source_budget_carrier_unclassified:README.md",)

    unsupported = classify_carrier("packages/ethos/core.xyz", manifest)
    assert unsupported.state == "unsupported"
    assert unsupported.identity is None
    assert unsupported.required_gaps == (
        "source_budget_carrier_unsupported:packages/ethos/core.xyz:.xyz",
    )


def test_carrier_manifest_digest_is_order_independent_and_semantic() -> None:
    python = _identity("python", include=("packages/**",), extensions=(".py",))
    docs = _identity(
        "docs",
        include=("docs/**",),
        extensions=(".md",),
        role="documentation",
        scope_id="documentation",
        metric_profile="documentation-v2",
    )

    assert carrier_manifest_digest(_manifest(python, docs)) == carrier_manifest_digest(
        _manifest(docs, python)
    )

    changed = docs.model_copy(update={"owner": "different-owner"})
    assert carrier_manifest_digest(_manifest(python, docs)) != carrier_manifest_digest(
        _manifest(python, changed)
    )


def test_carrier_manifest_schema_is_compact_typed_projection() -> None:
    schema_path = Path("system/schemas/kernel/source-budget-carriers.schema.json")
    schema = carrier_manifest_json_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "ETHOS Source Budget Carrier Manifest"
    assert (
        schema_path.read_text(encoding="utf-8") == json.dumps(schema, separators=(",", ":")) + "\n"
    )
