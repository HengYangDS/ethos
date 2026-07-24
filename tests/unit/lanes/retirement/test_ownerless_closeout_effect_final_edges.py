from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Any
from typing import cast

import pytest

import ethos.adapters.mutation.resolution.closeout.effect as closeout_effect
from ethos.adapters.mutation.resolution.closeout.effect import OwnerlessCloseoutRuntime
from ethos.adapters.mutation.resolution.closeout.wcp.core import WCPCloseoutExpectation
from ethos.adapters.mutation.resolution.closeout.wcp.core import WCPResponseError
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.records.core import target_digest
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionDecision

_EXECUTOR = "agent:codex:thread:executor"
_ACCEPTED_HEAD = "d" * 40
_STOP_AFTER_EXPECTATION_CAPTURE = "stop_after_expectation_capture"
_UNEXPECTED_WCP_CALL = "unexpected_wcp_call"


class OwnerlessTestError(ValueError):
    def __init__(self, gap: str, *, fence_acquired: bool) -> None:
        super().__init__(gap)
        self.fence_acquired = fence_acquired


def _error(gap: str, *, fence_acquired: bool) -> OwnerlessTestError:
    return OwnerlessTestError(gap, fence_acquired=fence_acquired)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _observation(tmp_path) -> LaneObservation:
    return LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="lane:ownerless-final-edges",
        path=(tmp_path / "orphan").as_posix(),
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def _decision(path, observation: LaneObservation) -> tuple[dict[str, object], bytes]:
    payload = LaneResolutionDecision(
        decision_id="lane-decision:00000000-0000-4000-8000-000000000022",
        disposition="retire",
        observation=observation,
        evidence_refs=("evidence:final-edge-review",),
        chronicle_ref="evidence/chronicle/final-edge-review.md",
        chronicle_digest="e" * 64,
        recovery_plan="Reconcile the exact durable closeout binding before retrying.",
        reason="Exercise the remaining fail-closed effect edges.",
        break_glass=True,
    ).to_payload()
    raw = (json.dumps(payload, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return payload, raw


def _wcp(raw: bytes) -> dict[str, object]:
    return {
        "schema_version": "workstation.repo-family-governance.v1",
        "decision_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _runtime(
    observation: LaneObservation,
    raw: bytes,
    **overrides: Any,
) -> OwnerlessCloseoutRuntime:
    fence = {"target_binding_digest": "f" * 64}
    values: dict[str, Any] = {
        "run_git": lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 0, "1" * 40 + "\n", ""
        ),
        "observe_lane": lambda *_args, **_kwargs: (observation, []),
        "records_artifact_root": lambda root: root / "records",
        "reservation_path": lambda root, target, artifact_root=None: (
            (artifact_root or root / "records") / "reservations" / f"{target}.json"
        ),
        "read_reservation": lambda **_kwargs: {},
        "reserve_target": lambda **_kwargs: None,
        "release_no_effect_reservation": lambda **_kwargs: None,
        "transition_reservation": lambda **_kwargs: {},
        "leases_by_branch": lambda _root: {},
        "acquire_fence": lambda *_args, **_kwargs: fence,
        "release_fence": lambda *_args, **_kwargs: None,
        "get_fence": lambda *_args, **_kwargs: fence,
        "probe_fence": lambda *_args, **_kwargs: ("present", fence),
        "state_database": lambda root: root / "state.sqlite",
        "run_wcp": lambda **_kwargs: _wcp(raw),
        "ownerless_error": _error,
        "ownerless_error_type": OwnerlessTestError,
        "verify_pre_effect": lambda **_kwargs: None,
        "retire_cas": lambda **_kwargs: None,
        "probe_ref": lambda _root, _branch: ("oid", _ACCEPTED_HEAD),
        "verify_postconditions": lambda **_kwargs: {"complete": True},
    }
    values.update(overrides)
    return OwnerlessCloseoutRuntime(**values)


def _retire(
    decision_path,
    decision: dict[str, object],
    observation: LaneObservation,
    runtime: OwnerlessCloseoutRuntime,
    *,
    executor_ref: str = _EXECUTOR,
) -> dict[str, object]:
    return closeout_effect.retire_clean_ownerless_lane(
        root=decision_path.parent,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        executor_ref=executor_ref,
        accepted_branch="dev",
        accepted_head=_ACCEPTED_HEAD,
        runtime=runtime,
    )


def _reservation(
    decision: dict[str, object],
    raw: bytes,
    observation: LaneObservation,
    *,
    postconditions: dict[str, object] | None = None,
) -> dict[str, object]:
    checks = postconditions or {"complete": True}
    return {
        "schema_version": 1,
        "decision_id": decision["decision_id"],
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        "executor_ref": _EXECUTOR,
        "wcp_schema_version": "workstation.repo-family-governance.v1",
        "wcp_decision_sha256": hashlib.sha256(raw).hexdigest(),
        "accepted_branch": "dev",
        "accepted_head": _ACCEPTED_HEAD,
        "wcp_binding_digest": "4" * 64,
        "target_digest": target_digest(observation.lane_ref, observation.head),
        "target_binding_digest": "f" * 64,
        "phase": "receipt",
        "recovery_state": "effect_complete_receipt_missing",
        "postcondition_digest": _digest(checks),
    }


def _expected_fence(
    decision: dict[str, object],
    raw: bytes,
    observation: LaneObservation,
    reservation: dict[str, object],
) -> dict[str, object]:
    return {
        "subject": observation.lane_ref,
        "expected_head": observation.head,
        "decision_id": str(decision["decision_id"]),
        "executor_ref": _EXECUTOR,
        "accepted_branch": "dev",
        "accepted_head": _ACCEPTED_HEAD,
        "target_binding_digest": "f" * 64,
        "payload": {
            "target_path": observation.path,
            "lane_incarnation_id": observation.lane_incarnation_id,
            "observation_digest": observation.digest(),
            "decision_sha256": hashlib.sha256(raw).hexdigest(),
            "chronicle_digest": str(decision["chronicle_digest"]),
            "wcp_schema_version": "workstation.repo-family-governance.v1",
            "wcp_decision_sha256": hashlib.sha256(raw).hexdigest(),
            "wcp_binding_digest": str(reservation["wcp_binding_digest"]),
        },
    }


def test_retire_rejects_missing_executor_and_unreadable_decision(tmp_path) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)
    runtime = _runtime(observation, raw)

    with pytest.raises(OwnerlessTestError, match="ownerless_executor_required") as missing_actor:
        _retire(
            decision_path,
            decision,
            observation,
            runtime,
            executor_ref="",
        )
    with pytest.raises(OwnerlessTestError, match="ownerless_decision_unavailable") as missing_file:
        _retire(
            tmp_path / "missing.json",
            decision,
            observation,
            runtime,
        )

    assert missing_actor.value.fence_acquired is False
    assert missing_file.value.fence_acquired is False


