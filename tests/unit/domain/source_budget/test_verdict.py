from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

import ethos.domain.source_budget.verdict as verdict_api
import ethos_core.contracts.source_budget.policy.core as policy_api
from ethos.domain.source_budget.core import SourceBudgetShadowObservation


def _vector(*items: tuple[str, str, str, int]) -> Any:
    api = policy_api
    return api.BudgetVector.canonical(
        tuple(
            api.BudgetLimit(scope_id=scope, metric_id=metric, unit=unit, value=value)
            for scope, metric, unit, value in items
        )
    )


def _observation(
    *items: tuple[str, str, str, int],
    commit: str = "f" * 40,
    snapshot_digest: str = "9" * 64,
    comparison_state: str = "reviewed_observation",
    required_gaps: tuple[str, ...] = (),
    with_v2: bool = True,
) -> Any:
    vector = _vector(*items)
    v2 = (
        {
            "manifest_digest": "5" * 64,
            "inventory_digest": "6" * 64,
            "contract_set_digest": "7" * 64,
            "provider_coverage": {"python-source-v2": 1},
            "coordinates": [item.model_dump(mode="json") for item in vector.coordinates],
            "vector_digest": vector.vector_digest,
            "snapshot_digest": snapshot_digest,
        }
        if with_v2
        else None
    )
    return SourceBudgetShadowObservation.model_validate(
        {
            "observer": {
                "profile_id": "synthetic-task5",
                "commit_sha": "a" * 40,
                "tree_sha": "b" * 40,
                "taxonomy_path": ".config/checks/format/selection.toml",
                "taxonomy_blob": "c" * 40,
                "taxonomy_content_sha256": "d" * 64,
                "taxonomy_semantic_sha256": "e" * 64,
            },
            "subject": {
                "commit_sha": commit,
                "tree_sha": "1" * 40,
                "snapshot_digest": "2" * 64,
            },
            "v1": {
                "declaration_commit": "3" * 40,
                "declared_total": 1,
                "replay_total": 1,
                "drift": 0,
                "metrics": {"global_total": 1},
                "category_deltas": {},
                "inventory": {
                    "file_count": 1,
                    "digest": "4" * 64,
                    "category_counts": {"python_product": 1},
                },
            },
            "v2": v2,
            "disagreements": [],
            "required_gaps": list(required_gaps),
            "comparison_state": comparison_state,
        }
    )


def _debt_record(*, expiry: str = "2026-07-24", allowance: int = 2) -> Any:
    api = policy_api
    return api.MappedSourceBudgetDebtV2(
        mapping_state="mapped",
        id="debt-1",
        origin_change="change-1",
        admitted_head="d" * 40,
        scope_digest="a" * 64,
        inventory_digest="b" * 64,
        baseline_snapshot_digest="c" * 64,
        historical_replay_digest="d" * 64,
        owner="owner",
        replacement="replacement",
        deletion_wave="wave-1",
        expiry=expiry,
        allowance=_vector(("product.python", "lexical_tokens", "lexical_token", allowance)),
        expected_deletion=_vector(("product.python", "lexical_tokens", "lexical_token", allowance)),
    )


def _debt_replay(record: Any, **updates: str) -> Any:
    api = verdict_api
    payload = {
        "debt_id": record.id,
        "admitted_head": record.admitted_head,
        "scope_digest": record.scope_digest,
        "inventory_digest": record.inventory_digest,
        "baseline_snapshot_digest": record.baseline_snapshot_digest,
        "historical_replay_digest": record.historical_replay_digest,
    }
    payload.update(updates)
    return api.MappedDebtReplayBinding(**payload)


