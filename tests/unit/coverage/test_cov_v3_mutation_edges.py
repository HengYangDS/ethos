from __future__ import annotations

import json
import sqlite3
import subprocess
from contextlib import closing
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
{"id":"bootstrap-git-failure","operation":"bootstrap","role":"accepted_root","dirty":false,"candidate_exists":false,"candidate_head":"c1","ancestor":false,"apply":true,"path_exists":false,"state":"blocked","gap":"candidate_worktree_add_failed"},
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
    return operation(repo=tmp_path, records_root=tmp_path, before={}, pre_effect={}, result={}, context=context, controls=dict(_CONTROLS), chronicle_ref="c", holder_ref="holder", owner_unavailable_recovery=False)  # fmt: skip


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
    report = lanes.bind_work_lane_claim(root=repo, claim_id="c", branch="work/none", apply=False)  # fmt: skip
    assert "work_lane_not_found:work/none" in report["required_gaps"]
    db = tmp_path / ".ethos/state/state.sqlite"
    acquire_lease(db, subject="work/other", holder_ref="agent:test:case:owner")
    active_lease = lanes._active_lease  # noqa: SLF001, RUF100 - lease lookup edge
    assert active_lease(db, "work/target") is None


def test_lane_start_input_and_git_failure_edges(tmp_path: Path, monkeypatch) -> None:
    repo = init_git_repo(tmp_path / "repo")
    invalid = lanes.start_work_lane(root=repo, name="x", holder_ref="bad")
    assert invalid["required_gaps"] == ["holder_ref_invalid"]
    planned = lanes.start_work_lane(
        root=repo,
        name="x",
        holder_ref="agent:test:case:owner",
    )
    assert planned["state"] == "planned"
    status = {
        "role": "accepted_root",
        "dirty": False,
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": str(repo),
            "head": "h",
        },
    }
    _setattrs(
        monkeypatch,
        lanes,
        {
            "workspace_status": lambda _root: status,
            "changed_paths": lambda _path: [],
            "run_git": lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "failed"),
        },
    )
    failed = lanes.start_work_lane(
        root=repo,
        name="x",
        holder_ref="agent:test:case:owner",
        apply=True,
    )
    assert failed["required_gaps"] == ["worktree_add_failed"]
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    blocked = lanes.start_work_lane(root=repo, name="occupied", path=occupied, holder_ref="agent:test:case:owner", apply=True)  # fmt: skip
    assert blocked["required_gaps"] == ["lane_start_target_path_exists"]
    occupied.rmdir()
    acquire, carrier_gap = lanes.acquire_lease, lanes._lane_start_carrier_gap  # noqa: SLF001, RUF100 - exact acquisition edges  # fmt: skip
    monkeypatch.setattr(lanes, "acquire_lease", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("lease_acquire_failed")))  # fmt: skip
    assert lanes.start_work_lane(root=repo, name="acquire", holder_ref="agent:test:case:owner", apply=True)["required_gaps"] == ["lease_acquire_failed"]  # fmt: skip
    lease = {"expected_head": "h", "holder_ref": "agent:test:case:owner", "lease_id": "lease:x", "epoch": 1, "expires_at": "x", "payload_sha256": "a" * 64}  # fmt: skip
    monkeypatch.setattr(lanes, "acquire_lease", lambda *_args, **_kwargs: lease)
    gaps = iter(("", "lane_start_target_path_exists"))
    monkeypatch.setattr(lanes, "_lane_start_carrier_gap", lambda *_args, **_kwargs: next(gaps))
    raced = lanes.start_work_lane(root=repo, name="raced", holder_ref="agent:test:case:owner", apply=True)  # fmt: skip
    assert raced["required_gaps"] == ["lane_creation_compensation_failed", "lane_start_target_path_ownership_unknown"]  # fmt: skip
    monkeypatch.setattr(lanes, "acquire_lease", acquire)
    monkeypatch.setattr(lanes, "_lane_start_carrier_gap", carrier_gap)


