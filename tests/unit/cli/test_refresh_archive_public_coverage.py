from __future__ import annotations

from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive_change as archive
import ethos.adapters.mutation.lane_lifecycle.archive_recovery as recovery
import ethos.adapters.mutation.lane_lifecycle.change_overlay as overlay
import ethos.adapters.openspec.lifecycle.archive_effect as archive_effect
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.openspec_lifecycle import assert_lifecycle_outcome

BRANCH = "work/feature"
HEAD = "old-head"
NEW_HEAD = "new-head"
CHANGE = "fixture-change"
ARCHIVE_DATE = datetime.now(UTC).date().isoformat()
ARCHIVE_PATH = f"openspec/changes/archive/{ARCHIVE_DATE}-fixture-change"


def test_archive_commit_subject_is_conventional(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    assert archive.lifecycle_commit_subject(repo, "archive", CHANGE) == (
        "chore(openspec): archive fixture-change"
    )


class _Dumpable:
    def __init__(self, **payload: object) -> None:
        self.payload = payload

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return dict(self.payload)


def _completed_governance(*, remaining: int = 0) -> dict[str, object]:
    return {
        "required_gaps": [],
        "lifecycle": {"changes": [{"name": CHANGE, "progress": {"remaining": remaining}}]},
        "commands": {"status": {"json": {"changes": []}}},
    }


def _archive_result(
    root: Path, *, change: str = CHANGE, path: str = ARCHIVE_PATH
) -> dict[str, Any]:
    absolute = root / path if not Path(path).is_absolute() else Path(path)
    return {
        "exit_code": 0,
        "parse_error": "",
        "stderr": "",
        "command": ["openspec", "archive", change],
        "json": {
            "archive": {
                "change": change,
                "path": absolute.as_posix(),
                "specsUpdated": [],
                "totals": {},
            }
        },
    }


def _stub_archive_public(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    guard: dict[str, object] | None = None,
    remaining: int = 0,
    result: dict[str, Any] | None = None,
    collision: bool = False,
    preserved_tree: str = "",
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test")
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: HEAD)
    monkeypatch.setattr(
        archive,
        "leases_by_branch",
        lambda _root: {
            BRANCH: {
                "lease_state": "valid",
                "holder_ref": "agent:test",
                "expected_head": HEAD,
                "expected_tree": "tree",
                "base_commitment_path": f"openspec/changes/{CHANGE}/commitment.toml",
            }
        },
    )
    monkeypatch.setattr(archive, "work_lane_transition_gaps", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(archive, "proof_gaps", lambda *_args: [])
    monkeypatch.setattr(
        archive,
        "openspec_governance_report",
        lambda *_args, **_kwargs: _completed_governance(remaining=remaining),
    )
    monkeypatch.setattr(
        archive,
        "local_state_mutation_guard",
        lambda _root: guard or {"required_gaps": []},
    )

    def git_stdout(_root: Path, *args: str) -> str:
        return {
            ("branch", "--show-current"): BRANCH,
            ("status", "--short"): "",
            ("diff", "--cached", "--name-only", "--diff-filter=ACMRTD"): (
                f"{ARCHIVE_PATH}/commitment.toml"
            ),
            ("write-tree",): "archive-tree",
            ("show", "-s", "--format=%ct", NEW_HEAD): "0",
        }.get(args, "")

    monkeypatch.setattr(archive, "git_stdout", git_stdout)

    def collision_report(*_args: object) -> archive.ArchiveCollision | None:
        preserved = root / f"{ARCHIVE_PATH}.preserved"
        if not collision:
            return None
        if preserved_tree or preserved.exists():
            message = "openspec_archive_collision_preservation_conflict"
            raise ValueError(message)
        return archive.ArchiveCollision(ARCHIVE_PATH, "archive-tree", f"{ARCHIVE_PATH}.preserved")

    monkeypatch.setattr(archive, "archive_collision", collision_report)
    postimage_observations = 0

    def observe_archive_postimage(
        *_args: object, **_kwargs: object
    ) -> archive_effect.ArchivePostimage:
        nonlocal postimage_observations
        postimage_observations += 1
        if postimage_observations == 1:
            return archive_effect.ArchivePostimage(
                change=CHANGE,
                head=HEAD,
                scope=None,
                active_present=True,
            )
        return archive_effect.ArchivePostimage(
            change=CHANGE,
            head=HEAD,
            scope={
                "archive_path": ARCHIVE_PATH,
                "changed_paths": (f"{ARCHIVE_PATH}/commitment.toml",),
                "completion_artifacts": (),
                "tree": "archive-tree",
            },
            active_present=False,
        )

    monkeypatch.setattr(archive, "archive_postimage", observe_archive_postimage)
    monkeypatch.setattr(archive.openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        archive.openspec_cli,
        "run_json",
        lambda *_args: result or _archive_result(root),
    )
    monkeypatch.setattr(archive, "dirty_changed_paths", lambda _root: ("spec.md",))
    monkeypatch.setattr(archive, "normalize_projected_specs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(archive, "stage_git_worktree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(archive, "archive_transition_environment", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        archive,
        "lifecycle_commit_subject",
        lambda *_args, **_kwargs: "chore(openspec): archive fixture-change",
    )


def test_archive_public_dry_run_and_local_state_guard(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    ready = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)
    assert ready["state"] == "ready_to_archive"
    assert_lifecycle_outcome(
        ready,
        "zero_effect",
        "not_required",
        "absent",
        f"ethos lane archive-change --change {CHANGE} --expect-head {HEAD} --apply --json",
    )

    _stub_archive_public(
        monkeypatch,
        tmp_path,
        guard={"required_gaps": ["migration"], "next_action": "ethos state migrate"},
    )
    blocked = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)
    assert blocked["required_gaps"] == ["local_state_migration_required"]
    assert blocked["next_action"] == "ethos state migrate"


def test_archive_public_rejects_an_existing_collision_preservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(
        monkeypatch,
        tmp_path,
        collision=True,
        preserved_tree="archive-tree",
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["openspec_archive_collision_preservation_conflict"]
    assert_lifecycle_outcome(
        report,
        "zero_effect",
        "not_required",
        "absent",
        "ethos lane status --json",
        user_decision_required=True,
    )


def test_archive_public_preserves_an_untracked_collision_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path, collision=True)
    preserved = tmp_path / f"{ARCHIVE_PATH}.preserved"
    preserved.mkdir(parents=True)
    marker = preserved / "marker"
    marker.write_text("keep", encoding="utf-8")

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["openspec_archive_collision_preservation_conflict"]
    assert marker.read_text(encoding="utf-8") == "keep"


def test_archive_public_preflight_rejects_incomplete_native_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path, remaining=1)
    monkeypatch.setattr(
        archive,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "required_gaps": ["native_warning"],
            "lifecycle": {"changes": [{"name": CHANGE, "progress": {"remaining": 1}}]},
        },
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)

    assert report["required_gaps"] == [
        "native_warning",
        f"openspec_change_incomplete:{CHANGE}",
    ]


