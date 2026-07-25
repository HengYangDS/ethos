from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.closeout.cleanup.core as cleanup
import ethos.adapters.mutation.resolution.closeout.effect as effect
import ethos.adapters.mutation.resolution.closeout.recovery as recovery
import ethos.adapters.mutation.resolution.closeout.retry as retry
import ethos.adapters.mutation.resolution.records.reservations as reservation_store
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.records.core import receipt_path
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.store.state.closeout import get_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.adapters.store.state.schema import state_database
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.unit.lanes.retirement.test_ownerless_closeout_effect import _apply
from tests.unit.lanes.retirement.test_ownerless_closeout_effect import _reservation
from tests.unit.lanes.retirement.test_ownerless_closeout_effect import _scenario

if TYPE_CHECKING:
    from pathlib import Path


def _start_reserved_no_effect(
    scenario: object, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, object], dict[str, int]]:
    real_cas = effect.retire_clean_ownerless_cas
    attempts = {"count": 0}

    def fail_first(**kwargs: object) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            message = "lane_resolution_ownerless_accepted_head_stale"
            raise effect.OwnerlessCloseoutError(
                message,
                phase="reserved",
                recovery_state="reserved_no_effect",
            )
        real_cas(**kwargs)

    monkeypatch.setattr(effect, "retire_clean_ownerless_cas", fail_first)
    with pytest.raises(effect.OwnerlessCloseoutError) as raised:
        _apply(scenario)
    assert str(raised.value) == "lane_resolution_ownerless_accepted_head_stale"
    return _reservation(scenario), attempts


def _apply_top_level(scenario: object) -> dict[str, object]:
    return apply_lane_resolution(
        root=scenario.repo,
        decision_path=scenario.decision_path,
        confirm_irreversible=True,
        apply=True,
    )


def _receipt_sidecar(scenario: object) -> Path:
    decision_id = str(scenario.decision["decision_id"])
    receipt = receipt_path(
        scenario.repo,
        decision_id,
        artifact_root=current_record_root(scenario.repo),
    )
    return receipt.with_name(f".{receipt.stem}.receipt-reservation")


def test_reserved_no_effect_retry_recovers_exact_existing_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    real_cas = effect.retire_clean_ownerless_cas
    real_release = cleanup.release_receipt_reservation
    attempts = {"count": 0}

    def fail_first(**kwargs: object) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            message = "lane_resolution_ownerless_accepted_head_stale"
            raise effect.OwnerlessCloseoutError(
                message,
                phase="reserved",
                recovery_state="reserved_no_effect",
            )
        real_cas(**kwargs)

    monkeypatch.setattr(effect, "retire_clean_ownerless_cas", fail_first)
    monkeypatch.setattr(
        cleanup,
        "release_receipt_reservation",
        lambda **_kwargs: "lane_resolution_receipt_reservation_release_failed",
    )
    first = _apply_top_level(scenario)
    sidecar = _receipt_sidecar(scenario)

    assert first["required_gaps"] == [
        "lane_resolution_ownerless_accepted_head_stale",
        "lane_resolution_receipt_reservation_release_failed",
    ]
    assert _reservation(scenario)["recovery_state"] == "reserved_no_effect"
    assert sidecar.read_bytes() == f"{scenario.decision['decision_id']}\n".encode()

    monkeypatch.setattr(cleanup, "release_receipt_reservation", real_release)
    events: list[str] = []
    real_claim = recovery.claim_receipt_reservation
    real_admit = recovery.pre_admit_ownerless_lane

    def claim(*args: object, mode: str, **kwargs: object):
        events.append(f"claim:{mode}")
        return real_claim(*args, mode=mode, **kwargs)

    def admit(**kwargs: object):
        events.append(
            "admit:token"
            if kwargs.get("receipt_reservation_token") is not None
            else "admit:tokenless"
        )
        return real_admit(**kwargs)

    monkeypatch.setattr(recovery, "claim_receipt_reservation", claim)
    monkeypatch.setattr(recovery, "pre_admit_ownerless_lane", admit)
    recovered = _apply_top_level(scenario)

    assert recovered["ok"] is True
    assert recovered["state"] == "retired"
    assert events[:2] == ["claim:recover", "admit:token"]
    assert attempts["count"] == 2
    assert not scenario.target.exists()
    assert not sidecar.exists()
    assert get_closeout_fence(state_database(scenario.repo), subject="work/orphan") is None


