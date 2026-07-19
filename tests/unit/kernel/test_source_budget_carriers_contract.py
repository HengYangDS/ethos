from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.carriers import CarrierInventory
from ethos_core.contracts.source_budget.carriers import CarrierManifest
from ethos_core.contracts.source_budget.carriers import CarrierManifestLoad
from ethos_core.contracts.source_budget.carriers import CarrierMatch
from ethos_core.contracts.source_budget.carriers import carrier_manifest_digest
from ethos_core.contracts.source_budget.carriers import carrier_manifest_json_schema
from ethos_core.contracts.source_budget.carriers import classify_carrier
from ethos_core.contracts.source_budget.carriers import classify_carriers


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
        ("include", ("packages/**", "packages/**")),
        ("include", ("bad\udcff/**",)),
        ("include", ("../outside/**",)),
        ("include", ("packages//**",)),
        ("include", ("packages/./**",)),
        ("include", ("packages/***",)),
        ("include", ("packages/**/**",)),
        ("include", ("packages/**/*",)),
        ("include", ("packages/**/[a].py",)),
        ("include", ("packages/**/?.py",)),
        ("include", ("*/**",)),
        ("include", ("**/*/*",)),
        ("include", ("**/*/**",)),
        ("include", (".gitignore", "**/.gitignore")),
        ("include", (".",)),
        ("include", ("packages/",)),
        ("include", (r"packages\\**\\*.py",)),
        ("extensions", ("py",)),
        ("extensions", (".py", ".py")),
        ("extensions", (".PY",)),
        ("extensions", (".py", ".foo.py")),
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


def test_carrier_matcher_validator_fails_closed_on_surrogate_input() -> None:
    with pytest.raises(ValueError, match="repository-relative POSIX paths"):
        CarrierIdentity.validate_matchers(("bad\udcff/**",))


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


def test_carrier_identity_rejects_suffix_glob_when_extensions_own_suffix() -> None:
    with pytest.raises(ValidationError, match="extensions"):
        _identity(
            "python-product",
            include=("**/*.py",),
            extensions=(".py",),
        )


def test_carrier_manifest_rejects_duplicate_ids_and_matcher_identities() -> None:
    first = _identity("first", include=("packages/**",), extensions=(".py",))
    duplicate_id = _identity("first", include=("tools/**",), extensions=(".py",))
    with pytest.raises(ValidationError, match="carrier ids"):
        _manifest(first, duplicate_id)

    duplicate_matcher = _identity("second", include=("packages/**",), extensions=(".py",))
    with pytest.raises(ValidationError, match="matcher"):
        _manifest(first, duplicate_matcher)


def test_carrier_manifest_requires_public_schema_alias() -> None:
    identity = _identity("python", include=("packages/**",), extensions=(".py",))
    payload = _manifest(identity).model_dump(mode="json", by_alias=True)
    payload["schema_id"] = payload.pop("schema")

    with pytest.raises(ValidationError, match="schema"):
        CarrierManifest.model_validate(payload)


def test_carrier_manifest_load_rejects_impossible_envelope_states() -> None:
    identity = _identity("python", include=("packages/**",), extensions=(".py",))

    with pytest.raises(ValueError, match="required gaps"):
        CarrierManifestLoad(None, ())

    with pytest.raises(ValueError, match="required gaps"):
        CarrierManifestLoad(_manifest(identity), ("unexpected_gap",))

    with pytest.raises(ValueError, match="typed manifest"):
        CarrierManifestLoad(object(), ())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="tuple"):
        CarrierManifestLoad(None, ["gap"])  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="non-empty strings"):
        CarrierManifestLoad(None, ("",))

    with pytest.raises(ValueError, match="unique and stably ordered"):
        CarrierManifestLoad(None, ("z", "a", "z"))


def test_carrier_result_models_reject_cross_field_inconsistency() -> None:
    with pytest.raises(ValidationError, match="classification result"):
        CarrierMatch(
            relative_path="packages/ethos/core.py",
            state="classified",
            identity=None,
            matched_carrier_ids=(),
            required_gaps=(),
        )

    failure = CarrierMatch(
        relative_path="README.md",
        state="unclassified",
        identity=None,
        matched_carrier_ids=(),
        required_gaps=("source_budget_carrier_unclassified:README.md",),
    )
    with pytest.raises(ValidationError, match="inventory required gaps"):
        CarrierInventory(
            manifest_digest="a" * 64,
            inventory_digest="b" * 64,
            matches=(failure,),
            required_gaps=(),
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"relative_path": "../escape"},
        {"required_gaps": ("",)},
        {"required_gaps": ("z", "a", "z")},
        {
            "state": "ambiguous",
            "matched_carrier_ids": ("", "valid"),
            "required_gaps": ("ambiguous",),
        },
    ],
)
def test_carrier_match_rejects_forged_path_ids_or_gaps(
    overrides: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "relative_path": "README.md",
        "state": "unclassified",
        "identity": None,
        "matched_carrier_ids": (),
        "required_gaps": ("source_budget_carrier_unclassified:README.md",),
    }
    payload.update(overrides)

    with pytest.raises(ValidationError):
        CarrierMatch.model_validate(payload)


