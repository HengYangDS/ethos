"""Return an archive whose proof failed to its exact pre-archive head."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
import ethos.adapters.mutation.lane_lifecycle.archive.compensation as compensation
from ethos.adapters.repo.git_effect_attestation import recover_plan
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.openspec_lifecycle import completed_lifecycle

if TYPE_CHECKING:
    from pathlib import Path

    from tests.support.openspec_lifecycle import OpenSpecLifecycle


def _compensate(lifecycle: OpenSpecLifecycle, expect_head: str) -> dict[str, object]:
    return archive.archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=expect_head,
        apply=True,
        compensate=True,
    )


def test_an_archive_returns_to_its_pre_archive_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    source = lifecycle.head
    archived = str(lifecycle.archive()["head"])
    command = ("lane", "archive-change", "--change", "fixture-change", "--expect-head", archived)

    preview = run_ethos(*command, "--compensate", "--json", cwd=lifecycle.worktree)["data"]
    assert (preview["state"], preview["previous_head"]) == ("ready_to_compensate", source)
    assert lifecycle.head == archived

    applied = run_ethos(*command, "--compensate", "--apply", "--json", cwd=lifecycle.worktree)
    assert (applied["data"]["state"], applied["data"]["compensation_state"]) == (
        "compensated",
        "completed",
    )
    assert lifecycle.head == source
    assert lifecycle.active.is_dir()
    assert not git(lifecycle.worktree, "status", "--short")
    ref = f"refs/heads/{lifecycle.branch}"
    operation = "openspec.archive.compensate"
    assert recover_plan(lifecycle.worktree, operation=operation, desired=source, ref_name=ref)
    assert lifecycle.archive()["head"] != source


@pytest.mark.parametrize("fault", ["unarchived", "landed", "head", "dirty", "actor"])
def test_compensation_refuses_an_inexact_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    head = lifecycle.head if fault == "unarchived" else str(lifecycle.archive()["head"])
    gap = {
        "unarchived": "openspec_archive_compensation_unavailable:fixture-change",
        "landed": "openspec_archive_landed:fixture-change",
        "head": "expect_head_mismatch",
        "dirty": "work_lane_dirty",
        "actor": "lease_actor_mismatch",
    }[fault]
    if fault == "landed":
        candidate = git(lifecycle.candidate, "branch", "--show-current")
        git(lifecycle.candidate, "merge", "--ff-only", head)
        assert git(lifecycle.candidate, "rev-parse", candidate) == head
    if fault == "dirty":
        (lifecycle.worktree / "untracked.md").write_text("Unrelated work.\n", encoding="utf-8")
    if fault == "actor":
        monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    observe = ("show-ref",), ("status", "--porcelain")
    before = [git(lifecycle.worktree, *args) for args in observe]

    report = _compensate(lifecycle, "f" * 40 if fault == "head" else head)

    assert (report["state"], report["required_gaps"]) == ("blocked", [gap])
    assert report["effect_state"] == "zero_effect"
    assert [git(lifecycle.worktree, *args) for args in observe] == before


def test_an_interrupted_compensation_finishes_its_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    source = lifecycle.head
    archived = str(lifecycle.archive()["head"])
    with monkeypatch.context() as interrupted:
        interrupted.setattr(
            compensation, "compensate_git_worktree", Mock(side_effect=OSError("interrupted"))
        )
        stopped = _compensate(lifecycle, archived)
    assert (stopped["state"], stopped["effect_state"]) == ("repair_required", "committed")
    assert stopped["next_action"] == (
        f"ethos lane archive-change --change fixture-change --expect-head {archived} "
        "--compensate --apply --json"
    )
    assert lifecycle.head == source
    assert git(lifecycle.worktree, "status", "--short")

    resumed = _compensate(lifecycle, archived)

    assert (resumed["state"], resumed["head"]) == ("compensated", source)
    assert lifecycle.active.is_dir()
    assert not git(lifecycle.worktree, "status", "--short")
