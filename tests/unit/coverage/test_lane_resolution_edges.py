from __future__ import annotations

# ruff: noqa: ARG005
import hashlib
import json
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

import ethos.adapters.mutation.resolution._effects as resolution_effects
import ethos.adapters.mutation.resolution._shared as resolution_shared
import ethos.adapters.mutation.resolution.closeout.cleanup.core as resolution_cleanup
import ethos.adapters.mutation.resolution.closeout.recovery as resolution_recovery
import ethos.adapters.mutation.resolution.lane as resolution
import ethos.adapters.mutation.resolution.observation as resolution_observation
import ethos.adapters.mutation.resolution.preservation.core as resolution_preservation
import ethos.adapters.mutation.resolution.receipts as resolution_receipts
import ethos.surface.cli.lane.resolution as resolution_cli
from ethos_core.contracts.resolution.lane import LaneObservation
from tests.support.contract_helpers import init_git_repo

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
    monkeypatch.setattr(resolution_recovery, "accepted_control_root", lambda _root: control_root)
    monkeypatch.setattr(resolution_recovery, "current_record_root", lambda _root: artifact_root)
    apply_request = {
        "root": tmp_path,
        "decision_path": tmp_path / "decision.json",
        "confirm_irreversible": False,
        "apply": True,
    }
    applied = resolution.apply_lane_resolution(**apply_request)
    assert applied["required_gaps"] == ["lane_resolution_receipt_invalid"]

    monkeypatch.setattr(
        resolution_recovery,
        "accepted_control_root",
        lambda _root: (_ for _ in ()).throw(
            ValueError("lane_resolution_accepted_control_root_unavailable")
        ),
    )
    unavailable = resolution.apply_lane_resolution(**apply_request)
    assert unavailable["required_gaps"] == ["lane_resolution_accepted_control_root_unavailable"]

    monkeypatch.setattr(resolution_recovery, "accepted_control_root", lambda _root: control_root)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            resolution_recovery,
            "claim_effect_receipt_reservation",
            lambda *_args, **_kwargs: (None, None, "lane_resolution_receipt_invalid"),
        )
        invalid_reservation = resolution.apply_lane_resolution(**apply_request)
    assert invalid_reservation["required_gaps"] == ["lane_resolution_receipt_invalid"]

    monkeypatch.setattr(
        resolution_recovery,
        "prepare_resolution_effect",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("unexpected effect failure")),
    )
    effect_failure = resolution.apply_lane_resolution(**apply_request)
    assert effect_failure["required_gaps"] == ["lane_resolution_effect_failed"]

    monkeypatch.setattr(
        resolution_cleanup,
        "release_resolution_receipt_reservation",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("cleanup failed")),
    )
    cleanup_failure = resolution.apply_lane_resolution(**apply_request)
    assert cleanup_failure["required_gaps"] == [
        "lane_resolution_effect_failed",
        "lane_resolution_receipt_reservation_release_failed",
    ]


def test_resolution_missing_dirty_and_invalid_decisions(tmp_path: Path, monkeypatch) -> None:
    repo = init_git_repo(tmp_path / "repo")
    missing, gaps = resolution_observation.observe_lane(repo, "work/missing")
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


