"""A consumer whose repository path is absent is released only through a previewed plan."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.materialization.host_retention as host_retention
from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.adapters.repo.runtime.host_store import record_consumer
from ethos.adapters.repo.runtime.materialization.host_retention import absent_consumers
from ethos.adapters.repo.runtime.materialization.host_retention import path_absent
from ethos.adapters.repo.runtime.materialization.host_retention import retire_unused_installations
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from tests.support.closed_directory import NEEDS_A_CLOSED_DIRECTORY

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class _Host:
    """A fixture host store, and repositories beside it that select its installations."""

    def __init__(self, base: Path) -> None:
        self.base = base.resolve()
        self.store = self.base / "host/ethos/installations"
        self.store.mkdir(parents=True)

    def installation(self, digit: str, *recorded: Path) -> Path:
        """Lay out one installation of 1 KiB that the given common directories recorded."""
        installation = self.store / (digit * 16)
        payload = installation / "runtime" / (digit * 64) / "payload"
        payload.parent.mkdir(parents=True)
        payload.write_bytes(b"x" * 1024)
        for common in recorded:
            record_consumer(installation, common)
        return installation

    def repository(self, name: str, selected: Path | None = None, current: bytes = b"") -> Path:
        """Make one common directory; it selects an installation, or holds the bytes given."""
        common = self.base / name / ".git"
        (common / "ethos/runtime").mkdir(parents=True)
        if selected is not None:
            current = runtime_selection_bytes(common, next((selected / "runtime").iterdir()))
        if current:
            (common / "ethos/runtime/CURRENT").write_bytes(current)
        return common

    def gone(self, name: str = "gone") -> Path:
        return self.base / name / ".git"

    def listing(self) -> list[Path]:
        return sorted(self.store.glob("*/**/*"))

    def plan(self, *scanned: Path, apply: bool = False, expect: str | None = None) -> dict:
        return absent_consumers(self.store, consumers=scanned, apply=apply, expected_plan=expect)


@pytest.fixture
def closed(tmp_path: Path) -> Iterator[Path]:
    """A directory that may not be searched, opened again when the test ends."""
    directory = tmp_path / "closed"
    (directory / "inside").mkdir(parents=True)
    directory.chmod(0)
    yield directory
    directory.chmod(0o700)


@pytest.mark.parametrize("relative", ["none/.git", "file/.git", "file"])
def test_only_a_missing_entry_is_absence(tmp_path: Path, relative: str) -> None:
    """No entry, also below a regular file, is absence; an entry of any kind is presence."""
    (tmp_path / "file").write_text("", encoding="utf-8")

    assert path_absent(tmp_path / relative) is (relative != "file")


@NEEDS_A_CLOSED_DIRECTORY
def test_a_place_the_host_cannot_look_at_is_unknown_and_is_never_planned(
    tmp_path: Path, closed: Path
) -> None:
    """A consumer below a directory without search permission is neither absent nor released."""
    host = _Host(tmp_path / "case")
    installation = host.installation("1")
    records = installation / "consumers"
    records.mkdir()
    for name, consumer in (("known", closed / "inside/.git"), ("lost", closed / "none/.git")):
        (records / name).write_text(consumer.as_posix() + "\n", encoding="utf-8")

    assert path_absent(closed / "inside/.git") is None
    assert path_absent(closed / "none/.git") is None
    assert host.plan()["absent"] == []
    assert absent_consumers(tmp_path / "no-store", consumers=(), apply=False)["absent"] == []
    with pytest.raises(ValueError, match="Permission denied"):
        absent_consumers(closed / "inside", consumers=(), apply=False)
    with pytest.raises(ValueError, match="host_store_plan_changed"):
        host.plan(apply=True, expect="0" * 64)
    assert len(installation_consumers(installation) or {}) == 2


def test_the_preview_names_exactly_the_absent_records_and_changes_nothing(tmp_path: Path) -> None:
    """A live consumer's record is not planned, and the preview leaves every file as it was."""
    host = _Host(tmp_path)
    live = host.repository("live")
    only = host.installation("1", host.gone())
    mixed = host.installation("2", host.gone(), live)
    host.installation("3", live)
    host.installation("4")
    before = host.listing()

    plan = host.plan(live)

    assert [(row["installation"], row["consumer"]) for row in plan["absent"]] == [
        (only.as_posix(), host.gone().as_posix()),
        (mixed.as_posix(), host.gone().as_posix()),
    ]
    assert all(row["bytes"] >= 1024 and row["named_by"] == [] for row in plan["absent"])
    assert plan["held_bytes"] == sum(row["bytes"] for row in plan["absent"])
    assert (plan["released"], plan["kept"], host.listing()) == ([], [], before)
    assert host.plan(live)["plan_digest"] == plan["plan_digest"]


