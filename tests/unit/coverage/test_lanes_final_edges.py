# ruff: noqa: ARG005, TC003, FBT002, C901
# Monkeypatch-heavy coverage edge tests intentionally preserve callable signatures
# matching patched runtime functions; unused parameters document those contracts.

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from ethos.adapters.mutation import lanes
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE


def cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, stderr)


POLICY = SimpleNamespace(candidate_branch="candidate/dev")


def status(
    role: str = ROLE_ACCEPTED_ROOT, dirty: bool = False, candidate: dict[str, object] | None = None
) -> dict[str, object]:
    return {
        "role": role,
        "dirty": dirty,
        "branch": "dev" if role == ROLE_ACCEPTED_ROOT else "work/x",
        "candidate": candidate
        or {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": "/tmp/candidate",
            "head": "c0",
        },
        "worktrees": [
            {"role": ROLE_ACCEPTED_ROOT, "path": "/repo", "branch": "dev", "head": "h0"},
            {"role": ROLE_WORK_LANE, "path": "/repo-w", "branch": "work/x", "head": "h1"},
        ],
    }


def test_lanes_remaining_branches(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(lanes, "_repo_root", lambda root: tmp_path)
    monkeypatch.setattr(lanes, "load_branch_role_policy", lambda root: POLICY)
    monkeypatch.setattr(
        lanes,
        "_git",
        lambda root, *args, check=True, **kwargs: cp(stdout="h1\n", stderr="fail", returncode=0),
    )

    monkeypatch.setattr(lanes, "workspace_status", lambda root: status())
    monkeypatch.setattr(
        lanes, "active_leases", lambda db: [{"subject": "work/x", "owner": "me", "payload": {}}]
    )
    assert (
        lanes.bind_work_lane_claim(root=tmp_path, claim_id="c", branch="work/x", apply=False)[
            "state"
        ]
        == "planned"
    )
    monkeypatch.setattr(lanes, "update_lease_payload", lambda *args, **kwargs: {})
    assert lanes.bind_work_lane_claim(root=tmp_path, claim_id="c", branch="work/x", apply=True)[
        "required_gaps"
    ] == ["work_lane_missing_lease:work/x"]

    monkeypatch.setattr(
        lanes,
        "workspace_status",
        lambda root: status(
            candidate={"exists": False, "worktree_exists": False, "worktree_path": "", "head": ""}
        ),
    )

    def branch_fails(root: Path, *args: str, check: bool = True, **kwargs: object):
        if args == ("rev-parse", "HEAD"):
            return cp(stdout="h1\n")
        if args[:1] == ("branch",):
            return cp(returncode=1, stderr="branch fail")
        return cp(returncode=0)

    monkeypatch.setattr(lanes, "_git", branch_fails)
    assert lanes.bootstrap_candidate(root=tmp_path, path=tmp_path / "candidate", apply=True)[
        "required_gaps"
    ] == ["candidate_bootstrap_failed"]

    monkeypatch.setattr(
        lanes,
        "workspace_status",
        lambda root: status(
            candidate={
                "exists": True,
                "worktree_exists": True,
                "worktree_path": "/tmp/candidate",
                "head": "h1",
            }
        ),
    )
    monkeypatch.setattr(lanes, "changed_paths", lambda path: [])
    monkeypatch.setattr(
        lanes, "_git", lambda root, *args, check=True, **kwargs: cp(stdout="h1\n", returncode=0)
    )
    assert lanes.refresh_candidate_from_accepted(root=tmp_path)["state"] == "base_current"
    monkeypatch.setattr(lanes, "workspace_status", lambda root: status(dirty=True))
    assert lanes.refresh_candidate_from_accepted(root=tmp_path)["required_gaps"] == [
        "accepted_root_dirty"
    ]
    monkeypatch.setattr(lanes, "workspace_status", lambda root: status(role=ROLE_WORK_LANE))
    assert lanes.refresh_candidate_from_accepted(root=tmp_path)["required_gaps"] == [
        "accepted_root_required"
    ]

    monkeypatch.setattr(
        lanes, "workspace_status", lambda root: status(role=ROLE_WORK_LANE, dirty=True)
    )
    assert lanes.refresh_work_lane_base(root=tmp_path)["required_gaps"] == ["work_lane_dirty"]
    monkeypatch.setattr(
        lanes,
        "workspace_status",
        lambda root: status(
            role=ROLE_WORK_LANE,
            candidate={
                "exists": True,
                "worktree_exists": True,
                "worktree_path": "/tmp/candidate",
                "head": "c1",
            },
        ),
    )
    monkeypatch.setattr(lanes, "_is_ancestor", lambda root, ancestor, descendant: False)
    calls = []

    def rebase_fails(root: Path, *args: str, check: bool = True, **kwargs: object):
        calls.append(args)
        if args == ("rev-parse", "HEAD"):
            return cp(stdout="h1\n")
        if args[:1] == ("rebase",) and args != ("rebase", "--abort"):
            return cp(returncode=1, stderr="rebase fail")
        return cp(returncode=0)

    monkeypatch.setattr(lanes, "_git", rebase_fails)
    failed = lanes.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head="h1"
    )
    assert failed["required_gaps"] == ["refresh_base_failed"]
    assert ("rebase", "--abort") in calls

    def rebase_ok(root: Path, *args: str, check: bool = True, **kwargs: object):
        if args == ("rev-parse", "HEAD"):
            return cp(stdout="h2\n")
        return cp(returncode=0)

    monkeypatch.setattr(lanes, "_git", rebase_ok)
    assert (
        lanes.refresh_work_lane_base(root=tmp_path, apply=True, authorized=True, expect_head="h2")[
            "state"
        ]
        == "base_refreshed"
    )

    worktrees = [
        {"role": ROLE_WORK_LANE, "path": str(tmp_path / "w"), "branch": "work/x", "head": "h1"}
    ]
    (tmp_path / "w").mkdir(exist_ok=True)
    monkeypatch.setattr(
        lanes, "workspace_status", lambda root: {**status(), "worktrees": worktrees}
    )
    monkeypatch.setattr(lanes, "_is_ancestor", lambda root, ancestor, descendant: True)
    monkeypatch.setattr(lanes, "changed_paths", lambda path: [])

    def remove_fails(root: Path, *args: str, check: bool = True, **kwargs: object):
        if args[:2] == ("worktree", "remove"):
            return cp(returncode=1, stderr="remove fail")
        return cp(returncode=0)

    monkeypatch.setattr(lanes, "_git", remove_fails)
    assert lanes.retire_landed_work_lanes(
        root=tmp_path,
        branch="work/x",
        expect_head="h1",
        apply=True,
    )["required_gaps"] == ["worktree_remove_failed"]

    def delete_fails(root: Path, *args: str, check: bool = True, **kwargs: object):
        if args[:2] == ("update-ref", "-d"):
            return cp(returncode=1, stderr="delete fail")
        return cp(returncode=0)

    monkeypatch.setattr(lanes, "_git", delete_fails)
    assert lanes.retire_landed_work_lanes(
        root=tmp_path,
        branch="work/x",
        expect_head="h1",
        apply=True,
    )["required_gaps"] == ["branch_delete_failed"]
