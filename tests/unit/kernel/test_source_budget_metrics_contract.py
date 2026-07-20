from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
from pydantic import ValidationError

import ethos_core.contracts.source_budget.carriers as c
import ethos_core.contracts.source_budget.metrics as m

if TYPE_CHECKING:
    from collections.abc import Callable

_D: dict[str, Any] = json.loads(
    (Path(__file__).parents[2] / "fixtures/source-budget-v2/compression-cases.json").read_text()
)["metrics"]


def _p(**changes: object) -> m.MetricProfile:
    return m.MetricProfile.model_validate(_D["base_profile"] | changes)


def _c(metric_id: str, unit: str, **changes: object) -> m.MetricContract:
    payload = _D["base_contract"] | {"metric_id": metric_id, "unit": unit} | changes
    payload.setdefault("contract_id", f"{payload['metric_profile']}:{metric_id}")
    return m.MetricContract.model_validate(payload)


def _s(profiles: object = None, contracts: object = None) -> m.MetricContractSet:
    default = (_c("lexical_tokens", "lexical_token"), _c("normalized_bytes", "normalized_byte"))
    return m.MetricContractSet(
        schema="ethos-source-budget-metrics-v3",
        contract_version=3,
        profiles=profiles or (_p(),),
        contracts=contracts or default,
    )


def _raises(error: type[Exception], match: str | None, call: Callable[[], object]) -> None:
    with pytest.raises(error, match=match):
        call()


def _invalid(case: dict[str, Any]) -> m.MetricContractSet:
    profiles = tuple(_p(**item) for item in case["profiles"])
    contracts = tuple(
        _c(
            item["metric_id"],
            item["unit"],
            **{key: value for key, value in item.items() if key not in {"metric_id", "unit"}},
        )
        for item in case["contracts"]
    )
    return _s(profiles, contracts)


def test_metric_validation_matrix() -> None:
    contract = _c("lexical_tokens", "lexical_token")
    _raises(ValidationError, "frozen", lambda: setattr(contract, "metric_id", "mutable"))
    _raises(
        ValidationError,
        "tokenizer",
        lambda: m.MetricContract.model_validate(contract.model_dump() | {"tokenizer": "x"}),
    )
    for field, value in _D["invalid_fields"]:
        payload = contract.model_dump() | {field: value}
        _raises(
            ValidationError, None, lambda payload=payload: m.MetricContract.model_validate(payload)
        )
    for case in _D["invalid_sets"]:
        _raises(ValidationError, case["message"], lambda case=case: _invalid(case))
    payload = _s().model_dump(mode="json", by_alias=True)
    payload["schema_id"] = payload.pop("schema")
    _raises(ValidationError, "schema", lambda: m.MetricContractSet.model_validate(payload))
    values = {"none": None, "contracts": _s(), "object": object()}
    for value_kind, gap_kind, gaps, message in _D["load_envelopes"]:
        required = list(gaps) if gap_kind == "list" else tuple(gaps)
        _raises(
            ValueError,
            message,
            lambda value=values[value_kind], required=required: m.MetricContractSetLoad(
                value, required
            ),
        )
    payload = _s().model_dump(mode="json", by_alias=True) | {"contract_version": 4}
    _raises(
        ValidationError, "contract version", lambda: m.MetricContractSet.model_validate(payload)
    )


def test_metric_behavior_matrix() -> None:
    identity = c.CarrierIdentity.model_validate(_D["base_carrier"])
    sets = tuple(
        _s((_p(required_metric_ids=order),))
        for order in (
            ("normalized_bytes", "lexical_tokens"),
            ("lexical_tokens", "normalized_bytes"),
        )
    )
    assert m.metric_contracts_digest(sets[0]) == m.metric_contracts_digest(sets[1])
    expected = ("lexical_tokens", "normalized_bytes")
    for contracts in sets:
        assert (
            tuple(item.metric_id for item in m.resolve_metric_contracts(identity, contracts))
            == expected
        )
    presets = _D["carrier_presets"]
    excluded = c.CarrierIdentity.model_validate(_D["base_carrier"] | presets["excluded"])
    unresolved = c.CarrierIdentity.model_validate(_D["base_carrier"] | presets["unresolved"])
    assert m.resolve_metric_contracts(excluded, _s()) == ()
    _raises(ValueError, "profile unresolved", lambda: m.resolve_metric_contracts(unresolved, _s()))
    lexical, normalized = (
        _c("lexical_tokens", "lexical_token"),
        _c("normalized_bytes", "normalized_byte"),
    )
    digest = m.metric_contracts_digest(_s(contracts=(lexical, normalized)))
    assert digest == m.metric_contracts_digest(_s(contracts=(normalized, lexical)))
    changed = lexical.model_copy(update={"parser_version": "stdlib-3.15"})
    assert digest != m.metric_contracts_digest(_s(contracts=(changed, normalized)))
    schema = m.metric_contracts_json_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "ETHOS Source Budget Metric Contracts"
    expected_schema = json.dumps(schema, separators=(",", ":")) + "\n"
    assert (
        Path("system/schemas/kernel/source-budget-metrics.schema.json").read_text()
        == expected_schema
    )


