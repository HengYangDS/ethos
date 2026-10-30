"""A runtime payload inventory reuses digests only for files whose exact state is unchanged."""

from __future__ import annotations

import hashlib
import os
import time
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.inventory_memo as inventory_memo
import ethos.adapters.repo.runtime.manifest as manifest
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory

if TYPE_CHECKING:
    from pathlib import Path

DIGEST = "a" * 64


class _Hashes:
    """Count the payload entries the inventory actually hashes."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        sha256 = hashlib.sha256

        def counted(*args: bytes) -> object:
            self.count += 1
            return sha256(*args)

        monkeypatch.setattr(manifest, "hashlib", SimpleNamespace(sha256=counted))


@pytest.fixture
def memo_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "cache"
    monkeypatch.setattr(inventory_memo, "_memo_directory", lambda: directory)
    monkeypatch.setattr(inventory_memo, "_MIN_FILES", 0)
    monkeypatch.setattr(inventory_memo, "_RACY_NS", 0)
    return directory


def _payload(tmp_path: Path, name: str = DIGEST) -> Path:
    runtime = tmp_path / "store" / name
    (runtime / "python/lib").mkdir(parents=True)
    (runtime / "python/lib/module.py").write_text("VALUE = 1\n")
    (runtime / "python/lib/other.py").write_text("OTHER = 2\n")
    (runtime / "python/bin").mkdir()
    (runtime / "python/bin/python").write_bytes(b"#!python\n")
    return runtime


def _await_later_ctime(directory: Path, recorded: int) -> None:
    """Wait until this filesystem stamps a later ctime, as the product's racy window ensures.

    The fixture records files at once, so a write in the same timestamp tick, as on Linux's coarse
    clock, would keep the recorded ctime.
    """
    probe = directory / "ctime-probe"
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        probe.touch()
        if probe.stat().st_ctime_ns > recorded:
            return
        time.sleep(0.001)
    pytest.fail("the filesystem stamped no later ctime within 5 seconds")


@pytest.mark.usefixtures("memo_directory")
def test_repeated_inventory_of_an_unchanged_payload_hashes_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second selection of the same sealed payload reuses every recorded digest."""
    runtime = _payload(tmp_path)
    hashes = _Hashes(monkeypatch)

    first = runtime_file_inventory(runtime)
    assert hashes.count == 3
    assert runtime_file_inventory(runtime) == first
    assert hashes.count == 3


@pytest.mark.usefixtures("memo_directory")
def test_changed_bytes_under_a_restored_mtime_are_hashed_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A write moves ctime, which restoring the mtime cannot undo, so damage stays visible."""
    runtime = _payload(tmp_path)
    first = runtime_file_inventory(runtime)
    module = runtime / "python/lib/module.py"
    times = module.stat()
    _await_later_ctime(tmp_path, times.st_ctime_ns)
    module.write_text("VALUE = 9\n")
    os.utime(module, ns=(times.st_atime_ns, times.st_mtime_ns))
    hashes = _Hashes(monkeypatch)

    second = runtime_file_inventory(runtime)

    assert hashes.count == 1
    assert second["python/lib/module.py"] != first["python/lib/module.py"]
    assert {path: value for path, value in second.items() if path != "python/lib/module.py"} == {
        path: value for path, value in first.items() if path != "python/lib/module.py"
    }


@pytest.mark.usefixtures("memo_directory")
def test_a_memoized_payload_still_refuses_added_bytecode(tmp_path: Path) -> None:
    """The memo replaces hashing only; every entry is still enumerated and judged."""
    runtime = _payload(tmp_path)
    runtime_file_inventory(runtime)
    (runtime / "python/lib/__pycache__").mkdir()
    (runtime / "python/lib/__pycache__/module.cpython-314.pyc").write_bytes(b"\0")

    with pytest.raises(ValueError, match="hook_runtime_payload_mismatch"):
        runtime_file_inventory(runtime)


@pytest.mark.parametrize("memo", ["malformed", "foreign"])
def test_an_unusable_memo_only_costs_its_hashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, memo_directory: Path, memo: str
) -> None:
    """A memo that is not this payload's own record is ignored, never trusted."""
    runtime = _payload(tmp_path)
    expected = runtime_file_inventory(runtime)
    (recorded,) = memo_directory.glob("*.json")
    if memo == "malformed":
        recorded.write_text("{")
    else:
        runtime_file_inventory(_payload(tmp_path / "other"))
        (foreign,) = (path for path in memo_directory.glob("*.json") if path != recorded)
        recorded.write_bytes(foreign.read_bytes())
    hashes = _Hashes(monkeypatch)

    assert runtime_file_inventory(runtime) == expected
    assert hashes.count == 3


@pytest.mark.usefixtures("memo_directory")
def test_recently_written_files_are_not_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file written within one timestamp tick of its hash could change unseen, so it rehashes."""
    monkeypatch.setattr(inventory_memo, "_RACY_NS", 3_600 * 10**9)
    runtime = _payload(tmp_path)
    runtime_file_inventory(runtime)
    hashes = _Hashes(monkeypatch)

    runtime_file_inventory(runtime)

    assert hashes.count == 3


@pytest.mark.parametrize("payload", ["small", "staging", "unsupported"])
def test_payloads_that_a_memo_cannot_serve_are_hashed_without_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, memo_directory: Path, payload: str
) -> None:
    """Small payloads, staging roots and Windows hash every file and record nothing."""
    if payload == "small":
        monkeypatch.setattr(inventory_memo, "_MIN_FILES", 256)
    if payload == "unsupported":
        monkeypatch.setattr(inventory_memo, "_SUPPORTED", False)
    runtime = _payload(tmp_path, ".staging-runtime" if payload == "staging" else DIGEST)
    runtime_file_inventory(runtime)
    hashes = _Hashes(monkeypatch)

    runtime_file_inventory(runtime)

    assert hashes.count == 3
    assert not memo_directory.exists() or not any(memo_directory.iterdir())


def test_retained_memos_are_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, memo_directory: Path
) -> None:
    """The cache keeps only the most recently written memos."""
    monkeypatch.setattr(inventory_memo, "_RETAINED", 2)
    for index in range(4):
        runtime_file_inventory(_payload(tmp_path / str(index), f"{index:064x}"))

    assert len(list(memo_directory.glob("*.json"))) == 2


@pytest.mark.parametrize("declared", ["absolute", "relative"])
def test_the_memo_lives_beside_the_host_runtime_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, declared: str
) -> None:
    """The host store's own root holds the memo, so an isolated host isolates its memos too."""
    monkeypatch.setattr(inventory_memo, "_MIN_FILES", 0)
    monkeypatch.setattr(inventory_memo, "_RACY_NS", 0)
    monkeypatch.chdir(tmp_path)
    host = tmp_path / "host"
    monkeypatch.setenv("XDG_DATA_HOME", str(host) if declared == "absolute" else "relative-host")
    runtime = _payload(tmp_path)

    expected = runtime_file_inventory(runtime)

    memos = list((host / "ethos/runtime-inventory").glob("*.json"))
    assert len(memos) == (1 if declared == "absolute" else 0)
    assert not (tmp_path / "relative-host").exists()
    assert runtime_file_inventory(runtime) == expected