def test_retire_rejects_missing_accepted_tree_and_wcp_response(tmp_path) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)
    missing_tree = _runtime(
        observation,
        raw,
        run_git=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "missing"),
    )

    with pytest.raises(OwnerlessTestError, match="ownerless_accepted_tree_unavailable"):
        _retire(decision_path, decision, observation, missing_tree)

    def reject_wcp(**_kwargs: object) -> dict[str, object]:
        gap = "lane_resolution_wcp_rejected"
        raise WCPResponseError(gap)

    rejected = _runtime(observation, raw, run_wcp=reject_wcp)
    with pytest.raises(OwnerlessTestError, match="ownerless_wcp_rejected"):
        _retire(decision_path, decision, observation, rejected)


@pytest.mark.parametrize(
    ("layout_case", "lane_ref", "expected_id", "expected_layout"),
    [
        ("canonical", "work/20260721-orphan", "20260721-orphan", "canonical"),
        ("historical", "work/orphan", "20260721-orphan", "historical_ownerless"),
        ("legacy", "work/orphan", "orphan", "legacy_ownerless"),
    ],
)
def test_retire_binds_exact_ownerless_layout_expectation(
    tmp_path,
    layout_case: str,
    lane_ref: str,
    expected_id: str,
    expected_layout: str,
) -> None:
    canonical_worktrees = tmp_path.parent / f"{tmp_path.name}-worktrees"
    lane_path = {
        "canonical": canonical_worktrees / "20260721-orphan",
        "historical": canonical_worktrees / "20260721-orphan",
        "legacy": tmp_path / "repo-work-orphan",
    }[layout_case]
    observation = _observation(tmp_path).model_copy(
        update={"lane_ref": lane_ref, "path": lane_path.as_posix()}
    )
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)
    captured: dict[str, object] = {}

    def capture_expectation(**kwargs: object) -> dict[str, object]:
        captured["expected"] = kwargs["expected"]
        raise WCPResponseError(_STOP_AFTER_EXPECTATION_CAPTURE)

    runtime = _runtime(observation, raw, run_wcp=capture_expectation)
    with pytest.raises(OwnerlessTestError, match="ownerless_wcp_rejected"):
        _retire(decision_path, decision, observation, runtime)

    expected = cast("WCPCloseoutExpectation", captured["expected"])
    assert expected.lane_id == expected_id
    assert expected.lane_layout == expected_layout


