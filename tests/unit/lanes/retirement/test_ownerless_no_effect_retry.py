from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.mutation.resolution._effects as effect_adapter
import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.release as no_effect_records
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.store.state.closeout import get_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos.surface.cli.lane.resolution import _default_decision_path
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import absorb_obsolete_delta_in_accepted
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import orphan_work_lane

_OWNERLESS_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000004"


def _decide(root: Path, decision_path: Path) -> dict[str, object]:
    return plan_lane_resolution(
        root=root,
        branch="work/orphan",
        disposition="retire",
        reason="Exercise the bounded lane-resolution transition.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=write_chronicle_decision(root, topic="lane-resolution-test", token="retire"),
        recovery_plan="Preserve exact observed state or block before effect.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )


def _ownerless_preflight(*, expected: Any, **_kwargs: object) -> dict[str, object]:
    decision = json.loads(expected.decision_bytes)
    return {
        "schema_version": "workstation.repo-family-governance.v1",
        "decision_sha256": hashlib.sha256(expected.decision_bytes).hexdigest(),
        "executor_ref": expected.executor_ref,
        "observation_digest": hashlib.sha256(
            json.dumps(
                expected.observation,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "chronicle_digest": decision["chronicle_digest"],
        "source": {"head": expected.accepted_head},
        "coordination": {"binding_digest": "d" * 64},
    }


def _ownerless_reservation() -> dict[str, object]:
    lane_ref, head = "work/20260722-ownerless", "a" * 40
    return {
        "schema_version": 1,
        "decision_id": _OWNERLESS_DECISION_ID,
        "lane_ref": lane_ref,
        "head": head,
        "executor_ref": "agent:codex:thread:executor",
        "wcp_schema_version": "workstation.repo-family-governance.v1",
        "wcp_decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "wcp_binding_digest": "d" * 64,
        "target_digest": record_store.target_digest(lane_ref, head),
        "target_binding_digest": "e" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }


def _apply_retire(repo: Path, decision_path: Path) -> dict[str, object]:
    return apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )


def _start_reserved_no_effect_attempt(
    repo: Path,
    decision_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, object], dict[str, int]]:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        _ownerless_preflight,
    )
    real_verify = effect_adapter._verify_ownerless_pre_effect  # noqa: SLF001, RUF100 - retry seam
    attempts = {"count": 0}

    def fail_first_verify(**kwargs: object) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            gap = "lane_resolution_ownerless_accepted_head_stale"
            raise effect_adapter.OwnerlessCloseoutError(
                gap,
                fence_acquired=True,
            )
        real_verify(**kwargs)

    monkeypatch.setattr(effect_adapter, "_verify_ownerless_pre_effect", fail_first_verify)
    return _apply_retire(repo, decision_path), attempts


def _planned_reservation_path(repo: Path, planned: dict[str, object]) -> Path:
    decision = planned["decision"]
    assert isinstance(decision, dict)
    observation = decision["observation"]
    assert isinstance(observation, dict)
    target = record_store.target_digest(
        "work/orphan",
        str(observation["head"]),
    )
    return record_store.ownerless_closeout_reservation_path(repo, target)


def test_ownerless_reserved_no_effect_retry_reuses_exact_sidecar_and_rechecks_wcp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    second = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert second["ok"] is True
    assert attempts["count"] == 2
    assert not lane.exists()
    assert not _planned_reservation_path(repo, planned).exists()


def test_ownerless_reserved_no_effect_retry_rebinds_after_accepted_forward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    old_fence = get_closeout_fence(state_database(repo), subject="work/orphan")
    new_accepted_head = absorb_obsolete_delta_in_accepted(repo)
    second = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert old_fence is not None
    assert old_fence["accepted_head"] != new_accepted_head
    assert second["ok"] is True
    assert second["receipt"]["ownerless_closeout_binding"]["accepted_head"] == new_accepted_head
    assert attempts["count"] == 2
    assert not lane.exists()
    assert not _planned_reservation_path(repo, planned).exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None


