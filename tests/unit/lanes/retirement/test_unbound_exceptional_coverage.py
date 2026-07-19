from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as unbound_observation
import ethos.adapters.mutation.lane_retirement.unbound.policy.core as unbound_policy
import ethos.adapters.mutation.lane_retirement.unbound.records.core as unbound_records
from ethos.adapters.mutation.lane_retirement.unbound.core import retire_unbound_work_lane_ref
from tests.support.lane_helpers import git
from tests.unit.lanes.retirement.test_unbound_and_helpers import _exceptional_fixture


def test_exceptional_retirement_observation_edges_are_fail_closed(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    chronicle_ref = "evidence/chronicle/test/2026-07-19.md"
    chronicle = repo / chronicle_ref
    chronicle.parent.mkdir(parents=True)
    chronicle.mkdir()

    directory = unbound_observation.chronicle_observation(
        repo,
        accepted_branch="dev",
        chronicle_ref=chronicle_ref,
    )
    assert directory[unbound_observation.HAS_LOCAL_CHRONICLE] is False
    chronicle.rmdir()
    chronicle.write_text("event: lane_retire/unbound_exceptional\n", encoding="utf-8")

    monkeypatch.setattr(
        unbound_observation.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError())
    )
    unreadable = unbound_observation.chronicle_observation(
        repo,
        accepted_branch="dev",
        chronicle_ref=chronicle_ref,
    )
    assert unreadable[unbound_observation.HAS_LOCAL_CHRONICLE] is False
    monkeypatch.undo()

    monkeypatch.setattr(unbound_observation, "git_show_bytes", lambda *_args: None)
    unaccepted = unbound_observation.chronicle_observation(
        repo,
        accepted_branch="dev",
        chronicle_ref=chronicle_ref,
    )
    assert unaccepted[unbound_observation.HAS_LOCAL_CHRONICLE] is True
    assert unaccepted[unbound_observation.HAS_ACCEPTED_CHRONICLE] is False
    assert unbound_observation.chronicle_fields(b"\xff") == {}
    assert unbound_observation.chronicle_path(repo, "") is None
    assert unbound_observation.chronicle_path(repo, "/outside") is None
    assert unbound_observation.chronicle_path(repo, "evidence/chronicle/../escape") is None

    monkeypatch.setattr(Path, "resolve", lambda _path: (_ for _ in ()).throw(OSError()))
    assert unbound_observation.chronicle_path(repo, chronicle_ref) is None
    monkeypatch.undo()

    assert (
        unbound_observation.claim_observation(
            repo,
            accepted_branch="dev",
            claim_id="../invalid",
        )[unbound_observation.HAS_LOCAL_CLAIM]
        is False
    )
    claim = repo / "evidence/claims/test.toml"
    claim.parent.mkdir(parents=True)
    claim.mkdir()
    assert (
        unbound_observation.claim_observation(
            repo,
            accepted_branch="dev",
            claim_id="test",
        )[unbound_observation.HAS_LOCAL_CLAIM]
        is False
    )
    claim.rmdir()
    claim.write_bytes(b"\xff")
    assert (
        unbound_observation.claim_observation(
            repo,
            accepted_branch="dev",
            claim_id="test",
        )[unbound_observation.HAS_LOCAL_CLAIM]
        is False
    )
    claim.write_text('[claim]\nid = "test"\nstate = "active"\n', encoding="utf-8")
    missing_accepted_claim = unbound_observation.claim_observation(
        repo,
        accepted_branch="dev",
        claim_id="test",
    )
    assert missing_accepted_claim[unbound_observation.HAS_LOCAL_CLAIM] is True
    assert missing_accepted_claim[unbound_observation.HAS_ACCEPTED_CLAIM] is False


