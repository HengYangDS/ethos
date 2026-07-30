from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import ethos.adapters.mutation.lanes as lanes
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.coordination import FOREIGN_WORK_LANE_NEXT_ACTION
from ethos.adapters.repo.coordination import ForeignLaneContext
from ethos.adapters.repo.coordination import coordination_package
from ethos.adapters.repo.coordination import foreign_work_lane
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.repo.status.workspace import workspace_status
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import create_change_source_lane
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_repo_with_candidate
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


_HOLDER = "agent:test:case:agent-test"


def _enable(repo: Path) -> None:
    workspace = repo / ".ethos/workspace.toml"
    workspace.parent.mkdir(parents=True, exist_ok=True)
    workspace.write_text("[branch_roles]\nrepository_family_worktrees = true\n", encoding="utf-8")


def test_family_profile_uses_date_bound_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    _enable(repo)
    monkeypatch.setattr(lanes, "utc_now", lambda: datetime(2026, 7, 22, tzinfo=UTC))
    report = start_work_lane(
        root=repo,
        name="retired lane admission",
        source_root=repo,
        holder_ref=_HOLDER,
    )
    lane_id = "20260722-retired-lane-admission"
    assert report["branch"] == f"work/{lane_id}"
    assert report["path"] == (tmp_path / "repo-worktrees" / lane_id).as_posix()


def test_family_profile_rejects_noncanonical_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    _enable(repo)
    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=repo,
        path=tmp_path / "outside",
        holder_ref=_HOLDER,
        apply=True,
    )
    assert report["ok"] is False
    assert report["required_gaps"] == ["work_lane_path_not_canonical"]


def test_family_profile_requires_the_canonical_work_branch_prefix(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos/workspace.toml").write_text(
        '[branch_roles]\nrepository_family_worktrees = true\nwork_branch_prefix = "lane/"\n',
        encoding="utf-8",
    )

    report = start_work_lane(root=repo, name="feature", source_root=repo, holder_ref=_HOLDER)

    assert report["ok"] is False
    assert report["required_gaps"] == ["repository_family_profile_requires_work_branch_prefix"]


def test_start_work_lane_returns_the_bound_actor_lease_and_carrier_receipt(tmp_path: Path) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    base_head = git(candidate, "rev-parse", "HEAD")

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["ok"] is True
    assert report["state"] == "started"
    assert report["branch"] == "work/feature"
    assert report["base"] == "candidate/dev"
    assert report["base_head"] == base_head
    assert report["path"] == target.resolve().as_posix()
    assert report["holder_ref"] == _HOLDER
    assert "claim_id" not in report
    assert (
        report["base_commitment_digest"]
        == load_profile_commitment(source, tree_ref=git(source, "rev-parse", "HEAD")).digest()
    )
    assert report["worktree"] == {
        "branch": "work/feature",
        "path": target.resolve().as_posix(),
        "head": report["head"],
        "role": "work_lane",
        "worktree_binding": "linked",
    }
    assert report["lease"] == {
        key: value
        for key, value in leases_by_branch(repo)["work/feature"].items()
        if key != "contract_binding"
    }
    assert report["lease"]["base_commitment_digest"] == report["base_commitment_digest"]
    assert report["lease"]["expected_head"] == report["head"]
    assert (
        workspace_status(target, include_foreign_path_scope=False)["closeout_support"][
            "contract_binding"
        ]
        == "bound"
    )
    assert report["required_gaps"] == []


def test_start_work_lane_acquires_lease_for_final_initialization_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    base_head = git(candidate, "rev-parse", "HEAD")
    acquired_heads: list[str] = []
    acquire_lease = lanes.acquire_lease

    def capture_expected_head(*args: object, **kwargs: object):
        acquired_heads.append(kwargs["lease"].expected_head)
        return acquire_lease(*args, **kwargs)

    monkeypatch.setattr(lanes, "acquire_lease", capture_expected_head)

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["ok"] is True
    assert report["head"] != base_head
    assert acquired_heads == [report["head"]]


