"""The patch workspace shows a patch's effect, or it refuses."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_workspace as owner
from ethos.adapters.repo.git_patch import unified_patch_changes
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_MOVE_AND_REFILL = (
    "diff --git a/a.txt b/b.txt\nsimilarity index 100%\nrename from a.txt\nrename to b.txt\n"
    "diff --git a/a.txt b/a.txt\nnew file mode 100644\n--- /dev/null\n+++ b/a.txt\n"
    "@@ -0,0 +1 @@\n+old\n"
)
_NEW_LINK = (
    "diff --git a/link b/link\nnew file mode 120000\n--- /dev/null\n+++ b/link\n"
    "@@ -0,0 +1 @@\n+no-such-target\n\\ No newline at end of file\n"
)
_MODE_ALONE = "diff --git a/tool.sh b/tool.sh\nold mode 100644\nnew mode 100755\n"


def _repository(tmp_path: Path) -> Path:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "a.txt").write_text("old\n", encoding="utf-8")
    (repo / "tool.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    commit_fixture(repo, "record two files")
    return repo


def _entered(repo: Path, patch: str) -> list[str]:
    """Enter the workspace of one patch and name what it holds."""
    changes, gap = unified_patch_changes(repo, patch)
    assert not gap
    with owner.patched_workspace(repo, patch, changes) as (workspace, _postimages):
        return sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*"))


@pytest.mark.skipif(os.name == "nt", reason="a symbolic link and a rename read as POSIX entries")
@pytest.mark.parametrize(
    ("patch", "held"),
    [
        # A creation that fills the path a move vacates leaves that path's bytes as they were.
        (_MOVE_AND_REFILL, ["a.txt", "b.txt"]),
        # A link whose target is no file is an entry of its own, read without following it.
        (_NEW_LINK, ["link"]),
    ],
    ids=["move-and-refill", "new-link"],
)
def test_a_patch_that_took_effect_is_read_whatever_one_path_shows(
    tmp_path: Path, patch: str, held: list[str]
) -> None:
    """Git applies a patch whole or not at all, so one shown effect proves the apply ran."""
    assert _entered(_repository(tmp_path), patch) == held


def test_a_workspace_that_git_left_as_it_was_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exit status of 0 with no effect is the run that Git made in another repository."""
    repo = _repository(tmp_path)
    patch = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
    changes, _gap = unified_patch_changes(repo, patch)
    monkeypatch.setattr(
        owner, "run_git", lambda *args, **_named: subprocess.CompletedProcess(args, 0, b"", b"")
    )
    with (
        pytest.raises(ValueError, match="left the workspace as it was"),
        owner.patched_workspace(repo, patch, changes),
    ):
        pytest.fail("the workspace was yielded")


@pytest.mark.skipif(os.name == "nt", reason="executable bits")
def test_a_patch_whose_only_change_the_work_tree_holds_shows_no_effect(tmp_path: Path) -> None:
    """A mode change that the work tree already carries leaves the copy as it was: refused."""
    repo = _repository(tmp_path)
    (repo / "tool.sh").chmod(0o755)
    with pytest.raises(ValueError, match="left the workspace as it was"):
        _entered(repo, _MODE_ALONE)
