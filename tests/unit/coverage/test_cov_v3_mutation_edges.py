from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.lane_lifecycle.refresh as refresh
import ethos_core.contracts.lifecycle.core as lifecycle
from ethos.adapters.mutation import core
from ethos.adapters.mutation import lanes
from ethos.adapters.mutation import proof as mutation_proof
from ethos.adapters.mutation.lane_retirement.unbound import core as unbound
from ethos.adapters.mutation.lane_retirement.unbound.observation import core as obs
from ethos.adapters.mutation.lane_retirement.unbound.policy import core as policy
from ethos.adapters.mutation.lane_retirement.unbound.records import core as records
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from tests.support.contract_helpers import init_git_repo

_REFRESH_CASES = json.loads(
    """[
{"id":"bootstrap-wrong-role","operation":"bootstrap","role":"other","dirty":false,"candidate_exists":false,"candidate_head":"c1","ancestor":false,"apply":false,"path_exists":false,"state":"blocked","gap":"candidate_bootstrap_requires_clean_accepted_root"},
{"id":"bootstrap-present","operation":"bootstrap","role":"accepted_root","dirty":false,"candidate_exists":true,"candidate_head":"c1","ancestor":false,"apply":false,"path_exists":false,"state":"present","gap":""},
{"id":"bootstrap-planned","operation":"bootstrap","role":"accepted_root","dirty":false,"candidate_exists":false,"candidate_head":"c1","ancestor":false,"apply":false,"path_exists":false,"state":"planned","gap":""},
{"id":"bootstrap-path-exists","operation":"bootstrap","role":"accepted_root","dirty":false,"candidate_exists":false,"candidate_head":"c1","ancestor":false,"apply":true,"path_exists":true,"state":"blocked","gap":"candidate_worktree_path_exists"},
{"id":"bootstrap-git-failure","operation":"bootstrap","role":"accepted_root","dirty":false,"candidate_exists":false,"candidate_head":"c1","ancestor":false,"apply":true,"path_exists":false,"state":"blocked","gap":"candidate_bootstrap_failed"},
{"id":"candidate-wrong-role","operation":"candidate","role":"work_lane","dirty":false,"candidate_exists":true,"candidate_head":"c1","ancestor":true,"apply":false,"path_exists":false,"state":"blocked","gap":"accepted_root_required"},
{"id":"candidate-dirty","operation":"candidate","role":"accepted_root","dirty":true,"candidate_exists":true,"candidate_head":"c1","ancestor":true,"apply":false,"path_exists":false,"state":"blocked","gap":"accepted_root_dirty"},
{"id":"candidate-current","operation":"candidate","role":"accepted_root","dirty":false,"candidate_exists":true,"candidate_head":"h1","ancestor":true,"apply":false,"path_exists":false,"state":"base_current","gap":""},
{"id":"candidate-refreshable","operation":"candidate","role":"accepted_root","dirty":false,"candidate_exists":true,"candidate_head":"c1","ancestor":true,"apply":false,"path_exists":false,"state":"ready_to_refresh_from_accepted","gap":""},
{"id":"lane-dirty","operation":"lane","role":"work_lane","dirty":true,"candidate_exists":true,"candidate_head":"c1","ancestor":false,"apply":false,"path_exists":false,"state":"blocked","gap":"work_lane_dirty"},
{"id":"lane-current","operation":"lane","role":"work_lane","dirty":false,"candidate_exists":true,"candidate_head":"c1","ancestor":true,"apply":false,"path_exists":false,"state":"base_current","gap":""}
]"""
)
_CONTROLS = json.loads('{"branch":"work/x","expect_head":"h","reason":"r","apply":true,"authorized":true,"break_glass":true,"confirm_irreversible":true}')  # fmt: skip


def _setattrs(monkeypatch, target, values: dict[str, object]) -> None:
    for name, value in values.items():
        monkeypatch.setattr(target, name, value)


def _apply_retirement(tmp_path: Path, before: dict[str, object]) -> dict[str, object]:
    operation = unbound._apply_retirement  # noqa: SLF001, RUF100 - internal retirement edge
    return operation(repo=tmp_path, before=before, result={}, controls=dict(_CONTROLS), chronicle_ref="c", holder_ref="holder", owner_unavailable_recovery=False)  # fmt: skip