def _policy(
    *,
    enforcement: str = "transition",
    debt_records: tuple[Any, ...] = (),
    waves: tuple[Any, ...] = (),
    terminal_product: int = 8,
) -> Any:
    api = policy_api
    return api.EvaluableSourceBudgetPolicyV2(
        schema="ethos-source-budget-policy-v2",
        contract_version=2,
        state="shadow",
        baseline_head="f" * 40,
        enforcement=enforcement,
        campaign_id="global-declarative-compression-program"
        if enforcement == "campaign_terminal"
        else None,
        baseline=api.BudgetBaselineBinding(
            admitted_head="f" * 40,
            manifest_digest="5" * 64,
            inventory_digest="6" * 64,
            contract_set_digest="7" * 64,
            snapshot_digest="9" * 64,
            vector=_vector(
                ("product.python", "lexical_tokens", "lexical_token", 10),
                ("tests.python", "normalized_bytes", "normalized_byte", 20),
            ),
        ),
        terminal=_vector(
            ("product.python", "lexical_tokens", "lexical_token", terminal_product),
            ("tests.python", "normalized_bytes", "normalized_byte", 15),
        ),
        permanent_allocations=_vector(),
        settled_reductions=_vector(),
        debt=api.SourceBudgetDebtLedgerV2(waves=waves, records=debt_records),
    )


def _inputs(**values: Any) -> Any:
    values.pop("policy", None)
    current_product = values.pop("current_product", 10)
    current_tests = values.pop("current_tests", 20)
    baseline = values.pop("baseline", None)
    current = values.pop("current", None)
    debt_replays = values.pop("debt_replays", ())
    required_gaps = values.pop("required_gaps", ())
    if values:
        msg = f"unexpected input options: {sorted(values)}"
        raise ValueError(msg)
    return verdict_api.SourceBudgetVerdictObservations(
        baseline=baseline
        or _observation(
            ("product.python", "lexical_tokens", "lexical_token", 10),
            ("tests.python", "normalized_bytes", "normalized_byte", 20),
        ),
        current=current
        or _observation(
            ("product.python", "lexical_tokens", "lexical_token", current_product),
            ("tests.python", "normalized_bytes", "normalized_byte", current_tests),
            commit="e" * 40,
            snapshot_digest="8" * 64,
        ),
        debt_replays=debt_replays,
        required_gaps=required_gaps,
    )


def test_verdict_is_logical_and_without_cross_coordinate_compensation() -> None:
    api = verdict_api
    policy = _policy()

    verdict = api.compile_budget_verdict(
        _inputs(current_product=11, current_tests=0, policy=policy),
        policy,
        date(2026, 7, 24),
    )

    assert verdict.ok is False
    assert verdict.required_gaps == (
        "source_budget_v2_transition_exceeded:product.python:lexical_tokens:11>10",
    )
    by_key = {
        (item.coordinate.scope_id, item.coordinate.metric_id): item for item in verdict.coordinates
    }
    assert by_key[("product.python", "lexical_tokens")].allowed == 10
    assert by_key[("tests.python", "normalized_bytes")].current == 0


def test_incomplete_or_unreviewed_task4_observation_blocks_before_arithmetic() -> None:
    api = verdict_api
    policy = _policy()
    incomplete = _observation(with_v2=False)

    verdict = api.compile_budget_verdict(
        _inputs(policy=policy, baseline=incomplete), policy, date(2026, 7, 24)
    )

    assert verdict.coordinates == ()
    assert verdict.required_gaps == ("source_budget_v2_baseline_observation_incomplete",)


def test_baseline_identity_mismatch_blocks_before_arithmetic() -> None:
    api = verdict_api
    policy_payload = _policy().model_dump(mode="json")
    policy_payload["baseline"]["snapshot_digest"] = "0" * 64
    policy = policy_api.validate_source_budget_policy_v2(policy_payload)

    verdict = api.compile_budget_verdict(_inputs(policy=policy), policy, date(2026, 7, 24))

    assert verdict.coordinates == ()
    assert verdict.required_gaps == ("source_budget_v2_baseline_identity_mismatch",)


