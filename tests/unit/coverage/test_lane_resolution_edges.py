from __future__ import annotations

# ruff: noqa: ARG005, TC003
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution._effects as resolution_effects
import ethos.adapters.mutation.resolution._observation as resolution_observation
import ethos.adapters.mutation.resolution.lane as resolution
import ethos.surface.cli.lane.resolution as resolution_cli
from ethos_core.contracts.resolution.lane import LaneObservation
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo


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


def test_resolution_plan_collects_all_request_gaps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        resolution,
        "observe_lane",
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
    monkeypatch.setattr(resolution, "observe_lane", lambda *_args: (observation, []))
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
    monkeypatch.setattr(
        resolution_effects,
        "validate_schema_instance",
        lambda *args, **kwargs: {"ok": False},
    )
    monkeypatch.setattr(resolution, "_local_artifact_path", lambda *_args: True)
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
        "decision_id": "lane-decision:00000000-0000-4000-8000-000000000004",
        "disposition": "block",
        "observation": observation.model_dump(mode="json"),
        "observation_digest": observation.digest(),
    }
    monkeypatch.setattr(resolution, "_read_decision", lambda *args, **kwargs: (decision, []))
    control_root = tmp_path / "control"
    control_root.mkdir()
    artifact_root = tmp_path / "records"
    monkeypatch.setattr(resolution, "accepted_control_root", lambda _root: control_root)
    monkeypatch.setattr(resolution, "records_artifact_root", lambda _root: artifact_root)
    applied = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=False,
        apply=True,
    )
    assert applied["required_gaps"] == ["lane_resolution_receipt_invalid"]


def test_resolution_missing_dirty_and_invalid_decisions(tmp_path: Path, monkeypatch) -> None:
    missing, gaps = resolution_observation.observe_lane(tmp_path, "work/missing")
    assert missing.lane_ref == "work/missing"
    assert gaps == ["lane_resolution_target_missing"]
    monkeypatch.setattr(resolution, "canonical_record_path", lambda *_args: True)
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
    monkeypatch.setattr(resolution, "observe_lane", lambda *_args: (observation, []))
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


def test_resolution_observation_ambiguous_lease_and_common_dir(tmp_path: Path, monkeypatch) -> None:
    lane = tmp_path / "lane"
    lane.mkdir()
    monkeypatch.setattr(
        resolution_observation,
        "worktree",
        lambda *_args: {"worktree": lane.as_posix(), "branch": "refs/heads/work/example"},
    )
    monkeypatch.setattr(
        resolution_observation,
        "git_output",
        lambda _root, *args, **kwargs: "a" * 40 if args[0] == "rev-parse" else "",
    )
    monkeypatch.setattr(resolution_observation, "untracked_digest", lambda _path: "c" * 64)
    monkeypatch.setattr(
        resolution_observation,
        "leases",
        lambda _root: [
            {"subject": "work/example", "holder_ref": "one"},
            {"subject": "work/example", "holder_ref": "two"},
        ],
    )
    observation, gaps = resolution_observation.observe_lane(tmp_path, "work/example")
    assert gaps == []
    assert observation.ambiguous is True
    assert observation.holder_ref == ""
    assert observation.lane_incarnation_id.startswith("decision-incarnation:")

    monkeypatch.setattr(
        resolution_observation,
        "leases",
        lambda _root: [
            {
                "subject": "work/example",
                "holder_ref": "agent:test:case:holder",
                "lane_incarnation_id": "lane:stored",
            }
        ],
    )
    stored, _ = resolution_observation.observe_lane(tmp_path, "work/example")
    assert stored.holder_ref == "agent:test:case:holder"
    assert stored.lane_incarnation_id == "lane:stored"

    monkeypatch.undo()
    monkeypatch.setattr(
        resolution_observation,
        "git_output",
        lambda *_args, **_kwargs: ".git/worktrees/lane",
    )
    monkeypatch.setattr(
        resolution_observation,
        "active_leases",
        lambda path: [{"path": path.as_posix()}],
    )
    assert resolution_observation.leases(tmp_path)[0]["path"].endswith(".ethos/state/state.sqlite")


def test_resolution_read_decision_schema_and_digest_edges(tmp_path: Path, monkeypatch) -> None:
    observation = _observation(tmp_path)
    monkeypatch.setattr(resolution, "canonical_record_path", lambda *_args: True)
    payload = {
        "decision_id": "lane-decision:00000000-0000-4000-8000-000000000005",
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
        resolution_observation.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout=b"", stderr=b""),
    )
    assert (
        resolution_observation.untracked_digest(tmp_path)
        == hashlib.sha256(b"unavailable").hexdigest()
    )
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

    monkeypatch.setattr(
        resolution_observation,
        "run_git",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="bad"),
    )
    monkeypatch.setattr(
        resolution_effects.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="bad"),
    )
    with pytest.raises(ValueError, match="bad"):
        resolution_observation.git_output(tmp_path, "status")
    with pytest.raises(ValueError, match="bad"):
        resolution_effects.run_command(tmp_path, "false")


def test_resolution_preserve_inventory_and_retire_failures(tmp_path: Path, monkeypatch) -> None:
    observation = _observation(tmp_path)
    decision = {"decision_id": "decision:one"}
    monkeypatch.setattr(resolution_effects, "run_command", lambda *args, **kwargs: None)
    responses = iter(
        (
            subprocess.CompletedProcess(["git"], 0, stdout=b"patch"),
            subprocess.CompletedProcess(["git"], 1, stdout=b""),
        )
    )
    monkeypatch.setattr(
        resolution_effects.subprocess,
        "run",
        lambda *args, **kwargs: next(responses),
    )
    package = tmp_path / "package"
    package.mkdir()
    with pytest.raises(ValueError, match="lane_resolution_untracked_inventory_failed"):
        resolution_effects.preserve_package(tmp_path, package, observation, decision)

    monkeypatch.setattr(
        resolution_effects,
        "run_git",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr=""),
    )
    with pytest.raises(ValueError, match="lane_resolution_branch_delete_failed"):
        resolution_effects.retire_lane(root=tmp_path, observation=observation)

    calls: list[list[str]] = []
    responses = iter(
        (
            subprocess.CompletedProcess(["git"], 0, stdout="", stderr=""),
            subprocess.CompletedProcess(["git"], 1, stdout="", stderr=""),
            subprocess.CompletedProcess(["git"], 0, stdout="", stderr=""),
        )
    )
    monkeypatch.setattr(
        resolution_effects,
        "run_git",
        lambda _root, *args, **kwargs: calls.append(list(args)) or next(responses),
    )
    with pytest.raises(ValueError, match="lane_resolution_worktree_remove_failed"):
        resolution_effects.retire_lane(root=tmp_path, observation=observation)
    assert calls[-1][:2] == ["update-ref", "refs/heads/work/example"]


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


def test_resolution_real_worktree_parser(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    lane = tmp_path / "lane"
    git(repo, "worktree", "add", "-b", "work/example", lane.as_posix(), "dev")
    assert resolution_observation.worktree(repo, "work/example")["worktree"] == lane.as_posix()
