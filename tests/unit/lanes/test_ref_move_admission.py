"""Accepted-ref move admission — the reference-transaction boundary.

`ref_move_admission_report` is the reducer bound to git's reference-transaction hook:
it decides whether a LOCAL ref update (merge/reset/branch -f/commit) to a protected
role may proceed. The candidate train's load-bearing invariant is that the accepted
branch only ever advances to the LIVE candidate head, by a fast-forward, carrying a
complete executed proof. These tests hold that boundary — the raw-git escapes it must
block and the sanctioned closeout path it must still admit — split out of
test_hook_admission.py so each file stays a cohesive, bounded contract suite.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
from contextlib import closing
from datetime import timedelta
from pathlib import Path

import pytest

import ethos.adapters.admission.git_admission as git_admission
import ethos.adapters.admission.transitions as transitions
from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.admission.git_admission import ref_move_admission_report
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.gates import resolve_gate_policy
from tests.support.contract_helpers import commit_active_commitment
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import conformant_proof_check
from tests.support.contract_helpers import exact_lease
from tests.support.contract_helpers import render_branch_policy
from tests.support.contract_helpers import seed_executed_proof
from tests.support.contract_helpers import start_adopted_work_lane
from tests.support.contract_helpers import write_active_commitment
from tests.support.contract_helpers import write_publication_topology
from tests.support.contract_helpers import write_role_policy
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

_FIXTURE_COMMITMENT_CARRIER = "openspec/changes/fixture-change/commitment.toml"
_HOLDER = "agent:codex:thread:first"


def _acquire_fixture_lease(repo: Path, branch: str, head: str, holder: str):
    return acquire_lease(
        state_database(repo),
        lease=exact_lease(
            repo=repo,
            branch=branch,
            holder_ref=holder,
            expected_head=head,
            carrier=_FIXTURE_COMMITMENT_CARRIER,
        ),
    )


def _leased_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = init_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    candidate = tmp_path / "repo-candidate"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    lane = tmp_path / "repo-work-current"
    git(repo, "worktree", "add", "-b", "work/current", lane.as_posix(), "dev")
    head = git(lane, "rev-parse", "HEAD")
    lease = _acquire_fixture_lease(repo, "work/current", head, _HOLDER)
    monkeypatch.setenv("ETHOS_ACTOR", _HOLDER)
    return repo, candidate, lane, head, lease


def _poison_lease(database: Path, branch: str, lease: dict[str, object]) -> str:
    payload = dict(lease["payload"])
    payload["retired_field"] = "retired"
    raw = json.dumps(payload, sort_keys=True)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("update leases set payload_json = ? where subject = ?", (raw, branch))
        connection.commit()
    return raw


@pytest.mark.parametrize(
    ("old_value", "new_value"),
    [
        ("a" * 40, "0" * 40),
        ("a" * 64, "0" * 64),
        ("0" * 40, "a" * 40),
        ("0" * 64, "a" * 64),
    ],
)
def test_work_lane_ref_transition_rejects_zero_oid_without_lease(
    tmp_path: Path, old_value: str, new_value: str
) -> None:
    repo = init_repo(tmp_path / "repo")
    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name="refs/heads/work/doomed",
        old_value=old_value,
        new_value=new_value,
    )

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["required_gaps"] == ["work_lane_missing_lease:work/doomed"]


def test_work_lane_ref_creation_requires_exact_lease_and_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    branch = "work/zero-bound"
    head = git(repo, "rev-parse", "HEAD")
    _acquire_fixture_lease(repo, branch, head, "agent:test:case:zero-bound")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:zero-bound")

    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name=f"refs/heads/{branch}",
        old_value="0" * 40,
        new_value=head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["work_lane_ref_create_no_ref_intent"]
    update = GitRefUpdate(expected="0" * 40, desired=head)
    intent = write_ref_intent(
        root=repo,
        ref_name=f"refs/heads/{branch}",
        update=update,
        operation="lane.import",
        plan_digest=canonical_json_digest({"operation": "lane.import"}),
    )
    admitted = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name=f"refs/heads/{branch}",
        old_value=update.expected,
        new_value=update.desired,
    )

    assert admitted["verdict"] == "pass"
    assert admitted["decision"] == {"action": "allow", "reason": "lane_creation_saga_started"}
    assert intent["nonce"]


def test_work_lane_ref_deletion_requires_ref_intent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    branch = "work/zero-bound"
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", branch, head)
    database = state_database(repo)
    _acquire_fixture_lease(repo, branch, head, "agent:test:case:zero-bound")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:zero-bound")

    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name=f"refs/heads/{branch}",
        old_value=head,
        new_value="0" * 40,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["work_lane_ref_delete_no_ref_intent"]
    assert git(repo, "rev-parse", branch) == head
    assert observe_lease(database, branch).state == "valid"


@pytest.mark.parametrize("case", ["create", "delete"])
def test_work_lane_ref_transition_committed_accepts_observed_zero_oid_terminal_state(
    tmp_path: Path,
    case: str,
) -> None:
    repo = init_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    branch = "work/terminal"
    if case == "create":
        git(repo, "branch", branch, head)
    report = work_lane_ref_transition_report(
        root=repo,
        phase="committed",
        ref_name=f"refs/heads/{branch}",
        old_value="0" * 40 if case == "create" else head,
        new_value=head if case == "create" else "0" * 40,
    )

    assert report["verdict"] == "pass"
    assert report["state"] == "admitted"
    assert report["decision"] == {
        "action": "allow",
        "reason": "lane_ref_terminal_state_observed",
    }


def test_work_lane_zero_oid_unknown_lease_is_observe_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    branch = "work/unknown-create"
    head = git(repo, "rev-parse", "HEAD")
    database = state_database(repo)
    lease = _acquire_fixture_lease(repo, branch, head, "agent:test:case:unknown-create")
    raw_payload = _poison_lease(database, branch, lease)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:unknown-create")

    report = work_lane_ref_transition_report(
        root=repo,
        phase="committed",
        ref_name=f"refs/heads/{branch}",
        old_value="0" * 40,
        new_value=head,
    )

    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == [f"work_lane_lease_unknown:{branch}"]
    with closing(sqlite3.connect(database)) as connection:
        stored = connection.execute(
            "select payload_json from leases where subject = ?", (branch,)
        ).fetchone()[0]
    assert stored == raw_payload


@pytest.mark.parametrize("width", [0, 1, 39, 41, 63, 65])
def test_work_lane_ref_transition_rejects_invalid_oid(tmp_path: Path, width: int) -> None:
    repo = init_repo(tmp_path / "repo")
    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name="refs/heads/work/doomed",
        old_value="a" * (width or 40),
        new_value="0" * width,
    )
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["work_lane_ref_oid_invalid"]


def test_work_lane_ref_transition_admits_noop_without_lease(tmp_path: Path) -> None:
    """A worktree setup can reassert a just-created lane ref at its existing HEAD before
    the lane lease is recorded.  This is no state transition and must not be blocked by
    the lease guard."""
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "work/starting", "dev")
    head = git(repo, "rev-parse", "work/starting")

    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name="refs/heads/work/starting",
        old_value=head,
        new_value=head,
    )

    assert report["verdict"] == "pass"
    assert report["decision"] == {"action": "allow", "reason": "lane_ref_noop"}


def test_work_lane_ref_transition_prepared_checks_holder_generation_and_old_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo, candidate, lane, head, _lease = _leased_lane(tmp_path, monkeypatch)
    target = _advance_candidate(candidate, "target")

    def unexpected_workspace_status(_root: Path) -> dict[str, object]:
        message = "work-lane ref transition must not build full workspace status"
        raise AssertionError(message)

    monkeypatch.setattr(transitions, "workspace_status", unexpected_workspace_status, raising=False)

    report = transitions.work_lane_ref_transition_report(
        root=lane,
        phase="prepared",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=target,
    )
    assert report["verdict"] == "pass"
    assert report["decision"]["action"] == "allow"
    assert report["lease"]["epoch"] == 1

    stale = transitions.work_lane_ref_transition_report(
        root=lane,
        phase="prepared",
        ref_name="refs/heads/work/current",
        old_value="c" * 40,
        new_value=target,
    )
    assert stale["verdict"] == "block"
    assert stale["required_gaps"] == [f"lane_ref_observation_stale:{'c' * 40}!={head}"]


def test_work_lane_ref_transition_committed_advances_local_lease_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, lane, head, _lease = _leased_lane(tmp_path, monkeypatch)
    new_head = _advance_candidate(candidate, "target")
    git(repo, "update-ref", "refs/heads/work/current", new_head, head)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=new_head,
    )
    assert report["verdict"] == "pass"
    assert report["state"] == "lease_ref_advanced"
    assert report["lease"]["expected_head"] == new_head
    assert report["lease"]["expected_tree"] == git(repo, "rev-parse", f"{new_head}^{{tree}}")


def test_work_lane_ref_transition_rebinds_one_exact_carrier_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, lane, head, initial = _leased_lane(tmp_path, monkeypatch)
    relocated = "records/fixture-change/commitment.toml"
    (candidate / relocated).parent.mkdir(parents=True)
    git(candidate, "mv", _FIXTURE_COMMITMENT_CARRIER, relocated)
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "relocate commitment carrier",
    )
    target = git(candidate, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/heads/work/current", target, head)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=target,
    )

    assert report["verdict"] == "pass", report
    assert report["state"] == "lease_ref_advanced"
    rebound = report["lease"]
    assert rebound["expected_head"] == target
    assert rebound["expected_tree"] == git(repo, "rev-parse", f"{target}^{{tree}}")
    assert rebound["base_commitment_path"] == relocated
    assert rebound["base_commitment_bytes_sha256"] == initial["base_commitment_bytes_sha256"]
    assert rebound["base_commitment_digest"] == initial["base_commitment_digest"]
    assert rebound["payload_sha256"] != initial["payload_sha256"]
    assert {
        name for name in initial["payload"] if initial["payload"][name] != rebound["payload"][name]
    } == {"expected_head", "expected_tree", "base_commitment_path"}


@pytest.mark.parametrize("case", ["content_change", "non_unique"])
def test_work_lane_ref_transition_rejects_inexact_carrier_relocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    repo, candidate, lane, head, initial = _leased_lane(tmp_path, monkeypatch)
    relocated = candidate / "records/fixture-change/commitment.toml"
    relocated.parent.mkdir(parents=True)
    git(candidate, "mv", _FIXTURE_COMMITMENT_CARRIER, relocated.relative_to(candidate).as_posix())
    if case == "non_unique":
        duplicate_path = candidate / "records/fixture-change-copy/commitment.toml"
        duplicate_path.parent.mkdir(parents=True)
        shutil.copyfile(relocated, duplicate_path)
        git(candidate, "add", duplicate_path.relative_to(candidate).as_posix())
    else:
        relocated.write_text(
            relocated.read_text(encoding="utf-8").replace(
                "Exercise the governed fixture lifecycle.",
                "Rewrite the governed fixture lifecycle.",
            ),
            encoding="utf-8",
        )
        git(candidate, "add", relocated.relative_to(candidate).as_posix())
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "relocate commitment carrier inexactly",
    )
    target = git(candidate, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/heads/work/current", target, head)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=target,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lease_base_commitment_path_mismatch"]
    stored = leases_by_branch(lane)["work/current"]
    assert (stored["expected_head"], stored["expected_tree"], stored["base_commitment_path"]) == (
        initial["expected_head"],
        initial["expected_tree"],
        initial["base_commitment_path"],
    )
    assert stored["payload_sha256"] == initial["payload_sha256"]


def test_work_lane_ref_transition_committed_rejects_unmoved_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, lane, head, _lease = _leased_lane(tmp_path, monkeypatch)
    new_head = _advance_candidate(candidate, "target")

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=new_head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [f"lane_ref_observation_stale:{new_head}!={head}"]
    lease = leases_by_branch(lane)["work/current"]
    assert (lease["expected_head"], lease["expected_tree"]) == (
        head,
        git(repo, "rev-parse", f"{head}^{{tree}}"),
    )


def test_work_lane_ref_transition_blocks_target_with_rewritten_base_commitment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, lane, head, _lease = _leased_lane(tmp_path, monkeypatch)
    commitment = candidate / "openspec" / "changes" / "fixture-change" / "commitment.toml"
    commitment.write_text(
        commitment.read_text(encoding="utf-8").replace(
            "Exercise the governed fixture lifecycle.",
            "Rewrite the governed fixture lifecycle.",
        ),
        encoding="utf-8",
    )
    git(candidate, "add", commitment.relative_to(candidate).as_posix())
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "rewrite base commitment",
    )
    target = git(candidate, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/heads/work/current", target, head)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=target,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lease_base_commitment_bytes_mismatch"]
    assert leases_by_branch(lane)["work/current"]["expected_head"] == head


def test_work_lane_ref_transition_rejects_unknown_lease_without_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _candidate, lane, head, lease = _leased_lane(tmp_path, monkeypatch)
    database = state_database(repo)
    _poison_lease(database, "work/current", lease)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="prepared",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value="b" * 40,
    )

    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == ["work_lane_lease_unknown:work/current"]


def _record_complete_proof(root: Path, head: str, *, changed_paths: tuple[str, ...] = ()) -> None:
    branch = git(root, "branch", "--show-current")
    holder = str(leases_by_branch(root).get(branch, {}).get("holder_ref") or "")
    original = os.environ.get("ETHOS_ACTOR")
    if holder:
        os.environ["ETHOS_ACTOR"] = holder
    try:
        plan = proof_plan(root, head=head, changed_paths=changed_paths)
        checks = tuple(
            conformant_proof_check(gate_id, root, tree_ref=head)
            for gate_id in resolve_gate_policy(root, tree_ref=head).gate_ids
        )
        attestation = issue_proof_attestation(
            root,
            {
                "plan": plan,
                "checks": checks,
                "verdict": "pass",
                "issuer": "agent:test:case:ref-move",
                "scope": "repository",
                "boundary": "repository",
            },
        )
        persist_proof_attestation(root, attestation)
    finally:
        if original is None:
            os.environ.pop("ETHOS_ACTOR", None)
        else:
            os.environ["ETHOS_ACTOR"] = original


def _accepted_boundary_repo(
    tmp_path: Path, *, release_mirror: str = "independent"
) -> tuple[Path, str]:
    """A repo on dev with a candidate/dev branch; return (root, base_head).

    Later commits are made on candidate/dev so the accepted branch (dev) can be
    probed for out-of-band advances to candidate-contained commits.
    """

    def g(*a: str) -> str:
        return subprocess.run(
            ["git", *a], cwd=tmp_path, capture_output=True, text=True, check=False
        ).stdout.strip()

    g("init", "-q", "-b", "dev")
    g("config", "user.name", "t")
    g("config", "user.email", "t@e.x")
    adoption_plan(tmp_path, apply=True)
    write_role_policy(
        tmp_path,
        candidate_branch="candidate/dev",
        work_branch_prefix="work/",
        proposal_branch_prefix="proposal/",
        release_mirror=release_mirror,
    )
    write_publication_topology(tmp_path)
    write_active_commitment(tmp_path)
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.write_text(
        profile.read_text(encoding="utf-8")
        + """
