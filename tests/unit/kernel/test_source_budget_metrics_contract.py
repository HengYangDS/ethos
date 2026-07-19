from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos_core.contracts.source_budget.carriers import CarrierIdentity
from ethos_core.contracts.source_budget.metrics import MetricContract
from ethos_core.contracts.source_budget.metrics import MetricContractSet
from ethos_core.contracts.source_budget.metrics import MetricProfile
from ethos_core.contracts.source_budget.metrics import metric_contracts_digest
from ethos_core.contracts.source_budget.metrics import metric_contracts_json_schema
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts


def _profile(
    *,
    profile_id: str = "python-source-v2",
    carrier_role: str = "authored_behavioral_source",
    required_metric_ids: tuple[str, ...] = ("lexical_tokens", "normalized_bytes"),
) -> MetricProfile:
    return MetricProfile.model_validate(
        {
            "profile_id": profile_id,
            "carrier_role": carrier_role,
            "required_metric_ids": required_metric_ids,
        }
    )


def _contract(
    metric_id: str,
    unit: str,
    **overrides: object,
) -> MetricContract:
    payload: dict[str, object] = {
        "contract_version": 2,
        "metric_id": metric_id,
        "unit": unit,
        "carrier_role": "authored_behavioral_source",
        "metric_profile": "python-source-v2",
        "parser_id": "python-tokenize",
        "parser_version": "stdlib-3.14",
        "grammar_digest": "a" * 64,
        "normalization_id": "python-source-normalization",
        "normalization_version": "1",
        "aggregation": "sum",
        "non_compensable": True,
    }
    payload.update(overrides)
    payload.setdefault("contract_id", f"{payload['metric_profile']}:{metric_id}")
    return MetricContract.model_validate(payload)


def _contract_set(
    *,
    profiles: tuple[MetricProfile, ...] | None = None,
    contracts: tuple[MetricContract, ...] | None = None,
) -> MetricContractSet:
    return MetricContractSet(
        schema="ethos-source-budget-metrics-v2",
        contract_version=2,
        profiles=profiles or (_profile(),),
        contracts=contracts
        or (
            _contract("lexical_tokens", "lexical_token"),
            _contract("normalized_bytes", "normalized_byte"),
        ),
    )


def test_metric_models_are_frozen_and_forbid_unknown_fields() -> None:
    contract = _contract("lexical_tokens", "lexical_token")

    with pytest.raises(ValidationError):
        contract.metric_id = "mutable"  # type: ignore[misc]

    payload = contract.model_dump()
    payload["tokenizer"] = "model-specific"
    with pytest.raises(ValidationError, match="tokenizer"):
        MetricContract.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("grammar_digest", "short"),
        ("aggregation", "average"),
        ("non_compensable", False),
        ("unit", "bpe_token"),
        ("unit", "model_token"),
    ],
)
def test_metric_contract_rejects_invalid_or_compensating_identity(
    field: str,
    value: object,
) -> None:
    payload = _contract("lexical_tokens", "lexical_token").model_dump()
    payload[field] = value

    with pytest.raises(ValidationError):
        MetricContract.model_validate(payload)


def test_metric_contract_set_rejects_duplicate_ids_and_coordinates() -> None:
    first = _contract("lexical_tokens", "lexical_token", contract_id="first")
    duplicate_id = _contract("normalized_bytes", "normalized_byte", contract_id="first")
    with pytest.raises(ValidationError, match="contract ids"):
        _contract_set(contracts=(first, duplicate_id))

    duplicate_coordinate = _contract(
        "lexical_tokens",
        "lexical_token",
        contract_id="second",
    )
    with pytest.raises(ValidationError, match="coordinates"):
        _contract_set(contracts=(first, duplicate_coordinate))


def test_metric_contract_set_rejects_dangling_or_role_mismatched_profiles() -> None:
    with pytest.raises(ValidationError, match="required metric"):
        _contract_set(
            profiles=(_profile(required_metric_ids=("missing_metric",)),),
            contracts=(_contract("lexical_tokens", "lexical_token"),),
        )

    mismatched = _contract(
        "lexical_tokens",
        "lexical_token",
        carrier_role="test_source",
    )
    with pytest.raises(ValidationError, match="role"):
        _contract_set(
            profiles=(_profile(required_metric_ids=("lexical_tokens",)),),
            contracts=(mismatched,),
        )


def test_metric_profile_resolution_is_complete_and_stably_ordered() -> None:
    contracts = _contract_set(
        profiles=(_profile(required_metric_ids=("normalized_bytes", "lexical_tokens")),),
    )
    identity = CarrierIdentity.model_validate(
        {
            "carrier_id": "python-product",
            "role": "authored_behavioral_source",
            "scope_id": "product.python",
            "disposition": "measure",
            "metric_profile": "python-source-v2",
            "extensions": (".py",),
            "include": ("packages/**",),
            "exclude": (),
            "owner": "ethos-quality",
            "exclusion_reason": None,
        }
    )

    resolved = resolve_metric_contracts(identity, contracts)

    assert tuple(item.metric_id for item in resolved) == (
        "normalized_bytes",
        "lexical_tokens",
    )


def test_metric_contract_digest_is_order_independent_and_semantic() -> None:
    lexical = _contract("lexical_tokens", "lexical_token")
    normalized = _contract("normalized_bytes", "normalized_byte")
    profile = _profile()

    assert metric_contracts_digest(
        _contract_set(profiles=(profile,), contracts=(lexical, normalized))
    ) == metric_contracts_digest(
        _contract_set(profiles=(profile,), contracts=(normalized, lexical))
    )

    changed = lexical.model_copy(update={"parser_version": "stdlib-3.15"})
    assert metric_contracts_digest(
        _contract_set(profiles=(profile,), contracts=(lexical, normalized))
    ) != metric_contracts_digest(
        _contract_set(profiles=(profile,), contracts=(changed, normalized))
    )


def test_metric_contract_schema_is_compact_typed_projection() -> None:
    schema_path = Path("system/schemas/kernel/source-budget-metrics.schema.json")
    schema = metric_contracts_json_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "ETHOS Source Budget Metric Contracts"
    assert (
        schema_path.read_text(encoding="utf-8") == json.dumps(schema, separators=(",", ":")) + "\n"
    )
