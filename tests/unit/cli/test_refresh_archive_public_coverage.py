# ruff: noqa: SLF001
from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive_change as archive
import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as refresh
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts


class _Dumpable:
    def __init__(self, **payload: object) -> None:
        self.payload = payload

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return dict(self.payload)


def _refresh_status(
    *,
    branch: str = "work/feature",
    role: str = "work_lane",
    dirty: bool = False,
    candidate: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "branch": branch,
        "role": role,
        "dirty": dirty,
        "candidate": candidate
        or {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": "/candidate",
            "head": "candidate-head",
        },
    }


def _stub_refresh_reader(
    monkeypatch: pytest.MonkeyPatch,
    status: dict[str, object],
    *,
    head: str = "work-head",
) -> None:
    monkeypatch.setattr(
        refresh,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(candidate_branch="candidate/dev"),
    )
    monkeypatch.setattr(refresh, "workspace_status", lambda _root: status)
    monkeypatch.setattr(
        refresh,
        "run_git",
        lambda _root, *_args, **_kwargs: SimpleNamespace(
            stdout=f"{head}\n", stderr="", returncode=0
        ),
    )
    monkeypatch.setattr(refresh, "changed_paths", lambda _path: ())


@pytest.mark.parametrize(
    ("candidate", "gap"),
    [
        ({"exists": False, "worktree_exists": False}, "candidate_branch_missing"),
        ({"exists": True, "worktree_exists": False}, "candidate_worktree_missing"),
        ({"exists": True, "worktree_exists": True}, "candidate_worktree_dirty"),
    ],
)
def test_refresh_public_reader_reports_candidate_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    candidate: dict[str, object],
    gap: str,
) -> None:
    candidate |= {"worktree_path": "/candidate", "head": "candidate-head"}
    _stub_refresh_reader(monkeypatch, _refresh_status(candidate=candidate))
    monkeypatch.setattr(refresh, "changed_paths", lambda _path: ("dirty",))

    report = refresh.refresh_work_lane_base(root=tmp_path)

    assert report["required_gaps"] == [gap]


def test_refresh_public_reader_exposes_identity_repair_route(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_refresh_reader(monkeypatch, _refresh_status())
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_args: False)
    monkeypatch.setattr(refresh, "equivalent_commit_identity", lambda *_args: True)

    report = refresh.refresh_work_lane_base(root=tmp_path)

    assert report["required_gaps"] == ["commit_identity_replacement_required"]
    assert "repair-identity" in str(report["next_action"])


def test_refresh_detached_recovery_failure_is_public_block(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_refresh_reader(monkeypatch, _refresh_status(branch="detached"))
    monkeypatch.setattr(
        refresh,
        "_recover_work_lane",
        lambda *_args: (_ for _ in ()).throw(ValueError("git_effect_recovery_ambiguous")),
    )

    report = refresh.refresh_work_lane_base(root=tmp_path, apply=True)

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["git_effect_recovery_ambiguous"]


def _recovery_plan(
    *,
    updates: dict[str, GitRefUpdate] | None = None,
    execution_branch: str = "work/feature",
) -> TransitionPlan:
    effect = GitEffect(
        updates=(
            updates
            if updates is not None
            else {"refs/heads/work/feature": GitRefUpdate(expected="a" * 40, desired="b" * 40)}
        ),
        assertions={"refs/heads/candidate/dev": "c" * 40},
    )
    return compile_git_effect_plan(
        Commitment(
            id="authority:test:refresh",
            intent="Recover one refresh effect.",
            subjects=("repository:test",),
            permissions=effect.permissions,
        ),
        Facts(
            repository="repository:test",
            head="b" * 40,
            tree="f" * 40,
            observed_at=datetime(2026, 8, 10, tzinfo=UTC),
            values={
                "refs": {name: update.expected for name, update in effect.updates.items()},
                "assertions": effect.assertions,
            },
        ),
        prior_attestations={},
        policy={"operation": "lane.refresh", "execution_branch": execution_branch},
        effect=effect,
    )


@pytest.mark.parametrize(
    ("plan", "gap"),
    [
        (None, "git_effect_recovery_ambiguous"),
        (
            _recovery_plan(
                updates={
                    "refs/heads/work/feature": GitRefUpdate(expected="a" * 40, desired="b" * 40),
                    "refs/heads/work/other": GitRefUpdate(expected="d" * 40, desired="e" * 40),
                }
            ),
            "git_effect_recovery_unproven",
        ),
        (
            _recovery_plan(
                updates={"refs/heads/dev": GitRefUpdate(expected="a" * 40, desired="b" * 40)},
                execution_branch="dev",
            ),
            "git_effect_recovery_unproven",
        ),
    ],
)
def test_refresh_detached_recovery_rejects_ambiguous_plans(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    plan: TransitionPlan | None,
    gap: str,
) -> None:
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: "b" * 40)
    monkeypatch.setattr(refresh, "recover_plan", lambda *_args, **_kwargs: plan)

    with pytest.raises(ValueError, match=gap):
        refresh._recover_work_lane(tmp_path, "candidate/dev", "c" * 40, "/candidate")