[proof]
code_correctness_gates = ["sample-tests", "sample-static"]

[proof.code_correctness_map]
behavior = "sample-tests"
static-analysis = "sample-static"

[[proof.gates]]
id = "sample-tests"
kind = "test"
command = ["sample", "test"]
dimensions = ["test", "coverage"]
execution_mode = "subprocess"
evidence_class = "proof"
trust_bearing = true
tool_adapter = "repository-native"

[[proof.gates]]
id = "sample-static"
kind = "typing"
command = ["sample", "typecheck"]
dimensions = ["static-analysis"]
execution_mode = "subprocess"
evidence_class = "contract"
trust_bearing = true
tool_adapter = "repository-native"
""",
        encoding="utf-8",
    )
    g("add", ".")
    g("commit", "-q", "-m", "base")
    base = g("rev-parse", "HEAD")
    g("branch", "candidate/dev")
    g("checkout", "-q", "candidate/dev")
    return tmp_path, base


@pytest.mark.parametrize(
    ("accepted_policy", "candidate_policy", "main_revision"),
    [
        ("accepted_ff", "independent", "HEAD"),
        ("independent", "accepted_ff", "HEAD~1"),
    ],
)
def test_release_mirror_admission_uses_current_accepted_policy(
    tmp_path: Path, accepted_policy: str, candidate_policy: str, main_revision: str
) -> None:
    repo, _base = _accepted_boundary_repo(tmp_path, release_mirror=accepted_policy)
    git(repo, "branch", "main", git(repo, "rev-parse", main_revision))
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text(
        workspace.read_text(encoding="utf-8").replace(
            f'release_mirror = "{accepted_policy}"', f'release_mirror = "{candidate_policy}"'
        ),
        encoding="utf-8",
    )
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "change release mirror policy")
    candidate_head = git(repo, "rev-parse", "HEAD")
    _record_complete_proof(repo, candidate_head)
    if candidate_policy == "accepted_ff":
        git(repo, "branch", "-f", "dev", candidate_head)

    report = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/main",
        old_value=git(repo, "rev-parse", "main"),
        new_value=candidate_head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["release_mirror_ref_move_no_ref_intent"]


def _advance_candidate(repo: Path, name: str) -> str:
    """Commit `name` on candidate/dev and return the new candidate head."""
    (repo / name).write_text(name, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@e.x", "commit", "-m", name)
    return git(repo, "rev-parse", "HEAD")


def test_ref_move_admission_blocks_accepted_bypass(tmp_path: Path) -> None:
    """The candidate-train invariant is un-bypassable: advancing the accepted branch to
    a commit that candidate has not validated is blocked, so a raw `git merge --ff-only
    work/x dev` cannot skip candidate. A candidate-contained advance passes containment
    (proof is still separately required)."""

    def g(*a: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *a], cwd=tmp_path, capture_output=True, text=True, check=False
        )

    g("init", "-b", "dev")
    g("config", "user.name", "t")
    g("config", "user.email", "t@e.x")
    workspace = tmp_path / ".ethos/workspace.toml"
    workspace.parent.mkdir()
    workspace.write_text(
        render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="independent",
        ),
        encoding="utf-8",
    )
    (tmp_path / "a").write_text("1", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "base")
    base = g("rev-parse", "HEAD").stdout.strip()
    g("branch", "candidate/dev")
    g("checkout", "-b", "work/x")
    (tmp_path / "b").write_text("2", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "work")
    work = g("rev-parse", "HEAD").stdout.strip()

    # bypass: move dev to a work commit candidate never validated -> blocked
    blocked = ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/dev", old_value=base, new_value=work
    )
    assert blocked["verdict"] == "block"
    assert "accepted_advance_not_candidate_validated" in blocked["required_gaps"]

    # a move of a non-accepted (work) ref is admitted untouched
    lane = ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/work/x", old_value=base, new_value=work
    )
    assert lane["verdict"] == "pass"

    # candidate-first: once candidate contains the commit, containment passes
    g("checkout", "candidate/dev")
    g("merge", "--ff-only", "work/x")
    advanced = ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/dev", old_value=base, new_value=work
    )
    assert "accepted_advance_not_candidate_validated" not in advanced["required_gaps"]


def test_ref_move_admission_blocks_unproven_candidate_ref_move(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    write_role_policy(
        repo,
        candidate_branch="candidate/dev",
        work_branch_prefix="work/",
        proposal_branch_prefix="proposal/",
    )
    head = git(repo, "rev-parse", "HEAD")
    candidate_head = "c" * 40

    report = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/candidate/dev",
        old_value=head,
        new_value=candidate_head,
    )

    assert report["verdict"] == "block"
    assert report["state"] == "blocked"
    assert report["decision"] == {
        "action": "block",
        "reason": "protected_ref_move_not_proven",
    }
    assert any("proof" in str(gap) or "not_proven" in str(gap) for gap in report["required_gaps"])


def test_ref_move_admission_blocks_proven_candidate_move_without_land_intent(
    tmp_path: Path,
) -> None:
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, candidate_head)

    report = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/candidate/dev",
        old_value=base,
        new_value=candidate_head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["candidate_ref_move_no_ref_intent"]


@pytest.mark.parametrize("branch", ["candidate/dev", "dev", "main"])
def test_ref_move_policy_bootstraps_from_promoted_strict_control(
    branch: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old, new, accepted = "a" * 40, "b" * 40, "c" * 40
    policy = render_branch_policy(
        release_branch="main",
        accepted_branch="dev",
        candidate_branch="candidate/dev",
        work_branch_prefix="work/",
        proposal_branch_prefix="proposal/",
        release_mirror="accepted_ff",
    )
    legacy = policy.replace(
        'proposal_branch_prefix = "proposal/"',
        'submit_branch_prefix = "submit/"',
    )
    monkeypatch.setattr(
        git_admission,
        "committed_file_text",
        lambda _repo, revision, _path: {old: legacy, new: policy, accepted: legacy}.get(
            revision, ""
        ),
    )
    monkeypatch.setattr(
        git_admission,
        "git_stdout",
        lambda _repo, *_args: accepted,
    )

    resolved = git_admission.resolve_ref_move_policy(
        Path(),
        ref_name=f"refs/heads/{branch}",
        old_value=old,
        new_value=new,
    )

    assert resolved.proposal_branch_prefix == "proposal/"


def test_ref_move_policy_uses_valid_profile_defaults_without_workspace(tmp_path: Path) -> None:
    repo = tmp_path
    git(repo, "init", "-q", "-b", "dev")
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.invalid")
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text('profile_id = "adopter"\n', encoding="utf-8")
    git(repo, "add", ".ethos/profile.toml")
    git(repo, "commit", "-m", "adopt")
    old = git(repo, "rev-parse", "HEAD")
    (repo / "change.txt").write_text("change", encoding="utf-8")
    git(repo, "add", "change.txt")
    git(repo, "commit", "-m", "change")
    new = git(repo, "rev-parse", "HEAD")

    resolved = git_admission.resolve_ref_move_policy(
        repo,
        ref_name="refs/heads/work/example",
        old_value=old,
        new_value=new,
    )

    assert resolved == BranchRolePolicy()


def test_ref_move_admission_admits_candidate_rewind_to_accepted_contained(tmp_path: Path) -> None:
    """A candidate-branch move to a commit the accepted branch already contains (a
    refresh-from-accepted rewind) promotes no new work, so it is admitted WITHOUT a fresh
    proof — the exemption that keeps `ethos lane refresh-base` working once the
    ETHOS_ALLOW_REF_MOVE bypass is gone. `base` is on the accepted branch (dev)."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")

    write_ref_intent(
        root=repo,
        ref_name="refs/heads/candidate/dev",
        update=GitEffect(
            updates={
                "refs/heads/candidate/dev": GitRefUpdate(
                    expected=candidate_head,
                    desired=base,
                )
            }
        ).updates["refs/heads/candidate/dev"],
        operation="candidate.refresh",
        plan_digest=canonical_json_digest({"operation": "candidate.refresh"}),
    )
    report = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/candidate/dev",
        old_value=candidate_head,
        new_value=base,  # rewind candidate back onto accepted-contained base
    )

    assert report["verdict"] == "pass"


