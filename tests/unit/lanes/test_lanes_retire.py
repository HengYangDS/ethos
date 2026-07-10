from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.mutation.lane_retirement.shared.core as retirement_shared
import ethos.adapters.mutation.lane_retirement.unbound.core as unbound_retirement
import ethos.adapters.repo.status.core as repo_status
from ethos.adapters.mutation.lane_lifecycle import core as lane_lifecycle_core
from ethos.adapters.mutation.lanes import retire_landed_work_lanes
from ethos.adapters.mutation.lanes import retire_unbound_work_lane_ref
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo import coordination as repo_coordination
from ethos.adapters.repo.dirty.core import committed_change_paths
from ethos.adapters.repo.dirty.core import dirty_provenance
from ethos.adapters.repo.status.bindings import has_changed_paths
from ethos.adapters.repo.status.bindings import worktree_binding
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


def test_retire_landed_work_lane_rejects_legacy_json_owner_projection(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {
                        "branch": "work/landed",
                        "owner": "agent-json",
                        "expires_at": "2999-01-01T00:00:00Z",
                        "worktree_path": landed.as_posix(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("ETHOS_ACTOR", "agent-json")
    report = retire_landed_work_lanes(root=repo, branch="work/landed")

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    selected = next(lane for lane in report["lanes"] if lane["branch"] == "work/landed")
    assert selected["lease"]["holder_ref"] == ""
    assert selected["lease"]["normalization_state"] == "legacy_ambiguous"
    assert selected["lease_state"] == "missing"


def test_retire_landed_work_lane_apply_preserves_unverified_json_projection(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    head = git(repo, "rev-parse", "work/landed")
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {
                        "branch": "work/landed",
                        "owner": "agent-json",
                        "expires_at": "2999-01-01T00:00:00Z",
                        "worktree_path": landed.as_posix(),
                    },
                    {
                        "branch": "work/other",
                        "owner": "agent-other",
                        "expires_at": "2999-01-01T00:00:00Z",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("ETHOS_ACTOR", "agent-json")
    report = retire_landed_work_lanes(root=repo, branch="work/landed", expect_head=head, apply=True)

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert landed.exists()
    assert git(repo, "branch", "--list", "work/landed") != ""
    leases = json.loads(lease_path.read_text(encoding="utf-8"))["leases"]
    assert [lease["branch"] for lease in leases] == ["work/landed", "work/other"]


def test_retire_landed_work_lane_block_explains_required_actor(monkeypatch, tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/landed",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )

    landed_head = git(landed, "rev-parse", "HEAD")
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    blocked = retire_landed_work_lanes(
        root=repo, branch="work/landed", expect_head=landed_head, apply=True
    )

    assert blocked["ok"] is False
    assert blocked["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert {
        key: blocked["mutation"][key]
        for key in (
            "invocation_holder_ref",
            "holder_bound",
            "invocation_source",
            "expect_head",
            "ref",
            "required_holder_ref",
        )
    } == {
        "invocation_holder_ref": "",
        "holder_bound": "false",
        "invocation_source": "ETHOS_ACTOR",
        "expect_head": landed_head,
        "ref": "refs/heads/work/landed",
        "required_holder_ref": "agent:test:case:agent-a",
    }
    assert blocked["mutation"]["decision"]["verdict"] == "block"
    assert blocked["mutation"]["legacy_binding_authoritative"] is False
    assert blocked["next_action"] == "set ETHOS_ACTOR to the current holder_ref or obtain handoff"


def test_retire_landed_work_lane_requires_matching_owner_for_leased_lane(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    db = repo / ".ethos" / "state" / "state.sqlite"
    state.acquire_lease(
        db,
        subject="work/landed",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-b")
    blocked = retire_landed_work_lanes(root=repo, branch="work/landed")

    assert blocked["ok"] is False
    assert blocked["state"] == "blocked"
    assert blocked["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert landed.exists()

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
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
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
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
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
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
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
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

    monkeypatch.setattr(retirement_shared, "run_git", fake_run_git)

    report = retirement_shared.remove_linked_lane(repo, lane, expect_head="a" * 40)

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

    monkeypatch.setattr(retirement_shared, "run_git", fake_run_git)

    report = retirement_shared.remove_linked_lane(repo, lane, expect_head="a" * 40)

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
    start_work_lane(
        root=repo,
        name="first",
        path=first,
        holder_ref="agent:test:case:agent-first",
        apply=True,
    )
    start_work_lane(
        root=repo,
        name="second",
        path=second,
        holder_ref="agent:test:case:agent-second",
        apply=True,
    )

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
            "holder_ref": "agent:test:case:agent-first",
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


def test_dirty_provenance_reports_missing_cwd_as_unavailable(tmp_path: Path) -> None:
    missing = tmp_path / "missing-worktree"

    report = dirty_provenance(missing)

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
    assert "missing-worktree" in str(report["error"])


def test_has_changed_paths_fails_closed_when_worktree_path_disappears(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing-candidate"

    assert has_changed_paths(missing) is True


def test_worktree_binding_reports_absent_path(tmp_path: Path) -> None:
    assert worktree_binding("", current_path=tmp_path.resolve()) == "absent"


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

    assert required == ["coordination_gap:current_scope_unknown"]
    assert advisory == [
        "foreign_work_lane_present",
        "coordination_gap:foreign_scope_unknown:work/unknown",
    ]


def test_foreign_unknown_scope_is_advisory_when_current_scope_is_bounded() -> None:
    required, advisory = repo_coordination.coordination_gaps(
        [
            {
                "branch": "work/unknown",
                "lease_state": "leased",
                "coordination_state": "unknown",
            }
        ],
        current_role="work_lane",
        current_scope_state="bounded",
    )

    assert required == []
    assert "coordination_gap:foreign_scope_unknown:work/unknown" in advisory


