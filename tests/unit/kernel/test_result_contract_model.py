from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from ethos.result import EthosResult


def test_ethos_result_is_frozen_strict_schema_model() -> None:
    result = EthosResult(command="status", ok=True, state="ready")
    mutable: Any = result

    with pytest.raises(ValidationError) as exc_info:
        mutable.state = "dirty"

    assert exc_info.value.errors()[0]["type"] == "frozen_instance"
    schema = EthosResult.model_json_schema(mode="serialization")
    assert schema["properties"]["schema_version"] == {
        "const": 1,
        "default": 1,
        "title": "Schema Version",
        "type": "integer",
    }
    assert schema["properties"]["command"]["type"] == "string"
    assert schema["properties"]["ok"]["type"] == "boolean"
    assert schema["properties"]["verdict"]["enum"] == ["pass", "block", "unknown"]


def test_ethos_result_derives_closed_verdict_without_false_green() -> None:
    assert EthosResult(command="status", ok=True, state="ready").verdict == "pass"
    assert (
        EthosResult(
            command="status",
            ok=False,
            state="blocked",
            required_gaps=("hard_gap",),
        ).verdict
        == "block"
    )
    assert EthosResult(command="status", ok=False, state="unknown").verdict == "unknown"
    assert (
        EthosResult(
            command="status",
            ok=True,
            state="ready",
            required_gaps=("hard_gap",),
        ).verdict
        == "block"
    )


def test_ethos_result_cannot_serialize_false_green_ok() -> None:
    result = EthosResult(
        command="status",
        ok=True,
        state="ready",
        required_gaps=("hard_gap",),
    )

    assert result.ok is False
    assert result.state == "ready"
    assert result.to_dict()["ok"] is False
    assert result.to_dict()["state"] == "ready"


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
        "ok": False,
        "verdict": "block",
        "state": "planned",
        "summary": {"changed": True},
        "diagnostics": [{"kind": "probe", "ok": True}],
        "required_gaps": ["gap-a"],
        "next_actions": ["ethos prove --json"],
        "data": {"value": 1},
    }
