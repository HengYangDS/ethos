from __future__ import annotations

# ruff: noqa: ARG005, TC003
import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import ethos.adapters.mutation.resolution.lane as resolution
import ethos.surface.cli.lane.resolution as resolution_cli
from ethos_core.contracts.resolution.lane import LaneObservation


def _observation(tmp_path: Path, *, dirty: bool = False) -> LaneObservation:
    return LaneObservation(
        lane_ref="work/example",
        head="a" * 40,
        lane_incarnation_id="lane:one",
        path=tmp_path.as_posix(),
        dirty=dirty,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def _transaction(*responses: str, returncode: int = 0) -> MagicMock:
    transaction = MagicMock()
    transaction.__enter__.return_value = transaction
    transaction.__exit__.return_value = False
    transaction.stdout.readline.side_effect = responses
    transaction.wait.return_value = returncode
    return transaction


def test_resolution_plan_collects_all_request_gaps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        resolution,
        "_observe_lane",
        lambda *_args: (_observation(tmp_path), []),
    )
    report = resolution.plan_lane_resolution(
        root=tmp_path,
        branch="work/example",
        disposition="invalid",
        reason="",
        evidence_refs=(),
        chronicle_ref="",
        recovery_plan="",
        decision_path=tmp_path / "tracked.json",
        break_glass=False,
        apply=False,
    )
    assert report["required_gaps"] == [
        "lane_resolution_disposition_invalid",
        "lane_resolution_reason_required",
        "lane_resolution_evidence_required",
        "lane_resolution_chronicle_required",
        "lane_resolution_recovery_plan_required",
        "lane_resolution_decision_path_not_local_artifact",
    ]
    retire = resolution.plan_lane_resolution(
        root=tmp_path,
        branch="work/example",
        disposition="retire",
        reason="reason",
        evidence_refs=("evidence:review",),
        chronicle_ref="",
        recovery_plan="recover",
        decision_path=tmp_path.parent / "decision.json",
        break_glass=False,
        apply=False,
    )
    assert "retire_exception_requires_break_glass" in retire["required_gaps"]


def test_resolution_plan_and_apply_schema_failure_edges(tmp_path: Path, monkeypatch) -> None:
    observation = _observation(tmp_path)
    monkeypatch.setattr(resolution, "_observe_lane", lambda *_args: (observation, []))
    monkeypatch.setattr(
        resolution,
        "_accepted_chronicle",
        lambda *args, **kwargs: ("evidence/chronicle/x.md", "d" * 64, []),
    )
    monkeypatch.setattr(
        resolution,
        "validate_schema_instance",
        lambda *args, **kwargs: {"ok": False},
    )
    report = resolution.plan_lane_resolution(
        root=tmp_path,
        branch="work/example",
        disposition="block",
        reason="reason",
        evidence_refs=("evidence:review",),
        chronicle_ref="evidence/chronicle/x.md",
        recovery_plan="recover",
        decision_path=tmp_path.parent / "decision.json",
        break_glass=False,
        apply=True,
    )
    assert report["required_gaps"] == ["lane_resolution_decision_invalid"]

    decision = {
        "decision_id": "decision:one",
        "disposition": "block",
        "observation": observation.model_dump(mode="json"),
        "observation_digest": observation.digest(),
    }
    monkeypatch.setattr(resolution, "_read_decision", lambda *args, **kwargs: (decision, []))
    applied = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=False,
        apply=True,
    )
    assert applied["required_gaps"] == ["lane_resolution_receipt_invalid"]


def test_resolution_missing_dirty_and_invalid_decisions(tmp_path: Path, monkeypatch) -> None:
    missing, gaps = resolution._observe_lane(tmp_path, "work/missing")
    assert missing.lane_ref == "work/missing"
    assert gaps == ["lane_resolution_target_missing"]
    assert resolution._read_decision(tmp_path / "missing.json", root=tmp_path)[1] == [
        "lane_resolution_decision_invalid"
    ]

    observation = _observation(tmp_path, dirty=True)
    decision = {
        "decision_id": "decision:one",
        "disposition": "retire",
        "observation": observation.model_dump(mode="json"),
        "observation_digest": observation.digest(),
    }
    monkeypatch.setattr(resolution, "_read_decision", lambda *args, **kwargs: (decision, []))
    monkeypatch.setattr(resolution, "_observe_lane", lambda *_args: (observation, []))
    report = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=False,
        apply=False,
    )
    assert report["required_gaps"] == [
        "irreversible_confirmation_required",
        "dirty_lane_retirement_blocked",
    ]


