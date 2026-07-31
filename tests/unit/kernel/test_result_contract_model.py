from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from ethos.result import EthosResult


def test_ethos_result_is_frozen_strict_schema_model() -> None:
    result = EthosResult(command="status", verdict="pass", state="ready")
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
    assert "ok" not in schema["properties"]
    assert schema["properties"]["verdict"]["enum"] == ["pass", "block", "unknown"]


def test_ethos_result_exposes_only_the_authoritative_verdict() -> None:
    result = EthosResult(command="status", verdict="pass", state="ready")

    assert result.verdict == "pass"
    assert not hasattr(result, "ok")


def test_ethos_result_rejects_pass_with_required_gaps() -> None:
    with pytest.raises(ValidationError, match="pass_with_required_gaps"):
        EthosResult(
            command="status",
            verdict="pass",
            state="ready",
            required_gaps=("hard_gap",),
        )


@pytest.mark.parametrize("severity", ["warning", "error"])
def test_ethos_result_rejects_pass_with_adverse_diagnostic(severity: str) -> None:
    with pytest.raises(ValidationError, match="pass_with_warnings"):
        EthosResult(
            command="status",
            verdict="pass",
            state="ready",
            diagnostics=({"severity": severity, "message": "adverse"},),
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"command": "status", "verdict": "passed", "state": "ready"},
        {"command": "status", "verdict": "pass", "state": 3},
        {"command": "status", "verdict": "pass", "state": "ready", "ok": True},
        {"command": "status", "verdict": "pass", "state": "ready", "extra": "blocked"},
    ],
)
def test_ethos_result_rejects_coercion_and_unknown_fields(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EthosResult.model_validate(payload)


def test_ethos_result_json_contract_has_no_parallel_success_flag() -> None:
    result = EthosResult(
        command="plan",
        verdict="block",
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
        "verdict": "block",
        "state": "planned",
        "summary": {"changed": True},
        "diagnostics": [{"kind": "probe", "ok": True}],
        "required_gaps": ["gap-a"],
        "next_actions": ["ethos prove --json"],
        "data": {"value": 1},
    }
