from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
from pydantic import ValidationError

import ethos_core.contracts.source_budget.carriers as c

if TYPE_CHECKING:
    from collections.abc import Callable

_D: dict[str, Any] = json.loads(
    (Path(__file__).parents[2] / "fixtures/source-budget-v2/compression-cases.json").read_text()
)["carrier"]


def _i(carrier_id: str, **changes: object) -> c.CarrierIdentity:
    return c.CarrierIdentity.model_validate(
        _D["base_identity"] | {"carrier_id": carrier_id} | changes
    )


def _m(*identities: c.CarrierIdentity) -> c.CarrierManifest:
    return c.CarrierManifest(
        schema="ethos-source-budget-carriers-v2", contract_version=2, carriers=identities
    )


def _mn(name: str) -> c.CarrierManifest:
    return c.CarrierManifest.model_validate(
        {
            "schema": "ethos-source-budget-carriers-v2",
            "contract_version": 2,
            "carriers": [_D["base_identity"] | item for item in _D["manifests"][name]],
        }
    )


def _match(**changes: object) -> c.CarrierMatch:
    payload = _D["base_match"] | changes
    for key in ("matched_carrier_ids", "required_gaps"):
        payload[key] = tuple(payload[key])
    return c.CarrierMatch.model_validate(payload)


def _raises(
    call: Callable[[], object], error: type[Exception] = ValidationError, match: str | None = None
) -> None:
    with pytest.raises(error, match=match):
        call()


def test_carrier_validation_matrix() -> None:
    identity = _i("python", include=("packages/**",), extensions=(".py",))
    _raises(lambda: setattr(identity, "carrier_id", "mutable"))
    _raises(
        lambda: c.CarrierIdentity.model_validate(identity.model_dump() | {"priority": 1}),
        match="priority",
    )
    for field, value in _D["invalid_matchers"]:
        payload = identity.model_dump() | {field: tuple(value)}
        _raises(lambda payload=payload: c.CarrierIdentity.model_validate(payload))
    _raises(
        lambda: c.CarrierIdentity.validate_matchers(("bad\udcff/**",)),
        ValueError,
        "repository-relative POSIX paths",
    )
    for disposition, profile, reason in _D["invalid_dispositions"]:
        payload = identity.model_dump() | {
            "disposition": disposition,
            "metric_profile": profile,
            "exclusion_reason": reason,
        }
        _raises(lambda payload=payload: c.CarrierIdentity.model_validate(payload))
    _raises(lambda: _i("python", include=("**/*.py",), extensions=(".py",)), match="extensions")
    first = _i("first", include=("packages/**",), extensions=(".py",))
    for other, message in (
        (_i("first", include=("tools/**",), extensions=(".py",)), "carrier ids"),
        (_i("second", include=("packages/**",), extensions=(".py",)), "matcher"),
    ):
        _raises(lambda other=other: _m(first, other), match=message)
    manifest = _m(identity)
    payload = manifest.model_dump(mode="json", by_alias=True)
    payload["schema_id"] = payload.pop("schema")
    _raises(lambda: c.CarrierManifest.model_validate(payload), match="schema")
    values = {"none": None, "manifest": manifest, "object": object()}
    for value_kind, gap_kind, gaps, message in _D["load_envelopes"]:
        required = list(gaps) if gap_kind == "list" else tuple(gaps)
        _raises(
            lambda value=values[value_kind], required=required: c.CarrierManifestLoad(
                value, required
            ),
            ValueError,
            message,
        )


