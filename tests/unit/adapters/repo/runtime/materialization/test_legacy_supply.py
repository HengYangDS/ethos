"""Installations pinned before consumers were recorded retire only through a previewed plan."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.adapters.repo.runtime.host_store import record_consumer
from ethos.adapters.repo.runtime.materialization.host_retention import legacy_supply
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes

if TYPE_CHECKING:
    from pathlib import Path

DAY = 24 * 3600


def _installation(store: Path, digest: str, *, age: float = 30 * DAY) -> Path:
    """Lay out one unrecorded installation last changed ``age`` seconds ago."""
    installation = store / digest[:16]
    runtime = installation / "runtime" / digest
    runtime.mkdir(parents=True)
    (runtime / "payload").write_bytes(b"x" * 1024)
    (installation / "OWNER").write_text(digest + "\n", encoding="utf-8")
    stamp = time.time() - age
    os.utime(installation, (stamp, stamp))
    return runtime


def _repository(root: Path, *, current: Path | None = None, rollback: Path | None = None) -> Path:
    (root / ".git/ethos/runtime").mkdir(parents=True)
    common = (root / ".git").resolve()
    for name, runtime in (("CURRENT", current), ("ROLLBACK", rollback)):
        if runtime is not None:
            (common / "ethos/runtime" / name).write_bytes(runtime_selection_bytes(common, runtime))
    return common


def _nothing_in_use() -> frozenset[Path]:
    return frozenset()


def _case(tmp_path: Path):
    store = (tmp_path / "host/ethos/installations").resolve()
    store.mkdir(parents=True)
    selected = _installation(store, "1" * 64)
    held = _installation(store, "2" * 64)
    running = _installation(store, "3" * 64)
    recent = _installation(store, "4" * 64, age=3600)
    unused = _installation(store, "5" * 64)
    recorded = _installation(store, "6" * 64)
    consumers = (
        _repository(tmp_path / "one", current=selected),
        _repository(tmp_path / "two", rollback=held),
    )
    record_consumer(recorded.parents[1], consumers[0])
    return (
        store,
        consumers,
        {
            "selected": selected,
            "held": held,
            "running": running,
            "recent": recent,
            "unused": unused,
            "recorded": recorded,
        },
    )


def test_the_preview_keeps_every_installation_still_used_and_removes_nothing(
    tmp_path: Path,
) -> None:
    """Only an old installation that no scanned repository or process uses is retirable."""
    store, consumers, runtimes = _case(tmp_path)

    plan = legacy_supply(
        store,
        consumers=consumers,
        in_use=lambda: frozenset({runtimes["running"] / "payload"}),
        grace_seconds=7 * DAY,
        apply=False,
    )

    assert [row["installation"] for row in plan["retirable"]] == [
        runtimes["unused"].parents[1].as_posix()
    ]
    assert plan["retirable"][0]["bytes"] >= 1024
    assert {row["reason"] for row in plan["kept"]} == {"named", "in_use", "recent"}
    assert all(runtime.exists() for runtime in runtimes.values())
    assert plan["retired"] == []


def test_an_approved_plan_retires_the_unused_and_records_the_named(tmp_path: Path) -> None:
    """Apply under the previewed plan reclaims exactly it and adopts every named installation."""
    store, consumers, runtimes = _case(tmp_path)
    preview = legacy_supply(
        store, consumers=consumers, in_use=_nothing_in_use, grace_seconds=7 * DAY, apply=False
    )

    applied = legacy_supply(
        store,
        consumers=consumers,
        in_use=_nothing_in_use,
        grace_seconds=7 * DAY,
        apply=True,
        expected_plan=str(preview["plan_digest"]),
    )

    assert applied["retired"] == [row["installation"] for row in preview["retirable"]]
    assert not runtimes["unused"].exists()
    assert not runtimes["running"].exists()
    for name in ("selected", "held", "recent", "recorded"):
        assert runtimes[name].exists()
    assert installation_consumers(runtimes["selected"].parents[1]) is not None
    assert installation_consumers(runtimes["held"].parents[1]) is not None


def test_a_plan_that_changed_since_its_preview_removes_nothing(tmp_path: Path) -> None:
    """A stale plan digest refuses the apply, so a preview never authorizes other removals."""
    store, consumers, runtimes = _case(tmp_path)

    with pytest.raises(ValueError, match="host_store_plan_changed"):
        legacy_supply(
            store,
            consumers=consumers,
            in_use=_nothing_in_use,
            grace_seconds=7 * DAY,
            apply=True,
            expected_plan="0" * 64,
        )

    assert all(runtime.exists() for runtime in runtimes.values())
