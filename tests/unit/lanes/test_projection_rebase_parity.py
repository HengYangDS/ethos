# These boundary tests preserve patched subprocess signatures.

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.mutation.lane_lifecycle.projection_rebase.core as projection_rebase
from tests.support.subprocesses import completed as cp

if TYPE_CHECKING:
    from pathlib import Path


def test_parity_projection_reader_rejects_unmerged_and_write_failures(
    monkeypatch, tmp_path: Path
) -> None:
    def run_git(_root: Path, *args: str, check: bool = True):
        del check
        if args[:1] == ("diff",):
            return cp(returncode=1)
        return cp(returncode=1)

    monkeypatch.setattr(projection_rebase, "run_git", run_git)
    assert projection_rebase.resolve_projection_only_rebase_conflict(tmp_path)["ok"] is False

    for failing_action in ("checkout", "add"):

        def run_git(
            _root: Path,
            *args: str,
            check: bool = True,
            _failing_action: str = failing_action,
        ):
            del check
            if args[:1] == ("diff",):
                return cp(stdout="evidence/parity/generic-shadow.json\n")
            return cp(returncode=1) if args[:1] == (_failing_action,) else cp(returncode=0)

        monkeypatch.setattr(projection_rebase, "run_git", run_git)
        assert projection_rebase.resolve_projection_only_rebase_conflict(tmp_path) == {
            "ok": False,
            "paths": ["evidence/parity/generic-shadow.json"],
            "gaps": [],
            "next_actions": [],
        }


def test_projection_rebase_skips_empty_patch_after_parity_resolution(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, ...]] = []
    diff_calls = 0

    def run_git(_root: Path, *args: str, check: bool = True):
        nonlocal diff_calls
        del check
        calls.append(args)
        if args[:3] == ("diff", "--name-only", "--diff-filter=U"):
            diff_calls += 1
            return cp(stdout="evidence/parity/generic-shadow.json\n" if diff_calls == 1 else "")
        if args[:1] in {("checkout",), ("add",)}:
            return cp(returncode=0)
        if args == ("-c", "core.editor=true", "rebase", "--continue"):
            return cp(returncode=1, stderr="No changes -- Patch already applied.")
        if args == ("rebase", "--skip"):
            return cp(returncode=0)
        return cp(returncode=1, stderr="unexpected git call")

    monkeypatch.setattr(projection_rebase, "run_git", run_git)
    resolved = projection_rebase.resolve_projection_rebase(
        tmp_path, cp(returncode=1, stderr="projection conflict")
    )

    assert resolved["ok"] is True
    assert resolved["paths"] == ["evidence/parity/generic-shadow.json"]
    assert ("rebase", "--skip") in calls


def test_projection_rebase_reports_failed_continue_for_caller_abort(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, ...]] = []
    diff_calls = 0

    def run_git(_root: Path, *args: str, check: bool = True):
        nonlocal diff_calls
        del check
        calls.append(args)
        if args[:3] == ("diff", "--name-only", "--diff-filter=U"):
            diff_calls += 1
            return cp(stdout="evidence/parity/generic-shadow.json\n" if diff_calls == 1 else "")
        if args[:1] in {("checkout",), ("add",)}:
            return cp(returncode=0)
        if args == ("-c", "core.editor=true", "rebase", "--continue"):
            return cp(returncode=1, stderr="continue failed")
        return cp(returncode=1, stderr="unexpected git call")

    monkeypatch.setattr(projection_rebase, "run_git", run_git)
    resolved = projection_rebase.resolve_projection_rebase(
        tmp_path, cp(returncode=1, stderr="projection conflict")
    )

    assert resolved["ok"] is False
    assert resolved["stderr"] == "continue failed"
    assert ("-c", "core.editor=true", "rebase", "--continue") in calls


def test_projection_rebase_bounded_recovery_fails_closed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(projection_rebase, "MAX_PROJECTION_REBASE_STEPS", 0)

    assert projection_rebase.resolve_projection_rebase(tmp_path, cp(returncode=1)) == {
        "ok": False,
        "paths": [],
        "gaps": [],
        "next_actions": [],
        "stderr": "projection rebase recovery exceeded bounded step limit",
    }


def test_projection_rebase_preserves_valid_staged_parity_then_replaces_wrong_adopter(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, ...]] = []
    diff_calls = 0

    def valid_stage(_root: Path, *args: str, check: bool = True):
        nonlocal diff_calls
        del check
        calls.append(args)
        if args[:3] == ("diff", "--name-only", "--diff-filter=U"):
            diff_calls += 1
            return cp(stdout="evidence/parity/generic-shadow.json\n" if diff_calls == 1 else "")
        if args == ("show", ":0:evidence/parity/generic-shadow.json"):
            return cp(stdout='{"schema_version":1,"adopter":"generic"}')
        if args == ("-c", "core.editor=true", "rebase", "--continue"):
            return cp(returncode=0)
        return cp(returncode=1, stderr="unexpected git call")

    monkeypatch.setattr(projection_rebase, "run_git", valid_stage)
    resolved = projection_rebase.resolve_projection_rebase(
        tmp_path, cp(returncode=1, stderr="rerere applied prior resolution")
    )
    assert resolved["ok"] is True
    assert ("show", ":0:evidence/parity/generic-shadow.json") in calls
    assert not any(call[:1] == ("checkout",) for call in calls)

    calls.clear()
    diff_calls = 0

    def wrong_stage(_root: Path, *args: str, check: bool = True):
        nonlocal diff_calls
        del check
        calls.append(args)
        if args[:3] == ("diff", "--name-only", "--diff-filter=U"):
            diff_calls += 1
            return cp(stdout="evidence/parity/generic-shadow.json\n" if diff_calls == 1 else "")
        if args == ("show", ":0:evidence/parity/generic-shadow.json"):
            return cp(stdout='{"schema_version":1,"adopter":"other"}')
        if args[:1] in {("checkout",), ("add",)}:
            return cp(returncode=0)
        if args == ("-c", "core.editor=true", "rebase", "--continue"):
            return cp(returncode=0)
        return cp(returncode=1, stderr="unexpected git call")

    monkeypatch.setattr(projection_rebase, "run_git", wrong_stage)
    resolved = projection_rebase.resolve_projection_rebase(
        tmp_path, cp(returncode=1, stderr="staged payload mismatch")
    )
    assert resolved["ok"] is True
    assert ("checkout", "--ours", "--", "evidence/parity/generic-shadow.json") in calls
