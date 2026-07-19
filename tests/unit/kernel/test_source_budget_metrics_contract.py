from __future__ import annotations

import json
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
        schema="ethos-source-budget-metrics-v2",
        contract_version=2,
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
    payload = _s().model_dump(mode="json", by_alias=True) | {"contract_version": 3}
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
