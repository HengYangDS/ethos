# ruff: noqa: TC003
"""Coverage-closure v2: config + lane refresh/retire pure-function branches."""

from __future__ import annotations

import subprocess
from pathlib import Path

import ethos.adapters.mutation.lane_lifecycle.refresh as lanes_refresh
import ethos.adapters.mutation.lane_retirement.landed.core as landed_retirement
from ethos.adapters import config

# --- adapters/config.py ------------------------------------------------------


def test_code_size_policy_empty_when_quality_not_a_table(tmp_path: Path) -> None:
    # A [quality] key that is not a table yields {} (line 29, now reachable after the
    # redundant double-isinstance guard was simplified).
    ethos = tmp_path / ".ethos"
    ethos.mkdir()
    (ethos / "rules.toml").write_text('quality = "not-a-table"\n', encoding="utf-8")
    assert config.code_size_policy(tmp_path) == {}


def test_code_size_policy_reads_code_size_table(tmp_path: Path) -> None:
    ethos = tmp_path / ".ethos"
    ethos.mkdir()
    (ethos / "rules.toml").write_text("[quality.code_size]\nmax_lines = 400\n", encoding="utf-8")
    assert config.code_size_policy(tmp_path) == {"max_lines": 400}


def test_code_size_policy_empty_when_code_size_not_a_table(tmp_path: Path) -> None:
    ethos = tmp_path / ".ethos"
    ethos.mkdir()
    (ethos / "rules.toml").write_text('[quality]\ncode_size = "nope"\n', encoding="utf-8")
    assert config.code_size_policy(tmp_path) == {}


# --- adapters/mutation/lane_lifecycle/refresh.py --------------------------------------


def test_apply_gaps_expect_head_mismatch() -> None:
    # apply with a mismatched expect_head yields expect_head_mismatch (lines 119-120).
    gaps = lanes_refresh._apply_gaps(
        apply=True, authorized=True, expect_head="aaa", current_head="bbb"
    )
    assert gaps == ["expect_head_mismatch"]


def test_candidate_worktree_gaps_branch_missing() -> None:
    # A candidate whose branch does not exist (line 126).
    candidate = {"exists": False, "worktree_exists": False}
    assert lanes_refresh._candidate_worktree_gaps(candidate, "/tmp/x") == [
        "candidate_branch_missing"
    ]


def test_candidate_worktree_gaps_worktree_missing() -> None:
    # A candidate branch present but no worktree (line 128).
    candidate = {"exists": True, "worktree_exists": False}
    assert lanes_refresh._candidate_worktree_gaps(candidate, "/tmp/x") == [
        "candidate_worktree_missing"
    ]


def test_candidate_worktree_gaps_dirty(tmp_path: Path) -> None:
    # A candidate worktree with an uncommitted change is dirty (line 130).
    def _g(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=T", "-c", "user.email=t@e.co", *args],
            cwd=tmp_path,
            check=True,
            text=True,
            capture_output=True,
        )

    _g("init", "-b", "main")
    (tmp_path / "a.txt").write_text("1", encoding="utf-8")
    _g("add", ".")
    _g("commit", "-m", "c1")
    (tmp_path / "a.txt").write_text("2", encoding="utf-8")  # uncommitted change
    candidate = {"exists": True, "worktree_exists": True}
    assert lanes_refresh._candidate_worktree_gaps(candidate, str(tmp_path)) == [
        "candidate_worktree_dirty"
    ]


def test_candidate_report_includes_stderr_when_present() -> None:
    # A non-empty stderr is attached to the report (line 145).
    context = {
        "ok": False,
        "state": "blocked",
        "branch": "candidate/dev",
        "head": "h",
        "previous_head": "p",
        "path": "/tmp/x",
        "required_gaps": ["x"],
    }
    report = lanes_refresh._candidate_report(context, stderr="boom")
    assert report["stderr"] == "boom"


# --- adapters/mutation/lane_retirement/landed/core.py ------------------------


def test_has_changed_paths_true_outside_repo(tmp_path: Path) -> None:
    # `git status` fails outside a repo, so the helper conservatively returns True
    # (lines 278-279).
    assert landed_retirement.has_changed_paths(tmp_path) is True
