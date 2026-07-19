from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.shared.core as retirement_shared
import ethos.adapters.repo.dirty.core as repo_dirty
import ethos.adapters.store.state.lease.lifecycle.core as state
from ethos.adapters.mutation.lane_retirement.landed.core import retire_landed_work_lanes
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo import coordination as repo_coordination
from ethos.adapters.repo.dirty.core import committed_change_paths
from ethos.adapters.repo.dirty.core import dirty_provenance
from ethos.adapters.repo.status.bindings import has_changed_paths
from ethos.adapters.repo.status.bindings import worktree_binding
from ethos.adapters.repo.status.core import workspace_status
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


_LANDED_BRANCH = "work/landed"
_LEASE_HOLDER = "agent:test:case:agent-a"


def _landed_lane(tmp_path: Path, *, lease_holder: str = "") -> tuple[Path, Path, Path]:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", _LANDED_BRANCH, landed.as_posix(), "dev")
    database = repo / ".ethos" / "state" / "state.sqlite"
    if lease_holder:
        state.acquire_lease(
            database,
            subject=_LANDED_BRANCH,
            holder_ref=lease_holder,
            ttl_seconds=3600,
        )
    return repo, landed, database


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
    repo, landed, _database = _landed_lane(tmp_path)
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {
                        "branch": _LANDED_BRANCH,
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
    report = retire_landed_work_lanes(root=repo, branch=_LANDED_BRANCH)

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    selected = next(lane for lane in report["lanes"] if lane["branch"] == _LANDED_BRANCH)
    assert selected["lease"]["holder_ref"] == ""
    assert selected["lease_state"] == "missing"


def test_retire_landed_work_lane_apply_preserves_unverified_json_projection(
    monkeypatch, tmp_path: Path
) -> None:
    repo, landed, _database = _landed_lane(tmp_path)
    head = git(repo, "rev-parse", _LANDED_BRANCH)
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {
                        "branch": _LANDED_BRANCH,
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
    report = retire_landed_work_lanes(
        root=repo, branch=_LANDED_BRANCH, expect_head=head, apply=True
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert landed.exists()
    assert git(repo, "branch", "--list", _LANDED_BRANCH) != ""
    leases = json.loads(lease_path.read_text(encoding="utf-8"))["leases"]
    assert [lease["branch"] for lease in leases] == [_LANDED_BRANCH, "work/other"]


def test_retire_landed_work_lane_block_explains_required_actor(monkeypatch, tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)

    landed_head = git(landed, "rev-parse", "HEAD")
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    blocked = retire_landed_work_lanes(
        root=repo, branch=_LANDED_BRANCH, expect_head=landed_head, apply=True
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
        "ref": f"refs/heads/{_LANDED_BRANCH}",
        "required_holder_ref": _LEASE_HOLDER,
    }
    assert blocked["mutation"]["decision"]["verdict"] == "block"
    assert blocked["mutation"]["legacy_binding_authoritative"] is False
    assert blocked["next_action"] == "set ETHOS_ACTOR to the current holder_ref or obtain handoff"


def test_retire_landed_work_lane_requires_matching_owner_for_leased_lane(
    monkeypatch, tmp_path: Path
) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-b")
    blocked = retire_landed_work_lanes(root=repo, branch="work/landed")

    assert blocked["ok"] is False
    assert blocked["state"] == "blocked"
    assert blocked["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert landed.exists()

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    allowed = retire_landed_work_lanes(root=repo, branch=_LANDED_BRANCH)

    assert allowed["ok"] is True
    assert allowed["state"] == "planned"
    assert allowed["required_gaps"] == []


def test_retire_landed_work_lane_apply_requires_branch(tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path)

    report = retire_landed_work_lanes(root=repo, apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == ["retire_branch_required"]
    assert landed.exists()


def test_retire_landed_work_lane_reports_missing_selected_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")

    report = retire_landed_work_lanes(root=repo, branch="work/missing")

    assert report["required_gaps"] == ["retire_branch_not_found"]


def test_retire_landed_work_lane_projects_removal_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    head = git(landed, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    monkeypatch.setattr(
        retirement_shared,
        "remove_linked_lane",
        lambda *_args, **_kwargs: {
            "ok": False,
            "state": "blocked",
            "required_gaps": ["worktree_remove_failed"],
        },
    )

    report = retire_landed_work_lanes(
        root=repo,
        branch=_LANDED_BRANCH,
        expect_head=head,
        apply=True,
    )

    assert report["required_gaps"] == ["worktree_remove_failed"]


@pytest.mark.parametrize(
    ("expect_head", "required_gap"),
    [(None, "expect_head_required"), ("not-the-lane-head", "expect_head_mismatch")],
    ids=("missing", "mismatched"),
)
def test_retire_landed_work_lane_apply_requires_matching_expected_head(
    monkeypatch,
    tmp_path: Path,
    expect_head: str | None,
    required_gap: str,
) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    report = retire_landed_work_lanes(
        root=repo,
        branch=_LANDED_BRANCH,
        expect_head=expect_head,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == [required_gap]
    assert landed.exists()
    assert git(repo, "branch", "--list", _LANDED_BRANCH) != ""


def test_retire_landed_work_lane_apply_removes_selected_clean_merged_lane(
    monkeypatch, tmp_path: Path
) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    landed_head = git(landed, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    report = retire_landed_work_lanes(
        root=repo,
        branch=_LANDED_BRANCH,
        expect_head=landed_head,
        apply=True,
    )

    assert report["ok"] is True
    assert report["state"] == "retired"
    assert report["mutation"]["expect_head"] == landed_head
    assert not landed.exists()
    assert git(repo, "branch", "--list", _LANDED_BRANCH) == ""


def test_remove_linked_lane_removes_clean_worktree_before_deleting_exact_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    lane_path = tmp_path / "repo-work-stuck"
    lane_path.mkdir()
    lane = {
        "branch": "work/stuck",
        "path": lane_path.as_posix(),
    }
    calls: list[tuple[str, ...]] = []

    def fake_run_git(
        _repo: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        calls.append(args)
        if _repo == repo and args[:1] == ("rev-parse",):
            return subprocess.CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if _repo == lane_path and args == ("rev-parse", "refs/heads/work/stuck"):
            return subprocess.CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if _repo == lane_path and args == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if _repo == lane_path and args == (
            "status",
            "--porcelain",
            "--untracked-files=all",
        ):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if _repo == lane_path and args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if _repo == repo and args[:3] == ("update-ref", "-d", "refs/heads/work/stuck"):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(retirement_shared, "run_git", fake_run_git)

    report = retirement_shared.remove_linked_lane(repo, lane, expect_head="a" * 40)

    assert report == {}
    assert calls == [
        ("rev-parse", "refs/heads/work/stuck"),
        ("rev-parse", "HEAD"),
        ("status", "--porcelain", "--untracked-files=all"),
        ("worktree", "remove", lane["path"]),
        ("update-ref", "-d", "refs/heads/work/stuck", "a" * 40),
    ]


def test_remove_linked_lane_blocks_before_effect_when_reobservation_is_stale_or_dirty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    lane_path = tmp_path / "repo-work-stuck"
    lane_path.mkdir()
    lane = {
        "branch": "work/stuck",
        "path": lane_path.as_posix(),
    }

    def fake_run_git(
        _repo: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        if _repo == lane_path and args == ("rev-parse", "refs/heads/work/stuck"):
            return subprocess.CompletedProcess(args, 0, stdout="b" * 40 + "\n", stderr="")
        if _repo == lane_path and args == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if _repo == lane_path and args == (
            "status",
            "--porcelain",
            "--untracked-files=all",
        ):
            return subprocess.CompletedProcess(args, 0, stdout="?? uncommitted.txt\n", stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(retirement_shared, "run_git", fake_run_git)

    report = retirement_shared.remove_linked_lane(repo, lane, expect_head="a" * 40)

    assert report == {
        "ok": False,
        "state": "blocked",
        "required_gaps": ["retirement_ref_stale", "work_lane_dirty"],
    }


@pytest.mark.parametrize(
    "case",
    [
        (
            {"branch": "", "path": ""},
            None,
            {},
            [
                "retirement_branch_missing",
                "expect_head_required",
                "retirement_worktree_path_unavailable",
            ],
        ),
        (
            {"branch": "work/stuck", "path": "<lane>"},
            "a" * 40,
            {
                ("rev-parse", "refs/heads/work/stuck"): (1, "", "missing ref"),
                ("rev-parse", "HEAD"): (1, "", "missing head"),
                ("status", "--porcelain", "--untracked-files=all"): (
                    1,
                    "",
                    "status unavailable",
                ),
            },
            [
                "retirement_ref_unavailable",
                "retirement_worktree_head_unavailable",
                "retirement_worktree_status_unavailable",
            ],
        ),
        (
            {"branch": "work/stuck", "path": "<lane>"},
            "a" * 40,
            {
                ("rev-parse", "refs/heads/work/stuck"): (0, "a" * 40 + "\n", ""),
                ("rev-parse", "HEAD"): (0, "b" * 40 + "\n", ""),
                ("status", "--porcelain", "--untracked-files=all"): (0, "", ""),
            },
            ["retirement_worktree_head_stale"],
        ),
    ],
)
def test_remove_linked_lane_reobservation_fails_closed_for_missing_or_unavailable_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[
        dict[str, str],
        str | None,
        dict[tuple[str, ...], tuple[int, str, str]],
        list[str],
    ],
) -> None:
    lane, expect_head, responses, required_gaps = case
    repo = init_repo(tmp_path / "repo")
    lane_path = tmp_path / "repo-work-stuck"
    if lane["path"]:
        lane_path.mkdir()
        lane = {**lane, "path": lane_path.as_posix()}

    def fake_run_git(
        _repo: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        returncode, stdout, stderr = responses[args]
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(retirement_shared, "run_git", fake_run_git)
    report = retirement_shared.remove_linked_lane(repo, lane, expect_head=expect_head)

    assert report == {
        "ok": False,
        "state": "blocked",
        "required_gaps": required_gaps,
    }


def test_remove_linked_lane_preserves_newer_ref_after_worktree_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    lane_path = tmp_path / "repo-work-stuck"
    lane_path.mkdir()
    lane = {"branch": "work/stuck", "path": lane_path.as_posix()}
    calls: list[tuple[str, ...]] = []

    def fake_run_git(
        _repo: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        calls.append(args)
        if _repo == lane_path and args == ("rev-parse", "refs/heads/work/stuck"):
            return subprocess.CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if _repo == lane_path and args == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        if _repo == lane_path and args == (
            "status",
            "--porcelain",
            "--untracked-files=all",
        ):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if _repo == lane_path and args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if _repo == repo and args[:3] == ("update-ref", "-d", "refs/heads/work/stuck"):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="cannot lock ref")
        raise AssertionError(args)

    monkeypatch.setattr(retirement_shared, "run_git", fake_run_git)
    report = retirement_shared.remove_linked_lane(repo, lane, expect_head="a" * 40)

    assert report == {
        "ok": False,
        "state": "blocked",
        "required_gaps": ["branch_delete_failed_after_worktree_removed"],
        "stderr": "cannot lock ref",
    }
    assert ("worktree", "remove", lane["path"]) in calls
    assert ("update-ref", "-d", "refs/heads/work/stuck", "a" * 40) in calls


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


def test_dirty_provenance_classifies_bounded_temporary_test_probes(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    probe_dir = repo / "tests" / "unit" / "kernel"
    probe_dir.mkdir(parents=True)
    for index in range(17):
        (probe_dir / f"test_probe_{index:02d}.py").write_text("# TEMP PROBE\n", encoding="utf-8")

    provenance = dirty_provenance(repo)

    assert provenance["temporary_probes"] == {
        "count": 17,
        "paths": [f"tests/unit/kernel/test_probe_{index:02d}.py" for index in range(16)],
        "truncated": True,
    }


def test_dirty_provenance_does_not_misclassify_ordinary_untracked_files(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    probe_dir = repo / "tests" / "unit"
    probe_dir.mkdir(parents=True)
    (probe_dir / "test_without_marker.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    (probe_dir / "probe.py").write_text("# TEMP PROBE\n", encoding="utf-8")
    tracked = probe_dir / "test_tracked.py"
    tracked.write_text("# TEMP PROBE\n", encoding="utf-8")
    git(repo, "add", tracked.relative_to(repo).as_posix())

    provenance = dirty_provenance(repo)

    assert provenance["temporary_probes"] == {
        "count": 0,
        "paths": [],
        "truncated": False,
    }


def test_temporary_probe_classification_ignores_unreadable_file(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    probe = repo / "tests" / "unit" / "test_missing_probe.py"
    probe.parent.mkdir(parents=True)
    probe.symlink_to("missing-probe-target.py")

    provenance = dirty_provenance(repo)

    assert provenance["temporary_probes"] == {
        "count": 0,
        "paths": [],
        "truncated": False,
    }


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

    monkeypatch.setattr(repo_dirty, "git_stdout_checked", fail_git)

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


def test_dirty_provenance_can_coarsen_untracked_residue(monkeypatch, tmp_path: Path) -> None:
    def summarized_git(_root: Path, *args: str) -> str:
        assert args == ("status", "--porcelain", "--untracked-files=normal")
        return "?? build/\n"

    monkeypatch.setattr(repo_dirty, "git_stdout_checked", summarized_git)

    report = dirty_provenance(tmp_path, untracked_files="normal")

    assert report["entries"] == [
        {"path": "build/", "index": "?", "worktree": "?", "kind": "untracked"}
    ]
    assert report["summary"]["untracked"] == 1


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


def test_retire_landed_selected_lane_ignores_unavailable_foreign_worktree(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    owned = tmp_path / "repo-work-owned"
    missing_foreign = tmp_path / "repo-work-missing-foreign"
    git(repo, "worktree", "add", "-b", "work/owned", owned.as_posix(), "dev")
    git(repo, "worktree", "add", "-b", "work/foreign", missing_foreign.as_posix(), "dev")
    owned_head = git(owned, "rev-parse", "HEAD")
    shutil.rmtree(missing_foreign)

    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/owned",
        holder_ref="agent:test:case:owner",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:owner")

    report = retire_landed_work_lanes(
        root=repo,
        branch="work/owned",
        expect_head=owned_head,
        apply=True,
    )

    assert report["ok"] is True
    assert report["state"] == "retired"
    assert not owned.exists()
    assert git(repo, "branch", "--list", "work/owned") == ""
    assert git(repo, "branch", "--list", "work/foreign") != ""


def test_retire_landed_selected_unavailable_worktree_fails_closed(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    missing = tmp_path / "repo-work-missing"
    git(repo, "worktree", "add", "-b", "work/missing", missing.as_posix(), "dev")
    missing_head = git(missing, "rev-parse", "HEAD")
    shutil.rmtree(missing)

    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/missing",
        holder_ref="agent:test:case:owner",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:owner")

    report = retire_landed_work_lanes(
        root=repo,
        branch="work/missing",
        expect_head=missing_head,
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["work_lane_dirty"]
    assert git(repo, "branch", "--list", "work/missing") != ""
