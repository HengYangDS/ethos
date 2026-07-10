from __future__ import annotations

from ethos_core.contracts.lane_resolution import LaneObservation
from ethos_core.contracts.lane_resolution import LaneResolutionDecision


def test_lane_resolution_decision_binds_exact_observation_and_does_not_authorize_replay() -> None:
    observation = LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="lane-incarnation:one",
        holder_ref="",
        path="/tmp/work-orphan",
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
    )
    decision = LaneResolutionDecision(
        decision_id="lane-decision:one",
        disposition="preserve",
        observation=observation,
        evidence_refs=("evidence:operator-review",),
        reason="Preserve before any retirement judgment.",
    )

    payload = decision.to_payload()
    assert payload["observation_digest"] == observation.digest()
    assert payload["recompute_before_effect"] is True
    assert payload["reusable_authorization"] is False
    assert payload["mints_authority"] is False
