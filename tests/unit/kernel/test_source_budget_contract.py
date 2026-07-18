from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos_core.contracts.source_budget.core import SourceBudgetPolicy
from ethos_core.contracts.source_budget.core import SourceBudgetWave
from ethos_core.contracts.source_budget.core import source_budget_json_schema


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


def test_source_budget_contract_preserves_lifecycle_fields():
    policy = SourceBudgetPolicy.model_validate(_policy_payload())

    assert policy.debt.records[0].deletion_wave == "w1"
    assert policy.debt.records[0].expiry == "2026-12-01"
    assert policy.debt.records[0].expected_net_deletion == 1


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
        SourceBudgetPolicy.model_validate(payload)


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
