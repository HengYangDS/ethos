"""Coverage-closure v3: mutation reachable branches (100% no-exemption)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.lane_lifecycle.refresh as lanes_refresh
import ethos.adapters.mutation.lane_retirement.unbound.observation.core as unbound_observation
import ethos_core.contracts.lifecycle.core as lifecycle_contract
from ethos.adapters.mutation import core
from ethos.adapters.mutation import lanes
from ethos.adapters.mutation import proof as mutation_proof
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.policy.gates import promotion_required_gate_ids
from tests.support.contract_helpers import conformant_proof_run

_REFRESH_CASES = json.loads(
    '[ ["bootstrap","other",false,false,false,false,"blocked","candidate_bootstrap_requires_clean_accepted_root"], ["bootstrap","accepted_root",true,false,false,false,"present",""], ["bootstrap","accepted_root",false,false,false,false,"planned",""], ["bootstrap","accepted_root",false,false,true,true,"blocked","candidate_worktree_path_exists"], ["bootstrap","accepted_root",false,false,true,false,"blocked","candidate_bootstrap_failed"], ["candidate","work_lane",false,"c1",false,false,"blocked","accepted_root_required"], ["candidate","accepted_root",true,"c1",false,false,"blocked","accepted_root_dirty"], ["candidate","accepted_root",false,"h1",false,false,"base_current",""], ["candidate","accepted_root",false,"c1",false,false,"ready_to_refresh_from_accepted",""], ["lane","work_lane",true,false,false,false,"blocked","work_lane_dirty"], ["lane","work_lane",false,true,false,false,"base_current",""] ]'
)


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
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


@pytest.mark.parametrize(
    ("candidate", "gap"),
    [
        ({"exists": False}, "candidate_branch_missing"),
        ({"exists": True, "worktree_exists": False}, "candidate_worktree_missing"),
    ],
)
def test_closeout_candidate_gaps_missing_boundaries(candidate: dict[str, bool], gap: str) -> None:
    assert core._closeout_candidate_gaps(Path("/x"), candidate, "head") == [gap]


def test_closeout_candidate_gaps_dirty_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "cand")
    (repo / "residue.txt").write_text("dirty\n", encoding="utf-8")
    assert core._closeout_candidate_gaps(
        repo, {"exists": True, "worktree_exists": True, "worktree_path": str(repo)}, "head"
    ) == ["candidate_worktree_dirty"]


def test_evaluate_closeout_mutation_requires_authorization_and_head(tmp_path: Path) -> None:
    request = lifecycle_contract.MutationRequest(
        command="closeout", apply=True, authorized=False, expect_head=None
    )
    decision = core.evaluate_closeout_mutation(request, root=tmp_path, current_head="x")
    assert (
        decision.ok,
        {"authorization_required", "expect_head_required"} <= set(decision.gaps),
    ) == (
        False,
        True,
    )


def test_evaluate_closeout_mutation_accepted_root_dirty(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "acc")
    (repo / "residue.txt").write_text("dirty\n", encoding="utf-8")
    decision = core.evaluate_closeout_mutation(
        lifecycle_contract.MutationRequest(
            command="closeout", apply=False, authorized=False, expect_head=None
        ),
        root=repo,
        current_head=_head(repo),
    )
    assert (decision.ok, "accepted_root_dirty" in decision.gaps) == (False, True)


def test_apply_land_to_candidate_returns_blocked_decision(tmp_path: Path) -> None:
    blocked = lifecycle_contract.MutationEvaluation(
        ok=False, state="blocked", gaps=("authorization_required",)
    )
    result = core.apply_land_to_candidate(
        root=_init_repo(tmp_path / "repo"),
        authorized=False,
        expect_head=None,
        admitted_decision=blocked,
    )
    assert (
        result["ok"],
        result["state"],
        "authorization_required" in result["required_gaps"],
    ) == (False, "blocked", True)


def test_bind_work_lane_claim_reports_lane_not_found(tmp_path: Path) -> None:
    result = lanes.bind_work_lane_claim(
        root=tmp_path, claim_id="c1", branch="work/none", apply=False
    )
    assert (result["ok"], "work_lane_not_found:work/none" in result["required_gaps"]) == (
        False,
        True,
    )


def test_active_lease_skips_non_matching_subject(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos/state/state.sqlite"
    acquire_lease(db_path, subject="work/other", holder_ref="agent:test:case:owner")
    assert lanes._active_lease(db_path, "work/target") is None


def test_bootstrap_candidate_skips_branch_create_when_branch_exists(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "acc")
    _run_git(repo, "branch", "candidate/dev")
    result = lanes_refresh.bootstrap_candidate(root=repo, path=tmp_path / "cand-new", apply=True)
    assert (result["ok"], result["state"]) == (True, "bootstrapped")


def test_refresh_candidate_from_accepted_reset_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, cand = _init_repo(tmp_path / "acc"), tmp_path / "cand"
    _run_git(repo, "worktree", "add", str(cand), "-b", "candidate/dev")
    (repo / "more.txt").write_text("more\n", encoding="utf-8")
    _ = (_run_git(repo, "add", "."), _run_git(repo, "commit", "-m", "c2"))
    real_git, reset_envs = lanes_refresh.run_git, []

    def fail_reset(
        root: Path, *args: str, check: bool = True, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        if "reset" in args:
            reset_envs.append(env)
            return subprocess.CompletedProcess(["git", *args], 1, "", "reset boom")
        return real_git(root, *args, check=check, env=env)

    monkeypatch.setattr(lanes_refresh, "run_git", fail_reset)
    result = lanes_refresh.refresh_candidate_from_accepted(
        root=repo, apply=True, authorized=True, expect_head=_head(repo)
    )
    assert (
        result["ok"],
        "candidate_refresh_from_accepted_failed" in result["required_gaps"],
        result["stderr"],
        reset_envs,
    ) == (False, True, "reset boom", [None])


def test_refresh_work_lane_base_protected_root(tmp_path: Path) -> None:
    result = lanes_refresh.refresh_work_lane_base(root=_init_repo(tmp_path / "acc"))
    assert "protected_root_mutation" in result["required_gaps"]


def test_unbound_work_lane_ref_skips_non_matching_entries() -> None:
    assert (
        unbound_observation.unbound_work_lane_ref(
            {"coordination": {"unbound_work_lane_refs": ["junk", {"branch": "work/other"}]}},
            "work/target",
        )
        is None
    )


def test_land_blocks_when_proof_carry_to_candidate_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        core,
        "candidate_base_report",
        lambda **_kwargs: {"ok": True, "path": str(tmp_path / "candidate"), "required_gaps": []},
    )
    monkeypatch.setattr(
        core, "run_git", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "h1\n", "")
    )
    monkeypatch.setattr(
        core,
        "carry_executed_proof_record",
        lambda **_kwargs: {"ok": False, "required_gaps": ["proof_not_proven"]},
    )
    result = core.apply_land_to_candidate(
        root=tmp_path,
        authorized=True,
        expect_head="h1",
        admitted_decision=lifecycle_contract.MutationEvaluation(ok=True, state="land_ready"),
    )
    assert (result["ok"], result["required_gaps"]) == (False, ["proof_not_proven"])


def test_advance_accepted_ref_blocks_when_proof_carry_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, candidate = _init_repo(tmp_path / "r"), tmp_path / "cand"
    _run_git(repo, "worktree", "add", "-b", "candidate/dev", str(candidate), "dev")
    (candidate / "c.txt").write_text("c\n", encoding="utf-8")
    _ = (_run_git(candidate, "add", "."), _run_git(candidate, "commit", "-m", "candidate change"))
    monkeypatch.setattr(
        core,
        "carry_executed_proof_record",
        lambda **_kwargs: {"ok": False, "required_gaps": ["proof_not_proven"]},
    )
    monkeypatch.setattr(core, "_candidate_gaps_for_proof", lambda *_args, **_kwargs: [])
    result = core.apply_candidate_to_accepted(root=repo, authorized=True, expect_head=_head(repo))
    assert (result["ok"], result["required_gaps"]) == (False, ["proof_not_proven"])


def test_discard_executed_proof_idempotent(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    head = "b" * 40
    runs = tuple(
        conformant_proof_run(gate, tmp_path) for gate in promotion_required_gate_ids(tmp_path)
    )
    mutation_proof.record_executed_proof(
        tmp_path, EvidenceSet.from_runs(id="proof", head=head, runs=runs).to_dict()
    )
    assert mutation_proof.discard_executed_proof(tmp_path, head) is True
    assert mutation_proof.discard_executed_proof(tmp_path, head) is False


@pytest.mark.parametrize("case", _REFRESH_CASES)
def test_refresh_decision_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: list[object]
) -> None:
    kind, role, flag, value, apply, path_exists, state, gap = case
    target = tmp_path / "candidate"
    if kind == "bootstrap" and path_exists:
        target.mkdir()
    present = flag if kind == "bootstrap" else True
    status = {
        "role": role,
        "dirty": flag if kind != "bootstrap" else False,
        "branch": "work/feature",
        "candidate": {
            "exists": present,
            "worktree_exists": present,
            "worktree_path": tmp_path.as_posix(),
            "head": value if kind == "candidate" else "c1",
        },
    }

    def fake_git(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        branch = args[:1] == ("branch",)
        return subprocess.CompletedProcess(
            ["git", *args],
            1 if branch else 0,
            "h1\n" if args == ("rev-parse", "HEAD") else "",
            "branch failed" if branch else "",
        )

    patches = {
        "repo_root": lambda root: root,
        "load_branch_role_policy": lambda _root: SimpleNamespace(candidate_branch="candidate/dev"),
        "workspace_status": lambda _root: status,
        "changed_paths": lambda _path: [],
        "is_ancestor": lambda *_args: value,
        "run_git": fake_git,
    }
    for name, replacement in patches.items():
        monkeypatch.setattr(lanes_refresh, name, replacement)
    if kind == "bootstrap":
        report = lanes_refresh.bootstrap_candidate(root=tmp_path, path=target, apply=apply)
    elif kind == "candidate":
        report = lanes_refresh.refresh_candidate_from_accepted(root=tmp_path)
    else:
        report = lanes_refresh.refresh_work_lane_base(root=tmp_path)
    assert (report["state"], report["required_gaps"]) == (state, [gap] if gap else [])
