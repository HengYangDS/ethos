from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

import ethos_core.contracts.resolution.lane
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.closeout import LaneResolutionClearReceipt
from ethos_core.contracts.resolution.closeout import LaneResolutionReceipt
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutBinding
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutReservation
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionDecision

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"


def _target_digest(lane_ref: str, head: str) -> str:
    return hashlib.sha256(f"{lane_ref}\0{head}".encode()).hexdigest()


def _binding(**overrides: object) -> dict[str, object]:
    return {
        "executor_ref": "agent:codex:thread:executor",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": _target_digest("work/orphan", "a" * 40),
        "target_binding_digest": "d" * 64,
        "postcondition_digest": "e" * 64,
    } | overrides


def _reservation(**overrides: object) -> dict[str, object]:
    return {
        "schema_version": 2,
        "decision_id": _DECISION_ID,
        "lane_ref": "work/orphan",
        "head": "a" * 40,
        "executor_ref": "agent:codex:thread:executor",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": _target_digest("work/orphan", "a" * 40),
        "target_binding_digest": "d" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    } | overrides


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
        "schema_version": 3,
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


def test_closeout_contracts_live_in_their_defining_module_only() -> None:
    assert tuple(OwnerlessCloseoutBinding.model_fields) == (
        "executor_ref",
        "decision_sha256",
        "accepted_branch",
        "accepted_head",
        "target_digest",
        "target_binding_digest",
        "postcondition_digest",
    )
    assert tuple(OwnerlessCloseoutReservation.model_fields) == (
        "schema_version",
        "decision_id",
        "lane_ref",
        "head",
        "executor_ref",
        "decision_sha256",
        "accepted_branch",
        "accepted_head",
        "target_digest",
        "target_binding_digest",
        "phase",
        "recovery_state",
        "postcondition_digest",
    )
    for retired_name in (
        "LaneResolutionClearReceipt",
        "LaneResolutionReceipt",
        "LaneResolutionState",
        "OwnerlessCloseoutBinding",
        "OwnerlessCloseoutReservation",
    ):
        assert not hasattr(ethos_core.contracts.resolution.lane, retired_name)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("head",), "a" * 40 + "\n"),
        (("head",), "a" * 39 + "\n"),
        (("head",), "a" * 63 + "\n"),
        (("observation_digest",), "d" * 64 + "\n"),
        (("observation_digest",), "d" * 63 + "\n"),
        (("preservation_manifest_sha256",), "e" * 64 + "\n"),
        (("preservation_manifest_sha256",), "e" * 63 + "\n"),
        (("ownerless_closeout_binding", "accepted_head"), "c" * 40 + "\n"),
        (("ownerless_closeout_binding", "accepted_head"), "c" * 39 + "\n"),
        (("ownerless_closeout_binding", "accepted_head"), "c" * 63 + "\n"),
        (("ownerless_closeout_binding", "decision_sha256"), "b" * 64 + "\n"),
        (("ownerless_closeout_binding", "target_digest"), "a" * 64 + "\n"),
        (("ownerless_closeout_binding", "target_binding_digest"), "d" * 64 + "\n"),
        (("ownerless_closeout_binding", "postcondition_digest"), "e" * 64 + "\n"),
        (("ownerless_closeout_binding", "executor_ref"), "agent:codex:thread:executor\n"),
    ],
)
def test_lane_resolution_receipt_schema_rejects_trailing_newlines(
    path: tuple[str, ...], value: str
) -> None:
    payload = _receipt(ownerless_closeout_binding=_binding())
    target = payload
    for field in path[:-1]:
        nested = target[field]
        assert isinstance(nested, dict)
        target = nested
    target[path[-1]] = value

    assert validate_schema_instance("lane-resolution-receipt.schema.json", payload)["ok"] is False


