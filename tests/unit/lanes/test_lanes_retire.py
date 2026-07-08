from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.repo.status.core as repo_status
from ethos.adapters.mutation import lanes_retire
from ethos.adapters.mutation.lane_lifecycle import core as lane_lifecycle_core
from ethos.adapters.mutation.lanes import retire_landed_work_lanes
from ethos.adapters.mutation.lanes import retire_unbound_work_lane_ref
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo import coordination as repo_coordination
from ethos.adapters.repo.dirty.core import committed_change_paths
from ethos.adapters.repo.dirty.core import dirty_provenance
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store import state

if TYPE_CHECKING:
    from pathlib import Path


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def add_candidate_worktree(repo: Path, path: Path) -> Path:
    git(repo, "worktree", "add", "-b", "candidate/dev", path.as_posix(), "dev")
    return path


def write_role_policy(
    repo: Path,
    *,
    candidate_branch: str = "stage/dev",
    work_branch_prefix: str = "lane/",
    submit_branch_prefix: str = "review/",
) -> None:
    (repo / ".ethos" / "workspace.toml").write_text(
        "\n".join(
            [
                "[branch_roles]",
                'release_branch = "main"',
                'accepted_branch = "dev"',
                f'candidate_branch = "{candidate_branch}"',
                f'work_branch_prefix = "{work_branch_prefix}"',
                f'submit_branch_prefix = "{submit_branch_prefix}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/workspace.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "configure branch roles",
    )


def assert_no_ui_projection(value: object) -> None:
    if isinstance(value, dict):
        forbidden = {"open_action", "open_label", "action", "label"}
        assert not (forbidden & set(value))
        for child in value.values():
            assert_no_ui_projection(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_ui_projection(child)


def test_retire_landed_work_lane_plans_only_merged_lanes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    active = tmp_path / "repo-work-active"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    git(repo, "worktree", "add", "-b", "work/active", active.as_posix(), "dev")
    (active / "README.md").write_text("# active\n", encoding="utf-8")
    git(active, "add", "README.md")
    git(
        active,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "active work",
    )

    report = retire_landed_work_lanes(root=repo)

    assert report["ok"] is True
    assert report["state"] == "planned"
    assert report["required_gaps"] == []
    lanes = {lane["branch"]: lane for lane in report["lanes"]}
    assert lanes["work/landed"]["retire_ready"] is True
    assert lanes["work/landed"]["required_gaps"] == []
    assert lanes["work/active"]["retire_ready"] is False
    assert lanes["work/active"]["required_gaps"] == ["work_lane_not_merged"]


def test_retire_landed_work_lane_block_explains_required_actor(monkeypatch, tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/landed",
        owner="agent-a",
        ttl_seconds=3600,
    )

    landed_head = git(landed, "rev-parse", "HEAD")
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    blocked = retire_landed_work_lanes(
        root=repo, branch="work/landed", expect_head=landed_head, apply=True
    )

    assert blocked["ok"] is False
    assert blocked["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert blocked["mutation"] == {
        "actor": "",
        "actor_bound": "false",
        "actor_source": "ETHOS_ACTOR",
        "expect_head": landed_head,
        "ref": "refs/heads/work/landed",
        "required_actor": "agent-a",
    }
    assert blocked["next_action"] == "set ETHOS_ACTOR to the lane lease owner or obtain handoff"


def test_retire_landed_work_lane_requires_matching_owner_for_leased_lane(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    db = repo / ".ethos" / "state" / "state.sqlite"
    state.acquire_lease(db, subject="work/landed", owner="agent-a", ttl_seconds=3600)

    monkeypatch.setenv("ETHOS_ACTOR", "agent-b")
    blocked = retire_landed_work_lanes(root=repo, branch="work/landed")

    assert blocked["ok"] is False
    assert blocked["state"] == "blocked"
    assert blocked["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert landed.exists()

    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")
    allowed = retire_landed_work_lanes(root=repo, branch="work/landed")

    assert allowed["ok"] is True
    assert allowed["state"] == "planned"
    assert allowed["required_gaps"] == []


def test_retire_landed_work_lane_apply_requires_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")

    report = retire_landed_work_lanes(root=repo, apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == ["retire_branch_required"]
    assert landed.exists()


def test_retire_landed_work_lane_apply_requires_expected_head(monkeypatch, tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")

    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/landed",
        owner="agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")
    report = retire_landed_work_lanes(root=repo, branch="work/landed", apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == ["expect_head_required"]
    assert landed.exists()
    assert git(repo, "branch", "--list", "work/landed") != ""


def test_retire_landed_work_lane_apply_rejects_mismatched_expected_head(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")

    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/landed",
        owner="agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")
    report = retire_landed_work_lanes(
        root=repo,
        branch="work/landed",
        expect_head="not-the-lane-head",
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["expect_head_mismatch"]
    assert landed.exists()
    assert git(repo, "branch", "--list", "work/landed") != ""


def test_retire_landed_work_lane_apply_removes_selected_clean_merged_lane(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    landed_head = git(landed, "rev-parse", "HEAD")

    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/landed",
        owner="agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")
    report = retire_landed_work_lanes(
        root=repo,
        branch="work/landed",
        expect_head=landed_head,
        apply=True,
    )

    assert report["ok"] is True
    assert report["state"] == "retired"
    assert report["mutation"]["expect_head"] == landed_head
    assert not landed.exists()
    assert git(repo, "branch", "--list", "work/landed") == ""


def test_remove_linked_lane_restores_ref_when_worktree_remove_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    lane = {
        "branch": "work/stuck",
        "path": (tmp_path / "repo-work-stuck").as_posix(),
    }
    calls: list[tuple[str, ...]] = []

    def fake_run_git(
        _repo: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        calls.append(args)
        if args[:3] == ("update-ref", "-d", "refs/heads/work/stuck"):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:3] == ("worktree", "remove", "--force"):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="locked")
        if args[:2] == ("update-ref", "refs/heads/work/stuck"):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(lanes_retire, "run_git", fake_run_git)

    report = lanes_retire.remove_linked_lane(repo, lane, expect_head="a" * 40)

    assert report == {
        "ok": False,
        "state": "blocked",
        "required_gaps": ["worktree_remove_failed"],
        "stderr": "locked",
        "rollback_stderr": "",
    }
    assert calls == [
        ("update-ref", "-d", "refs/heads/work/stuck", "a" * 40),
        ("worktree", "remove", "--force", lane["path"]),
        ("update-ref", "refs/heads/work/stuck", "a" * 40, "0" * 40),
    ]


def test_remove_linked_lane_reports_restore_failure_when_partial_cleanup_persists(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    lane = {
        "branch": "work/stuck",
        "path": (tmp_path / "repo-work-stuck").as_posix(),
    }

    def fake_run_git(
        _repo: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        if args[:3] == ("update-ref", "-d", "refs/heads/work/stuck"):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:3] == ("worktree", "remove", "--force"):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="locked")
        if args[:2] == ("update-ref", "refs/heads/work/stuck"):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="restore failed")
        raise AssertionError(args)

    monkeypatch.setattr(lanes_retire, "run_git", fake_run_git)

    report = lanes_retire.remove_linked_lane(repo, lane, expect_head="a" * 40)

    assert report == {
        "ok": False,
        "state": "blocked",
        "required_gaps": ["worktree_remove_failed", "branch_restore_failed"],
        "stderr": "locked",
        "rollback_stderr": "restore failed",
    }


def test_candidate_status_reports_commits_behind_accepted(tmp_path: Path) -> None:
    """Candidate-train integrity: status surfaces how far candidate/dev is behind the
    accepted root (dev), so promotions that bypassed the lane->candidate->accepted
    train (e.g. a raw merge straight to accepted) are visible, not silent drift."""
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "candidate/dev")
    for name in ("b.txt", "c.txt"):
        (repo / name).write_text("x\n", encoding="utf-8")
        git(repo, "add", name)
        git(
            repo,
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            f"add {name}",
        )

    status = workspace_status(repo)

    assert status["candidate"]["behind_accepted"] == 2


def test_workspace_status_reports_dirty_provenance(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    (worktree / "README.md").write_text("# edited\n", encoding="utf-8")
    (worktree / "new.txt").write_text("new\n", encoding="utf-8")

    status = workspace_status(worktree)

    provenance = status["dirty_provenance"]
    assert provenance["dirty"] is True
    assert provenance["summary"]["tracked"] == 1
    assert provenance["summary"]["untracked"] == 1
    entries = {entry["path"]: entry for entry in provenance["entries"]}
    assert entries["README.md"]["kind"] == "tracked"
    assert entries["new.txt"]["kind"] == "untracked"


def test_workspace_status_recommends_legitimate_lane_migration_on_overlap(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    first = tmp_path / "repo-work-first"
    second = tmp_path / "repo-work-second"
    start_work_lane(root=repo, name="first", path=first, owner="agent:first", apply=True)
    start_work_lane(root=repo, name="second", path=second, owner="agent:second", apply=True)

    (first / "README.md").write_text("# first\n", encoding="utf-8")
    git(first, "add", "README.md")
    git(
        first,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "first",
    )
    (second / "README.md").write_text("# second\n", encoding="utf-8")
    git(second, "add", "README.md")
    git(
        second,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "second",
    )

    status = workspace_status(second)

    recommendations = status["coordination"]["migration_recommendations"]
    assert recommendations == [
        {
            "kind": "overlap_resolution",
            "overlapping_branch": "work/first",
            "owner": "agent:first",
            "recommendation": "preserve_legitimate_lane_and_replay_or_move_verified_head",
            "next_actions": [
                "do not land a temporary overlapping lane directly",
                "refresh or move the leased lane work/first after review",
                "delete the temporary lane after the legitimate lane carries the verified head",
            ],
        }
    ]


def test_committed_change_paths_returns_empty_when_diff_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    paths = committed_change_paths(repo, "missing-candidate-ref")

    assert paths == ()


def test_dirty_provenance_reports_unavailable_git_status(monkeypatch, tmp_path: Path) -> None:
    def fail_git(_root: Path, *args: str) -> str:
        assert args == ("status", "--porcelain", "--untracked-files=all")
        raise subprocess.CalledProcessError(128, ["git", *args], stderr="fatal: not a git repo")

    monkeypatch.setattr(repo_status, "_run_git", fail_git)

    report = dirty_provenance(tmp_path)

    assert report["dirty"] is True
    assert report["state"] == "unavailable"
    assert report["entries"] == []
    assert report["summary"] == {
        "tracked": 0,
        "untracked": 0,
        "deleted": 0,
        "conflicted": 0,
        "unavailable": 1,
    }
    assert "fatal: not a git repo" in str(report["error"])


def test_coordination_state_reports_unknown_for_unbounded_scope() -> None:
    assert (
        repo_coordination.coordination_state(
            current_role="work_lane",
            current_path_scope=("packages/ethos/src",),
            current_scope_state="bounded",
            foreign_path_scope=(),
            foreign_scope_state="unknown",
        )
        == "unknown"
    )

    required, advisory = repo_coordination.coordination_gaps(
        [
            {
                "branch": "work/unknown",
                "lease_state": "leased",
                "coordination_state": "unknown",
            }
        ],
        current_role="work_lane",
        current_scope_state="unknown",
    )

    assert required == [
        "coordination_gap:current_scope_unknown",
        "coordination_gap:foreign_scope_unknown:work/unknown",
    ]
    assert advisory == ["foreign_work_lane_present"]


def test_retire_unbound_work_lane_ref_dry_run_reports_head_bound_plan(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "work/stale-ref", "dev")
    head = git(repo, "rev-parse", "work/stale-ref")

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch="work/stale-ref",
        expect_head=head,
        reason="superseded by accepted root",
    )

    assert report["ok"] is True
    assert report["state"] == "ready_to_retire_unbound"
    assert report["head"] == head
    assert report["mutation"] == {
        "apply": False,
        "authorized": False,
        "expect_head": head,
        "ref": "refs/heads/work/stale-ref",
    }
    assert git(repo, "rev-parse", "--verify", "work/stale-ref") == head


def test_retire_unbound_work_lane_ref_apply_deletes_only_matching_ref(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "work/stale-ref", "dev")
    head = git(repo, "rev-parse", "work/stale-ref")

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch="work/stale-ref",
        expect_head=head,
        reason="superseded by accepted root",
        apply=True,
        authorized=True,
    )

    assert report["ok"] is True
    assert report["state"] == "retired_unbound"
    assert report["retired_ref"] == "refs/heads/work/stale-ref"
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", "refs/heads/work/stale-ref"],
            cwd=repo,
            check=False,
        ).returncode
        == 1
    )


def test_retire_unbound_work_lane_ref_blocks_head_mismatch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "work/stale-ref", "dev")

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch="work/stale-ref",
        expect_head="0" * 40,
        reason="superseded by accepted root",
        apply=True,
        authorized=True,
    )

    assert report["ok"] is False
    assert "expect_head_mismatch" in report["required_gaps"]
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", "refs/heads/work/stale-ref"],
            cwd=repo,
            check=False,
        ).returncode
        == 0
    )


