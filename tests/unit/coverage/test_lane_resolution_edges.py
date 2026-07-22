from __future__ import annotations

# ruff: noqa: ARG005
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import ethos.adapters.mutation.resolution._effects as resolution_effects
import ethos.adapters.mutation.resolution._observation as resolution_observation
import ethos.adapters.mutation.resolution._shared as resolution_shared
import ethos.adapters.mutation.resolution.lane as resolution
import ethos.adapters.mutation.resolution.receipts as resolution_receipts
import ethos.adapters.mutation.resolution.records.core as resolution_records
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
    monkeypatch.setattr(resolution, "records_artifact_root", lambda _root: artifact_root)
    applied = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=False,
        apply=True,
    )
    assert applied["required_gaps"] == ["lane_resolution_receipt_invalid"]

    monkeypatch.setattr(
        resolution,
        "accepted_control_root",
        lambda _root: (_ for _ in ()).throw(
            ValueError("lane_resolution_accepted_control_root_unavailable")
        ),
    )
    unavailable = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=False,
        apply=True,
    )
    assert unavailable["required_gaps"] == ["lane_resolution_accepted_control_root_unavailable"]

    monkeypatch.setattr(resolution, "accepted_control_root", lambda _root: control_root)
    monkeypatch.setattr(
        resolution,
        "reserve_resolution_receipt",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("lane_resolution_receipt_invalid")),
    )
    invalid_reservation = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=False,
        apply=True,
    )
    assert invalid_reservation["required_gaps"] == ["lane_resolution_receipt_invalid"]

    monkeypatch.setattr(resolution, "reserve_resolution_receipt", lambda **_kwargs: None)
    monkeypatch.setattr(
        resolution,
        "prepare_resolution_effect",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("unexpected effect failure")),
    )
    effect_failure = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=False,
        apply=True,
    )
    assert effect_failure["required_gaps"] == ["lane_resolution_effect_failed"]

    monkeypatch.setattr(
        resolution,
        "release_resolution_receipt_reservation",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("cleanup failed")),
    )
    cleanup_failure = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=False,
        apply=True,
    )
    assert cleanup_failure["required_gaps"] == [
        "lane_resolution_effect_failed",
        "lane_resolution_receipt_reservation_release_failed",
    ]


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
        resolution_effects.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="bad"),
    )
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


def test_resolution_shared_control_root_failure_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(resolution_shared, "_primary_control_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        resolution_shared,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(accepted_branch="dev"),
    )
    monkeypatch.setattr(resolution_shared, "_git_output", lambda *_args: "")
    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_shared.accepted_control_root(tmp_path)

    missing = tmp_path / "missing"
    monkeypatch.setattr(resolution_shared, "_git_output", lambda *_args: "a" * 40)
    monkeypatch.setattr(
        resolution_shared,
        "_registered_worktrees",
        lambda _root: [
            {"branch": "refs/heads/other", "worktree": tmp_path.as_posix()},
            {"branch": "refs/heads/dev", "worktree": missing.as_posix()},
        ],
    )
    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_shared.accepted_control_root(tmp_path)


def test_resolution_shared_parser_and_path_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        resolution_shared,
        "_git_output",
        lambda *_args: (tmp_path / "missing" / ".git").as_posix(),
    )
    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_shared._primary_control_root(  # noqa: SLF001, RUF100 - coverage probes the private control-root failure boundary
            tmp_path
        )

    monkeypatch.setattr(
        resolution_shared.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr=""),
    )
    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_shared._registered_worktrees(  # noqa: SLF001, RUF100 - coverage probes the private parser failure boundary
            tmp_path
        )

    monkeypatch.setattr(
        resolution_shared.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            0,
            stdout=f"worktree {tmp_path}\nbranch refs/heads/dev\n\n",
            stderr="",
        ),
    )
    assert resolution_shared._registered_worktrees(  # noqa: SLF001, RUF100 - coverage probes the private porcelain parser
        tmp_path
    ) == [{"worktree": tmp_path.as_posix(), "branch": "refs/heads/dev"}]
    assert resolution_shared.canonical_package_path(tmp_path, "invalid") is None
    outside = tmp_path.parent / "outside-record"
    assert resolution_shared.display_path(tmp_path, outside) == outside.resolve().as_posix()


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
    manifest_path.write_text("{", encoding="utf-8")
    with pytest.raises(TypeError, match="lane_resolution_preservation_manifest_invalid"):
        resolution_receipts.verify_preservation_package(
            root=tmp_path,
            package={"path": package.as_posix()},
            artifact_root=tmp_path,
        )

    manifest_path.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError, match="lane_resolution_preservation_manifest_invalid"):
        resolution_receipts.verify_preservation_package(
            root=tmp_path,
            package={"path": package.as_posix()},
            artifact_root=tmp_path,
        )

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
            root=tmp_path,
            package={"path": package.as_posix(), "manifest": "invalid"},
            artifact_root=tmp_path,
        )
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        resolution_receipts.verify_preservation_package(
            root=tmp_path,
            package={"path": package.as_posix(), "manifest": {"decision_id": decision_id}},
            artifact_root=tmp_path,
        )

    manifest["untracked_archive_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        resolution_receipts.verify_preservation_package(
            root=tmp_path,
            package={"path": package.as_posix()},
            artifact_root=tmp_path,
        )