def test_resolution_observation_reads_single_common_directory_lease(
    tmp_path: Path, monkeypatch
) -> None:
    lane = tmp_path / "lane"
    lane.mkdir()
    monkeypatch.setattr(
        resolution,
        "workspace_status",
        lambda _root: {"worktrees": [{"path": lane.as_posix(), "branch": "work/example"}]},
    )
    monkeypatch.setattr(
        resolution,
        "run_git",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="a" * 40, stderr=""),
    )
    monkeypatch.setattr(resolution, "_untracked_digest", lambda _path: "c" * 64)
    monkeypatch.setattr(
        resolution,
        "leases_by_branch",
        lambda _root: {
            "work/example": {
                "holder_ref": "agent:test:case:holder",
                "lane_incarnation_id": "lane:stored",
            }
        },
    )
    stored, gaps = resolution._observe_lane(tmp_path, "work/example")
    assert gaps == []
    assert stored.holder_ref == "agent:test:case:holder"
    assert stored.lane_incarnation_id == "lane:stored"
    assert stored.ambiguous is False
    assert stored.orphan is False


def test_resolution_read_decision_schema_and_digest_edges(tmp_path: Path, monkeypatch) -> None:
    observation = _observation(tmp_path)
    payload = {
        "decision_id": "lane-decision:one",
        "disposition": "block",
        "observation": observation.model_dump(mode="json"),
        "observation_digest": "bad",
        "evidence_refs": ["evidence:review"],
        "chronicle_ref": "evidence/chronicle/x.md",
        "chronicle_digest": "d" * 64,
        "recovery_plan": "recover",
        "reason": "reason",
        "break_glass": False,
    }
    decision = tmp_path / "decision.json"
    decision.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        resolution, "validate_schema_instance", lambda *args, **kwargs: {"ok": False}
    )
    assert resolution._read_decision(decision, root=tmp_path)[1] == [
        "lane_resolution_decision_invalid"
    ]
    monkeypatch.setattr(
        resolution, "validate_schema_instance", lambda *args, **kwargs: {"ok": True}
    )
    assert resolution._read_decision(decision, root=tmp_path)[1] == [
        "lane_resolution_decision_digest_invalid"
    ]


def test_resolution_untracked_chronicle_and_command_failures(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        resolution.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout=b"", stderr=b""),
    )
    assert resolution._untracked_digest(tmp_path) == hashlib.sha256(b"unavailable").hexdigest()
    outside = tmp_path.parent / "outside.md"
    assert resolution._accepted_chronicle(
        tmp_path, chronicle_ref=outside.as_posix(), disposition="block"
    )[2] == ["lane_resolution_chronicle_outside_repository"]
    wrong = tmp_path / "evidence/chronicle/x.md"
    wrong.parent.mkdir(parents=True)
    wrong.write_text("lane_resolution/preserve", encoding="utf-8")
    assert resolution._accepted_chronicle(
        tmp_path, chronicle_ref="evidence/chronicle/x.md", disposition="block"
    )[2] == ["lane_resolution_chronicle_disposition_mismatch"]


def test_resolution_preserve_inventory_and_retire_failures(tmp_path: Path, monkeypatch) -> None:
    observation = _observation(tmp_path)
    decision = {"decision_id": "decision:one"}
    monkeypatch.setattr(
        resolution,
        "run_git",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="", stderr=""),
    )
    responses = iter(
        (
            subprocess.CompletedProcess(["git"], 0, stdout=b"patch"),
            subprocess.CompletedProcess(["git"], 1, stdout=b""),
        )
    )
    monkeypatch.setattr(resolution.subprocess, "run", lambda *args, **kwargs: next(responses))
    with pytest.raises(ValueError, match="lane_resolution_untracked_inventory_failed"):
        resolution._preserve(root=tmp_path, observation=observation, decision=decision)

    transaction = _transaction("start: ok\n", "prepare: ok\n")
    monkeypatch.setattr(resolution.subprocess, "Popen", lambda *_args, **_kwargs: transaction)
    monkeypatch.setattr(
        resolution,
        "run_git",
        lambda *args, **_kwargs: subprocess.CompletedProcess(args, 1, stdout="", stderr=""),
    )
    with pytest.raises(ValueError, match="lane_resolution_worktree_remove_failed"):
        resolution._retire(root=tmp_path, observation=observation)

    monkeypatch.setattr(
        resolution.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _transaction("start: ok\n", ""),
    )
    with pytest.raises(ValueError, match="lane_resolution_branch_delete_failed"):
        resolution._retire(root=tmp_path, observation=observation, force=True)


