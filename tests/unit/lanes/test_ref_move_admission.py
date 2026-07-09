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

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from ethos.adapters.admission.core import ref_move_admission_report
from ethos.adapters.mutation.proof import _promotion_required_gate_ids
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo


def _complete_proof_evidence(head: str, root: Path) -> dict[str, object]:
    """A COMPLETE executed-proof body: one passing trust-bearing run per required gate.

    Post-completeness-binding, a promotion proof must cover the required land floor, so
    the accepted-ref boundary tests seed the full floor to reach the boundary check
    itself — a single-run proof would now stop earlier at proof_incomplete.
    """
    runs = tuple(
        ProofRun(
            action_id=gate_id,
            command=("pytest",),
            exit_code=0,
            stdout="",
            stderr="",
            state="proven",
            evidence_class="test",
            verdict="passed",
            trust_bearing=True,
            diagnostics=(),
        )
        for gate_id in _promotion_required_gate_ids(root)
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


def test_ref_move_admission_admits_fast_forward_to_proven_candidate_head(
    tmp_path: Path,
) -> None:
    """Happy path (self-harm guard): a fast-forward of dev to the live candidate head
    carrying a complete executed proof is exactly what closeout produces — it must be
    admitted with no boundary gaps, or the moat would deadlock the sanctioned path."""
    repo, base = _accepted_boundary_repo(tmp_path)
    candidate_head = _advance_candidate(repo, "c1")  # c1 IS the live candidate head
    record_executed_proof(repo, _complete_proof_evidence(candidate_head, repo))

    report = ref_move_admission_report(
        root=repo, ref_name="refs/heads/dev", old_value=base, new_value=candidate_head
    )

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_reference_transaction_hook_fails_closed_on_accepted_branch(tmp_path: Path) -> None:
    """The accepted-branch ref-move gate fails CLOSED: with no reachable ethos binary a
    direct commit onto the accepted branch is BLOCKED (the hole that let a direct commit
    bypass candidate while the CLI lagged its own command). Non-accepted branches fail
    OPEN so an unavailable binary does not brick ordinary work-lane commits; the
    sanctioned closeout escape (ETHOS_ALLOW_REF_MOVE=1) still advances the accepted
    branch."""
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
    g("checkout", "-b", "work/x")
    (tmp_path / "w").write_text("w", encoding="utf-8")
    g("add", ".")
    work_commit = g("commit", "-m", "work commit", env=no_binary)
    assert work_commit.returncode == 0

    # (3) sanctioned closeout escape -> accepted branch advances
    g("checkout", "dev")
    closeout = g("merge", "--ff-only", "work/x", env={**no_binary, "ETHOS_ALLOW_REF_MOVE": "1"})
    assert closeout.returncode == 0
    assert g("rev-parse", "dev").stdout.strip() != dev_head
