from __future__ import annotations

import subprocess
from pathlib import Path

from ethos_workspace.lanes import start_work_lane
from ethos_workspace.prewrite import prewrite_guard
from ethos_workspace.state import active_leases
from ethos_workspace.status import workspace_status


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


def test_workspace_status_reports_foreign_work_lanes_without_reading_them(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    foreign = tmp_path / "repo-work-foreign"
    git(repo, "worktree", "add", "-b", "work/foreign", foreign.as_posix(), "dev")

    status = workspace_status(repo)

    assert status["role"] == "accepted_root"
    assert status["foreign_work_lanes"] == [
        {
            "branch": "work/foreign",
            "open_action": "open_worktree",
            "open_label": "Open Worktree",
            "head": git(repo, "rev-parse", "dev"),
            "path": foreign.as_posix(),
            "role": "work_lane",
        }
    ]
    assert "foreign_work_lane_present" in status["required_gaps"]


def test_workspace_status_marks_candidate_and_work_lanes_as_open_worktree(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")

    status = workspace_status(repo)

    assert status["candidate"]["open_action"] == "open_worktree"
    assert status["candidate"]["open_label"] == "Open Worktree"
    assert status["candidate"]["worktree_path"] == candidate.as_posix()
    worktree_actions = {
        action["branch"]: action
        for action in status["branch_actions"]
        if action["action"] == "open_worktree"
    }
    assert worktree_actions["candidate/dev"]["label"] == "Open Worktree"
    assert worktree_actions["candidate/dev"]["path"] == candidate.as_posix()
    assert worktree_actions["work/feature"]["label"] == "Open Worktree"
    assert worktree_actions["work/feature"]["path"] == worktree.as_posix()


def test_workspace_status_reports_missing_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    status = workspace_status(repo)

    assert status["candidate"] == {
        "branch": "candidate/dev",
        "exists": False,
        "head": "",
        "worktree_exists": False,
        "worktree_path": "",
        "open_action": "bootstrap_worktree",
        "open_label": "Bootstrap Worktree",
    }
    assert "candidate_branch_missing" in status["required_gaps"]


def test_workspace_status_reports_candidate_branch_without_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "candidate/dev", "dev")

    status = workspace_status(repo)

    assert status["candidate"]["exists"] is True
    assert status["candidate"]["worktree_exists"] is False
    assert status["candidate"]["worktree_path"] == ""
    assert "candidate_worktree_missing" in status["required_gaps"]


def test_prewrite_rejects_tracked_path_from_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = prewrite_guard(
        root=repo,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["error"] == "protected_lane_prewrite_blocked"
    assert report["role"] == "accepted_root"


def test_prewrite_allows_owned_work_lane_with_matching_editor_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is True
    assert report["role"] == "work_lane"
    assert report["error"] == ""


def test_prewrite_rejects_work_lane_without_editor_root_binding(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
    )

    assert report["ok"] is False
    assert report["role"] == "work_lane"
    assert report["error"] == "editor_root_missing"


def test_prewrite_rejects_protected_lane_roles(tmp_path: Path) -> None:
    cases = {
        "candidate": ("candidate/dev",),
        "submit": ("submit/review",),
        "other": ("feature/unknown",),
    }
    for role, checkout_args in cases.items():
        repo = init_repo(tmp_path / f"repo-{role}")
        git(repo, "checkout", "-b", *checkout_args)

        report = prewrite_guard(
            root=repo,
            paths=[repo / "README.md"],
            editor_root=repo,
            require_editor_root=True,
        )

        assert report["ok"] is False
        assert report["role"] == role
        assert report["error"] == "protected_lane_prewrite_blocked"


def test_prewrite_rejects_detached_lane(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo-detached")
    git(repo, "checkout", "--detach", "HEAD")

    report = prewrite_guard(
        root=repo,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["role"] == "detached"
    assert report["error"] == "protected_lane_prewrite_blocked"


def test_start_work_lane_apply_creates_worktree_and_records_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["branch"] == "work/feature"
    assert worktree.exists()
    assert git(worktree, "branch", "--show-current") == "work/feature"
    leases = active_leases(repo / ".ethos" / "state" / "state.sqlite")
    assert [(lease["subject"], lease["owner"]) for lease in leases] == [
        ("work/feature", "agent:test")
    ]


def test_start_work_lane_apply_requires_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "candidate_branch_missing" in report["required_gaps"]
    assert not worktree.exists()


def test_start_work_lane_apply_requires_candidate_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "candidate/dev", "dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "candidate_worktree_missing" in report["required_gaps"]
    assert not worktree.exists()


def test_start_work_lane_apply_starts_from_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    candidate_head = git(repo, "rev-parse", "candidate/dev")
    (repo / "README.md").write_text("# changed on dev\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance dev only",
    )
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is True
    assert git(worktree, "rev-parse", "HEAD") == candidate_head
    assert git(repo, "rev-parse", "dev") != candidate_head


def test_start_work_lane_apply_requires_clean_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    current_worktree = tmp_path / "repo-work-current"
    new_worktree = tmp_path / "repo-work-nested"
    git(repo, "worktree", "add", "-b", "work/current", current_worktree.as_posix(), "dev")

    report = start_work_lane(
        root=current_worktree,
        name="nested",
        path=new_worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "lane_start_requires_clean_accepted_root" in report["required_gaps"]
    assert not new_worktree.exists()


def test_start_work_lane_apply_rejects_dirty_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["role"] == "accepted_root"
    assert report["dirty"] is True
    assert "lane_start_requires_clean_accepted_root" in report["required_gaps"]
    assert not worktree.exists()
