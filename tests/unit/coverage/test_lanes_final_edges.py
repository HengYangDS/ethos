# ruff: noqa: ARG005, TC003
# Monkeypatch-heavy coverage edge tests intentionally preserve callable signatures
# matching patched runtime functions; unused parameters document those contracts.

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import ethos.adapters.mutation.lane_lifecycle.projection_rebase.core as lane_projection_rebase
from ethos.adapters.mutation import lanes
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE


def cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, stderr)


def fake_git(
    responses: dict[tuple[str, ...], subprocess.CompletedProcess[str]],
    *,
    calls: list[tuple[str, ...]] | None = None,
    default: subprocess.CompletedProcess[str] | None = None,
):
    def run(*_run_args: object, **_run_kwargs: object) -> subprocess.CompletedProcess[str]:
        args = tuple(str(arg) for arg in _run_args[1:])
        if calls is not None:
            calls.append(args)
        for prefix, response in responses.items():
            if args[: len(prefix)] == prefix:
                return response
        return default or cp(returncode=0)

    return run


POLICY = SimpleNamespace(candidate_branch="candidate/dev")


def status(
    role: str = ROLE_ACCEPTED_ROOT,
    *,
    dirty: bool = False,
    candidate: dict[str, object] | None = None,
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
    monkeypatch.setattr(lanes, "repo_root", lambda root: tmp_path)
    monkeypatch.setattr(lanes, "load_branch_role_policy", lambda root: POLICY)
    monkeypatch.setattr(
        lanes,
        "run_git",
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

    monkeypatch.setattr(
        lanes,
        "run_git",
        fake_git(
            {
                ("rev-parse", "HEAD"): cp(stdout="h1\n"),
                ("branch",): cp(returncode=1, stderr="branch fail"),
            }
        ),
    )
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
        lanes, "run_git", lambda root, *args, check=True, **kwargs: cp(stdout="h1\n", returncode=0)
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
    monkeypatch.setattr(lanes, "is_ancestor", lambda root, ancestor, descendant: False)
    calls = []

    monkeypatch.setattr(
        lanes,
        "run_git",
        fake_git(
            {
                ("rev-parse", "HEAD"): cp(stdout="h1\n"),
                ("rebase", "candidate/dev"): cp(returncode=1, stderr="rebase fail"),
            },
            calls=calls,
        ),
    )
    failed = lanes.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head="h1"
    )
    assert failed["required_gaps"] == ["refresh_base_failed"]
    assert ("rebase", "--abort") in calls

    monkeypatch.setattr(
        lanes,
        "run_git",
        fake_git({("rev-parse", "HEAD"): cp(stdout="h2\n")}),
    )
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
    monkeypatch.setattr(lanes, "is_ancestor", lambda root, ancestor, descendant: True)
    monkeypatch.setattr(lanes, "changed_paths", lambda path: [])

    monkeypatch.setattr(
        lanes,
        "run_git",
        fake_git({("worktree", "remove"): cp(returncode=1, stderr="remove fail")}),
    )
    monkeypatch.setenv("ETHOS_ACTOR", "me")
    assert lanes.retire_landed_work_lanes(
        root=tmp_path,
        branch="work/x",
        expect_head="h1",
        apply=True,
    )["required_gaps"] == ["worktree_remove_failed"]

    monkeypatch.setattr(
        lanes,
        "run_git",
        fake_git({("update-ref", "-d"): cp(returncode=1, stderr="delete fail")}),
    )
    assert lanes.retire_landed_work_lanes(
        root=tmp_path,
        branch="work/x",
        expect_head="h1",
        apply=True,
    )["required_gaps"] == ["branch_delete_failed"]


def test_refresh_base_projection_resolution_edge_failures(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(
        lane_projection_rebase,
        "run_git",
        fake_git({("diff",): cp(returncode=1)}, calls=calls),
    )
    assert lane_projection_rebase.resolve_projection_only_rebase_conflict(tmp_path)["ok"] is False

    monkeypatch.setattr(
        lane_projection_rebase,
        "run_git",
        fake_git(
            {
                ("diff",): cp(stdout="evidence/parity/generic-shadow.json\n"),
                ("checkout",): cp(returncode=1),
            }
        ),
    )
    assert lane_projection_rebase.resolve_projection_only_rebase_conflict(tmp_path) == {
        "ok": False,
        "paths": ["evidence/parity/generic-shadow.json"],
        "gaps": [],
        "next_actions": [],
    }

    monkeypatch.setattr(
        lane_projection_rebase,
        "run_git",
        fake_git(
            {
                ("diff",): cp(stdout="evidence/parity/generic-shadow.json\n"),
                ("add",): cp(returncode=1),
            }
        ),
    )
    assert lane_projection_rebase.resolve_projection_only_rebase_conflict(tmp_path) == {
        "ok": False,
        "paths": ["evidence/parity/generic-shadow.json"],
        "gaps": [],
        "next_actions": [],
    }

    monkeypatch.setattr(
        lane_projection_rebase,
        "run_git",
        fake_git({("diff",): cp(stdout="evidence/parity/generic-shadow.json\nREADME.md\n")}),
    )
    assert lane_projection_rebase.resolve_projection_only_rebase_conflict(tmp_path)["ok"] is False


def test_projection_rebase_skips_empty_projection_patch(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []
    diff_calls = 0

    def run_git(_root: Path, *args: str, check: bool = True):
        nonlocal diff_calls
        del check
        calls.append(tuple(args))
        if args[:3] == ("diff", "--name-only", "--diff-filter=U"):
            diff_calls += 1
            if diff_calls == 1:
                return cp(stdout="evidence/parity/generic-shadow.json\n")
            return cp(stdout="")
        if args[:1] in {("checkout",), ("add",)}:
            return cp(returncode=0)
        if args == ("-c", "core.editor=true", "rebase", "--continue"):
            return cp(returncode=1, stderr="No changes -- Patch already applied.")
        if args == ("rebase", "--skip"):
            return cp(returncode=0)
        return cp(returncode=1, stderr="unexpected git call")

    monkeypatch.setattr(lane_projection_rebase, "run_git", run_git)

    resolved = lane_projection_rebase.resolve_projection_rebase(
        tmp_path,
        cp(returncode=1, stderr="projection conflict"),
    )

    assert resolved["ok"] is True
    assert resolved["paths"] == ["evidence/parity/generic-shadow.json"]
    assert ("rebase", "--skip") in calls


def test_refresh_work_lane_base_aborts_when_projection_continue_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(lanes, "load_branch_role_policy", lambda root: POLICY)
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
    monkeypatch.setattr(lanes, "changed_paths", lambda path: [])
    monkeypatch.setattr(lanes, "is_ancestor", lambda root, ancestor, descendant: False)
    calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(
        lanes,
        "run_git",
        fake_git(
            {
                ("rev-parse", "HEAD"): cp(stdout="h1\n"),
                ("rebase", "candidate/dev"): cp(returncode=1, stderr="projection conflict"),
                ("diff",): cp(stdout="evidence/parity/generic-shadow.json\n"),
                ("checkout",): cp(returncode=0),
                ("add",): cp(returncode=0),
                ("-c", "core.editor=true", "rebase", "--continue"): cp(
                    returncode=1, stderr="continue fail"
                ),
                ("rebase", "--abort"): cp(returncode=0),
            },
            calls=calls,
        ),
    )
    failed = lanes.refresh_work_lane_base(
        root=tmp_path,
        apply=True,
        authorized=True,
        expect_head="h1",
    )

    assert failed["required_gaps"] == ["refresh_base_failed"]
    assert ("rebase", "--abort") in calls
