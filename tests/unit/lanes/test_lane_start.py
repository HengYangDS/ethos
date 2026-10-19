"""Public Work Lane admission, creation, and exact resource compensation."""

from __future__ import annotations

import sqlite3
from collections import Counter
from contextlib import closing
from datetime import UTC
from datetime import datetime
from functools import partial

import pytest

import ethos.adapters.mutation.lane_lifecycle.start as lane_start
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.worktree_effects import remove_worktree
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.signature import configure_signer

HOLDER = "agent:test:case:lane-start"
COMMAND = "/runtime/python -B -I -m ethos.cli"
NOW = datetime.now(UTC)
BRANCH = f"work/{NOW:%Y%m%d}-feature"


class _StartClock(datetime):
    """Hold the lane date fixed so a run crossing UTC midnight keeps one lane identity."""

    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz)


@pytest.fixture
def start_case(tmp_path, monkeypatch):
    """Keep native Git/Lease effects while isolating package supply and the lane date."""
    repo, candidate = init_repo_with_candidate(tmp_path)
    target = repo.parent / f"{repo.name}-worktrees" / BRANCH.removeprefix("work/")
    monkeypatch.setattr(lane_start, "datetime", _StartClock)
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


@pytest.mark.parametrize("fail_hook", [False, True])
def test_historical_start_preserves_candidate_and_compensates_only_owned_state(
    start_case, tmp_path, monkeypatch, *, fail_hook
):
    """An exact trusted base is independent of today's candidate and governing runtime."""
    repo, candidate, target, start = start_case
    configure_signer(repo, tmp_path)
    git(repo, "-c", "commit.gpgsign=true", "commit", "--allow-empty", "-m", "test: signed base")
    base = git(repo, "rev-parse", "HEAD")
    git(candidate, "merge", "--ff-only", base)
    candidate_head = commit_fixture_file(candidate, "later.txt", "later\n", "later candidate")
    indexes = (git(repo, "write-tree"), git(candidate, "write-tree"))
    reflog = git(repo, "reflog", "show", "candidate/dev")
    planned = start(base=base)
    assert planned["state"] == "planned"
    assert planned["base_head"] == base
    assert f"--base {base}" in planned["next_action"]
    assert _observe(repo, target) == ("", False, None)
    if fail_hook:
        monkeypatch.setattr(lane_start, "install_hook_launchers", _failure)
    applied = start(base=base, apply=True)
    assert applied["state"] == ("blocked" if fail_hook else "started")
    assert ref_head(repo, "candidate/dev") == candidate_head
    assert (git(repo, "write-tree"), git(candidate, "write-tree")) == indexes
    assert git(repo, "reflog", "show", "candidate/dev") == reflog
    if fail_hook:
        assert applied["required_gaps"] == ["injected_failure"]
        assert _observe(repo, target) == ("", False, None)
        assert f"--base {base}" in applied["next_action"]
    else:
        assert ref_head(repo, BRANCH) == git(target, "rev-parse", "HEAD") == base
        resumed = start(base=base, apply=True)
        assert resumed["lease"]["generation"] == applied["lease"]["generation"]
        assert resumed["ref_attestation"] == {}


def test_explicit_unsigned_base_is_refused_before_lane_effects(start_case):
    """A discoverable native commit is not a trusted maintenance selection."""
    repo, _candidate, target, start = start_case
    git(repo, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "test: unsigned base")
    base = git(repo, "rev-parse", "HEAD")
    assert git(repo, "log", "-1", "--format=%G?", base) == "N"
    before = _observe(repo, target)
    result = start(base=base, apply=True)
    assert result["verdict"] == "block"
    assert result["required_gaps"]
    assert _observe(repo, target) == before


def test_historical_base_rechecks_current_trust_before_effects(start_case, tmp_path, monkeypatch):
    """Bootstrap cannot turn a former trusted observation into effect authority."""
    repo, _candidate, target, start = start_case
    configure_signer(repo, tmp_path)
    git(repo, "-c", "commit.gpgsign=true", "commit", "--allow-empty", "-m", "test: signed base")
    base = git(repo, "rev-parse", "HEAD")
    before = _observe(repo, target)
    monkeypatch.setattr(
        lane_start,
        "require_runtime_wheel_provenance",
        lambda: (tmp_path / "trust/allowed-signers").write_text(""),
    )
    result = start(base=base, apply=True)
    assert result["verdict"] == "block"
    assert result["required_gaps"]
    assert _observe(repo, target) == before


def test_historical_base_obeys_current_identity_not_its_old_policy(start_case, tmp_path):
    """A trusted key cannot bypass the current repository's explicit attribution rule."""
    repo, _candidate, target, start = start_case
    configure_signer(repo, tmp_path)
    git(repo, "-c", "commit.gpgsign=true", "commit", "--allow-empty", "-m", "test: signed base")
    base = git(repo, "rev-parse", "HEAD")
    commit_fixture_file(
        repo,
        ".ethos/workspace.toml",
        '[commit_policy]\nsubject_pattern = ".*"\nsigning_required = true\n'
        'signing_format = "ssh"\n[commit_policy.author]\n'
        'name = "Required Author"\nemail = "required@example.invalid"\n',
        "current identity contract",
    )
    before = _observe(repo, target)
    result = start(base=base, apply=True)
    assert result["verdict"] == "block"
    assert any("commit_author_identity_mismatch" in gap for gap in result["required_gaps"])
    assert _observe(repo, target) == before


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