def test_lane_start_uses_captured_candidate_and_preserves_foreign_same_head_ref(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    target = tmp_path / "lane"
    captured, current = "a" * 40, {"head": "a" * 40}
    status = {
        "role": "accepted_root",
        "dirty": False,
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": str(repo),
            "head": captured,
        },
    }

    def acquire(_database, **kwargs):
        assert kwargs["payload"]["expected_head"] == captured
        current["head"] = "b" * 40
        return {
            "expected_head": captured,
            "holder_ref": kwargs["holder_ref"],
            "lease_id": "lease:x",
            "epoch": 1,
            "expires_at": "2099-01-01T00:00:00+00:00",
            "payload_sha256": "c" * 64,
        }

    def git(_root, *args, **_kwargs):
        assert current["head"] != captured
        assert args[-1] == captured
        return subprocess.CompletedProcess(args, 0, "", "")

    _setattrs(
        monkeypatch,
        lanes,
        {
            "workspace_status": lambda _root: status,
            "changed_paths": lambda _path: [],
            "acquire_lease": acquire,
            "run_git": git,
            "_exact_worktree": lambda *_args, **kwargs: kwargs["head"] == captured,
            "_started_worktree": lambda **_kwargs: {},
        },
    )
    started = lanes.start_work_lane(
        root=repo,
        name="x",
        path=target,
        holder_ref="agent:test:case:owner",
        apply=True,
    )
    assert started["base_head"] == captured

    monkeypatch.setattr(lanes, "_exact_worktree", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(lanes, "ref_head", lambda *_args: captured)
    monkeypatch.setattr(lanes, "run_git", pytest.fail)
    retained = lanes._abort_lane_start(  # noqa: SLF001, RUF100 - exact saga boundary
        repo,
        target=target,
        branch="work/x",
        lease=started["lease"],
        completed=subprocess.CompletedProcess([], 1, "", "failed"),
    )
    assert retained["lease_state"] == "retained"
    assert retained["required_gaps"] == [
        "lane_creation_compensation_failed",
        "lane_start_target_ref_ownership_unknown",
    ]


def test_lane_start_failed_add_preserves_concurrent_same_shape_carrier(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    target = tmp_path / "lane"
    head = "a" * 40
    status = {
        "role": "accepted_root",
        "dirty": False,
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": str(repo),
            "head": head,
        },
    }
    lease = {
        "expected_head": head,
        "holder_ref": "agent:test:case:owner",
        "lease_id": "lease:x",
        "epoch": 1,
        "expires_at": "2099-01-01T00:00:00+00:00",
        "payload_sha256": "a" * 64,
    }

    def git(_root, *args, **_kwargs):
        if args[:2] == ("worktree", "add"):
            target.mkdir()
            return subprocess.CompletedProcess(args, 1, "", "lost race")
        pytest.fail(f"foreign carrier cleanup attempted: {args}")

    _setattrs(
        monkeypatch,
        lanes,
        {
            "workspace_status": lambda _root: status,
            "changed_paths": lambda _path: [],
            "acquire_lease": lambda *_args, **_kwargs: lease,
            "_lane_start_carrier_gap": lambda *_args, **_kwargs: "",
            "_exact_worktree": lambda *_args, **_kwargs: target.exists(),
            "ref_head": lambda *_args: head if target.exists() else "",
            "run_git": git,
        },
    )

    report = lanes.start_work_lane(
        root=repo,
        name="x",
        path=target,
        holder_ref="agent:test:case:owner",
        apply=True,
    )

    assert target.exists()
    assert report["lease_state"] == "retained"
    assert report["required_gaps"] == [
        "lane_creation_compensation_failed",
        "lane_start_target_path_ownership_unknown",
    ]


def test_lane_start_abort_retains_lease_for_unknown_or_failed_cleanup(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    branch = "work/x"
    target = tmp_path / "lane"
    lease = {
        "expected_head": "h",
        "holder_ref": "agent:test:case:owner",
        "lease_id": "lease:x",
        "epoch": 1,
        "expires_at": "2099-01-01T00:00:00+00:00",
        "payload_sha256": "a" * 64,
    }
    monkeypatch.setattr(lanes, "_exact_worktree", lambda *_args, **_kwargs: False)
    target.mkdir()
    unknown = lanes._abort_lane_start(  # noqa: SLF001, RUF100 - exact saga boundary
        repo,
        target=target,
        branch=branch,
        lease=lease,
        completed=subprocess.CompletedProcess([], 1, "", "failed"),
    )
    assert unknown["lease_state"] == "retained"
    assert unknown["required_gaps"] == [
        "lane_creation_compensation_failed",
        "lane_start_target_path_ownership_unknown",
    ]
    target.rmdir()
    monkeypatch.setattr(lanes, "ref_head", lambda *_args: "")
    monkeypatch.setattr(
        lanes,
        "revoke_lease",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("lease_revoke_failed")),
    )
    retained = lanes._abort_lane_start(  # noqa: SLF001, RUF100 - exact saga boundary
        repo,
        target=target,
        branch=branch,
        lease=lease,
        completed=subprocess.CompletedProcess([], 1, "", "failed"),
    )
    assert retained["carrier_cleanup"] == {
        "worktree_removed": True,
        "ref_removed": True,
    }
    assert retained["lease_state"] == "retained"
    assert retained["required_gaps"] == [
        "lane_creation_compensation_failed",
        "lease_revoke_failed",
    ]


@pytest.mark.parametrize("target_state", ["missing", "present"])
def test_lane_start_abort_removes_exact_carriers(
    tmp_path: Path, monkeypatch, target_state: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    target_exists = target_state == "present"
    target, head = tmp_path / "lane", "h"
    if target_exists:
        target.mkdir()
    lease = {"expected_head": head, "holder_ref": "agent:test:case:owner", "lease_id": "lease:x", "epoch": 1, "expires_at": "x", "payload_sha256": "a" * 64}  # fmt: skip
    exact, refs = iter((True, False)), iter((head, ""))

    def git(_root, *args, **_kwargs):
        if args[:2] == ("worktree", "remove") and target_exists:
            target.rmdir()
        assert ("--force" in args) is not target_exists if args[:2] == ("worktree", "remove") else args[:2] == ("update-ref", "-d")  # fmt: skip
        return subprocess.CompletedProcess(args, 0, "", "")

    _setattrs(monkeypatch, lanes, {"_exact_worktree": lambda *_args, **_kwargs: next(exact), "ref_head": lambda *_args: next(refs), "run_git": git, "revoke_lease": lambda *_args, **_kwargs: {}})  # fmt: skip
    report = lanes._abort_lane_start(repo, target=target, branch="work/x", lease=lease, completed=subprocess.CompletedProcess([], 0, "", "failed"))  # noqa: SLF001, RUF100 - exact saga boundary  # fmt: skip
    assert report["lease_state"] == "revoked"


def test_lane_start_abort_reports_carrier_cleanup_failures(tmp_path: Path, monkeypatch) -> None:
    repo = init_git_repo(tmp_path / "repo")
    target, head = tmp_path / "lane", "h"
    lease = {"expected_head": head, "holder_ref": "agent:test:case:owner", "lease_id": "lease:x", "epoch": 1, "expires_at": "x", "payload_sha256": "a" * 64}  # fmt: skip
    _setattrs(monkeypatch, lanes, {"_exact_worktree": lambda *_args, **_kwargs: True, "run_git": lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "")})  # fmt: skip
    worktree = lanes._abort_lane_start(repo, target=target, branch="work/x", lease=lease, completed=subprocess.CompletedProcess([], 0, "", "failed"))  # noqa: SLF001, RUF100 - exact saga boundary  # fmt: skip
    assert worktree["required_gaps"][-1] == "lane_start_worktree_cleanup_failed"
    exact, git_results = iter((True, False)), iter((0, 1))
    _setattrs(monkeypatch, lanes, {"_exact_worktree": lambda *_args, **_kwargs: next(exact), "ref_head": lambda *_args: head, "run_git": lambda *_args, **_kwargs: subprocess.CompletedProcess([], next(git_results), "", "")})  # fmt: skip
    ref = lanes._abort_lane_start(repo, target=target, branch="work/x", lease=lease, completed=subprocess.CompletedProcess([], 0, "", "failed"))  # noqa: SLF001, RUF100 - exact saga boundary  # fmt: skip
    assert ref["required_gaps"][-1] == "lane_start_ref_cleanup_failed"
    _setattrs(monkeypatch, lanes, {"_exact_worktree": lambda *_args, **_kwargs: False, "ref_head": lambda *_args: "changed"})  # fmt: skip
    changed = lanes._abort_lane_start(repo, target=target, branch="work/x", lease=lease, completed=subprocess.CompletedProcess([], 0, "", "failed"))  # noqa: SLF001, RUF100 - exact saga boundary  # fmt: skip
    assert changed["required_gaps"][-1] == "lane_start_ref_changed"


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
        failed = case["id"] == "bootstrap-git-failure" and args[:2] == ("worktree", "add")
        return subprocess.CompletedProcess([], int(failed), "h1\n" if args == ("rev-parse", "HEAD") else "", "worktree add failed" if failed else "")  # fmt: skip

    _setattrs(monkeypatch, refresh, {"repo_root": lambda root: root, "load_branch_role_policy": lambda _root: SimpleNamespace(candidate_branch="candidate/dev"), "workspace_status": lambda _root: status, "changed_paths": lambda _path: [], "is_ancestor": lambda *_args: case["ancestor"], "run_git": git})  # fmt: skip
    if case["operation"] == "bootstrap":
        report = refresh.bootstrap_candidate(root=tmp_path, path=target, apply=case["apply"])
    elif case["operation"] == "candidate":
        report = refresh.refresh_candidate_from_accepted(root=tmp_path)
    else:
        report = refresh.refresh_work_lane_base(root=tmp_path)
    assert (report["state"], report["required_gaps"]) == (case["state"], [case["gap"]] if case["gap"] else [])  # fmt: skip


def test_candidate_refresh_reports_reset_failure(tmp_path: Path, monkeypatch) -> None:
    status = {
        "role": "accepted_root",
        "dirty": False,
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": str(tmp_path),
            "head": "candidate",
        },
    }

    def git(_root: Path, *args: str, **_kwargs):
        return subprocess.CompletedProcess(
            [],
            int(args[:2] == ("reset", "--hard")),
            "accepted\n" if args == ("rev-parse", "HEAD") else "",
            "reset failed" if args[:2] == ("reset", "--hard") else "",
        )

    _setattrs(
        monkeypatch,
        refresh,
        {
            "repo_root": lambda root: root,
            "load_branch_role_policy": lambda _root: SimpleNamespace(
                candidate_branch="candidate/dev"
            ),
            "workspace_status": lambda _root: status,
            "changed_paths": lambda _path: [],
            "run_git": git,
        },
    )
    report = refresh.refresh_candidate_from_accepted(
        root=tmp_path,
        apply=True,
        authorized=True,
        expect_head="accepted",
    )
    assert report["required_gaps"] == ["candidate_refresh_from_accepted_failed"]


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

    def locked(_path):
        raise sqlite3.OperationalError("locked")  # noqa: EM101, RUF100 - injected lock failure

    monkeypatch.setattr(unbound.sqlite3, "connect", locked)
    monkeypatch.setattr(unbound, "state_database", lambda _repo: tmp_path / "state.sqlite")
    monkeypatch.setattr(unbound.observation, "public_observation", lambda value: value)
    assert _finish_retirement(tmp_path, {"lease_relinquished": {"lease_id": "l"}})["lease_relinquish_rolled_back"] == {"lease_id": "l"}  # fmt: skip
    assert _finish_retirement(tmp_path, {})["required_gaps"] == ["unbound_retire_active_lease"]


