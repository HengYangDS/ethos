"""Every command's result fits its budget; failing steps stay inline; nothing refuses for size."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from ethos.result import EthosResult
from ethos.result import apply_payload_budget
from ethos.result import expand_result


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
    assert Path(bounded.bound["detail"]["path"]).is_file()


def test_failing_steps_stay_inline_with_their_first_lines(tmp_path: Path) -> None:
    """An agent learns which step failed and why without reading the artifact."""
    checks = [_check(f"gate-{index}", "pass", 3) for index in range(30)]
    checks.append(_check("ruff", "block", 200))
    bounded = apply_payload_budget(_land(checks, padding=40_000), root=tmp_path)

    inline = bounded.bound
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
    assert payload["bound"]["omitted_failing"] > 0
    assert payload["verdict"] == "block"


def test_an_oversized_gap_list_is_truncated_with_its_count(tmp_path: Path) -> None:
    """Thousands of gaps still fit: the inline list keeps the first ones and counts the rest."""
    gaps = tuple(f"source_binding_missing:path/{index:05d}.py" for index in range(3_000))
    result = EthosResult(command="prove", verdict="block", state="gapped", required_gaps=gaps)

    bounded = apply_payload_budget(result, root=tmp_path)

    assert len(bounded.to_json().encode()) <= 16 * 1024
    assert bounded.required_gaps[0] == gaps[0]
    assert bounded.bound["omitted_gaps"] == len(gaps) - len(bounded.required_gaps)
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
    assert Path(bounded.bound["detail"]["path"]).is_file()
    assert "attestation" not in bounded.data


def test_a_bounded_result_reads_in_full_and_refuses_a_changed_artifact(tmp_path: Path) -> None:
    """A consumer that needs the evidence reads the digest-bound artifact, never a stale copy."""
    result = _land([_check("ruff", "block", 5)], padding=40_000)
    payload = apply_payload_budget(result, root=tmp_path).to_dict()

    assert expand_result(payload) == result.to_dict()
    assert expand_result(result.to_dict()) == result.to_dict()
    Path(payload["bound"]["detail"]["path"]).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="result_detail_mismatch"):
        expand_result(payload)


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
    assert bounded.bound["partial"] == ("candidate_update",)
    assert bounded.bound["moved"] == ("log",)
    assert "log" not in bounded.data


def test_detail_has_an_agent_safe_path_and_stale_detail_is_removed(tmp_path: Path) -> None:
    """A path an agent can pass unquoted; detail older than a week goes when new detail arrives."""
    stale = tmp_path / "payloads" / "status" / ("0" * 64 + ".json")
    stale.parent.mkdir(parents=True)
    stale.write_text("{}", encoding="utf-8")
    week = 7 * 24 * 3600
    os.utime(stale, (time.time() - week - 60, time.time() - week - 60))
    result = EthosResult(
        command="lane prewrite", verdict="pass", state="admitted", data={"x": "y" * 40_000}
    )

    detail = Path(apply_payload_budget(result, root=tmp_path).bound["detail"]["path"])

    assert " " not in detail.as_posix()
    assert detail.parent.name == "lane-prewrite"
    assert detail.is_file()
    assert not stale.exists()


def test_a_store_that_refuses_detail_leaves_the_result_inline(tmp_path: Path) -> None:
    """Detail is a cache: when it cannot be written, the result still fits and says why."""
    blocked = tmp_path / "store"
    blocked.write_text("not a directory", encoding="utf-8")
    result = _land([_check("ruff", "block", 5)], padding=40_000)

    bounded = apply_payload_budget(result, root=blocked)

    assert "detail" not in bounded.bound
    assert bounded.bound["detail_unavailable"]
    assert len(bounded.to_json().encode()) <= 16 * 1024
    assert bounded.verdict == "block"
    with pytest.raises(ValueError, match="result_detail_unavailable"):
        expand_result(bounded.to_dict())


def test_a_commands_own_detail_entry_is_never_replaced(tmp_path: Path) -> None:
    """`adopt` names a failure in `data.detail`; the bound lives beside data, not inside it."""
    result = EthosResult(
        command="adopt",
        verdict="block",
        state="gapped",
        required_gaps=("formation_git_commit_failed",),
        data={"detail": "commit_signature_untrusted", "log": ["z" * 100] * 400},
    )

    bounded = apply_payload_budget(result, root=tmp_path)

    assert bounded.data["detail"] == "commit_signature_untrusted"
    assert Path(bounded.bound["detail"]["path"]).is_file()
