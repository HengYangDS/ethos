from __future__ import annotations

# ruff: noqa: ARG005
import hashlib
import json
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

import ethos.adapters.mutation.resolution._effects as resolution_effects
import ethos.adapters.mutation.resolution._observation as resolution_observation
import ethos.adapters.mutation.resolution.closeout.recovery as resolution_recovery
import ethos.adapters.mutation.resolution.lane as resolution
import ethos.adapters.mutation.resolution.preservation.core as resolution_preservation
import ethos.adapters.mutation.resolution.receipts as resolution_receipts
import ethos.surface.cli.lane.resolution as resolution_cli
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from pathlib import Path


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
    monkeypatch.setattr(resolution, "canonical_record_path", lambda *_args: True)
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
    monkeypatch.setattr(resolution, "current_record_root", lambda _root: artifact_root)
    apply_request = {
        "root": tmp_path,
        "decision_path": tmp_path / "decision.json",
        "confirm_irreversible": False,
        "apply": True,
    }
    applied = resolution.apply_lane_resolution(**apply_request)
    assert applied["required_gaps"] == ["lane_resolution_receipt_invalid"]

    monkeypatch.setattr(
        resolution,
        "accepted_control_root",
        lambda _root: (_ for _ in ()).throw(
            ValueError("lane_resolution_accepted_control_root_unavailable")
        ),
    )
    unavailable = resolution.apply_lane_resolution(**apply_request)
    assert unavailable["required_gaps"] == ["lane_resolution_accepted_control_root_unavailable"]

    monkeypatch.setattr(resolution, "accepted_control_root", lambda _root: control_root)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            resolution_recovery,
            "claim_receipt_reservation",
            lambda *_args, **_kwargs: (False, None, "lane_resolution_receipt_invalid"),
        )
        invalid_reservation = resolution.apply_lane_resolution(**apply_request)
    assert invalid_reservation["required_gaps"] == ["lane_resolution_receipt_invalid"]

    monkeypatch.setattr(
        resolution,
        "prepare_resolution_effect",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("unexpected effect failure")),
    )
    effect_failure = resolution.apply_lane_resolution(**apply_request)
    assert effect_failure["required_gaps"] == ["lane_resolution_effect_failed"]

    monkeypatch.setattr(
        resolution,
        "release_resolution_receipt_reservation",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("cleanup failed")),
    )
    cleanup_failure = resolution.apply_lane_resolution(**apply_request)
    assert cleanup_failure["required_gaps"] == [
        "lane_resolution_effect_failed",
        "lane_resolution_receipt_reservation_release_failed",
    ]


def test_resolution_missing_dirty_and_invalid_decisions(tmp_path: Path, monkeypatch) -> None:
    missing, gaps = resolution_observation.observe_lane(tmp_path, "work/missing")
    assert missing.lane_ref == "work/missing"
    assert gaps == ["lane_resolution_target_missing"]
    record_root = tmp_path / "records"
    decision_path = record_root / "decisions" / "missing.json"
    monkeypatch.setattr(resolution, "canonical_record_path", lambda *_args: True)
    monkeypatch.setattr(resolution, "current_record_root", lambda _root: record_root)
    assert resolution._read_decision(decision_path, root=tmp_path)[1] == [
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


def test_resolution_observation_uses_shared_status_and_lease_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = tmp_path / "lane"
    lane.mkdir()
    monkeypatch.setattr(
        resolution_observation,
        "workspace_status",
        lambda _root: {"worktrees": [{"branch": "work/example", "path": lane.as_posix()}]},
    )

    def run_git(_root: Path, *args: str, **_kwargs):
        stdout = "a" * 40 if args[:1] == ("rev-parse",) else ""
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(resolution_observation, "run_git", run_git)
    monkeypatch.setattr(resolution_observation, "untracked_digest", lambda _path: "c" * 64)
    monkeypatch.setattr(
        resolution_observation,
        "leases_by_branch",
        lambda _root: {
            "work/example": {
                "holder_ref": "agent:test:case:holder",
                "lane_incarnation_id": "lane:stored",
            }
        },
    )
    observation, gaps = resolution_observation.observe_lane(tmp_path, "work/example")
    assert gaps == []
    assert observation.holder_ref == "agent:test:case:holder"
    assert observation.lane_incarnation_id == "lane:stored"
    assert observation.ambiguous is False
    assert observation.orphan is False

    monkeypatch.setattr(resolution_observation, "leases_by_branch", lambda _root: {})
    inferred, _ = resolution_observation.observe_lane(tmp_path, "work/example")
    assert inferred.holder_ref == ""
    assert inferred.lane_incarnation_id.startswith("decision-incarnation:")
    assert inferred.orphan is True

    monkeypatch.setattr(resolution_observation, "workspace_status", lambda _root: {"worktrees": []})
    monkeypatch.setattr(
        resolution_observation,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["git"], 0, stdout="sha256\n", stderr=""
        ),
    )
    missing, missing_gaps = resolution_observation.observe_lane(tmp_path, "work/missing")
    assert len(missing.head) == 64
    assert missing_gaps == ["lane_resolution_target_missing"]


def test_resolution_read_decision_schema_and_digest_edges(tmp_path: Path, monkeypatch) -> None:
    observation = _observation(tmp_path)
    record_root = tmp_path / "records"
    monkeypatch.setattr(resolution, "canonical_record_path", lambda *_args: True)
    monkeypatch.setattr(resolution, "current_record_root", lambda _root: record_root)
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
    decision = record_root / "decisions" / "decision.json"
    decision.parent.mkdir(parents=True)
    decision.write_bytes(resolution.canonical_current_record_bytes(payload))
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