def _finish_retirement(tmp_path: Path, context: dict[str, object]) -> dict[str, object]:
    operation = unbound._relinquish_then_delete  # noqa: SLF001, RUF100 - internal effect edge
    return operation(repo=tmp_path, control_root=tmp_path, records_root=tmp_path, before={}, pre_effect={}, result={}, context=context, controls=dict(_CONTROLS), chronicle_ref="c", holder_ref="holder", owner_unavailable_recovery=False)  # fmt: skip


def test_closeout_and_lane_guards(tmp_path: Path) -> None:
    candidate_gaps = core._closeout_candidate_gaps  # noqa: SLF001, RUF100 - fail-closed candidate edges
    candidates = ({"exists": False}, {"exists": True, "worktree_exists": False})
    assert [candidate_gaps(Path("/x"), item, "h") for item in candidates] == [["candidate_branch_missing"], ["candidate_worktree_missing"]]  # fmt: skip
    repo = init_git_repo(tmp_path / "dirty")
    (repo / "x").write_text("x", encoding="utf-8")
    candidate = {"exists": True, "worktree_exists": True, "worktree_path": str(repo)}
    assert candidate_gaps(repo, candidate, "h") == ["candidate_worktree_dirty"]
    request = lifecycle.MutationRequest(command="closeout", apply=True, authorized=False, expect_head=None)  # fmt: skip
    decision = core.evaluate_closeout_mutation(request, root=tmp_path, current_head="x")
    assert {"authorization_required", "expect_head_required"} <= set(decision.gaps)
    blocked = lifecycle.MutationEvaluation(ok=False, state="blocked", gaps=("authorization_required",))  # fmt: skip
    result = core.apply_land_to_candidate(root=init_git_repo(tmp_path / "blocked"), authorized=False, expect_head=None, admitted_decision=blocked)  # fmt: skip
    assert result["required_gaps"] == ["authorization_required"]
    report = lanes.bind_work_lane_claim(root=tmp_path, claim_id="c", branch="work/none", apply=False)  # fmt: skip
    assert "work_lane_not_found:work/none" in report["required_gaps"]
    db = tmp_path / ".ethos/state/state.sqlite"
    acquire_lease(db, subject="work/other", holder_ref="agent:test:case:owner")
    active_lease = lanes._active_lease  # noqa: SLF001, RUF100 - lease lookup edge
    assert active_lease(db, "work/target") is None


def test_land_proof_failure(tmp_path: Path, monkeypatch) -> None:
    _setattrs(monkeypatch, core, {"candidate_base_report": lambda **_kw: {"ok": True, "path": str(tmp_path / "candidate"), "required_gaps": []}, "run_git": lambda *_args, **_kw: subprocess.CompletedProcess([], 0, "h1\n", ""), "carry_executed_proof_record": lambda **_kw: {"ok": False, "required_gaps": ["proof_not_proven"]}})  # fmt: skip
    ready = lifecycle.MutationEvaluation(ok=True, state="land_ready")
    result = core.apply_land_to_candidate(root=tmp_path, authorized=True, expect_head="h1", admitted_decision=ready)  # fmt: skip
    assert result["required_gaps"] == ["proof_not_proven"]


def test_closeout_blocks_when_proof_carry_fails(tmp_path: Path) -> None:
    policy = SimpleNamespace(
        accepted_branch="dev", candidate_branch="candidate/dev", release_mirror="independent"
    )
    request = core.CloseoutRequest(
        root=tmp_path,
        policy=policy,
        current_head="a",
        candidate_head="b",
        candidate_path=tmp_path,
        worktrees=[],
    )
    dependencies = core.CloseoutDependencies(
        run_git=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "a\n", ""),
        is_ancestor=lambda *_args: True,
        carry_proof=lambda **_kwargs: {"ok": False, "required_gaps": ["proof_not_proven"]},
        discard_proof=lambda *_args: None,
    )
    result = core.promote_candidate_to_accepted(request, dependencies=dependencies)
    assert result["ok"] is False
    assert result["required_gaps"] == ["proof_not_proven"]


def test_discard_executed_proof_is_idempotent(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "proof")
    head = "b" * 40
    mutation_proof.record_executed_proof(repo, {"id": "proof", "head": head, "runs": []})
    assert mutation_proof.discard_executed_proof(repo, head) is True
    assert mutation_proof.discard_executed_proof(repo, head) is False