def _constructed_contract(metric_id: str, unit: str, **changes: object) -> m.MetricContract:
    payload = _D["base_contract"] | {"metric_id": metric_id, "unit": unit} | changes
    payload.setdefault("contract_id", f"{payload['metric_profile']}:{metric_id}")
    contract = m.MetricContract.model_construct(
        **{key: value for key, value in payload.items() if key in m.MetricContract.model_fields}
    )
    for field in ("execution_mode", "max_carrier_bytes"):
        object.__setattr__(contract, field, payload[field])
    return contract


def _forged_contracts(method: str, field: str, value: object) -> tuple[m.MetricContract, ...]:
    contracts = _s().contracts
    if method == "model_copy":
        return tuple(item.model_copy(update={field: value}) for item in contracts)
    return tuple(
        m.MetricContract.model_construct(**(item.model_dump() | {field: value}))
        for item in contracts
    )


def test_metric_registry_rejects_forged_float_version_at_trust_boundaries() -> None:
    registry = _s()
    _raises(
        ValueError,
        "contract version",
        lambda: m.MetricContractSet.model_construct(
            schema_id=registry.schema_id,
            contract_version=3.0,
            profiles=registry.profiles,
            contracts=registry.contracts,
        ),
    )
    forged = registry.model_copy(update={"contract_version": 3.0})
    _raises(ValueError, "contract version", lambda: m.MetricContractSetLoad(forged, ()))
    identity = c.CarrierIdentity.model_validate(_D["base_carrier"])
    _raises(ValueError, "contract version", lambda: m.resolve_metric_contracts(identity, forged))


def test_metric_resource_boundaries_replay_homogeneous_forged_atoms() -> None:
    identity = c.CarrierIdentity.model_validate(_D["base_carrier"])
    invalid = (
        ("contract_version", 3.0),
        ("execution_mode", "subprocess"),
        ("max_carrier_bytes", True),
        ("max_carrier_bytes", 1.5),
        ("max_carrier_bytes", 0),
        ("max_carrier_bytes", -1),
    )
    for field, value in invalid:
        for method in ("model_construct", "model_copy"):
            atoms = _forged_contracts(method, field, value)
            registry = _s().model_copy(update={"contracts": atoms})
            _raises(
                ValueError,
                "metric contract",
                lambda atoms=atoms: m.metric_provider_resource_contract(atoms),
            )
            _raises(
                ValueError,
                "metric contract",
                lambda registry=registry: m.MetricContractSetLoad(registry, ()),
            )
            _raises(
                ValueError,
                "metric contract",
                lambda registry=registry: m.resolve_metric_contracts(identity, registry),
            )


def test_metric_contract_v3_resource_boundary_is_required_and_strict() -> None:
    contract = _c("lexical_tokens", "lexical_token")
    assert contract.execution_mode == "bounded_in_process_v1"
    assert contract.max_carrier_bytes == 65536
    for field in ("execution_mode", "max_carrier_bytes"):
        payload = contract.model_dump()
        payload.pop(field)
        _raises(
            ValidationError,
            field,
            lambda payload=payload: m.MetricContract.model_validate(payload),
        )
    for field in ("path_override", "profile_override", "carrier_override"):
        payload = contract.model_dump() | {field: {"scope": 1}}
        _raises(
            ValidationError,
            field,
            lambda payload=payload: m.MetricContract.model_validate(payload),
        )
    old_unbounded = contract.model_dump()
    old_unbounded["contract_version"] = 2
    old_unbounded.pop("execution_mode")
    old_unbounded.pop("max_carrier_bytes")
    _raises(
        ValidationError,
        "contract version",
        lambda: m.MetricContract.model_validate(old_unbounded),
    )
    all_v4 = _s().model_dump(mode="json", by_alias=True)
    all_v4["contract_version"] = 4
    for item in all_v4["contracts"]:
        item["contract_version"] = 4
    _raises(
        ValidationError,
        "contract version",
        lambda: m.MetricContractSet.model_validate(all_v4),
    )