def test_a_scanned_selection_that_cannot_be_read_keeps_the_records_out(tmp_path: Path) -> None:
    """A repository that may name the installation, and cannot say, holds its records."""
    host = _Host(tmp_path)
    installation = host.installation("1", host.gone())
    unreadable = host.repository("unreadable", current=b"not a selection\n\n\n")

    plan = host.plan(unreadable)

    assert plan["absent"] == []
    assert plan["kept"] == [{"installation": installation.as_posix(), "reason": "uncertain"}]


def test_an_applied_plan_releases_the_records_and_removes_no_installation(tmp_path: Path) -> None:
    """A moved repository is recorded first; the next cleanup then retires only what is free."""
    host = _Host(tmp_path)
    freed = host.installation("1", host.gone())
    moved = host.installation("2", host.gone("before"))
    after = host.repository("after", selected=moved)
    preview = host.plan(after)
    assert [row["named_by"] for row in preview["absent"]] == [[], [after.as_posix()]]

    applied = host.plan(after, apply=True, expect=str(preview["plan_digest"]))

    assert applied["released"] == [host.gone().as_posix(), host.gone("before").as_posix()]
    assert (applied["absent"], applied["not_released"]) == (preview["absent"], [])
    assert freed.is_dir()
    assert installation_consumers(freed) == {}
    assert list((installation_consumers(moved) or {}).values()) == [after]
    cleanup = retire_unused_installations(host.store, in_use=frozenset)
    assert (cleanup["retired"], cleanup["retained"]) == ([freed.as_posix()], [moved.as_posix()])


def test_a_changed_plan_releases_nothing(tmp_path: Path) -> None:
    """A consumer that came back after the preview changes the plan, and its record stays."""
    host = _Host(tmp_path)
    installation = host.installation("1", host.gone())
    preview = host.plan()
    host.repository("gone")

    with pytest.raises(ValueError, match="host_store_plan_changed"):
        host.plan(apply=True, expect=str(preview["plan_digest"]))

    assert list((installation_consumers(installation) or {}).values()) == [host.gone()]


@pytest.mark.parametrize("reason", ["present", "unknown"])
def test_a_path_not_read_absent_again_at_the_apply_keeps_its_record_and_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    """Each record's path is read again before its unlink; one not released says why."""
    host = _Host(tmp_path)
    installation = host.installation("1", host.gone())
    preview = host.plan()
    (planned,) = preview["absent"]
    answers = iter((True, False if reason == "present" else None))
    monkeypatch.setattr(host_retention, "path_absent", lambda _path: next(answers))

    applied = host.plan(apply=True, expect=str(preview["plan_digest"]))

    named = {key: planned[key] for key in ("installation", "record", "consumer")}
    assert (applied["released"], applied["not_released"]) == ([], [named | {"reason": reason}])
    assert list((installation_consumers(installation) or {}).values()) == [host.gone()]


def test_a_failure_of_another_kind_in_the_middle_keeps_what_was_released(tmp_path: Path) -> None:
    """A naming repository's record that cannot be decoded stops the release, which is named."""
    host = _Host(tmp_path)
    host.installation("1", host.gone())
    moved = host.installation("2", host.gone("before"))
    after = host.repository("after", selected=moved)
    record_consumer(moved, after)
    records = installation_consumers(moved) or {}
    next(record for record, common in records.items() if common == after).write_bytes(b"\xff\n")
    preview = host.plan(after)

    applied = host.plan(after, apply=True, expect=str(preview["plan_digest"]))

    assert "utf-8" in applied["failed"]
    assert applied["released"] == [host.gone().as_posix()]
    assert len(installation_consumers(moved) or {}) == 2