def test_archive_public_missing_native_command_does_not_mutate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(archive.openspec_cli, "openspec_base_command", lambda: None)

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == ["openspec_official_cli_missing"]
    assert_lifecycle_outcome(
        report,
        "zero_effect",
        "not_required",
        "absent",
        "ethos lane status --json",
        user_decision_required=True,
    )


def test_archive_public_exception_compensates_exact_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(
        archive.openspec_cli,
        "run_json",
        lambda *_args: (_ for _ in ()).throw(ValueError("archive_failed")),
    )
    compensated: list[dict[str, object]] = []
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda _root, **kwargs: compensated.append(kwargs),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["archive_failed"]
    assert_lifecycle_outcome(
        report,
        "mutated",
        "completed",
        "absent",
        f"ethos lane archive-change --change {CHANGE} --expect-head {HEAD} --apply --json",
    )
    assert compensated == [{"head": HEAD, "untracked_path": ""}]


@pytest.mark.parametrize("collision", [False, True])
def test_archive_public_commit_failure_compensates_native_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, collision: bool
) -> None:
    _stub_archive_public(monkeypatch, tmp_path, collision=collision)
    monkeypatch.setattr(archive, "move_tracked_tree", lambda *_args: None)
    monkeypatch.setattr(
        archive,
        "commit_git_worktree",
        lambda *_args, **_kwargs: {"verdict": "block", "error": "hook rejected"},
    )
    compensated: list[str] = []
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda _root, **kwargs: compensated.append(str(kwargs["untracked_path"])),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == ["openspec_archive_commit_failed"]
    assert report["stderr"] == "hook rejected"
    assert_lifecycle_outcome(
        report,
        "mutated",
        "completed",
        "absent",
        f"ethos lane archive-change --change {CHANGE} --expect-head {HEAD} --apply --json",
    )
    assert compensated == [f"{ARCHIVE_PATH}.preserved" if collision else ARCHIVE_PATH]


