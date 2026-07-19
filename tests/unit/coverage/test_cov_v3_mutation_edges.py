from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.lane_lifecycle.refresh as refresh
import ethos_core.contracts.lifecycle.core as lifecycle
from ethos.adapters.mutation import core
from ethos.adapters.mutation import lanes
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from tests.support.contract_helpers import init_git_repo

_CASES = json.loads(
    '[ ["bootstrap","other",false,false,false,false,"blocked","candidate_bootstrap_requires_clean_accepted_root"], ["bootstrap","accepted_root",true,false,false,false,"present",""], ["bootstrap","accepted_root",false,false,false,false,"planned",""], ["bootstrap","accepted_root",false,false,true,true,"blocked","candidate_worktree_path_exists"], ["bootstrap","accepted_root",false,false,true,false,"blocked","candidate_bootstrap_failed"], ["candidate","work_lane",false,"c1",false,false,"blocked","accepted_root_required"], ["candidate","accepted_root",true,"c1",false,false,"blocked","accepted_root_dirty"], ["candidate","accepted_root",false,"h1",false,false,"base_current",""], ["candidate","accepted_root",false,"c1",false,false,"ready_to_refresh_from_accepted",""], ["lane","work_lane",true,false,false,false,"blocked","work_lane_dirty"], ["lane","work_lane",false,true,false,false,"base_current",""] ]'
)


def test_closeout_and_lane_guard_matrix(tmp_path: Path) -> None:
    assert [
        core._closeout_candidate_gaps(Path("/x"), candidate, "head")
        for candidate in ({"exists": False}, {"exists": True, "worktree_exists": False})
    ] == [["candidate_branch_missing"], ["candidate_worktree_missing"]]
    repo = init_git_repo(tmp_path / "dirty")
    (repo / "residue.txt").write_text("dirty\n", encoding="utf-8")
    candidate = {"exists": True, "worktree_exists": True, "worktree_path": str(repo)}
    assert core._closeout_candidate_gaps(repo, candidate, "head") == ["candidate_worktree_dirty"]
    request = lifecycle.MutationRequest(
        command="closeout", apply=True, authorized=False, expect_head=None
    )
    decision = core.evaluate_closeout_mutation(request, root=tmp_path, current_head="x")
    assert {"authorization_required", "expect_head_required"} <= set(decision.gaps)
    blocked = lifecycle.MutationEvaluation(
        ok=False, state="blocked", gaps=("authorization_required",)
    )
    result = core.apply_land_to_candidate(
        root=init_git_repo(tmp_path / "blocked"),
        authorized=False,
        expect_head=None,
        admitted_decision=blocked,
    )
    assert result["required_gaps"] == ["authorization_required"]
    report = lanes.bind_work_lane_claim(
        root=tmp_path, claim_id="c1", branch="work/none", apply=False
    )
    assert "work_lane_not_found:work/none" in report["required_gaps"]
    db = tmp_path / ".ethos/state/state.sqlite"
    acquire_lease(db, subject="work/other", holder_ref="agent:test:case:owner")
    assert lanes._active_lease(db, "work/target") is None


def test_land_proof_failure_is_fail_closed(tmp_path: Path, monkeypatch) -> None:
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
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "h1\n", ""),
    )
    monkeypatch.setattr(
        core,
        "carry_executed_proof_record",
        lambda **_kwargs: {"ok": False, "required_gaps": ["proof_not_proven"]},
    )
    ready = lifecycle.MutationEvaluation(ok=True, state="land_ready")
    result = core.apply_land_to_candidate(
        root=tmp_path,
        authorized=True,
        expect_head="h1",
        admitted_decision=ready,
    )
    assert result["required_gaps"] == ["proof_not_proven"]


@pytest.mark.parametrize("case", _CASES)
def test_refresh_decision_matrix(tmp_path: Path, monkeypatch, case: list[object]) -> None:
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

    def fake_git(_root: Path, *args: str, **_kwargs):
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
        monkeypatch.setattr(refresh, name, replacement)
    if kind == "bootstrap":
        report = refresh.bootstrap_candidate(root=tmp_path, path=target, apply=apply)
    elif kind == "candidate":
        report = refresh.refresh_candidate_from_accepted(root=tmp_path)
    else:
        report = refresh.refresh_work_lane_base(root=tmp_path)
    assert (report["state"], report["required_gaps"]) == (
        state,
        [gap] if gap else [],
    )
