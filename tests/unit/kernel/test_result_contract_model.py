from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from ethos.result import EthosResult


def test_ethos_result_is_frozen_strict_schema_model() -> None:
    result = EthosResult(command="status", ok=True, state="ready")

    with pytest.raises(ValidationError) as exc_info:
        result.state = "dirty"  # type: ignore[misc]

    assert exc_info.value.errors()[0]["type"] == "frozen_instance"
    schema = EthosResult.model_json_schema()
    assert schema["properties"]["command"]["type"] == "string"
    assert schema["properties"]["ok"]["type"] == "boolean"


@pytest.mark.parametrize(
    "payload",
    [
        {"command": "status", "ok": "true", "state": "ready"},
        {"command": "status", "ok": True, "state": 3},
        {"command": "status", "ok": True, "state": "ready", "extra": "blocked"},
    ],
)
def test_ethos_result_rejects_coercion_and_unknown_fields(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EthosResult.model_validate(payload)


def test_ethos_result_json_contract_stays_compatible() -> None:
    result = EthosResult(
        command="plan",
        ok=True,
        state="planned",
        summary={"changed": True},
        diagnostics=({"kind": "probe", "ok": True},),
        required_gaps=("gap-a",),
        next_actions=("ethos prove --json",),
        data={"value": 1},
    )

    payload = json.loads(result.to_json())

    assert payload == {
        "schema_version": 1,
        "command": "plan",
        "ok": True,
        "state": "planned",
        "summary": {"changed": True},
        "diagnostics": [{"kind": "probe", "ok": True}],
        "required_gaps": ["gap-a"],
        "next_actions": ["ethos prove --json"],
        "data": {"value": 1},
    }