@pytest.mark.parametrize(
    ("result", "collision", "compensated_path"),
    [
        (
            {
                "exit_code": 0,
                "parse_error": "",
                "json": {"archive": {"change": CHANGE, "path": "/outside"}},
            },
            False,
            "",
        ),
        (
            {
                "exit_code": 0,
                "parse_error": "",
                "json": {"archive": {"change": "other", "path": ""}},
            },
            False,
            "",
        ),
        (
            {
                "exit_code": 0,
                "parse_error": "",
                "json": {"archive": {"change": "other", "path": ""}},
            },
            True,
            f"{ARCHIVE_PATH}.preserved",
        ),
    ],
)
def test_archive_public_rejects_invalid_native_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    result: dict[str, object],
    *,
    collision: bool,
    compensated_path: str,
) -> None:
    _stub_archive_public(monkeypatch, tmp_path, result=result, collision=collision)
    monkeypatch.setattr(archive, "move_tracked_tree", lambda *_args: None)
    compensated: list[str] = []
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda _root, **kwargs: compensated.append(str(kwargs["untracked_path"])),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == ["openspec_archive_result_invalid"]
    assert_lifecycle_outcome(
        report,
        "mutated",
        "completed",
        "absent",
        f"ethos lane archive-change --change {CHANGE} --expect-head {HEAD} --apply --json",
    )
    assert compensated == [compensated_path]


def test_archive_public_reports_failed_compensation_and_retained_residue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(
        monkeypatch,
        tmp_path,
        result={
            "exit_code": 0,
            "parse_error": "",
            "json": {"archive": {"change": "other", "path": ""}},
        },
    )
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("restore_failed")),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == [
        "openspec_archive_result_invalid",
        "openspec_archive_compensation_failed",
    ]
    assert_lifecycle_outcome(
        report,
        "mutated",
        "failed",
        "retained",
        "ethos lane status --json",
        user_decision_required=True,
    )
    assert report["compensation_error"] == "restore_failed"


