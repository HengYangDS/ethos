from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ethos.result import EthosResult
from ethos.result import apply_payload_budget
from tests.support.literal_cases import literal_case


def _result(**updates: object) -> EthosResult:
    return EthosResult.model_validate(
        {"command": "status", "verdict": "pass", "state": "ready"} | updates
    )


def _payload() -> dict[str, object]:
    return _result().to_dict()


def test_ethos_result_is_frozen_strict_schema_model() -> None:
    result = _result()
    mutable: Any = result

    with pytest.raises(ValidationError) as exc_info:
        mutable.state = "dirty"

    assert exc_info.value.errors()[0]["type"] == "frozen_instance"
    schema = EthosResult.model_json_schema(mode="serialization")
    assert schema["properties"]["schema_version"] == {
        "const": 2,
        "default": 2,
        "title": "Schema Version",
        "type": "integer",
    }
    assert schema["properties"]["command"]["type"] == "string"
    assert "ok" not in schema["properties"]
    assert schema["properties"]["verdict"]["enum"] == ["pass", "block", "unknown"]
    assert json.loads(Path("system/schemas/kernel/result.schema.json").read_text()) == (
        schema
        | {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://ethos.local/schemas/result.schema.json",
        }
    )


def test_ethos_result_exposes_only_the_authoritative_verdict() -> None:
    result = _result()

    assert result.verdict == "pass"
    assert not hasattr(result, "ok")


@pytest.mark.parametrize(
    ("verdict", "required_gaps", "next_action", "expected"),
    literal_case(
        "kernel.test_result_contract_model:parametrize:test_ethos_result_derives_one_non_persistent_continuation:0"
    ),
)
def test_ethos_result_derives_one_non_persistent_continuation(
    verdict: str,
    required_gaps: tuple[str, ...],
    next_action: str,
    expected: str,
) -> None:
    result = _result(
        verdict=verdict,
        state="ready" if verdict == "pass" else "blocked",
        required_gaps=required_gaps,
        next_action=next_action,
    )

    assert result.continuation == expected
    assert result.next_action == next_action


def test_ethos_result_projects_unknown_gaps_as_missing_facts_or_evidence() -> None:
    result = _result(
        verdict="unknown",
        state="unknown",
        required_gaps=("facts_unavailable", "proof_missing"),
        next_action="observe the missing repository facts",
    )

    assert result.continuation == "blocked"
    assert result.missing_facts_or_evidence == ("facts_unavailable", "proof_missing")


def test_ethos_result_requires_user_decision_for_authority_bearing_action() -> None:
    result = _result(
        command="lane housekeeping",
        state="planned",
        next_action="ethos lane housekeeping --authorize --apply --json",
    )

    assert result.user_decision_required is True
    assert result.continuation == "await-user"


@pytest.mark.parametrize(
    "next_action",
    literal_case(
        "kernel.test_result_contract_model:parametrize:test_ethos_result_recognizes_mutation_flag_forms:1"
    ),
)
def test_ethos_result_recognizes_mutation_flag_forms(next_action: str) -> None:
    result = _result(next_action=next_action)

    assert result.user_decision_required is True
    assert result.continuation == "await-user"


@pytest.mark.parametrize(
    "required_gap",
    literal_case(
        "kernel.test_result_contract_model:parametrize:test_ethos_result_awaits_external_decisions_named_by_gap:2"
    ),
)
def test_ethos_result_awaits_external_decisions_named_by_gap(required_gap: str) -> None:
    result = _result(
        verdict="block",
        state="blocked",
        required_gaps=(required_gap,),
        next_action="satisfy the reported governance gap",
    )

    assert result.user_decision_required is True
    assert result.continuation == "await-user"


def test_ethos_result_round_trips_its_public_payload() -> None:
    result = _result(
        verdict="block",
        state="blocked",
        required_gaps=("candidate_base_stale",),
        next_action="ethos lane refresh-base --apply --authorize --json",
    )

    assert EthosResult.from_payload(result.to_dict()) == result
    assert EthosResult.from_payload(json.loads(result.to_json())) == result