@pytest.mark.parametrize("case", _REFRESH_CASES, ids=[case["id"] for case in _REFRESH_CASES])
def test_refresh_matrix(tmp_path: Path, monkeypatch, case: dict[str, object]) -> None:
    target = tmp_path / "candidate"
    if case["operation"] == "bootstrap" and case["path_exists"]:
        target.mkdir()
    candidate = {"exists": case["candidate_exists"], "worktree_exists": case["candidate_exists"], "worktree_path": str(tmp_path), "head": case["candidate_head"]}  # fmt: skip
    status = {"role": case["role"], "dirty": case["dirty"], "branch": "work/x", "candidate": candidate}  # fmt: skip

    def git(_root: Path, *args: str, **_kwargs):
        branch_failed = args[:1] == ("branch",)
        return subprocess.CompletedProcess([], int(branch_failed), "h1\n" if args == ("rev-parse", "HEAD") else "", "branch failed" if branch_failed else "")  # fmt: skip

    _setattrs(monkeypatch, refresh, {"repo_root": lambda root: root, "load_branch_role_policy": lambda _root: SimpleNamespace(candidate_branch="candidate/dev"), "workspace_status": lambda _root: status, "changed_paths": lambda _path: [], "is_ancestor": lambda *_args: case["ancestor"], "run_git": git})  # fmt: skip
    if case["operation"] == "bootstrap":
        report = refresh.bootstrap_candidate(root=tmp_path, path=target, apply=case["apply"])
    elif case["operation"] == "candidate":
        report = refresh.refresh_candidate_from_accepted(root=tmp_path)
    else:
        report = refresh.refresh_work_lane_base(root=tmp_path)
    assert (report["state"], report["required_gaps"]) == (case["state"], [case["gap"]] if case["gap"] else [])  # fmt: skip


def test_unbound_observation_policy_records(tmp_path: Path, monkeypatch) -> None:
    regular_bytes = obs._regular_bytes  # noqa: SLF001, RUF100 - unreadable file edge
    assert regular_bytes(tmp_path / "missing") is None
    assert obs.chronicle_path(tmp_path, "evidence/chronicle/a/../b") is None

    class BadRepo:
        def __truediv__(self, _other):
            return self

        def resolve(self):
            raise OSError

    assert obs.chronicle_path(BadRepo(), "evidence/chronicle/x") is None

    def claim_local(claim_id: str) -> bool:
        return bool(obs.claim_observation(tmp_path, accepted_branch="dev", claim_id=claim_id)["has_local_claim"])  # fmt: skip

    assert not claim_local("missing")
    claim = tmp_path / "evidence/claims/x.toml"
    claim.parent.mkdir(parents=True)
    claim.write_text("[", encoding="utf-8")
    assert not claim_local("x")
    monkeypatch.setattr(obs.tomllib, "loads", lambda _value: [])
    claim.write_text("x", encoding="utf-8")
    assert not claim_local("x")
    monkeypatch.setattr(obs.tomllib, "loads", lambda _value: {"claim": {"id": "x", "state": "active"}})  # fmt: skip
    monkeypatch.setattr(obs, "git_show_bytes", lambda *_args: None)
    assert claim_local("x")
    assert obs.retirement_bindings({"branch": "work/x"}) == {}
    entry = obs._entry  # noqa: SLF001, RUF100 - missing ledger edge
    assert entry({}, "work/x") is None
    assert policy.active_lease_gaps({obs.HAS_ACTIVE_LEASE: True}) == ["unbound_retire_active_lease"]
    assert policy.accepted_control_root({"worktrees": "bad"}, accepted_head="h")[0] is None
    assert policy.accepted_control_root({"worktrees": ["bad"]}, accepted_head="h")[0] is None
    assert policy.accepted_control_root({"worktrees": [{"role": "accepted_root", "path": str(tmp_path / "missing")}]}, accepted_head="h")[0] is None  # fmt: skip
    monkeypatch.setattr(obs, "ref_head", lambda *_args: "other")
    assert policy.accepted_control_root({"worktrees": [{"role": "accepted_root", "path": str(tmp_path)}]}, accepted_head="h")[1].endswith("stale")  # fmt: skip
    path = tmp_path / "record"
    path.mkdir()
    with pytest.raises(ValueError, match="unsafe"):
        records.read_record(path, kind=records.ATTEMPT_KIND)
    path.rmdir()
    path.write_text("[", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid"):
        records.read_record(path, kind=records.ATTEMPT_KIND)
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError, match="invalid"):
        records.read_record(path, kind=records.ATTEMPT_KIND)
    assert not records.valid_lease_relinquishment([], {}, subject="x")
    assert not records.valid_lease_relinquishment({"active": None}, {}, subject="x")
    assert records.stable_gap(ValueError("known")) == "known"
    assert records.stable_gap(ValueError("bad\nlong")) == "unbound_retire_effect_failed"