def test_archive_public_retries_committed_transition_before_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: NEW_HEAD)
    lease = {
        "expected_head": HEAD,
        "base_commitment_path": f"openspec/changes/{CHANGE}/commitment.toml",
    }
    monkeypatch.setattr(archive, "leases_by_branch", lambda _root: {BRANCH: dict(lease)})
    monkeypatch.setattr(
        archive,
        "git_stdout",
        lambda _root, *args: {
            ("branch", "--show-current"): BRANCH,
            ("rev-parse", f"{NEW_HEAD}^"): HEAD,
            ("diff", "--name-only", "--diff-filter=ACMRTD", HEAD, NEW_HEAD): (
                f"{ARCHIVE_PATH}/commitment.toml"
            ),
        }.get(args, ""),
    )
    monkeypatch.setattr(recovery, "current_tracked_head", lambda _root: NEW_HEAD)
    monkeypatch.setattr(recovery, "leases_by_branch", lambda _root: {BRANCH: dict(lease)})
    monkeypatch.setattr(recovery, "git_stdout", archive.git_stdout)
    monkeypatch.setattr(recovery, "work_lane_transition_gaps", lambda *_args, **_kwargs: [])
    transitions: list[dict[str, object]] = []
    monkeypatch.setattr(
        recovery,
        "issue_archive_effect",
        lambda *_args, **_kwargs: _Dumpable(id="archive-receipt"),
    )
    monkeypatch.setattr(recovery, "exact_archive_paths", lambda *_args: True)
    monkeypatch.setattr(recovery, "read_attestation_set", lambda _root: ("", ()))
    monkeypatch.setattr(recovery, "record_attestation_once", lambda _root, receipt: receipt)
    monkeypatch.setattr(recovery, "exact_carrier_relocation", lambda *_args: True)

    def transition(**kwargs: object) -> dict[str, object]:
        transitions.append(kwargs)
        lease.update(
            expected_head=NEW_HEAD,
            base_commitment_path=f"{ARCHIVE_PATH}/commitment.toml",
        )
        return {"verdict": "pass", "required_gaps": []}

    monkeypatch.setattr(overlay, "work_lane_ref_transition_report", transition)
    monkeypatch.setattr(overlay, "leases_by_branch", lambda _root: {BRANCH: dict(lease)})
    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["verdict"] == "pass"
    assert report["state"] == "archive_attestation_recovered"
    assert transitions == [
        {
            "root": tmp_path,
            "phase": "committed",
            "ref_name": f"refs/heads/{BRANCH}",
            "old_value": HEAD,
            "new_value": NEW_HEAD,
        }
    ]


def _stub_archive_attestation_recovery(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "head": HEAD,
        "record_attempts": 0,
        "record_ids": [],
        "selected": [],
        "receipt": _Dumpable(id="archive-receipt"),
    }
    lease = {
        "lease_state": "valid",
        "holder_ref": "agent:test",
        "expected_head": HEAD,
        "expected_tree": "tree",
        "base_commitment_path": f"openspec/changes/{CHANGE}/commitment.toml",
    }
    _stub_archive_public(monkeypatch, root)
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: state["head"])
    monkeypatch.setattr(archive, "leases_by_branch", lambda _root: {BRANCH: dict(lease)})
    monkeypatch.setattr(
        archive,
        "git_stdout",
        lambda _root, *args: {
            ("branch", "--show-current"): BRANCH,
            ("status", "--short"): "",
            ("rev-parse", f"{HEAD}:{ARCHIVE_PATH}"): "",
            ("diff", "--cached", "--name-only", "--diff-filter=ACMRTD"): (
                f"{ARCHIVE_PATH}/commitment.toml"
            ),
            ("write-tree",): "archive-tree",
            ("rev-parse", f"{NEW_HEAD}^"): HEAD,
            ("diff", "--name-only", "--diff-filter=ACMRTD", HEAD, NEW_HEAD): (
                f"{ARCHIVE_PATH}/commitment.toml"
            ),
            ("show", "-s", "--format=%ct", NEW_HEAD): "0",
        }.get(args, ""),
    )
    monkeypatch.setattr(recovery, "current_tracked_head", lambda _root: state["head"])
    monkeypatch.setattr(recovery, "leases_by_branch", lambda _root: {BRANCH: dict(lease)})
    monkeypatch.setattr(recovery, "git_stdout", archive.git_stdout)
    monkeypatch.setattr(recovery, "work_lane_transition_gaps", lambda *_args, **_kwargs: [])

    def commit(*_args: object, **_kwargs: object) -> dict[str, object]:
        state["head"] = NEW_HEAD
        lease.update(
            expected_head=NEW_HEAD,
            base_commitment_path=f"{ARCHIVE_PATH}/commitment.toml",
        )
        return {"verdict": "pass"}

    monkeypatch.setattr(archive, "commit_git_worktree", commit)
    monkeypatch.setattr(recovery, "exact_carrier_relocation", lambda *_args: True)
    monkeypatch.setattr(recovery, "exact_archive_paths", lambda *_args: True)
    monkeypatch.setattr(
        recovery,
        "issue_archive_effect",
        lambda *_args, **_kwargs: state["receipt"],
    )
    monkeypatch.setattr(
        recovery, "read_attestation_set", lambda _root: ("", tuple(state["selected"]))
    )

    def record(_root: Path, receipt: object) -> object:
        state["record_attempts"] = int(state["record_attempts"]) + 1
        record_ids = state["record_ids"]
        assert isinstance(record_ids, list)
        assert isinstance(receipt, _Dumpable)
        record_ids.append(receipt.payload["id"])
        if state["record_attempts"] == 1:
            message = "attestation_set_cas_retry_exhausted"
            raise ValueError(message)
        selected = state["selected"]
        assert isinstance(selected, list)
        selected.append(receipt)
        return receipt

    monkeypatch.setattr(recovery, "record_attestation_once", record)
    return state


