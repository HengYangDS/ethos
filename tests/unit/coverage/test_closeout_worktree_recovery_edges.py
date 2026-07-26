# fmt: off
from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path
from subprocess import CompletedProcess

import pytest

import ethos.adapters.mutation.closeout.core as closeout
import ethos.adapters.mutation.core as mutation
from ethos.adapters.mutation.core import CloseoutWorktreeRecoveryInputs
from ethos_core.contracts.branch.roles import BranchRolePolicy
from ethos_core.contracts.lifecycle.core import (
    CloseoutWorktreeRecoveryRequest as RecoveryMutationRequest,
)


def _internal(name: str):
    return getattr(closeout, name)


atomic_rename_no_replace = _internal("_atomic_rename_no_replace")
fingerprint = _internal("_fingerprint")
lock_fact = _internal("_lock_fact")
post_recovery_gaps = _internal("_post_recovery_gaps")
quarantine_fact = _internal("_quarantine_fact")
quarantine_lock = _internal("_quarantine_lock")
recovery_head_drift_gaps = _internal("_recovery_head_drift_gaps")
recovery_receipt = _internal("_recovery_receipt")


def _request(
    tmp_path: Path,
    *,
    receipt: Path | None = None,
    expected_receipt_sha256: str = "c" * 64,
    expected_lock_sha256: str = "d" * 64,
    quarantine: Path | None = None,
) -> closeout.CloseoutWorktreeRecoveryRequest:
    return closeout.CloseoutWorktreeRecoveryRequest(
        root=tmp_path / "accepted",
        policy=BranchRolePolicy(),
        current_head="a" * 40,
        candidate_head="b" * 40,
        candidate_path=tmp_path / "candidate",
        failure_receipt=receipt,
        expected_failure_receipt_sha256=expected_receipt_sha256,
        expected_index_lock_sha256=expected_lock_sha256,
        lock_quarantine=quarantine,
    )


def _completed(*, stdout: str = "", stderr: str = "", returncode: int = 0) -> CompletedProcess[str]:
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _failure_receipt(previous: str, candidate: str, **overrides: object) -> dict[str, object]:
    update = {
        "branch": "dev",
        "source_branch": "candidate/dev",
        "head": previous,
        "previous_head": previous,
        "candidate_head": candidate,
        "required_gaps": ["accepted_worktree_sync_failed"],
    }
    update.update(overrides)
    return {
        "command": "land",
        "ok": False,
        "state": "blocked",
        "data": {"accepted_update": update},
    }


