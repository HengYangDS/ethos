from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.store.state.closeout as closeout_store
from ethos.adapters.store.state.closeout import acquire_closeout_fence
from ethos.adapters.store.state.closeout import get_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.adapters.store.state.schema import state_database_inventory

if TYPE_CHECKING:
    from pathlib import Path


def _acquire(
    db_path: Path,
    *,
    subject: str = "work/target",
    decision_id: str = "decision:one",
    executor_ref: str = "agent:codex:thread:executor",
):
    return acquire_closeout_fence(
        db_path,
        subject=subject,
        expected_head="a" * 40,
        decision_id=decision_id,
        executor_ref=executor_ref,
        accepted_branch="dev",
        accepted_head="b" * 40,
        target_path="/tmp/ethos-ownerless-target",
        lane_incarnation_id="lane-incarnation:target",
        observation_digest="c" * 64,
        decision_sha256="d" * 64,
        chronicle_digest="e" * 64,
    )


def test_closeout_fence_is_exact_idempotent_and_release_is_cas(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    first = _acquire(db_path)
    assert _acquire(db_path) == first
    assert get_closeout_fence(db_path, subject="work/target") == first
    assert set(first["payload"]) == {
        "target_path",
        "lane_incarnation_id",
        "observation_digest",
        "decision_sha256",
        "chronicle_digest",
        "acquisition_id",
    }
    with pytest.raises(ValueError, match="lane_closeout_fence_release_stale"):
        release_closeout_fence(
            db_path,
            subject="work/target",
            decision_id="decision:other",
            target_binding_digest=first["target_binding_digest"],
        )
    release_closeout_fence(
        db_path,
        subject="work/target",
        decision_id="decision:one",
        target_binding_digest=first["target_binding_digest"],
    )
    assert get_closeout_fence(db_path, subject="work/target") is None
    second = _acquire(db_path)
    assert second["payload"]["acquisition_id"] != first["payload"]["acquisition_id"]
    assert second["target_binding_digest"] != first["target_binding_digest"]


def test_closeout_fence_requires_canonical_executor_input_and_raw_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical = "agent:codex:thread:executor"
    alias = "agent:alias:case:raw"
    real_parse = closeout_store.HolderRef.parse

    def normalize(_cls: type[object], _value: str) -> object:
        return real_parse(canonical)

    monkeypatch.setattr(closeout_store.HolderRef, "parse", classmethod(normalize))
    with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid"):
        _acquire(tmp_path / "input.sqlite", executor_ref=alias)

    row_db = tmp_path / "row.sqlite"
    _acquire(row_db)
    with closing(sqlite3.connect(row_db)) as connection, connection:
        connection.execute("update closeout_fences set executor_ref = ?", (alias,))
    assert closeout_store.probe_closeout_fence(row_db, subject="work/target") == (
        "unverifiable",
        None,
    )


def test_closeout_fence_rejects_existing_lease_or_claim(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    acquire_lease(
        db_path,
        subject="work/target",
        holder_ref="agent:test:case:owner",
        payload={"claim_id": "claim:late"},
    )
    with pytest.raises(ValueError, match="lane_closeout_coordinated:work/target"):
        _acquire(db_path)


def test_closeout_fence_allows_an_expired_lease_residue(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    acquire_lease(
        db_path,
        subject="work/target",
        holder_ref="agent:test:case:expired-owner",
        payload={"claim_id": ""},
        ttl_seconds=-1,
    )

    assert _acquire(db_path)["subject"] == "work/target"


@pytest.mark.parametrize("expiry", ["not-a-time", "2026-07-22T16:57:22"])
def test_closeout_fence_blocks_a_lease_with_ambiguous_expiry(tmp_path: Path, expiry: str) -> None:
    db_path = tmp_path / "state.sqlite"
    acquire_lease(
        db_path,
        subject="work/target",
        holder_ref="agent:test:case:ambiguous-owner",
        payload={"claim_id": ""},
    )
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("update leases set expires_at = ?", (expiry,))
    with closing(sqlite3.connect(db_path)) as connection:
        assert connection.execute(
            "select expires_at from leases where subject = ?", ("work/target",)
        ).fetchone() == (expiry,)

    with pytest.raises(ValueError, match="lane_closeout_coordinated:work/target"):
        _acquire(db_path)


def test_lease_acquisition_rejects_a_held_closeout_fence(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    _acquire(db_path)
    with pytest.raises(ValueError, match="lane_closeout_fenced:work/target"):
        acquire_lease(
            db_path,
            subject="work/target",
            holder_ref="agent:test:case:late",
            payload={"claim_id": "claim:late"},
        )


def test_closeout_fence_is_target_scoped(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    _acquire(db_path)
    with pytest.raises(ValueError, match="lane_closeout_target_competition:work/target"):
        _acquire(db_path, decision_id="decision:other")
    assert _acquire(db_path, subject="work/independent")["subject"] == "work/independent"


def test_closeout_fence_inventory_exposes_exact_recovery_binding(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    fence = _acquire(db_path)

    inventory = state_database_inventory(db_path)

    assert inventory["closeout_fence_schema"] == "current"
    assert inventory["closeout_fence_count"] == 1
    assert inventory["closeout_fences"] == [fence]


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("target_path", "relative/path"),
        ("lane_incarnation_id", ""),
        ("observation_digest", "not-a-digest"),
        ("decision_sha256", "0" * 63),
        ("chronicle_digest", "0" * 65),
    ],
)
def test_closeout_fence_rejects_incomplete_or_untyped_binding(
    tmp_path: Path, field: str, bad: str
) -> None:
    kwargs = {
        "subject": "work/target",
        "expected_head": "a" * 40,
        "decision_id": "decision:one",
        "executor_ref": "agent:codex:thread:executor",
        "accepted_branch": "dev",
        "accepted_head": "b" * 40,
        "target_path": "/tmp/ethos-ownerless-target",
        "lane_incarnation_id": "lane-incarnation:target",
        "observation_digest": "c" * 64,
        "decision_sha256": "d" * 64,
        "chronicle_digest": "e" * 64,
    }
    kwargs[field] = bad

    with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid"):
        acquire_closeout_fence(tmp_path / "state.sqlite", **kwargs)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("subject", False),
        ("expected_head", True),
        ("decision_id", 7),
        ("executor_ref", False),
        ("accepted_branch", 1),
        ("accepted_head", False),
        ("target_path", ["/tmp/target"]),
        ("lane_incarnation_id", True),
        ("observation_digest", False),
        ("decision_sha256", 1),
        ("chronicle_digest", True),
    ],
)
def test_closeout_fence_rejects_raw_binding_coercion_with_stable_gap(
    tmp_path: Path, field: str, bad: object
) -> None:
    kwargs: dict[str, object] = {
        "subject": "work/target",
        "expected_head": "a" * 40,
        "decision_id": "decision:one",
        "executor_ref": "agent:codex:thread:executor",
        "accepted_branch": "dev",
        "accepted_head": "b" * 40,
        "target_path": "/tmp/ethos-ownerless-target",
        "lane_incarnation_id": "lane-incarnation:target",
        "observation_digest": "c" * 64,
        "decision_sha256": "d" * 64,
        "chronicle_digest": "e" * 64,
    }
    kwargs[field] = bad

    with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid"):
        acquire_closeout_fence(tmp_path / "state.sqlite", **kwargs)