def test_mapped_debt_is_active_on_inclusive_expiry_and_wave_due_date() -> None:
    api = verdict_api
    contracts = policy_api
    record = _debt_record(expiry="2026-07-24")
    wave = contracts.SourceBudgetWaveV2(id="wave-1", due_on="2026-07-24", state="active")
    policy = _policy(debt_records=(record,), waves=(wave,))

    verdict = api.compile_budget_verdict(
        _inputs(
            current_product=12,
            policy=policy,
            debt_replays=(_debt_replay(record),),
        ),
        policy,
        date(2026, 7, 24),
    )

    product = next(
        item for item in verdict.coordinates if item.coordinate.scope_id == "product.python"
    )
    assert verdict.ok is True
    assert product.debt_allowance == 2
    assert product.allowed == 12
    assert verdict.advisory_gaps == ("source_budget_v2_debt_active:debt-1",)


def test_expired_overdue_stale_and_unmapped_debt_contribute_zero_allowance() -> None:
    api = verdict_api
    contracts = policy_api
    expired_record = _debt_record(expiry="2026-07-24")
    expired_wave = contracts.SourceBudgetWaveV2(id="wave-1", due_on="2026-07-24", state="active")
    expired_policy = _policy(debt_records=(expired_record,), waves=(expired_wave,))
    expired = api.compile_budget_verdict(
        _inputs(policy=expired_policy, debt_replays=(_debt_replay(expired_record),)),
        expired_policy,
        date(2026, 7, 25),
    )
    assert expired.coordinates == ()
    assert expired.required_gaps == ("source_budget_v2_debt_expired:debt-1",)

    overdue_record = _debt_record(expiry="2026-07-30")
    overdue_policy = _policy(debt_records=(overdue_record,), waves=(expired_wave,))
    overdue = api.compile_budget_verdict(
        _inputs(policy=overdue_policy, debt_replays=(_debt_replay(overdue_record),)),
        overdue_policy,
        date(2026, 7, 25),
    )
    assert overdue.coordinates == ()
    assert overdue.required_gaps == ("source_budget_v2_debt_overdue:debt-1",)

    live_record = _debt_record(expiry="2026-07-30")
    live_wave = contracts.SourceBudgetWaveV2(id="wave-1", due_on="2026-07-30", state="active")
    stale_policy = _policy(debt_records=(live_record,), waves=(live_wave,))
    stale = api.compile_budget_verdict(
        _inputs(
            policy=stale_policy,
            debt_replays=(_debt_replay(live_record, inventory_digest="0" * 64),),
        ),
        stale_policy,
        date(2026, 7, 24),
    )
    assert stale.coordinates == ()
    assert stale.required_gaps == ("source_budget_v2_debt_stale:debt-1",)

    unmapped = contracts.UnmappedSourceBudgetDebtV2(
        mapping_state="unmapped",
        id="debt-1",
        origin_change="change-1",
        owner="owner",
        replacement="replacement",
        deletion_wave="wave-1",
        expiry="2026-07-30",
        missing_bindings=(
            "admitted_head",
            "scope_digest",
            "inventory_digest",
            "baseline_snapshot",
            "historical_replay",
        ),
    )
    unmapped_policy = _policy(debt_records=(unmapped,), waves=(live_wave,))
    unmapped_verdict = api.compile_budget_verdict(
        _inputs(policy=unmapped_policy), unmapped_policy, date(2026, 7, 24)
    )
    assert unmapped_verdict.coordinates == ()
    assert unmapped_verdict.required_gaps == ("source_budget_v2_debt_unmapped:debt-1",)


def test_campaign_growth_is_advisory_but_unmet_terminal_target_is_blocking() -> None:
    api = verdict_api
    campaign = _policy(enforcement="campaign_terminal")
    campaign_verdict = api.compile_budget_verdict(
        _inputs(current_product=11, policy=campaign), campaign, date(2026, 7, 24)
    )
    assert campaign_verdict.ok is False
    assert campaign_verdict.required_gaps == (
        "source_budget_v2_terminal_exceeded:product.python:lexical_tokens:11>8",
        "source_budget_v2_terminal_exceeded:tests.python:normalized_bytes:20>15",
    )
    assert campaign_verdict.advisory_gaps == (
        "source_budget_v2_campaign_growth_overage:product.python:lexical_tokens:11>10",
    )

    terminal = _policy(enforcement="terminal")
    terminal_verdict = api.compile_budget_verdict(
        _inputs(current_product=9, current_tests=15, policy=terminal),
        terminal,
        date(2026, 7, 24),
    )
    assert terminal_verdict.ok is False
    assert terminal_verdict.required_gaps == (
        "source_budget_v2_terminal_exceeded:product.python:lexical_tokens:9>8",
    )


