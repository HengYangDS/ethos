from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import ethos_core.contracts.source_budget.policy.core as policy_v2
from ethos_core.contracts.source_budget import core as source_budget_contract
from ethos_core.contracts.source_budget.core import SourceBudgetWave
from ethos_core.contracts.source_budget.core import source_budget_json_schema
from ethos_core.contracts.source_budget.core import validate_source_budget_policy
from ethos_core.contracts.source_budget.core import validate_source_budget_taxonomy


def _policy_payload() -> dict[str, object]:
    return {
        "baseline_head": "a" * 40,
        "enforcement": "transition",
        "baseline": {"global_total": 1, "python_total": 1},
        "terminal": {"global_total": 0, "python_total": 0},
        "debt": {
            "maximum_total": 1,
            "waves": [{"id": "w1", "due_on": "2026-12-01", "state": "active"}],
            "records": [
                {
                    "id": "debt-1",
                    "owner": "owner",
                    "replacement": "replacement",
                    "deletion_wave": "w1",
                    "expiry": "2026-12-01",
                    "allowance": 1,
                    "expected_net_deletion": 1,
                    "allowance_by_category": {"python_product": 1},
                }
            ],
        },
    }


def test_source_budget_contract_preserves_public_api_names() -> None:
    assert source_budget_contract.JSON_SCHEMA_DRAFT_2020_12.endswith("2020-12/schema")
    assert source_budget_contract.ISO_DATE_LENGTH == 10
    assert source_budget_contract.ISO_DATE_ERROR == "must be an ISO-8601 calendar date"
    assert (
        source_budget_contract.SourceBudgetDebtRecord.validate_expiry("2026-12-01") == "2026-12-01"
    )
    assert callable(source_budget_contract.SourceBudgetTaxonomy.validate_taxonomy)
    assert callable(source_budget_contract.SourceBudgetDebt.validate_lifecycle_bindings)
    assert callable(source_budget_contract.SourceBudgetPolicyBase.validate_taxonomy)


def test_source_budget_contract_preserves_lifecycle_fields():
    policy = validate_source_budget_policy(_policy_payload())

    assert policy.debt.records[0].deletion_wave == "w1"
    assert policy.debt.records[0].expiry == "2026-12-01"
    assert policy.debt.records[0].expected_net_deletion == 1


@pytest.mark.parametrize(
    ("enforcement", "campaign_id"),
    [
        ("campaign_terminal", None),
        ("campaign_terminal", "compression"),
        ("transition", "compression"),
        ("transition", None),
    ],
)
def test_source_budget_contract_validates_campaign_binding(enforcement, campaign_id):
    payload = _policy_payload()
    payload["enforcement"] = enforcement
    if campaign_id is not None or (enforcement, campaign_id) == ("transition", None):
        payload["campaign_id"] = campaign_id

    if enforcement == "campaign_terminal" and campaign_id:
        assert validate_source_budget_policy(payload).campaign_id == campaign_id
    else:
        with pytest.raises(ValidationError):
            validate_source_budget_policy(payload)


@pytest.mark.parametrize(
    "case",
    [
        "missing_owner",
        "malformed_expiry",
        "invalid_expiry_calendar",
        "unknown_wave",
        "duplicate_wave",
        "duplicate_record",
        "missing_aggregate",
    ],
)
def test_source_budget_contract_rejects_invalid_debt_lifecycle(case):
    payload = _policy_payload()
    record = payload["debt"]["records"][0]
    if case == "missing_owner":
        record.pop("owner")
    elif case == "malformed_expiry":
        record["expiry"] = "T5"
    elif case == "invalid_expiry_calendar":
        record["expiry"] = "2026-02-30"
    elif case == "unknown_wave":
        record["deletion_wave"] = "unknown"
    elif case == "duplicate_wave":
        payload["debt"]["waves"].append(dict(payload["debt"]["waves"][0]))
    elif case == "duplicate_record":
        payload["debt"]["records"].append(dict(record))
    else:
        payload["baseline"].pop("python_total")

    with pytest.raises(ValidationError):
        validate_source_budget_policy(payload)


