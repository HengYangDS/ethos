"""Every command's result fits its budget; failing steps stay inline; nothing refuses for size."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ethos.result import EthosResult
from ethos.result import apply_payload_budget
from tests.support.ethos_cli_runner import expand_payload


def _check(action_id: str, verdict: str, lines: int) -> dict[str, object]:
    output = "\n".join(f"{action_id} line {index}" for index in range(lines))
    return {
        "action_id": action_id,
        "verdict": verdict,
        "exit_code": 0 if verdict == "pass" else 1,
        "stdout": output,
        "stderr": "",
    }


def _land(checks: list[dict[str, object]], *, padding: int = 0) -> EthosResult:
    return EthosResult(
        command="land",
        verdict="block",
        state="gapped",
        required_gaps=("gate_failed:ruff",),
        next_action="ethos prove --full --execute",
        data={"checks": checks, "evidence": "x" * padding},
    )


def test_a_command_without_its_own_budget_is_bounded_by_the_default(tmp_path: Path) -> None:
    """`land` declares no budget; its oversized result still externalizes its detail."""
    result = _land([_check("ruff", "block", 5)], padding=40_000)

    bounded = apply_payload_budget(result, root=tmp_path)

    assert len(bounded.to_json().encode()) <= 16 * 1024
    assert Path(bounded.data["detail"]["path"]).is_file()


def test_failing_steps_stay_inline_with_their_first_lines(tmp_path: Path) -> None:
    """An agent learns which step failed and why without reading the artifact."""
    checks = [_check(f"gate-{index}", "pass", 3) for index in range(30)]
    checks.append(_check("ruff", "block", 200))
    bounded = apply_payload_budget(_land(checks, padding=40_000), root=tmp_path)

    inline = bounded.data["inline"]
    (failing,) = inline["failing"]
    assert failing["action_id"] == "ruff"
    assert failing["exit_code"] == 1
    assert len(failing["output"]) == 20
    assert failing["output"][0] == "ruff line 0"
    assert failing["omitted_lines"] == 180
    assert inline["passing_count"] == 30


def test_a_result_that_cannot_shrink_is_truncated_never_refused(tmp_path: Path) -> None:
    """Even hundreds of failing steps fit: the list truncates and says how much it dropped."""
    checks = [_check(f"gate-{index}", "block", 50) for index in range(400)]
    bounded = apply_payload_budget(_land(checks, padding=10), root=tmp_path)

    payload = json.loads(bounded.to_json())
    assert len(bounded.to_json().encode()) <= 16 * 1024
    assert payload["data"]["inline"]["omitted_failing"] > 0
    assert payload["verdict"] == "block"


def test_an_oversized_gap_list_is_truncated_with_its_count(tmp_path: Path) -> None:
    """Thousands of gaps still fit: the inline list keeps the first ones and counts the rest."""
    gaps = tuple(f"source_binding_missing:path/{index:05d}.py" for index in range(3_000))
    result = EthosResult(command="prove", verdict="block", state="gapped", required_gaps=gaps)

    bounded = apply_payload_budget(result, root=tmp_path)

    assert len(bounded.to_json().encode()) <= 16 * 1024
    assert bounded.required_gaps[0] == gaps[0]
    assert bounded.data["inline"]["omitted_gaps"] == len(gaps) - len(bounded.required_gaps)
    assert bounded.verdict == "block"


def test_the_handles_a_next_step_needs_stay_inline(tmp_path: Path) -> None:
    """A receipt, a lane path or an exact plan digest is how the next call binds; it never moves."""
    result = EthosResult(
        command="publish",
        verdict="pass",
        state="ready_to_publish",
        next_action="ethos publish --receipt /r.json --apply",
        data={
            "request_receipt": {"path": "/r.json", "sha256": "sha256:" + "a" * 64},
            "path": "/lanes/one",
            "remote_observations": {"peer": "x" * 40_000},
        },
    )

    bounded = apply_payload_budget(result, root=tmp_path)

    assert bounded.data["request_receipt"] == result.data["request_receipt"]
    assert bounded.data["path"] == "/lanes/one"
    assert "remote_observations" not in bounded.data
    assert len(bounded.to_json().encode()) <= 16 * 1024


def test_a_commands_own_evidence_reference_survives_beside_the_detail_handle(
    tmp_path: Path,
) -> None:
    """Prove names its evidence artifact; the bound adds its own handle and never replaces it."""
    evidence = {"path": "artifact.json", "sha256": "sha256:" + "b" * 64}
    result = EthosResult(
        command="prove",
        verdict="pass",
        state="ready",
        data={"artifact_reference": evidence, "attestation": {"body": "x" * 40_000}},
    )

    bounded = apply_payload_budget(result, root=tmp_path)

    assert bounded.data["artifact_reference"] == evidence
    assert Path(bounded.data["detail"]["path"]).is_file()
    assert "attestation" not in bounded.data


def test_the_runner_expands_detail_and_refuses_a_changed_artifact(tmp_path: Path) -> None:
    """A test that needs the evidence reads the digest-bound artifact, never a stale copy."""
    result = _land([_check("ruff", "block", 5)], padding=40_000)
    payload = apply_payload_budget(result, root=tmp_path).to_dict()

    assert expand_payload(payload) == result.to_dict()
    Path(payload["data"]["detail"]["path"]).write_text("{}", encoding="utf-8")
    with pytest.raises(AssertionError, match="payload_artifact_mismatch"):
        expand_payload(payload)


def test_a_large_entry_keeps_its_scalar_fields_and_says_what_it_shortened(tmp_path: Path) -> None:
    """An agent still reads `candidate_update.state` inline; nested evidence moves to detail."""
    update = {
        "state": "candidate_validated",
        "path": "/lanes/one",
        "attestation": {"id": "sha256:" + "d" * 64, "body": "x" * 40_000},
    }
    result = EthosResult(
        command="land",
        verdict="pass",
        state="landed",
        data={"candidate_update": update, "log": ["y" * 100] * 400},
    )

    bounded = apply_payload_budget(result, root=tmp_path)

    assert bounded.data["candidate_update"] == {
        "state": "candidate_validated",
        "path": "/lanes/one",
    }
    assert bounded.data["inline"]["partial"] == ("candidate_update",)
    assert bounded.data["inline"]["moved"] == ("log",)
    assert "log" not in bounded.data