def test_retire_rejects_unrelated_branch_and_canonical_directory_before_wcp(tmp_path) -> None:
    canonical_worktrees = tmp_path.parent / f"{tmp_path.name}-worktrees"
    observation = _observation(tmp_path).model_copy(
        update={
            "lane_ref": "work/orphan",
            "path": (canonical_worktrees / "20260721-unrelated").as_posix(),
        }
    )
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)
    events: list[str] = []

    def reject_wcp(**_kwargs: object) -> dict[str, object]:
        events.append("wcp")
        raise WCPResponseError(_UNEXPECTED_WCP_CALL)

    runtime = _runtime(observation, raw, run_wcp=reject_wcp)
    with pytest.raises(OwnerlessTestError, match="ownerless_wcp_expectation_invalid"):
        _retire(decision_path, decision, observation, runtime)

    assert events == []


@pytest.mark.parametrize("lane_ref", ["orphan", "work/"])
def test_retire_rejects_invalid_lane_ref_before_wcp(tmp_path, lane_ref: str) -> None:
    observation = _observation(tmp_path).model_copy(update={"lane_ref": lane_ref})
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)
    events: list[str] = []

    def reject_wcp(**_kwargs: object) -> dict[str, object]:
        events.append("wcp")
        raise WCPResponseError(_UNEXPECTED_WCP_CALL)

    runtime = _runtime(observation, raw, run_wcp=reject_wcp)
    with pytest.raises(OwnerlessTestError, match="ownerless_wcp_expectation_invalid"):
        _retire(decision_path, decision, observation, runtime)

    assert events == []


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("lane_closeout_competing_fence", "lane_closeout_competing_fence"),
        ("storage unavailable", "lane_resolution_ownerless_fence_failed"),
    ],
)
def test_retire_classifies_fence_acquisition_failures(
    tmp_path,
    message: str,
    expected: str,
) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)

    def fail_fence(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise ValueError(message)

    runtime = _runtime(observation, raw, acquire_fence=fail_fence)
    with pytest.raises(OwnerlessTestError, match=expected) as caught:
        _retire(decision_path, decision, observation, runtime)

    assert caught.value.fence_acquired is False


def test_retire_fails_closed_on_reservation_and_final_transition_writes(tmp_path) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)

    def fail_reservation(**_kwargs: object) -> None:
        message = "reservation unavailable"
        raise OSError(message)

    reservation_failure = _runtime(observation, raw, reserve_target=fail_reservation)
    with pytest.raises(OwnerlessTestError, match="ownerless_reservation_failed"):
        _retire(decision_path, decision, observation, reservation_failure)

    def fail_transition(**_kwargs: object) -> None:
        message = "transition unavailable"
        raise ValueError(message)

    transition_failure = _runtime(
        observation,
        raw,
        transition_reservation=fail_transition,
    )
    with pytest.raises(OwnerlessTestError, match="ownerless_reservation_update_failed"):
        _retire(decision_path, decision, observation, transition_failure)


def test_partial_classification_fails_closed_when_reservation_update_fails(tmp_path) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)

    def partial_error(**_kwargs: object) -> None:
        gap = "lane_resolution_ownerless_postcondition_failed:target_ref_absent"
        raise OwnerlessTestError(gap, fence_acquired=True)

    def fail_transition(**_kwargs: object) -> None:
        message = "reservation transition unavailable"
        raise OSError(message)

    runtime = _runtime(
        observation,
        raw,
        verify_pre_effect=partial_error,
        transition_reservation=fail_transition,
    )
    with pytest.raises(OwnerlessTestError, match="ownerless_reservation_update_failed") as caught:
        _retire(decision_path, decision, observation, runtime)

    assert caught.value.fence_acquired is True


def test_recovery_rejects_unreadable_decision_and_stale_bindings(tmp_path) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)
    reservation = _reservation(decision, raw, observation)
    runtime = _runtime(observation, raw)

    with pytest.raises(OwnerlessTestError, match="ownerless_decision_stale"):
        closeout_effect.recover_completed_ownerless_closeout(
            root=tmp_path,
            decision_path=tmp_path / "missing.json",
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            reservation=reservation,
            runtime=runtime,
        )

    wrong_target = dict(reservation, decision_id="lane-decision:other")
    with pytest.raises(OwnerlessTestError, match="ownerless_decision_stale"):
        closeout_effect.recover_completed_ownerless_closeout(
            root=tmp_path,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            reservation=wrong_target,
            runtime=runtime,
        )

    with pytest.raises(OwnerlessTestError, match="recovery_binding_mismatch:executor_ref"):
        closeout_effect.recover_completed_ownerless_closeout(
            root=tmp_path,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref="agent:codex:thread:other",
            reservation=reservation,
            runtime=runtime,
        )