def test_identical_start_after_compensated_failure_retains_every_effect(start_case, monkeypatch):
    repo, candidate, target, start = start_case
    outcomes = iter(("injected_failure", "injected_failure", ""))

    def projection(_root):
        if failure := next(outcomes):
            raise ValueError(failure)
        return {"state": "current"}

    monkeypatch.setattr(lane_start, "install_hook_launchers", projection)
    reports = [start(apply=True) for _ in range(3)]
    assert [report["required_gaps"] for report in reports] == [["injected_failure"]] * 2 + [[]]
    assert _observe(repo, target)[:2] == (git(candidate, "rev-parse", "HEAD"), True)
    assert leases_by_branch(repo)[BRANCH]["holder_ref"] == HOLDER
    recorded = Counter(
        (item.payload.body["plan"]["policy"]["transition"], item.plan_digest)
        for item in read_attestation_set(repo)[1]
    )
    assert recorded[("lane.start", reports[2]["ref_attestation"]["plan_digest"])] == 3
    assert sorted(recorded.values()) == [2, 3]


def test_retired_lane_starts_again_under_the_same_name_and_head(start_case):
    repo, _candidate, target, start = start_case
    first = start(apply=True)
    head, lease = first["head"], leases_by_branch(repo)[BRANCH]
    remove_worktree(repo, target, branch=BRANCH, head=head, force=False)
    revoke = LeaseOperationRequest(
        operation="revoke",
        branch=BRANCH,
        holder_ref=HOLDER,
        generation=integer_value(lease["generation"]),
        expires_at=str(lease["expires_at"]),
        apply=True,
    )
    revoke_lease(state_database(repo), request=revoke)
    retirement = GitEffect(
        updates={f"refs/heads/{BRANCH}": GitRefUpdate(expected=head, desired="0" * len(head))},
        assertions={"refs/heads/dev": head},
    )
    policy = {"operation": "lane.retire", "subject": BRANCH}
    plan = compile_observed_git_effect(repo, None, retirement, head=head, policy=policy)
    execute_git_effect(repo, plan, issuer=HOLDER)
    second = start(apply=True)
    assert second["required_gaps"] == []
    assert second["ref_attestation"]["plan_digest"] == first["ref_attestation"]["plan_digest"]
    assert second["ref_attestation"]["id"] != first["ref_attestation"]["id"]
    assert _observe(repo, target)[:2] == (head, True)
    assert leases_by_branch(repo)[BRANCH]["holder_ref"] == HOLDER


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


@pytest.mark.parametrize("mode", ["canonical", "noncanonical"])
def test_start_places_every_work_lane_in_a_dated_sibling_worktree(start_case, mode):
    """Without any declaration, a lane lives at `<repository>-worktrees/<yyyymmdd>-<slug>/`."""
    repo, _candidate, target, start = start_case
    elsewhere = repo.parent / "repo-work-semantic-lane"
    report = start(name="semantic lane", path=elsewhere if mode == "noncanonical" else None)
    if mode == "canonical":
        lane_id = f"{NOW:%Y%m%d}-semantic-lane"
        assert report["branch"] == f"work/{lane_id}"
        assert report["path"] == (repo.parent / f"{repo.name}-worktrees" / lane_id).as_posix()
    else:
        assert report["required_gaps"] == ["work_lane_path_not_canonical"]
    assert _observe(repo, target) == ("", False, None)


def test_start_names_the_lane_family_after_the_canonical_checkout(start_case):
    """An accepted root checked out beside the canonical checkout shares its lane family."""
    repo, _candidate, _target, start = start_case
    accepted = repo.parent / "repo-accepted"
    git(repo, "switch", "-q", "-c", "main")
    git(repo, "worktree", "add", "-q", accepted.as_posix(), "dev")

    report = start(root=accepted, name="semantic lane", path=None)

    lane_id = f"{NOW:%Y%m%d}-semantic-lane"
    assert report["path"] == (repo.parent / "repo-worktrees" / lane_id).as_posix()
    assert not (repo.parent / "repo-accepted-worktrees").exists()


@pytest.mark.parametrize("name", ["20261016-archive-relocation", "12345678-ticket", "relocation"])
def test_start_refuses_a_name_that_already_carries_a_lane_date(start_case, name):
    """No lane path repeats its date: a dated name is refused with its undated slug."""
    repo, _candidate, _target, start = start_case
    report = start(name=name, path=None)
    lane_id = f"{NOW:%Y%m%d}-{name}"
    if not name.startswith("2026"):
        # Eight digits that are not a calendar date are part of the name itself.
        assert (report["state"], report["branch"]) == ("planned", f"work/{lane_id}")
        return
    assert report["required_gaps"] == ["work_lane_name_dated"]
    assert report["undated_name"] == "archive-relocation"
    assert report["next_action"] == (
        f"ethos lane start archive-relocation --holder-ref {HOLDER} --root {repo.as_posix()} --json"
    )
    assert ref_head(repo, f"work/{lane_id}") == ""
    assert not (repo.parent / f"{repo.name}-worktrees" / lane_id).exists()
    assert f"work/{lane_id}" not in leases_by_branch(repo)


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
        target.mkdir(parents=True)
        (target / "user.txt").write_text("keep\n")
        gap = "lane_start_target_path_exists"
    before = _observe(repo, target)
    result = start(apply=True)
    assert result["required_gaps"] == [gap]
    assert _observe(repo, target) == before
    if boundary == "target_path":
        assert (target / "user.txt").read_text() == "keep\n"
