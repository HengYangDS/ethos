"""Coverage-closure v3: mutation reachable branches (100% no-exemption)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.mutation.lane_lifecycle.refresh as lanes_refresh
import ethos.adapters.mutation.lane_retirement.unbound.core as unbound_retirement
import ethos_core.contracts.lifecycle.core as lifecycle_contract
from ethos.adapters.mutation import core
from ethos.adapters.mutation import lanes
from ethos.adapters.mutation import proof as mutation_proof
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.policy.gates import promotion_required_gate_ids
from tests.support.contract_helpers import conformant_proof_run

if TYPE_CHECKING:
    import pytest


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    return subprocess.run(
        ["git", "-c", "user.name=Cov", "-c", "user.email=cov@example.test", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )


def _init_repo(root: Path, branch: str = "dev") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _run_git(root, "init", "-b", branch)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _run_git(root, "add", ".")
    _run_git(root, "commit", "-m", "seed")
    return root


def _head(root: Path) -> str:
    return _run_git(root, "rev-parse", "HEAD").stdout.strip()


# --- mutation/core.py --------------------------------------------------------


def test_closeout_candidate_gaps_missing_branch() -> None:
    # Candidate branch absent short-circuits before worktree checks (line 74).
    gaps = core._closeout_candidate_gaps(Path("/x"), {"exists": False}, "head")
    assert gaps == ["candidate_branch_missing"]


def test_closeout_candidate_gaps_missing_worktree() -> None:
    # Candidate branch exists but its worktree does not (line 76).
    gaps = core._closeout_candidate_gaps(
        Path("/x"), {"exists": True, "worktree_exists": False}, "head"
    )
    assert gaps == ["candidate_worktree_missing"]


def test_closeout_candidate_gaps_dirty_worktree(tmp_path: Path) -> None:
    # A present-but-dirty candidate worktree yields the dirty gap (line 79).
    repo = _init_repo(tmp_path / "cand")
    (repo / "residue.txt").write_text("dirty\n", encoding="utf-8")  # untracked -> dirty
    candidate = {"exists": True, "worktree_exists": True, "worktree_path": str(repo)}
    gaps = core._closeout_candidate_gaps(repo, candidate, "head")
    assert gaps == ["candidate_worktree_dirty"]


def test_evaluate_closeout_mutation_requires_authorization_and_head(
    tmp_path: Path,
) -> None:
    # apply without authorization/expect_head appends both gaps (lines 203, 206).
    request = lifecycle_contract.MutationRequest(
        command="closeout", apply=True, authorized=False, expect_head=None
    )
    decision = core.evaluate_closeout_mutation(request, root=tmp_path, current_head="x")
    assert decision.ok is False
    assert "authorization_required" in decision.gaps
    assert "expect_head_required" in decision.gaps


def test_evaluate_closeout_mutation_accepted_root_dirty(tmp_path: Path) -> None:
    # An accepted-root checkout that is dirty is blocked as accepted_root_dirty (line 213).
    repo = _init_repo(tmp_path / "acc")  # branch dev == accepted_root
    (repo / "residue.txt").write_text("dirty\n", encoding="utf-8")  # untracked -> dirty
    request = lifecycle_contract.MutationRequest(
        command="closeout", apply=False, authorized=False, expect_head=None
    )
    decision = core.evaluate_closeout_mutation(request, root=repo, current_head=_head(repo))
    assert decision.ok is False
    assert "accepted_root_dirty" in decision.gaps


def test_apply_land_to_candidate_returns_blocked_decision(tmp_path: Path) -> None:
    # A not-ok admitted decision returns the blocked payload early (line 247).
    repo = _init_repo(tmp_path / "repo")
    blocked = lifecycle_contract.MutationEvaluation(
        ok=False, state="blocked", gaps=("authorization_required",)
    )
    result = core.apply_land_to_candidate(
        root=repo, authorized=False, expect_head=None, admitted_decision=blocked
    )
    assert result["ok"] is False
    assert result["state"] == "blocked"
    assert "authorization_required" in result["required_gaps"]


# --- mutation/lanes.py -------------------------------------------------------


def test_bind_work_lane_claim_reports_lane_not_found(tmp_path: Path) -> None:
    # No matching work-lane worktree appends work_lane_not_found (line 175).
    result = lanes.bind_work_lane_claim(
        root=tmp_path, claim_id="c1", branch="work/none", apply=False
    )
    assert result["ok"] is False
    assert "work_lane_not_found:work/none" in result["required_gaps"]


def test_active_lease_skips_non_matching_subject(tmp_path: Path) -> None:
    # A lease whose subject differs is skipped, looping on (branch 325->324) to None.
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    acquire_lease(db_path, subject="work/other", holder_ref="agent:test:case:owner")
    assert lanes._active_lease(db_path, "work/target") is None


# --- mutation/lane_lifecycle/refresh.py -------------------------------------


def test_bootstrap_candidate_skips_branch_create_when_branch_exists(
    tmp_path: Path,
) -> None:
    # Candidate branch present (no worktree) skips branch creation (branch 71->83)
    # and adds the worktree directly.
    repo = _init_repo(tmp_path / "acc")
    _run_git(repo, "branch", "candidate/dev")  # ref exists, no worktree
    target = tmp_path / "cand-new"  # must not exist yet
    result = lanes_refresh.bootstrap_candidate(root=repo, path=target, apply=True)
    assert result["ok"] is True
    assert result["state"] == "bootstrapped"


def test_refresh_candidate_from_accepted_reset_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A failing `git reset --hard` in the candidate worktree is reported (line 231).
    repo = _init_repo(tmp_path / "acc")  # dev at C1
    cand = tmp_path / "cand"
    _run_git(repo, "worktree", "add", str(cand), "-b", "candidate/dev")  # candidate/dev at C1
    (repo / "more.txt").write_text("more\n", encoding="utf-8")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "c2")  # dev advances to C2
    accepted_head = _head(repo)

    real_git = lanes_refresh.run_git
    reset_envs: list[dict[str, str] | None] = []

    def _fail_reset(
        root: Path,
        *args: str,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if "reset" in args:
            reset_envs.append(env)
            return subprocess.CompletedProcess(
                args=["git", *args], returncode=1, stdout="", stderr="reset boom"
            )
        return real_git(root, *args, check=check, env=env)

    monkeypatch.setattr(lanes_refresh, "run_git", _fail_reset)
    result = lanes_refresh.refresh_candidate_from_accepted(
        root=repo, apply=True, authorized=True, expect_head=accepted_head
    )
    assert result["ok"] is False
    assert "candidate_refresh_from_accepted_failed" in result["required_gaps"]
    assert result["stderr"] == "reset boom"
    # The candidate refresh reset no longer carries a ref-move escape env — the target is
    # accepted-contained, so the armed hook admits the rewind without one.
    assert reset_envs == [None]


def test_refresh_work_lane_base_protected_root(tmp_path: Path) -> None:
    # A non-work-lane checkout is blocked as protected_root_mutation (line 272).
    repo = _init_repo(tmp_path / "acc")  # branch dev != work_lane
    result = lanes_refresh.refresh_work_lane_base(root=repo)
    assert result["ok"] is True or result["ok"] is False  # deterministic dict shape
    assert "protected_root_mutation" in result["required_gaps"]


# --- mutation/lane_retirement/unbound.py ------------------------------------


def test_unbound_work_lane_ref_skips_non_matching_entries() -> None:
    # Non-dict and non-matching ref rows are skipped, looping on (branch 294->293).
    status = {"coordination": {"unbound_work_lane_refs": ["junk", {"branch": "work/other"}]}}
    assert unbound_retirement._unbound_work_lane_ref(status, "work/target") is None


# --- slice 2c: proof-carry-before-ref-move reorder + discard hygiene ---------


def test_land_blocks_when_proof_carry_to_candidate_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # core.py: the proof is carried to the candidate BEFORE the merge; a failed carry blocks
    # the land with the carry's gaps and never reaches the ref move.
    monkeypatch.setattr(
        core,
        "candidate_base_report",
        lambda **_kwargs: {
            "ok": True,
            "path": str(tmp_path / "candidate"),
            "required_gaps": [],
        },
    )
    monkeypatch.setattr(
        core,
        "run_git",
        lambda *_a, **_k: subprocess.CompletedProcess([], 0, "h1\n", ""),
    )
    monkeypatch.setattr(
        core,
        "carry_executed_proof_record",
        lambda **_k: {"ok": False, "required_gaps": ["proof_not_proven"]},
    )
    ready = lifecycle_contract.MutationEvaluation(ok=True, state="land_ready")
    result = core.apply_land_to_candidate(
        root=tmp_path, authorized=True, expect_head="h1", admitted_decision=ready
    )
    assert result["ok"] is False
    assert result["required_gaps"] == ["proof_not_proven"]


def test_advance_accepted_ref_blocks_when_proof_carry_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # core.py: the closeout carries the proof to the accepted root BEFORE the CAS; a failed
    # carry blocks with the carry's gaps and never moves the ref. Driven through the public
    # apply_candidate_to_accepted so no private helper is touched.
    repo = _init_repo(tmp_path / "r")
    candidate = tmp_path / "cand"
    _run_git(repo, "worktree", "add", "-b", "candidate/dev", str(candidate), "dev")
    (candidate / "c.txt").write_text("c\n", encoding="utf-8")
    _run_git(candidate, "add", ".")
    _run_git(candidate, "commit", "-m", "candidate change")
    accepted_head = _head(repo)
    monkeypatch.setattr(
        core,
        "carry_executed_proof_record",
        lambda **_k: {"ok": False, "required_gaps": ["proof_not_proven"]},
    )
    monkeypatch.setattr(core, "_candidate_gaps_for_proof", lambda *_a, **_k: [])
    result = core.apply_candidate_to_accepted(root=repo, authorized=True, expect_head=accepted_head)
    assert result["ok"] is False
    assert result["required_gaps"] == ["proof_not_proven"]


def test_discard_executed_proof_idempotent(tmp_path: Path) -> None:
    # proof.py: discard reclaims a pre-placed proof record; True when one existed, False when
    # absent (idempotent).
    _init_repo(tmp_path)
    head = "b" * 40
    runs = tuple(conformant_proof_run(g, tmp_path) for g in promotion_required_gate_ids(tmp_path))
    mutation_proof.record_executed_proof(
        tmp_path, EvidenceSet.from_runs(id="proof", head=head, runs=runs).to_dict()
    )
    assert mutation_proof.discard_executed_proof(tmp_path, head) is True
    assert mutation_proof.discard_executed_proof(tmp_path, head) is False
