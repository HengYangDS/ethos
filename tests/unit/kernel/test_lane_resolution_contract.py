from __future__ import annotations

import pytest
from pydantic import ValidationError

from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionDecision
from ethos_core.contracts.resolution.lane import LaneResolutionReceipt


def test_lane_resolution_decision_binds_exact_observation_and_does_not_authorize_replay() -> None:
    observation = LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="lane-incarnation:one",
        holder_ref="",
        path="/var/empty/work-orphan",
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )
    decision = LaneResolutionDecision(
        decision_id="lane-decision:one",
        disposition="preserve",
        observation=observation,
        evidence_refs=("evidence:operator-review",),
        chronicle_ref="evidence/chronicle/lane-resolution/decision.md",
        chronicle_digest="d" * 64,
        recovery_plan="Preserve the exact observed work before effect.",
        reason="Preserve before any retirement judgment.",
    )

    payload = decision.to_payload()
    assert payload["observation_digest"] == observation.digest()
    assert payload["recompute_before_effect"] is True
    assert payload["reusable_authorization"] is False
    assert payload["mints_authority"] is False


def _receipt(**overrides: object) -> dict[str, object]:
    return {
        "receipt_id": "lane-resolution-receipt:one",
        "decision_id": "lane-decision:one",
        "completed": True,
        "state": "retired",
        "observation_digest": "d" * 64,
        "reconciliation_required": False,
        "lane_ref": "work/orphan",
        "head": "a" * 40,
        "preservation_package": "",
        "preservation_manifest_sha256": "",
        "mints_authority": False,
    } | overrides


def test_lane_resolution_receipt_has_one_outcome_field() -> None:
    payload = LaneResolutionReceipt.model_validate(_receipt()).to_payload()

    assert payload["state"] == "retired"
    assert "disposition" not in payload


@pytest.mark.parametrize("width", [41, 63])
def test_lane_resolution_contracts_reject_intermediate_oid_widths(width: int) -> None:
    with pytest.raises(ValidationError):
        LaneObservation(
            lane_ref="work/orphan",
            head="a" * width,
            lane_incarnation_id="lane-incarnation:one",
            path="/var/empty/work-orphan",
            dirty=False,
            foreign=True,
            orphan=True,
            ambiguous=False,
            tracked_digest="b" * 64,
            untracked_digest="c" * 64,
        )

    assert (
        validate_schema_instance("lane-resolution-receipt.schema.json", _receipt(head="a" * width))[
            "ok"
        ]
        is False
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [("completed", 1), ("reconciliation_required", 0), ("mints_authority", 0)],
)
def test_lane_resolution_receipt_rejects_coercive_booleans(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        LaneResolutionReceipt.model_validate(_receipt(**{field: value}))


@pytest.mark.parametrize("field", ["dirty", "foreign", "orphan", "ambiguous"])
@pytest.mark.parametrize("value", [0, 1, "false", "true"])
def test_lane_resolution_observation_rejects_coercive_booleans(field: str, value: object) -> None:
    payload = {
        "lane_ref": "work/orphan",
        "head": "a" * 40,
        "lane_incarnation_id": "lane-incarnation:one",
        "path": "/var/empty/work-orphan",
        "dirty": False,
        "foreign": True,
        "orphan": True,
        "ambiguous": False,
        "tracked_digest": "b" * 64,
        "untracked_digest": "c" * 64,
        field: value,
    }
    with pytest.raises(ValidationError):
        LaneObservation.model_validate(payload)


@pytest.mark.parametrize("value", [0, 1, "false", "true"])
def test_lane_resolution_decision_rejects_coercive_break_glass(value: object) -> None:
    observation = LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="lane-incarnation:one",
        path="/var/empty/work-orphan",
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )
    with pytest.raises(ValidationError):
        LaneResolutionDecision(
            decision_id="lane-decision:one",
            disposition="preserve",
            observation=observation,
            evidence_refs=("evidence:operator-review",),
            chronicle_ref="evidence/chronicle/lane-resolution/decision.md",
            chronicle_digest="d" * 64,
            recovery_plan="Restore the preserved package.",
            reason="Preserve before removal.",
            break_glass=value,
        )