def test_unbound_record_collision(tmp_path: Path, monkeypatch) -> None:
    payload = {"kind": records.ATTEMPT_KIND}
    monkeypatch.setattr(records, "validate_record", lambda *_args, **_kw: None)

    def collide(*_args):
        raise FileExistsError

    monkeypatch.setattr(records.os, "link", collide)
    seen = iter(({}, payload))
    monkeypatch.setattr(records, "read_record", lambda *_args, **_kw: next(seen))
    assert records.write_record(tmp_path / "same", payload, kind=records.ATTEMPT_KIND).endswith("same")  # fmt: skip
    seen = iter(({}, {"other": True}))
    monkeypatch.setattr(records, "read_record", lambda *_args, **_kw: next(seen))
    with pytest.raises(ValueError, match="collision"):
        records.write_record(tmp_path / "collision", payload, kind=records.ATTEMPT_KIND)


def test_unbound_core_exception_edges(tmp_path: Path, monkeypatch) -> None:
    def fail_write(*_args, **_kwargs):
        raise ValueError("write_gap")  # noqa: EM101, RUF100 - injected record failure

    monkeypatch.setattr(unbound.records, "write_record", fail_write)
    write = unbound._write  # noqa: SLF001, RUF100 - stable write edge
    assert write(tmp_path, {}, "kind") == ("", "write_gap")
    _setattrs(monkeypatch, unbound, {"repo_root": lambda root: root, "_observe": lambda *_args, **_kw: {}, "_admission_gaps": lambda *_args, **_kw: []})  # fmt: skip
    monkeypatch.setattr(unbound.policy, "lease_recovery_gaps", lambda *_args, **_kw: ["lease_gap"])
    monkeypatch.setattr(unbound.lane_retirement_shared, "current_holder_ref", lambda: "holder")
    monkeypatch.setattr(unbound.reporting, "report", lambda **kw: {"required_gaps": kw["gaps"]})
    assert unbound.retire_unbound_work_lane_ref(root=tmp_path, branch="work/x")["required_gaps"] == ["lease_gap"]  # fmt: skip
    before = {"status": {}, "accepted_head": "h", "protected_refs": {}, "claim_id": "c", "observation_sha256": "s"}  # fmt: skip
    monkeypatch.setattr(unbound.policy, "accepted_control_root", lambda *_args, **_kw: (None, "no_root"))  # fmt: skip
    monkeypatch.setattr(unbound.reporting, "blocked", lambda result, gaps: result | {"required_gaps": gaps})  # fmt: skip
    assert _apply_retirement(tmp_path, before)["required_gaps"] == ["no_root"]
    observed = {obs.HAS_ACTIVE_LEASE: True, "branch": "work/x", "active_lease": {"holder_ref": "holder", "lease_id": "l", "epoch": 1, "expected_head": "h"}}  # fmt: skip
    monkeypatch.setattr(unbound, "revoke_lease", lambda *_args, **_kw: {"revoked": True})
    assert unbound.relinquish_owned_lease(tmp_path, observed=observed, holder_ref="holder") == {"revoked": True}  # fmt: skip

    def locked(_path):
        raise sqlite3.OperationalError("locked")  # noqa: EM101, RUF100 - injected lock failure

    monkeypatch.setattr(unbound, "initialize_state", locked)
    monkeypatch.setattr(unbound.observation, "public_observation", lambda value: value)
    assert _finish_retirement(tmp_path, {"lease_relinquished": {"lease_id": "l"}})["lease_relinquish_rolled_back"] == {"lease_id": "l"}  # fmt: skip
    assert _finish_retirement(tmp_path, {})["required_gaps"] == ["unbound_retire_active_lease"]


