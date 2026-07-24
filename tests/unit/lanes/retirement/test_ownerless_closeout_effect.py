from __future__ import annotations

import hashlib
import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution._effects as effects
import ethos.adapters.mutation.resolution.lane as lane_adapter
import ethos.adapters.mutation.resolution.records.reservations as reservation_store
from ethos.adapters.mutation.resolution._observation import observe_lane
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.store.state.closeout import get_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutBinding
from ethos_core.contracts.resolution.lane import LaneResolutionDecision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import orphan_work_lane

if TYPE_CHECKING:
    from pathlib import Path

    from ethos_core.contracts.resolution.lane import LaneObservation


_EXECUTOR = "agent:codex:thread:executor"
_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"
_REPLACEMENT_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000002"


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _decision(
    root: Path,
    path: Path,
    observation: LaneObservation,
    *,
    decision_id: str = _DECISION_ID,
) -> tuple[dict[str, object], bytes]:
    chronicle_ref = "evidence/chronicle/test.md"
    chronicle = root / chronicle_ref
    chronicle.parent.mkdir(parents=True, exist_ok=True)
    chronicle_bytes = b"decision: lane_resolution/retire\n"
    chronicle.write_bytes(chronicle_bytes)
    payload = LaneResolutionDecision(
        decision_id=decision_id,
        disposition="retire",
        observation=observation,
        evidence_refs=("evidence/test.md",),
        chronicle_ref=chronicle_ref,
        chronicle_digest=hashlib.sha256(chronicle_bytes).hexdigest(),
        recovery_plan="Restore the exact linked Work Lane if closeout is partial.",
        reason="The exact clean ownerless Work Lane is approved for closeout.",
        break_glass=True,
    ).to_payload()
    raw = json.dumps(payload, sort_keys=True).encode()
    path.write_bytes(raw)
    return payload, raw


def _wcp(raw: bytes, observation: LaneObservation, accepted_head: str) -> dict[str, object]:
    decision = json.loads(raw)
    return {
        "schema_version": "workstation.repo-family-governance.v1",
        "decision_sha256": hashlib.sha256(raw).hexdigest(),
        "executor_ref": _EXECUTOR,
        "observation_digest": observation.digest(),
        "chronicle_digest": str(decision["chronicle_digest"]),
        "source": {"head": accepted_head},
        "coordination": {"binding_digest": "d" * 64},
    }


def _fence(observation: LaneObservation, accepted_head: str) -> dict[str, object]:
    return {
        "subject": observation.lane_ref,
        "expected_head": observation.head,
        "decision_id": _DECISION_ID,
        "executor_ref": _EXECUTOR,
        "accepted_branch": "dev",
        "accepted_head": accepted_head,
        "target_binding_digest": "e" * 64,
    }


def _registered(repo: Path, path: Path) -> bool:
    return f"worktree {path}\n" in git(repo, "worktree", "list", "--porcelain")


@pytest.mark.parametrize(
    ("responses", "expected"),
    [
        ([subprocess.CompletedProcess([], 1, "", "")], ("absent", "")),
        ([subprocess.CompletedProcess([], 128, "", "fatal")], ("unverifiable", "")),
        ([OSError("probe failed")], ("unverifiable", "")),
        (
            [
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 128, "", "fatal"),
            ],
            ("unverifiable", ""),
        ),
        (
            [
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, "not-an-oid\n", ""),
            ],
            ("unverifiable", ""),
        ),
        (
            [
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, f"{'a' * 40}\n", ""),
            ],
            ("oid", "a" * 40),
        ),
    ],
)
def test_ownerless_ref_probe_has_explicit_three_state_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    responses: list[object],
    expected: tuple[str, str],
) -> None:
    queue = list(responses)

    def probe(*_args: object, **_kwargs: object):
        response = queue.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(effects, "run_git", probe)

    assert effects.probe_ownerless_ref(tmp_path, "work/orphan") == expected