def test_retire_unbound_work_lane_ref_blocks_linked_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-linked"
    git(repo, "worktree", "add", "-b", "work/linked", worktree.as_posix(), "dev")
    head = git(repo, "rev-parse", "work/linked")

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch="work/linked",
        expect_head=head,
        reason="superseded by accepted root",
        apply=True,
        authorized=True,
    )

    assert report["ok"] is False
    assert "unbound_retire_ref_not_unbound" in report["required_gaps"]
    assert worktree.exists()


def test_retire_unbound_work_lane_ref_requires_reason_authorization_and_head(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "work/stale-ref", "dev")

    report = retire_unbound_work_lane_ref(root=repo, branch="work/stale-ref", apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "authorization_required",
        "expect_head_required",
        "retire_reason_required",
    ]


def test_lanes_retire_repo_root_falls_back_when_git_root_unavailable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fail_git(_root: Path, *args: str, check: bool = True):
        assert args == ("rev-parse", "--show-toplevel")
        raise subprocess.CalledProcessError(128, ["git", *args])

    monkeypatch.setattr(lane_lifecycle_core, "run_git", fail_git)

    assert lane_lifecycle_core.repo_root(tmp_path) == tmp_path.resolve()


def test_retire_unbound_work_lane_ref_reports_delete_failure(monkeypatch, tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "work/stale-ref", "dev")
    head = git(repo, "rev-parse", "work/stale-ref")
    real_git = lanes_retire.run_git

    def fake_git(root: Path, *args: str, check: bool = True):
        if args[:2] == ("update-ref", "-d"):
            return subprocess.CompletedProcess(["git", *args], 1, "", "locked ref")
        return real_git(root, *args, check=check)

    monkeypatch.setattr(lanes_retire, "run_git", fake_git)

    report = lanes_retire.retire_unbound_work_lane_ref(
        root=repo,
        branch="work/stale-ref",
        expect_head=head,
        reason="superseded by accepted root",
        apply=True,
        authorized=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["unbound_ref_delete_failed"]
    assert report["stderr"] == "locked ref"


def test_retire_unbound_work_lane_ref_classifies_branch_input_gaps(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "topic", "dev")

    missing_branch = retire_unbound_work_lane_ref(
        root=repo,
        branch="",
        expect_head="h",
        reason="cleanup",
    )
    assert "unbound_retire_branch_required" in missing_branch["required_gaps"]

    not_found = retire_unbound_work_lane_ref(
        root=repo,
        branch="work/missing",
        expect_head="h",
        reason="cleanup",
    )
    assert "unbound_retire_branch_not_found" in not_found["required_gaps"]

    wrong_role = retire_unbound_work_lane_ref(
        root=repo,
        branch="topic",
        expect_head=git(repo, "rev-parse", "topic"),
        reason="cleanup",
    )
    assert "unbound_retire_not_work_lane" in wrong_role["required_gaps"]


def test_lanes_retire_handles_malformed_status_fragments() -> None:
    assert lanes_retire._unbound_work_lane_ref({}, "work/x") is None
    assert (
        lanes_retire._unbound_work_lane_ref(
            {"coordination": {"unbound_work_lane_refs": {}}}, "work/x"
        )
        is None
    )
    assert lanes_retire._branch_binding({}, "work/x") is None
    assert lanes_retire._branch_binding({"branch_bindings": {}}, "work/x") is None


def test_dirty_provenance_lives_in_semantic_subpackage(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")

    report = dirty_provenance(repo)

    assert report["dirty"] is True
    assert report["summary"]["untracked"] == 1
