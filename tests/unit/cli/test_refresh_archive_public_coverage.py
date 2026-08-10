from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive_change as archive
import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as refresh

BRANCH = "work/feature"
HEAD = "old-head"
NEW_HEAD = "new-head"
CHANGE = "fixture-change"
ARCHIVE_PATH = (
    f"openspec/changes/archive/{datetime.now().astimezone().date().isoformat()}-fixture-change"
)


class _Dumpable:
    def __init__(self, **payload: object) -> None:
        self.payload = payload

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return dict(self.payload)


def _refresh_status(
    *,
    branch: str = BRANCH,
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
    archive_tree = "archive-tree" if collision else ""

    def git_stdout(_root: Path, *args: str) -> str:
        if args[:2] == ("branch", "--show-current"):
            return BRANCH
        if args[:2] == ("status", "--short"):
            return ""
        if args[:2] == ("rev-parse", f"{HEAD}:{ARCHIVE_PATH}"):
            return archive_tree
        if args[:2] == ("rev-parse", f"{HEAD}:{ARCHIVE_PATH}.preserved"):
            return ""
        if args[:3] == ("diff", "--cached", "--name-only"):
            return f"{ARCHIVE_PATH}/commitment.toml"
        return ""

    monkeypatch.setattr(archive, "git_stdout", git_stdout)
    monkeypatch.setattr(
        archive, "collision_preservation_path", lambda *_args: f"{ARCHIVE_PATH}.preserved"
    )
    monkeypatch.setattr(archive, "artifact_output_paths", lambda *_args: ())
    monkeypatch.setattr(archive.openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        archive.openspec_cli,
        "run_json",
        lambda *_args: result or _archive_result(root),
    )
    monkeypatch.setattr(archive, "dirty_changed_paths", lambda _root: ("spec.md",))
    monkeypatch.setattr(archive, "normalize_projected_specs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(archive, "stage_git_worktree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        archive,
        "lease_bound_archive_scope_report",
        lambda *_args, **_kwargs: {"verdict": "pass", "state": "archive_transition"},
    )
    monkeypatch.setattr(archive, "initiating_hook_transaction", lambda _root: nullcontext({}))
    monkeypatch.setattr(archive, "archive_transition_environment", lambda *_args, **_kwargs: {})


def test_archive_public_dry_run_and_local_state_guard(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    ready = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD)
    assert ready["state"] == "ready_to_archive"

    _stub_archive_public(
        monkeypatch,
        tmp_path,
        guard={"required_gaps": ["migration"], "next_action": "ethos state migrate"},
    )
    blocked = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)
    assert blocked["required_gaps"] == ["local_state_migration_required"]
    assert blocked["next_action"] == "ethos state migrate"


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

    assert report["required_gaps"] == ["native_warning", f"openspec_change_incomplete:{CHANGE}"]


def test_archive_public_missing_native_command_does_not_mutate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
    monkeypatch.setattr(archive.openspec_cli, "openspec_base_command", lambda: None)

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == ["openspec_official_cli_missing"]


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

    assert report["state"] == "repair_required"
    assert report["required_gaps"] == ["archive_failed"]
    assert compensated == [{"head": HEAD, "untracked_path": ""}]


def test_archive_public_commit_failure_compensates_native_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path)
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
    assert compensated == [ARCHIVE_PATH]


@pytest.mark.parametrize(
    "result",
    [
        {
            "exit_code": 0,
            "parse_error": "",
            "json": {"archive": {"change": CHANGE, "path": "/outside"}},
        },
        {"exit_code": 0, "parse_error": "", "json": {"archive": {"change": "other", "path": ""}}},
    ],
)
def test_archive_public_rejects_invalid_native_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    result: dict[str, object],
) -> None:
    _stub_archive_public(monkeypatch, tmp_path, result=result)
    compensated: list[str] = []
    monkeypatch.setattr(
        archive,
        "compensate_git_worktree",
        lambda _root, **kwargs: compensated.append(str(kwargs["untracked_path"])),
    )

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["required_gaps"] == ["openspec_archive_result_invalid"]
    assert compensated == [""]


