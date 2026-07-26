# fmt: off
from __future__ import annotations

import errno
import hashlib
from pathlib import Path

import ethos.adapters.mutation.closeout.core as closeout


def test_recovery_quarantine_keeps_source_when_atomic_no_replace_rejects_target_race(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A concurrent target creation cannot consume the only lock evidence."""
    lock = tmp_path / "index.lock"
    quarantine = tmp_path / "quarantine.lock"
    lock.write_bytes(b"stale lock\n")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    fingerprint = closeout._lock_fact(lock, digest)[0]["fingerprint"]  # noqa: SLF001

    def reject_target_race(_source: Path, target: Path) -> None:
        target.write_bytes(b"raced target\n")
        raise FileExistsError(errno.EEXIST, "target raced")

    monkeypatch.setattr(closeout, "_atomic_rename_no_replace", reject_target_race, raising=False)

    assert closeout._quarantine_lock(lock, quarantine, fingerprint, digest) == "recovery_lock_quarantine_exists"  # noqa: SLF001
    assert lock.read_bytes() == b"stale lock\n"
    assert quarantine.read_bytes() == b"raced target\n"


def test_atomic_no_replace_never_overwrites_existing_quarantine_target(tmp_path: Path) -> None:
    """The relocation primitive preserves both source and existing destination."""
    source = tmp_path / "index.lock"
    target = tmp_path / "quarantine.lock"
    source.write_bytes(b"source\n")
    target.write_bytes(b"existing\n")

    try:
        closeout._atomic_rename_no_replace(source, target)  # noqa: SLF001
    except FileExistsError:
        pass
    else:  # pragma: no cover - the assertion below gives the contract failure.
        raise AssertionError("atomic no-replace relocation overwrote an existing target")

    assert source.read_bytes() == b"source\n"
    assert target.read_bytes() == b"existing\n"


def test_recovery_quarantine_rejects_a_dangling_symlink_target(tmp_path: Path) -> None:
    """A dangling target is still an occupied forensic destination."""
    lock = tmp_path / "index.lock"
    quarantine = tmp_path / "quarantine.lock"
    lock.write_bytes(b"stale lock\n")
    quarantine.symlink_to(tmp_path / "missing-target")
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    lock_fact = closeout._lock_fact(lock, digest)[0]  # noqa: SLF001

    _fact, gaps = closeout._quarantine_fact(  # noqa: SLF001
        quarantine,
        root=tmp_path / "accepted",
        candidate_path=tmp_path / "candidate",
        lock=lock_fact,
    )

    assert gaps == ["recovery_lock_quarantine_exists"]
