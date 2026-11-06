"""Every command's result fits its budget; failing steps stay inline; nothing refuses for size."""

from __future__ import annotations

import hashlib
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

    (failing,) = bounded.bound["failing"]
    observed = (failing["action_id"], failing["exit_code"], len(failing["output"]))
    assert observed == ("ruff", 1, 20)
    assert (failing["output"][0], failing["omitted_lines"]) == ("ruff line 0", 180)
    assert bounded.bound["passing_count"] == 30


def test_a_result_that_cannot_shrink_is_truncated_never_refused(tmp_path: Path) -> None:
    """Even hundreds of failing steps fit: the list truncates and says how much it dropped."""
    checks = [_check(f"gate-{index}", "block", 50) for index in range(400)]
    bounded = apply_payload_budget(_land(checks, padding=10), root=tmp_path)

    assert len(bounded.to_json().encode()) <= 16 * 1024
    assert (bounded.bound["omitted_failing"] > 0, bounded.verdict) == (True, "block")


def test_an_oversized_gap_list_is_truncated_with_its_count(tmp_path: Path) -> None:
    """Thousands of gaps still fit: the inline list keeps the first ones and counts the rest."""
    gaps = tuple(f"source_binding_missing:path/{index:05d}.py" for index in range(3_000))
    result = EthosResult(command="prove", verdict="block", state="gapped", required_gaps=gaps)

    bounded = apply_payload_budget(result, root=tmp_path)

    assert len(bounded.to_json().encode()) <= 16 * 1024
    assert (bounded.required_gaps[0], bounded.verdict) == (gaps[0], "block")
    assert bounded.bound["omitted_gaps"] == len(gaps) - len(bounded.required_gaps)


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


def _stale(root: Path) -> Path:
    """Write one `status` detail file older than the week-long retention window."""
    stale = root / "payloads" / "status" / ("0" * 64 + ".json")
    stale.parent.mkdir(parents=True)
    stale.write_text("{}", encoding="utf-8")
    week = 7 * 24 * 3600
    os.utime(stale, (time.time() - week - 60, time.time() - week - 60))
    return stale


def test_detail_has_an_agent_safe_path_and_stale_detail_is_removed(tmp_path: Path) -> None:
    """A path an agent can pass unquoted; detail older than a week goes when new detail arrives."""
    stale = _stale(tmp_path)
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


@pytest.mark.parametrize(
    ("command", "entry"),
    [
        (
            "prove",
            {"artifact_reference": {"path": "artifact.json", "sha256": "sha256:" + "b" * 64}},
        ),
        ("adopt", {"detail": "commit_signature_untrusted"}),
    ],
)
def test_a_commands_own_data_entries_survive_beside_the_bound(
    tmp_path: Path, command: str, entry: dict[str, object]
) -> None:
    """Prove names its evidence and adopt its failure in `data`; the bound never replaces them."""
    result = EthosResult(
        command=command, verdict="pass", state="ready", data=entry | {"log": ["z" * 100] * 400}
    )

    bounded = apply_payload_budget(result, root=tmp_path)

    assert {key: bounded.data[key] for key in entry} == entry
    assert Path(bounded.bound["detail"]["path"]).is_file()


def test_small_entries_move_largest_first_until_the_result_fits(tmp_path: Path) -> None:
    """Entries under the inline size still go when together they exceed the budget."""
    entries = {f"entry_{index:02}": "e" * (600 + index) for index in range(40)}
    result = EthosResult(command="lane status", verdict="pass", state="ready", data=entries)

    bounded = apply_payload_budget(result, root=tmp_path)

    assert len(bounded.to_json().encode()) <= 16 * 1024
    assert bounded.bound["moved"] == tuple(sorted(set(entries) - set(bounded.data)))
    moved = min(len(entries[key]) for key in bounded.bound["moved"])
    assert moved >= max(len(entries[key]) for key in bounded.data)


def _rebound(payload: dict[str, object], content: bytes) -> dict[str, object]:
    """Point a bounded payload at other detail bytes whose digest and size it then names."""
    detail = dict(payload["bound"]["detail"])
    Path(detail["path"]).write_bytes(content)
    detail |= {
        "sha256": f"sha256:{hashlib.sha256(content).hexdigest()}",
        "size_bytes": len(content),
    }
    return payload | {"bound": payload["bound"] | {"detail": detail}}


def test_detail_that_names_another_result_refuses(tmp_path: Path) -> None:
    """Matching bytes are not enough: the detail must be a result that agrees with the bound."""
    result = _land([_check("ruff", "block", 5)], padding=40_000)
    payload = apply_payload_budget(result, root=tmp_path).to_dict()
    other = EthosResult(command="land", verdict="pass", state="landed").to_json().encode()

    for content in (b"{}", other):
        with pytest.raises(ValueError, match="result_detail_mismatch"):
            expand_result(_rebound(payload, content))
    Path(payload["bound"]["detail"]["path"]).unlink()
    with pytest.raises(ValueError, match="result_detail_mismatch"):
        expand_result(payload)


def test_expansion_returns_another_builds_result_as_it_was_written(tmp_path: Path) -> None:
    """Digest, size and kept fields bind the detail; this build's result model does not."""
    result = _land([_check("ruff", "block", 5)], padding=40_000)
    payload = apply_payload_budget(result, root=tmp_path).to_dict() | {"producer": "next build"}
    full = result.to_dict() | {"producer": "next build"}

    assert expand_result(_rebound(payload, json.dumps(full).encode())) == full
    with pytest.raises(ValueError, match="result_detail_mismatch"):
        expand_result(_rebound(payload, b"[]"))


def test_stale_detail_that_cannot_be_removed_stays_without_failing(tmp_path: Path) -> None:
    """Retention is best effort: an undeletable stale file never blocks the new result."""
    stale = _stale(tmp_path)
    stale.parent.chmod(0o500)
    try:
        # The new detail goes to its own command's directory; only the stale one is read-only.
        result = EthosResult(
            command="lane status", verdict="pass", state="ready", data={"x": "y" * 40_000}
        )
        bounded = apply_payload_budget(result, root=tmp_path)
    finally:
        stale.parent.chmod(0o700)
    assert stale.exists()
    assert Path(bounded.bound["detail"]["path"]).is_file()