def test_archive_public_collision_falls_back_to_exact_lease_cas_and_finishes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path, collision=True)
    monkeypatch.setattr(archive, "move_tracked_tree", lambda *_args: None)
    monkeypatch.setattr(
        archive, "commit_git_worktree", lambda *_args, **_kwargs: {"verdict": "pass"}
    )
    heads = iter((HEAD, NEW_HEAD))
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: next(heads))
    lease = {
        "expected_head": HEAD,
        "base_commitment_path": f"openspec/changes/{CHANGE}/commitment.toml",
        "lease_id": "lease:1",
        "epoch": 1,
        "expires_at": "2026-08-11T00:00:00+00:00",
        "payload_sha256": "d" * 64,
    }

    def leases_by_branch(_root: Path) -> dict[str, dict[str, object]]:
        return {BRANCH: dict(lease)}

    monkeypatch.setattr(archive, "leases_by_branch", leases_by_branch)
    monkeypatch.setattr(
        archive,
        "relocated_commitment_fields_to",
        lambda *_args, **_kwargs: {"expected_head": NEW_HEAD, "binding": "target"},
    )
    monkeypatch.setattr(
        archive,
        "work_lane_ref_transition_report",
        lambda **_kwargs: {"verdict": "block", "required_gaps": ["stale"]},
    )
    monkeypatch.setattr(
        archive,
        "advance_lease_ref",
        lambda *_args, **_kwargs: (
            lease.update(
                expected_head=NEW_HEAD,
                base_commitment_path=f"{ARCHIVE_PATH}/commitment.toml",
            )
            or dict(lease)
        ),
    )
    monkeypatch.setattr(archive, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(archive, "integer_value", int)
    monkeypatch.setattr(
        archive,
        "load_repository_commitment",
        lambda *_args, **_kwargs: SimpleNamespace(id="repository:self", digest=lambda: "r" * 64),
    )
    monkeypatch.setattr(
        archive,
        "load_commitment",
        lambda *_args, **_kwargs: SimpleNamespace(digest=lambda: "c" * 64),
    )
    monkeypatch.setattr(archive, "current_tree", lambda *_args: "tree")
    monkeypatch.setattr(
        archive,
        "issue_native_effect",
        lambda *_args, **_kwargs: _Dumpable(id="archive-receipt"),
    )
    monkeypatch.setattr(archive, "persist_attestation", lambda *_args: None)

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["state"] == "archived"
    assert report["preserved_archive_path"] == f"{ARCHIVE_PATH}.preserved"
    assert report["attestation"] == {"id": "archive-receipt"}


def test_archive_public_lease_cas_failure_is_repair_required(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_archive_public(monkeypatch, tmp_path, collision=True)
    monkeypatch.setattr(archive, "move_tracked_tree", lambda *_args: None)
    monkeypatch.setattr(
        archive, "commit_git_worktree", lambda *_args, **_kwargs: {"verdict": "pass"}
    )
    heads = iter((HEAD, NEW_HEAD))
    monkeypatch.setattr(archive, "current_tracked_head", lambda _root: next(heads))
    lease = {
        "expected_head": HEAD,
        "base_commitment_path": f"openspec/changes/{CHANGE}/commitment.toml",
        "lease_id": "lease:1",
        "epoch": 1,
        "expires_at": "2026-08-11T00:00:00+00:00",
        "payload_sha256": "d" * 64,
    }
    monkeypatch.setattr(archive, "leases_by_branch", lambda _root: {BRANCH: lease})
    monkeypatch.setattr(
        archive,
        "relocated_commitment_fields_to",
        lambda *_args, **_kwargs: {"expected_head": NEW_HEAD},
    )
    monkeypatch.setattr(
        archive, "work_lane_ref_transition_report", lambda **_kwargs: {"verdict": "block"}
    )
    monkeypatch.setattr(
        archive,
        "advance_lease_ref",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("lease_epoch_stale")),
    )
    monkeypatch.setattr(archive, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(archive, "integer_value", int)

    report = archive.archive_change(root=tmp_path, change=CHANGE, expect_head=HEAD, apply=True)

    assert report["state"] == "repair_required"
    assert "openspec_archive_lease_not_advanced" in report["required_gaps"]