def test_resolution_chronicle_command_failures(tmp_path: Path) -> None:
    accepted_chronicle = resolution._accepted_chronicle
    outside = tmp_path.parent / "outside.md"
    assert accepted_chronicle(tmp_path, chronicle_ref=outside.as_posix(), disposition="block")[
        2
    ] == ["lane_resolution_chronicle_outside_repository"]
    wrong = tmp_path / "evidence/chronicle/x.md"
    wrong.parent.mkdir(parents=True)
    wrong.write_text("lane_resolution/preserve", encoding="utf-8")
    assert accepted_chronicle(
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


def test_resolution_shared_path_and_chronicle_failure_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    assert not resolution_shared.record_destination_safe(root, tmp_path / "outside.json")
    assert not resolution_shared.record_destination_safe(root, root / "nested/../record.json")

    destination = root / "record.json"
    path_type = type(destination)
    original_resolve = path_type.resolve

    def fail_destination_resolve(path, *args, **kwargs):
        if path == destination.absolute():
            raise OSError("unavailable")
        return original_resolve(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(path_type, "resolve", fail_destination_resolve)
        assert not resolution_shared.record_destination_safe(root, destination)

    base_decision = {
        "disposition": "block",
        "chronicle_digest": hashlib.sha256(b"lane_resolution/block\n").hexdigest(),
    }
    for reference in (
        (tmp_path / "absolute.md").as_posix(),
        "evidence/chronicle/../outside.md",
        "docs/chronicle/event.md",
        "evidence/chronicle",
    ):
        assert not resolution_shared.current_chronicle_matches(
            root, base_decision | {"chronicle_ref": reference}
        )

    chronicle_ref = "evidence/chronicle/event.md"
    decision = base_decision | {"chronicle_ref": chronicle_ref}
    with monkeypatch.context() as scoped:
        scoped.setattr(
            resolution_shared.record_posix,
            "open_directory_path",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
        )
        assert not resolution_shared.current_chronicle_matches(root, decision)
    assert not resolution_shared.current_chronicle_matches(root, decision)
    chronicle = root / chronicle_ref
    chronicle.parent.mkdir(parents=True)
    assert not resolution_shared.current_chronicle_matches(root, decision)
    chronicle.write_bytes(b"lane_resolution/block\n")
    with monkeypatch.context() as scoped:
        scoped.setattr(
            resolution_shared.record_posix,
            "directory_descriptor_is_live",
            lambda *_args: False,
        )
        assert not resolution_shared.current_chronicle_matches(root, decision)


def test_resolution_shared_cross_record_binding_edges() -> None:
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000090"
    observation = {"lane_ref": "work/example", "head": "a" * 40}
    decision = {
        "observation": observation,
        "observation_digest": "b" * 64,
        "content_sha256": "c" * 64,
        "disposition": "block",
        "break_glass": False,
    }
    reservation_record = {
        "lane_ref": "work/other",
        "head": observation["head"],
        "decision_sha256": decision["content_sha256"],
        "physical_path": "reservation.json",
    }
    assert resolution_shared.cross_record_invalid_paths(
        decisions={decision_id: decision},
        manifests={},
        receipts={},
        clears={},
        reservations={decision_id: reservation_record},
    ) == ["reservation.json"]

    receipt = {
        "state": "preserved",
        "preservation_manifest_sha256": "d" * 64,
        "physical_path": "receipt.json",
    }
    manifest = {
        "manifest_sha256": "d" * 64,
        "physical_path": "manifest.json",
    }
    clear = {"manifest_sha256": "e" * 64, "physical_path": "clear.json"}
    assert resolution_shared.cross_record_invalid_paths(
        decisions={},
        manifests={decision_id: manifest},
        receipts={decision_id: receipt},
        clears={decision_id: clear},
        reservations={},
    ) == ["clear.json"]

    quarantined = manifest | {"quarantined": True}
    assert resolution_shared.cross_record_invalid_paths(
        decisions={},
        manifests={decision_id: quarantined},
        receipts={decision_id: receipt},
        clears={},
        reservations={},
    ) == ["manifest.json"]
    assert resolution_shared.cross_record_invalid_paths(
        decisions={},
        manifests={},
        receipts={},
        clears={decision_id: clear},
        reservations={},
    ) == ["clear.json"]


def test_resolution_lane_write_and_recovery_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observation = _observation(tmp_path)
    monkeypatch.setattr(resolution, "observe_lane", lambda *_args: (observation, []))
    monkeypatch.setattr(
        resolution,
        "_accepted_chronicle",
        lambda *_args, **_kwargs: ("evidence/chronicle/x.md", "d" * 64, []),
    )
    monkeypatch.setattr(
        resolution, "validate_schema_instance", lambda *_args, **_kwargs: {"ok": True}
    )
    monkeypatch.setattr(resolution, "canonical_record_path", lambda *_args: True)
    monkeypatch.setattr(resolution, "current_record_root", lambda _root: tmp_path / "records")
    monkeypatch.setattr(
        resolution,
        "write_json_atomic",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )
    planned = resolution.plan_lane_resolution(
        root=tmp_path,
        branch=observation.lane_ref,
        disposition="block",
        reason="reason",
        evidence_refs=("evidence:review",),
        chronicle_ref="evidence/chronicle/x.md",
        recovery_plan="recover",
        decision_path=tmp_path / "decision.json",
        break_glass=False,
        apply=True,
    )
    assert planned["required_gaps"] == ["lane_resolution_decision_path_not_local_artifact"]

    decision = {
        "decision_id": "lane-decision:00000000-0000-4000-8000-000000000091",
        "disposition": "retire",
        "observation": observation.model_dump(mode="json"),
        "observation_digest": observation.digest(),
    }
    monkeypatch.setattr(resolution, "_read_decision", lambda *_args, **_kwargs: (decision, []))
    monkeypatch.setattr(resolution, "lane_resolution_inventory", lambda **_kwargs: {})
    monkeypatch.setattr(resolution, "current_record_integrity_gap", lambda **_kwargs: "")
    monkeypatch.setattr(
        resolution,
        "ownerless_recovery_context",
        lambda **_kwargs: ({}, None, None, "lane_resolution_recovery_unavailable"),
    )
    blocked = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=True,
        apply=True,
    )
    assert blocked["state"] == "blocked"
    assert blocked["required_gaps"] == ["lane_resolution_recovery_unavailable"]

    monkeypatch.setattr(
        resolution,
        "ownerless_recovery_context",
        lambda **_kwargs: (
            {"recovery_state": "effect_complete_receipt_missing"},
            tmp_path / "control",
            tmp_path / "records",
            "",
        ),
    )
    monkeypatch.setattr(
        resolution,
        "recover_ownerless_resolution",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("must not recover in dry run")),
    )
    dry_run = resolution.apply_lane_resolution(
        root=tmp_path,
        decision_path=tmp_path / "decision.json",
        confirm_irreversible=True,
        apply=False,
    )
    assert dry_run["ok"] is True