def test_resolution_clear_post_receipt_failure_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000100"
    manifest_sha256 = "a" * 64
    manifest = {
        "manifest_sha256": manifest_sha256,
        "package_path": "package",
        "copy_count": 1,
    }
    monkeypatch.setattr(
        resolution_receipts,
        "_manifests_with_conflicts",
        lambda _root: ({decision_id: manifest}, set()),
    )
    monkeypatch.setattr(resolution_receipts, "_unsafe_package_path_present", lambda _root: False)
    monkeypatch.setattr(resolution_receipts, "_unsafe_record_path_present", lambda _root: False)

    def records(_root: Path, category: str, _schema: str):
        if category == "receipts":
            return ({decision_id: {"preservation_manifest_sha256": manifest_sha256}}, set())
        return ({}, set())

    monkeypatch.setattr(resolution_receipts, "_records_with_conflicts", records)
    monkeypatch.setattr(
        resolution_receipts,
        "_clear_chronicle",
        lambda *_args: ("evidence/chronicle/clear.md", "b" * 64, []),
    )
    monkeypatch.setattr(resolution_receipts, "_validate_schema", lambda *_args: None)
    record_root = tmp_path / "records"
    receipt_path = record_root / "clears" / "receipt.json"
    monkeypatch.setattr(resolution_receipts, "records_artifact_root", lambda _root: record_root)
    monkeypatch.setattr(
        resolution_receipts,
        "clear_receipt_path",
        lambda _root, _decision_id: receipt_path,
    )

    def write_receipt(path: Path, _payload: dict[str, object], *, record_root: Path) -> None:
        assert path.is_relative_to(record_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("receipt\n", encoding="utf-8")

    monkeypatch.setattr(resolution_receipts, "write_json_atomic", write_receipt)
    request = resolution_receipts.LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref="evidence/chronicle/clear.md",
        reason="Clear the exact retained package.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )

    monkeypatch.setattr(resolution_receipts, "record_destination_safe", lambda *_args: False)
    unsafe_receipt = resolution_receipts.clear_lane_resolution_package(
        root=tmp_path,
        request=request,
    )
    assert unsafe_receipt["required_gaps"] == ["lane_resolution_clear_receipt_path_unsafe"]

    monkeypatch.setattr(resolution_receipts, "record_destination_safe", lambda *_args: True)
    monkeypatch.setattr(resolution_receipts, "_package_path_safe", lambda *_args: False)
    unsafe_package = resolution_receipts.clear_lane_resolution_package(
        root=tmp_path,
        request=request,
    )
    assert unsafe_package["required_gaps"] == ["lane_resolution_package_path_unsafe"]
    assert not receipt_path.exists()

    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text("different\n", encoding="utf-8")
    monkeypatch.setattr(resolution_receipts, "_package_path_safe", lambda *_args: True)
    mismatched = resolution_receipts.clear_lane_resolution_package(root=tmp_path, request=request)
    assert mismatched["required_gaps"] == ["lane_resolution_clear_manifest_mismatch"]
    assert not receipt_path.exists()


def test_resolution_receipt_inventory_scan_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    symlink_root = tmp_path / "symlink-root"
    symlink_root.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(resolution_receipts, "artifact_roots", lambda _root: (symlink_root,))
    assert (
        resolution_receipts._unsafe_package_path_present(tmp_path)  # noqa: SLF001, RUF100 - coverage probes the private path-safety scanner
        is True
    )

    unreadable = tmp_path / "unreadable"
    unreadable.mkdir()
    original_iterdir = Path.iterdir
    monkeypatch.setattr(
        Path,
        "iterdir",
        lambda self: (
            (_ for _ in ()).throw(OSError("unreadable"))
            if self == unreadable
            else original_iterdir(self)
        ),
    )
    monkeypatch.setattr(resolution_receipts, "artifact_roots", lambda _root: (unreadable,))
    assert (
        resolution_receipts._unsafe_package_path_present(tmp_path)  # noqa: SLF001, RUF100 - coverage probes the private unreadable-root scanner
        is True
    )

    manifest_root = tmp_path / "manifest-root"
    manifest_path = manifest_root / "package" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({"decision_id": "invalid"}), encoding="utf-8")
    monkeypatch.setattr(resolution_receipts, "artifact_roots", lambda _root: (manifest_root,))
    monkeypatch.setattr(resolution_receipts, "_package_path_safe", lambda *_args: True)
    assert resolution_receipts._manifests_with_conflicts(  # noqa: SLF001, RUF100 - coverage probes invalid stored identifiers
        tmp_path
    ) == ({}, set())

    category_target = tmp_path / "category-target"
    category_target.mkdir()
    category_root = tmp_path / "category-root"
    category_root.mkdir()
    (category_root / "receipts").symlink_to(category_target, target_is_directory=True)
    monkeypatch.setattr(resolution_receipts, "artifact_roots", lambda _root: (category_root,))
    assert resolution_receipts._records_with_conflicts(  # noqa: SLF001, RUF100 - coverage probes symlinked record categories
        tmp_path,
        "receipts",
        "lane-resolution-receipt.schema.json",
    ) == ({}, set())

    decision_id = "lane-decision:00000000-0000-4000-8000-000000000101"
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root, payload in (
        (first, {"decision_id": "invalid"}),
        (first, {"decision_id": decision_id, "head": "a" * 40}),
        (second, {"decision_id": decision_id, "head": "b" * 40}),
    ):
        category = root / "receipts"
        category.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        (category / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(resolution_receipts, "artifact_roots", lambda _root: (first, second))
    monkeypatch.setattr(
        resolution_receipts,
        "validate_schema_instance",
        lambda *_args, **_kwargs: {"ok": True},
    )
    records, conflicts = resolution_receipts._records_with_conflicts(  # noqa: SLF001, RUF100 - coverage probes duplicate immutable records
        tmp_path,
        "receipts",
        "lane-resolution-receipt.schema.json",
    )
    assert records[decision_id]["head"] == "a" * 40
    assert conflicts == {decision_id}


def test_resolution_record_storage_write_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    symlink_root = tmp_path / "record-root-link"
    symlink_root.symlink_to(target, target_is_directory=True)
    assert resolution_shared.record_destination_safe(symlink_root, symlink_root / "record") is False

    record_root = tmp_path / "records"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *args, **kwargs):
        if path == record_root:
            message = "unavailable"
            raise OSError(message)
        return original_resolve(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "resolve", fail_resolve)
        assert (
            resolution_shared.record_destination_safe(record_root, record_root / "record") is False
        )

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        resolution_records.write_json_atomic(
            tmp_path / "outside.json",
            {},
            record_root=record_root,
        )

    destination = record_root / "receipts" / "record.json"
    with monkeypatch.context() as scoped:
        checks = iter((True, False))
        scoped.setattr(resolution_records, "record_destination_safe", lambda *_args: next(checks))
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            resolution_records.write_json_atomic(destination, {}, record_root=record_root)

    with monkeypatch.context() as scoped:
        checks = iter((True, True, False))
        scoped.setattr(resolution_records, "record_destination_safe", lambda *_args: next(checks))
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            resolution_records.write_json_atomic(destination, {}, record_root=record_root)

    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        resolution_records.reserve_resolution_receipt(
            root=tmp_path,
            decision_id="invalid",
            artifact_root=record_root,
        )


