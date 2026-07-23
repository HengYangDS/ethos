from __future__ import annotations

import json

from ethos.adapters.mutation.resolution.receipts import canonical_resolution_decision_snapshot
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionDecision


def _decision() -> dict[str, object]:
    observation = LaneObservation(
        lane_ref="work/20260722-receipt-final",
        head="a" * 40,
        lane_incarnation_id="lane-incarnation:20260722-receipt-final",
        path="/tmp/20260722-receipt-final",
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )
    return LaneResolutionDecision(
        decision_id="lane-decision:00000000-0000-4000-8000-000000000301",
        disposition="retire",
        observation=observation,
        evidence_refs=("evidence:20260722-receipt-final",),
        chronicle_ref="evidence/chronicle/20260722-receipt-final.md",
        chronicle_digest="d" * 64,
        recovery_plan="Recover only the exact canonical decision snapshot.",
        reason="Exercise final canonical receipt coverage.",
        break_glass=True,
    ).to_payload()


def test_canonical_decision_snapshot_returns_the_exact_payload() -> None:
    decision = _decision()
    decision_bytes = json.dumps(decision, sort_keys=True).encode()

    snapshot, gap = canonical_resolution_decision_snapshot(
        decision_bytes=decision_bytes,
        decision=decision,
    )

    assert (snapshot, gap) == (decision, "")


def test_canonical_decision_snapshot_rejects_invalid_bytes() -> None:
    snapshot, gap = canonical_resolution_decision_snapshot(
        decision_bytes=b"\xff",
        decision=_decision(),
    )

    assert snapshot == {}
    assert gap == "lane_resolution_ownerless_decision_invalid"


def test_canonical_decision_snapshot_rejects_a_nonserializable_caller_payload() -> None:
    canonical = _decision()
    decision_bytes = json.dumps(canonical, sort_keys=True).encode()
    caller_payload = dict(canonical, reason=object())

    snapshot, gap = canonical_resolution_decision_snapshot(
        decision_bytes=decision_bytes,
        decision=caller_payload,
    )

    assert snapshot == {}
    assert gap == "lane_resolution_ownerless_decision_stale"
