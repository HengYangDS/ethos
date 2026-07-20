"""Branch-complete tests for ref-absent owner-unavailable lease reconciliation."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
import ethos.adapters.mutation.lane_retirement.unbound.policy.core as policy
import ethos.adapters.mutation.lane_retirement.unbound.reconciliation.core as reconciliation
import ethos.adapters.mutation.lane_retirement.unbound.records.core as records
from tests.unit.lanes.retirement.test_unbound_and_helpers import (
    _partial_effect_reconciliation_fixture,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def residue(tmp_path: Path, monkeypatch):
    """Return one accepted ref-absent foreign-lease residue and recovery actor."""
    values = _partial_effect_reconciliation_fixture(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")
    return values


def _apply(repo: Path, branch: str, chronicle: str) -> dict[str, object]:
    return reconciliation.reconcile_ref_absent_owner_unavailable_lease(
        root=repo,
        branch=branch,
        controls=reconciliation.RefAbsentReconciliationControls(
            reason="accepted policy binds the exact ref-absent partial effect",
            chronicle_ref=chronicle,
            apply=True,
            authorized=True,
            break_glass=True,
            confirm_irreversible=True,
        ),
    )


def test_reconciliation_requires_reason(residue) -> None:
    """The dry-run refuses an empty irreversible-effect reason."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue

    report = reconciliation.reconcile_ref_absent_owner_unavailable_lease(
        root=repo,
        branch=branch,
        controls=reconciliation.RefAbsentReconciliationControls(chronicle_ref=chronicle),
    )

    assert report["required_gaps"] == ["retire_reason_required"]