def test_carrier_match_rejects_complete_result_envelope_forgeries() -> None:
    identity = _identity("python", include=("packages/**",), extensions=(".py",))
    invalid_label = f"<invalid-path:{'a' * 64}>"
    invalid_cases = (
        (
            {
                "relative_path": "README.md",
                "path_state": "invalid",
                "state": "unclassified",
                "identity": None,
                "matched_carrier_ids": (),
                "required_gaps": ("invalid",),
            },
            "synthetic label",
        ),
        (
            {
                "relative_path": invalid_label,
                "path_state": "invalid",
                "state": "unsupported",
                "identity": None,
                "matched_carrier_ids": (),
                "required_gaps": ("invalid",),
            },
            "must be unclassified",
        ),
        (
            {
                "relative_path": "README.md",
                "state": "ambiguous",
                "identity": None,
                "matched_carrier_ids": ("z", "a", "z"),
                "required_gaps": ("ambiguous",),
            },
            "matched ids must be stable",
        ),
        (
            {
                "relative_path": "packages/a.py",
                "state": "classified",
                "identity": identity,
                "matched_carrier_ids": ("other",),
                "required_gaps": (),
            },
            "one matched identity",
        ),
        (
            {
                "relative_path": "packages/a.py",
                "state": "classified",
                "identity": identity,
                "matched_carrier_ids": ("python",),
                "required_gaps": ("unexpected",),
            },
            "success forbids",
        ),
        (
            {
                "relative_path": "README.md",
                "state": "unclassified",
                "identity": identity,
                "matched_carrier_ids": (),
                "required_gaps": ("unclassified",),
            },
            "failure forbids identity",
        ),
        (
            {
                "relative_path": "README.md",
                "state": "unclassified",
                "identity": None,
                "matched_carrier_ids": (),
                "required_gaps": (),
            },
            "failure requires required gaps",
        ),
        (
            {
                "relative_path": "README.md",
                "state": "ambiguous",
                "identity": None,
                "matched_carrier_ids": ("one",),
                "required_gaps": ("ambiguous",),
            },
            "ambiguity requires multiple ids",
        ),
        (
            {
                "relative_path": "README.md",
                "state": "unsupported",
                "identity": None,
                "matched_carrier_ids": ("one",),
                "required_gaps": ("unsupported",),
            },
            "failure forbids matched ids",
        ),
    )

    for payload, message in invalid_cases:
        with pytest.raises(ValidationError, match=message):
            CarrierMatch.model_validate(payload)


def test_carrier_inventory_rejects_unstable_or_duplicate_match_order() -> None:
    manifest = _manifest(_identity("all", include=("**",)))
    inventory = classify_carriers(("a.py", "b.py"), manifest)

    with pytest.raises(ValidationError, match="stably ordered"):
        CarrierInventory(
            manifest_digest=inventory.manifest_digest,
            inventory_digest=inventory.inventory_digest,
            matches=tuple(reversed(inventory.matches)),
            required_gaps=inventory.required_gaps,
        )

    with pytest.raises(ValidationError, match="stably ordered"):
        CarrierInventory(
            manifest_digest=inventory.manifest_digest,
            inventory_digest=inventory.inventory_digest,
            matches=(inventory.matches[0], inventory.matches[0]),
            required_gaps=inventory.required_gaps,
        )


def test_carrier_inventory_rejects_forged_digest() -> None:
    manifest = _manifest(_identity("all", include=("**",)))
    inventory = classify_carriers(("a.py",), manifest)
    payload = inventory.model_dump()
    payload["inventory_digest"] = "0" * 64

    with pytest.raises(ValidationError, match="inventory digest"):
        CarrierInventory.model_validate(payload)


def test_carrier_inventory_digest_binds_full_identity_semantics() -> None:
    manifest = _manifest(_identity("all", include=("**",)))
    inventory = classify_carriers(("a.py",), manifest)
    identity = inventory.matches[0].identity
    assert identity is not None
    forged_match = inventory.matches[0].model_copy(
        update={"identity": identity.model_copy(update={"owner": "forged-owner"})}
    )

    with pytest.raises(ValidationError, match="inventory digest"):
        CarrierInventory(
            manifest_digest=inventory.manifest_digest,
            inventory_digest=inventory.inventory_digest,
            matches=(forged_match,),
            required_gaps=inventory.required_gaps,
        )


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


