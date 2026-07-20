"""Branch-complete tests for ref-absent owner-unavailable lease reconciliation."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.unbound.reconciliation.core as reconciliation
import ethos.adapters.mutation.lane_retirement.unbound.records.core as records
from tests.unit.lanes.retirement.test_unbound_and_helpers import (
    _partial_effect_reconciliation_fixture,
)


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