def test_resolution_preserve_inventory_and_retire_failures(tmp_path: Path, monkeypatch) -> None:
    observation = _observation(tmp_path)
    decision = {"decision_id": "decision:one"}
    package = tmp_path / "package"
    package.mkdir()

    def fixed_git(_root: Path, *args: str, **_kwargs: object):
        if args[:2] == ("bundle", "create"):
            (package / "repository.bundle").write_bytes(b"bundle")
        return subprocess.CompletedProcess(["git", *args], 0, stdout="", stderr="")

    def fixed_git_bytes(_root: Path, *args: str):
        return subprocess.CompletedProcess(["git", *args], 0, stdout=b"patch", stderr=b"")

    monkeypatch.setattr(resolution_preservation, "run_git", fixed_git)
    monkeypatch.setattr(resolution_preservation, "run_git_bytes", fixed_git_bytes)
    monkeypatch.setattr(resolution_effects, "untracked_files", lambda _source: None)
    with pytest.raises(ValueError, match="lane_resolution_untracked_inventory_failed"):
        resolution_effects.preserve_package(tmp_path, package, observation, decision)

    transaction = _transaction("start: ok\n", "prepare: ok\n")
    monkeypatch.setattr(
        resolution_effects.subprocess, "Popen", lambda *_args, **_kwargs: transaction
    )
    monkeypatch.setattr(
        resolution_effects,
        "run_git",
        lambda *args, **_kwargs: subprocess.CompletedProcess(args, 1, stdout="", stderr=""),
    )
    with pytest.raises(ValueError, match="lane_resolution_worktree_remove_failed"):
        resolution_effects.retire_lane(root=tmp_path, observation=observation)

    monkeypatch.setattr(
        resolution_effects.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _transaction("start: ok\n", ""),
    )
    with pytest.raises(ValueError, match="lane_resolution_branch_delete_failed"):
        resolution_effects.retire_lane(root=tmp_path, observation=observation, force=True)


def test_resolution_retire_pre_effect_failure_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observation = _observation(tmp_path)
    transaction = _transaction()
    transaction.stderr = None
    monkeypatch.setattr(
        resolution_effects.subprocess, "Popen", lambda *_args, **_kwargs: transaction
    )
    with pytest.raises(ValueError, match="lane_resolution_branch_delete_failed"):
        resolution_effects.retire_lane(root=tmp_path, observation=observation)

    monkeypatch.setattr(
        resolution_effects.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )
    with pytest.raises(ValueError, match="lane_resolution_branch_delete_failed"):
        resolution_effects.retire_lane(root=tmp_path, observation=observation)


@pytest.mark.parametrize(
    "case",
    [
        (True, "lane_resolution_branch_delete_failed_after_worktree_removed"),
        (False, "lane_resolution_branch_delete_state_uncertain"),
    ],
    ids=("present", "absent"),
)
def test_resolution_retire_commit_failure_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[bool, str],
) -> None:
    present, gap = case
    observation = _observation(tmp_path)
    transaction = _transaction("start: ok\n", "prepare: ok\n")
    transaction.stdin.write.side_effect = (None, None, OSError("commit failed"))
    monkeypatch.setattr(
        resolution_effects.subprocess, "Popen", lambda *_args, **_kwargs: transaction
    )
    results = iter(
        (
            subprocess.CompletedProcess(["git", "worktree"], 0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                ["git", "show-ref"], int(not present), stdout="", stderr=""
            ),
        )
    )
    monkeypatch.setattr(resolution_effects, "run_git", lambda *_args, **_kwargs: next(results))

    with pytest.raises(ValueError, match=gap):
        resolution_effects.retire_lane(root=tmp_path, observation=observation)


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


def test_resolution_effect_and_decision_path_failure_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(resolution, "canonical_record_path", lambda *_args: False)
    assert resolution._read_decision(  # noqa: SLF001, RUF100 - coverage probes the private decision reader boundary
        tmp_path / "decision.json", root=tmp_path
    )[1] == ["lane_resolution_decision_path_not_local_artifact"]


def test_resolution_receipt_and_manifest_validation_edges(tmp_path: Path) -> None:
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000099"
    receipt = resolution_effects.completion_receipt(
        {"decision_id": decision_id, "disposition": "block", "break_glass": False},
        _observation(tmp_path),
        "blocked_by_decision",
        {},
    )
    receipt["decision_id"] = "invalid"
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        resolution_receipts.write_resolution_receipt(
            root=tmp_path,
            receipt=receipt,
            artifact_root=tmp_path,
        )

    package = tmp_path / "package"
    package.mkdir()
    manifest_path = package / "manifest.json"
    verification = {"root": tmp_path, "artifact_root": tmp_path}
    stored_package = {"path": package.as_posix()}
    manifest_path.write_text("{", encoding="utf-8")
    with pytest.raises(TypeError, match="lane_resolution_preservation_manifest_invalid"):
        resolution_receipts.verify_preservation_package(package=stored_package, **verification)

    manifest_path.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError, match="lane_resolution_preservation_manifest_invalid"):
        resolution_receipts.verify_preservation_package(package=stored_package, **verification)

    bundle = package / "repository.bundle"
    patch = package / "tracked.patch"
    bundle.write_bytes(b"bundle")
    patch.write_bytes(b"patch")
    manifest = {
        "decision_id": decision_id,
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "untracked_archive_sha256": "",
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(TypeError, match="lane_resolution_preservation_manifest_invalid"):
        resolution_receipts.verify_preservation_package(
            package={"path": package.as_posix(), "manifest": "invalid"},
            **verification,
        )
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        resolution_receipts.verify_preservation_package(
            package={"path": package.as_posix(), "manifest": {"decision_id": decision_id}},
            **verification,
        )

    manifest["untracked_archive_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        resolution_receipts.verify_preservation_package(package=stored_package, **verification)