def test_archive_public_recovers_attestation_after_the_git_effect_completed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = _stub_archive_attestation_recovery(monkeypatch, tmp_path)

    partial = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert partial["state"] == "archive_attestation_pending"
    assert partial["head"] == NEW_HEAD
    assert partial["required_gaps"] == ["openspec_archive_attestation_not_recorded"]
    recovery = partial["recovery"]
    next_action = partial["next_action"]
    assert isinstance(recovery, dict)
    assert recovery["reason"] == "attestation_set_cas_retry_exhausted"
    assert isinstance(next_action, str)
    assert f"--expect-head {NEW_HEAD}" in next_action

    recovered = archive.archive_change(
        root=tmp_path,
        change=CHANGE,
        expect_head=NEW_HEAD,
        apply=True,
    )

    assert recovered["verdict"] == "pass"
    assert recovered["state"] == "archive_attestation_recovered"
    assert state["record_attempts"] == 2
    assert len(set(state["record_ids"])) == 1
    attestation = recovered["attestation"]
    assert isinstance(attestation, dict)
    assert attestation["id"] == state["record_ids"][0]

    replayed = archive.archive_change(
        root=tmp_path,
        change=CHANGE,
        expect_head=NEW_HEAD,
        apply=True,
    )
    assert replayed["verdict"] == "pass"
    assert replayed["state"] == "archive_attestation_recovered"
    assert replayed["required_gaps"] == []
    assert replayed["attestation"] == attestation
    assert state["record_attempts"] == 2


def test_archive_lease_recovery_dry_run_projects_the_exact_retry_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    stale_lease = {
        "lease_state": "valid",
        "holder_ref": "agent:test",
        "expected_head": HEAD,
        "expected_tree": "tree",
        "base_commitment_path": f"openspec/changes/{CHANGE}/commitment.toml",
    }
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: NEW_HEAD)
    monkeypatch.setattr(archive, "leases_by_branch", lambda _root: {BRANCH: stale_lease})
    monkeypatch.setattr(recovery, "git_stdout", lambda *_args: f"{ARCHIVE_PATH}/commitment.toml")
    monkeypatch.setattr(recovery, "exact_carrier_relocation", lambda *_args: True)
    monkeypatch.setattr(recovery, "exact_archive_paths", lambda *_args: True)

    report = archive.archive_change(
        root=tmp_path,
        change=CHANGE,
        expect_head=HEAD,
        apply=False,
    )

    assert report["state"] == "ready_to_recover_archive_lease"
    assert report["next_action"] == (
        f"ethos lane archive-change --change {CHANGE} --expect-head {HEAD} --apply --json"
    )