def test_recovery_rejects_accepted_head_and_postcondition_drift(tmp_path) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision, raw = _decision(decision_path, observation)
    postconditions = {"complete": True}
    reservation = _reservation(decision, raw, observation, postconditions=postconditions)

    stale_head = _runtime(
        observation,
        raw,
        probe_ref=lambda _root, _branch: ("oid", "0" * 40),
    )
    with pytest.raises(OwnerlessTestError, match="ownerless_accepted_head_stale"):
        closeout_effect.recover_completed_ownerless_closeout(
            root=tmp_path,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            reservation=reservation,
            runtime=stale_head,
        )

    fence = _expected_fence(decision, raw, observation, reservation)
    digest_drift = _runtime(
        observation,
        raw,
        probe_fence=lambda *_args, **_kwargs: ("present", fence),
        verify_postconditions=lambda **_kwargs: {"complete": False},
    )
    with pytest.raises(OwnerlessTestError, match="postcondition_failed:postcondition_digest"):
        closeout_effect.recover_completed_ownerless_closeout(
            root=tmp_path,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=_EXECUTOR,
            reservation=reservation,
            runtime=digest_drift,
        )


def test_pre_effect_rejects_stale_fence_decision_and_observation(tmp_path) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    _payload, raw = _decision(decision_path, observation)
    decision_sha256 = hashlib.sha256(raw).hexdigest()
    fence = {"exact": True}

    stale_fence = _runtime(
        observation,
        raw,
        probe_fence=lambda *_args, **_kwargs: ("absent", None),
    )
    with pytest.raises(OwnerlessTestError, match="ownerless_fence_stale"):
        closeout_effect.verify_ownerless_pre_effect(
            runtime=stale_fence,
            root=tmp_path,
            database=tmp_path / "state.sqlite",
            decision_path=decision_path,
            decision_sha256=decision_sha256,
            observation=observation,
            accepted_branch="dev",
            accepted_head=_ACCEPTED_HEAD,
            fence=fence,
        )

    exact_fence = _runtime(
        observation,
        raw,
        probe_fence=lambda *_args, **_kwargs: ("present", fence),
    )
    with pytest.raises(OwnerlessTestError, match="ownerless_decision_stale"):
        closeout_effect.verify_ownerless_pre_effect(
            runtime=exact_fence,
            root=tmp_path,
            database=tmp_path / "state.sqlite",
            decision_path=tmp_path / "missing.json",
            decision_sha256=decision_sha256,
            observation=observation,
            accepted_branch="dev",
            accepted_head=_ACCEPTED_HEAD,
            fence=fence,
        )

    stale_observation = _runtime(
        observation,
        raw,
        probe_fence=lambda *_args, **_kwargs: ("present", fence),
        observe_lane=lambda *_args, **_kwargs: (observation, ["observation unavailable"]),
    )
    with pytest.raises(OwnerlessTestError, match="ownerless_observation_stale"):
        closeout_effect.verify_ownerless_pre_effect(
            runtime=stale_observation,
            root=tmp_path,
            database=tmp_path / "state.sqlite",
            decision_path=decision_path,
            decision_sha256=decision_sha256,
            observation=observation,
            accepted_branch="dev",
            accepted_head=_ACCEPTED_HEAD,
            fence=fence,
        )


def test_lane_apply_keeps_non_ownerless_recovery_gap_in_blocked_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision, _raw = _decision(decision_path, observation)
    globals_ = apply_lane_resolution.__globals__
    monkeypatch.setitem(globals_, "_read_decision", lambda *_args, **_kwargs: (decision, []))
    monkeypatch.setitem(globals_, "_resolution_runtime", object)
    monkeypatch.setitem(
        globals_,
        "ownerless_recovery_context",
        lambda **_kwargs: ({}, None, None, "lane_resolution_recovery_context_invalid"),
    )

    report = apply_lane_resolution(
        root=tmp_path,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["lane_resolution_recovery_context_invalid"]


def test_lane_recovery_readiness_does_not_execute_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    observation = _observation(tmp_path)
    decision_path = tmp_path / "decision.json"
    decision, _raw = _decision(decision_path, observation)
    recovery = {"recovery_state": "effect_complete_receipt_missing"}
    globals_ = apply_lane_resolution.__globals__
    monkeypatch.setitem(globals_, "_read_decision", lambda *_args, **_kwargs: (decision, []))
    monkeypatch.setitem(globals_, "_resolution_runtime", object)
    monkeypatch.setitem(
        globals_,
        "ownerless_recovery_context",
        lambda **_kwargs: (recovery, tmp_path, tmp_path / "records", ""),
    )
    monkeypatch.setitem(
        globals_,
        "recover_ownerless_resolution",
        lambda **_kwargs: pytest.fail("readiness must not execute ownerless recovery"),
    )

    report = apply_lane_resolution(
        root=tmp_path,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=False,
    )

    assert report["ok"] is True
    assert report["required_gaps"] == []