def test_source_budget_taxonomy_rejects_unknown_aggregate_member() -> None:
    with pytest.raises(ValidationError, match="aggregate member unknown"):
        validate_source_budget_taxonomy(
            {
                "carrier": [{"category": "python", "extensions": [".py"]}],
                "aggregates": {"total": ["missing"]},
            }
        )


def test_source_budget_contract_requires_terminal_aggregates() -> None:
    payload = _policy_payload()
    payload["terminal"].pop("global_total")

    with pytest.raises(ValidationError, match="terminal must include required aggregates"):
        validate_source_budget_policy(payload)


def test_source_budget_date_validator_rejects_non_calendar_values():
    with pytest.raises(ValueError, match="must be an ISO-8601 calendar date"):
        SourceBudgetWave.validate_due_on("T5")


def test_source_budget_schema_is_a_compact_typed_contract_projection():
    schema_path = Path("system/schemas/kernel/source-budget.schema.json")

    schema = source_budget_json_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "ETHOS Source Budget Policy"
    assert (
        schema_path.read_text(encoding="utf-8") == json.dumps(schema, separators=(",", ":")) + "\n"
    )


def _v2_api():
    return policy_v2


def _v2_limit(scope: str, metric: str, unit: str, value: int):
    api = _v2_api()
    return api.BudgetLimit(scope_id=scope, metric_id=metric, unit=unit, value=value)


def _v2_vector(*items):
    return _v2_api().BudgetVector.canonical(tuple(items))


def _v2_shadow_payload() -> dict[str, object]:
    baseline = _v2_vector(
        _v2_limit("product.python", "lexical_tokens", "lexical_token", 10),
        _v2_limit("tests.python", "normalized_bytes", "normalized_byte", 20),
    )
    terminal = _v2_vector(
        _v2_limit("product.python", "lexical_tokens", "lexical_token", 8),
        _v2_limit("tests.python", "normalized_bytes", "normalized_byte", 15),
    )
    empty = _v2_vector()
    return {
        "schema": "ethos-source-budget-policy-v2",
        "contract_version": 2,
        "state": "shadow",
        "baseline_head": "a" * 40,
        "enforcement": "transition",
        "campaign_id": None,
        "baseline": {
            "admitted_head": "a" * 40,
            "manifest_digest": "1" * 64,
            "inventory_digest": "2" * 64,
            "contract_set_digest": "3" * 64,
            "snapshot_digest": "4" * 64,
            "vector": baseline.model_dump(mode="json"),
        },
        "terminal": terminal.model_dump(mode="json"),
        "permanent_allocations": empty.model_dump(mode="json"),
        "settled_reductions": empty.model_dump(mode="json"),
        "debt": {"waves": [], "records": []},
    }


def test_v2_vector_canonical_constructor_sorts_and_binds_digest() -> None:
    api = _v2_api()
    later = _v2_limit("tests.python", "normalized_bytes", "normalized_byte", 20)
    earlier = _v2_limit("product.python", "lexical_tokens", "lexical_token", 10)

    vector = api.BudgetVector.canonical((later, earlier))

    assert vector.coordinates == (earlier, later)
    assert len(vector.vector_digest) == 64
    assert api.BudgetVector.model_validate(vector.model_dump(mode="json")) == vector


def test_v2_vector_rejects_unordered_duplicate_cross_unit_and_forged_input() -> None:
    api = _v2_api()
    first = _v2_limit("product.python", "lexical_tokens", "lexical_token", 10)
    second = _v2_limit("tests.python", "normalized_bytes", "normalized_byte", 20)
    valid = _v2_vector(first, second)

    unordered = valid.model_dump(mode="json")
    unordered["coordinates"] = list(reversed(unordered["coordinates"]))
    with pytest.raises(ValidationError, match="unique and stably ordered"):
        api.BudgetVector.model_validate(unordered)

    duplicate = valid.model_dump(mode="json")
    duplicate["coordinates"] = [
        first.model_dump(mode="json"),
        {
            "scope_id": first.scope_id,
            "metric_id": first.metric_id,
            "unit": "normalized_byte",
            "value": 10,
        },
    ]
    with pytest.raises(ValidationError, match="coordinate keys must be unique"):
        api.BudgetVector.model_validate(duplicate)

    forged = valid.model_dump(mode="json")
    forged["vector_digest"] = "0" * 64
    with pytest.raises(ValidationError, match="digest must match canonical content"):
        api.BudgetVector.model_validate(forged)


