"""The patch workspace shows a patch's effect, or it refuses."""

from __future__ import annotations

import os
import subprocess
import tempfile
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
_EDIT = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"


def _repository(tmp_path: Path) -> Path:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "a.txt").write_text("old\n", encoding="utf-8")
    (repo / "tool.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    commit_fixture(repo, "record two files")
    return repo


def _entered(repo: Path, patch: str) -> list[str]:
    """Enter the workspace of one patch and name what it holds."""
    changes, gap = unified_patch_changes(repo, patch)
    assert (gap, bool(changes)) == ("", True)
    with owner.patched_workspace(repo, patch, changes) as (workspace, _postimages):
        return sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*"))


def test_a_creation_at_a_path_that_a_move_vacates_is_read(tmp_path: Path) -> None:
    """The refilled path holds its bytes as before; the move's own target shows the apply."""
    assert _entered(_repository(tmp_path), _MOVE_AND_REFILL) == ["a.txt", "b.txt"]


@pytest.mark.skipif(os.name == "nt", reason="a symbolic link")
def test_a_patch_that_makes_a_named_path_a_link_is_refused(tmp_path: Path) -> None:
    """The admission reads postimages as the text of regular files, so it judges no link."""
    with pytest.raises(ValueError, match="no regular file"):
        _entered(_repository(tmp_path), _NEW_LINK)


def test_a_workspace_that_git_left_as_it_was_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inside another checkout, with its ceiling defeated, Git exits with 0 and changes nothing."""
    repo = _repository(tmp_path)
    inside = init_git_repo(tmp_path / "other") / f"build{os.pathsep}1"
    inside.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(inside))
    with pytest.raises(ValueError, match="left a path that it names as it was"):
        _entered(repo, _EDIT)


def test_a_patch_that_changed_one_of_two_named_paths_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git skips by path: one path that shows the patch does not vouch for another."""
    repo = _repository(tmp_path)
    patch = _EDIT + _EDIT.replace("a.txt", "tool.sh").replace("-old", "-#!/bin/sh")

    def half(root: Path, *args: str, **_named: object) -> subprocess.CompletedProcess[bytes]:
        (root / "a.txt").write_text("new\n", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, b"", b"")

    changes, gap = unified_patch_changes(repo, patch)
    assert (gap, len(changes)) == ("", 2)
    monkeypatch.setattr(owner, "run_git", half)
    with (
        pytest.raises(ValueError, match="left a path that it names as it was"),
        owner.patched_workspace(repo, patch, changes),
    ):
        pytest.fail("the workspace was yielded")


@pytest.mark.skipif(os.name == "nt", reason="executable bits")
def test_a_patch_whose_only_change_the_work_tree_holds_shows_no_effect(tmp_path: Path) -> None:
    """A mode change that the work tree already carries leaves the copy as it was: refused."""
    repo = _repository(tmp_path)
    (repo / "tool.sh").chmod(0o755)
    with pytest.raises(ValueError, match="left a path that it names as it was"):
        _entered(repo, _MODE_ALONE)
