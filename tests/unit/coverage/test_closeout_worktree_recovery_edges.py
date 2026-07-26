# fmt: off
from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace

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
index_lock_path = _internal("_index_lock_path")
inside = _internal("_inside")
lock_fact = _internal("_lock_fact")
post_recovery_gaps = _internal("_post_recovery_gaps")
quarantine_fact = _internal("_quarantine_fact")
quarantine_lock = _internal("_quarantine_lock")
recovery_head_drift_gaps = _internal("_recovery_head_drift_gaps")
recovery_residue_gaps = _internal("_recovery_residue_gaps")
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


def test_recovery_inspection_reports_each_forensic_precondition(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Inspection accumulates each failed receipt, head, and lock binding."""
    current = "a" * 40

    def inspect(
        receipt: dict[str, object],
        heads: dict[str, str],
        is_ancestor,
        lock_gap: str = "",
    ) -> dict[str, object]:
        monkeypatch.setattr(closeout, "_recovery_receipt", lambda *_args: (receipt, []))
        monkeypatch.setattr(closeout, "_recovery_heads", lambda *_args: heads)
        monkeypatch.setattr(closeout, "_recovery_residue_gaps", lambda *_args: [])
        monkeypatch.setattr(closeout, "_index_lock_path", lambda *_args: (None, lock_gap))
        monkeypatch.setattr(closeout, "_lock_fact", lambda *_args: ({}, []))
        monkeypatch.setattr(closeout, "_quarantine_fact", lambda *_args, **_kwargs: ({}, []))
        return closeout.inspect_accepted_worktree_sync_recovery(
            _request(tmp_path),
            dependencies=closeout.CloseoutDependencies(is_ancestor=is_ancestor),
        )

    missing = inspect(
        {},
        {"head": "wrong", "accepted": "wrong", "candidate": ""},
        lambda *_args: False,
        "recovery_index_lock_path_unavailable",
    )
    assert missing["required_gaps"] == [
        "recovery_previous_head_missing",
        "recovery_candidate_head_missing",
        "recovery_promoted_refs_mismatch",
        "recovery_candidate_not_descendant",
        "recovery_index_lock_path_unavailable",
    ]

    previous, receipt_candidate, observed_candidate = "c" * 40, "b" * 40, "d" * 40
    drifted = inspect(
        {"previous_head": previous, "candidate_head": receipt_candidate},
        {"head": current, "accepted": current, "candidate": observed_candidate},
        lambda _root, left, right: (left, right) == (current, observed_candidate),
    )
    assert drifted["required_gaps"] == [
        "recovery_receipt_candidate_head_mismatch",
        "recovery_previous_head_not_ancestor",
    ]

    invalid_previous = inspect(
        {"previous_head": "not-a-head", "candidate_head": current},
        {"head": current, "accepted": current, "candidate": current},
        lambda *_args: True,
    )
    assert invalid_previous["required_gaps"] == ["recovery_previous_head_invalid"]


def test_recovery_effect_rejects_invalid_inspection_and_post_sync_gaps(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Effect execution cannot pass malformed, raced, or post-sync observations."""
    lock = tmp_path / "index.lock"
    quarantine = tmp_path / "quarantine.lock"
    lock.write_bytes(b"stale lock\n")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    request = _request(tmp_path, expected_lock_sha256=digest, quarantine=quarantine)
    lock_data = lock_fact(lock, digest)[0]

    monkeypatch.setattr(
        closeout,
        "inspect_accepted_worktree_sync_recovery",
        lambda *_args, **_kwargs: {"ok": False, "required_gaps": ["recovery_not_ready"]},
    )
    not_ready = closeout.recover_accepted_worktree_sync(request)
    assert not_ready["required_gaps"] == ["recovery_not_ready"]

    for lock_observation, expected_gap in (
        ([], "recovery_observation_invalid"),
        ({"fingerprint": []}, "recovery_index_lock_fingerprint_invalid"),
    ):
        monkeypatch.setattr(
            closeout,
            "inspect_accepted_worktree_sync_recovery",
            lambda *_args, lock_observation=lock_observation, **_kwargs: {
                "ok": True,
                "index_lock": lock_observation,
                "lock_quarantine": {},
                "required_gaps": [],
            },
        )
        report = closeout.recover_accepted_worktree_sync(request)
        assert report["required_gaps"] == [expected_gap]

    inspected = {
        "ok": True,
        "previous_head": "e" * 40,
        "receipt": {},
        "index_lock": lock_data,
        "lock_quarantine": {"path": quarantine.as_posix()},
        "required_gaps": [],
    }
    monkeypatch.setattr(
        closeout,
        "inspect_accepted_worktree_sync_recovery",
        lambda *_args, **_kwargs: inspected,
    )
    monkeypatch.setattr(closeout, "_quarantine_lock", lambda *_args: "recovery_index_lock_drift")
    raced = closeout.recover_accepted_worktree_sync(request)
    assert raced["required_gaps"] == ["recovery_index_lock_drift"]
    assert "lock_quarantined" not in raced

    monkeypatch.setattr(closeout, "_quarantine_lock", lambda *_args: "")
    monkeypatch.setattr(closeout, "_recovery_head_drift_gaps", lambda *_args: [])
    monkeypatch.setattr(closeout, "sync_worktree_to_head", lambda *_args: (_completed(), 1))
    monkeypatch.setattr(
        closeout,
        "_post_recovery_gaps",
        lambda *_args, **_kwargs: ["recovery_postcondition_failed"],
    )
    post_sync = closeout.recover_accepted_worktree_sync(request)
    assert post_sync["required_gaps"] == ["recovery_postcondition_failed"]
    assert post_sync["lock_quarantine"] == {"path": quarantine.as_posix()}


def test_recovery_private_helpers_fail_closed_on_unreadable_forensic_inputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Private forensic helpers reject every unreadable or racing input state."""
    request = _request(tmp_path)
    assert recovery_receipt(request) == ({}, ["recovery_failure_receipt_required"])

    inside_receipt = request.root / "receipt.json"
    inside_receipt.parent.mkdir()
    inside_receipt.write_text("{}", encoding="utf-8")
    _fact, gaps = recovery_receipt(_request(tmp_path, receipt=inside_receipt))
    assert gaps == ["recovery_failure_receipt_invalid"]

    external_receipt = tmp_path / "receipt.json"
    external_receipt.write_text("{}", encoding="utf-8")
    _fact, gaps = recovery_receipt(
        _request(
            tmp_path,
            receipt=external_receipt,
            expected_receipt_sha256="not-a-digest",
        )
    )
    assert gaps == [
        "recovery_failure_receipt_digest_invalid",
        "recovery_failure_receipt_shape_invalid",
    ]

    assert recovery_residue_gaps(tmp_path, "", lambda *_args, **_kwargs: _completed()) == [
        "recovery_previous_head_missing"
    ]
    assert index_lock_path(tmp_path, lambda *_args, **_kwargs: _completed(returncode=1)) == (
        None,
        "recovery_index_lock_path_unavailable",
    )

    lock = tmp_path / "index.lock"
    lock.write_bytes(b"stale lock\n")
    assert lock_fact(lock, "not-a-digest")[1] == ["recovery_index_lock_digest_invalid"]
    missing_lock = tmp_path / "missing.lock"
    assert lock_fact(missing_lock, "a" * 64)[1] == ["recovery_index_lock_missing"]
    lock_data = lock_fact(lock, hashlib.sha256(lock.read_bytes()).hexdigest())[0]
    quarantine = tmp_path / "quarantine.lock"

    original_lstat = Path.lstat
    with monkeypatch.context() as patch:
        def unreadable_quarantine(path: Path):
            if path == quarantine:
                raise PermissionError
            return original_lstat(path)

        patch.setattr(
            Path,
            "lstat",
            unreadable_quarantine,
        )
        _fact, gaps = quarantine_fact(
            quarantine,
            root=request.root,
            candidate_path=request.candidate_path,
            lock=lock_data,
        )
    assert gaps == ["recovery_lock_quarantine_invalid"]

    _fact, gaps = quarantine_fact(
        quarantine,
        root=request.root,
        candidate_path=request.candidate_path,
        lock={"path": (tmp_path / "missing-source.lock").as_posix()},
    )
    assert gaps == ["recovery_lock_quarantine_invalid"]

    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    assert quarantine_lock(lock, quarantine, {"ino": -1}, digest) == "recovery_index_lock_drift"
    with monkeypatch.context() as patch:
        patch.setattr(closeout, "_atomic_rename_no_replace", lambda *_args: None)
        assert (
            quarantine_lock(lock, quarantine, lock_data["fingerprint"], digest)
            == "recovery_lock_quarantine_drifted"
        )
    with monkeypatch.context() as patch:
        def stable_lock_fact(path: Path, expected: str):
            return {
                "path": path.as_posix(),
                "sha256": expected,
                "fingerprint": lock_data["fingerprint"],
            }, []

        patch.setattr(
            closeout,
            "_atomic_rename_no_replace",
            lambda source, target: target.write_bytes(source.read_bytes()),
        )
        patch.setattr(closeout, "_lock_fact", stable_lock_fact)
        assert (
            quarantine_lock(lock, quarantine, lock_data["fingerprint"], digest)
            == "recovery_index_lock_present_after_quarantine"
        )


@pytest.mark.parametrize("platform", ["darwin", "linux", "win32"])
def test_atomic_no_replace_rejects_unsupported_platform_bindings(
    tmp_path: Path,
    monkeypatch,
    platform: str,
) -> None:
    """Every unsupported native binding blocks before moving a forensic lock."""
    library = SimpleNamespace(renameatx_np=None, renameat2=None)
    monkeypatch.setattr(closeout.sys, "platform", platform)
    monkeypatch.setattr(closeout.ctypes, "CDLL", lambda *_args, **_kwargs: library)

    with pytest.raises(OSError, match="atomic no-replace rename is unavailable"):
        atomic_rename_no_replace(tmp_path / "source", tmp_path / f"{platform}.lock")


def test_atomic_no_replace_reports_native_nonexist_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A native error other than target existence remains fail-closed."""
    class NativeOperation:
        argtypes = None
        restype = None

        def __call__(self, *_args) -> int:
            return -1

    monkeypatch.setattr(closeout.sys, "platform", "darwin")
    monkeypatch.setattr(
        closeout.ctypes,
        "CDLL",
        lambda *_args, **_kwargs: SimpleNamespace(renameatx_np=NativeOperation()),
    )
    monkeypatch.setattr(closeout.ctypes, "get_errno", lambda: errno.EIO)

    with pytest.raises(OSError, match="Errno 5") as error:
        atomic_rename_no_replace(tmp_path / "source", tmp_path / "target")

    assert error.value.errno == errno.EIO


def test_recovery_postconditions_and_path_checks_fail_closed_on_os_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Unreadable quarantines and path resolution faults remain visible blockers."""
    lock = tmp_path / "index.lock"
    quarantine = tmp_path / "quarantine.lock"
    lock.write_bytes(b"stale lock\n")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    lock_data = lock_fact(lock, digest)[0]
    request = _request(tmp_path)
    lock.unlink()

    with monkeypatch.context() as patch:
        patch.setattr(closeout, "_recovery_head_drift_gaps", lambda *_args: [])
        patch.setattr(closeout, "_lock_fact", lambda *_args: (_ for _ in ()).throw(OSError()))
        gaps = post_recovery_gaps(
            request,
            lock=lock_data,
            quarantine=quarantine,
            run=lambda *_args, **_kwargs: _completed(),
        )
    assert gaps == ["recovery_lock_quarantine_drifted"]

    with monkeypatch.context() as patch:
        patch.setattr(Path, "resolve", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
        assert inside(tmp_path / "path", tmp_path) is True


def test_recovery_report_plans_a_valid_residue_without_running_effect(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A verified dry run returns the recovery plan without touching the lock."""
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
        lambda *_args, **_kwargs: {"ok": True, "residue_exact": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        mutation,
        "recover_accepted_worktree_sync",
        lambda *_args, **_kwargs: pytest.fail("dry run reached recovery effect"),
    )

    report = mutation.closeout_worktree_sync_recovery_report(
        root=tmp_path,
        request=RecoveryMutationRequest(
            command="closeout_worktree_recovery",
            apply=False,
            authorized=False,
            expect_head=head,
        ),
        inputs=CloseoutWorktreeRecoveryInputs(
            failure_receipt=None,
            expect_failure_receipt_sha256="",
            expect_index_lock_sha256="",
            lock_quarantine=None,
        ),
    )

    assert (report["ok"], report["state"], report["required_gaps"]) == (True, "planned", [])
