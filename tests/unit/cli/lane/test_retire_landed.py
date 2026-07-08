from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos

if TYPE_CHECKING:
    from pathlib import Path


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def test_summary_preserves_retired_selected_after_apply(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    def post_apply_report(
        *,
        root: Path,
        branch: str | None = None,
        expect_head: str | None = None,
        apply: bool = False,
    ) -> dict[str, object]:
        assert root == repo
        assert branch == "work/landed"
        assert expect_head == "abc123"
        assert apply is True
        return {
            "ok": True,
            "state": "retired",
            "branch": "work/landed",
            "retired": {
                "branch": "work/landed",
                "path": str(tmp_path / "repo-work-landed"),
                "head": "abc123",
                "retire_ready": True,
                "required_gaps": [],
            },
            "lanes": [
                {
                    "branch": "work/other-landed",
                    "path": str(tmp_path / "repo-work-other"),
                    "head": "def456",
                    "retire_ready": True,
                    "required_gaps": [],
                }
            ],
            "mutation": {
                "expect_head": "abc123",
                "ref": "refs/heads/work/landed",
                "actor": "agent-a",
            },
            "required_gaps": [],
        }

    monkeypatch.setattr("ethos.surface.cli.lane.retire_landed_work_lanes", post_apply_report)

    payload = run_ethos(
        "lane",
        "retire-landed",
        "--branch",
        "work/landed",
        "--expect-head",
        "abc123",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire-landed"
    assert payload["ok"] is True
    assert payload["state"] == "retired"
    assert payload["summary"] == {
        "landed_lane_count": 2,
        "selected_branch": "work/landed",
        "selected_retire_ready": True,
        "selected_blockers": [],
    }