def test_carrier_result_matrix() -> None:
    _raises(
        lambda: _match(
            relative_path="packages/ethos/core.py", state="classified", required_gaps=()
        ),
        match="classification result",
    )
    _raises(
        lambda: c.CarrierInventory(
            manifest_digest="a" * 64,
            inventory_digest="b" * 64,
            matches=(_match(),),
            required_gaps=(),
        ),
        match="inventory required gaps",
    )
    for changes in _D["match_overrides"]:
        _raises(lambda changes=changes: _match(**changes))
    identity = _i("python", include=("packages/**",), extensions=(".py",))
    invalid_label = f"<invalid-path:{'a' * 64}>"
    for source, message in _D["match_forgeries"]:
        payload = dict(source)
        payload["relative_path"] = (
            invalid_label if payload["relative_path"] == "<invalid>" else payload["relative_path"]
        )
        payload["identity"] = identity if payload["identity"] else None
        _raises(lambda payload=payload: _match(**payload), match=message)
    inventory = c.classify_carriers(("a.py", "b.py"), _mn("all"))
    for matches in (tuple(reversed(inventory.matches)), (inventory.matches[0],) * 2):
        payload = inventory.model_dump() | {"matches": matches}
        _raises(
            lambda payload=payload: c.CarrierInventory.model_validate(payload),
            match="stably ordered",
        )
    inventory = c.classify_carriers(("a.py",), _mn("all"))
    _raises(
        lambda: c.CarrierInventory.model_validate(
            inventory.model_dump() | {"inventory_digest": "0" * 64}
        ),
        match="inventory digest",
    )
    identity = inventory.matches[0].identity
    assert identity is not None
    forged = inventory.matches[0].model_copy(
        update={"identity": identity.model_copy(update={"owner": "forged-owner"})}
    )
    _raises(
        lambda: c.CarrierInventory.model_validate(inventory.model_dump() | {"matches": (forged,)}),
        match="inventory digest",
    )


def test_carrier_behavior_matrix() -> None:
    for manifest, path, state, identity_id, ids, gaps in _D["classification_cases"]:
        match = c.classify_carrier(path, _mn(manifest))
        assert (
            match.state,
            match.identity.carrier_id if match.identity else None,
            match.matched_carrier_ids,
            match.required_gaps,
        ) == (state, identity_id, tuple(ids), tuple(gaps))
    for path in _D["invalid_paths"]:
        match = c.classify_carrier(path, _mn("all"))
        assert match.relative_path.startswith("<invalid-path:")
        assert match.relative_path.endswith(">")
        assert (match.state, match.identity, match.matched_carrier_ids, match.required_gaps) == (
            "unclassified",
            None,
            (),
            (f"source_budget_carrier_path_invalid:{match.relative_path}",),
        )
    manifest = _mn("all")
    empty = c.classify_carriers((), manifest)
    assert (empty.matches, empty.required_gaps) == ((), ("source_budget_carrier_inventory_empty",))
    collision = c.classify_carriers(("!\udcff", "<invalid-path>"), manifest)
    assert len(collision.matches) == 2
    assert {item.state for item in collision.matches} == {"classified", "unclassified"}
    assert len(collision.required_gaps) == 1
    assert collision.required_gaps[0].startswith(
        "source_budget_carrier_path_invalid:<invalid-path:"
    )
    invalid = c.classify_carrier("!\udcff", manifest)
    legal = c.classify_carrier(invalid.relative_path, manifest)
    inventory = c.classify_carriers(("!\udcff", invalid.relative_path), manifest)
    assert (legal.state, len(inventory.matches), inventory.required_gaps) == (
        "classified",
        2,
        invalid.required_gaps,
    )
    assert {(item.relative_path, item.path_state, item.state) for item in inventory.matches} == {
        (invalid.relative_path, "invalid", "unclassified"),
        (invalid.relative_path, "valid", "classified"),
    }
    mixed = c.classify_carriers(("z.py", "bad\udcff.py"), manifest)
    paths = tuple(item.relative_path for item in mixed.matches)
    assert paths[0].startswith("<invalid-path:")
    assert (paths[0].endswith(">"), paths[1], mixed.required_gaps) == (
        True,
        "z.py",
        (f"source_budget_carrier_path_invalid:{paths[0]}",),
    )
    python, docs = _mn("digest").carriers
    digest = c.carrier_manifest_digest(_m(python, docs))
    assert digest == c.carrier_manifest_digest(_m(docs, python))
    assert digest != c.carrier_manifest_digest(_m(python, docs.model_copy(update={"owner": "x"})))
    schema = c.carrier_manifest_json_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "ETHOS Source Budget Carrier Manifest"
    expected = json.dumps(schema, separators=(",", ":")) + "\n"
    assert Path("system/schemas/kernel/source-budget-carriers.schema.json").read_text() == expected
