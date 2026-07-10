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
        ["git", *args], cwd=root, check=True, text=True, capture_output=True
    )
    return completed.stdout.strip()


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / ".gitignore").write_text(
        ".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8"
    )
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text(
        "*\n!.gitignore\n", encoding="utf-8"
    )
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


def test_retire_unbound_work_lane_ref_dry_run_reports_head_bound_plan(
    tmp_path: Path,
) -> None:
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
    assert report["mutation"]["request"] == {
        "command": "lane-retire-unbound",
        "apply": False,
        "confirmation_present": False,
        "expect_head": head,
    }
    assert report["mutation"]["ref"] == "refs/heads/work/stale-ref"
    assert report["mutation"]["decision"]["verdict"] == "allow"
    assert git(repo, "rev-parse", "--verify", "work/stale-ref") == head


def test_retire_unbound_work_lane_ref_apply_deletes_only_matching_ref(
    tmp_path: Path,
) -> None:
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


def test_lane_retirement_repo_root_falls_back_when_git_root_unavailable(
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
    real_git = retirement_shared.run_git

    def fake_git(root: Path, *args: str, check: bool = True):
        if args[:2] == ("update-ref", "-d"):
            return subprocess.CompletedProcess(["git", *args], 1, "", "locked ref")
        return real_git(root, *args, check=check)

    monkeypatch.setattr(retirement_shared, "run_git", fake_git)

    report = unbound_retirement.retire_unbound_work_lane_ref(
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


def test_retire_unbound_work_lane_ref_classifies_branch_input_gaps(
    tmp_path: Path,
) -> None:
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


def test_lane_retirement_handles_malformed_status_fragments() -> None:
    assert unbound_retirement._unbound_work_lane_ref({}, "work/x") is None
    assert (
        unbound_retirement._unbound_work_lane_ref(
            {"coordination": {"unbound_work_lane_refs": {}}}, "work/x"
        )
        is None
    )
    assert unbound_retirement._branch_binding({}, "work/x") is None
    assert unbound_retirement._branch_binding({"branch_bindings": {}}, "work/x") is None


def test_dirty_provenance_lives_in_semantic_subpackage(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")

    report = dirty_provenance(repo)

    assert report["dirty"] is True
    assert report["summary"]["untracked"] == 1


def test_delete_json_projection_lease_ignores_absent_or_malformed_projection(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0

    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text("{not-json", encoding="utf-8")
    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0

    lease_path.write_text(json.dumps([{"branch": "work/landed"}]), encoding="utf-8")
    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0

    lease_path.write_text(json.dumps({"leases": "not-a-list"}), encoding="utf-8")
    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0


def test_delete_json_projection_lease_matches_branch_or_subject_and_preserves_rows(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {"subject": "work/landed", "owner": "agent-subject"},
                    {"branch": "work/other", "owner": "agent-other"},
                    "opaque-row",
                ],
            }
        ),
        encoding="utf-8",
    )

    removed = retirement_shared.delete_json_projection_lease(repo, subject="work/landed")

    assert removed == 1
    payload = json.loads(lease_path.read_text(encoding="utf-8"))
    assert payload == {
        "leases": [
            {"branch": "work/other", "owner": "agent-other"},
            "opaque-row",
        ],
        "schema_version": 1,
    }


def test_delete_json_projection_lease_leaves_projection_when_subject_is_absent(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    original = {"leases": [{"branch": "work/other", "owner": "agent-other"}]}
    lease_path.write_text(json.dumps(original), encoding="utf-8")

    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0
    assert json.loads(lease_path.read_text(encoding="utf-8")) == original
