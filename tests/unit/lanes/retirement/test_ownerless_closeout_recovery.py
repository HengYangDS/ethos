from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.mutation.resolution._effects as effect_adapter
import ethos.adapters.mutation.resolution.lane as lane_adapter
import ethos.adapters.mutation.resolution.records.core as record_store
from ethos.adapters.mutation.resolution._shared import records_artifact_root
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.receipts import lane_resolution_inventory
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from ethos.adapters.store.state.closeout import get_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos.surface.cli.lane.resolution import _default_decision_path
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import orphan_work_lane

_OWNERLESS_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000004"
_COMPETING_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000005"


def _decide(
    root: Path,
    decision_path: Path,
    disposition: str = "block",
) -> dict[str, object]:
    exceptional = disposition in {"preserve-retire", "retire"}
    return plan_lane_resolution(
        root=root,
        branch="work/orphan",
        disposition=disposition,
        reason="Exercise the bounded lane-resolution transition.",
        evidence_refs=(("evidence:maintainer-decision",) if exceptional else ("evidence:review",)),
        chronicle_ref=write_chronicle_decision(
            root, topic="lane-resolution-test", token=disposition
        ),
        recovery_plan="Preserve exact observed state or block before effect.",
        decision_path=decision_path,
        break_glass=exceptional,
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


def _ownerless_reservation(*, decision_id: str = _OWNERLESS_DECISION_ID) -> dict[str, object]:
    lane_ref, head = "work/20260722-ownerless", "a" * 40
    return {
        "schema_version": 1,
        "decision_id": decision_id,
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


def _ownerless_receipt(binding: dict[str, object] | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "receipt_id": "lane-resolution-receipt:ownerless",
        "decision_id": _OWNERLESS_DECISION_ID,
        "completed": True,
        "state": "retired",
        "observation_digest": "e" * 64,
        "reconciliation_required": False,
        "lane_ref": "work/20260722-ownerless",
        "head": "a" * 40,
        "preservation_package": "",
        "preservation_manifest_sha256": "",
        "mints_authority": False,
    }
    if binding is not None:
        payload["schema_version"] = 2
        payload["ownerless_closeout_binding"] = binding
    return payload


@pytest.mark.parametrize(
    ("gap", "state"),
    [
        (
            "lane_resolution_ownerless_worktree_removed_ref_present",
            "ownerless_worktree_removed_ref_present",
        ),
        (
            "lane_resolution_ownerless_transition_unknown",
            "ownerless_transition_unknown",
        ),
    ],
)
def test_resolution_retains_reservation_for_partial_ref_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gap: str,
    state: str,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    _decide(repo, decision_path, "retire")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setitem(
        apply_lane_resolution.__globals__,
        "retire_clean_ownerless_lane",
        lambda **_kwargs: (_ for _ in ()).throw(
            effect_adapter.OwnerlessCloseoutError(gap, fence_acquired=True)
        ),
    )

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert (report["ok"], report["state"], report["required_gaps"]) == (
        False,
        state,
        [gap],
    )
    assert report["receipt"] == {}
    assert report["receipt_path"] == ""
    assert (
        len(tuple((records_artifact_root(repo) / "receipts").glob(".*.receipt-reservation"))) == 1
    )


def test_resolution_retains_reservation_when_ownerless_worktree_remove_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    _decide(repo, decision_path, "retire")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setitem(
        apply_lane_resolution.__globals__,
        "retire_clean_ownerless_lane",
        lambda **_kwargs: (_ for _ in ()).throw(
            effect_adapter.OwnerlessCloseoutError(
                "lane_resolution_ownerless_worktree_remove_failed",
                fence_acquired=True,
            )
        ),
    )

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert (report["ok"], report["state"], report["required_gaps"]) == (
        False,
        "ownerless_worktree_remove_failed",
        ["lane_resolution_ownerless_worktree_remove_failed"],
    )
    assert lane.is_dir()
    assert git(repo, "show-ref", "--verify", "refs/heads/work/orphan")
    assert report["receipt"] == {}
    assert report["receipt_path"] == ""
    assert (
        len(tuple((records_artifact_root(repo) / "receipts").glob(".*.receipt-reservation"))) == 1
    )


def test_ownerless_reserved_no_effect_retry_reuses_exact_sidecar_and_rechecks_wcp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path, "retire")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        _ownerless_preflight,
    )
    real_verify = effect_adapter._verify_ownerless_pre_effect  # noqa: SLF001, RUF100 - retry seam
    attempts = 0

    def fail_first_verify(**kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            gap = "lane_resolution_ownerless_accepted_head_stale"
            raise effect_adapter.OwnerlessCloseoutError(
                gap,
                fence_acquired=True,
            )
        real_verify(**kwargs)

    monkeypatch.setattr(effect_adapter, "_verify_ownerless_pre_effect", fail_first_verify)

    first = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )
    second = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert first["required_gaps"] == ["lane_resolution_ownerless_accepted_head_stale"]
    assert second["ok"] is True
    assert attempts == 2
    assert not lane.exists()
    target = record_store.target_digest(
        "work/orphan",
        str(planned["decision"]["observation"]["head"]),
    )
    assert not record_store.ownerless_closeout_reservation_path(repo, target).exists()