def test_ownerless_effect_rejects_replaced_decision_before_any_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, _ = _decision(repo, decision_path, observation)
    _, replacement_raw = _decision(
        repo,
        decision_path,
        observation,
        decision_id=_REPLACEMENT_DECISION_ID,
    )
    events: list[str] = []

    def admitted(**_kwargs: object) -> dict[str, object]:
        events.append("wcp")
        return _wcp(replacement_raw, observation, accepted_head)

    monkeypatch.setattr(effects, "run_worktree_closeout_check", admitted)

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_decision_stale",
    ) as caught:
        effects.retire_clean_ownerless_lane(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            accepted_branch="dev",
            accepted_head=accepted_head,
        )

    assert caught.value.fence_acquired is False
    assert events == []
    assert lane.is_dir()
    assert _registered(repo, lane)
    assert git(repo, "rev-parse", "work/orphan") == observation.head
    assert get_closeout_fence(state_database(repo), subject=observation.lane_ref) is None
    assert not reservation_store.ownerless_closeout_reservation_path(
        repo,
        reservation_store.target_digest(observation.lane_ref, observation.head),
    ).exists()


def test_ownerless_effect_classifies_failed_remove_after_real_removal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    real_run_git = effects.run_git
    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )

    def partial_remove(root: Path, *args: str, **kwargs: object):
        if args[:2] == ("worktree", "remove"):
            removed = real_run_git(root, *args, **kwargs)
            assert removed.returncode == 0
            return subprocess.CompletedProcess(args, 1, "", "injected nonzero after removal")
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(effects, "run_git", partial_remove)

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_worktree_removed_ref_present",
    ):
        effects.retire_clean_ownerless_lane(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            accepted_branch="dev",
            accepted_head=accepted_head,
        )

    assert not lane.exists()
    assert not _registered(repo, lane)
    assert git(repo, "rev-parse", "work/orphan") == observation.head
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            reservation_store.target_digest(observation.lane_ref, observation.head),
        ),
    )
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "effect",
        "worktree_removed_ref_present",
    )


def test_ownerless_effect_classifies_failed_remove_with_unverifiable_ref_as_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    real_run_git = effects.run_git
    target_ref = f"refs/heads/{observation.lane_ref}"
    removed = False
    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )

    def partial_remove(root: Path, *args: str, **kwargs: object):
        nonlocal removed
        if args[:2] == ("worktree", "remove"):
            completed = real_run_git(root, *args, **kwargs)
            assert completed.returncode == 0
            removed = True
            return subprocess.CompletedProcess(args, 1, "", "injected nonzero after removal")
        if removed and args[-1:] == (target_ref,) and args[0] == "show-ref":
            return subprocess.CompletedProcess(args, 128, "", "injected fatal probe")
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(effects, "run_git", partial_remove)

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_transition_unknown",
    ):
        effects.retire_clean_ownerless_lane(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            accepted_branch="dev",
            accepted_head=accepted_head,
        )

    assert not lane.exists()
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            reservation_store.target_digest(observation.lane_ref, observation.head),
        ),
    )
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "unknown",
        "transition_unknown",
    )


@pytest.mark.parametrize("registration_fault", ["returncode", "exception"])
def test_ownerless_effect_requires_verifiable_registration_for_no_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    registration_fault: str,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    real_run_git = effects.run_git
    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )

    def failed_remove(root: Path, *args: str, **kwargs: object):
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 1, "", "injected no-effect failure")
        if args[:3] == ("worktree", "list", "--porcelain"):
            if registration_fault == "exception":
                message = "injected registration probe failure"
                raise OSError(message)
            return subprocess.CompletedProcess(args, 128, "", "injected fatal probe")
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(effects, "run_git", failed_remove)

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_transition_unknown",
    ):
        effects.retire_clean_ownerless_lane(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            accepted_branch="dev",
            accepted_head=accepted_head,
        )

    assert lane.is_dir()
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            reservation_store.target_digest(observation.lane_ref, observation.head),
        ),
    )
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "unknown",
        "transition_unknown",
    )


def test_ownerless_effect_keeps_no_effect_state_when_failed_remove_preserves_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    real_run_git = effects.run_git
    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )

    def failed_remove(root: Path, *args: str, **kwargs: object):
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 1, "", "injected no-effect failure")
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(effects, "run_git", failed_remove)

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_worktree_remove_failed",
    ):
        effects.retire_clean_ownerless_lane(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            accepted_branch="dev",
            accepted_head=accepted_head,
        )

    assert lane.is_dir()
    assert _registered(repo, lane)
    assert git(repo, "rev-parse", "work/orphan") == observation.head
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            reservation_store.target_digest(observation.lane_ref, observation.head),
        ),
    )
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "reserved",
        "reserved_no_effect",
    )