def test_ref_move_admission_blocks_rollback_to_old_proven_commit(tmp_path: Path) -> None:
    """B2: a raw rollback of dev to an older, still-proven, still-candidate-contained
    commit is a non-fast-forward and must block — accepted history only advances."""
    repo, _base = _accepted_boundary_repo(tmp_path)
    c1 = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, c1)
    c2 = _advance_candidate(repo, "c2")

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=c2, new_value=c1
    )

    assert report["verdict"] == "block"
    assert "accepted_ref_move_not_fast_forward" in report["required_gaps"]


def test_ref_move_admission_blocks_advance_to_non_head_intermediate(tmp_path: Path) -> None:
    """B3: advancing dev to a candidate-CONTAINED but non-head intermediate commit
    (fast-forward, proven) still bypasses closeout — only the live candidate head may
    be promoted, so it must block."""
    repo, base = _accepted_boundary_repo(tmp_path)
    c1 = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, c1)
    _c2 = _advance_candidate(repo, "c2")  # live candidate head is now c2

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=c1
    )

    assert report["verdict"] == "block"
    assert "accepted_ref_move_not_candidate_head" in report["required_gaps"]


def _write_matching_intent(repo: Path, *, old_value: str, new_value: str) -> None:
    """Write the exact one-shot marker after proof admission succeeds independently."""
    write_ref_intent(
        root=repo,
        ref_name="refs/heads/dev",
        update=GitEffect(
            updates={
                "refs/heads/dev": GitRefUpdate(
                    expected=old_value,
                    desired=new_value,
                )
            }
        ).updates["refs/heads/dev"],
        operation="candidate.accept",
        plan_digest=canonical_json_digest({"operation": "candidate.accept"}),
    )