def test_reconciliation_blocks_attempt_write_failure(residue, monkeypatch) -> None:
    """Intent-write failure cannot advance to the foreign lease CAS."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue
    error = "denied"
    monkeypatch.setattr(
        records,
        "write_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError(error)),
    )

    report = _apply(repo, branch, chronicle)

    assert report["required_gaps"] == [error]


def test_reconciliation_blocks_stale_pre_effect_observation(residue, monkeypatch) -> None:
    """The final observation must equal the admitted observation before CAS."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue
    observe = reconciliation.observation.observe_ref_absent_reconciliation
    calls = 0

    def drift(repo_root: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        observed = observe(repo_root, branch=branch, chronicle_ref=chronicle_ref)
        return observed if calls == 1 else {**observed, "claim_id": "drifted-claim"}

    monkeypatch.setattr(reconciliation.observation, "observe_ref_absent_reconciliation", drift)

    report = _apply(repo, branch, chronicle)

    assert "unbound_retire_pre_effect_observation_stale" in report["required_gaps"]


def test_reconciliation_blocks_lease_cas_failure(residue, monkeypatch) -> None:
    """A native exact-lease CAS refusal is surfaced without a receipt."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue
    monkeypatch.setattr(reconciliation, "relinquish_owned_lease", lambda *_args, **_kwargs: None)

    report = _apply(repo, branch, chronicle)

    assert report["required_gaps"] == ["unbound_retire_active_lease"]


def test_reconciliation_blocks_sqlite_effect_failure(residue, monkeypatch) -> None:
    """A database failure remains a fail-closed native-effect gap."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue

    def failed_initialize(_database: Path) -> None:
        raise sqlite3.Error

    monkeypatch.setattr(reconciliation, "initialize_state", failed_initialize)

    report = _apply(repo, branch, chronicle)

    assert report["required_gaps"] == ["unbound_retire_effect_failed"]


@pytest.mark.parametrize(
    ("field", "value", "gap"),
    [
        ("head", "a" * 40, "unbound_retire_partial_effect_ref_reappeared"),
        ("worktree_binding", "linked", "unbound_retire_partial_effect_worktree_reappeared"),
        (reconciliation.observation.HAS_ACTIVE_LEASE, True, "unbound_retire_active_lease"),
    ],
)
def test_reconciliation_blocks_post_effect_drift(
    residue, monkeypatch, field: str, value: object, gap: str
) -> None:
    """Receipt publication requires every postcondition to remain true."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue
    observe = reconciliation.observation.observe_ref_absent_reconciliation
    calls = 0

    def drift(repo_root: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        observed = observe(repo_root, branch=branch, chronicle_ref=chronicle_ref)
        return observed if calls != 3 else {**observed, field: value}

    monkeypatch.setattr(reconciliation.observation, "observe_ref_absent_reconciliation", drift)

    report = _apply(repo, branch, chronicle)

    assert gap in report["required_gaps"]


def test_reconciliation_blocks_protected_ref_post_effect_drift(residue, monkeypatch) -> None:
    """Protected ref movement blocks receipt issuance after the irreversible CAS."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue
    observe = reconciliation.observation.observe_ref_absent_reconciliation
    calls = 0

    def drift(repo_root: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        observed = observe(repo_root, branch=branch, chronicle_ref=chronicle_ref)
        if calls != 3:
            return observed
        protected = dict(observed["protected_refs"])
        protected["dev"] = "a" * 40
        return {**observed, "protected_refs": protected}

    monkeypatch.setattr(reconciliation.observation, "observe_ref_absent_reconciliation", drift)

    report = _apply(repo, branch, chronicle)

    assert report["required_gaps"] == ["unbound_retire_protected_refs_changed"]


def test_reconciliation_blocks_chronicle_post_effect_drift(residue, monkeypatch) -> None:
    """Changing accepted Chronicle bytes blocks receipt issuance after the CAS."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue
    observe = reconciliation.observation.observe_ref_absent_reconciliation
    calls = 0

    def drift(repo_root: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        observed = observe(repo_root, branch=branch, chronicle_ref=chronicle_ref)
        if calls != 3:
            return observed
        changed = dict(observed["chronicle"])
        changed["sha256"] = "a" * 64
        return {**observed, "chronicle": changed}

    monkeypatch.setattr(reconciliation.observation, "observe_ref_absent_reconciliation", drift)

    report = _apply(repo, branch, chronicle)

    assert report["required_gaps"] == ["unbound_retire_chronicle_changed"]


def test_reconciliation_blocks_receipt_write_failure(residue, monkeypatch) -> None:
    """Receipt persistence failure is explicit after a successful lease-only CAS."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue
    write = records.write_record
    error = "receipt denied"

    def fail_receipt(path: Path, payload: dict[str, object], *, kind: str) -> str:
        if kind == records.RECONCILIATION_RECEIPT_KIND:
            raise OSError(error)
        return write(path, payload, kind=kind)

    monkeypatch.setattr(records, "write_record", fail_receipt)

    report = _apply(repo, branch, chronicle)

    assert report["required_gaps"] == [error]


@pytest.mark.parametrize(
    ("recovery_actor", "expected_gap"),
    [
        ("", "unbound_retire_recovery_actor_required"),
        (
            "agent:test:session:missing-source-owner",
            "unbound_retire_owner_unavailable_holder_not_foreign",
        ),
    ],
)
def test_reconciliation_requires_a_distinct_recovery_actor(
    residue, recovery_actor: str, expected_gap: str
) -> None:
    """Lease-only recovery cannot impersonate or omit the unavailable holder."""
    repo, branch, _head, chronicle, _lease, attempt, _source_path = residue
    observed = observation.observe_ref_absent_reconciliation(
        repo, branch=branch, chronicle_ref=chronicle
    )

    assert policy.partial_effect_reconciliation_gaps(
        observed, recovery_actor=recovery_actor, source_attempt=attempt
    ) == [expected_gap]


@pytest.mark.parametrize(
    ("change", "expected_gap"),
    [
        ("chronicle", "unbound_retire_partial_effect_chronicle_missing"),
        ("path", "unbound_retire_owner_unavailable_source_path_present"),
        ("attempt", "unbound_retire_partial_effect_attempt_mismatch"),
    ],
)
def test_reconciliation_policy_blocks_changed_residue_contract(
    residue, change: str, expected_gap: str
) -> None:
    """The policy binds the reconciliation mode, absent source path, and attempt tuple."""
    repo, branch, _head, chronicle, _lease, attempt, source_path = residue
    observed = observation.observe_ref_absent_reconciliation(
        repo, branch=branch, chronicle_ref=chronicle
    )
    if change == "chronicle":
        observed["chronicle"]["partial_effect_reconciliation"] = ""
    elif change == "path":
        source_path.mkdir()
    else:
        attempt = {**attempt, "effect": "wrong"}

    assert policy.partial_effect_reconciliation_gaps(
        observed,
        recovery_actor="agent:test:case:recovery-operator",
        source_attempt=attempt,
    ) == [expected_gap]


@pytest.mark.parametrize(
    ("change", "expected_gap"),
    [
        ("ref", "unbound_retire_partial_effect_ref_present"),
        ("worktree", "unbound_retire_partial_effect_worktree_present"),
        ("lease", "unbound_retire_partial_effect_lease_missing"),
    ],
)
def test_reconciliation_policy_requires_the_exact_ref_absent_residue(
    residue, change: str, expected_gap: str
) -> None:
    """Ref, worktree, and exact-lease presence are mutually required residue facts."""
    repo, branch, _head, chronicle, _lease, attempt, _source_path = residue
    observed = observation.observe_ref_absent_reconciliation(
        repo, branch=branch, chronicle_ref=chronicle
    )
    if change == "ref":
        observed["head"] = "a" * 40
    elif change == "worktree":
        observed["worktree_binding"] = "linked"
    else:
        observed[observation.HAS_ACTIVE_LEASE] = False

    assert policy.partial_effect_reconciliation_gaps(
        observed,
        recovery_actor="agent:test:case:recovery-operator",
        source_attempt=attempt,
    ) == [expected_gap]


def test_reconciliation_observation_projects_lease_claim_and_source_attempt_bindings() -> None:
    """Read-model helpers retain only safe lease and historical-attempt identities."""
    assert observation.lease_claim_id({"payload": {"claim_id": "claim"}}) == "claim"
    assert observation.lease_claim_id({"payload": "bad"}) == ""
    source_attempt = {
        "operation_id": "exceptional-unbound-retirement:" + "a" * 64,
        "accepted_head": "b" * 40,
        "claim_id": "claim",
        "chronicle_ref": "evidence/chronicle/test/2026-07-20.md",
        "chronicle_sha256": "c" * 64,
        "chronicle_claim_id": "chronicle-claim",
        "chronicle_claim_sha256": "d" * 64,
        "ignored": "value",
    }

    assert records.source_attempt_binding(source_attempt) == {
        key: source_attempt[key]
        for key in (
            "operation_id",
            "accepted_head",
            "claim_id",
            "chronicle_ref",
            "chronicle_sha256",
            "chronicle_claim_id",
            "chronicle_claim_sha256",
        )
    }


def test_reconciliation_policy_rejects_a_lease_binding_changed_after_attempt(
    residue,
) -> None:
    """The immutable failed attempt must retain the exact foreign lease generation."""
    repo, branch, _head, chronicle, _lease, attempt, _source_path = residue
    observed = observation.observe_ref_absent_reconciliation(
        repo, branch=branch, chronicle_ref=chronicle
    )
    attempt = {**attempt, "lease_relinquish_binding": {"active": False}}

    assert policy.partial_effect_reconciliation_gaps(
        observed,
        recovery_actor="agent:test:case:recovery-operator",
        source_attempt=attempt,
    ) == ["unbound_retire_partial_effect_attempt_mismatch"]


@pytest.mark.parametrize(
    ("mode", "expected_gap"),
    [
        ("missing", "unbound_retire_partial_effect_attempt_missing"),
        ("wrong-prefix", "unbound_retire_partial_effect_attempt_mismatch"),
    ],
)
def test_reconciliation_rejects_an_unavailable_or_malformed_prior_attempt(
    residue, monkeypatch, mode: str, expected_gap: str
) -> None:
    """Prior-attempt loading is fail-closed before any reconciliation intent record."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue
    observed = observation.observe_ref_absent_reconciliation(
        repo, branch=branch, chronicle_ref=chronicle
    )
    if mode == "missing":
        monkeypatch.setattr(
            records,
            "read_record",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid")),
        )
    else:
        observed["chronicle"]["source_retirement_attempt_id"] = "wrong"

    _attempt, gap = reconciliation._partial_effect_attempt(observed)

    assert gap == expected_gap


@pytest.mark.parametrize(
    ("controls", "expected_gap"),
    [
        (
            reconciliation.RefAbsentReconciliationControls(
                reason="reason", chronicle_ref="evidence/chronicle/test/2026-07-20.md", apply=True
            ),
            "authorization_required",
        ),
        (
            reconciliation.RefAbsentReconciliationControls(
                reason="reason",
                chronicle_ref="evidence/chronicle/test/2026-07-20.md",
                apply=True,
                authorized=True,
            ),
            "unbound_retire_requires_break_glass",
        ),
        (
            reconciliation.RefAbsentReconciliationControls(
                reason="reason",
                chronicle_ref="evidence/chronicle/test/2026-07-20.md",
                apply=True,
                authorized=True,
                break_glass=True,
            ),
            "irreversible_confirmation_required",
        ),
    ],
)
def test_reconciliation_apply_controls_are_independently_required(
    residue, controls: reconciliation.RefAbsentReconciliationControls, expected_gap: str
) -> None:
    """Each irreversible apply control remains independently enforced."""
    repo, branch, _head, chronicle, _lease, attempt, _source_path = residue
    observed = observation.observe_ref_absent_reconciliation(
        repo, branch=branch, chronicle_ref=chronicle
    )
    controls = reconciliation.RefAbsentReconciliationControls(
        reason=controls.reason,
        chronicle_ref=chronicle,
        apply=controls.apply,
        authorized=controls.authorized,
        break_glass=controls.break_glass,
        confirm_irreversible=controls.confirm_irreversible,
    )

    assert expected_gap in reconciliation._partial_effect_admission_gaps(
        observed,
        controls=controls,
        holder_ref="agent:test:case:recovery-operator",
        source_attempt=attempt,
        attempt_gap="",
    )


def test_reconciliation_rejects_missing_protected_ref_observation(residue) -> None:
    """Reconciliation requires every protected ref before it can enter the effect window."""
    repo, branch, _head, chronicle, _lease, attempt, _source_path = residue
    observed = observation.observe_ref_absent_reconciliation(
        repo, branch=branch, chronicle_ref=chronicle
    )
    observed["protected_refs"] = {"dev": ""}

    assert (
        "unbound_retire_protected_ref_unavailable"
        in reconciliation._partial_effect_admission_gaps(
            observed,
            controls=reconciliation.RefAbsentReconciliationControls(
                reason="reason", chronicle_ref=chronicle
            ),
            holder_ref="agent:test:case:recovery-operator",
            source_attempt=attempt,
            attempt_gap="",
        )
    )


def test_reconciliation_records_reject_invalid_nested_source_attempt(residue) -> None:
    """No durable reconciliation record may incorporate an invalid historical attempt."""
    repo, branch, _head, chronicle, _lease, attempt, _source_path = residue
    observed = observation.observe_ref_absent_reconciliation(
        repo, branch=branch, chronicle_ref=chronicle
    )
    payload = records.reconciliation_attempt_payload(
        operation_id="ref-absent-owner-unavailable-lease-reconciliation:" + "a" * 64,
        reason="reason",
        observation=observed,
        source_retirement_attempt={**attempt, "kind": "wrong"},
    )

    with pytest.raises(ValueError, match="unbound_retire_record_invalid"):
        records.validate_record(payload, kind=records.RECONCILIATION_ATTEMPT_KIND)


def test_reconciliation_blocks_unavailable_accepted_control_root(residue, monkeypatch) -> None:
    """Apply refuses when the current accepted record root cannot be revalidated."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = residue
    monkeypatch.setattr(policy, "accepted_control_root", lambda *_args, **_kwargs: (None, "gone"))

    report = _apply(repo, branch, chronicle)

    assert report["required_gaps"] == ["gone", "unbound_retire_partial_effect_attempt_mismatch"]
