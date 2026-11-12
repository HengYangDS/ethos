"""The Markdown list rule that `pre-commit` admits on staged index blobs."""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.runtime_scenarios import git_process

if TYPE_CHECKING:
    from pathlib import Path

_LOOSE = "# Notes\n\n- one\n\n- two\n"
_TIGHT = "# Notes\n\n- one\n- two\n"


@pytest.mark.parametrize(
    ("staged", "unstaged", "gap"),
    [
        ({"notes.md": _LOOSE}, {}, "notes.md:5"),
        ({"notes.md": _TIGHT}, {"notes.md": _LOOSE}, ""),
        ({".gitattributes": "notes.md linguist-vendored\n", "notes.md": _LOOSE}, {}, ""),
        ({"openspec/changes/archive/2026-09-01-old/notes.md": _LOOSE}, {}, ""),
    ],
    ids=["stray-blank", "worktree-only", "received", "archived-record"],
)
def test_pre_commit_admits_the_list_rule_on_staged_markdown(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    staged: dict[str, str],
    unstaged: dict[str, str],
    gap: str,
) -> None:
    """The staged bytes decide; received files and archived records keep their own bytes."""
    for name, text in staged.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text, encoding="utf-8")
    assert git_process(repo, "add", *staged).returncode == 0
    for name, text in unstaged.items():
        (repo / name).write_text(text, encoding="utf-8")
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == int(bool(gap))
    error = capsys.readouterr().err
    assert (f"pre_commit_markdown_spacing:{gap}" in error) if gap else not error