def test_resolution_receipt_reservation_failure_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_root = tmp_path / "records"
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000102"
    with monkeypatch.context() as scoped:
        checks = iter((True, True, False))
        scoped.setattr(resolution_records, "record_destination_safe", lambda *_args: next(checks))
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            resolution_records.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=decision_id,
                artifact_root=record_root,
            )

    destination = resolution_records.receipt_path(
        tmp_path,
        decision_id,
        artifact_root=record_root,
    )
    reservation = destination.with_name(f".{destination.stem}.receipt-reservation")
    with monkeypatch.context() as scoped:
        scoped.setattr(
            resolution_records,
            "_fsync_directory",
            lambda _directory: (_ for _ in ()).throw(RuntimeError("fsync failed")),
        )
        with pytest.raises(RuntimeError, match="fsync failed"):
            resolution_records.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=decision_id,
                artifact_root=record_root,
            )
    assert not reservation.exists()

    with monkeypatch.context() as scoped:
        checks = iter((True, True, True, True, False, True))
        scoped.setattr(resolution_records, "record_destination_safe", lambda *_args: next(checks))
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            resolution_records.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=decision_id,
                artifact_root=record_root,
            )
    assert not reservation.exists()

    occupied_id = "lane-decision:00000000-0000-4000-8000-000000000103"
    occupied_destination = resolution_records.receipt_path(
        tmp_path,
        occupied_id,
        artifact_root=record_root,
    )

    def occupy_destination(_directory: Path) -> None:
        occupied_destination.parent.mkdir(parents=True, exist_ok=True)
        occupied_destination.write_text("occupied\n", encoding="utf-8")

    with monkeypatch.context() as scoped:
        scoped.setattr(resolution_records, "_fsync_directory", occupy_destination)
        with pytest.raises(FileExistsError):
            resolution_records.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=occupied_id,
                artifact_root=record_root,
            )
    assert occupied_destination.is_file()

    with monkeypatch.context() as scoped:
        scoped.setattr(resolution_records, "record_destination_safe", lambda *_args: False)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            resolution_records.release_resolution_receipt_reservation(
                root=tmp_path,
                decision_id=decision_id,
                artifact_root=record_root,
            )

    missing_id = "lane-decision:00000000-0000-4000-8000-000000000104"
    resolution_records.release_resolution_receipt_reservation(
        root=tmp_path,
        decision_id=missing_id,
        artifact_root=record_root,
    )