def test_equivalent_proof_cannot_invalidate_matching_ref_intent(tmp_path: Path) -> None:
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, candidate_head)
    _write_matching_intent(repo, old_value=base, new_value=candidate_head)
    first = proof_attestation(repo, candidate_head)
    assert first is not None
    equivalent = Attestation.issue(
        first.model_dump(exclude={"id", "schema_version", "statement_digest"})
        | {"issued_at": first.issued_at + timedelta(seconds=1)}
    )
    persist_proof_attestation(repo, equivalent)

    report = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/dev",
        old_value=base,
        new_value=candidate_head,
    )

    assert report["verdict"] == "pass"


def test_distinct_proof_closures_block_ref_move_admission(
    tmp_path: Path,
) -> None:
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, candidate_head)
    _write_matching_intent(repo, old_value=base, new_value=candidate_head)
    _record_complete_proof(repo, candidate_head, changed_paths=("other-operation",))

    report = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/dev",
        old_value=base,
        new_value=candidate_head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["stale_binding"]


def test_ref_move_admission_admits_official_closeout_with_intent_marker(
    tmp_path: Path,
) -> None:
    """B7 happy path (self-harm guard): a fast-forward of dev to the live candidate head
    carrying a complete executed proof AND a matching ref-intent marker is exactly
    what official closeout produces — it must be admitted with no boundary gaps, or the
    moat would deadlock the sanctioned path."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")  # c1 IS the live candidate head
    _record_complete_proof(repo, candidate_head)
    _write_matching_intent(repo, old_value=base, new_value=candidate_head)

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []


def test_ref_move_admission_blocks_raw_move_without_ref_intent(tmp_path: Path) -> None:
    """B1 (the load-bearing nail): a raw `git update-ref refs/heads/dev <candidate_head>
    <old>` is byte-identical to official closeout's CAS — fast-forward, == live candidate
    head, complete proof — yet carries NO ref-intent marker. Without the marker it
    must block, or raw git could promote a proven candidate head bypassing closeout."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, candidate_head)

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert report["verdict"] == "block"
    assert "accepted_ref_move_no_ref_intent" in report["required_gaps"]