def test_refresh_detached_recovery_replays_exact_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = _recovery_plan()
    calls: list[str] = []
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: "b" * 40)
    monkeypatch.setattr(refresh, "recover_plan", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(
        refresh, "_attach_work_lane", lambda _root, branch, head: calls.append(f"{branch}:{head}")
    )

    def execute(_root: Path, _plan: TransitionPlan, **kwargs: object) -> None:
        assert kwargs["detached_branch"] == "work/feature"
        kwargs["projection"]()

    monkeypatch.setattr(refresh, "execute_git_effect", execute)

    report = refresh._recover_work_lane(tmp_path, "candidate/dev", "c" * 40, "/candidate")

    assert report["state"] == "base_refreshed"
    assert report["previous_head"] == "a" * 40
    assert calls == [f"work/feature:{'b' * 40}"]


def test_refresh_recovery_and_restore_compensate_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = _recovery_plan()
    monkeypatch.setattr(refresh, "ref_head", lambda *_args: "new")
    monkeypatch.setattr(
        refresh,
        "execute_git_effect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("cas")),
    )
    assert (
        refresh._recover_applied_refresh(tmp_path, plan, lambda: None, "work/feature", "b" * 40)
        is None
    )

    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: "detached")
    monkeypatch.setattr(
        refresh,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(stdout="", stderr="", returncode=0),
    )
    monkeypatch.setattr(refresh, "compensate_git_worktree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        refresh,
        "attach_worktree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("attachment stale")),
    )
    assert refresh._restore_pre_refresh_checkout(tmp_path, "work/feature", "old") == [
        "refresh_base_worktree_restore_failed"
    ]


def _completed_governance(change: str = "fixture-change") -> dict[str, object]:
    return {
        "required_gaps": [],
        "lifecycle": {"changes": [{"name": change, "progress": {"remaining": 0}}]},
        "commands": {"status": {"json": {"changes": []}}},
    }


def _archive_result(root: Path, change: str = "fixture-change") -> dict[str, Any]:
    path = root / "openspec/changes/archive/2026-08-10-fixture-change"
    return {
        "exit_code": 0,
        "parse_error": "",
        "stderr": "",
        "command": ["openspec", "archive", change],
        "json": {
            "archive": {
                "change": change,
                "path": path.as_posix(),
                "specsUpdated": [],
                "totals": {},
            }
        },
    }


def _stub_archive_public(
    monkeypatch: pytest.MonkeyPatch,
    *,
    guard: dict[str, object] | None = None,
) -> None:
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: "old-head")
    monkeypatch.setattr(
        archive,
        "git_stdout",
        lambda _root, *args: "work/feature" if args[:2] == ("branch", "--show-current") else "",
    )
    monkeypatch.setattr(archive, "leases_by_branch", lambda _root: {"work/feature": {}})
    monkeypatch.setattr(archive, "_archive_preflight", lambda *_args: [])
    monkeypatch.setattr(archive, "_archive_collision", lambda *_args: None)
    monkeypatch.setattr(
        archive,
        "local_state_mutation_guard",
        lambda _root: guard or {"required_gaps": []},
    )


def test_archive_public_dry_run_and_local_state_guard(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch)
    ready = archive.archive_change(root=tmp_path, change="fixture-change", expect_head="old-head")
    assert ready["state"] == "ready_to_archive"

    _stub_archive_public(
        monkeypatch,
        guard={"required_gaps": ["migration"], "next_action": "ethos state migrate"},
    )
    blocked = archive.archive_change(
        root=tmp_path, change="fixture-change", expect_head="old-head", apply=True
    )
    assert blocked["required_gaps"] == ["local_state_migration_required"]
    assert blocked["next_action"] == "ethos state migrate"


def test_archive_public_exception_compensates_exact_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch)
    compensated: list[dict[str, object]] = []
    monkeypatch.setattr(
        archive,
        "_apply_archive",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("archive_failed")),
    )
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda _root, **kwargs: compensated.append(kwargs),
    )

    report = archive.archive_change(
        root=tmp_path, change="fixture-change", expect_head="old-head", apply=True
    )

    assert report["state"] == "repair_required"
    assert report["required_gaps"] == ["archive_failed"]
    assert compensated == [{"head": "old-head", "untracked_path": ""}]


def test_archive_preflight_rejects_incomplete_native_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(archive, "_precondition_gaps", lambda *_args: [])
    monkeypatch.setattr(
        archive,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "required_gaps": ["native_warning"],
            "lifecycle": {"changes": [{"name": "fixture-change", "progress": {"remaining": 1}}]},
        },
    )

    gaps = archive._archive_preflight(
        tmp_path, "work/feature", "head", "head", {}, "fixture-change"
    )

    assert gaps == ["native_warning", "openspec_change_incomplete:fixture-change"]