@pytest.mark.parametrize("field", ["manifest_sha256", "chronicle_digest"])
@pytest.mark.parametrize("hex_count", [63, 64])
def test_lane_resolution_clear_receipt_schema_rejects_trailing_newlines(
    field: str, hex_count: int
) -> None:
    clear = LaneResolutionClearReceipt(
        schema_version=1,
        clear_receipt_id="lane-resolution-clear-receipt:one",
        decision_id="lane-decision:one",
        manifest_sha256="a" * 64,
        chronicle_ref="evidence/chronicle/lane-resolution/clear.md",
        chronicle_digest="b" * 64,
        reason="The exact recovery package was reviewed and cleared.",
        completed=True,
        mints_authority=False,
    ).model_dump(mode="json")
    clear[field] = "a" * hex_count + "\n"

    assert (
        validate_schema_instance("lane-resolution-clear-receipt.schema.json", clear)["ok"] is False
    )


def test_closeout_records_require_explicit_provider_neutral_versions() -> None:
    receipt = LaneResolutionReceipt.model_validate(_receipt())
    clear = LaneResolutionClearReceipt(
        schema_version=1,
        clear_receipt_id="lane-resolution-clear-receipt:one",
        decision_id="lane-decision:one",
        manifest_sha256="a" * 64,
        chronicle_ref="evidence/chronicle/lane-resolution/clear.md",
        chronicle_digest="b" * 64,
        reason="The exact recovery package was reviewed and cleared.",
        completed=True,
        mints_authority=False,
    )

    assert receipt.schema_version == 3
    assert clear.schema_version == 1
    with pytest.raises(ValidationError):
        LaneResolutionReceipt.model_validate(
            {key: value for key, value in _receipt().items() if key != "schema_version"}
        )
    with pytest.raises(ValidationError):
        LaneResolutionClearReceipt.model_validate(
            {key: value for key, value in clear.model_dump().items() if key != "schema_version"}
        )


@pytest.mark.parametrize(
    ("phase", "recovery_state", "postcondition_digest"),
    [
        ("reserved", "reserved_no_effect", ""),
        ("effect", "worktree_removed_ref_present", ""),
        ("postcondition", "postcondition_failed", ""),
        ("receipt", "effect_complete_receipt_missing", "f" * 64),
        ("unknown", "transition_unknown", ""),
    ],
)
def test_ownerless_reservation_preserves_phase_recovery_invariants(
    phase: str, recovery_state: str, postcondition_digest: str
) -> None:
    reservation = OwnerlessCloseoutReservation.model_validate(
        _reservation(
            phase=phase,
            recovery_state=recovery_state,
            postcondition_digest=postcondition_digest,
        )
    )

    assert reservation.phase == phase
    assert reservation.recovery_state == recovery_state


@pytest.mark.parametrize(
    ("phase", "recovery_state", "postcondition_digest"),
    [
        ("effect", "reserved_no_effect", ""),
        ("receipt", "effect_complete_receipt_missing", ""),
        ("reserved", "reserved_no_effect", "f" * 64),
    ],
)
def test_ownerless_reservation_rejects_invalid_phase_recovery_combinations(
    phase: str, recovery_state: str, postcondition_digest: str
) -> None:
    with pytest.raises(ValidationError):
        OwnerlessCloseoutReservation.model_validate(
            _reservation(
                phase=phase,
                recovery_state=recovery_state,
                postcondition_digest=postcondition_digest,
            )
        )


def test_ownerless_closeout_contracts_reject_provider_fields_and_target_drift() -> None:
    with pytest.raises(ValidationError):
        OwnerlessCloseoutBinding.model_validate(_binding(adapter_binding_digest="f" * 64))
    with pytest.raises(ValidationError):
        OwnerlessCloseoutReservation.model_validate(_reservation(target_digest="f" * 64))


def test_lane_resolution_receipt_has_one_outcome_field() -> None:
    payload = LaneResolutionReceipt.model_validate(_receipt()).to_payload()

    assert payload["schema_version"] == 3
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
    with pytest.raises(ValidationError):
        OwnerlessCloseoutReservation.model_validate(
            _reservation(head="a" * width, target_digest=_target_digest("work/orphan", "a" * width))
        )
    with pytest.raises(ValidationError):
        OwnerlessCloseoutBinding.model_validate(_binding(accepted_head="a" * width))


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
