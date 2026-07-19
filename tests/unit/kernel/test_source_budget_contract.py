from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

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