@pytest.mark.parametrize("probe_fault", ["returncode_128", "exception"])
def test_ownerless_effect_fails_closed_when_target_ref_absence_is_unverifiable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    probe_fault: str,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    real_run_git = effects.run_git
    target_ref = f"refs/heads/{observation.lane_ref}"
    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )

    def faulting_probe(root: Path, *args: str, **kwargs: object):
        if (
            not lane.exists()
            and args[-1:] == (target_ref,)
            and args[0]
            in {
                "rev-parse",
                "show-ref",
            }
        ):
            if probe_fault == "exception":
                message = "injected target-ref probe failure"
                raise OSError(message)
            return subprocess.CompletedProcess(args, 128, "", "injected fatal probe")
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(effects, "run_git", faulting_probe)

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_postcondition_failed:target_ref_absent",
    ):
        effects.retire_clean_ownerless_lane(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            accepted_branch="dev",
            accepted_head=accepted_head,
        )

    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            reservation_store.target_digest(observation.lane_ref, observation.head),
        ),
    )
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "postcondition",
        "postcondition_failed",
    )


def test_completed_ownerless_recovery_allows_only_an_exactly_released_fence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, _ = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )
    binding = effects.retire_clean_ownerless_lane(
        root=repo,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        executor_ref=_EXECUTOR,
        accepted_branch="dev",
        accepted_head=accepted_head,
    )
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            str(binding["target_digest"]),
        ),
    )
    release_closeout_fence(
        state_database(repo),
        subject=observation.lane_ref,
        decision_id=_DECISION_ID,
        target_binding_digest=str(binding["target_binding_digest"]),
    )

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_fence_stale",
    ):
        effects.recover_completed_ownerless_closeout(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            reservation=reservation,
        )

    receipt = effects.completion_receipt(decision, observation, "retired", {})
    receipt["ownerless_closeout_binding"] = {
        field: binding[field] for field in OwnerlessCloseoutBinding.model_fields
    }
    recovered = effects.recover_completed_ownerless_closeout(
        root=repo,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        executor_ref=_EXECUTOR,
        reservation=reservation,
        receipt=receipt,
    )
    assert recovered["postcondition_digest"] == binding["postcondition_digest"]

    monkeypatch.setattr(
        effects, "probe_closeout_fence", lambda *_args, **_kwargs: ("present", {"other": 1})
    )
    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_fence_stale",
    ):
        effects.recover_completed_ownerless_closeout(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            reservation=reservation,
            receipt=receipt,
        )


def test_ownerless_effect_orders_preflight_fence_cas_and_postverify(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, gaps = observe_lane(repo, "work/orphan")
    assert gaps == []
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    wcp = _wcp(raw, observation, accepted_head)
    events: list[str] = []
    git_calls: list[tuple[str, ...]] = []
    acquired: dict[str, object] = {}
    real_acquire = effects.acquire_closeout_fence
    real_probe_fence = effects.probe_closeout_fence
    real_run_git = effects.run_git

    def preflight(**_kwargs: object) -> dict[str, object]:
        events.append("preflight")
        return wcp

    def acquire(db_path: Path, **kwargs: object) -> dict[str, object]:
        assert events == ["preflight"]
        events.append("fence")
        acquired.update(real_acquire(db_path, **kwargs))
        return acquired

    def probe_fence(db_path: Path, *, subject: str) -> tuple[str, dict[str, object] | None]:
        assert subject == observation.lane_ref
        events.append("get-fence")
        return real_probe_fence(db_path, subject=subject)

    def recording_git(root: Path, *args: str, **kwargs: object):
        git_calls.append(args)
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(effects, "run_worktree_closeout_check", preflight)
    monkeypatch.setattr(effects, "acquire_closeout_fence", acquire)
    monkeypatch.setattr(effects, "probe_closeout_fence", probe_fence)
    monkeypatch.setattr(effects, "run_git", recording_git)

    binding = effects.retire_clean_ownerless_lane(
        root=repo,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        executor_ref=_EXECUTOR,
        accepted_branch="dev",
        accepted_head=accepted_head,
    )

    assert events[:2] == ["preflight", "fence"]
    assert not lane.exists()
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "refs/heads/work/orphan"],
            cwd=repo,
            check=False,
        ).returncode
        != 0
    )
    assert git(repo, "rev-parse", "dev") == accepted_head
    assert all("--force" not in call for call in git_calls)
    assert binding["target_binding_digest"] == acquired["target_binding_digest"]
    assert binding["decision_sha256"] == hashlib.sha256(raw).hexdigest()
    assert set(OwnerlessCloseoutBinding.model_validate(binding).model_dump()) == {
        "executor_ref",
        "decision_sha256",
        "accepted_branch",
        "accepted_head",
        "target_digest",
        "target_binding_digest",
        "postcondition_digest",
    }
    assert len(str(binding["postcondition_digest"])) == 64
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            str(binding["target_digest"]),
        ),
    )
    assert reservation["recovery_state"] == "effect_complete_receipt_missing"
    assert reservation["postcondition_digest"] == binding["postcondition_digest"]