def test_v2_policy_rejects_coordinate_mismatch_and_reduction_underflow() -> None:
    api = _v2_api()
    mismatch = _v2_shadow_payload()
    mismatch["terminal"] = _v2_vector(
        _v2_limit("product.python", "lexical_tokens", "lexical_token", 8)
    ).model_dump(mode="json")
    with pytest.raises(ValidationError, match="baseline and terminal coordinates must match"):
        api.validate_source_budget_policy_v2(mismatch)

    underflow = _v2_shadow_payload()
    underflow["settled_reductions"] = _v2_vector(
        _v2_limit("product.python", "lexical_tokens", "lexical_token", 11)
    ).model_dump(mode="json")
    with pytest.raises(ValidationError, match="settled reduction underflows"):
        api.validate_source_budget_policy_v2(underflow)


def test_v2_mapped_debt_requires_expected_deletion_at_least_allowance() -> None:
    api = _v2_api()
    payload = _v2_shadow_payload()
    payload["debt"] = {
        "waves": [{"id": "wave-1", "due_on": "2026-07-30", "state": "active"}],
        "records": [
            {
                "mapping_state": "mapped",
                "id": "debt-1",
                "origin_change": "change-1",
                "admitted_head": "b" * 40,
                "scope_digest": "5" * 64,
                "inventory_digest": "6" * 64,
                "baseline_snapshot_digest": "7" * 64,
                "historical_replay_digest": "8" * 64,
                "owner": "owner",
                "replacement": "replacement",
                "deletion_wave": "wave-1",
                "expiry": "2026-07-30",
                "allowance": _v2_vector(
                    _v2_limit("product.python", "lexical_tokens", "lexical_token", 2)
                ).model_dump(mode="json"),
                "expected_deletion": _v2_vector(
                    _v2_limit("product.python", "lexical_tokens", "lexical_token", 1)
                ).model_dump(mode="json"),
            }
        ],
    }

    with pytest.raises(ValidationError, match="expected deletion must cover allowance"):
        api.validate_source_budget_policy_v2(payload)


def test_v2_unmapped_debt_cannot_carry_allowance_or_inferred_bindings() -> None:
    api = _v2_api()
    payload = _v2_shadow_payload()
    payload["debt"] = {
        "waves": [{"id": "wave-1", "due_on": "2026-07-30", "state": "active"}],
        "records": [
            {
                "mapping_state": "unmapped",
                "id": "debt-1",
                "origin_change": "change-1",
                "owner": "owner",
                "replacement": "replacement",
                "deletion_wave": "wave-1",
                "expiry": "2026-07-30",
                "missing_bindings": ["admitted_head"],
                "allowance": _v2_vector(
                    _v2_limit("product.python", "lexical_tokens", "lexical_token", 2)
                ).model_dump(mode="json"),
            }
        ],
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        api.validate_source_budget_policy_v2(payload)


def test_v2_inactive_policy_forbids_fabricated_baseline_and_terminal_vectors() -> None:
    api = _v2_api()
    payload = {
        "schema": "ethos-source-budget-policy-v2",
        "contract_version": 2,
        "state": "inactive",
        "baseline_head": "a" * 40,
        "enforcement": "campaign_terminal",
        "campaign_id": "global-declarative-compression-program",
        "debt": {"waves": [], "records": []},
        "baseline": _v2_shadow_payload()["baseline"],
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        api.validate_source_budget_policy_v2(payload)


def test_source_budget_schema_composes_unchanged_v1_and_strict_v2() -> None:
    schema_path = Path("system/schemas/kernel/source-budget.schema.json")
    schema = source_budget_json_schema()

    assert len(schema["oneOf"]) == 2
    assert "SourceBudgetCampaignPolicy" in schema["$defs"]
    assert "InactiveSourceBudgetPolicyV2" in schema["$defs"]
    assert validate_source_budget_policy(_policy_payload()).enforcement == "transition"
    assert (
        schema_path.read_text(encoding="utf-8") == json.dumps(schema, separators=(",", ":")) + "\n"
    )