def test_ownerless_effect_complete_retry_finalizes_receipt_before_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path, "retire")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        _ownerless_preflight,
    )
    real_write = lane_adapter.write_resolution_receipt

    def fail_receipt_write(**_kwargs: object) -> str:
        message = "receipt unavailable"
        raise OSError(message)

    monkeypatch.setattr(lane_adapter, "write_resolution_receipt", fail_receipt_write)
    first = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert first["required_gaps"] == ["lane_resolution_receipt_write_failed_after_effect"]
    assert not lane.exists()
    target = record_store.target_digest(
        "work/orphan",
        str(planned["decision"]["observation"]["head"]),
    )
    reservation_path = record_store.ownerless_closeout_reservation_path(repo, target)
    assert (
        record_store.read_ownerless_closeout_reservation(
            record_root=records_artifact_root(repo),
            path=reservation_path,
        )["recovery_state"]
        == "effect_complete_receipt_missing"
    )
    monkeypatch.setattr(lane_adapter, "write_resolution_receipt", real_write)
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        lambda **_kwargs: pytest.fail("completed effect recovery must not rerun WCP"),
    )

    recovered = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert recovered["ok"] is True
    assert recovered["state"] == "retired"
    assert recovered["receipt"]["ownerless_closeout_binding"]
    assert Path(str(recovered["receipt_path"])).is_file()
    assert not reservation_path.exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    assert not tuple((records_artifact_root(repo) / "receipts").glob(".*.receipt-reservation"))


@pytest.mark.parametrize(
    ("phase", "recovery_state"),
    [
        ("effect", "worktree_removed_ref_present"),
        ("postcondition", "postcondition_failed"),
        ("unknown", "transition_unknown"),
    ],
)
def test_ownerless_other_partial_retry_requires_explicit_reconciliation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    recovery_state: str,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path, "retire")
    decision = planned["decision"]
    observation = decision["observation"]
    accepted_head = git(repo, "rev-parse", "dev")
    reservation = {
        "schema_version": 1,
        "decision_id": decision["decision_id"],
        "lane_ref": observation["lane_ref"],
        "head": observation["head"],
        "executor_ref": "agent:codex:thread:executor",
        "wcp_schema_version": "workstation.repo-family-governance.v1",
        "wcp_decision_sha256": hashlib.sha256(decision_path.read_bytes()).hexdigest(),
        "accepted_branch": "dev",
        "accepted_head": accepted_head,
        "wcp_binding_digest": "d" * 64,
        "target_digest": record_store.target_digest(
            str(observation["lane_ref"]), str(observation["head"])
        ),
        "target_binding_digest": "e" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }
    record_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation)
    record_store.transition_ownerless_closeout_reservation(
        root=repo,
        expected=reservation,
        phase=phase,
        recovery_state=recovery_state,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        lambda **_kwargs: pytest.fail("partial recovery must block before WCP"),
    )

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    assert (report["ok"], report["state"], report["required_gaps"]) == (
        False,
        "partial_transition",
        [f"lane_resolution_ownerless_reconciliation_required:{recovery_state}"],
    )


def test_ownerless_cleanup_keeps_visible_reservation_when_fence_release_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path, "retire")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        _ownerless_preflight,
    )
    monkeypatch.setattr(
        lane_adapter,
        "release_closeout_fence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fence retained")),
    )

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )

    target = record_store.target_digest(
        "work/orphan",
        str(planned["decision"]["observation"]["head"]),
    )
    assert (report["ok"], report["state"], report["required_gaps"]) == (
        False,
        "partial_transition",
        ["lane_resolution_ownerless_cleanup_failed"],
    )
    assert record_store.ownerless_closeout_reservation_path(repo, target).is_file()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is not None