def test_resolution_apply_surfaces_retire_runtime_failures(tmp_path: Path, monkeypatch) -> None:
    observation = _observation(tmp_path)
    decision = {
        "decision_id": "decision:one",
        "disposition": "retire",
        "observation": observation.model_dump(mode="json"),
        "observation_digest": observation.digest(),
    }
    monkeypatch.setattr(resolution, "_read_decision", lambda *_args, **_kwargs: (decision, []))
    monkeypatch.setattr(resolution, "_observe_lane", lambda *_args: (observation, []))

    transaction = _transaction()
    transaction.stderr = None
    monkeypatch.setattr(resolution.subprocess, "Popen", lambda *_args, **_kwargs: transaction)
    with pytest.raises(ValueError, match="lane_resolution_branch_delete_failed"):
        resolution.apply_lane_resolution(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            confirm_irreversible=True,
            apply=True,
        )

    transaction = _transaction()
    transaction.stdin.write.side_effect = OSError
    monkeypatch.setattr(resolution.subprocess, "Popen", lambda *_args, **_kwargs: transaction)
    with pytest.raises(ValueError, match="lane_resolution_branch_delete_failed"):
        resolution.apply_lane_resolution(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            confirm_irreversible=True,
            apply=True,
        )

    transaction = _transaction("start: ok\n", "prepare: ok\n")
    transaction.stdin.write.side_effect = (None, None, OSError())
    monkeypatch.setattr(resolution.subprocess, "Popen", lambda *_args, **_kwargs: transaction)
    monkeypatch.setattr(
        resolution,
        "run_git",
        MagicMock(
            side_effect=(
                subprocess.CompletedProcess(["git", "worktree"], 0),
                subprocess.CompletedProcess(["git", "show-ref"], 0),
            )
        ),
    )
    report = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=True,
        apply=True,
    )
    assert report["required_gaps"] == [
        "lane_resolution_branch_delete_failed_after_worktree_removed"
    ]


def test_resolution_locks_the_ref_before_removing_the_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observation = _observation(tmp_path)
    transaction = _transaction("start: ok\n", "prepare: ok\n", "commit: ok\n")
    monkeypatch.setattr(resolution.subprocess, "Popen", lambda *_args, **_kwargs: transaction)
    monkeypatch.setattr(
        resolution,
        "run_git",
        lambda *args, **_kwargs: (
            transaction.stdout.readline.call_count == 2
            and subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        ),
    )

    resolution._retire(root=tmp_path, observation=observation, force=True)

    assert transaction.stdout.readline.call_count == 3


def test_resolution_reports_ref_preservation_after_commit_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observation = _observation(tmp_path)

    transaction = _transaction("start: ok\n", "prepare: ok\n", "", returncode=1)
    monkeypatch.setattr(resolution.subprocess, "Popen", lambda *_args, **_kwargs: transaction)
    responses = iter(
        (
            subprocess.CompletedProcess(["git", "worktree"], 0, stdout="", stderr=""),
            subprocess.CompletedProcess(["git", "show-ref"], 0, stdout="", stderr=""),
        )
    )
    monkeypatch.setattr(resolution, "run_git", lambda *_args, **_kwargs: next(responses))

    with pytest.raises(
        ValueError, match="lane_resolution_branch_delete_failed_after_worktree_removed"
    ):
        resolution._retire(root=tmp_path, observation=observation, force=True)


def test_resolution_cli_delegates_and_emits(tmp_path: Path, monkeypatch) -> None:
    emitted: list[tuple[object, bool]] = []
    report = {"ok": True, "state": "planned", "branch": "work/example", "required_gaps": []}
    monkeypatch.setattr(resolution_cli, "resolve_root", lambda root: tmp_path)
    monkeypatch.setattr(resolution_cli, "plan_lane_resolution", lambda **kwargs: report)
    monkeypatch.setattr(resolution_cli, "apply_lane_resolution", lambda **kwargs: report)
    monkeypatch.setattr(
        resolution_cli,
        "emit",
        lambda result, json_output=False: emitted.append((result, json_output)),
    )
    resolution_cli.lane_resolution_decide(
        branch="work/example",
        disposition="block",
        reason="reason",
        evidence_ref=("evidence:review",),
        chronicle_ref="evidence/chronicle/x.md",
        recovery_plan="recover",
        decision_path=tmp_path / "decision.json",
        break_glass=False,
        apply=False,
        root=tmp_path,
        json_output=True,
    )
    resolution_cli.lane_resolution_apply(
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=False,
        apply=False,
        root=tmp_path,
        json_output=True,
    )
    assert [result.command for result, _ in emitted] == [
        "lane resolution decide",
        "lane resolution apply",
    ]