def test_start_work_lane_creates_no_work_ref_before_final_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    acquire_lease = lanes.acquire_lease

    def assert_ref_absent(*args: object, **kwargs: object):
        assert ref_head(repo, "work/feature") == ""
        return acquire_lease(*args, **kwargs)

    monkeypatch.setattr(lanes, "acquire_lease", assert_ref_absent)

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["ok"] is True
    assert ref_head(repo, "work/feature") == report["head"]


def test_start_work_lane_revokes_final_lease_when_ref_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    run_git = lanes.run_git

    def fail_ref_creation(root: Path, *args: str, **kwargs: object):
        if args[:2] == ("update-ref", "refs/heads/work/feature"):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="injected ref failure")
        return run_git(root, *args, **kwargs)

    monkeypatch.setattr(lanes, "run_git", fail_ref_creation)

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["lease_state"] == "revoked"
    assert report["required_gaps"] == ["lane_start_ref_creation_failed"]
    assert "work/feature" not in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_preserves_foreign_ref_created_during_failed_cas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    run_git = lanes.run_git
    foreign_head = git(candidate, "rev-parse", "HEAD")

    def race_ref_creation(root: Path, *args: str, **kwargs: object):
        if args[:2] == ("update-ref", "refs/heads/work/feature"):
            git(repo, "update-ref", "refs/heads/work/feature", foreign_head)
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="injected ref race")
        return run_git(root, *args, **kwargs)

    monkeypatch.setattr(lanes, "run_git", race_ref_creation)

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["lease_state"] == "retained"
    assert report["required_gaps"] == [
        "lane_creation_compensation_failed",
        "lane_start_ref_changed",
    ]
    assert "work/feature" in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == foreign_head
    assert not target.exists()


