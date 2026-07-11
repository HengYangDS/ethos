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
import subprocess
from pathlib import Path

import pytest

from ethos.adapters.admission.closeout_intent.core import CloseoutTransition
from ethos.adapters.admission.closeout_intent.core import write_closeout_intent
from ethos.adapters.admission.core import push_admission_report
from ethos.adapters.admission.core import ref_move_admission_report
from ethos.adapters.admission.core import work_lane_ref_transition_report
from ethos.adapters.mutation.proof import _promotion_required_gate_ids
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.policy.gates import gate_policy_digest
from tests.support.contract_helpers import conformant_proof_run
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo


def test_work_lane_ref_transition_prepared_checks_holder_generation_and_old_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    lane = tmp_path / "repo-work-current"
    git(repo, "worktree", "add", "-b", "work/current", lane.as_posix(), "dev")
    head = git(lane, "rev-parse", "HEAD")
    from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease

    acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        payload={"expected_head": head},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:first")

    report = work_lane_ref_transition_report(
        root=lane,
        phase="prepared",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value="b" * 40,
    )
    assert report["ok"] is True
    assert report["decision"]["action"] == "allow"
    assert report["lease"]["epoch"] == 1

    stale = work_lane_ref_transition_report(
        root=lane,
        phase="prepared",
        ref_name="refs/heads/work/current",
        old_value="c" * 40,
        new_value="b" * 40,
    )
    assert stale["ok"] is False
    assert any("lease_head_stale" in gap for gap in stale["required_gaps"])


def test_work_lane_ref_transition_committed_advances_local_lease_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    lane = tmp_path / "repo-work-current"
    git(repo, "worktree", "add", "-b", "work/current", lane.as_posix(), "dev")
    head = git(lane, "rev-parse", "HEAD")
    new_head = "b" * 40
    from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease

    acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        payload={"expected_head": head},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:first")

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=new_head,
    )
    assert report["ok"] is True
    assert report["state"] == "lease_head_advanced"
    assert report["lease"]["expected_head"] == new_head


def _complete_proof_evidence(head: str, root: Path) -> dict[str, object]:
    """A COMPLETE, POLICY-CONFORMANT executed-proof body: one passing run per required
    gate, carrying that gate's canonical command / trust_bearing / evidence_class.

    Post-completeness + policy-conformance binding, a promotion proof must cover the
    required land floor AND each run must conform to its gate's live policy identity, so
    the boundary tests reach the boundary check itself rather than a placeholder-command
    conformance gap.
    """
    runs = tuple(
        conformant_proof_run(gate_id, root) for gate_id in _promotion_required_gate_ids(root)
    )
    return EvidenceSet.from_runs(id="proof", head=head, runs=runs).to_dict()


def _accepted_boundary_repo(tmp_path: Path) -> tuple[Path, str]:
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
    g("commit", "--allow-empty", "-q", "-m", "base")
    base = g("rev-parse", "HEAD")
    g("branch", "candidate/dev")
    g("checkout", "-q", "candidate/dev")
    return tmp_path, base


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
    assert blocked["ok"] is False
    assert "accepted_advance_not_candidate_validated" in blocked["required_gaps"]

    # a move of a non-accepted (work) ref is admitted untouched
    lane = ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/work/x", old_value=base, new_value=work
    )
    assert lane["ok"] is True

    # candidate-first: once candidate contains the commit, containment passes
    g("checkout", "candidate/dev")
    g("merge", "--ff-only", "work/x")
    advanced = ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/dev", old_value=base, new_value=work
    )
    assert "accepted_advance_not_candidate_validated" not in advanced["required_gaps"]