def test_terminal_mode_blocks_even_valid_active_debt() -> None:
    api = verdict_api
    contracts = policy_api
    record = _debt_record(expiry="2026-07-30")
    wave = contracts.SourceBudgetWaveV2(id="wave-1", due_on="2026-07-30", state="active")
    policy = _policy(
        enforcement="terminal",
        debt_records=(record,),
        waves=(wave,),
        terminal_product=12,
    )

    verdict = api.compile_budget_verdict(
        _inputs(
            current_product=10,
            current_tests=15,
            policy=policy,
            debt_replays=(_debt_replay(record),),
        ),
        policy,
        date(2026, 7, 24),
    )

    assert verdict.ok is False
    assert verdict.required_gaps == ("source_budget_v2_terminal_active_debt:debt-1",)


def test_explicit_input_gap_blocks_without_reading_external_state() -> None:
    api = verdict_api
    policy = _policy()

    verdict = api.compile_budget_verdict(
        _inputs(
            policy=policy,
            required_gaps=(
                "source_budget_v2_replay_unavailable",
                "source_budget_v2_contract_unavailable",
            ),
        ),
        policy,
        date(2026, 7, 24),
    )

    assert verdict.coordinates == ()
    assert verdict.required_gaps == (
        "source_budget_v2_replay_unavailable",
        "source_budget_v2_contract_unavailable",
    )


def test_multiple_invalid_debt_records_accumulate_stable_gaps() -> None:
    api = verdict_api
    contracts = policy_api
    wave = contracts.SourceBudgetWaveV2(id="wave-1", due_on="2026-07-30", state="active")

    def unmapped(debt_id: str) -> Any:
        return contracts.UnmappedSourceBudgetDebtV2(
            mapping_state="unmapped",
            id=debt_id,
            origin_change=f"change-{debt_id}",
            owner="owner",
            replacement="replacement",
            deletion_wave="wave-1",
            expiry="2026-07-30",
            missing_bindings=("admitted_head",),
        )

    policy = _policy(debt_records=(unmapped("debt-1"), unmapped("debt-2")), waves=(wave,))

    verdict = api.compile_budget_verdict(_inputs(policy=policy), policy, date(2026, 7, 24))

    assert verdict.coordinates == ()
    assert verdict.required_gaps == (
        "source_budget_v2_debt_unmapped:debt-1",
        "source_budget_v2_debt_unmapped:debt-2",
    )


def test_debt_gap_order_is_independent_of_policy_record_order() -> None:
    contracts = policy_api
    wave = contracts.SourceBudgetWaveV2(id="wave-1", due_on="2026-07-30", state="active")

    def unmapped(debt_id: str) -> Any:
        return contracts.UnmappedSourceBudgetDebtV2(
            mapping_state="unmapped",
            id=debt_id,
            origin_change=f"change-{debt_id}",
            owner="owner",
            replacement="replacement",
            deletion_wave="wave-1",
            expiry="2026-07-30",
            missing_bindings=("admitted_head",),
        )

    first = unmapped("debt-1")
    second = unmapped("debt-2")
    forward = _policy(debt_records=(first, second), waves=(wave,))
    reverse = _policy(debt_records=(second, first), waves=(wave,))

    forward_verdict = verdict_api.compile_budget_verdict(
        _inputs(policy=forward), forward, date(2026, 7, 24)
    )
    reverse_verdict = verdict_api.compile_budget_verdict(
        _inputs(policy=reverse), reverse, date(2026, 7, 24)
    )

    assert forward_verdict == reverse_verdict