def test_retire_resolution_requires_clean_target_and_irreversible_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    _decide(repo, decision_path, "retire")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")

    def preflight(*, expected, **_kwargs):
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

    monkeypatch.setattr(effect_adapter, "run_worktree_closeout_check", preflight)

    blocked = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert "irreversible_confirmation_required" in blocked["required_gaps"]

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )
    assert applied["ok"] is True
    binding = applied["receipt"]["ownerless_closeout_binding"]
    assert binding["target_digest"] == record_store.target_digest(
        "work/orphan", str(applied["receipt"]["head"])
    )
    assert binding["target_binding_digest"]
    assert not lane.exists()
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "refs/heads/work/orphan"],
            cwd=repo,
            check=False,
        ).returncode
        != 0
    )
    assert not record_store.ownerless_closeout_reservation_path(
        repo,
        str(binding["target_digest"]),
    ).exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None


def test_ownerless_target_reservation_is_target_scoped_and_exactly_resumable(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = _ownerless_reservation()

    path = record_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation)

    assert path.name == f"{reservation['target_digest']}.json"
    assert json.loads(path.read_text(encoding="utf-8")) == reservation
    assert (
        record_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation) == path
    )
    with pytest.raises(FileExistsError):
        record_store.reserve_ownerless_closeout_target(
            root=repo,
            reservation=_ownerless_reservation(decision_id=_COMPETING_DECISION_ID),
        )
    changed = dict(reservation, executor_ref="agent:codex:thread:other")
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_mismatch"):
        record_store.reserve_ownerless_closeout_target(root=repo, reservation=changed)


def test_ownerless_reservation_accepts_the_canonical_holder_ref_contract(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = _ownerless_reservation()
    reservation["executor_ref"] = "agent:Codex:thread:Executor+1"

    path = record_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation)

    assert (
        record_store.read_ownerless_closeout_reservation(
            record_root=records_artifact_root(repo),
            path=path,
        )["executor_ref"]
        == reservation["executor_ref"]
    )


@pytest.mark.parametrize(
    ("phase", "recovery_state"),
    [
        ("effect", "worktree_removed_ref_present"),
        ("receipt", "effect_complete_receipt_missing"),
        ("postcondition", "postcondition_failed"),
        ("unknown", "transition_unknown"),
    ],
)
def test_inventory_exposes_ownerless_partial_reservation(
    tmp_path: Path,
    phase: str,
    recovery_state: str,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = _ownerless_reservation()
    record_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation)
    postcondition_digest = "f" * 64 if recovery_state == "effect_complete_receipt_missing" else ""
    record_store.transition_ownerless_closeout_reservation(
        root=repo,
        expected=reservation,
        phase=phase,
        recovery_state=recovery_state,
        postcondition_digest=postcondition_digest,
    )

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["summary"]["inflight_count"] == 1
    assert inventory["summary"]["partial_count"] == 1
    entry = inventory["entries"][0]
    assert entry["target_digest"] == reservation["target_digest"]
    assert entry["phase"] == phase
    assert entry["recovery_state"] == recovery_state
    assert Path(str(entry["reservation_path"])).is_file()


def test_ownerless_recovery_requires_same_decision_exact_binding_and_complete_effect(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = _ownerless_reservation()
    record_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation)
    with pytest.raises(ValueError, match="lane_resolution_ownerless_recovery_not_finalizable"):
        record_store.ownerless_closeout_recovery_binding(root=repo, expected=reservation)
    completed = record_store.transition_ownerless_closeout_reservation(
        root=repo,
        expected=reservation,
        phase="receipt",
        recovery_state="effect_complete_receipt_missing",
        postcondition_digest="f" * 64,
    )

    binding = record_store.ownerless_closeout_recovery_binding(root=repo, expected=reservation)

    assert binding == {
        key: completed[key]
        for key in (
            "executor_ref",
            "wcp_schema_version",
            "wcp_decision_sha256",
            "accepted_branch",
            "accepted_head",
            "wcp_binding_digest",
            "target_digest",
            "target_binding_digest",
            "postcondition_digest",
        )
    }
    competing = dict(reservation, decision_id=_COMPETING_DECISION_ID)
    with pytest.raises(ValueError, match="lane_resolution_ownerless_recovery_binding_mismatch"):
        record_store.ownerless_closeout_recovery_binding(root=repo, expected=competing)
    receipt = _ownerless_receipt(binding)
    write_resolution_receipt(
        root=repo,
        receipt=receipt,
        require_ownerless_closeout_binding=True,
    )

    record_store.release_ownerless_closeout_reservation(root=repo, expected=reservation)

    assert not record_store.ownerless_closeout_reservation_path(
        repo, str(reservation["target_digest"])
    ).exists()