def test_carrier_classification_fails_closed_for_surrogate_paths() -> None:
    manifest = _manifest(
        _identity("python", include=("**",), extensions=(".py",)),
    )

    match = classify_carrier("bad\udcff.py", manifest)

    assert match.relative_path.startswith("<invalid-path:")
    assert match.relative_path.endswith(">")
    assert match.state == "unclassified"
    assert match.identity is None
    assert match.matched_carrier_ids == ()
    assert match.required_gaps == (f"source_budget_carrier_path_invalid:{match.relative_path}",)


@pytest.mark.parametrize(
    "relative",
    ["/absolute.py", "foo//bar.py", "foo/./bar.py", ".", "foo/"],
)
def test_carrier_classification_rejects_noncanonical_paths(relative: str) -> None:
    manifest = _manifest(
        _identity("all", include=("**",)),
    )

    match = classify_carrier(relative, manifest)

    assert match.relative_path.startswith("<invalid-path:")
    assert match.relative_path.endswith(">")
    assert match.state == "unclassified"
    assert match.identity is None
    assert match.required_gaps == (f"source_budget_carrier_path_invalid:{match.relative_path}",)


def test_carrier_globs_are_path_segment_aware() -> None:
    shallow = _identity(
        "shallow-python",
        include=("packages/*",),
        extensions=(".py",),
    )
    recursive = _identity(
        "recursive-python",
        include=("packages/**",),
        extensions=(".py",),
        owner="recursive-owner",
    )
    root_markdown = _identity(
        "root-markdown",
        include=("*.md",),
        extensions=(),
        role="documentation",
        scope_id="documentation.root",
        metric_profile="documentation-v2",
    )
    manifest = _manifest(shallow, recursive, root_markdown)

    nested_python = classify_carrier("packages/a/b.py", manifest)
    nested_markdown = classify_carrier("docs/guide.md", manifest)

    assert nested_python.state == "classified"
    assert nested_python.identity == recursive
    assert nested_markdown.state == "unsupported"


def test_empty_carrier_inventory_is_a_required_gap() -> None:
    manifest = _manifest(
        _identity("all", include=("**",)),
    )

    inventory = classify_carriers((), manifest)

    assert inventory.matches == ()
    assert inventory.required_gaps == ("source_budget_carrier_inventory_empty",)


def test_carrier_inventory_does_not_erase_invalid_label_collisions() -> None:
    manifest = _manifest(_identity("all", include=("**",)))

    inventory = classify_carriers(("!\udcff", "<invalid-path>"), manifest)

    assert len(inventory.matches) == 2
    assert {match.state for match in inventory.matches} == {
        "classified",
        "unclassified",
    }
    assert len(inventory.required_gaps) == 1
    assert inventory.required_gaps[0].startswith(
        "source_budget_carrier_path_invalid:<invalid-path:"
    )


def test_synthetic_label_shape_does_not_reserve_a_legal_path() -> None:
    manifest = _manifest(_identity("all", include=("**",)))
    invalid = classify_carrier("!\udcff", manifest)

    legal = classify_carrier(invalid.relative_path, manifest)
    inventory = classify_carriers(("!\udcff", invalid.relative_path), manifest)

    assert legal.state == "classified"
    assert len(inventory.matches) == 2
    assert {
        (match.relative_path, match.path_state, match.state) for match in inventory.matches
    } == {
        (invalid.relative_path, "invalid", "unclassified"),
        (invalid.relative_path, "valid", "classified"),
    }
    assert inventory.required_gaps == invalid.required_gaps


def test_carrier_inventory_stably_orders_mixed_invalid_paths() -> None:
    manifest = _manifest(_identity("all", include=("**",)))

    inventory = classify_carriers(("z.py", "bad\udcff.py"), manifest)

    relative_paths = tuple(match.relative_path for match in inventory.matches)
    assert relative_paths[0].startswith("<invalid-path:")
    assert relative_paths[0].endswith(">")
    assert relative_paths[1] == "z.py"
    assert inventory.required_gaps == (f"source_budget_carrier_path_invalid:{relative_paths[0]}",)


def test_carrier_classification_supports_declared_multi_dot_extensions() -> None:
    archive = _identity(
        "archives",
        include=("archives/**",),
        extensions=(".tar.gz",),
        role="vendor_or_lock",
        scope_id="vendor.archives",
        disposition="exclude",
        metric_profile=None,
        exclusion_reason="Archives are governed separately.",
    )

    match = classify_carrier("archives/example.tar.gz", _manifest(archive))

    assert match.state == "excluded"
    assert match.identity == archive
    assert match.matched_carrier_ids == ("archives",)
    assert match.required_gaps == ()


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