def test_ref_move_admission_blocks_unproven_candidate_ref_move(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    candidate_head = "c" * 40

    report = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/candidate/dev",
        old_value=head,
        new_value=candidate_head,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["decision"] == {
        "action": "block",
        "reason": "protected_ref_move_not_proven",
    }
    assert any("proof" in str(gap) or "not_proven" in str(gap) for gap in report["required_gaps"])


def test_ref_move_admission_admits_candidate_rewind_to_accepted_contained(tmp_path: Path) -> None:
    """A candidate-branch move to a commit the accepted branch already contains (a
    refresh-from-accepted rewind) promotes no new work, so it is admitted WITHOUT a fresh
    proof — the exemption that keeps `ethos lane refresh-base` working once the
    ETHOS_ALLOW_REF_MOVE bypass is gone. `base` is on the accepted branch (dev)."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")

    report = ref_move_admission_report(
        root=repo,
        ref_name="refs/heads/candidate/dev",
        old_value=candidate_head,
        new_value=base,  # rewind candidate back onto accepted-contained base
    )

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_ref_move_admission_blocks_rollback_to_old_proven_commit(tmp_path: Path) -> None:
    """B2: a raw rollback of dev to an older, still-proven, still-candidate-contained
    commit is a non-fast-forward and must block — accepted history only advances."""
    repo, _base = _accepted_boundary_repo(tmp_path)
    c1 = _advance_candidate(repo, "c1")
    c2 = _advance_candidate(repo, "c2")
    record_executed_proof(repo, _complete_proof_evidence(c1, repo))  # c1 proven + contained

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=c2, new_value=c1
    )

    assert report["ok"] is False
    assert "accepted_ref_move_not_fast_forward" in report["required_gaps"]


def test_ref_move_admission_blocks_advance_to_non_head_intermediate(tmp_path: Path) -> None:
    """B3: advancing dev to a candidate-CONTAINED but non-head intermediate commit
    (fast-forward, proven) still bypasses closeout — only the live candidate head may
    be promoted, so it must block."""
    repo, base = _accepted_boundary_repo(tmp_path)
    c1 = _advance_candidate(repo, "c1")
    _c2 = _advance_candidate(repo, "c2")  # live candidate head is now c2
    record_executed_proof(repo, _complete_proof_evidence(c1, repo))  # c1 proven, FF, != head

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=c1
    )

    assert report["ok"] is False
    assert "accepted_ref_move_not_candidate_head" in report["required_gaps"]


def _write_matching_intent(repo: Path, *, old_value: str, new_value: str) -> None:
    """Write the closeout-intent marker official closeout would write for this move,
    carrying the proof's real evidence_digest and the live gate_policy_digest so
    admission's digest checks pass."""
    record = executed_proof_record(repo, new_value)
    evidence_digest = str(record.get("evidence_digest", "")) if isinstance(record, dict) else ""
    write_closeout_intent(
        root=repo,
        transition=CloseoutTransition(
            ref_name="refs/heads/dev",
            old_value=old_value,
            new_value=new_value,
            candidate_head=new_value,
        ),
        evidence_digest=evidence_digest,
        gate_policy_digest=gate_policy_digest(repo),
    )


def test_ref_move_admission_admits_official_closeout_with_intent_marker(
    tmp_path: Path,
) -> None:
    """B7 happy path (self-harm guard): a fast-forward of dev to the live candidate head
    carrying a complete executed proof AND a matching closeout-intent marker is exactly
    what official closeout produces — it must be admitted with no boundary gaps, or the
    moat would deadlock the sanctioned path."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")  # c1 IS the live candidate head
    record_executed_proof(repo, _complete_proof_evidence(candidate_head, repo))
    _write_matching_intent(repo, old_value=base, new_value=candidate_head)

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_ref_move_admission_blocks_raw_move_without_closeout_intent(tmp_path: Path) -> None:
    """B1 (the load-bearing nail): a raw `git update-ref refs/heads/dev <candidate_head>
    <old>` is byte-identical to official closeout's CAS — fast-forward, == live candidate
    head, complete proof — yet carries NO closeout-intent marker. Without the marker it
    must block, or raw git could promote a proven candidate head bypassing closeout."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    record_executed_proof(repo, _complete_proof_evidence(candidate_head, repo))

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert report["ok"] is False
    assert "accepted_ref_move_no_closeout_intent" in report["required_gaps"]


def test_ref_move_admission_blocks_reused_closeout_intent(tmp_path: Path) -> None:
    """B6: the marker is one-shot. Once admission consumes it, a second identical move
    finds no marker and blocks — a nonce cannot authorize two promotions."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    record_executed_proof(repo, _complete_proof_evidence(candidate_head, repo))
    _write_matching_intent(repo, old_value=base, new_value=candidate_head)

    first = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )
    second = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert first["ok"] is True
    assert second["ok"] is False
    assert "accepted_ref_move_no_closeout_intent" in second["required_gaps"]


def test_ref_move_admission_blocks_mismatched_closeout_intent(tmp_path: Path) -> None:
    """B4: a marker whose old/new binding does not match the actual ref move is refused
    (a marker minted for a different transition cannot authorize this one)."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    record_executed_proof(repo, _complete_proof_evidence(candidate_head, repo))
    # Marker binds a different old_value than the actual move.
    _write_matching_intent(repo, old_value="0" * 40, new_value=candidate_head)

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert report["ok"] is False
    assert "closeout_intent_mismatch" in report["required_gaps"]


def test_ref_move_admission_blocks_stale_closeout_intent(tmp_path: Path) -> None:
    """B5: an expired marker is refused (TTL bounds how long a written intent stays
    admissible, so a crashed closeout's residue cannot be reused later)."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    record_executed_proof(repo, _complete_proof_evidence(candidate_head, repo))
    _write_matching_intent(repo, old_value=base, new_value=candidate_head)
    _backdate_markers(repo)

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert report["ok"] is False
    assert "closeout_intent_stale" in report["required_gaps"]


def _backdate_markers(repo: Path) -> None:
    """Expire every closeout-intent marker by rewriting expires_at into the past."""
    from ethos.adapters.admission.closeout_intent.core import _marker_dir

    marker_dir = _marker_dir(repo)
    for path in marker_dir.glob("*.json"):
        marker = json.loads(path.read_text(encoding="utf-8"))
        marker["expires_at"] = "2000-01-01T00:00:00+00:00"
        path.write_text(json.dumps(marker), encoding="utf-8")


def test_reference_transaction_hook_fails_closed_on_accepted_branch(tmp_path: Path) -> None:
    """The accepted-branch ref-move gate fails CLOSED: with no reachable ethos binary a
    direct commit onto the accepted branch is BLOCKED (the hole that let a direct commit
    bypass candidate while the CLI lagged its own command). Non-accepted branches fail
    OPEN so an unavailable binary does not brick ordinary work-lane commits. There is NO
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
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    shutil.copy(hook_src, hooks / "reference-transaction")
    (hooks / "reference-transaction").chmod(0o755)
    (tmp_path / "a").write_text("1", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "base")
    g("branch", "candidate/dev")
    g("config", "core.hooksPath", ".githooks")
    g("config", "ethos.acceptedBranch", "dev")

    no_binary = {**os.environ, "PATH": "/usr/bin:/bin"}

    # (1) accepted branch, no ethos binary -> BLOCKED (fail-closed)
    (tmp_path / "b").write_text("2", encoding="utf-8")
    g("add", ".")
    blocked = g("commit", "-m", "direct to dev", env=no_binary)
    assert blocked.returncode != 0
    dev_head = g("rev-parse", "dev").stdout.strip()

    # (2) non-accepted branch, no ethos binary -> ALLOWED (fail-open)
    g("checkout", "-b", "work/x", env=no_binary)
    (tmp_path / "w").write_text("w", encoding="utf-8")
    g("add", ".")
    work_commit = g("commit", "-m", "work commit", env=no_binary)
    assert work_commit.returncode == 0

    # (3) the removed env escape no longer works: a raw ff-merge to the accepted branch is
    # STILL blocked even with ETHOS_ALLOW_REF_MOVE=1 set, and dev does not move.
    g("checkout", "dev")
    escape = g("merge", "--ff-only", "work/x", env={**no_binary, "ETHOS_ALLOW_REF_MOVE": "1"})
    assert escape.returncode != 0
    assert g("rev-parse", "dev").stdout.strip() == dev_head


# ── H2: the push plane enforces the SAME candidate-train topology as the ref-move plane ──
def test_push_admission_blocks_off_train_proven_head(tmp_path: Path) -> None:
    """A push of a proven commit that candidate never validated must block — the same
    accepted_advance_gaps the local ref-move reducer applies, so a raw `git push` cannot
    promote off-train work the ref hook would refuse."""
    repo, base = _accepted_boundary_repo(tmp_path)
    _advance_candidate(repo, "c1")
    git(repo, "checkout", "-q", "-b", "work/x")
    off_train = _advance_candidate(repo, "d")  # commit on work/x, never on candidate
    record_executed_proof(repo, _complete_proof_evidence(off_train, repo))

    report = push_admission_report(
        root=repo, target_ref="refs/heads/dev", pushed_head=off_train, remote_head=base
    )

    assert report["ok"] is False
    assert "accepted_advance_not_candidate_validated" in report["required_gaps"]


def test_push_admission_blocks_non_head_intermediate(tmp_path: Path) -> None:
    """B/H2: pushing a candidate-contained but non-head proven commit to dev must block."""
    repo, base = _accepted_boundary_repo(tmp_path)
    c1 = _advance_candidate(repo, "c1")
    _advance_candidate(repo, "c2")  # live candidate head is c2
    record_executed_proof(repo, _complete_proof_evidence(c1, repo))

    report = push_admission_report(
        root=repo, target_ref="refs/heads/dev", pushed_head=c1, remote_head=base
    )

    assert report["ok"] is False
    assert "accepted_ref_move_not_candidate_head" in report["required_gaps"]


def test_push_admission_blocks_rollback(tmp_path: Path) -> None:
    """C/H2: a force-push rewinding dev to an older proven commit (non-fast-forward)
    must block at the push plane — the rollback needs zero forgery."""
    repo, _base = _accepted_boundary_repo(tmp_path)
    c1 = _advance_candidate(repo, "c1")
    c2 = _advance_candidate(repo, "c2")
    record_executed_proof(repo, _complete_proof_evidence(c1, repo))

    report = push_admission_report(
        root=repo, target_ref="refs/heads/dev", pushed_head=c1, remote_head=c2
    )

    assert report["ok"] is False
    assert "accepted_ref_move_not_fast_forward" in report["required_gaps"]


def test_push_admission_admits_fast_forward_to_proven_candidate_head(tmp_path: Path) -> None:
    """A fast-forward push of dev to the live candidate head carrying a complete proof is
    the sanctioned publish — it must be admitted (no marker needed: a push carries no
    in-process closeout-intent, only the topology + proof gates apply)."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")
    record_executed_proof(repo, _complete_proof_evidence(candidate_head, repo))

    report = push_admission_report(
        root=repo, target_ref="refs/heads/dev", pushed_head=candidate_head, remote_head=base
    )

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_push_admission_leaves_work_lane_push_untouched(tmp_path: Path) -> None:
    """A push to a non-accepted (work-lane) ref carries no candidate-train topology."""
    repo, base = _accepted_boundary_repo(tmp_path)
    git(repo, "checkout", "-q", "-b", "work/x")
    head = _advance_candidate(repo, "w")

    report = push_admission_report(
        root=repo, target_ref="refs/heads/work/x", pushed_head=head, remote_head=base
    )

    assert report["ok"] is True