def test_unbound_lease_recovery_argument_edges(tmp_path: Path, monkeypatch) -> None:
    observed = {
        obs.HAS_ACTIVE_LEASE: True,
        "branch": "work/x",
        "active_lease": {
            "holder_ref": "agent:test:source",
            "lease_id": "lease:source",
            "epoch": 1,
            "expected_head": "h",
        },
    }
    assert (
        unbound._lease_relinquish_arguments(  # noqa: SLF001, RUF100
            observed=observed,
            holder_ref="agent:test:recovery",
            owner_unavailable_recovery=False,
        )
        is None
    )
    missing_branch = dict(observed)
    missing_branch.pop("branch")
    assert (
        unbound._lease_relinquish_arguments(  # noqa: SLF001, RUF100
            observed=missing_branch,
            holder_ref="agent:test:source",
            owner_unavailable_recovery=False,
        )
        is None
    )

    seen: dict[str, object] = {}

    def revoke_owner_unavailable(_database: Path, **kwargs):
        seen.update(kwargs)
        return {"revoked": True}

    monkeypatch.setattr(unbound, "revoke_owner_unavailable_lease", revoke_owner_unavailable)
    assert unbound.relinquish_owned_lease(
        tmp_path,
        observed=observed,
        holder_ref="agent:test:recovery",
        owner_unavailable_recovery=True,
    ) == {"revoked": True}
    assert seen == {
        "subject": "work/x",
        "source_holder_ref": "agent:test:source",
        "expected_lease_id": "lease:source",
        "expected_epoch": 1,
        "expected_head": "h",
    }


def test_unbound_pre_effect_and_receipt_edges(tmp_path: Path, monkeypatch) -> None:
    before = {"status": {}, "accepted_head": "h", "protected_refs": {}, "claim_id": "c", "observation_sha256": "s", "bind": 1}  # fmt: skip
    monkeypatch.setattr(unbound.policy, "accepted_control_root", lambda *_args, **_kw: (tmp_path, ""))  # fmt: skip
    _setattrs(monkeypatch, unbound.records, {"operation_id": lambda **_kw: "op:x", "attempt_payload": lambda **_kw: {}, "attempt_path": lambda *_args: tmp_path / "attempt"})  # fmt: skip
    monkeypatch.setattr(unbound.reporting, "blocked", lambda result, gaps: result | {"required_gaps": gaps})  # fmt: skip
    monkeypatch.setattr(unbound, "_write", lambda *_args: ("", "write_gap"))
    assert _apply_retirement(tmp_path, before)["required_gaps"] == ["write_gap"]
    monkeypatch.setattr(unbound, "_write", lambda *_args: ("attempt", ""))
    monkeypatch.setattr(unbound, "_observe", lambda *_args, **_kw: {"bind": 2})
    monkeypatch.setattr(unbound, "_admission_gaps", lambda *_args, **_kw: [])
    monkeypatch.setattr(unbound.policy, "lease_recovery_gaps", lambda *_args, **_kw: [])
    monkeypatch.setattr(unbound.observation, "operation_bindings", lambda value: {"bind": value["bind"]})  # fmt: skip
    monkeypatch.setattr(unbound.observation, "public_observation", lambda value: value)
    assert _apply_retirement(tmp_path, before)["required_gaps"] == ["unbound_retire_pre_effect_observation_stale"]  # fmt: skip

    class Conn:
        def execute(self, *_args):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    observations = iter(({}, {}))
    _setattrs(monkeypatch, unbound, {"initialize_state": lambda _path: None, "_observe": lambda *_args, **_kw: next(observations), "relinquish_owned_lease": lambda *_args, **_kw: {}, "_delete_ref_transaction": lambda *_args, **_kw: SimpleNamespace(returncode=0, stderr=""), "_commit_or_restore": lambda *_args: None, "_write": lambda *_args: ("", "receipt_gap")})  # fmt: skip
    monkeypatch.setattr(unbound.sqlite3, "connect", lambda _path: Conn())
    _setattrs(monkeypatch, unbound.policy, {"lease_recovery_gaps": lambda *_args, **_kw: [], "post_effect_gaps": lambda **_kw: []})  # fmt: skip
    monkeypatch.setattr(unbound.observation, "operation_bindings", lambda _value: {})
    _setattrs(monkeypatch, unbound.records, {"effect_summary": lambda _value: {}, "receipt_payload": lambda **_kw: {}, "receipt_path": lambda *_args: tmp_path / "receipt"})  # fmt: skip
    assert _finish_retirement(tmp_path, {"operation_id": "op"})["required_gaps"] == ["receipt_gap"]