def test_verdict_observations_reject_duplicate_replay_and_gap_identity() -> None:
    inputs = _inputs()
    record = _debt_record()
    replay = _debt_replay(record)

    with pytest.raises(ValidationError, match="debt replay bindings must be unique"):
        verdict_api.SourceBudgetVerdictObservations(
            baseline=inputs.baseline,
            current=inputs.current,
            debt_replays=(replay, replay),
        )
    with pytest.raises(ValidationError, match="verdict input gaps must be unique"):
        verdict_api.SourceBudgetVerdictObservations(
            baseline=inputs.baseline,
            current=inputs.current,
            required_gaps=("source_budget_v2_missing", "source_budget_v2_missing"),
        )


def test_verdict_requires_typed_inputs_and_an_explicit_calendar_date() -> None:
    policy = _policy()

    with pytest.raises(TypeError, match="typed observations and policy"):
        verdict_api.compile_budget_verdict(object(), policy, date(2026, 7, 24))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="explicit calendar date"):
        verdict_api.compile_budget_verdict(_inputs(), policy, "2026-07-24")  # type: ignore[arg-type]


def test_inactive_policy_blocks_before_vector_evaluation() -> None:
    inactive = policy_api.InactiveSourceBudgetPolicyV2(
        schema="ethos-source-budget-policy-v2",
        contract_version=2,
        state="inactive",
        baseline_head="f" * 40,
        enforcement="campaign_terminal",
        campaign_id="global-declarative-compression-program",
        debt=policy_api.SourceBudgetDebtLedgerV2(),
    )

    result = verdict_api.compile_budget_verdict(_inputs(), inactive, date(2026, 7, 24))

    assert result.required_gaps == ("source_budget_v2_policy_inactive",)


def test_forged_baseline_and_current_vectors_accumulate_incomplete_gaps() -> None:
    policy = _policy()
    baseline_payload = _inputs().baseline.model_dump(mode="json")
    current_payload = _inputs().current.model_dump(mode="json")
    baseline_payload["v2"]["vector_digest"] = "0" * 64
    current_payload["v2"]["vector_digest"] = "0" * 64
    baseline = SourceBudgetShadowObservation.model_validate(baseline_payload)
    current = SourceBudgetShadowObservation.model_validate(current_payload)

    result = verdict_api.compile_budget_verdict(
        _inputs(baseline=baseline, current=current), policy, date(2026, 7, 24)
    )

    assert result.required_gaps == (
        "source_budget_v2_baseline_observation_incomplete",
        "source_budget_v2_current_observation_incomplete",
    )


def test_current_identity_mismatch_blocks_before_arithmetic() -> None:
    policy = _policy()
    current_payload = _inputs().current.model_dump(mode="json")
    current_payload["v2"]["manifest_digest"] = "0" * 64
    current = SourceBudgetShadowObservation.model_validate(current_payload)

    result = verdict_api.compile_budget_verdict(_inputs(current=current), policy, date(2026, 7, 24))

    assert result.required_gaps == ("source_budget_v2_current_identity_mismatch",)


def test_observation_vector_and_identity_helpers_fail_closed_on_defensive_edges() -> None:
    policy = _policy()
    missing = _observation(with_v2=False)
    vector = _vector(("product.python", "lexical_tokens", "lexical_token", 10))

    observation_vector = vars(verdict_api)["_observation_vector"]
    baseline_matches = vars(verdict_api)["_baseline_matches"]
    current_matches = vars(verdict_api)["_current_matches"]
    assert observation_vector(missing) is None
    assert baseline_matches(missing, vector, policy) is False
    assert current_matches(missing, vector, policy) is False

    duplicate_payload = _inputs().current.model_dump(mode="json")
    duplicate_payload["v2"]["coordinates"] = [
        {
            "scope_id": "product.python",
            "metric_id": "lexical_tokens",
            "unit": "lexical_token",
            "value": 10,
        },
        {
            "scope_id": "product.python",
            "metric_id": "lexical_tokens",
            "unit": "normalized_byte",
            "value": 10,
        },
    ]
    duplicate = SourceBudgetShadowObservation.model_validate(duplicate_payload)

    assert observation_vector(duplicate) is None