def test_metric_provider_resource_contract_rejects_mixed_provider_or_ceiling() -> None:
    lexical = _constructed_contract("lexical_tokens", "lexical_token")
    normalized = _constructed_contract("normalized_bytes", "normalized_byte")
    assert m.metric_provider_resource_contract((lexical, normalized)) == (
        "bounded_in_process_v1",
        65536,
    )
    drifted = _constructed_contract("normalized_bytes", "normalized_byte", max_carrier_bytes=32768)
    _raises(
        ValueError,
        "resource",
        lambda: m.metric_provider_resource_contract((lexical, drifted)),
    )
    other = _constructed_contract(
        "normalized_bytes",
        "normalized_byte",
        parser_id="json-stdlib",
        parser_version="cpython-3.14+ethos-json-v1",
        grammar_digest="b" * 64,
        normalization_id="structured-scalars",
    )
    _raises(ValueError, "provider", lambda: m.metric_provider_resource_contract((lexical, other)))


def test_metric_registry_rejects_cross_profile_provider_resource_drift() -> None:
    profiles = (
        _p(profile_id="python-a", required_metric_ids=("lexical_tokens",)),
        _p(profile_id="python-b", required_metric_ids=("normalized_bytes",)),
    )
    contracts = (
        _constructed_contract(
            "lexical_tokens", "lexical_token", metric_profile="python-a", contract_id="a"
        ),
        _constructed_contract(
            "normalized_bytes",
            "normalized_byte",
            metric_profile="python-b",
            contract_id="b",
            max_carrier_bytes=32768,
        ),
    )
    _raises(
        ValueError,
        "provider resource",
        lambda: m.MetricContractSet.model_construct(
            schema_id="ethos-source-budget-metrics-v3",
            contract_version=3,
            profiles=profiles,
            contracts=contracts,
        ),
    )


def test_metric_resource_fields_change_digest_and_schema_projection() -> None:
    contracts = (
        _constructed_contract("lexical_tokens", "lexical_token"),
        _constructed_contract("normalized_bytes", "normalized_byte"),
    )
    registry = m.MetricContractSet.model_construct(
        schema_id="ethos-source-budget-metrics-v3",
        contract_version=3,
        profiles=(_p(),),
        contracts=contracts,
    )
    changed_contracts = tuple(
        item.model_copy(update={"max_carrier_bytes": 131072}) for item in contracts
    )
    changed = m.MetricContractSet.model_construct(
        schema_id="ethos-source-budget-metrics-v3",
        contract_version=3,
        profiles=registry.profiles,
        contracts=changed_contracts,
    )
    assert m.metric_contracts_digest(registry) != m.metric_contracts_digest(changed)
    schema = m.metric_contracts_json_schema()
    assert schema["properties"]["schema"]["const"] == "ethos-source-budget-metrics-v3"
    contract_schema = schema["$defs"]["MetricContract"]
    assert contract_schema["properties"]["execution_mode"]["const"] == "bounded_in_process_v1"
    assert contract_schema["properties"]["max_carrier_bytes"]["exclusiveMinimum"] == 0


def test_repository_metric_policy_declares_v3_fixed_provider_ceilings() -> None:
    payload = tomllib.loads(Path("system/policies/source-budget-metrics.toml").read_text())
    assert payload["schema"] == "ethos-source-budget-metrics-v3"
    assert payload["contract_version"] == 3
    for contract in payload["contracts"]:
        expected = (
            262144
            if contract["parser_id"] == "utf8-footprint"
            else 65536
            if contract["parser_id"] == "python-tokenize"
            else 32768
        )
        assert contract["contract_version"] == 3
        assert contract["execution_mode"] == "bounded_in_process_v1"
        assert contract["max_carrier_bytes"] == expected