def test_ownerless_effect_retains_fence_when_accepted_ref_drifts_after_admission(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    fence = _fence(observation, accepted_head)

    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )

    def acquire_then_drift(_db_path: Path, **_kwargs: object) -> dict[str, object]:
        git(
            repo,
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "--allow-empty",
            "-m",
            "accepted drift",
        )
        return fence

    monkeypatch.setattr(effects, "acquire_closeout_fence", acquire_then_drift)
    monkeypatch.setattr(
        effects, "probe_closeout_fence", lambda *_args, **_kwargs: ("present", fence)
    )

    with pytest.raises(effects.OwnerlessCloseoutError) as caught:
        effects.retire_clean_ownerless_lane(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            accepted_branch="dev",
            accepted_head=accepted_head,
        )

    assert caught.value.fence_acquired is True
    assert "accepted_head_stale" in str(caught.value)
    assert lane.is_dir()
    assert git(repo, "rev-parse", "work/orphan") == observation.head
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            reservation_store.target_digest(observation.lane_ref, observation.head),
        ),
    )
    assert reservation["phase"] == "reserved"
    assert reservation["recovery_state"] == "reserved_no_effect"


def test_ownerless_effect_records_transition_unknown_for_ordinary_post_cas_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )

    def fail_postconditions(**_kwargs: object) -> dict[str, object]:
        message = "unexpected verifier failure"
        raise RuntimeError(message)

    monkeypatch.setattr(effects, "_verify_ownerless_postconditions", fail_postconditions)

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_transition_unknown",
    ):
        effects.retire_clean_ownerless_lane(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            accepted_branch="dev",
            accepted_head=accepted_head,
        )

    assert not lane.exists()
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            reservation_store.target_digest(observation.lane_ref, observation.head),
        ),
    )
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "unknown",
        "transition_unknown",
    )


def test_ownerless_effect_rejects_dangling_symlink_at_retired_target_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")
    accepted_head = git(repo, "rev-parse", "dev")
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(repo, decision_path, observation)
    real_cas = effects._retire_clean_ownerless_cas  # noqa: SLF001, RUF100 - fault injection seam
    monkeypatch.setattr(
        effects,
        "run_worktree_closeout_check",
        lambda **_kwargs: _wcp(raw, observation, accepted_head),
    )

    def leave_dangling_symlink(**kwargs: object) -> None:
        real_cas(**kwargs)
        lane.symlink_to(tmp_path / "missing-target", target_is_directory=True)

    monkeypatch.setattr(effects, "_retire_clean_ownerless_cas", leave_dangling_symlink)

    with pytest.raises(
        effects.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_postcondition_failed:target_path_absent",
    ):
        effects.retire_clean_ownerless_lane(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            accepted_branch="dev",
            accepted_head=accepted_head,
        )

    assert lane.is_symlink()
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=reservation_store.ownerless_closeout_reservation_path(
            repo,
            reservation_store.target_digest(observation.lane_ref, observation.head),
        ),
    )
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "postcondition",
        "postcondition_failed",
    )


@pytest.mark.parametrize(
    ("disposition", "changes", "expected"),
    [
        ("retire", {}, 1),
        ("preserve-retire", {}, 0),
        ("retire", {"dirty": True}, 0),
        ("retire", {"orphan": False}, 0),
        ("retire", {"holder_ref": "agent:test:case:owner"}, 0),
    ],
)
def test_ownerless_route_requires_exact_clean_orphan_state(
    tmp_path: Path, disposition: str, changes: dict[str, object], expected: int
) -> None:
    repo, _ = orphan_work_lane(tmp_path)
    observation, _ = observe_lane(repo, "work/orphan")

    assert lane_adapter._ownerless_closeout_candidate(  # noqa: SLF001, RUF100 - route law
        disposition, observation.model_copy(update=changes)
    ) is bool(expected)