@pytest.mark.parametrize(
    "gap",
    [
        "attestation_set_ref_dangling",
        "attestation_set_root_invalid",
        "attestation_set_member_invalid",
        "attestation_set_symbolic_ref_forbidden",
    ],
)
def test_archive_recovery_fails_closed_when_the_attestation_set_is_damaged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    gap: str,
) -> None:
    _stub_archive_attestation_recovery(monkeypatch, tmp_path)
    partial = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)
    assert partial["state"] == "archive_attestation_pending"

    def damaged_set(_root: Path) -> object:
        raise ValueError(gap)

    monkeypatch.setattr(recovery, "read_attestation_set", damaged_set)

    report = archive.archive_change(
        root=tmp_path,
        change=CHANGE,
        expect_head=NEW_HEAD,
        apply=False,
    )

    assert report["verdict"] == "block"
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [gap]


class _WorkLanePolicy:
    def role_for_branch(self, _branch: str) -> str:
        return "work_lane"


@pytest.mark.parametrize(
    ("lease", "actor", "expected_gap", "expected_state", "expected_action"),
    [
        (
            {},
            "agent:test",
            f"work_lane_missing_lease:{BRANCH}",
            "lease_missing",
            "ethos lane status --json",
        ),
        (
            {
                "lease_state": "expired",
                "holder_ref": "agent:test",
                "lease_id": "lease:test",
                "epoch": 7,
                "expected_head": HEAD,
                "expected_tree": "tree",
                "expires_at": "2026-08-20T00:00:00Z",
                "payload_sha256": "a" * 64,
            },
            "agent:test",
            f"work_lane_lease_expired:{BRANCH}",
            "lease_expired",
            (
                "ethos lane lease resume --lease-id lease:test --epoch 7 "
                f"--expect-head {HEAD} --expires-at 2026-08-20T00:00:00Z "
                f"--payload-sha256 {'a' * 64} --branch {BRANCH} "
                "--holder-ref agent:test --apply --json"
            ),
        ),
        (
            {
                "lease_state": "valid",
                "holder_ref": "agent:other",
                "expected_head": HEAD,
                "expected_tree": "tree",
            },
            "agent:test",
            "lease_actor_mismatch",
            "different_holder",
            (
                "ethos attestation query --predicate lane-resolution:takeover "
                f"--subject git:branch:{BRANCH} --json"
            ),
        ),
    ],
)
def test_work_lane_transition_reports_the_first_exact_lease_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    lease: dict[str, object],
    actor: str,
    expected_gap: str,
    expected_state: str,
    expected_action: str,
) -> None:
    monkeypatch.setattr(overlay, "load_branch_role_policy", lambda _root: _WorkLanePolicy())
    monkeypatch.setattr(overlay, "current_tree", lambda _root, _head: "tree")
    monkeypatch.setattr(overlay, "git_stdout", lambda *_args: "")

    gaps = overlay.work_lane_transition_gaps(
        tmp_path,
        branch=BRANCH,
        head=HEAD,
        expect_head=HEAD,
        lease=lease,
        actor=actor,
        role_gap="archive_requires_work_lane",
    )

    assert gaps == [expected_gap]
    report = recovery.archive_preflight_report(BRANCH, HEAD, CHANGE, gaps, lease=lease)
    assert report["state"] == expected_state
    assert report["next_action"] == expected_action


def test_archive_zero_effect_preflight_has_no_compensation_gap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(archive, "leases_by_branch", lambda _root: {})
    monkeypatch.setattr(
        archive,
        "work_lane_transition_gaps",
        lambda *_args, **_kwargs: [f"work_lane_missing_lease:{BRANCH}"],
    )
    compensated: list[object] = []
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda *_args, **kwargs: compensated.append(kwargs),
    )

    report = archive.archive_change(
        root=tmp_path,
        change=CHANGE,
        expect_head=HEAD,
        apply=True,
    )

    assert report["state"] == "lease_missing"
    assert report["required_gaps"] == [f"work_lane_missing_lease:{BRANCH}"]
    assert_lifecycle_outcome(
        report,
        "zero_effect",
        "not_required",
        "absent",
        "ethos lane status --json",
        user_decision_required=True,
    )
    assert compensated == []
    required_gaps = report["required_gaps"]
    assert isinstance(required_gaps, list)
    assert not any("compensation" in gap or "cleanup" in gap for gap in required_gaps)
