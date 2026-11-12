"""The canonical text layout that `pre-commit` admits on staged index blobs."""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.runtime_scenarios import git_process

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("staged", "unstaged", "gap"),
    [
        ({".gitignore": "\nbuild/\n"}, {}, ".gitignore:1"),
        ({".gitignore": "build/\n\n\n*.log\n"}, {}, ".gitignore:3"),
        ({".gitignore": "build/\n"}, {".gitignore": "\nbuild/\n"}, ""),
        ({"notes.txt": "\n\nfree text\n"}, {}, ""),
    ],
    ids=["leading-blank", "doubled-blank", "worktree-only", "unowned-text"],
)
def test_pre_commit_admits_the_canonical_text_layout(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    staged: dict[str, str],
    unstaged: dict[str, str],
    gap: str,
) -> None:
    """The staged bytes of a canonical-text file decide; other text keeps its own owner."""
    for name, text in staged.items():
        (repo / name).write_text(text, encoding="utf-8")
    assert git_process(repo, "add", *staged).returncode == 0
    for name, text in unstaged.items():
        (repo / name).write_text(text, encoding="utf-8")
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == int(bool(gap))
    error = capsys.readouterr().err
    assert (f"pre_commit_text_layout:{gap}" in error) if gap else not error