def test_retry_does_not_adopt_concurrently_locked_exact_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    real_cas = effect.retire_clean_ownerless_cas
    live_writer_ready = threading.Event()
    release_live_writer = threading.Event()
    retry_reached_effect = threading.Event()
    live_reports: list[dict[str, object]] = []

    def pause_live_writer(**kwargs: object) -> None:
        if threading.current_thread().name == "live-writer":
            live_writer_ready.set()
            assert release_live_writer.wait(timeout=5)
            real_cas(**kwargs)
            return
        retry_reached_effect.set()
        real_cas(**kwargs)

    monkeypatch.setattr(effect, "retire_clean_ownerless_cas", pause_live_writer)
    live_writer = threading.Thread(
        target=lambda: live_reports.append(_apply_top_level(scenario)),
        name="live-writer",
    )
    live_writer.start()
    assert live_writer_ready.wait(timeout=5)

    try:
        blocked = _apply_top_level(scenario)
    finally:
        release_live_writer.set()
        live_writer.join(timeout=5)

    assert live_writer.is_alive() is False
    assert retry_reached_effect.is_set() is False
    assert blocked["ok"] is False
    assert blocked["required_gaps"] == ["lane_resolution_receipt_path_exists"]
    assert live_reports[0]["ok"] is True
    assert not scenario.target.exists()


def _advance_accepted(scenario: object, message: str = "advance accepted") -> str:
    path = scenario.repo / f"{message.replace(' ', '-')}.txt"
    path.write_text(f"{message}\n", encoding="utf-8")
    git(scenario.repo, "add", path.name)
    git(
        scenario.repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )
    return git(scenario.repo, "rev-parse", "dev")


def test_same_head_retry_releases_old_binding_before_fresh_fence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario(tmp_path)
    old_reservation, attempts = _start_reserved_no_effect(scenario, monkeypatch)
    old_fence = get_closeout_fence(state_database(scenario.repo), subject="work/orphan")
    assert old_fence is not None
    events: list[str] = []
    real_release_fence = retry.release_closeout_fence
    real_release_reservation = retry.release_ownerless_no_effect_reservation
    real_acquire = effect.acquire_closeout_fence
    real_reobserve = effect.reobserve_ownerless_closeout_under_fence

    def release_fence(*args: object, **kwargs: object) -> None:
        events.append("release_fence")
        real_release_fence(*args, **kwargs)

    def release_reservation(**kwargs: object) -> None:
        events.append("release_reservation")
        real_release_reservation(**kwargs)

    def acquire(*args: object, **kwargs: object) -> dict[str, object]:
        events.append("acquire")
        return real_acquire(*args, **kwargs)

    def reobserve(**kwargs: object):
        events.append("reobserve")
        return real_reobserve(**kwargs)

    monkeypatch.setattr(retry, "release_closeout_fence", release_fence)
    monkeypatch.setattr(retry, "release_ownerless_no_effect_reservation", release_reservation)
    monkeypatch.setattr(effect, "acquire_closeout_fence", acquire)
    monkeypatch.setattr(effect, "reobserve_ownerless_closeout_under_fence", reobserve)
    binding = _apply(scenario)
    fresh_fence = get_closeout_fence(state_database(scenario.repo), subject="work/orphan")
    assert fresh_fence is not None
    assert events[:4] == ["release_fence", "release_reservation", "acquire", "reobserve"]
    assert fresh_fence["payload"]["acquisition_id"] != old_fence["payload"]["acquisition_id"]
    assert binding["target_binding_digest"] == fresh_fence["target_binding_digest"]
    assert binding["target_binding_digest"] != old_reservation["target_binding_digest"]
    assert attempts["count"] == 2