def test_unbound_lease_recovery_argument_edges() -> None:
    observed = {
        obs.HAS_ACTIVE_LEASE: True,
        "branch": "work/x",
        "active_lease": {
            "holder_ref": "agent:test:source",
            "lease_id": "lease:source",
            "epoch": 1,
            "expected_head": "h",
            "expires_at": "x",
            "payload_sha256": "y",
        },
    }
    with closing(sqlite3.connect(":memory:")) as connection:
        assert (
            unbound.relinquish_owned_lease(
                connection,
                observed=observed,
                holder_ref="agent:test:recovery",
            )
            is None
        )
    missing_branch = dict(observed)
    missing_branch.pop("branch")
    with closing(sqlite3.connect(":memory:")) as connection:
        assert (
            unbound.relinquish_owned_lease(
                connection,
                observed=missing_branch,
                holder_ref="agent:test:source",
            )
            is None
        )


def test_unbound_pre_effect_and_receipt_edges(tmp_path: Path, monkeypatch) -> None:
    before = {"status": {}, "accepted_head": "h", "protected_refs": {}, "claim_id": "c", "observation_sha256": "s", "bind": 1}  # fmt: skip
    monkeypatch.setattr(unbound.policy, "accepted_control_root", lambda *_args, **_kw: (tmp_path, ""))  # fmt: skip
    monkeypatch.setattr(unbound.records, "repository_records_root", lambda _repo: tmp_path)
    monkeypatch.setattr(unbound, "state_database", lambda _repo: tmp_path / "state.sqlite")
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
    _setattrs(monkeypatch, unbound, {"_observe": lambda *_args, **_kw: next(observations), "relinquish_owned_lease": lambda *_args, **_kw: {}, "_delete_ref_transaction": lambda *_args, **_kw: SimpleNamespace(returncode=0, stderr=""), "_commit_or_restore": lambda *_args: None, "_write": lambda *_args: ("", "receipt_gap")})  # fmt: skip
    monkeypatch.setattr(unbound.sqlite3, "connect", lambda _path: Conn())
    _setattrs(monkeypatch, unbound.policy, {"lease_recovery_gaps": lambda *_args, **_kw: [], "post_effect_gaps": lambda **_kw: []})  # fmt: skip
    monkeypatch.setattr(unbound.observation, "operation_bindings", lambda _value: {})
    _setattrs(monkeypatch, unbound.records, {"effect_summary": lambda _value: {}, "receipt_payload": lambda **_kw: {}, "receipt_path": lambda *_args: tmp_path / "receipt"})  # fmt: skip
    assert _finish_retirement(tmp_path, {"operation_id": "op"})["required_gaps"] == ["receipt_gap"]