def test_recovery_quarantine_keeps_source_when_atomic_no_replace_rejects_target_race(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A concurrent target creation cannot consume the only lock evidence."""
    lock = tmp_path / "index.lock"
    quarantine = tmp_path / "quarantine.lock"
    lock.write_bytes(b"stale lock\n")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    lock_fingerprint = lock_fact(lock, digest)[0]["fingerprint"]

    def reject_target_race(_source: Path, target: Path) -> None:
        target.write_bytes(b"raced target\n")
        raise FileExistsError(errno.EEXIST, "target raced")

    monkeypatch.setattr(closeout, "_atomic_rename_no_replace", reject_target_race, raising=False)

    assert quarantine_lock(lock, quarantine, lock_fingerprint, digest) == "recovery_lock_quarantine_exists"
    assert lock.read_bytes() == b"stale lock\n"
    assert quarantine.read_bytes() == b"raced target\n"


def test_atomic_no_replace_never_overwrites_existing_quarantine_target(tmp_path: Path) -> None:
    """The relocation primitive preserves both source and existing destination."""
    source = tmp_path / "index.lock"
    target = tmp_path / "quarantine.lock"
    source.write_bytes(b"source\n")
    target.write_bytes(b"existing\n")

    try:
        atomic_rename_no_replace(source, target)
    except FileExistsError:
        pass
    else:  # pragma: no cover - the assertion below gives the contract failure.
        pytest.fail("atomic no-replace relocation overwrote an existing target")

    assert source.read_bytes() == b"source\n"
    assert target.read_bytes() == b"existing\n"


def test_recovery_quarantine_rejects_a_dangling_symlink_target(tmp_path: Path) -> None:
    """A dangling target is still an occupied forensic destination."""
    lock = tmp_path / "index.lock"
    quarantine = tmp_path / "quarantine.lock"
    lock.write_bytes(b"stale lock\n")
    quarantine.symlink_to(tmp_path / "missing-target")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    lock_data = lock_fact(lock, digest)[0]

    _fact, gaps = quarantine_fact(
        quarantine,
        root=tmp_path / "accepted",
        candidate_path=tmp_path / "candidate",
        lock=lock_data,
    )

    assert gaps == ["recovery_lock_quarantine_exists"]


def test_recovery_rechecks_promoted_refs_after_quarantine_before_reset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A post-quarantine ref drift must block before the destructive reset."""
    lock = tmp_path / "index.lock"
    quarantine = tmp_path / "quarantine.lock"
    lock.write_bytes(b"stale lock\n")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    lock_data = lock_fact(lock, digest)[0]
    request = closeout.CloseoutWorktreeRecoveryRequest(
        root=tmp_path / "accepted",
        policy=BranchRolePolicy(),
        current_head="a" * 40,
        candidate_head="b" * 40,
        candidate_path=tmp_path / "candidate",
        failure_receipt=tmp_path / "receipt.json",
        expected_failure_receipt_sha256="c" * 64,
        expected_index_lock_sha256=digest,
        lock_quarantine=quarantine,
    )
    inspected = {
        "ok": True,
        "previous_head": "d" * 40,
        "receipt": {},
        "index_lock": lock_data,
        "lock_quarantine": {"path": quarantine.as_posix()},
        "required_gaps": [],
    }
    sync_calls: list[object] = []
    monkeypatch.setattr(
        closeout,
        "inspect_accepted_worktree_sync_recovery",
        lambda *_args, **_kwargs: inspected,
    )
    events: list[str] = []

    def quarantined(*_args) -> str:
        events.append("quarantine")
        return ""

    monkeypatch.setattr(closeout, "_quarantine_lock", quarantined)
    monkeypatch.setattr(
        closeout,
        "_recovery_heads",
        lambda *_args: events.append("heads") or {"head": "e" * 40, "accepted": "e" * 40, "candidate": "b" * 40},
    )
    monkeypatch.setattr(closeout, "_post_recovery_gaps", lambda *_args, **_kwargs: [])

    def record_sync(*_args, **_kwargs):
        events.append("sync")
        sync_calls.append(True)
        return CompletedProcess(args=[], returncode=0, stdout="", stderr=""), 1

    monkeypatch.setattr(closeout, "sync_worktree_to_head", record_sync)

    report = closeout.recover_accepted_worktree_sync(
        request,
        dependencies=closeout.CloseoutDependencies(is_ancestor=lambda *_args: True),
    )

    assert report["required_gaps"] == ["recovery_promoted_refs_drifted"]
    assert sync_calls == []
    assert events == ["quarantine", "heads"]


def test_recovery_receipt_rejects_malformed_and_mismatched_failure_boundaries(tmp_path: Path) -> None:
    """Receipt parsing keeps every required forensic binding fail-closed."""
    receipt = tmp_path / "receipt.json"
    previous, candidate = "e" * 40, "a" * 40
    cases = (
        (b"not-json", "recovery_failure_receipt_invalid"),
        (json.dumps(_failure_receipt(previous, candidate, required_gaps=["other_failure"])).encode(), "recovery_failure_receipt_not_sync_failure"),
        (json.dumps(_failure_receipt(previous, candidate, branch="main")).encode(), "recovery_failure_receipt_branch_mismatch"),
        (json.dumps(_failure_receipt(previous, candidate, head="f" * 40)).encode(), "recovery_failure_receipt_head_invalid"),
    )
    for raw, expected_gap in cases:
        receipt.write_bytes(raw)
        _fact, gaps = recovery_receipt(
            _request(tmp_path, receipt=receipt, expected_receipt_sha256=hashlib.sha256(raw).hexdigest())
        )
        assert expected_gap in gaps


def test_recovery_lock_and_quarantine_checks_cover_unsafe_inputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Unsafe lock facts and non-atomic relocation never consume evidence."""
    lock = tmp_path / "index.lock"
    lock.write_bytes(b"stale lock\n")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    directory = tmp_path / "not-a-lock"
    directory.mkdir()
    _fact, gaps = lock_fact(directory, digest)
    assert gaps == ["recovery_index_lock_type_invalid"]
    link = tmp_path / "link.lock"
    link.symlink_to(lock)
    _fact, gaps = lock_fact(link, digest)
    assert gaps == ["recovery_index_lock_type_invalid"]
    _fact, gaps = lock_fact(lock, "0" * 64)
    assert gaps == ["recovery_index_lock_digest_mismatch"]
    original_fingerprint = fingerprint
    calls: list[object] = []

    def drifted_fingerprint(value):
        calls.append(value)
        return original_fingerprint(value) | {"mtime_ns": len(calls)}

    monkeypatch.setattr(closeout, "_fingerprint", drifted_fingerprint)
    _fact, gaps = lock_fact(lock, digest)
    assert gaps == ["recovery_index_lock_drift"]
    monkeypatch.setattr(closeout, "_fingerprint", original_fingerprint)
    lock_data = lock_fact(lock, digest)[0]
    quarantine = tmp_path / "quarantine.lock"
    _fact, gaps = quarantine_fact(
        tmp_path / "accepted" / "inside.lock",
        root=tmp_path / "accepted",
        candidate_path=tmp_path / "candidate",
        lock=lock_data,
    )
    assert gaps == ["recovery_lock_quarantine_invalid"]
    original_stat = Path.stat

    def cross_device_stat(path: Path, *args, **kwargs):
        value = original_stat(path, *args, **kwargs)
        if path == quarantine.parent:
            values = list(value)
            values[2] += 1
            return os.stat_result(values)
        return value

    monkeypatch.setattr(Path, "stat", cross_device_stat)
    _fact, gaps = quarantine_fact(
        quarantine,
        root=tmp_path / "accepted",
        candidate_path=tmp_path / "candidate",
        lock=lock_data,
    )
    assert gaps == ["recovery_lock_quarantine_cross_device"]
    monkeypatch.setattr(Path, "stat", original_stat)

    def unavailable_atomic_move(*_args) -> None:
        raise OSError(errno.ENOTSUP, "atomic no-replace unavailable")

    monkeypatch.setattr(closeout, "_atomic_rename_no_replace", unavailable_atomic_move)
    assert quarantine_lock(lock, quarantine, lock_data["fingerprint"], digest) == "recovery_lock_quarantine_move_failed"
    assert lock.read_bytes() == b"stale lock\n"
    assert quarantine.exists() is False


def test_recovery_records_quarantine_when_sync_fails_and_postconditions_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A moved lock remains observable when synchronization or final checks block."""
    lock = tmp_path / "index.lock"
    quarantine = tmp_path / "quarantine.lock"
    lock.write_bytes(b"stale lock\n")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    lock_data = lock_fact(lock, digest)[0]
    request = _request(tmp_path, expected_lock_sha256=digest, quarantine=quarantine)
    inspected = {
        "ok": True,
        "previous_head": "e" * 40,
        "receipt": {},
        "index_lock": lock_data,
        "lock_quarantine": {"path": quarantine.as_posix()},
        "required_gaps": [],
    }
    head_drift_gaps = recovery_head_drift_gaps
    monkeypatch.setattr(closeout, "inspect_accepted_worktree_sync_recovery", lambda *_args, **_kwargs: inspected)
    monkeypatch.setattr(closeout, "_recovery_head_drift_gaps", lambda *_args: [])
    monkeypatch.setattr(closeout, "sync_worktree_to_head", lambda *_args: (_completed(stderr="reset failed", returncode=1), 2))
    report = closeout.recover_accepted_worktree_sync(request)
    assert report["required_gaps"] == ["recovery_worktree_sync_failed"]
    assert report["lock_quarantine"] == {"path": quarantine.as_posix()}
    assert lock.exists() is False
    assert quarantine.read_bytes() == b"stale lock\n"
    monkeypatch.setattr(closeout, "_recovery_head_drift_gaps", head_drift_gaps)

    def post_run(_root: Path, *args: str, **_kwargs) -> CompletedProcess[str]:
        if args[-1] == "HEAD" or args[-1] == "dev":
            return _completed(stdout="f" * 40)
        if args[-1] == "candidate/dev":
            return _completed(returncode=1)
        if args[:2] == ("status", "--short"):
            return _completed(stdout="M README.md\n")
        return _completed()

    assert post_recovery_gaps(
        request,
        lock=lock_data,
        quarantine=quarantine,
        run=post_run,
    ) == [
        "recovery_promoted_refs_drifted",
        "recovery_candidate_drifted",
        "recovery_worktree_dirty_after_sync",
    ]
    lock.write_bytes(b"newly-present lock\n")
    assert "recovery_index_lock_present_after_sync" in post_recovery_gaps(
        request,
        lock=lock_data,
        quarantine=quarantine,
        run=post_run,
    )


def test_recovery_report_blocks_malformed_observation_before_effect(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Malformed inspection output cannot silently become a recoverable residue."""
    head = "a" * 40
    candidate = tmp_path / "candidate"
    monkeypatch.setattr(mutation, "run_git", lambda *_args, **_kwargs: _completed(stdout=head))
    monkeypatch.setattr(mutation, "load_branch_role_policy", lambda *_args: BranchRolePolicy())
    monkeypatch.setattr(
        mutation,
        "workspace_status",
        lambda *_args, **_kwargs: {
            "role": "accepted_root",
            "dirty": True,
            "candidate": {"head": head, "worktree_path": candidate.as_posix()},
        },
    )
    monkeypatch.setattr(
        mutation,
        "inspect_accepted_worktree_sync_recovery",
        lambda *_args, **_kwargs: {"ok": False, "residue_exact": True, "required_gaps": None},
    )
    monkeypatch.setattr(
        mutation,
        "recover_accepted_worktree_sync",
        lambda *_args, **_kwargs: pytest.fail("malformed observation reached recovery effect"),
    )

    report = mutation.closeout_worktree_sync_recovery_report(
        root=tmp_path,
        request=RecoveryMutationRequest(
            command="closeout_worktree_recovery",
            apply=True,
            authorized=True,
            expect_head=head,
            confirm_stale_index_lock=True,
            confirm_irreversible=True,
        ),
        inputs=CloseoutWorktreeRecoveryInputs(
            failure_receipt=None,
            expect_failure_receipt_sha256="",
            expect_index_lock_sha256="",
            lock_quarantine=None,
        ),
    )

    assert report["required_gaps"] == ["recovery_observation_invalid"]
