"""Public Work Lane admission, creation, and exact resource compensation."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from functools import partial

import pytest

import ethos.adapters.mutation.lane_lifecycle.start as lane_start
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

HOLDER = "agent:test:case:lane-start"
COMMAND = "/runtime/python -B -I -m ethos.cli"
BRANCH = "work/feature"


@pytest.fixture
def start_case(tmp_path, monkeypatch):
    """Keep native Git/Lease effects while isolating package supply."""
    repo, candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-feature"
    monkeypatch.setattr(lane_start, "require_runtime_wheel_provenance", lambda: None)
    monkeypatch.setattr(lane_start, "runtime_command", lambda _root: COMMAND)
    monkeypatch.setattr(lane_start, "install_hook_launchers", lambda _root: {"state": "current"})
    start = partial(
        lane_start.start_work_lane, root=repo, name="feature", path=target, holder_ref=HOLDER
    )
    return repo, candidate, target, start


def _failure(*_args, message="injected_failure", **_kwargs):
    raise ValueError(message)


def _observe(repo, target):
    return ref_head(repo, BRANCH), target.exists(), leases_by_branch(repo).get(BRANCH)


@pytest.mark.parametrize("advance_accepted", [False, True])
def test_start_preserves_candidate_identity_minimal_lease_and_exact_bootstrap(
    start_case, advance_accepted
):
    repo, candidate, target, start = start_case
    head = git(candidate, "rev-parse", "HEAD")
    accepted = (
        commit_fixture_file(repo, "accepted-only.txt", "accepted advances\n", "advance accepted")
        if advance_accepted
        else head
    )
    before = _observe(repo, target)
    planned = start()
    assert planned["state"] == "planned"
    assert _observe(repo, target) == before == ("", False, None)
    bootstrap = planned["runner_bootstrap"]
    assert bootstrap == {
        "command": COMMAND,
        "environment_scope": "git_common_package_runtime",
        "next_action": f"{COMMAND} status --root {target.as_posix()} --json",
    }
    assert "uv run" not in bootstrap["next_action"]
    first = start(apply=True)
    second = start(apply=True)
    assert first["verdict"] == second["verdict"] == "pass"
    assert first["head"] == first["base_head"] == second["head"] == head
    assert git(target, "rev-parse", "HEAD") == head
    assert git(target, "status", "--short") == ""
    assert tuple(repo.parent.rglob("commitment.toml")) == ()
    lease = leases_by_branch(repo)[BRANCH]
    assert set(lease) == {
        "subject",
        "lease_state",
        "lane_ref",
        "holder_ref",
        "generation",
        "expires_at",
    }
    assert (lease["lane_ref"], lease["holder_ref"], lease["generation"]) == (BRANCH, HOLDER, 1)
    assert first["lease"] == second["lease"]
    assert first["ref_attestation"]["commitment_digest"] is None
    body = first["ref_attestation"]["payload"]["body"]
    assert body["plan"]["facts"]["head"] == body["input"]["head"] == accepted
    assert second["ref_attestation"] == {}


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize(
    "failure_at", ["require_runtime_wheel_provenance", "install_hook_launchers", "holder"]
)
def test_failed_start_only_compensates_resources_created_by_this_invocation(
    start_case, monkeypatch, existing, failure_at
):
    repo, _candidate, target, start = start_case
    if existing:
        assert start(apply=True)["verdict"] == "pass"
        (target / "uncommitted.txt").write_text("preserve existing user content\n")
    before = _observe(repo, target)
    removed = []
    native_remove = lane_start.remove_worktree

    def remove(root, path, **kwargs):
        removed.append((path, kwargs))
        return native_remove(root, path, **kwargs)

    monkeypatch.setattr(lane_start, "remove_worktree", remove)
    if failure_at == "holder":
        result = start(apply=True, holder_ref="agent:test:case:foreign" if existing else "invalid")
    else:
        monkeypatch.setattr(lane_start, failure_at, _failure)
        result = start(apply=True)
    assert result["verdict"] == "block"
    gap = (
        (f"lease_holder_mismatch:{BRANCH}" if existing else "holder_ref_invalid")
        if failure_at == "holder"
        else "injected_failure"
    )
    assert result["required_gaps"] == [gap]
    assert _observe(repo, target) == before
    if existing:
        assert (target / "uncommitted.txt").read_text() == "preserve existing user content\n"
    if not existing and failure_at == "install_hook_launchers":
        assert removed == [
            (target, {"branch": BRANCH, "head": ref_head(repo, "candidate/dev"), "force": False})
        ]
    else:
        assert removed == []


@pytest.mark.parametrize(
    "failure",
    [
        "missing_receipt",
        "missing_receipt_with_content",
        "dirty",
        "remove",
        "lease",
        "expiry",
        "ref",
    ],
)
def test_unreceipted_worktree_creation_is_retained_for_recovery(start_case, monkeypatch, failure):
    repo, _candidate, target, start = start_case
    native_add = lane_start.add_worktree

    def interrupted(*args, **kwargs):
        native_add(*args, **kwargs)
        if failure == "missing_receipt_with_content":
            (target / "retained.txt").write_text("unowned residue\n")
        message = "worktree_receipt_unavailable"
        raise ValueError(message)

    def failed_hook(_root):
        if failure == "dirty":
            (target / "retained.txt").write_text("unowned residue\n")
        if failure == "expiry":
            with closing(sqlite3.connect(lane_start.state_database(repo))) as conn, conn:
                conn.execute(
                    "update leases set expires_at = ? where lane_ref = ?",
                    ("2999-01-01T00:00:00+00:00", BRANCH),
                )
        _failure()

    monkeypatch.setattr(lane_start, "install_hook_launchers", failed_hook)
    if failure.startswith("missing_receipt"):
        monkeypatch.setattr(lane_start, "add_worktree", interrupted)
    elif failure in {"remove", "lease", "ref"}:
        monkeypatch.setattr(
            lane_start,
            {"remove": "remove_worktree", "lease": "revoke_lease", "ref": "_delete_started_ref"}[
                failure
            ],
            _failure,
        )
    worktree_retained = failure in {
        "missing_receipt",
        "missing_receipt_with_content",
        "dirty",
        "remove",
    }
    lease_retained = failure != "ref"
    report = start(apply=True)
    resource = "worktree" if worktree_retained else "lease" if lease_retained else "ref"
    assert report["required_gaps"] == [
        "worktree_receipt_unavailable"
        if failure.startswith("missing_receipt")
        else "injected_failure",
        f"lane_start_{resource}_cleanup_failed",
    ]
    assert _observe(repo, target)[:2] == (ref_head(repo, "candidate/dev"), worktree_retained)
    assert (BRANCH in leases_by_branch(repo)) is lease_retained
    if failure == "expiry":
        assert leases_by_branch(repo)[BRANCH]["expires_at"] == "2999-01-01T00:00:00+00:00"
    if failure in {"missing_receipt_with_content", "dirty"}:
        assert (target / "retained.txt").read_text() == "unowned residue\n"


@pytest.mark.parametrize("mode", ["canonical", "noncanonical", "prefix"])
def test_start_honors_repository_topology_without_parallel_lanes(start_case, mode):
    repo, _candidate, target, start = start_case
    prefix = 'work_branch_prefix = "topic/"\n' if mode == "prefix" else ""
    commit_fixture_file(
        repo,
        ".ethos/workspace.toml",
        "[branch_roles]\ncanonical_sibling_worktrees = true\n" + prefix,
        "configure Work Lanes",
    )
    report = start(name="semantic lane", path=target if mode == "noncanonical" else None)
    if mode == "canonical":
        lane_id = report["branch"].removeprefix("work/")
        assert lane_id.endswith("-semantic-lane")
        assert report["path"] == (repo.parent / f"{repo.name}-worktrees" / lane_id).as_posix()
    else:
        gap = (
            "work_lane_path_not_canonical"
            if mode == "noncanonical"
            else "repository_family_profile_requires_work_branch_prefix"
        )
        assert report["required_gaps"] == [gap]
    assert _observe(repo, target) == ("", False, None)


@pytest.mark.parametrize(
    "boundary",
    [
        "runtime",
        "accepted_dirty",
        "candidate_missing",
        "projection_missing",
        "candidate_dirty",
        "target_ref",
        "target_path",
    ],
)
def test_start_rejects_invalid_preconditions_without_effects(start_case, monkeypatch, boundary):
    repo, candidate, target, start = start_case
    if boundary == "runtime":
        gap = "hook_runtime_current_missing"
        monkeypatch.setattr(lane_start, "runtime_command", partial(_failure, message=gap))
    elif boundary in {"accepted_dirty", "candidate_dirty"}:
        (repo if boundary == "accepted_dirty" else candidate).joinpath("dirty.txt").write_text(
            "keep\n"
        )
        gap = (
            "lane_start_requires_clean_accepted_root"
            if boundary == "accepted_dirty"
            else "candidate_worktree_dirty"
        )
    elif boundary in {"candidate_missing", "projection_missing"}:
        git(repo, "worktree", "remove", candidate.as_posix())
        if boundary == "candidate_missing":
            git(repo, "branch", "-D", "candidate/dev")
        gap = (
            "candidate_branch_missing"
            if boundary == "candidate_missing"
            else "candidate_worktree_missing"
        )
    elif boundary == "target_ref":
        head = commit_fixture_file(repo, "new.txt", "new\n", "new commit")
        git(repo, "update-ref", f"refs/heads/{BRANCH}", head)
        gap = "lane_start_target_ref_exists"
    else:
        target.mkdir()
        (target / "user.txt").write_text("keep\n")
        gap = "lane_start_target_path_exists"
    before = _observe(repo, target)
    result = start(apply=True)
    assert result["required_gaps"] == [gap]
    assert _observe(repo, target) == before
    if boundary == "target_path":
        assert (target / "user.txt").read_text() == "keep\n"
