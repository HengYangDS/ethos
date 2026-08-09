from __future__ import annotations

import hashlib
import subprocess
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_start_carrier as lane_start_carrier
import ethos.adapters.mutation.lanes as lanes
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.coordination import FOREIGN_WORK_LANE_NEXT_ACTION
from ethos.adapters.repo.coordination import ForeignLaneContext
from ethos.adapters.repo.coordination import foreign_work_lane
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.status.bindings import closeout_support
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import branch_role_policy_from_text
from ethos.contracts.branch.roles import strict_branch_role_policy_from_text
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.lifecycle_cases import LaneStartCase

if TYPE_CHECKING:
    from pathlib import Path


_HOLDER = "agent:test:case:agent-test"

_LEGACY_BRANCH_POLICY = """[branch_roles]
release_branch = "main"
accepted_branch = "dev"
candidate_branch = "candidate/dev"
release_mirror = "accepted_ff"
work_branch_prefix = "work/"
proposal_branch_prefix = "proposal/"
repository_family_worktrees = true
"""


def test_work_lane_projections_preserve_exact_carrier_coordinates() -> None:
    lease = {
        "lane_incarnation_id": "lane-incarnation:example",
        "lease_id": "lease:example",
        "holder_ref": _HOLDER,
        "epoch": 2,
        "expected_head": "a" * 40,
        "expected_tree": "b" * 40,
        "issued_at": "2026-08-01T00:00:00+00:00",
        "renewed_at": "2026-08-01T00:00:00+00:00",
        "path_scope": ["src/**"],
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "d" * 64,
        "expires_at": "2026-08-02T00:00:00+00:00",
        "payload_sha256": "e" * 64,
        "lease_state": "valid",
        "commitment_binding": "mismatch",
    }

    summary = lease_generation(lease)
    support = closeout_support(
        branch="work/example",
        role=ROLE_WORK_LANE,
        dirty=False,
        candidate={
            "exists": False,
            "worktree_exists": False,
            "branch": "candidate/dev",
            "worktree_path": "",
        },
        lease_by_branch={"work/example": lease},
        coordination_required_gaps=[],
    )

    assert {
        "expected_head": lease["expected_head"],
        "expected_tree": lease["expected_tree"],
        "issued_at": lease["issued_at"],
        "renewed_at": lease["renewed_at"],
        "path_scope": lease["path_scope"],
        "base_commitment_path": lease["base_commitment_path"],
        "base_commitment_bytes_sha256": lease["base_commitment_bytes_sha256"],
        "base_commitment_digest": lease["base_commitment_digest"],
    }.items() <= summary.items()
    assert {
        "lease_expected_head": lease["expected_head"],
        "lease_expected_tree": lease["expected_tree"],
        "lease_base_commitment_path": lease["base_commitment_path"],
        "lease_base_commitment_bytes_sha256": lease["base_commitment_bytes_sha256"],
        "base_commitment_digest": lease["base_commitment_digest"],
    }.items() <= support.items()


def _enable(repo: Path) -> None:
    workspace = repo / ".ethos/workspace.toml"
    workspace.parent.mkdir(parents=True, exist_ok=True)
    workspace.write_text("[branch_roles]\ncanonical_sibling_worktrees = true\n", encoding="utf-8")


def test_canonical_sibling_profile_uses_date_bound_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
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


def test_canonical_sibling_profile_rejects_noncanonical_path(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _enable(repo)
    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=repo,
        path=tmp_path / "outside",
        holder_ref=_HOLDER,
        apply=True,
    )
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["work_lane_path_not_canonical"]


