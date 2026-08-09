from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.mutation.lane_lifecycle.identity_repair as repair
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_OLD = "a" * 40
_NEW = "b" * 40
_BRANCH = "work/test"
_HOLDER = "agent:test:case:owner"


def _policy() -> SimpleNamespace:
    return SimpleNamespace(
        candidate_branch="candidate/dev",
        accepted_branch="dev",
        release_branch="main",
        release_mirror=RELEASE_MIRROR_ACCEPTED_FF,
    )


def _proof() -> SimpleNamespace:
    return SimpleNamespace(model_dump=lambda **_kwargs: {"kind": "proof"})


def _admit_public_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    refs: dict[str, str],
    *,
    sync_branch: str,
) -> tuple[dict[str, object], list[str]]:
    status = {
        "role": ROLE_WORK_LANE,
        "dirty": False,
        "branch": _BRANCH,
        "worktrees": [],
    }
    lease = {
        "lease_state": "valid",
        "holder_ref": _HOLDER,
        "expected_head": _NEW,
        "expected_tree": "tree",
    }
    synchronized: list[str] = []
    monkeypatch.setenv("ETHOS_ACTOR", _HOLDER)
    monkeypatch.setattr(repair, "workspace_status", lambda *_args, **_kwargs: status)
    monkeypatch.setattr(repair, "current_tracked_head", lambda _root: _NEW)
    monkeypatch.setattr(repair, "leases_by_branch", lambda _root: {_BRANCH: lease})
    monkeypatch.setattr(repair, "proof_attestation", lambda *_args: _proof())
    monkeypatch.setattr(repair, "proof_gaps", lambda *_args: [])
    monkeypatch.setattr(
        repair,
        "verify_commit_trust",
        lambda *_args: {"verdict": "pass", "required_gaps": []},
    )
    monkeypatch.setattr(repair, "equivalent_commit_identity", lambda *_args: True)
    monkeypatch.setattr(repair, "current_tree", lambda *_args: "tree")
    monkeypatch.setattr(repair, "load_branch_role_policy", lambda _root: _policy())
    monkeypatch.setattr(repair, "ref_head", lambda _root, branch: refs[branch])
    monkeypatch.setattr(repair, "ref_worktree_paths", lambda *_args: ())
    monkeypatch.setattr(repair, "worktree_sync_gap", lambda *_args: "")
    monkeypatch.setattr(repair, "load_lease_bound_commitment", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(repair, "compile_observed_git_effect", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        repair,
        "execute_git_effect",
        lambda *_args, **_kwargs: SimpleNamespace(model_dump=lambda **_kwargs: {}),
    )

    def sync(_root: Path, _paths: object, branch: str, *_args: object) -> dict[str, object]:
        synchronized.append(branch)
        return {"worktree_sync": "failed" if branch == sync_branch else "current"}

    monkeypatch.setattr(repair, "sync_ref_worktrees", sync)
    report = repair.repair_commit_identity(
        root=tmp_path,
        old_commit=_OLD,
        new_commit=_NEW,
        expect_head=_NEW,
        apply=True,
        authorized=True,
    )
    return report, synchronized


def test_identity_repair_public_preflight_reports_ref_and_worktree_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    status = {
        "role": ROLE_WORK_LANE,
        "dirty": False,
        "branch": _BRANCH,
        "worktrees": [{"branch": "candidate/dev", "path": tmp_path.as_posix()}],
    }
    monkeypatch.setenv("ETHOS_ACTOR", _HOLDER)
    monkeypatch.setattr(repair, "workspace_status", lambda *_args, **_kwargs: status)
    monkeypatch.setattr(repair, "current_tracked_head", lambda _root: _NEW)
    monkeypatch.setattr(
        repair,
        "leases_by_branch",
        lambda _root: {
            _BRANCH: {
                "lease_state": "valid",
                "holder_ref": _HOLDER,
                "expected_head": _NEW,
                "expected_tree": "tree",
            }
        },
    )
    monkeypatch.setattr(repair, "proof_attestation", lambda *_args: _proof())
    monkeypatch.setattr(repair, "proof_gaps", lambda *_args: [])
    monkeypatch.setattr(repair, "verify_commit_trust", lambda *_args: {"required_gaps": []})
    monkeypatch.setattr(repair, "equivalent_commit_identity", lambda *_args: True)
    monkeypatch.setattr(repair, "current_tree", lambda *_args: "tree")
    monkeypatch.setattr(repair, "load_branch_role_policy", lambda _root: _policy())
    monkeypatch.setattr(
        repair,
        "ref_head",
        lambda _root, branch: {"candidate/dev": _OLD, "dev": "foreign", "main": _OLD}[branch],
    )
    monkeypatch.setattr(repair, "ref_worktree_paths", lambda *_args: (tmp_path,))
    monkeypatch.setattr(repair, "worktree_sync_gap", lambda *_args: "worktree_head_stale")

    report = repair.repair_commit_identity(
        root=tmp_path,
        old_commit=_OLD,
        new_commit=_NEW,
        expect_head=_NEW,
        apply=False,
        authorized=False,
    )

    assert "identity_repair_ref_stale:dev:foreign" in report["required_gaps"]
    assert any("worktree_head_stale" in gap for gap in report["required_gaps"])


def test_identity_repair_public_apply_fails_closed_when_candidate_sync_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, synchronized = _admit_public_repair(
        tmp_path,
        monkeypatch,
        {"candidate/dev": _NEW, "dev": _NEW, "main": _NEW},
        sync_branch="candidate/dev",
    )

    assert report["required_gaps"] == ["identity_repair_cas_rejected"]
    assert report["stderr"] == "identity_repair_candidate_worktree_sync_failed"
    assert synchronized == ["candidate/dev"]


def test_identity_repair_public_apply_includes_release_sync_and_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, synchronized = _admit_public_repair(
        tmp_path,
        monkeypatch,
        {"candidate/dev": _NEW, "dev": _NEW, "main": _OLD},
        sync_branch="main",
    )

    assert report["required_gaps"] == ["identity_repair_cas_rejected"]
    assert report["stderr"] == "identity_repair_accepted_worktree_sync_failed"
    assert synchronized == ["candidate/dev", "main"]


def test_identity_repair_public_recognition_without_updates_still_requires_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, synchronized = _admit_public_repair(
        tmp_path,
        monkeypatch,
        {"candidate/dev": _NEW, "dev": _NEW, "main": _NEW},
        sync_branch="dev",
    )

    assert report["required_gaps"] == ["identity_repair_cas_rejected"]
    assert report["stderr"] == "identity_repair_accepted_worktree_sync_failed"
    assert synchronized == ["candidate/dev", "dev"]
