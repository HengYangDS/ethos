"""A host-store installation is retired only when no recorded consumer still needs it."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.runtime.host_store import record_consumer
from ethos.adapters.repo.runtime.materialization.host_retention import retire_unused_installations
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes

if TYPE_CHECKING:
    from pathlib import Path


def _installation(store: Path, digest: str) -> Path:
    """Lay out one pinned installation and return its runtime root."""
    runtime = store / digest[:16] / "runtime" / digest
    runtime.mkdir(parents=True)
    (store / digest[:16] / "OWNER").write_text(digest + "\n", encoding="utf-8")
    return runtime


def _consumer(root: Path, *, current: Path | None = None, rollback: Path | None = None) -> Path:
    """Create one repository common directory that selects or holds the given runtimes."""
    (root / ".git/ethos/runtime").mkdir(parents=True)
    common = (root / ".git").resolve()
    for name, runtime in (("CURRENT", current), ("ROLLBACK", rollback)):
        if runtime is not None:
            selector = common / "ethos/runtime" / name
            selector.write_bytes(runtime_selection_bytes(common, runtime.resolve()))
    return common


def _store(tmp_path: Path) -> Path:
    store = tmp_path / "host/ethos/installations"
    store.mkdir(parents=True)
    return store.resolve()


def _nothing_in_use() -> frozenset[Path]:
    return frozenset()


def test_an_installation_no_consumer_still_names_is_retired(tmp_path: Path) -> None:
    """A repository that moved on releases the installation it recorded."""
    store = _store(tmp_path)
    old = _installation(store, "a" * 64)
    selected = _installation(store, "b" * 64)
    repository = _consumer(tmp_path / "repository", current=selected)
    record_consumer(old.parents[1], repository)
    record_consumer(selected.parents[1], repository)

    report = retire_unused_installations(store, in_use=_nothing_in_use)

    assert not old.parents[1].exists()
    assert selected.exists()
    assert report["retired"] == [old.parents[1].as_posix()]


def test_a_rollback_supply_keeps_its_installation(tmp_path: Path) -> None:
    """The predecessor a repository can still roll back to is not reclaimed."""
    store = _store(tmp_path)
    rollback = _installation(store, "c" * 64)
    repository = _consumer(tmp_path / "repository", rollback=rollback)
    record_consumer(rollback.parents[1], repository)

    report = retire_unused_installations(store, in_use=_nothing_in_use)

    assert rollback.exists()
    assert report["retired"] == []


def test_a_record_whose_repository_is_gone_is_dropped(tmp_path: Path) -> None:
    """A removed repository no longer holds anything, so its record and installation go."""
    store = _store(tmp_path)
    runtime = _installation(store, "d" * 64)
    repository = _consumer(tmp_path / "repository", current=runtime)
    record_consumer(runtime.parents[1], repository)
    shutil.rmtree(tmp_path / "repository")

    report = retire_unused_installations(store, in_use=_nothing_in_use)

    assert report["retired"] == [runtime.parents[1].as_posix()]


def test_unrecorded_installations_are_never_retired(tmp_path: Path) -> None:
    """An installation pinned before consumers were recorded has unknown users and stays."""
    store = _store(tmp_path)
    legacy = _installation(store, "e" * 64)

    report = retire_unused_installations(store, in_use=_nothing_in_use)

    assert legacy.exists()
    assert (report["retired"], report["unrecorded"]) == ([], 1)


@pytest.mark.parametrize("reason", ["in_use", "unreadable_selector"])
def test_an_installation_whose_use_is_uncertain_is_retained(tmp_path: Path, reason: str) -> None:
    """A running process or a selector that cannot be read keeps the installation."""
    store = _store(tmp_path)
    runtime = _installation(store, "f" * 64)
    repository = _consumer(tmp_path / "repository")
    record_consumer(runtime.parents[1], repository)

    def in_use() -> frozenset[Path]:
        return frozenset({runtime / "python/bin/python"}) if reason == "in_use" else frozenset()

    if reason != "in_use":
        (repository / "ethos/runtime/CURRENT").write_bytes(b"not a selector\n")

    report = retire_unused_installations(store, in_use=in_use)

    assert runtime.exists()
    assert report["retired"] == []
