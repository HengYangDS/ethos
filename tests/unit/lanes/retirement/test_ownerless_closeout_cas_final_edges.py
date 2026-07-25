from __future__ import annotations

import hashlib
import json
import subprocess
from unittest.mock import MagicMock

import pytest

import ethos.adapters.mutation.resolution._effects as effects
from ethos.adapters.mutation.resolution.observation import observe_lane
from ethos_core.contracts.resolution.lane import LaneResolutionDecision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import orphan_work_lane

_EXECUTOR = "agent:codex:thread:executor"


def _decision(path, observation) -> tuple[dict[str, object], bytes]:
    payload = LaneResolutionDecision(
        decision_id="lane-decision:00000000-0000-4000-8000-000000000023",
        disposition="retire",
        observation=observation,
        evidence_refs=("evidence:cas-final-edge-review",),
        chronicle_ref="evidence/chronicle/cas-final-edge-review.md",
        chronicle_digest="c" * 64,
        recovery_plan="Reconcile the exact target ref and worktree registration before retrying.",
        reason="Exercise the remaining transactional CAS failure edges.",
        break_glass=True,
    ).to_payload()
    raw = (json.dumps(payload, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return payload, raw


def _wcp(raw: bytes, observation, accepted_head: str) -> dict[str, object]:
    return {
        "schema_version": "workstation.repo-family-governance.v1",
        "decision_sha256": hashlib.sha256(raw).hexdigest(),
        "executor_ref": _EXECUTOR,
        "observation_digest": observation.digest(),
        "chronicle_digest": "c" * 64,
        "source": {"head": accepted_head},
        "coordination": {"binding_digest": "d" * 64},
    }


def _case(tmp_path, monkeypatch: pytest.MonkeyPatch):
    repo, lane = orphan_work_lane(tmp_path)
    observation, gaps = observe_lane(repo, "work/orphan")
    assert gaps == []
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)
    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )
    return repo, lane, observation, accepted_head, decision_path, decision


def _transaction(*responses: str) -> MagicMock:
    transaction = MagicMock()
    transaction.__enter__.return_value = transaction
    transaction.__exit__.return_value = False
    transaction.stdout.readline.side_effect = responses
    transaction.wait.return_value = 0
    return transaction


def _route_update_ref(
    monkeypatch: pytest.MonkeyPatch,
    outcome: MagicMock | OSError,
) -> None:
    real_popen = subprocess.Popen

    def routed(args, *popen_args, **popen_kwargs):
        if list(args) == ["git", "update-ref", "--stdin"]:
            if isinstance(outcome, OSError):
                raise outcome
            return outcome
        return real_popen(args, *popen_args, **popen_kwargs)

    monkeypatch.setattr(subprocess, "Popen", routed)


def _retire(case) -> None:
    repo, _lane, observation, accepted_head, decision_path, decision = case
    effects.retire_clean_ownerless_lane(
        root=repo,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        executor_ref=_EXECUTOR,
        accepted_branch="dev",
        accepted_head=accepted_head,
    )


def test_ownerless_cas_rejects_missing_transaction_stream(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    transaction = _transaction()
    transaction.stderr = None
    _route_update_ref(monkeypatch, transaction)

    with pytest.raises(effects.OwnerlessCloseoutError, match="ownerless_ref_prepare_failed"):
        _retire(case)

    assert case[1].is_dir()


def test_ownerless_cas_aborts_failed_prepare(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    transaction = _transaction("start: ok\n", "prepare: rejected\n")
    _route_update_ref(monkeypatch, transaction)

    with pytest.raises(effects.OwnerlessCloseoutError, match="ownerless_ref_prepare_failed"):
        _retire(case)

    transaction.stdin.write.assert_any_call("abort\n")
    assert case[1].is_dir()


def test_ownerless_cas_uses_noop_update_for_accepted_head_check(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    transaction = _transaction("start: ok\n", "prepare: rejected\n")
    _route_update_ref(monkeypatch, transaction)

    with pytest.raises(effects.OwnerlessCloseoutError, match="ownerless_ref_prepare_failed"):
        _retire(case)

    _repo, _lane, observation, accepted_head, *_rest = case
    writes = [call.args[0] for call in transaction.stdin.write.call_args_list]
    assert writes[:3] == [
        "start\n",
        f"update refs/heads/dev {accepted_head} {accepted_head}\n",
        f"delete refs/heads/{observation.lane_ref} {observation.head}\nprepare\n",
    ]


def test_ownerless_cas_classifies_update_ref_start_failure(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    _route_update_ref(monkeypatch, OSError("update-ref unavailable"))

    with pytest.raises(effects.OwnerlessCloseoutError, match="ownerless_ref_prepare_failed"):
        _retire(case)

    assert case[1].is_dir()


def test_ownerless_cas_classifies_commit_io_failure_after_worktree_removal(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    transaction = _transaction("start: ok\n", "prepare: ok\n")
    transaction.stdin.write.side_effect = (None, None, None, OSError("commit write failed"))
    _route_update_ref(monkeypatch, transaction)

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="ownerless_worktree_removed_ref_present",
    ):
        _retire(case)

    repo, lane, observation, *_rest = case
    assert not lane.exists()
    assert git(repo, "rev-parse", observation.lane_ref) == observation.head