def test_ownerless_reserved_no_effect_retry_recovers_after_fence_release_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    new_accepted_head = absorb_obsolete_delta_in_accepted(repo)
    real_release = effect_adapter.release_ownerless_no_effect_reservation

    def fail_reservation_release(**_kwargs: object) -> None:
        message = "simulated crash after fence release"
        raise OSError(message)

    monkeypatch.setattr(
        effect_adapter,
        "release_ownerless_no_effect_reservation",
        fail_reservation_release,
    )
    interrupted = _apply_retire(repo, decision_path)
    reservation_path = _planned_reservation_path(repo, planned)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert interrupted["required_gaps"] == ["lane_resolution_ownerless_retry_reset_failed"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    assert reservation_path.is_file()
    assert lane.is_dir()

    monkeypatch.setattr(
        effect_adapter,
        "release_ownerless_no_effect_reservation",
        real_release,
    )
    recovered = _apply_retire(repo, decision_path)

    assert recovered["ok"] is True
    assert recovered["receipt"]["ownerless_closeout_binding"]["accepted_head"] == new_accepted_head
    assert not reservation_path.exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    assert not lane.exists()


def test_ownerless_reserved_no_effect_retry_rejects_divergent_accepted_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    old_fence = get_closeout_fence(state_database(repo), subject="work/orphan")
    old_accepted_head = git(repo, "rev-parse", "dev")
    accepted_tree = git(repo, "rev-parse", f"{old_accepted_head}^{{tree}}")
    divergent_head = git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit-tree",
        accepted_tree,
        "-m",
        "divergent accepted history",
    )
    git(repo, "update-ref", "refs/heads/dev", divergent_head, old_accepted_head)

    blocked = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert blocked["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") == old_fence
    assert _planned_reservation_path(repo, planned).is_file()
    assert lane.is_dir()
    assert git(repo, "show-ref", "--verify", "refs/heads/work/orphan")


@pytest.mark.parametrize(
    ("fence_state", "fence", "expected_gap"),
    [
        ("present", {"different": True}, "lane_resolution_ownerless_fence_stale"),
        ("present", None, "lane_resolution_ownerless_fence_unverifiable"),
        ("unverifiable", None, "lane_resolution_ownerless_fence_unverifiable"),
        ("unknown", None, "lane_resolution_ownerless_fence_unverifiable"),
        ("absent", {"unexpected": True}, "lane_resolution_ownerless_fence_unverifiable"),
    ],
)
def test_ownerless_reserved_no_effect_retry_rejects_untrusted_fence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fence_state: str,
    fence: dict[str, object] | None,
    expected_gap: str,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    old_fence = get_closeout_fence(state_database(repo), subject="work/orphan")
    absorb_obsolete_delta_in_accepted(repo)
    monkeypatch.setattr(
        effect_adapter,
        "probe_closeout_fence",
        lambda *_args, **_kwargs: (fence_state, fence),
    )

    blocked = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert blocked["required_gaps"] == [expected_gap]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") == old_fence
    assert _planned_reservation_path(repo, planned).is_file()
    assert lane.is_dir()


def test_ownerless_reserved_no_effect_retry_rejects_executor_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    old_fence = get_closeout_fence(state_database(repo), subject="work/orphan")
    absorb_obsolete_delta_in_accepted(repo)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:different-executor")

    blocked = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert blocked["required_gaps"] == [
        "lane_resolution_ownerless_recovery_binding_mismatch:executor_ref"
    ]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") == old_fence
    assert _planned_reservation_path(repo, planned).is_file()
    assert lane.is_dir()