def test_resolution_lane_malformed_decision_and_chronicle_observation_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(resolution, "canonical_record_path", lambda *_args: True)
    monkeypatch.setattr(resolution, "current_record_root", lambda _root: tmp_path / "records")
    monkeypatch.setattr(
        resolution,
        "read_current_record_path",
        lambda *_args, **_kwargs: (b"{", "current"),
    )
    assert resolution._read_decision(tmp_path / "decision.json", root=tmp_path)[1] == [
        "lane_resolution_decision_invalid"
    ]

    identity = resolution_observation.DescriptorIdentity(1, 2, 3, 4, 5, 6)
    working = resolution_observation.ExactFileSnapshot(b"chronicle", identity)
    monkeypatch.setattr(
        resolution,
        "git_object_bytes",
        lambda *_args: (_ for _ in ()).throw(
            resolution_observation.OwnerlessGitObservationError("unverifiable", "git_object")
        ),
    )
    assert not resolution._accepted_chronicle_matches(tmp_path, "evidence/chronicle/x.md", working)


def test_resolution_receipt_rejects_explicit_noncanonical_default(tmp_path: Path) -> None:
    observation = _observation(tmp_path)
    decision = {
        "decision_id": "lane-decision:00000000-0000-4000-8000-000000000092",
        "disposition": "retire",
        "break_glass": False,
    }
    receipt = resolution_effects.completion_receipt(decision, observation, "retired", {})
    receipt["ownerless_closeout_binding"] = None
    assert not resolution_receipts.exact_ownerless_resolution_receipt(
        receipt=receipt,
        decision=decision,
        observation=observation,
        expected_binding={},
    )
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        resolution_receipts._validated_resolution_receipt(
            root=tmp_path,
            receipt=receipt,
            require_ownerless_closeout_binding=True,
        )