def test_legacy_complete_branch_policy_preserves_canonical_sibling_authority(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos/workspace.toml").write_text(_LEGACY_BRANCH_POLICY, encoding="utf-8")

    assert branch_role_policy_from_text(_LEGACY_BRANCH_POLICY).canonical_sibling_worktrees
    assert strict_branch_role_policy_from_text(_LEGACY_BRANCH_POLICY).canonical_sibling_worktrees
    report = start_work_lane(
        root=repo,
        name="repository record publication",
        source_root=repo,
        path=tmp_path / "intentionally-noncanonical",
        holder_ref=_HOLDER,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["work_lane_path_not_canonical"]


def test_incomplete_retired_branch_policy_key_fails_closed() -> None:
    text = "[branch_roles]\nrepository_family_worktrees = true\n"

    with pytest.raises(ValueError, match="branch_roles legacy schema requires migration"):
        branch_role_policy_from_text(text)
    with pytest.raises(ValueError, match="branch_roles legacy schema requires migration"):
        strict_branch_role_policy_from_text(text)


def test_canonical_sibling_profile_requires_configured_work_branch_prefix(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos/workspace.toml").write_text(
        '[branch_roles]\ncanonical_sibling_worktrees = true\nwork_branch_prefix = "lane/"\n',
        encoding="utf-8",
    )

    report = start_work_lane(root=repo, name="feature", source_root=repo, holder_ref=_HOLDER)

    assert report["verdict"] == "block"
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

    assert report["verdict"] == "pass"
    assert report["state"] == "started"
    assert report["branch"] == "work/feature"
    assert report["base"] == "candidate/dev"
    assert report["base_head"] == base_head
    assert report["path"] == target.resolve().as_posix()
    assert report["hook_runtime"] == hook_runtime_binding(target)
    assert report["hook_runtime"]["required_gaps"] == []
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
        if key != "commitment_binding"
    }
    assert report["lease"]["base_commitment_digest"] == report["base_commitment_digest"]
    assert report["lease"]["expected_head"] == report["head"]
    assert report["lease"]["expected_tree"] == git(target, "rev-parse", "HEAD^{tree}")
    assert report["lease"]["base_commitment_path"] == (
        "openspec/changes/fixture-change/commitment.toml"
    )
    assert "materialized_carrier" not in report
    assert (
        report["lease"]["base_commitment_bytes_sha256"]
        == hashlib.sha256(
            (target / report["lease"]["base_commitment_path"]).read_bytes()
        ).hexdigest()
    )
    closeout_support = workspace_status(target, include_foreign_path_scope=False)[
        "closeout_support"
    ]
    assert closeout_support["commitment_binding"] == "bound"
    assert {
        "lease_expected_head": report["lease"]["expected_head"],
        "lease_expected_tree": report["lease"]["expected_tree"],
        "lease_base_commitment_path": report["lease"]["base_commitment_path"],
        "lease_base_commitment_bytes_sha256": report["lease"]["base_commitment_bytes_sha256"],
        "base_commitment_digest": report["lease"]["base_commitment_digest"],
    }.items() <= closeout_support.items()
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

    assert report["verdict"] == "pass"
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

    assert report["verdict"] == "pass"
    assert ref_head(repo, "work/feature") == report["head"]


def test_start_work_lane_revokes_final_lease_when_ref_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)
    target = tmp_path / "repo-work-feature"

    def fail_ref_creation(*_args: object, **_kwargs: object):
        msg = "injected ref failure"
        raise ValueError(msg)

    monkeypatch.setattr(lane_start_carrier, "execute_git_effect", fail_ref_creation)

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
    foreign_head = git(candidate, "rev-parse", "HEAD")

    def race_ref_creation(*_args: object, **_kwargs: object):
        git(repo, "update-ref", "refs/heads/work/feature", foreign_head)
        msg = "injected ref race"
        raise ValueError(msg)

    monkeypatch.setattr(lane_start_carrier, "execute_git_effect", race_ref_creation)

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

    assert lane["next_action"] == FOREIGN_WORK_LANE_NEXT_ACTION
    lease = leases_by_branch(repo)[branch]
    assert {
        "expected_head": lease["expected_head"],
        "expected_tree": lease["expected_tree"],
        "base_commitment_path": lease["base_commitment_path"],
        "base_commitment_bytes_sha256": lease["base_commitment_bytes_sha256"],
        "base_commitment_digest": lease["base_commitment_digest"],
    }.items() <= lane["lease"].items()
    assert lane["action_preview"] == {
        "candidate_actions": ["observe"],
        "blocked_actions": ["write", "land", "retire"],
        "why": ["foreign_lane_requires_handoff_or_exact_authorized_lease_takeover"],
        "mints_authority": False,
        "recheck_required": True,
    }