def test_ownerless_partial_reservation_cannot_be_downgraded_to_no_effect(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = _ownerless_reservation()
    path = record_store.reserve_ownerless_closeout_target(root=repo, reservation=reservation)
    partial = record_store.transition_ownerless_closeout_reservation(
        root=repo,
        expected=reservation,
        phase="unknown",
        recovery_state="transition_unknown",
    )

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.transition_ownerless_closeout_reservation(
            root=repo,
            expected=reservation,
            phase="reserved",
            recovery_state="reserved_no_effect",
        )

    assert json.loads(path.read_text(encoding="utf-8")) == partial


@pytest.mark.parametrize(
    "case",
    [
        "non_object",
        "reserved_with_partial_state",
        "completed_effect_without_digest",
        "non_completed_effect_with_digest",
    ],
)
def test_ownerless_reservation_reader_rejects_invalid_state_contract(
    tmp_path: Path,
    case: str,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation: object = _ownerless_reservation()
    if case == "non_object":
        reservation = []
    elif case == "reserved_with_partial_state":
        reservation = dict(
            _ownerless_reservation(),
            phase="reserved",
            recovery_state="transition_unknown",
        )
    elif case == "completed_effect_without_digest":
        reservation = dict(
            _ownerless_reservation(),
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
        )
    else:
        reservation = dict(
            _ownerless_reservation(),
            phase="unknown",
            recovery_state="transition_unknown",
            postcondition_digest="f" * 64,
        )
    canonical = _ownerless_reservation()
    path = record_store.ownerless_closeout_reservation_path(
        repo,
        str(canonical["target_digest"]),
    )
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(reservation), encoding="utf-8")

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.read_ownerless_closeout_reservation(
            record_root=records_artifact_root(repo),
            path=path,
        )


def test_ownerless_receipt_binding_is_optional_for_history_but_complete_when_required(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = _ownerless_reservation()
    binding = {
        key: value
        for key, value in dict(reservation, postcondition_digest="f" * 64).items()
        if key
        in {
            "executor_ref",
            "wcp_schema_version",
            "wcp_decision_sha256",
            "accepted_branch",
            "accepted_head",
            "wcp_binding_digest",
            "target_digest",
            "target_binding_digest",
            "postcondition_digest",
        }
    }

    legacy_path = write_resolution_receipt(root=repo, receipt=_ownerless_receipt(None))
    assert Path(legacy_path).is_file()
    ownerless = _ownerless_receipt(binding)
    ownerless["decision_id"] = _COMPETING_DECISION_ID
    ownerless_path = write_resolution_receipt(
        root=repo,
        receipt=ownerless,
        require_ownerless_closeout_binding=True,
    )
    assert (
        json.loads(Path(ownerless_path).read_text(encoding="utf-8"))["ownerless_closeout_binding"]
        == binding
    )
    for index, missing in enumerate(("postcondition_digest", "target_binding_digest"), start=6):
        incomplete = dict(ownerless)
        incomplete["decision_id"] = f"lane-decision:00000000-0000-4000-8000-{index:012d}"
        incomplete["ownerless_closeout_binding"] = dict(binding)
        del incomplete["ownerless_closeout_binding"][missing]
        with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
            write_resolution_receipt(
                root=repo,
                receipt=incomplete,
                require_ownerless_closeout_binding=True,
            )
    mismatched = dict(ownerless)
    mismatched["decision_id"] = "lane-decision:00000000-0000-4000-8000-000000000007"
    mismatched["ownerless_closeout_binding"] = dict(binding, target_digest="0" * 64)
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        write_resolution_receipt(
            root=repo,
            receipt=mismatched,
            require_ownerless_closeout_binding=True,
        )