def test_ref_move_admission_blocks_reused_ref_intent(tmp_path: Path) -> None:
    """B6: the marker is one-shot. Once admission consumes it, a second identical move
    finds no marker and blocks — a nonce cannot authorize two promotions."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, candidate_head)
    _write_matching_intent(repo, old_value=base, new_value=candidate_head)

    first = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )
    committed = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/dev",
        old_value=base,
        new_value=candidate_head,
        phase="committed",
    )
    second = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert first["verdict"] == "pass"
    assert committed["verdict"] == "pass"
    assert second["verdict"] == "block"
    assert second["required_gaps"] == ["ref_intent_reused"]


def test_ref_move_admission_blocks_mismatched_ref_intent(tmp_path: Path) -> None:
    """B4: a marker whose old/new binding does not match the actual ref move is refused
    (a marker minted for a different transition cannot authorize this one)."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, candidate_head)
    # Marker binds a different old_value than the actual move.
    _write_matching_intent(repo, old_value="0" * 40, new_value=candidate_head)

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert report["verdict"] == "block"
    assert "ref_intent_mismatch" in report["required_gaps"]


def test_ref_move_admission_blocks_stale_ref_intent(tmp_path: Path) -> None:
    """B5: an expired marker is refused (TTL bounds how long a written intent stays
    admissible, so a crashed closeout's residue cannot be reused later)."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, candidate_head)
    _write_matching_intent(repo, old_value=base, new_value=candidate_head)
    _backdate_markers(repo)

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert report["verdict"] == "block"
    assert "ref_intent_stale" in report["required_gaps"]


def _backdate_markers(repo: Path) -> None:
    """Expire every ref-intent marker by rewriting expires_at into the past."""
    marker_dir = ref_intent_dir(repo)
    for path in marker_dir.glob("*.json"):
        marker = json.loads(path.read_text(encoding="utf-8"))
        marker["expires_at"] = "2000-01-01T00:00:00+00:00"
        path.write_text(json.dumps(marker), encoding="utf-8")


def test_reference_transaction_hook_fails_closed_on_governed_branches(tmp_path: Path) -> None:
    """The accepted-branch ref-move gate fails CLOSED: with no reachable ethos binary a
    direct commit onto the accepted branch is BLOCKED (the hole that let a direct commit
    bypass candidate while the CLI lagged its own command). Existing Work Lane mutations
    also fail closed because their ref may not outrun the exact Lease. There is NO
    env escape: the former ETHOS_ALLOW_REF_MOVE=1 short-circuit was itself a hole (any
    process could set it) and was removed, so setting it no longer advances the accepted
    branch — sanctioned closeout must earn an admitted verdict through the reducer."""
    hook_src = Path(__file__).resolve().parents[3] / ".githooks" / "reference-transaction"
    if not hook_src.exists():
        pytest.skip("reference-transaction hook script not present")

    def g(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True, check=False, env=env
        )

    g("init", "-b", "dev")
    g("config", "user.name", "t")
    g("config", "user.email", "t@e.x")
    (hooks := tmp_path / ".githooks").mkdir()
    Path(shutil.copy(hook_src, hooks / "reference-transaction")).chmod(0o755)
    (workspace := tmp_path / ".ethos/workspace.toml").parent.mkdir()
    workspace.write_text(
        render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="independent",
        ),
        encoding="utf-8",
    )
    (tmp_path / "a").write_text("1", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "base")
    g("branch", "candidate/dev")
    g("branch", "work/x")
    g("config", "core.hooksPath", ".githooks")

    no_binary = {**os.environ, "PATH": "/usr/bin:/bin"}

    # New Work Lane refs are also fail-closed: official lane start acquires the
    # exact Lease before it creates the ref, so raw branch creation has no bootstrap bypass.
    raw_creation = g("checkout", "-b", "work/unleased", env=no_binary)
    assert raw_creation.returncode != 0
    assert g("show-ref", "--verify", "refs/heads/work/unleased").returncode != 0

    # `pack-refs` presents ref creation/deletion records indistinguishable from
    # real transitions. The hook must reject it rather than admitting direct
    # accepted deletion; installation disables automatic packing separately.
    dev_before_noop = g("rev-parse", "dev").stdout.strip()
    maintenance = g("pack-refs", "--all", "--prune", env=no_binary)
    assert maintenance.returncode != 0
    assert g("rev-parse", "dev").stdout.strip() == dev_before_noop
    g("checkout", "work/x", env=no_binary)
    blocked_delete = g("branch", "-D", "dev", env=no_binary)
    assert blocked_delete.returncode != 0
    assert g("rev-parse", "dev").stdout.strip() == dev_before_noop
    g("checkout", "dev", env=no_binary)

    # (1) accepted branch, no ethos binary -> BLOCKED (fail-closed)
    (tmp_path / "b").write_text("2", encoding="utf-8")
    g("add", ".")
    blocked = g("commit", "-m", "direct to dev", env=no_binary)
    assert blocked.returncode != 0
    dev_head = g("rev-parse", "dev").stdout.strip()

    # (2) existing Work Lane, no ethos binary -> BLOCKED (exact Lease fail-closed)
    g("checkout", "work/x", env=no_binary)
    (tmp_path / "w").write_text("w", encoding="utf-8")
    g("add", ".")
    work_commit = g("commit", "-m", "work commit", env=no_binary)
    assert work_commit.returncode != 0
    g("config", "core.hooksPath", "")
    committed = g("commit", "-m", "work commit")
    assert committed.returncode == 0
    g("config", "core.hooksPath", ".githooks")

    # (3) the removed env escape no longer works: a raw ff-merge to the accepted branch is
    # STILL blocked even with ETHOS_ALLOW_REF_MOVE=1 set, and dev does not move.
    g("checkout", "dev")
    escape = g("merge", "--ff-only", "work/x", env={**no_binary, "ETHOS_ALLOW_REF_MOVE": "1"})
    assert escape.returncode != 0
    assert g("rev-parse", "dev").stdout.strip() == dev_head


def test_reference_transaction_hook_fails_closed_on_empty_release_mirror_verdict(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = tmp_path / "candidate"
    git(repo, "branch", "main")
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    (candidate / "change").write_text("candidate\n", encoding="utf-8")
    git(candidate, "add", "change")
    git(candidate, "commit", "-m", "candidate")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    exclude = repo / git(repo, "rev-parse", "--git-path", "info/exclude")
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a", encoding="utf-8") as excluded:
        excluded.write("build/\nsrc/\ntools/\n")
    runtime = candidate / "tools/ci/scripts/with-python-runtime.sh"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
    runtime.chmod(0o755)
    package = candidate / "src/ethos"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text('[branch_roles]\nrelease_mirror = "accepted_ff"\n', encoding="utf-8")
    hook = Path(__file__).resolve().parents[3] / ".githooks/reference-transaction"

    completed = subprocess.run(
        [hook, "prepared"],
        cwd=repo,
        input=f"{git(repo, 'rev-parse', 'main')} {candidate_head} refs/heads/main\n",
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0


def test_reference_transaction_hook_uses_the_candidate_project_environment() -> None:
    hook = Path(__file__).resolve().parents[3] / ".githooks/reference-transaction"
    text = hook.read_text(encoding="utf-8")

    assert 'candidate_python="$candidate_root/build/runtime/venv/bin/python"' in text
    assert '"${candidate_python}" -P -m ethos.cli hook ref-transaction' in text
    assert "--isolated" not in text


# ── H2: the push plane enforces the SAME candidate-train topology as the ref-move plane ──
def test_push_admission_blocks_off_train_proven_head(tmp_path: Path) -> None:
    """A push of a proven commit that candidate never validated must block — the same
    accepted_advance_gaps the local ref-move reducer applies, so a raw `git push` cannot
    promote off-train work the ref hook would refuse."""
    repo, base = _accepted_boundary_repo(tmp_path)
    _advance_candidate(repo, "c1")
    git(repo, "checkout", "-q", "-b", "work/x")
    off_train = _advance_candidate(repo, "d")  # commit on work/x, never on candidate
    _acquire_fixture_lease(repo, "work/x", off_train, "agent:test:case:ref-move")
    _record_complete_proof(repo, off_train)

    report = push_admission_report(
        root=repo, target_ref="refs/heads/dev", pushed_head=off_train, remote_head=base
    )

    assert report["verdict"] == "block"
    assert "accepted_advance_not_candidate_validated" in report["required_gaps"]


def test_push_admission_blocks_non_head_intermediate(tmp_path: Path) -> None:
    """B/H2: pushing a candidate-contained but non-head proven commit to dev must block."""
    repo, base = _accepted_boundary_repo(tmp_path)
    c1 = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, c1)
    _advance_candidate(repo, "c2")  # live candidate head is c2

    report = push_admission_report(
        root=repo, target_ref="refs/heads/dev", pushed_head=c1, remote_head=base
    )

    assert report["verdict"] == "block"
    assert "accepted_ref_move_not_candidate_head" in report["required_gaps"]


def test_push_admission_blocks_rollback(tmp_path: Path) -> None:
    """C/H2: a force-push rewinding dev to an older proven commit (non-fast-forward)
    must block at the push plane — the rollback needs zero forgery."""
    repo, _base = _accepted_boundary_repo(tmp_path)
    c1 = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, c1)
    c2 = _advance_candidate(repo, "c2")

    report = push_admission_report(
        root=repo, target_ref="refs/heads/dev", pushed_head=c1, remote_head=c2
    )

    assert report["verdict"] == "block"
    assert "accepted_ref_move_not_fast_forward" in report["required_gaps"]


def test_push_admission_requires_local_closeout_before_protected_publication(
    tmp_path: Path,
) -> None:
    """A proven candidate head is publishable only after local accepted closeout."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    _record_complete_proof(repo, candidate_head)

    blocked = push_admission_report(
        root=repo, target_ref="refs/heads/dev", pushed_head=candidate_head, remote_head=base
    )
    git(repo, "update-ref", "refs/heads/dev", candidate_head, base)
    admitted = push_admission_report(
        root=repo, target_ref="refs/heads/dev", pushed_head=candidate_head, remote_head=base
    )

    assert blocked["verdict"] == "block"
    assert "push_to_protected_role_not_proven:local_ref_mismatch:dev" in blocked["required_gaps"]
    assert admitted["verdict"] == "pass"


def test_protected_push_uses_target_role_not_caller_work_lane(tmp_path: Path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    candidate_head = commit_fixture_file(
        fixture.candidate, "CANDIDATE.md", "candidate\n", "candidate"
    )
    seed_executed_proof(fixture.candidate, candidate_head)
    git(fixture.repository, "update-ref", "refs/heads/dev", candidate_head)

    report = push_admission_report(
        root=fixture.worktree,
        target_ref="refs/heads/dev",
        pushed_head=candidate_head,
        remote_head=git(fixture.repository, "rev-parse", f"{candidate_head}^"),
    )

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []


def test_push_admission_rejects_remote_work_lane(tmp_path: Path) -> None:
    """Work lanes are local-only and never enter either remote publication plane."""
    repo, base = _accepted_boundary_repo(tmp_path)
    git(repo, "checkout", "-q", "-b", "work/x")
    head = _advance_candidate(repo, "w")

    report = push_admission_report(
        root=repo, target_ref="refs/heads/work/x", pushed_head=head, remote_head=base
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["publication_remote_branch_forbidden:work/x"]
