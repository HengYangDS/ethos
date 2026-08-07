"""Accepted/candidate ref-move and protected publication admission."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.git_admission as git_admission
from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.admission.git_admission import ref_move_admission_report
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.gates import resolve_gate_policy
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import conformant_proof_check
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import render_branch_policy
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.governed_repository import write_active_commitment
from tests.support.governed_repository import write_publication_topology
from tests.support.governed_repository import write_role_policy

_FIXTURE_COMMITMENT_CARRIER = "openspec/changes/fixture-change/commitment.toml"

if TYPE_CHECKING:
    from pathlib import Path


def _acquire_fixture_lease(repo: Path, branch: str, head: str, holder: str) -> None:
    acquire_lease(
        state_database(repo),
        lease=exact_lease(
            repo=repo,
            branch=branch,
            holder_ref=holder,
            expected_head=head,
            carrier=_FIXTURE_COMMITMENT_CARRIER,
        ),
    )


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
    repo = init_git_repo(tmp_path / "repo")
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