def test_descendant_retry_rebinds_to_current_accepted_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario(tmp_path)
    old_reservation, _attempts = _start_reserved_no_effect(scenario, monkeypatch)
    new_head = _advance_accepted(scenario)
    binding = _apply(scenario)
    assert binding["accepted_head"] == new_head
    assert binding["accepted_head"] != old_reservation["accepted_head"]
    assert _reservation(scenario)["accepted_head"] == new_head


def test_retry_with_absent_old_fence_releases_reservation_then_reobserves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario(tmp_path)
    old_reservation, _attempts = _start_reserved_no_effect(scenario, monkeypatch)
    old_fence = get_closeout_fence(state_database(scenario.repo), subject="work/orphan")
    assert old_fence is not None
    release_closeout_fence(
        state_database(scenario.repo),
        subject="work/orphan",
        decision_id=str(old_reservation["decision_id"]),
        target_binding_digest=str(old_reservation["target_binding_digest"]),
    )
    events: list[str] = []
    real_release = retry.release_ownerless_no_effect_reservation
    real_admit = effect.admit_ownerless_closeout
    real_reobserve = effect.reobserve_ownerless_closeout_under_fence

    def release(**kwargs: object) -> None:
        events.append("release_reservation")
        real_release(**kwargs)

    def admit(**kwargs: object):
        events.append("admit")
        return real_admit(**kwargs)

    def reobserve(**kwargs: object):
        events.append("reobserve")
        return real_reobserve(**kwargs)

    monkeypatch.setattr(retry, "release_ownerless_no_effect_reservation", release)
    monkeypatch.setattr(effect, "admit_ownerless_closeout", admit)
    monkeypatch.setattr(effect, "reobserve_ownerless_closeout_under_fence", reobserve)
    _apply(scenario)
    assert events == ["admit", "release_reservation", "reobserve"]


def test_descendant_classification_precedes_competition_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario(tmp_path)
    _old, _attempts = _start_reserved_no_effect(scenario, monkeypatch)
    old_fence = get_closeout_fence(state_database(scenario.repo), subject="work/orphan")
    new_head = _advance_accepted(scenario)
    assert old_fence is not None
    assert old_fence["accepted_head"] != new_head
    binding = _apply(scenario)
    assert binding["accepted_head"] == new_head


def test_divergent_accepted_head_blocks_without_releasing_old_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario(tmp_path)
    old_reservation, _attempts = _start_reserved_no_effect(scenario, monkeypatch)
    old_fence = get_closeout_fence(state_database(scenario.repo), subject="work/orphan")
    accepted_tree = git(scenario.repo, "rev-parse", f"{scenario.accepted_head}^{{tree}}")
    divergent = git(
        scenario.repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit-tree",
        accepted_tree,
        "-m",
        "divergent",
    )
    git(scenario.repo, "update-ref", "refs/heads/dev", divergent, scenario.accepted_head)
    with pytest.raises(effect.OwnerlessCloseoutError, match="accepted_head_stale"):
        _apply(scenario)
    assert get_closeout_fence(state_database(scenario.repo), subject="work/orphan") == old_fence
    assert _reservation(scenario) == old_reservation


def test_decision_and_chronicle_drift_block_before_retry_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for drift in ("decision", "chronicle"):
        scenario = _scenario(tmp_path / drift)
        old_reservation, _attempts = _start_reserved_no_effect(scenario, monkeypatch)
        old_fence = get_closeout_fence(state_database(scenario.repo), subject="work/orphan")
        if drift == "decision":
            scenario.decision_path.write_bytes(scenario.decision_path.read_bytes() + b"\n")
        else:
            (scenario.repo / str(scenario.decision["chronicle_ref"])).write_text(
                "decision: lane_resolution/retire\ndrift\n", encoding="utf-8"
            )
        with pytest.raises(effect.OwnerlessCloseoutError):
            _apply(scenario)
        assert get_closeout_fence(state_database(scenario.repo), subject="work/orphan") == old_fence
        assert _reservation(scenario) == old_reservation
        monkeypatch.undo()