def test_foreign_and_unbound_lane_observation_only_requests_handoff_or_takeover(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    foreign = create_change_source_lane(
        repo,
        tmp_path / "repo-work-foreign",
        branch="work/foreign",
        holder_ref="agent:test:case:foreign",
    )
    branch = "work/foreign"
    lane = foreign_work_lane(
        {
            "path": foreign.as_posix(),
            "head": git(foreign, "rev-parse", "HEAD"),
            "branch": branch,
            "role": "work_lane",
            "worktree_binding": "linked",
        },
        ForeignLaneContext(
            current_role="work_lane",
            current_path_scope=("openspec",),
            current_scope_state="bounded",
            candidate_branch="candidate/dev",
            lease=leases_by_branch(repo)[branch],
            root=repo,
        ),
    )

    coordination = coordination_package(
        [lane],
        required_gaps=[],
        advisory_gaps=[],
        unbound_work_lane_refs=[
            {
                "branch": "work/unbound",
                "head": "a" * 40,
                "base_commitment_digest": "",
                "contract_binding": "missing",
                "lease_state": "missing",
                "relation_to_accepted": "unknown",
                "next_action": "ignored",
            }
        ],
    )

    assert lane["next_action"] == FOREIGN_WORK_LANE_NEXT_ACTION
    assert lane["action_preview"] == {
        "candidate_actions": ["observe"],
        "blocked_actions": ["write", "land", "retire"],
        "why": ["foreign_lane_requires_handoff_or_exact_authorized_lease_takeover"],
        "mints_authority": False,
        "recheck_required": True,
    }
    assert coordination["next_action"] == FOREIGN_WORK_LANE_NEXT_ACTION
    unbound = coordination["unbound_work_lane_refs"]
    assert isinstance(unbound, list)
    assert unbound[0]["next_action"] == FOREIGN_WORK_LANE_NEXT_ACTION


def test_start_work_lane_initialization_head_is_checkout_and_identity_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    first_source = create_change_source_lane(
        repo,
        tmp_path / "repo-work-source",
        holder_ref=_HOLDER,
    )
    run_git = lanes.run_git
    identities = iter(
        (
            {
                "GIT_AUTHOR_NAME": "First Author",
                "GIT_AUTHOR_EMAIL": "first-author@example.invalid",
                "GIT_AUTHOR_DATE": "2001-01-01T00:00:00+00:00",
                "GIT_COMMITTER_NAME": "First Committer",
                "GIT_COMMITTER_EMAIL": "first-committer@example.invalid",
                "GIT_COMMITTER_DATE": "2001-01-01T00:00:00+00:00",
            },
            {
                "GIT_AUTHOR_NAME": "Second Author",
                "GIT_AUTHOR_EMAIL": "second-author@example.invalid",
                "GIT_AUTHOR_DATE": "2002-02-02T00:00:00+00:00",
                "GIT_COMMITTER_NAME": "Second Committer",
                "GIT_COMMITTER_EMAIL": "second-committer@example.invalid",
                "GIT_COMMITTER_DATE": "2002-02-02T00:00:00+00:00",
            },
        )
    )

    def vary_ambient_identity(root: Path, *args: str, **kwargs: object):
        if args[:1] == ("commit-tree",):
            kwargs["env"] = {**next(identities), **dict(kwargs.get("env") or {})}
        return run_git(root, *args, **kwargs)

    monkeypatch.setattr(lanes, "run_git", vary_ambient_identity)
    first = start_work_lane(
        root=repo,
        name="first",
        source_root=first_source,
        path=tmp_path / "first-target",
        holder_ref=_HOLDER,
        apply=True,
    )
    second = start_work_lane(
        root=repo,
        name="second",
        source_root=first_source,
        path=tmp_path / "second-target",
        holder_ref=_HOLDER,
        apply=True,
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert second["head"] == first["head"]


def test_start_work_lane_blocks_source_lease_head_mismatch(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    source_file = source / "SOURCE.md"
    source_file.write_text("drift\n", encoding="utf-8")
    git(source, "add", "SOURCE.md")
    git(
        source,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "drift source without advancing lease",
    )

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["required_gaps"] == ["source_lease_head_mismatch"]
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_blocks_source_lease_contract_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    leases_by_branch = lanes.leases_by_branch

    def mismatched_contract(root: Path):
        leases = leases_by_branch(root)
        if root.resolve() == source.resolve():
            lease = dict(leases["work/change-source"])
            lease["contract_binding"] = "mismatch"
            leases["work/change-source"] = lease
        return leases

    monkeypatch.setattr(lanes, "leases_by_branch", mismatched_contract)

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["required_gaps"] == ["source_lease_contract_unbound"]
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_blocks_candidate_active_change_carrier(tmp_path: Path) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    carrier = candidate / "openspec/changes/stale/commitment.toml"
    carrier.parent.mkdir(parents=True)
    repository = load_repository_commitment(candidate)
    carrier.write_text(
        'schema_version = 1\nid = "change:stale"\nintent = "Stale."\n'
        f'subjects = ["{repository.id}"]\nscope = ["**"]\n',
        encoding="utf-8",
    )
    git(candidate, "add", "openspec/changes/stale/commitment.toml")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "seed forbidden candidate carrier",
    )

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["required_gaps"] == ["candidate_active_change_carrier_present"]
    assert report["candidate_active_changes"] == ["stale"]
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_blocks_source_head_drift_before_lease_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    run_git = lanes.run_git
    drifted = False

    def drift_after_initialization_commit(root: Path, *args: str, **kwargs: object):
        nonlocal drifted
        completed = run_git(root, *args, **kwargs)
        if args[:1] == ("commit-tree",) and completed.returncode == 0 and not drifted:
            drifted = True
            source_file = source / "SOURCE.md"
            source_file.write_text("drift\n", encoding="utf-8")
            git(source, "add", "SOURCE.md")
            git(
                source,
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "drift source",
            )
        return completed

    monkeypatch.setattr(lanes, "run_git", drift_after_initialization_commit)

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["source_head_changed_during_lane_start"]
    assert "work/feature" not in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_blocks_candidate_head_drift_before_lease_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    run_git = lanes.run_git
    drifted = False

    def drift_after_initialization_commit(root: Path, *args: str, **kwargs: object):
        nonlocal drifted
        completed = run_git(root, *args, **kwargs)
        if args[:1] == ("commit-tree",) and completed.returncode == 0 and not drifted:
            drifted = True
            commit_fixture_file(candidate, "CANDIDATE.md", "drift\n", "drift candidate")
        return completed

    monkeypatch.setattr(lanes, "run_git", drift_after_initialization_commit)

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["candidate_head_changed_during_lane_start"]
    assert "work/feature" not in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_work_lane_status_reports_base_contract_rewrite_as_mismatch(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )
    assert report["ok"] is True
    contract = target / "openspec" / "changes" / "fixture-change" / "commitment.toml"
    contract.write_text(
        contract.read_text(encoding="utf-8").replace(
            "Exercise the governed fixture lifecycle.",
            "Attempt to rewrite the immutable base.",
        ),
        encoding="utf-8",
    )

    status = workspace_status(target, include_foreign_path_scope=False)

    assert status["closeout_support"]["contract_binding"] == "mismatch"
    assert status["closeout_support"]["supported"] is False


def test_start_work_lane_blocks_dirty_root_before_reserving_or_creating(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    (repo / "README.md").write_text("# dirty\n", encoding="utf-8")

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report == {
        "ok": False,
        "state": "blocked",
        "branch": "work/feature",
        "path": target.resolve().as_posix(),
        "role": "accepted_root",
        "dirty": True,
        "required_gaps": ["lane_start_requires_clean_accepted_root"],
    }
    assert "work/feature" not in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_blocks_missing_candidate_contract_without_effects(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    git(source, "rm", "-r", "openspec/changes/fixture-change")

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["source_work_lane_invalid"]
    assert "work/feature" not in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_blocks_ambiguous_candidate_contract_without_effects(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    second = source / "openspec/changes/second"
    second.mkdir(parents=True)
    (second / "commitment.toml").write_text(
        'schema_version = 1\nid = "change:second"\nintent = "Second."\n'
        'subjects = ["repository:self"]\n',
        encoding="utf-8",
    )
    (second / "tasks.md").write_text("- [ ] Continue\n", encoding="utf-8")

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["source_work_lane_invalid"]
    assert "work/feature" not in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_rejects_invalid_actor_before_reserving_or_creating(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref="invalid",
        apply=True,
    )

    assert report == {
        "ok": False,
        "state": "blocked",
        "branch": "work/feature",
        "required_gaps": ["holder_ref_invalid"],
    }
    assert "work/feature" not in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_leaves_no_lease_when_worktree_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    run_git = lanes.run_git

    def fail_worktree_add(root: Path, *args: str, **kwargs: object):
        if args[:3] == ("worktree", "add", "--detach"):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="injected failure")
        return run_git(root, *args, **kwargs)

    monkeypatch.setattr(lanes, "run_git", fail_worktree_add)

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report == {
        "ok": False,
        "state": "blocked",
        "branch": "work/feature",
        "path": target.resolve().as_posix(),
        "stderr": "injected failure",
        "carrier_cleanup": {"worktree_removed": True, "ref_removed": True},
        "lease_state": "not_acquired",
        "required_gaps": ["worktree_add_failed"],
    }
    assert "work/feature" not in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_start_work_lane_retains_final_lease_when_carrier_ownership_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"
    run_git = lanes.run_git

    def hide_created_worktree(root: Path, *args: str, **kwargs: object):
        completed = run_git(root, *args, **kwargs)
        if args[:3] == ("worktree", "list", "--porcelain") and ref_head(root, "work/feature"):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return completed

    monkeypatch.setattr(lanes, "run_git", hide_created_worktree)

    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=source,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["lease_state"] == "retained"
    assert report["required_gaps"] == [
        "lane_creation_compensation_failed",
        "lane_start_target_path_ownership_unknown",
    ]
    assert "work/feature" in leases_by_branch(repo)
    assert ref_head(repo, "work/feature")
    assert target.exists()
