"""A host-store installation is retired only when no recorded consumer still needs it."""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from filelock import Timeout

import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.adapters.repo.runtime.host_store import record_consumer
from ethos.adapters.repo.runtime.materialization.host_retention import retire_unused_installations
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from tests.support.runtime_scenarios import materialized_activation_case

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


@pytest.mark.parametrize(
    "left",
    [
        "nothing",
        "parent-file",
        "file",
        pytest.param(
            "link", marks=pytest.mark.skipif(os.name == "nt", reason="a link needs a privilege")
        ),
    ],
)
def test_a_consumer_whose_path_is_gone_keeps_its_record_and_installation(
    tmp_path: Path, left: str
) -> None:
    """A moved repository or an unmounted volume looks like a removed one, so nothing goes.

    A link that names nothing, or a file that Git left when it moved its directory, is kept as
    well and is not called absent: neither says what stood there. A file where the repository
    stood leaves nothing at the path, on every host.
    """
    store = _store(tmp_path)
    runtime = _installation(store, "d" * 64)
    repository = _consumer(tmp_path / "repository", current=runtime)
    record_consumer(runtime.parents[1], repository)
    shutil.rmtree(tmp_path / "repository")
    if left == "parent-file":
        repository.parent.write_text("", encoding="utf-8")
    elif left != "nothing":
        repository.parent.mkdir()
    if left == "link":
        repository.symlink_to(tmp_path / "unmounted/.git", target_is_directory=True)
    if left == "file":
        repository.write_text("gitdir: ../moved\n", encoding="utf-8")

    report = retire_unused_installations(store, in_use=_nothing_in_use)

    assert runtime.exists()
    assert report["retired"] == []
    gone = left in {"nothing", "parent-file"}
    assert report["absent"] == ([repository.as_posix()] if gone else [])
    assert list(installation_consumers(runtime.parents[1]).values()) == [repository]


@pytest.mark.skipif(
    os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="a directory that its owner cannot search needs POSIX modes and no superuser",
)
@pytest.mark.parametrize(
    "closed", ["..", "", "ethos", "ethos/runtime"], ids=["parent", "common", "state", "selectors"]
)
def test_a_consumer_whose_selectors_cannot_be_looked_at_keeps_its_installation(
    tmp_path: Path, closed: str
) -> None:
    """A place that may not be searched is unknown: never released, and never called absent."""
    store = _store(tmp_path)
    runtime = _installation(store, "9" * 64)
    repository = _consumer(tmp_path / "repository", current=runtime)
    record_consumer(runtime.parents[1], repository)
    place = repository.parent if closed == ".." else repository / closed
    place.chmod(0)
    try:
        report = retire_unused_installations(store, in_use=_nothing_in_use)
    finally:
        place.chmod(0o700)

    assert runtime.exists()
    assert (report["retired"], report["absent"]) == ([], [])
    assert list(installation_consumers(runtime.parents[1]).values()) == [repository]


def test_a_file_where_a_consumer_keeps_its_state_selects_nothing(tmp_path: Path) -> None:
    """A selector below a file is not there, on every host, so its installation is released."""
    store = _store(tmp_path)
    runtime = _installation(store, "7" * 64)
    repository = _consumer(tmp_path / "repository", current=runtime)
    record_consumer(runtime.parents[1], repository)
    shutil.rmtree(repository / "ethos")
    (repository / "ethos").write_text("", encoding="utf-8")

    report = retire_unused_installations(store, in_use=_nothing_in_use)

    assert report["retired"] == [runtime.parents[1].as_posix()]


def test_a_record_of_a_path_that_no_host_can_be_asked_about_ends_no_cleanup(
    tmp_path: Path,
) -> None:
    """A damaged record is unknown, so its installation stays and the next one is still read."""
    store = _store(tmp_path)
    kept, old = _installation(store, "5" * 64), _installation(store, "6" * 64)
    records = kept.parents[1] / "consumers"
    records.mkdir(mode=0o700)
    damaged = f"{tmp_path.as_posix()}/repository\0/.git\n"
    (records / "damaged").write_text(damaged, encoding="utf-8")
    record_consumer(old.parents[1], _consumer(tmp_path / "repository"))

    report = retire_unused_installations(store, in_use=_nothing_in_use)

    assert kept.exists()
    assert (report["retired"], report["absent"]) == ([old.parents[1].as_posix()], [])


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


def test_a_selection_in_progress_keeps_its_record_and_installation(tmp_path: Path) -> None:
    """A repository holding its selection lock may be about to name the installation it pinned."""
    store = _store(tmp_path)
    runtime = _installation(store, "1" * 64)
    other = _consumer(tmp_path / "other", current=runtime)
    pinning = _consumer(tmp_path / "pinning")
    for consumer in (other, pinning):
        record_consumer(runtime.parents[1], consumer)
    with FileLock(pinning / "ethos/runtime-selection.lock"):
        retire_unused_installations(store, in_use=_nothing_in_use)
    (pinning / "ethos/runtime/CURRENT").write_bytes(runtime_selection_bytes(pinning, runtime))
    shutil.rmtree(tmp_path / "other")

    report = retire_unused_installations(store, in_use=_nothing_in_use)

    assert runtime.exists()
    assert report["retained"] == [runtime.parents[1].as_posix()]


def test_retention_creates_nothing_in_a_consumer_without_ethos_state(tmp_path: Path) -> None:
    """A recorded repository without ETHOS state selects nothing and gets no lock from retention."""
    store = _store(tmp_path)
    runtime = _installation(store, "2" * 64)
    (tmp_path / "plain/.git").mkdir(parents=True)
    common = (tmp_path / "plain/.git").resolve()
    record_consumer(runtime.parents[1], common)

    report = retire_unused_installations(store, in_use=_nothing_in_use)

    assert not (common / "ethos").exists()
    assert report["retired"] == [runtime.parents[1].as_posix()]


def test_hook_install_holds_the_selection_lock_from_its_pins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retention sees the window between a pin and the selector write as a held lock."""
    repo, runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    lock = common / "ethos/runtime-selection.lock"
    held: list[bool] = []

    def pin(*_arguments: object, **_options: object) -> Path:
        probe = FileLock(lock)
        try:
            probe.acquire(blocking=False)
        except Timeout:
            held.append(True)
        else:
            probe.release()
            held.append(False)
        return runtime

    monkeypatch.setattr(runtime_materialization, "materialize_runtime", pin)

    install_hook_launchers(repo)

    assert held == [True]
    released = FileLock(lock)
    released.acquire(blocking=False)
    released.release()