def test_archive_apply_missing_native_command_does_not_mutate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        archive, "openspec_governance_report", lambda *_args, **_kwargs: _completed_governance()
    )
    monkeypatch.setattr(archive, "artifact_output_paths", lambda *_args: ())
    monkeypatch.setattr(archive.openspec_cli, "openspec_base_command", lambda: None)

    report = archive._apply_archive(tmp_path, "work/feature", "old-head", "fixture-change")

    assert report["required_gaps"] == ["openspec_official_cli_missing"]


def test_archive_apply_commit_failure_compensates_native_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result = _archive_result(tmp_path)
    archive_path = result["json"]["archive"]["path"]
    monkeypatch.setattr(
        archive, "openspec_governance_report", lambda *_args, **_kwargs: _completed_governance()
    )
    monkeypatch.setattr(archive, "artifact_output_paths", lambda *_args: ())
    monkeypatch.setattr(archive.openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(archive.openspec_cli, "run_json", lambda *_args: result)
    monkeypatch.setattr(archive, "dirty_changed_paths", lambda _root: ("spec.md",))
    monkeypatch.setattr(archive, "normalize_projected_specs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(archive, "stage_git_worktree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        archive,
        "git_stdout",
        lambda _root, *args: (
            "openspec/changes/archive/2026-08-10-fixture-change/commitment.toml"
            if args[:3] == ("diff", "--cached", "--name-only")
            else ""
        ),
    )
    monkeypatch.setattr(
        archive,
        "lease_bound_archive_scope_report",
        lambda *_args, **_kwargs: {"verdict": "pass", "state": "archive_transition"},
    )
    monkeypatch.setattr(archive, "initiating_hook_transaction", lambda _root: nullcontext({}))
    monkeypatch.setattr(archive, "archive_transition_environment", lambda *_args, **_kwargs: {})
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

    report = archive._apply_archive(tmp_path, "work/feature", "old-head", "fixture-change")

    assert report["required_gaps"] == ["openspec_archive_commit_failed"]
    assert report["stderr"] == "hook rejected"
    assert compensated == [Path(archive_path).resolve().relative_to(tmp_path).as_posix()]


def test_archive_finish_collision_lease_fallback_and_postcondition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    collision = archive._ArchiveCollision("archive/path", "tree", "archive/preserved")
    finish = archive._ArchiveFinish(
        "work/feature",
        "old-head",
        "fixture-change",
        _archive_result(tmp_path),
        "openspec/changes/archive/2026-08-10-fixture-change",
        ("spec.md",),
        collision,
    )
    leases = iter(
        [
            {"expected_head": "old-head", "base_commitment_path": "active"},
            {
                "expected_head": "new-head",
                "base_commitment_path": finish.archive_path + "/commitment.toml",
            },
        ]
    )
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: "new-head")
    monkeypatch.setattr(archive, "leases_by_branch", lambda _root: {"work/feature": next(leases)})
    monkeypatch.setattr(
        archive, "relocated_commitment_fields_to", lambda *_args, **_kwargs: {"binding": "target"}
    )
    monkeypatch.setattr(
        archive,
        "work_lane_ref_transition_report",
        lambda **_kwargs: {"verdict": "block", "required_gaps": ["stale"]},
    )
    monkeypatch.setattr(
        archive, "_advance_archive_lease", lambda *_args, **_kwargs: {"verdict": "pass"}
    )
    monkeypatch.setattr(
        archive, "openspec_governance_report", lambda *_args, **_kwargs: {"required_gaps": []}
    )
    attestation = _Dumpable(id="archive-receipt")
    monkeypatch.setattr(archive, "_archive_attestation", lambda *_args, **_kwargs: attestation)
    monkeypatch.setattr(archive, "persist_attestation", lambda *_args: None)

    report = archive._finish_archive(tmp_path, finish)

    assert report["state"] == "archived"
    assert report["preserved_archive_path"] == "archive/preserved"
    assert report["attestation"] == {"id": "archive-receipt"}


def test_archive_lease_advance_reports_cas_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(archive, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(
        archive,
        "advance_lease_ref",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("lease_epoch_stale")),
    )

    report = archive._advance_archive_lease(
        tmp_path,
        branch="work/feature",
        previous_head="old-head",
        lease={
            "lease_id": "lease:1",
            "epoch": 1,
            "expires_at": "2026-08-11T00:00:00+00:00",
            "payload_sha256": "a" * 64,
        },
        target={"expected_head": "new-head"},
    )

    assert report == {"verdict": "block", "required_gaps": ["lease_epoch_stale"]}


@pytest.mark.parametrize(
    "payload",
    [
        {
            "exit_code": 0,
            "parse_error": "",
            "json": {"archive": {"change": "fixture-change", "path": "/outside"}},
        },
        {"exit_code": 0, "parse_error": "", "json": {"archive": {"change": "other", "path": ""}}},
    ],
)
def test_archive_native_receipt_rejects_outside_or_wrong_change(
    tmp_path: Path, payload: dict[str, object]
) -> None:
    gaps, archive_path = archive._official_result_gaps(tmp_path, "fixture-change", payload)

    assert gaps == ["openspec_archive_result_invalid"]
    assert archive_path == ""