def test_optional_git_worktree_lock_is_observed_but_never_mints_authority(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    foreign = create_change_source_lane(
        repo,
        tmp_path / "repo-work-locked",
        branch="work/locked",
        holder_ref="agent:test:case:foreign",
    )
    git(repo, "worktree", "lock", "--reason", "handoff-in-progress", foreign.as_posix())

    status = workspace_status(repo)
    lane = next(item for item in status["foreign_work_lanes"] if item["branch"] == "work/locked")

    assert lane["git_lock"] == {
        "locked": True,
        "reason": "handoff-in-progress",
        "mints_authority": False,
    }
    assert lane["action_preview"]["mints_authority"] is False
    assert lane["handoff_required"] is True


def test_unbound_work_lane_ref_preserves_exact_lease_coordinates(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    path = create_change_source_lane(
        repo,
        tmp_path / "repo-work-unbound",
        branch="work/unbound",
        holder_ref="agent:test:case:unbound",
    )
    lease = leases_by_branch(repo)["work/unbound"]
    git(repo, "worktree", "remove", path.as_posix())

    status = workspace_status(repo, include_foreign_path_scope=False)
    binding = next(item for item in status["branch_bindings"] if item["branch"] == "work/unbound")
    assert "coordination" not in status
    unbound = status["unbound_work_lane_refs"]

    assert {
        "expected_head",
        "expected_tree",
        "base_commitment_path",
        "base_commitment_bytes_sha256",
    }.isdisjoint(binding)
    assert len(unbound) == 1
    assert {
        name: unbound[0][name]
        for name in (
            "lane_incarnation_id",
            "lease_id",
            "holder_ref",
            "epoch",
            "expected_head",
            "expected_tree",
            "issued_at",
            "renewed_at",
            "path_scope",
            "expires_at",
            "payload_sha256",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    } == {
        name: lease[name]
        for name in (
            "lane_incarnation_id",
            "lease_id",
            "holder_ref",
            "epoch",
            "expected_head",
            "expected_tree",
            "issued_at",
            "renewed_at",
            "path_scope",
            "expires_at",
            "payload_sha256",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    }
    assert validate_schema_instance("workspace-status.schema.json", status, root=repo) == {
        "verdict": "pass",
        "required_gaps": [],
    }


@pytest.mark.parametrize("commitment", [False, True], ids=["head", "commitment"])
def test_start_work_lane_blocks_source_generation_drift(
    tmp_path: Path, *, commitment: bool
) -> None:
    case = LaneStartCase.create(tmp_path, holder=_HOLDER)
    case.commit_source_drift(commitment=commitment)

    report = case.start(holder=_HOLDER)

    assert report["required_gaps"] == ["source_lease_head_mismatch"]
    case.assert_absent()


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

    assert report["required_gaps"] == ["openspec_active_change_unarchived:stale:candidate"]
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

    assert report["verdict"] == "block"
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

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["candidate_head_changed_during_lane_start"]
    assert "work/feature" not in leases_by_branch(repo)
    assert ref_head(repo, "work/feature") == ""
    assert not target.exists()


def test_work_lane_status_keeps_committed_binding_and_blocks_dirty_rewrite(tmp_path: Path) -> None:
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
    assert report["verdict"] == "pass"
    commitment = target / "openspec" / "changes" / "fixture-change" / "commitment.toml"
    commitment.write_text(
        commitment.read_text(encoding="utf-8").replace(
            "Exercise the governed fixture lifecycle.",
            "Attempt to rewrite the immutable base.",
        ),
        encoding="utf-8",
    )

    status = workspace_status(target, include_foreign_path_scope=False)

    assert validate_schema_instance("workspace-status.schema.json", status, root=target) == {
        "verdict": "pass",
        "required_gaps": [],
    }
    assert status["closeout_support"]["commitment_binding"] == "bound"
    assert status["closeout_support"]["supported"] is False
    assert status["closeout_support"]["required_gaps"] == ["work_lane_dirty"]


@pytest.mark.parametrize(
    ("mutation", "expected_gap"),
    [
        ("dirty-root", "lane_start_requires_clean_accepted_root"),
        ("missing-carrier", "source_work_lane_invalid"),
        ("ambiguous-carrier", "source_work_lane_invalid"),
    ],
)
def test_start_work_lane_blocks_invalid_source_state_without_effects(
    tmp_path: Path, mutation: str, expected_gap: str
) -> None:
    case = LaneStartCase.create(tmp_path, holder=_HOLDER)
    if mutation == "dirty-root":
        (case.repo / "README.md").write_text("# dirty\n", encoding="utf-8")
    elif mutation == "missing-carrier":
        git(case.source, "rm", "-r", "openspec/changes/fixture-change")
    else:
        second = case.source / "openspec/changes/second"
        second.mkdir(parents=True)
        (second / "commitment.toml").write_text(
            'schema_version = 1\nid = "change:second"\nintent = "Second."\n'
            'subjects = ["repository:self"]\n',
            encoding="utf-8",
        )
        (second / "tasks.md").write_text("- [ ] Continue\n", encoding="utf-8")

    report = case.start(holder=_HOLDER)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [expected_gap]
    case.assert_absent()


def test_start_work_lane_rejects_invalid_actor_before_reserving_or_creating(
    tmp_path: Path,
) -> None:
    case = LaneStartCase.create(tmp_path, holder=_HOLDER)

    report = case.start(holder="invalid")

    assert report["required_gaps"] == ["holder_ref_invalid"]
    case.assert_absent()


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
        "verdict": "block",
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

    assert report["verdict"] == "block"
    assert report["state"] == "blocked"
    assert report["lease_state"] == "retained"
    assert report["required_gaps"] == [
        "lane_creation_compensation_failed",
        "lane_start_target_path_ownership_unknown",
    ]
    assert "work/feature" in leases_by_branch(repo)
    assert ref_head(repo, "work/feature")
    assert target.exists()
