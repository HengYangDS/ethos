from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.identity_repair as repair
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    from pathlib import Path


def _policy() -> SimpleNamespace:
    return SimpleNamespace(
        candidate_branch="candidate/dev",
        accepted_branch="dev",
        release_branch="main",
        release_mirror=RELEASE_MIRROR_ACCEPTED_FF,
    )


def test_identity_repair_public_preflight_reports_ref_and_worktree_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old, new = "a" * 40, "b" * 40
    status = {
        "role": ROLE_WORK_LANE,
        "dirty": False,
        "branch": "work/test",
        "worktrees": [{"branch": "candidate/dev", "path": tmp_path.as_posix()}],
    }
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:owner")
    monkeypatch.setattr(repair, "workspace_status", lambda *_args, **_kwargs: status)
    monkeypatch.setattr(repair, "current_tracked_head", lambda _root: new)
    monkeypatch.setattr(
        repair,
        "leases_by_branch",
        lambda _root: {
            "work/test": {
                "lease_state": "valid",
                "holder_ref": "agent:test:case:owner",
                "expected_head": new,
                "expected_tree": "tree",
            }
        },
    )
    monkeypatch.setattr(repair, "proof_attestation", lambda *_args: SimpleNamespace())
    monkeypatch.setattr(repair, "proof_gaps", lambda *_args: [])
    monkeypatch.setattr(repair, "verify_commit_trust", lambda *_args: {"required_gaps": []})
    monkeypatch.setattr(repair, "equivalent_commit_identity", lambda *_args: True)
    monkeypatch.setattr(repair, "current_tree", lambda *_args: "tree")
    monkeypatch.setattr(repair, "load_branch_role_policy", lambda _root: _policy())
    monkeypatch.setattr(
        repair,
        "ref_head",
        lambda _root, branch: {"candidate/dev": old, "dev": "foreign", "main": old}[branch],
    )
    monkeypatch.setattr(repair, "ref_worktree_paths", lambda *_args: (tmp_path,))
    monkeypatch.setattr(repair, "worktree_sync_gap", lambda *_args: "worktree_head_stale")

    report = repair.repair_commit_identity(
        root=tmp_path,
        old_commit=old,
        new_commit=new,
        expect_head=new,
        apply=False,
        authorized=False,
    )

    assert "identity_repair_ref_stale:dev:foreign" in report["required_gaps"]
    assert any("worktree_head_stale" in gap for gap in report["required_gaps"])


def test_identity_repair_candidate_recognition_fails_closed_on_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    replacement = SimpleNamespace(
        root=tmp_path,
        old="a" * 40,
        new="b" * 40,
        refs={"candidate/dev": "b" * 40},
        status={"worktrees": []},
    )
    monkeypatch.setattr(repair, "load_branch_role_policy", lambda _root: _policy())
    monkeypatch.setattr(
        repair,
        "_sync_branch_worktrees",
        lambda *_args: {"worktree_sync": "failed"},
    )

    with pytest.raises(ValueError, match="identity_repair_candidate_worktree_sync_failed"):
        repair._apply_candidate_replacement(replacement)  # noqa: SLF001


def test_identity_repair_accepted_recognition_includes_release_and_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old, new = "a" * 40, "b" * 40
    replacement = SimpleNamespace(
        root=tmp_path,
        old=old,
        new=new,
        refs={"candidate/dev": new, "dev": new, "main": old},
        status={"worktrees": []},
        authority=SimpleNamespace(),
        evidence={},
        lease={"holder_ref": "agent:test:case:owner"},
        branch="work/test",
    )
    monkeypatch.setattr(repair, "load_branch_role_policy", lambda _root: _policy())
    monkeypatch.setattr(repair, "_plan", lambda *_args, **_kwargs: SimpleNamespace())
    monkeypatch.setattr(
        repair,
        "execute_git_effect",
        lambda *_args, **_kwargs: SimpleNamespace(model_dump=lambda **_kwargs: {}),
    )
    monkeypatch.setattr(
        repair,
        "_sync_branch_worktrees",
        lambda _root, _status, branch, *_args: {
            "worktree_sync": "failed" if branch == "main" else "current"
        },
    )

    with pytest.raises(ValueError, match="identity_repair_accepted_worktree_sync_failed"):
        repair._apply_accepted_replacement(replacement)  # noqa: SLF001


def test_identity_repair_accepted_recognition_without_updates_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old, new = "a" * 40, "b" * 40
    replacement = SimpleNamespace(
        root=tmp_path,
        old=old,
        new=new,
        refs={"candidate/dev": new, "dev": new, "main": new},
        status={"worktrees": []},
    )
    monkeypatch.setattr(repair, "load_branch_role_policy", lambda _root: _policy())
    monkeypatch.setattr(
        repair,
        "_sync_branch_worktrees",
        lambda _root, _status, branch, *_args: {
            "worktree_sync": "failed" if branch == "dev" else "current"
        },
    )

    with pytest.raises(ValueError, match="identity_repair_accepted_worktree_sync_failed"):
        repair._apply_accepted_replacement(replacement)  # noqa: SLF001