def test_ethos_result_rejects_forged_derived_payload() -> None:
    payload = _payload()
    payload["continuation"] = "continue"

    with pytest.raises(ValueError, match="result_derived_field_mismatch:continuation"):
        EthosResult.from_payload(payload)


def test_ethos_result_rejects_incomplete_public_payload() -> None:
    payload = _payload()
    del payload["continuation"]

    with pytest.raises(ValueError, match="result_payload_field_missing:continuation"):
        EthosResult.from_payload(payload)


@pytest.mark.parametrize(
    "field",
    literal_case(
        "kernel.test_result_contract_model:parametrize:test_ethos_result_rejects_truncated_wire_payload:3"
    ),
)
def test_ethos_result_rejects_truncated_wire_payload(field: str) -> None:
    payload = _payload()
    del payload[field]

    with pytest.raises(ValueError, match=f"result_payload_field_missing:{field}"):
        EthosResult.from_payload(payload)


def test_ethos_result_rejects_unclosed_verdicts() -> None:
    cases = (
        ({"required_gaps": ("hard_gap",)}, "pass_with_required_gaps"),
        ({"verdict": "unknown", "state": "unknown"}, "unknown_without_required_gaps"),
        ({"verdict": "block", "state": "block"}, "block_without_reason"),
    )
    for updates, reason in cases:
        with pytest.raises(ValidationError, match=reason):
            _result(**updates)


@pytest.mark.parametrize("severity", ["warning", "error"])
def test_ethos_result_rejects_pass_with_adverse_diagnostic(severity: str) -> None:
    with pytest.raises(ValidationError, match="pass_with_warnings"):
        _result(diagnostics=({"severity": severity, "message": "adverse"},))


@pytest.mark.parametrize(
    "payload",
    literal_case(
        "kernel.test_result_contract_model:parametrize:test_ethos_result_rejects_coercion_and_unknown_fields:4"
    ),
)
def test_ethos_result_rejects_coercion_and_unknown_fields(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EthosResult.model_validate(payload)


def test_projection_preserves_blocking_gaps_without_parallel_success_flag() -> None:
    result = _result(
        command="plan",
        verdict="block",
        state="planned",
        summary={"changed": True},
        diagnostics=({"kind": "probe", "ok": True},),
        required_gaps=("gap-a",),
        next_action="ethos prove --json",
        data={"value": 1},
    )

    payload = json.loads(result.to_json())

    assert payload == {
        "schema_version": 2,
        "command": "plan",
        "verdict": "block",
        "state": "planned",
        "summary": {"changed": True},
        "diagnostics": [{"kind": "probe", "ok": True}],
        "required_gaps": ["gap-a"],
        "next_action": "ethos prove --json",
        "user_decision_required": False,
        "data": {"value": 1},
        "continuation": "blocked",
        "missing_facts_or_evidence": [],
    }


def test_ethos_result_payload_is_deeply_immutable() -> None:
    result = _result(
        summary={"nested": {"value": 1}},
        diagnostics=({"kind": "probe", "details": {"value": 1}},),
        governance_context={"authority": {"owner": "repository"}},
        data={"nested": {"value": 1}},
    )

    with pytest.raises(TypeError):
        result.summary["nested"]["value"] = 2
    with pytest.raises(TypeError):
        result.diagnostics[0]["details"]["value"] = 2
    with pytest.raises(TypeError):
        result.governance_context["authority"]["owner"] = "host"
    with pytest.raises(TypeError):
        result.data["nested"]["value"] = 2


def test_payload_budget_preserves_deep_immutability(tmp_path) -> None:
    bounded = apply_payload_budget(
        _result(data={"large": "x" * 20_000}),
        root=tmp_path,
    )

    with pytest.raises(TypeError):
        bounded.data["artifact_reference"]["path"] = "changed"
    assert Path(bounded.data["artifact_reference"]["path"]).is_file()