def test_ownerless_reserved_no_effect_retry_rejects_correlated_binding_corruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    reservation_path = _planned_reservation_path(repo, planned)
    reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
    reservation["target_binding_digest"] = "0" * 64
    reservation_path.write_text(
        json.dumps(reservation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with closing(sqlite3.connect(state_database(repo))) as connection:
        connection.execute(
            "update closeout_fences set target_binding_digest = ? where subject = ?",
            ("0" * 64, "work/orphan"),
        )
        connection.commit()
    absorb_obsolete_delta_in_accepted(repo)

    blocked = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert blocked["required_gaps"] == ["lane_resolution_ownerless_fence_stale"]
    assert reservation_path.is_file()
    assert lane.is_dir()
    assert git(repo, "show-ref", "--verify", "refs/heads/work/orphan")


def test_ownerless_reserved_no_effect_retry_maps_ancestry_probe_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    old_fence = get_closeout_fence(state_database(repo), subject="work/orphan")
    absorb_obsolete_delta_in_accepted(repo)
    real_run_git = effect_adapter.run_git

    def fail_ancestry(root: Path, *args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("merge-base", "--is-ancestor"):
            message = "ancestry probe unavailable"
            raise OSError(message)
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(effect_adapter, "run_git", fail_ancestry)
    blocked = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert blocked["required_gaps"] == ["lane_resolution_ownerless_retry_reset_failed"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") == old_fence
    assert _planned_reservation_path(repo, planned).is_file()
    assert lane.is_dir()


def test_ownerless_reserved_no_effect_retry_maps_reservation_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    old_fence = get_closeout_fence(state_database(repo), subject="work/orphan")
    absorb_obsolete_delta_in_accepted(repo)

    def fail_read(**_kwargs: object) -> dict[str, object]:
        message = "reservation unavailable"
        raise ValueError(message)

    monkeypatch.setattr(effect_adapter, "read_ownerless_closeout_reservation", fail_read)
    blocked = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert blocked["required_gaps"] == ["lane_resolution_ownerless_reservation_failed"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") == old_fence
    assert _planned_reservation_path(repo, planned).is_file()
    assert lane.is_dir()


def test_ownerless_reserved_no_effect_retry_rejects_decision_removed_after_wcp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    old_fence = get_closeout_fence(state_database(repo), subject="work/orphan")
    absorb_obsolete_delta_in_accepted(repo)

    def preflight_then_remove_decision(*, expected: Any, **kwargs: object) -> dict[str, object]:
        response = _ownerless_preflight(expected=expected, **kwargs)
        decision_path.unlink()
        return response

    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        preflight_then_remove_decision,
    )
    blocked = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert blocked["required_gaps"] == ["lane_resolution_ownerless_decision_stale"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") == old_fence
    assert _planned_reservation_path(repo, planned).is_file()
    assert lane.is_dir()


@pytest.mark.parametrize(
    ("drift", "expected_gap"),
    [
        ("decision", "lane_resolution_ownerless_decision_stale"),
        ("accepted", "lane_resolution_ownerless_accepted_head_stale"),
        ("observation", "lane_resolution_ownerless_observation_stale"),
    ],
)
def test_ownerless_reserved_no_effect_retry_rejects_post_probe_state_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
    expected_gap: str,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    old_fence = get_closeout_fence(state_database(repo), subject="work/orphan")
    absorb_obsolete_delta_in_accepted(repo)
    real_probe = effect_adapter.probe_closeout_fence
    drifted = False

    def probe_then_drift(*args: object, **kwargs: object):
        nonlocal drifted
        result = real_probe(*args, **kwargs)
        if drifted:
            return result
        drifted = True
        if drift == "decision":
            decision_path.write_bytes(decision_path.read_bytes() + b"\n")
        elif drift == "accepted":
            git(
                repo,
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "advance accepted during retry",
            )
        else:
            (lane / "late-drift.txt").write_text("drift\n", encoding="utf-8")
        return result

    monkeypatch.setattr(effect_adapter, "probe_closeout_fence", probe_then_drift)
    blocked = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert blocked["required_gaps"] == [expected_gap]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") == old_fence
    assert _planned_reservation_path(repo, planned).is_file()
    assert lane.is_dir()


def test_ownerless_reserved_no_effect_retry_rejects_late_coordination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    first, _attempts = _start_reserved_no_effect_attempt(repo, decision_path, monkeypatch)
    old_fence = get_closeout_fence(state_database(repo), subject="work/orphan")
    absorb_obsolete_delta_in_accepted(repo)
    monkeypatch.setattr(
        effect_adapter,
        "leases_by_branch",
        lambda _root: {"work/orphan": {"holder_ref": "agent:test:case:late"}},
    )
    blocked = _apply_retire(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert blocked["required_gaps"] == [
        "lane_resolution_ownerless_recovery_binding_mismatch:coordination"
    ]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") == old_fence
    assert _planned_reservation_path(repo, planned).is_file()
    assert lane.is_dir()


def test_ownerless_no_effect_reservation_release_is_exact_compare_and_delete(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = _ownerless_reservation()
    path = record_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation)

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_mismatch"):
        no_effect_records.release_ownerless_no_effect_reservation(
            root=repo,
            expected=dict(reservation, wcp_binding_digest="0" * 64),
        )

    assert path.is_file()
    no_effect_records.release_ownerless_no_effect_reservation(root=repo, expected=reservation)
    assert not path.exists()


def test_ownerless_no_effect_reservation_release_rejects_unsafe_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = _ownerless_reservation()
    path = record_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation)
    monkeypatch.setattr(no_effect_records, "record_destination_safe", lambda *_args: False)

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        no_effect_records.release_ownerless_no_effect_reservation(
            root=repo,
            expected=reservation,
        )

    assert path.is_file()