def test_exceptional_retirement_policy_helpers_cover_every_fail_closed_outcome(
    tmp_path: Path,
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    observed = unbound_observation.observe(repo, branch=branch, chronicle_ref=chronicle)
    unavailable = {**observed, "protected_refs": {"main": "", "dev": head}}
    assert "unbound_retire_protected_ref_unavailable" in unbound_policy.admission_gaps(
        repo,
        branch=branch,
        expect_head=head,
        reason="must require protected refs",
        apply=False,
        authorized=False,
        break_glass=False,
        confirm_irreversible=False,
        observed=unavailable,
    )
    assert unbound_policy.target_gaps(
        {"event": "", "target_branch": "", "target_head": ""},
        branch=branch,
        head=head,
    ) == ["unbound_retire_chronicle_event_missing"]
    assert unbound_policy.target_gaps(
        {
            "event": unbound_policy.EVENT,
            "target_branch": "work/other",
            "target_head": "other",
        },
        branch=branch,
        head=head,
    ) == ["unbound_retire_chronicle_target_mismatch"]

    assert unbound_policy.accepted_control_root({}, accepted_head=head)[1] == (
        "unbound_retire_accepted_control_root_unavailable"
    )
    assert (
        unbound_policy.accepted_control_root({"worktrees": [object()]}, accepted_head=head)[1]
        == "unbound_retire_accepted_control_root_unavailable"
    )
    assert (
        unbound_policy.accepted_control_root(
            {"worktrees": [{"role": unbound_policy.ROLE_ACCEPTED_ROOT, "path": ""}]},
            accepted_head=head,
        )[1]
        == "unbound_retire_accepted_control_root_unavailable"
    )
    assert (
        unbound_policy.accepted_control_root(
            {
                "worktrees": [
                    {
                        "role": unbound_policy.ROLE_ACCEPTED_ROOT,
                        "path": (tmp_path / "missing").as_posix(),
                    }
                ]
            },
            accepted_head=head,
        )[1]
        == "unbound_retire_accepted_control_root_unavailable"
    )
    accepted_head = git(repo, "rev-parse", "dev")
    accepted_status = {
        "worktrees": [{"role": unbound_policy.ROLE_ACCEPTED_ROOT, "path": repo.as_posix()}]
    }
    assert unbound_policy.accepted_control_root(accepted_status, accepted_head="0" * 40)[1] == (
        "unbound_retire_accepted_control_root_stale"
    )
    control_root, gap = unbound_policy.accepted_control_root(
        accepted_status, accepted_head=accepted_head
    )
    assert control_root == repo.resolve()
    assert gap == ""
    assert (
        unbound_policy.accepted_control_root(
            {"worktrees": [{"role": "work_lane", "path": repo.as_posix()}]}, accepted_head=head
        )[1]
        == "unbound_retire_accepted_control_root_unavailable"
    )

    before = {
        "protected_refs": {"main": head},
        "chronicle": {"ref": "before"},
    }
    after = {
        "protected_refs": {"main": "other"},
        "chronicle": {"ref": "after"},
        "head": head,
        "status_unbound": True,
        "worktree_binding": "unbound",
        unbound_observation.HAS_ACTIVE_LEASE: True,
    }
    deleted = subprocess.CompletedProcess(["git", "update-ref"], 1, "", "failed")
    assert unbound_policy.post_effect_gaps(before=before, after=after, deleted=deleted) == [
        "unbound_retire_active_lease",
        "unbound_retire_chronicle_changed",
        "unbound_retire_protected_refs_changed",
        "unbound_retire_ref_delete_failed",
        "unbound_retire_ref_remove_not_observed",
        "unbound_retire_status_postcondition_not_observed",
    ]


def test_exceptional_retirement_records_cover_idempotence_races_and_invalid_payloads(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    before = unbound_observation.observe(repo, branch=branch, chronicle_ref=chronicle)
    operation_id = unbound_records.operation_id(
        branch=branch,
        expect_head=head,
        accepted_head=str(before["accepted_head"]),
        protected_refs=before["protected_refs"],
        claim_id=str(before["claim_id"]),
        chronicle=unbound_observation.chronicle_binding(before),
        reason="coverage record",
        observation_sha256=str(before["observation_sha256"]),
    )
    payload = unbound_records.attempt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=head,
        reason="coverage record",
        observation=before,
    )
    record = tmp_path / "record.json"
    assert unbound_records.write_record(record, payload, kind=unbound_records.ATTEMPT_KIND) == (
        record.as_posix()
    )
    assert unbound_records.write_record(record, payload, kind=unbound_records.ATTEMPT_KIND) == (
        record.as_posix()
    )
    collision = {**payload, "reason": "different valid record"}
    record.write_text(json.dumps(collision), encoding="utf-8")
    with pytest.raises(ValueError, match="unbound_retire_record_collision"):
        unbound_records.write_record(record, payload, kind=unbound_records.ATTEMPT_KIND)

    def race_equal(_source: Path, destination: Path) -> None:
        destination.write_text(json.dumps(payload), encoding="utf-8")
        raise FileExistsError

    equal_race = tmp_path / "equal-race.json"
    monkeypatch.setattr(unbound_records.os, "link", race_equal)
    assert unbound_records.write_record(equal_race, payload, kind=unbound_records.ATTEMPT_KIND) == (
        equal_race.as_posix()
    )

    def race_collision(_source: Path, destination: Path) -> None:
        destination.write_text(json.dumps(collision), encoding="utf-8")
        raise FileExistsError

    monkeypatch.setattr(unbound_records.os, "link", race_collision)
    with pytest.raises(ValueError, match="unbound_retire_record_collision"):
        unbound_records.write_record(
            tmp_path / "collision-race.json",
            payload,
            kind=unbound_records.ATTEMPT_KIND,
        )
    monkeypatch.undo()

    with pytest.raises(ValueError, match="unbound_retire_record_unsafe"):
        unbound_records.read_record(tmp_path, kind=unbound_records.ATTEMPT_KIND)
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="unbound_retire_record_invalid"):
        unbound_records.read_record(malformed, kind=unbound_records.ATTEMPT_KIND)
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError, match="unbound_retire_record_invalid"):
        unbound_records.read_record(malformed, kind=unbound_records.ATTEMPT_KIND)

    invalid_cases = (
        {},
        {**payload, "operation_id": "wrong"},
        {**payload, "branch": "topic"},
        {**payload, "expected_head": "short"},
        {**payload, "mints_authority": True},
        {**payload, "protected_refs": {}},
    )
    for invalid in invalid_cases:
        with pytest.raises(ValueError, match="unbound_retire_record_invalid"):
            unbound_records.validate_record(invalid, kind=unbound_records.ATTEMPT_KIND)

    receipt = {
        **{key: value for key, value in payload.items() if key != "protected_refs"},
        "kind": unbound_records.RECEIPT_KIND,
        "protected_refs_before": payload["protected_refs"],
        "protected_refs_after": before["protected_refs"],
        "after_observation_sha256": "a" * 64,
        "postconditions": {
            "ref_absent": True,
            "unbound_absent": True,
            "active_lease_absent": True,
            "protected_refs_unchanged": True,
            "chronicle_unchanged": True,
        },
    }
    unbound_records.validate_record(receipt, kind=unbound_records.RECEIPT_KIND)
    with pytest.raises(ValueError, match="unbound_retire_record_invalid"):
        unbound_records.validate_record(
            {**receipt, "postconditions": {"ref_absent": False}},
            kind=unbound_records.RECEIPT_KIND,
        )
    with pytest.raises(ValueError, match="unbound_retire_record_invalid"):
        unbound_records.validate_record(
            {**receipt, "protected_refs_after": {"main": "changed"}},
            kind=unbound_records.RECEIPT_KIND,
        )


def test_exceptional_retirement_covers_control_root_and_receipt_write_failures(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    controls = {
        "root": repo,
        "branch": branch,
        "expect_head": head,
        "reason": "coverage control root",
        "chronicle_ref": chronicle,
        "authorized": True,
        "break_glass": True,
        "confirm_irreversible": True,
        "apply": True,
    }
    monkeypatch.setattr(
        unbound_policy,
        "accepted_control_root",
        lambda *_args, **_kwargs: (None, "unbound_retire_accepted_control_root_unavailable"),
    )
    blocked = retire_unbound_work_lane_ref(**controls)
    assert blocked["required_gaps"] == ["unbound_retire_accepted_control_root_unavailable"]
    monkeypatch.undo()

    real_write = unbound_records.write_record

    def fail_receipt(path: Path, payload: dict[str, object], *, kind: str) -> str:
        if kind == unbound_records.RECEIPT_KIND:
            raise OSError(*("receipt write failure",))
        return real_write(path, payload, kind=kind)

    monkeypatch.setattr(unbound_records, "write_record", fail_receipt)
    receipt_failure = retire_unbound_work_lane_ref(**controls)
    assert receipt_failure["required_gaps"] == ["receipt write failure"]