def test_crash_after_old_fence_release_recovers_on_next_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario(tmp_path)
    _old, attempts = _start_reserved_no_effect(scenario, monkeypatch)
    real_release = retry.release_ownerless_no_effect_reservation

    def crash(**_kwargs: object) -> None:
        message = "crash after fence release"
        raise OSError(message)

    monkeypatch.setattr(retry, "release_ownerless_no_effect_reservation", crash)
    with pytest.raises(effect.OwnerlessCloseoutError, match="retry_reset_failed"):
        _apply(scenario)
    assert get_closeout_fence(state_database(scenario.repo), subject="work/orphan") is None
    monkeypatch.setattr(retry, "release_ownerless_no_effect_reservation", real_release)
    _apply(scenario)
    assert attempts["count"] == 2


def test_retry_reset_noops_without_reservation_and_releases_absent_fence_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario(tmp_path)
    fresh = effect.admit_clean_ownerless_lane(
        root=scenario.repo,
        decision_path=scenario.decision_path,
        decision=scenario.decision,
        executor_ref="agent:codex:thread:executor",
    )

    retry.reset_reserved_no_effect_retry(
        admission=fresh,
        database=state_database(scenario.repo),
        record_root=current_record_root(scenario.repo),
    )

    old_reservation, _attempts = _start_reserved_no_effect(scenario, monkeypatch)
    old_fence = get_closeout_fence(state_database(scenario.repo), subject="work/orphan")
    assert old_fence is not None
    release_closeout_fence(
        state_database(scenario.repo),
        subject="work/orphan",
        decision_id=str(old_reservation["decision_id"]),
        target_binding_digest=str(old_reservation["target_binding_digest"]),
    )
    retry_admission = effect.admit_clean_ownerless_lane(
        root=scenario.repo,
        decision_path=scenario.decision_path,
        decision=scenario.decision,
        executor_ref="agent:codex:thread:executor",
    )
    assert retry_admission.existing_reservation is not None
    assert retry_admission.retry_fence_acquisition_id is None
    events: list[str] = []
    real_release_reservation = retry.release_ownerless_no_effect_reservation
    monkeypatch.setattr(
        retry,
        "release_closeout_fence",
        lambda **_kwargs: pytest.fail("an absent old fence must not be released again"),
    )

    def release_reservation(**kwargs: object) -> None:
        events.append("reservation")
        real_release_reservation(**kwargs)

    monkeypatch.setattr(retry, "release_ownerless_no_effect_reservation", release_reservation)
    retry.reset_reserved_no_effect_retry(
        admission=retry_admission,
        database=state_database(scenario.repo),
        record_root=current_record_root(scenario.repo),
    )

    assert events == ["reservation"]
    assert get_closeout_fence(state_database(scenario.repo), subject="work/orphan") is None
    reservation_path = reservation_store.ownerless_closeout_reservation_path(
        scenario.repo,
        str(old_reservation["target_digest"]),
        artifact_root=current_record_root(scenario.repo),
    )
    assert not reservation_path.exists()


def test_ownerless_no_effect_reservation_release_is_exact_compare_and_delete(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    lane_ref, head = "work/ownerless", "a" * 40
    reservation = {
        "schema_version": 2,
        "decision_id": "lane-decision:00000000-0000-4000-8000-000000000004",
        "lane_ref": lane_ref,
        "head": head,
        "executor_ref": "agent:codex:thread:executor",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": reservation_store.target_digest(lane_ref, head),
        "target_binding_digest": "e" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }
    path = reservation_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation)
    with pytest.raises(ValueError, match="reservation_mismatch"):
        reservation_store.release_ownerless_no_effect_reservation(
            root=repo,
            expected=dict(reservation, target_binding_digest="0" * 64),
        )
    assert path.is_file()
    reservation_store.release_ownerless_no_effect_reservation(root=repo, expected=reservation)
    assert not path.exists()
